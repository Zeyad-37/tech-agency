---
name: address-feedback
description: "Address all open PR feedback in one pass: fetches unresolved review comments (human + Copilot + bot) and failing quality gates, plans fixes, applies them, pushes, and re-watches checks until green. Use after /ship-it once external review is in. The bias-sensitive work (judging feedback, planning and applying fixes) runs in a fresh-context subagent every invocation, so the current conversation can never bias how reviewer feedback is judged. Pass --auto-merge to merge automatically once green; otherwise stops at a final approval gate. Triggers: 'address feedback', 'handle PR feedback', 'fix review comments', 'resolve PR comments', 'address PR', 'finish PR'."
---

# Address Feedback — Resolve PR Comments and Quality Gates

This skill is the back half of the delivery loop. It assumes a PR exists (typically created by `/ship-it`) and external review has produced feedback. It collects every unresolved comment and failing check, applies fixes, and lands the PR.

## Step 0: Run the Feedback Pass in a Fresh Context (mandatory, unconditional)

If the agent carries the session conversation into this pass, it is biased — it already "knows" why the code was written the way it was, and will tend to dismiss reviewer feedback ("the reviewer is wrong, I know this code") or apply a fix that rationalizes the original choice. The judgment about *whether a reviewer is right* and *what the fix should be* MUST be made by an agent with no memory of the current session, working only from the PR's committed state and the reviewers' comments.

**Always run the bias-sensitive work in a fresh-context subagent — every invocation, no exceptions.** Spawn it with the `Agent` tool using `subagent_type: general-purpose`. The orchestrating agent passes the subagent **only** the PR number/branch and the `--auto-merge` flag — never any "what we did / why we did it" narrative from the session, because that narrative is exactly the bias being excluded. The subagent re-derives all feedback fresh from `gh`/git.

Run order with the interactive gates preserved:

1. **Subagent pass A (fresh context):** runs Steps 2–4 — locate or create the branch's worktree, gather all feedback, classify and plan. Returns the feedback summary table and the proposed fix plan as its result. Asks the user nothing.
2. **Parent relays Step 5:** the orchestrating agent presents the returned plan to the user and gets confirmation (or auto-approves under `--auto-merge`). Relaying a plan the subagent produced carries no code bias.
3. **Subagent pass B (fresh context):** given the approved plan + PR number, runs Steps 6–7 — apply fixes, reply to threads, push, watch checks. If new failures appear it loops within its own pass (cap 3). Returns what it changed and the final check status.
4. **Parent relays Step 8:** the orchestrating agent presents the merge gate to the user and, on approval (or under `--auto-merge`), performs the mechanical merge and Step 9 cleanup. Merging is mechanical and needs no fresh context.

Each subagent pass starts clean and never sees this conversation. The parent's role is limited to relaying gates and the final mechanical merge — it must not inject session rationale into either subagent prompt.

## Step 1: Parse Arguments

Look for these in the user's prompt:

- **PR number** (e.g. `#123` or `123`) — if absent, infer from the current branch via `gh pr view --json number,url,headRefName,baseRefName`.
- **`--auto-merge` flag** — if present, the skill merges automatically once everything is green and resolved. If absent, the skill stops at a final approval gate.

Confirm the parsed values with the user in one line:

```
PR: #123 (branch: feature/foo)  |  Auto-merge: ON/OFF
```

## Step 2: Locate (or Create) the Branch's Worktree, Then Sync

Per the worktree-first rule (`@.claude/rules/shared/worktree-first.md`), the fix work must run in a worktree — never the main checkout. First **search for an existing worktree** already checked out on `{branch}`; if one exists, reuse it; only if none exists do you **create a new one**.

```bash
BRANCH="{branch}"

# 1. Search every existing worktree (this includes the main checkout) for one
#    already on BRANCH.
WT_PATH=$(git worktree list --porcelain | awk -v b="refs/heads/$BRANCH" '
  $1=="worktree" {p=$2}
  $1=="branch" && $2==b {print p; exit}')

if [ -n "$WT_PATH" ] && [ "$WT_PATH" != "$(git rev-parse --show-toplevel)" ]; then
  # 2a. Found a dedicated worktree on this branch — reuse it.
  echo "Reusing existing worktree: $WT_PATH"
  cd "$WT_PATH"
elif [ -n "$WT_PATH" ]; then
  # 2b. The branch is checked out in the MAIN checkout. That violates
  #     worktree-first — move it into a dedicated worktree instead.
  MAIN_REPO="$WT_PATH"
  WT_PATH="${MAIN_REPO}/../$(basename "$MAIN_REPO")-worktrees/${BRANCH//\//-}"
  git -C "$MAIN_REPO" checkout main        # free the branch from the main checkout
  git worktree add "$WT_PATH" "$BRANCH"
  cd "$WT_PATH"
else
  # 2c. No worktree on this branch anywhere — create one.
  MAIN_REPO=$(git rev-parse --show-toplevel)
  WT_PATH="${MAIN_REPO}/../$(basename "$MAIN_REPO")-worktrees/${BRANCH//\//-}"
  git worktree add "$WT_PATH" "$BRANCH"    # branch already exists (the PR branch)
  cd "$WT_PATH"
fi

# 3. Confirm location, then sync with remote.
pwd                              # must be inside the worktree, not the main checkout
git branch --show-current        # must equal $BRANCH
git fetch origin
git pull --ff-only origin "$BRANCH"
```

