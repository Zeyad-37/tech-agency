---
name: address-feedback
description: "Address all open PR feedback in one pass: fetches unresolved review comments (human + Copilot + bot) and failing quality gates, plans fixes, applies them, pushes, and re-watches checks until green. Use after /ship-it once external review is in. Pass --auto-merge to merge automatically once green; otherwise stops at a final approval gate. Triggers: 'address feedback', 'handle PR feedback', 'fix review comments', 'resolve PR comments', 'address PR', 'finish PR'."
---

# Address Feedback — Resolve PR Comments and Quality Gates

This skill is the back half of the delivery loop. It assumes a PR exists (typically created by `/ship-it`) and external review has produced feedback. It collects every unresolved comment and failing check, applies fixes, and lands the PR.

## Step 1: Parse Arguments

Look for these in the user's prompt:

- **PR number** (e.g. `#123` or `123`) — if absent, infer from the current branch via `gh pr view --json number,url,headRefName,baseRefName`.
- **`--auto-merge` flag** — if present, the skill merges automatically once everything is green and resolved. If absent, the skill stops at a final approval gate.

Confirm the parsed values with the user in one line:

```
PR: #123 (branch: feature/foo)  |  Auto-merge: ON/OFF
```

## Step 2: Ensure Local Branch Matches Remote

```bash
git fetch origin
git checkout {branch}
git pull --ff-only origin {branch}
```

If the pull is not fast-forward, surface the conflict to the user and stop. Do not auto-rebase or auto-merge.

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

For RECOMMENDED items that are small (rename, missing doc, trivial null-safety), apply inline. For larger recommendations (refactors, broader cleanups), file them to `docs/tech-debt/backlog.md` as follow-up tasks and link them in the PR comment thread.

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

If all green:

- **Without `--auto-merge`**: print a summary and ask the user "Merge now? (y/n)". Wait for explicit confirmation.
- **With `--auto-merge`**: merge immediately.

Merge command:

```bash
gh pr merge {n} --squash --delete-branch
```

Use `--squash` by default to keep `main` history clean; the project's `shared-standards.md` doesn't mandate a strategy, so squash is the safe default for feature branches. If the user prefers merge commits or rebase, they'll say so.

## Step 9: Post-Merge Cleanup

```bash
git checkout main
git pull --ff-only
git branch -d {branch}
git worktree remove {path}  # only if this was a worktree
```

Run `/update-board {TASK-ID} → Done` to commit the final board transition on `main`.

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
