---
name: create-pr
description: "Create a pull request with a standardized format. The PR title includes the task ID, and the body lists participating agents, a summary, test plan, and review checklist. Use when the user says 'create PR', 'open PR', 'submit PR', 'make a pull request', 'PR for this branch', or 'ready for review'. This skill commits any uncommitted changes, pushes the branch, and creates the PR automatically — no additional confirmation required."
---

# Create PR — Standardized Pull Request Creation

This skill creates a pull request with a consistent, structured format that includes the task ID in the title, lists the authoring and participating agents, and provides a summary, test plan, and review checklist. It ensures every PR in the agency follows the same template regardless of which agent or skill initiates it.

**Auto-push enabled:** Invoking `/create-pr` is the explicit authorization to commit, push, and open the PR. No additional confirmation is needed.

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

## Step 3b: Check for UI Changes and Visual Evidence

Before presenting the PR, check if the branch contains UI changes that need visual evidence:

```bash
# Detect UI-related file changes
UI_CHANGES=$(git diff --name-only main..HEAD | grep -iE '(Screen|Content|Component|View|Composable|Preview|page\.tsx|page\.jsx|layout\.tsx|designsystem|DesignSystem|Theme|Color|Typography|Spacing)' | head -5)
```

If `UI_CHANGES` is non-empty:

1. Check if `.screenshots/` directory exists with before/after images
2. If screenshots exist, include the **Visual Changes** section in the PR body (see template above)
3. If screenshots do NOT exist, prompt the user:

```
UI changes detected in this PR:
  {list of UI-related files}

Visual evidence (before/after screenshots) is required for UI changes.
Run `/capture-screenshots` to generate them automatically, or provide screenshots manually.

Continue without screenshots? (not recommended)
```

If the user chooses to continue without screenshots, add a note in the Visual Changes section:

```markdown
## Visual Changes

> **WARNING:** Visual evidence was not provided for this PR. Reviewer should request screenshots before approving.
```

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

## Step 6: Report the PR

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