Notes:
- The search in step 1 uses `git worktree list`, which includes the main checkout — so if the branch happens to be checked out there, it's found (and step 2b relocates it to a dedicated worktree to honor worktree-first).
- `git worktree add <path> <branch>` (no `-b`) attaches the **existing** PR branch; don't create a new branch.
- This resolution is idempotent: subagent pass A may create the worktree, and pass B's identical Step 2 then finds and reuses it.
- If the pull is not fast-forward, surface the conflict to the user and stop. Do not auto-rebase or auto-merge.
- Cleanup of a worktree created here is handled in Step 9 (`git worktree remove`) after merge.

## Step 3: Gather Feedback

Collect every source of feedback in parallel. Use `gh` for all GitHub calls.

### 3a. Review comments (line-level)

```bash
gh api repos/{owner}/{repo}/pulls/{n}/comments --paginate
```

Filter to comments where `in_reply_to_id` is null OR the thread is not marked resolved. The GraphQL API gives resolution state directly; prefer it when comments are many:

```bash
gh api graphql -f query='
  query($owner:String!,$name:String!,$num:Int!){
    repository(owner:$owner,name:$name){
      pullRequest(number:$num){
        reviewThreads(first:100){
          nodes{ isResolved isOutdated comments(first:20){ nodes{ id author{login} body path line } } }
        }
      }
    }
  }' -F owner={owner} -F name={repo} -F num={n}
```

Keep only threads where `isResolved == false` and `isOutdated == false`.

### 3b. Issue-level comments (PR conversation)

```bash
gh api repos/{owner}/{repo}/issues/{n}/comments --paginate
```

Filter to comments newer than the latest push by the PR author. Include Copilot, reviewers, bots.

### 3c. PR reviews (summary verdicts)

```bash
gh pr view {n} --json reviews
```

Capture any review with state `CHANGES_REQUESTED` and its body.

### 3d. Failing checks

```bash
gh pr checks {n} --json name,state,link
```

For each `FAILURE` or `CANCELLED` check, fetch the failing job log:

```bash
gh run view {run-id} --log-failed
```

Cap log retrieval at 200 lines per failed job to avoid blowing context.

## Step 4: Classify and Plan

Group findings into a single table, deduplicating overlapping comments (Copilot often mirrors human reviewers):

```markdown
## Feedback Summary — PR #{n}

| # | Source | Severity | File:Line | Issue | Proposed Fix |
|---|--------|----------|-----------|-------|--------------|
| 1 | reviewer @alice | required | Foo.kt:42 | NPE on null user | guard with ?: return |
| 2 | Copilot | required | Bar.kt:10 | Hardcoded URL | move to BuildConfig |
| 3 | CI: detekt | required | Baz.kt:5 | force-unwrap | use ?: error(...) |
| 4 | reviewer @bob | recommended | Qux.kt:88 | rename variable | rename to {x} |

**Required:** {n}  |  **Recommended:** {n}  |  **Failing checks:** {n}
```

Severity:
- **required** — anything in a `CHANGES_REQUESTED` review, anything from a failing check, anything explicitly marked "must fix" / "blocking" / "P0" / "P1" by a reviewer.
- **recommended** — everything else from human reviewers and Copilot suggestions phrased as "consider …" / "nit:" / "could".

If there are zero required items and zero failing checks, jump to Step 8.

## Step 5: Confirm the Plan

Present the table to the user and ask:

> Apply all REQUIRED fixes + failing-check repairs now? Recommended items: apply small ones, defer large ones as follow-up tasks. (y / n / select)

Default to "y" if the user provided `--auto-merge` — they've signed up for autonomy.

## Step 6: Apply Fixes

For each REQUIRED item:

1. Apply the fix in the touched file.
2. Run the relevant test for the touched module: `./gradlew :{module}:allTests`.
3. Commit with: `[STORY-ID] @{Agent}: address review — {short description}`.

For failing checks specifically:
- **detekt / lint** — fix the violation, do not add to baseline unless the user explicitly asks.
- **test failures** — fix the implementation, not the test, unless the test is genuinely wrong (state your reasoning before changing a test).
- **build failures** — fix and re-run locally before pushing.

