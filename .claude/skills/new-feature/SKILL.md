---
name: new-feature
description: "Kick off a new feature on an existing product. Starts with Diana (BRD) or Sage (ADR) depending on scope, then sets up board tasks. Use when the user says 'add a feature', 'new feature', 'I want to add', 'implement [something] for [product]', or describes a feature to add to an existing codebase."
---

# New Feature Kickoff

This skill handles the planning chain for adding a feature to an existing product. It's lighter than a full product kickoff — it may skip Morgan (PRD) if the user already knows what they want.

## Step 1: Assess Scope

Ask the user (if not already clear):

- **What** feature? (description)
- **Why?** (user need / business goal)
- **Which product/codebase?** (to find existing docs)
- **Rough size?** (small = 1-2 stories, medium = 3-5, large/epic = 6+)

Check `docs/` for existing context on this product. Documents are filed by type per `@.claude/rules/shared/handoff-protocol.md` as `docs/{doc-type}/{Task-Id}-{Doc Type}-Title.md`:

```bash
grep -ril "{feature-name}" docs/artifacts/prd/ docs/artifacts/brd/ docs/artifacts/adr/ docs/artifacts/rfc/ docs/artifacts/design-spec/ 2>/dev/null
```

## Step 2: Route by Size

### Small feature (1-2 stories)
Skip BRD. Go straight to the relevant engineer:
```
Using [agent], implement [feature].
User story: [ID]: [description].
Context: the docs found in Step 1 (docs/artifacts/prd/, docs/artifacts/brd/, docs/artifacts/adr/ ...).
```

### Medium feature (3-5 stories)
Start with Diana for a focused BRD:
```
Write a BRD for adding [feature] to [product].
Context: [what exists, what's changing].
Existing architecture: the ADRs found in docs/artifacts/adr/ for this product.
```
Save to `docs/artifacts/brd/{Task-Id}-BRD-{Title}.md`. **Get @Zeyad approval.**

Then have Sage review if architectural changes are needed. If yes, write an ADR. If the feature fits within existing architecture, skip Sage and go to Atlas for board setup.

### Large feature / Epic
This is an RFC situation. Tell the implementing agent:
```
This is an epic. Write an RFC before any code.
Save to docs/artifacts/rfc/{Task-Id}-RFC-{Title}.md.
Include: Goal, Background, Proposed Plan, Alternatives (2+), Open Questions, Estimated Scope.
```
**Get @Zeyad approval on the RFC.**

Then follow the full chain: Diana (BRD) → Sage (ADR if needed) → Atlas (board setup).

## Step 3: Create a Worktree

Before any implementation begins, create a **git worktree**. All Claude Code work happens in a worktree — the main checkout is an orchestration root only, and `git checkout -b` there stomps any parallel session. See `@.claude/rules/shared/worktree-first.md`.

Resolve the base branch first, per `worktree-first.md` § Base Branch Resolution: explicit `--base` → epic integration branch (`epic/{EPIC-ID}-{slug}`) → hotfix release tag → `origin/main`.

```bash
MAIN_REPO="$(git rev-parse --show-toplevel)"

BASE="main"                                  # or epic/{EPIC-ID}-{slug} when this feature belongs to an epic
BRANCH="{STORY-ID}/{short-description}"      # e.g. US-042/social-sharing, FEAT-007/push-notifications
WORKTREE_DIR="${MAIN_REPO}/../$(basename "$MAIN_REPO")-worktrees/${BRANCH//\//-}"

git -C "$MAIN_REPO" fetch origin "$BASE"
git -C "$MAIN_REPO" worktree add --no-track -b "$BRANCH" "$WORKTREE_DIR" "origin/$BASE"
cd "$WORKTREE_DIR"

# Verify BEFORE any write. If either check fails, STOP and report — do not
# proceed in the wrong directory and do not modify the main checkout.
pwd                          # must equal $WORKTREE_DIR
git branch --show-current    # must equal $BRANCH
```

The worktree's PR merges back into `$BASE` — branch-off and merge-into are always the same branch.

For small features that skip board setup, create the worktree immediately after routing to the engineer. For medium/large features, create it after board tasks are set up (so the story ID is available).

## Step 4: Board Setup

For medium and large features, invoke Atlas:
```
Break down the [feature] into tasks and add to the board via board.create_task().
Reference: docs/artifacts/brd/{Task-Id}-BRD-{Title}.md [and the ADR/RFC if applicable].
Assign agents based on the work involved.
New tasks land in Backlog: | Task ID | Priority | Description | Requested By |
```

**Every implementation task on the board MUST have a paired test task.** When Atlas creates board tasks, each `[Implement X]` task must be accompanied by a `[Write tests for X]` task. Neither task is Done until both are complete.

## Step 5: Design (if UI is involved)

If the feature has a user-facing component, invoke Pixel:
```
Design the [screens/components] for [feature].
Reference: docs/artifacts/brd/{Task-Id}-BRD-{Title}.md for user stories.
Target platforms: [platforms].
```
Save to `docs/artifacts/design-spec/{Task-Id}-Design Spec-{Title}.md`. **Get @Zeyad approval.**

