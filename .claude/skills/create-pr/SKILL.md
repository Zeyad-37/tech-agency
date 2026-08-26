---
name: create-pr
description: "Create a pull request with a standardized format. The PR title includes the task ID, and the body lists participating agents, a summary, test plan, and review checklist. If the branch has UI changes, before/after screenshots are captured automatically and embedded in the PR. Auto-pushes by default; pass --no-push to stop after the pre-push verification gate (used by parent skills like /ship-it that manage their own approval flow). Use when the user says 'create PR', 'open PR', 'submit PR', 'make a pull request', 'PR for this branch', or 'ready for review'."
---

# Create PR — Standardized Pull Request Creation

This skill creates a pull request with a consistent, structured format that includes the task ID in the title, lists the authoring and participating agents, and provides a summary, test plan, and review checklist. It ensures every PR in the agency follows the same template regardless of which agent or skill initiates it.

**Default: auto-push.** Invoking `/create-pr` without flags is the explicit authorization to commit, run pre-push verification, push the branch, and open the PR — no additional confirmation needed. Pass `--no-push` to stop after the verification gate (Step 4b) so a parent skill (e.g. `/ship-it`) can handle push and `gh pr create` with its own approval flow. The verification gate runs in both modes — `--no-push` defers push, not safety.

**Base branch:** Pass `--base <branch>` when the PR should merge into something other than `main` — typically an epic integration branch (`epic/{EPIC-ID}-{slug}`) for branches dispatched off an epic. Without the flag, Pre-flight 0 resolves the base automatically.

**Auto-screenshots:** If the branch contains UI changes, `/create-pr` automatically runs `/capture-screenshots` to generate before/after visual evidence and embeds the comparison table in the PR. This is mandatory and non-skippable for UI PRs — the only fallback is a manual screenshot request when screenshot tooling is not configured for the affected platform (see Step 3b).

## When to Use

Call `/create-pr` when:

- An agent finishes a task and is ready for code review
- After `/update-board {TASK-ID} → Review` has been run (board is already updated)
- When the user explicitly asks to create a PR for the current branch

Other skills (`/pick-up-task`, `/kick-off`, `/tech-task`, `/dispatch`) invoke this automatically at the end of their task completion flow.

## Pre-flight 0: Resolve the Base Branch

The base branch is where this PR merges into AND what the branch is rebased onto. It is `main` for most work, but a branch that was cut from an epic integration branch must PR back into that integration branch. Resolve `BASE` in this order:

1. **`--base <branch>` flag** — passed by the caller (dispatched agents receive it from `/dispatch` / `/dispatch-task`, which record the base per task). Use it verbatim.
2. **Auto-detect an epic base** — if any `origin/epic/*` branch exists, pick the candidate (`main` + every `origin/epic/*`) whose merge-base with `HEAD` is the most recent commit. If an epic branch wins, confirm with @Zeyad before proceeding: "This branch appears to be cut from `epic/US-100-checkout` — target it instead of `main`?"
3. **Default** — `main`.

