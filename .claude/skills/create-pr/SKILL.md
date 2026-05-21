---
name: create-pr
description: "Create a pull request with a standardized format. The PR title includes the task ID, and the body lists participating agents, a summary, test plan, and review checklist. If the branch has UI changes, before/after screenshots are captured automatically and embedded in the PR. Use when the user says 'create PR', 'open PR', 'submit PR', 'make a pull request', 'PR for this branch', or 'ready for review'. This skill commits any uncommitted changes, pushes the branch, and creates the PR automatically — no additional confirmation required."
---

# Create PR — Standardized Pull Request Creation

This skill creates a pull request with a consistent, structured format that includes the task ID in the title, lists the authoring and participating agents, and provides a summary, test plan, and review checklist. It ensures every PR in the agency follows the same template regardless of which agent or skill initiates it.

**Auto-push enabled:** Invoking `/create-pr` is the explicit authorization to commit, push, and open the PR. No additional confirmation is needed.

**Auto-screenshots:** If the branch contains UI changes, `/create-pr` automatically runs `/capture-screenshots` to generate before/after visual evidence and embeds the comparison table in the PR. This is mandatory and non-skippable for UI PRs — the only fallback is a manual screenshot request when screenshot tooling is not configured for the affected platform (see Step 3b).

## When to Use

Call `/create-pr` when:

- An agent finishes a task and is ready for code review
- After `/update-board {TASK-ID} → Review` has been run (board is already updated)
- When the user explicitly asks to create a PR for the current branch

Other skills (`/pick-up-task`, `/kick-off`, `/tech-task`, `/dispatch`) invoke this automatically at the end of their task completion flow.

## Pre-flight: Rebase onto Main if Behind

Before doing anything else, fetch the latest state of `main` and rebase the current branch onto it if it has fallen behind. A PR opened from a stale branch risks conflicts and makes review harder.

```bash
# Fetch latest remote state without merging
git fetch origin main

# Check how many commits the branch is behind main
BEHIND=$(git rev-list --count HEAD..origin/main)
echo "Branch is $BEHIND commit(s) behind origin/main"
```

**If `BEHIND` is 0** — branch is up to date. Proceed to Step 1.

**If `BEHIND` is > 0** — rebase automatically:

```bash
git rebase origin/main
```

- If the rebase succeeds cleanly, report to @Zeyad and proceed to Step 1:
  ```
  ✅ Rebased onto origin/main ({BEHIND} commit(s) applied). Branch is now up to date.
  ```

- If the rebase hits conflicts, abort and stop:
  ```bash
  git rebase --abort
  ```
  Then report:
  ```
  ⚠️  Rebase onto origin/main failed due to merge conflicts.

  Conflicts must be resolved manually before creating the PR.
  Run the following, resolve conflicts, then re-run /create-pr:

    git rebase origin/main
    # resolve conflicts in each file
    git add <resolved-files>
    git rebase --continue
  ```
  Do NOT proceed until the rebase is clean.

## Step 1: Gather PR Context

Collect the following from the current branch and task context:

- **Task ID**: Infer from the branch name (e.g., `US-042/login-screen` → `US-042`) or the most recent commit prefix
- **Branch name**: `git branch --show-current`
- **Base branch**: Usually `main` (verify with `git remote show origin | grep 'HEAD branch'` if unsure)
- **Primary author**: The agent who did the majority of the work (from commit history: `git log --format='%s' main..HEAD`)
- **Participating agents**: All agents who contributed commits on this branch (extract unique `@AgentName` from commit messages)
- **Task description**: From the board or the branch name's description slug
- **Related docs**: Check `docs/{feature-name}/` for PRD, BRD, ADR, RFC references

```bash
# Gather context
BRANCH=$(git branch --show-current)
TASK_ID=$(echo "$BRANCH" | grep -oE '^[A-Z]+-[0-9]+' || echo "$BRANCH" | cut -d'/' -f1)

# Get all participating agents from commit messages
AGENTS=$(git log --format='%s' main..HEAD | grep -oE '@[A-Za-z]+' | sort -u | tr '\n' ', ' | sed 's/,$//')

# Get primary author (most commits)
PRIMARY=$(git log --format='%s' main..HEAD | grep -oE '@[A-Za-z]+' | sort | uniq -c | sort -rn | head -1 | awk '{print $2}')

# Count commits and changed files
COMMIT_COUNT=$(git rev-list --count main..HEAD)
FILES_CHANGED=$(git diff --stat main..HEAD | tail -1)
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
- **Branch:** `{BRANCH}` → `main`
```

## Step 3b: Check for UI Changes and Capture Visual Evidence (Mandatory)

Before presenting the PR, check if the branch contains UI changes that need visual evidence:

```bash
# Detect UI-related file changes
UI_CHANGES=$(git diff --name-only main..HEAD | grep -iE '(Screen|Content|Component|View|Composable|Preview|page\.tsx|page\.jsx|layout\.tsx|designsystem|DesignSystem|Theme|Color|Typography|Spacing)' | head -5)
```

**If `UI_CHANGES` is empty** — no UI changes. Omit the Visual Changes section entirely and proceed to Step 4.

**If `UI_CHANGES` is non-empty** — before/after screenshots are mandatory. Do NOT prompt the user to opt out and do NOT proceed without visual evidence:

1. If `.screenshots/before/` and `.screenshots/after/` already exist with images for the affected screens, reuse them — include the **Visual Changes** section in the PR body (see template above) and proceed to Step 4.
2. Otherwise, automatically invoke `/capture-screenshots` to generate the before/after comparison. This runs the full per-platform capture flow (Paparazzi / swift-snapshot-testing / Playwright) on `main` and the feature branch, and produces the comparison table.

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

## Step 5: Push and Create the PR

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
- **Branch:** `{branch}` → `main`
EOF
)" \
  --base main
```

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
  Branch: {branch} → main
  Author: @{PrimaryAgent}
  Participants: @{Agent1}, @{Agent2}
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