## Step 6: Testing Requirements (mandatory — no exceptions)

Every feature, regardless of size, must include tests written alongside the implementation. This is not optional.

### What must be covered

- **Unit tests**: every new use case, ViewModel/InputHandler, service method, and utility function
- **Integration tests**: every new API endpoint or repository method (real DB via Testcontainers where applicable)
- **Edge cases**: empty states, error paths, invalid inputs — not just the happy path

### Placement

Tests live next to (or in the designated test directory for) the code they cover, following the project's existing test structure. A PR that adds `FooUseCase.kt` without a corresponding `FooUseCaseTest.kt` (or equivalent) is **not ready for review**.

### Coverage targets (per coding standards)

- 80%+ on shared/domain/service/use-case code
- 60%+ overall

## Step 7: Quality Gate (must pass before PR — hard stop)

Before raising a PR or marking any task Done, the implementing agent MUST run and pass a **static-analysis gate** and a **test gate**. Both are mandatory. What they are made of depends on the stack — this skill routes work to @Nova (Next.js), @Flux (Fastify), @Pyra (FastAPI) and @Swift (iOS) as readily as to @Kai and @Link, and Gradle commands do not exist on most of those.

### 1. Detect the stack

```bash
ls -la gradlew 2>/dev/null                     && echo "GRADLE_PROJECT"
ls -la Package.swift *.xcodeproj 2>/dev/null   && echo "SWIFT_PROJECT"
ls -la package.json 2>/dev/null                && echo "NODE_PROJECT"
ls -la pyproject.toml requirements.txt 2>/dev/null && echo "PYTHON_PROJECT"
grep -qi "iosArm64\|androidTarget\|wasmJs" settings.gradle.kts build.gradle.kts 2>/dev/null \
    && echo "KMP_MULTIPLATFORM"
```

A repo can match more than one — a KMP monorepo with a Next.js admin app matches both. Run the gate for **every** stack the change touches.

### 2. Run the matching gate

| Stack | Static analysis | Tests |
|---|---|---|
| KMP (multiplatform) | `./gradlew detekt` | `./gradlew testAndroidHostTest iosSimulatorArm64Test` |
| Android / Gradle only | `./gradlew detekt` | `./gradlew testDebugUnitTest` |
| JVM / Spring Boot | `./gradlew detekt` (or `spotbugsMain`) | `./gradlew test` |
| iOS / Swift | `swiftlint lint --strict` | `xcodebuild test -scheme {Scheme} -destination 'platform=iOS Simulator,name=iPhone 15'` |
| Web / Next.js | `npx eslint . && npx tsc --noEmit` | `npx vitest run` (+ `npx playwright test` if the change is user-facing) |
| Node / Fastify | `npx eslint . && npx tsc --noEmit` | `npx vitest run` |
| Python / FastAPI | `ruff check . && mypy src/` | `pytest` |

If the project's actual commands differ from the table (custom scripts, a Makefile, Nx/Turbo targets), use the project's own — read `package.json` scripts, `Makefile`, or the CI workflow in `.github/workflows/pr-checks.yml`, which is the authoritative list of what must pass. Never skip a gate because the table's command is not the project's command.

Static analysis must be clean. If a suppression is truly necessary it carries an inline reason (`// detekt:suppress <RuleName> - <reason>`, `// eslint-disable-next-line <rule> -- <reason>`, `# noqa: <code>  # <reason>`, `// swiftlint:disable:next <rule> - <reason>`). Blanket file-level suppressions are not acceptable.

Tests must be green. Zero failures, zero errors.

### 3. Verify new test files exist

Confirm that for every new source file introduced, a corresponding test file exists. List them explicitly in the PR description.

### 4. Report in the PR description

The PR description must include a "Quality Gate" section naming the **actual commands run** for this project's stack:

```
## Quality Gate
Stack: {detected stack(s)}
- [ ] `{static analysis command}` — PASSED
- [ ] `{test command}` — PASSED (X tests, 0 failures)
- [ ] New test files added:
  - `path/to/FooUseCaseTest.kt`
  - `path/to/BarViewModel.test.ts`
```

If either gate fails, fix the issue and re-run before proceeding. Do not move the board task to Review until this section is complete and green.

## Handoff Reminders

- All docs are saved by type per `@.claude/rules/shared/handoff-protocol.md`: `docs/{doc-type}/{Task-Id}-{Doc Type}-Title.md` (e.g. `docs/artifacts/brd/US-042-BRD-Social Sharing.md`). There is no `docs/by-type/` cross-reference tree — the type folder *is* the index
- Every handoff doc needs @Zeyad approval before the next step
- Engineers should read all existing feature docs before starting (per `@.claude/rules/shared/agent-preamble.md`)
- **No PR without a passing static-analysis gate and a passing test gate** — this is a hard gate, not a suggestion