For RECOMMENDED items that are small (rename, missing doc, trivial null-safety), apply inline. For larger recommendations (refactors, broader cleanups), file them to `docs/guides/tech-debt/backlog.md` as follow-up tasks and link them in the PR comment thread.

## Step 7: Reply, Push, Re-watch

### 7a. Reply to threads

For each resolved comment thread, post a brief reply via:

```bash
gh api repos/{owner}/{repo}/pulls/{n}/comments \
  -f body="Addressed in {commit-sha}: {one-line summary}" \
  -F in_reply_to={comment-id}
```

Mark the thread resolved via GraphQL `resolveReviewThread` mutation if the project uses required-resolution.

### 7b. Push

```bash
git push origin {branch}
```

### 7c. Watch checks

```bash
gh pr checks {n} --watch
```

This blocks until all checks finish. On any new failure, loop back to Step 3 and address the new feedback. Cap the loop at 3 iterations — if checks fail a third time, stop and surface to the user.

## Step 8: Merge Gate

Compute readiness:

```
[ ] No unresolved review threads
[ ] No CHANGES_REQUESTED reviews still active (need a new APPROVED review or explicit dismissal)
[ ] All required checks GREEN
[ ] Branch up to date with base
```

If any box is unchecked, report what's missing and stop.

If all green, both modes run the **same pre-merge sequence**. The only difference between them is whether a human confirms first — nothing merges immediately in either mode, because the board commit has to land in the PR first.

**Pre-merge board sequence (both modes):**

1. Run `/update-board {TASK-ID} → Done`. The board update must land in the same PR as the change, never as a separate commit on `main` (see `@.claude/rules/shared/board-in-pr.md`). `/update-board` Step 3 commits **and pushes** for a `→ Done` transition — it is the single owner of that push, so do not run `git push` again here.
2. That push is a new head and re-triggers required checks. **Re-evaluate the readiness checklist above against the new head** — "All required checks GREEN" and "Branch up to date with base" were computed against the pre-board-commit head and no longer hold. Wait for the new run to finish.
3. If the new run fails, drop the Done commit off the branch (`git reset --hard HEAD~1` then `git push --force-with-lease`), move the task back to Review, and re-enter Step 3 with the new failure — bounded by the same 3-iteration cap as Step 7c.
4. Once the new run is green, merge.

Then take the merge decision:

- **Without `--auto-merge`**: print a summary and ask the user "Merge now? (y/n)". Wait for explicit confirmation, then run the pre-merge board sequence and merge.
- **With `--auto-merge`**: skip the confirmation prompt only — proceed straight into the pre-merge board sequence, then merge.

Merge command:

```bash
gh pr merge {n} --squash --delete-branch
```

Use `--squash` by default to keep `main` history clean; the project's `shared-standards.md` doesn't mandate a strategy, so squash is the safe default for feature branches. If the user prefers merge commits or rebase, they'll say so.

## Step 9: Post-Merge Cleanup

```bash
MAIN_REPO=$(git rev-parse --path-format=absolute --git-common-dir | xargs dirname)
cd "$MAIN_REPO"                       # step out of the worktree before removing it
git checkout main
git pull --ff-only
git worktree remove "$WT_PATH"        # the worktree resolved/created in Step 2
git branch -d "$BRANCH"               # safe-delete now that the branch isn't checked out
```

Remove the worktree before deleting the branch (git refuses to delete a branch that's still checked out in a worktree). If `$WT_PATH` was the main checkout itself (none was created — rare), skip `git worktree remove` and just `git checkout main`.

No board update happens here — `→ Done` was already committed and pushed onto the PR branch in Step 8, so it merged with the change. Never commit `board-context.md` on `main`.

Print:

```markdown
## ✅ PR #{n} merged

**Commit:** {sha} on main
**Task:** {task-id} → Done
**Required fixes applied:** {n}
**Recommended applied / deferred:** {n} / {n}
**Follow-up tech-debt tasks filed:** {n}
```

## Failure Modes

- **Conflicts on `git pull --ff-only`** → stop, ask user to resolve. Never auto-rebase.
- **CI is flaky** → re-run the failed check once via `gh run rerun --failed`. If it fails again, treat as a real failure.
- **Reviewer wants something we disagree with** → never silently ignore. Either implement, or push back with reasoning in a PR comment and ask the user how to proceed.
- **Auto-merge is on but a required reviewer hasn't approved** → stop at the merge gate regardless; auto-merge means "no manual gate from me", not "bypass branch protection".

## Notes

- This skill is intentionally one-shot. For continuous event-driven response to PR events (Copilot finishes → auto-respond), build a GitHub Actions workflow that invokes Claude headlessly; this skill is for human-initiated "the feedback is in, deal with it" passes.
- The `--auto-merge` flag changes the final approval, not the review-application step. The plan in Step 5 still gets auto-approved when `--auto-merge` is set, because asking twice in the same run would defeat the flag's purpose.