(The hotfix step from `worktree-first.md`'s resolution order is intentionally absent here: hotfix PRs are opened and merged by the `/hotfix` process, which owns its own release-branch + `main` merge flow — they don't go through `/create-pr`'s base detection.)

```bash
BASE="${BASE_FLAG:-main}"
if [ -z "$BASE_FLAG" ] && git ls-remote --heads origin 'epic/*' | grep -q .; then
  # Compare merge-base recency of main vs each epic/* branch
  git fetch origin main 'refs/heads/epic/*:refs/remotes/origin/epic/*'
  # git merge-base prints nothing when there is no common ancestor — guard each
  # result so an empty value never reaches the integer comparison.
  BEST=main; BEST_TIME=0
  mb=$(git merge-base HEAD origin/main 2>/dev/null) && [ -n "$mb" ] && BEST_TIME=$(git log -1 --format=%ct "$mb")
  while read -r ref; do
    b="${ref#refs/remotes/origin/}"
    mb=$(git merge-base HEAD "origin/$b" 2>/dev/null) || continue
    [ -n "$mb" ] || continue
    t=$(git log -1 --format=%ct "$mb")
    [ "$t" -gt "$BEST_TIME" ] && { BEST="$b"; BEST_TIME="$t"; }
  done < <(git for-each-ref --format='%(refname)' 'refs/remotes/origin/epic/*')
  BASE="$BEST"   # if not main, confirm with @Zeyad before continuing
fi
echo "PR base: $BASE"
```

`BASE` is used everywhere below — the rebase target, `gh pr create --base`, and the PR body. Never hardcode `main` past this point.

## Pre-flight: Rebase onto the Base if Behind

Before doing anything else, fetch the latest state of `$BASE` and rebase the current branch onto it if it has fallen behind. A PR opened from a stale branch risks conflicts and makes review harder.

```bash
# Fetch latest remote state without merging
git fetch origin "$BASE"

# Check how many commits the branch is behind the base
BEHIND=$(git rev-list --count HEAD.."origin/$BASE")
echo "Branch is $BEHIND commit(s) behind origin/$BASE"
```

**If `BEHIND` is 0** — branch is up to date. Proceed to Step 1.

**If `BEHIND` is > 0** — rebase automatically:

```bash
git rebase "origin/$BASE"
```

- If the rebase succeeds cleanly, report to @Zeyad and proceed to Step 1:
  ```
  ✅ Rebased onto origin/{BASE} ({BEHIND} commit(s) applied). Branch is now up to date.
  ```

- If the rebase hits conflicts, abort and stop:
  ```bash
  git rebase --abort
  ```
  Then report:
  ```
  ⚠️  Rebase onto origin/{BASE} failed due to merge conflicts.

  Conflicts must be resolved manually before creating the PR.
  Run the following, resolve conflicts, then re-run /create-pr:

    git rebase origin/{BASE}
    # resolve conflicts in each file
    git add <resolved-files>
    git rebase --continue
  ```
  Do NOT proceed until the rebase is clean.

## Step 1: Gather PR Context

Collect the following from the current branch and task context:

- **Task ID**: Infer from the branch name (e.g., `US-042/login-screen` → `US-042`) or the most recent commit prefix
- **Branch name**: `git branch --show-current`
- **Base branch**: `$BASE` from Pre-flight 0 (`main` unless overridden or auto-detected as an epic integration branch)
- **Primary author**: The agent who did the majority of the work (from commit history: `git log --format='%s' "origin/$BASE"..HEAD`)
- **Participating agents**: All agents who contributed commits on this branch (extract unique `@AgentName` from commit messages)
- **Task description**: From the board or the branch name's description slug
- **Related docs**: Check `docs/{feature-name}/` for PRD, BRD, ADR, RFC references

```bash
# Gather context
BRANCH=$(git branch --show-current)
TASK_ID=$(echo "$BRANCH" | grep -oE '^[A-Z]+-[0-9]+' || echo "$BRANCH" | cut -d'/' -f1)

# Get all participating agents from commit messages
AGENTS=$(git log --format='%s' "origin/$BASE"..HEAD | grep -oE '@[A-Za-z]+' | sort -u | tr '\n' ', ' | sed 's/,$//')

# Get primary author (most commits)
PRIMARY=$(git log --format='%s' "origin/$BASE"..HEAD | grep -oE '@[A-Za-z]+' | sort | uniq -c | sort -rn | head -1 | awk '{print $2}')

# Count commits and changed files
COMMIT_COUNT=$(git rev-list --count "origin/$BASE"..HEAD)
FILES_CHANGED=$(git diff --stat "origin/$BASE"..HEAD | tail -1)
```

## Step 2: Build the PR Title

The PR title MUST include the task ID as a prefix:

```
[{TASK-ID}] {Short description of what the PR does}
```

Examples:
- `[US-042] Add email validation to registration flow`
- `[T-003] Refactor shared DTO validation`
- `[BUG-017] Fix null crash on profile load`
- `[tech] Improve git hooks and add pre-push checks` (for tech tasks without a story ID)
- `[deps] Upgrade Kotlin to 2.1.0`
- `[HOT-001] Fix login crash on Android 14`

Rules for the title:
- Max 72 characters
- Imperative mood ("Add", "Fix", "Refactor" — not "Added", "Fixes", "Refactoring")
- No period at the end
- Task ID must match the branch naming convention from `shared-standards.md`

## Step 3: Build the PR Body

Use this template exactly:

```markdown
## Summary

{2-4 bullet points describing what changed and why. Focus on the "why" not the "what".}

## Agents

- **Primary author:** {PRIMARY_AGENT} — {role description}
- **Participating:** {COMMA_SEPARATED_AGENTS} (if more than one agent contributed)

## Changes

{Brief description of the key changes organized by area. For example:}
- **{Module/Layer}**: {What changed}
- **{Module/Layer}**: {What changed}
- **Tests**: {What test coverage was added}

## Related Docs

- {Link to PRD, BRD, ADR, RFC, or design spec if they exist — e.g., `docs/{feature-name}/prd.md`}
- {Or "N/A — no related feature docs" for tech tasks}

## Visual Changes

{Include this section ONLY if the PR contains UI changes. Omit entirely for non-UI PRs.}

{If `/capture-screenshots` was run, include the generated comparison table here:}

| Screen | Before | After |
|--------|--------|-------|
| {screen-name} | ![before](.screenshots/before/{path}) | ![after](.screenshots/after/{path}) |
| {screen-name} (dark) | ![before](.screenshots/before/{path}) | ![after](.screenshots/after/{path}) |

{If automated screenshots are not available, paste manual screenshots or note:}
- Screenshots attached as PR comment / inline images

> **Required:** Every PR with UI changes MUST include before/after visual evidence. Run `/capture-screenshots` to automate this, or provide screenshots manually.

## Test Plan

- [ ] {Specific verification step 1}
- [ ] {Specific verification step 2}
- [ ] Unit tests pass: `{test command}`
- [ ] Lint/format clean: `{lint command}`
- [ ] {Platform-specific check if applicable}

## Review Checklist

- [ ] Code follows coding standards (`@.claude/rules/{platform}-coding-standards.md`)
- [ ] All 4 states handled (loading, success, empty, error) — if UI change
- [ ] Accessibility requirements met — if UI change
- [ ] Visual evidence provided (before/after screenshots) — if UI change
- [ ] No force-unwraps (`!!` / `!`) in production code
- [ ] No hardcoded secrets or credentials
- [ ] Acceptance criteria from the task are satisfied
- [ ] Performance: no regressions (benchmark results below if applicable)

## Metrics

- **Commits:** {COMMIT_COUNT}
- **Files changed:** {FILES_CHANGED summary}
- **Branch:** `{BRANCH}` → `{BASE}`
```

## Step 3b: Check for UI Changes and Capture Visual Evidence (Mandatory)

Before presenting the PR, check if the branch contains UI changes that need visual evidence:

```bash
# Detect UI-related file changes
UI_CHANGES=$(git diff --name-only "origin/$BASE"..HEAD | grep -iE '(Screen|Content|Component|View|Composable|Preview|page\.tsx|page\.jsx|layout\.tsx|designsystem|DesignSystem|Theme|Color|Typography|Spacing)' | head -5)
```

**If `UI_CHANGES` is empty** — no UI changes. Omit the Visual Changes section entirely and proceed to Step 4.

**If `UI_CHANGES` is non-empty** — before/after screenshots are mandatory. Do NOT prompt the user to opt out and do NOT proceed without visual evidence:

1. If `.screenshots/before/` and `.screenshots/after/` already exist with images for the affected screens, reuse them — include the **Visual Changes** section in the PR body (see template above) and proceed to Step 4.
2. Otherwise, automatically invoke `/capture-screenshots` to generate the before/after comparison. This runs the full per-platform capture flow (Paparazzi / swift-snapshot-testing / Playwright) on the base branch (`$BASE`) and the feature branch, and produces the comparison table.

```
UI changes detected in this PR:
  {list of UI-related files}

Capturing before/after screenshots automatically (required for UI changes)…
```

After `/capture-screenshots` completes:

- Include the generated **Visual Changes** comparison table in the PR body.
- Ensure the screenshots are part of the PR. By default, commit them on this branch in Step 4 (`git add .screenshots/`) so the table renders on GitHub. If the project's convention is to keep `.screenshots/` out of git (PR-comment upload), follow the capture-screenshots skill's Option B and post the table as a PR comment after Step 5 instead.

**Only fall back to a manual screenshot request if automated capture is impossible** — i.e., `/capture-screenshots` reports the required tooling is not configured for an affected platform. In that case, follow the capture-screenshots skill's Step 4 (manual request) and add this note to the Visual Changes section so the gap is explicit and review-blocking:

```markdown
## Visual Changes

> **MANUAL EVIDENCE REQUIRED:** Automated screenshot tooling is not configured for {platform}.
> Reviewer must obtain before/after screenshots before approving — do not merge without them.
```

Never silently skip visual evidence for a UI PR.

## Step 4: Commit Any Uncommitted Changes and Push

Ensure all changes are committed, then push immediately — no confirmation required:

```bash
# Check for uncommitted changes
git status
```

If there are uncommitted changes, commit them using the standard format before pushing:

```bash
git add <relevant files>
git commit -m "[{TASK-ID}] @{Agent}: {description}"
```

## Step 4b: Pre-Push Verification Gate

Before pushing, run platform-specific compile and test gates that an Android-host-only build would miss. **Never push without these passing — a failed gate aborts the push** and the user fixes the underlying issue before re-invoking `/create-pr`.

```bash
# Detect project shape
HAS_KMP_IOS="no"
[ -d "iosApp" ] && HAS_KMP_IOS="yes"
[ -d "shared/src/iosMain" ] && HAS_KMP_IOS="yes"
ls -d **/src/iosMain 2>/dev/null | grep -q . && HAS_KMP_IOS="yes"

HAS_ANDROID_APP="no"
[ -d "androidApp" ] && HAS_ANDROID_APP="yes"
[ -d "app" ] && HAS_ANDROID_APP="yes"

# Re-detect UI changes (same heuristic Step 3b uses)
UI_CHANGES_PRESENT=$(git diff --name-only "origin/$BASE"..HEAD | grep -iE '(Screen|Content|Component|Composable|page\.tsx|page\.jsx)' | head -1)

# --- Gate 1: KMP/iOS compile gate ---
# Catches link errors, missing `actual` declarations, and KMP cross-target type
# mismatches that are invisible to Android host builds. This is the #1 source of
# "green locally, red in CI" misses for KMP projects.
if [ "$HAS_KMP_IOS" = "yes" ]; then
  echo "→ iOS compile gate: ./gradlew compileKotlinIosSimulatorArm64"
  ./gradlew compileKotlinIosSimulatorArm64 || { echo "❌ iOS compile gate failed. Push aborted."; exit 1; }
fi

# --- Gate 2: Host tests for changed feature modules ---
# Fast subset of the full test suite — only the modules this branch actually touched.
if [ "$HAS_ANDROID_APP" = "yes" ]; then
  CHANGED_MODULES=$(git diff --name-only "origin/$BASE"..HEAD | grep -oE '^features/[^/]+/[^/]+' | sort -u)
  for module in $CHANGED_MODULES; do
    GRADLE_PATH=":$(echo "$module" | tr '/' ':')"
    echo "→ Host tests: ${GRADLE_PATH}:testDebugUnitTest"
    ./gradlew "${GRADLE_PATH}:testDebugUnitTest" 2>/dev/null || true  # don't block on missing host-test config
  done
fi

# --- Gate 3: Screenshot-test compile (UI changes only) ---
# @Ignore'd Paparazzi tests in androidApp still COMPILE against feature *Content
# signatures. When a Content composable signature changes, this gate catches it
# locally — otherwise CI is the first to notice.
if [ -n "$UI_CHANGES_PRESENT" ] && [ "$HAS_ANDROID_APP" = "yes" ]; then
  echo "→ Screenshot-test compile gate: ./gradlew :androidApp:compileDebugUnitTestKotlin"
  ./gradlew :androidApp:compileDebugUnitTestKotlin || {
    echo "❌ Screenshot-test compile failed — a Content composable signature change broke @Ignore'd tests."
    echo "   Fix the test sites or update fixtures, then re-run /create-pr."
    exit 1
  }
fi

echo "✅ All pre-push gates passed."
```

**Why each gate exists:**

| Gate | What it catches | Why local Android builds miss it |
|---|---|---|
| iOS compile (`compileKotlinIosSimulatorArm64`) | iOS link errors, missing `actual` declarations, KMP cross-target type mismatches | Android host builds only compile `androidMain` + `commonMain` against the JVM target |
| Host tests (changed modules) | Logic regressions in unit tests of the modules you actually touched | The full test suite is too slow to run pre-push; this is the fast subset |
| Screenshot-test compile | Signature drift between feature `*Content` composables and `@Ignore`d Paparazzi tests in `androidApp` | The tests are `@Ignore`d so they don't run, but they DO compile — and break when signatures change |

If a gate fails, the push is aborted. Do not bypass.

## Step 5: Push and Create the PR

**If `--no-push` was passed: stop here.** All commits, the verification gate, and the prepared PR title/body remain in conversation context. Emit a handoff report so the parent skill (e.g. `/ship-it`) can push and `gh pr create` once it has explicit user approval:

```
✅ PR prepared locally (--no-push):
  Branch: {branch}
  Title: [{TASK-ID}] {short description}
  Body:  <ready for `gh pr create --body`>
  Verification gate: passed

Next: parent skill handles `git push -u origin {branch}` + `gh pr create` on approval.
```

Skip Steps 5–7. Do NOT run the worktree sweep (Step 6) — defer it to the parent skill or the next auto-push invocation.

Otherwise (auto-push, the default), proceed:

```bash
# 1. Push the branch (set upstream if first push)
git push -u origin "$BRANCH"

# 2. Create the PR
gh pr create \
  --title "[{TASK-ID}] {Short description}" \
  --body "$(cat <<'EOF'
## Summary

- {bullet 1}
- {bullet 2}

## Agents

- **Primary author:** @{PrimaryAgent} — {role}
- **Participating:** @{Agent1}, @{Agent2}

## Changes

- **{Area}**: {description}
- **Tests**: {test coverage added}

## Related Docs

- `docs/{feature-name}/{doc}.md`

## Visual Changes

{Include before/after screenshot table if UI changes are present, omit section if no UI changes}

## Test Plan

- [ ] Unit tests pass
- [ ] Lint clean
- [ ] {verification step}

## Review Checklist

- [ ] Coding standards followed
- [ ] Visual evidence provided — if UI change
- [ ] No force-unwraps in production code
- [ ] No hardcoded secrets
- [ ] Acceptance criteria satisfied

## Metrics

- **Commits:** {N}
- **Files changed:** {summary}
- **Branch:** `{branch}` → `{base}`
EOF
)" \
  --base "$BASE"
```

## Step 5b: Request a Copilot Review (Mandatory, Non-Blocking)

This repo's settings do **not** auto-request a Copilot review on new PRs, so `/create-pr` requests it explicitly via the GitHub API immediately after the PR is created. Skip this step entirely when `--no-push` was passed (no PR exists yet) — the parent skill owns the request in that path.

```bash
# Resolve owner/repo and the PR number just created
REPO=$(gh repo view --json nameWithOwner --jq '.nameWithOwner')
PR_NUMBER=$(gh pr view "$BRANCH" --json number --jq '.number')

# Request Copilot as a reviewer. The Copilot reviewer is a bot account, so it
# must be added through the requested_reviewers REST endpoint, not --reviewer.
gh api --method POST "repos/${REPO}/pulls/${PR_NUMBER}/requested_reviewers" \
  -f "reviewers[]=copilot-pull-request-reviewer[bot]" \
  && echo "✅ Copilot review requested on PR #${PR_NUMBER}" \
  || echo "⚠️  Could not request a Copilot review (feature may be disabled for this account/repo, or already requested). Continuing — this does not block the PR."
```

Rules for this step:
- **Non-blocking.** If the request fails — Copilot code review not enabled for the account/org, the bot already requested, insufficient permissions, or `gh` unavailable — log the warning and continue. Never abort PR creation over a failed Copilot request.
- Requesting Copilot is in **addition** to the human reviewers from the Reviewer Assignment matrix, not a replacement.
- Copilot code review must be enabled for the account/org (GitHub Copilot Pro/Business/Enterprise with code review turned on) for the request to succeed. The disabled auto-request setting only affects the automatic trigger — manual API requests still work when the feature itself is on.

## Step 6: Sweep Merged Worktrees (Auto-Cleanup)

Immediately after the PR is created, scan all existing worktrees and remove any whose branch has already been merged. This is how worktrees created by `/dispatch` and `/dispatch-task` get cleaned up — there is no separate cleanup command.

```bash
# Run from the main repo (NOT inside a worktree).
MAIN_REPO_ROOT="$(git rev-parse --show-toplevel)"
CURRENT_WT="$(pwd)"

git worktree list --porcelain | awk '/^worktree /{print $2}' | while read -r WT; do
  # Never touch the main checkout or the worktree we're currently inside.
  [ "$WT" = "$MAIN_REPO_ROOT" ] && continue
  [ "$WT" = "$CURRENT_WT" ] && continue

  BR=$(git -C "$WT" branch --show-current 2>/dev/null)
  [ -z "$BR" ] && continue

  # Only clean up if a PR for this branch is in merged state.
  MERGED_PR=$(gh pr list --head "$BR" --state merged --json number --jq '.[0].number' 2>/dev/null)
  if [ -n "$MERGED_PR" ]; then
    git -C "$MAIN_REPO_ROOT" worktree remove "$WT" \
      && git -C "$MAIN_REPO_ROOT" branch -d "$BR" \
      && echo "Cleaned up merged worktree: $WT (branch $BR, PR #$MERGED_PR)"
  fi
done
```

Rules for the sweep:
- Skip the main checkout. Skip the worktree the current shell is inside (the PR just created is not merged yet, so it would be skipped by the merged-state check anyway, but the explicit guard is belt-and-braces).
- Use `git branch -d` (safe delete), never `-D`. If the branch isn't fully merged, the delete fails and the worktree is preserved for manual inspection — that's the intended fallback.
- Report each cleanup on its own line so @Zeyad sees what was reclaimed.
- If `gh` is not available or `gh pr list` errors, skip the sweep silently rather than blocking the PR flow.

## Step 7: Report the PR

After the PR is created, report back:

```
PR created: #{pr_number}
  Title: [{TASK-ID}] {description}
  Branch: {branch} → {base}
  Author: @{PrimaryAgent}
  Participants: @{Agent1}, @{Agent2}
  Copilot review: requested (or "not requested — {reason}")
  URL: {pr_url}

Next: Run `/code-review` to get a structured review, or tag a specific agent for review.
```

## Reviewer Assignment

Suggest reviewers based on the task type and the code review matrix:

| Change Type | Suggested Reviewers |
|------------|-------------------|
| Frontend (Web) | @Nova + one backend agent if API changes |
| iOS | @Swift + @Link if KMP shared code changed |
| Android | @Kai + @Link if KMP shared code changed |
| KMP shared | @Link + @Swift + @Kai (all platform consumers) |
| Backend (Node) | @Flux + @Shield if auth/security |
| Backend (Python) | @Pyra + @Shield if auth/security |
| Backend (JVM/Ktor) | @Forge or @Link + @Shield if auth/security |
| Infrastructure/CI | @Sentinel |
| Design system | @Pixel + platform implementers |
| Any security-sensitive change | @Shield (mandatory) |

Add `--reviewer` flags to `gh pr create` when reviewers can be determined:

```bash
gh pr create ... --reviewer "shield" --reviewer "link"
```

A **Copilot review is always requested in addition** to these human reviewers (see Step 5b). Copilot is a bot account and cannot be added via `--reviewer` — it goes through the `requested_reviewers` API call in Step 5b.

## Multi-Agent PRs

When multiple agents contributed to a branch (common with `/dispatch` or shared branches):

- List ALL participating agents in the "Agents" section
- The primary author is the agent with the most commits
- Each agent's contributions should be noted in the "Changes" section
- All participating agents should be tagged in the PR description

## Integration with Other Skills

This skill is automatically invoked by:
- `/pick-up-task` — after task completion, board update, and test verification
- `/kick-off` — after the task work is complete
- `/tech-task` — after implementation and board update
- `/dispatch` — after each dispatched agent finishes in their worktree

Agents can also invoke it directly at any time by saying "create PR" or "open a pull request".

## PR Update (Amending an Existing PR)

If the PR already exists and you need to update it (e.g., after code review changes):

1. Commit your changes locally with the standard commit format
2. Push immediately — `/create-pr` carries push authorization:

```bash
git push

# Update the PR body if needed
gh pr edit {PR_NUMBER} --body "$(cat <<'EOF'
{updated body}
EOF
)"
```

Do NOT force-push or amend existing commits on a PR that's under review — create new commits so reviewers can see what changed.
