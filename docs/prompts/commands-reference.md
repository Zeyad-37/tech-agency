# Commands Reference

These are the **34 first-party slash commands** shipped by the tech-agency plugin. They are available in every project once the plugin is installed, and they automate the most common multi-step workflows so you don't have to type out full prompts.

The plugin also ships **14 vendored skills** from Google (`/android-*`) and JetBrains (`/kotlin-*`) — 48 skills in total. Those are documented upstream; when to route a task to one is specified in `@.claude/rules/shared/kotlin-agent-skills.md` and in the Android and KMP coding standards. Provenance and licensing: `../../.claude/skills/VENDORED-SKILLS.md`.

> Installing the plugin is not the whole setup. Run `/setup-repo` once per project to bootstrap the shared policy rules, the board, the git hooks, and `.claude/settings.json`. See `../setup-guide.md`.

## Daily Operations

### `/daily-sync`

Runs the daily Kanban sync as Atlas. Reads the board, checks git activity, flags blockers, WIP violations, and stale tasks (>5 days in progress). Produces a status report and updates `board-context.md`.

**When to use:** Daily, or whenever you want to know the current state of work.

**Example triggers:**
- "daily sync"
- "what's the status"
- "how are things going"
- "board status"

---

### `/replenish`

Reviews the backlog, applies RICE prioritization, moves items to Ready, and allocates 15-20% capacity to tech debt. Run by Atlas with input from Morgan.

**When to use:** Weekly, or whenever the Ready column is running low.

**Example triggers:**
- "replenish the board"
- "what should we work on next"
- "review the backlog"
- "fill the board"

---

### `/retro`

Runs a retrospective. Analyzes cycle times, throughput, blockers, and process issues for a feature or time period. Produces action items and saves to `docs/retros/`.

**When to use:** After a major feature ships, or monthly.

**Example triggers:**
- "run retro"
- "retrospective"
- "how did that feature go"
- "what can we improve"

---

## Project Kickoff

### `/new-product`

Full product kickoff chain: Morgan (PRD) → Diana (BRD) → Sage (ADR + system design) → Atlas (board setup). Asks clarifying questions about the product vision, platforms, and constraints before starting. Pauses for your approval at each handoff.

**When to use:** Starting a brand new product from scratch.

**Example triggers:**
- "I want to build a habit tracker app"
- "new product: team management tool for remote teams"
- "kick off a new project"

---

### `/new-feature`

Feature kickoff that adapts to scope. Small features go straight to the engineer. Medium features start with Diana (BRD). Large features/epics require an RFC first. Pauses for approval at each handoff.

**When to use:** Adding a feature to an existing product.

**Example triggers:**
- "add social sharing to the habit tracker"
- "new feature: push notifications"
- "I want to add dark mode"

---

### `/write-prd`

Dispatches Morgan to produce a standalone, industry-standard PRD — problem framing, personas, RICE-scored features, an explicit MVP boundary, measurable success metrics, risks, and launch criteria. Unlike `/new-product`, it does **not** chain into BRD → ADR → board setup: it produces one approved PRD and stops.

**When to use:** you want a PRD without committing to the full planning chain — a new feature on an existing product, a product idea that needs definition first, or backfilling a PRD for work already in flight.

**Example triggers:**
- "write a PRD for offline mode"
- "draft product requirements for the referral program"
- "create a PRD"
- "product spec for X"

---

## Release & Incident Response

### `/release`

Executes the full release checklist: QA sign-off (Apex), security review (Shield), documentation update (Scroll), release notes (Morgan), your go/no-go, then deployment (Sentinel). Each gate must pass before proceeding.

**When to use:** When you're ready to ship a version to production.

**Example triggers:**
- "release v1.2.0"
- "ship it"
- "are we ready to deploy"
- "cut a release"

**Arguments:** Optionally provide the version number: `/release v1.2.0`

---

### `/hotfix`

Emergency hotfix process. Creates a hotfix branch from the release tag, assigns the minimal fix, coordinates expedited review (1-hour SLA), gets your approval, and deploys. Requires a post-mortem within 24 hours.

**When to use:** Critical bug in production that can't wait for the next release.

**Example triggers:**
- "critical bug: login is broken on Android"
- "production is crashing"
- "P0: users can't complete checkout"
- "hotfix needed"

---

### `/investigate-crash`

Crash spike investigation protocol. Analyzes recent commits against crash data, identifies the culprit commit, suggests a targeted fix and rollback candidate, then produces a structured post-mortem saved to `.claude/post-mortems/`.

**When to use:** Crashlytics alert, sudden crash spike, or app stability issues.

**Example triggers:**
- "crash spike on Android profile screen"
- "Crashlytics shows 5% crash rate"
- "app is crashing after the last deploy"
- "triage this crash"

---

### `/investigate-bug`

Functional bug investigation protocol. Analyzes expected vs actual behavior, traces the issue through recent commits and feature specs, identifies the root cause, and produces a bug report with fix plan. For severe bugs (P0/P1), also generates a post-mortem.

**When to use:** App behaves incorrectly but doesn't crash — wrong output, missing data, broken feature, regression in behavior.

**Example triggers:**
- "the search results are showing wrong items"
- "users can't complete checkout since last deploy"
- "this feature doesn't match the spec"
- "investigate this bug"

---

### `/postmortem`

Structured post-mortem using the **5 Whys** root cause analysis methodology. Goes beyond the immediate technical root cause to uncover the systemic failures that allowed the issue to be introduced AND escape every quality gate to reach production. Traces two parallel chains: (A) how the issue was introduced, and (B) how it escaped unit tests, integration tests, code review, CI/lint, QA, staging/canary, and monitoring. Produces a post-mortem document saved to `.claude/post-mortems/` and creates prevention board tasks for every gap identified.

**When to use:** After completing an `/investigate-crash` or `/investigate-bug` session, when a recurring incident is detected, for near-misses caught in staging, or whenever a deep root cause analysis is needed.

**Example triggers:**
- "write a postmortem"
- "5 whys analysis"
- "root cause analysis"
- "why did this reach production"
- "postmortem for the crash investigation"

---

### `/pick-up-task`

Agent task pickup protocol. Reads the Kanban board, selects the highest-priority Ready task matching the agent's domain, validates it has acceptance criteria and unblocked dependencies, moves it to In Progress, loads all feature context, and presents a work plan before beginning implementation.

**When to use:** An agent has capacity and needs to start the next piece of work from the board.

**Example triggers:**
- "pick up next task"
- "what should I work on next"
- "grab next item from the board"
- "start next task"

---

## Productivity

### `/kick-off`

Starts the day's work in one command. Chains three workflows: runs a daily sync (board status, blockers, stale tasks), replenishes the Ready column if it's running low, then picks up the next task matching the agent's domain. Gets an agent from zero to productive in a single step.

**When to use:** At the start of a work session, or whenever an agent needs to get going.

**Example triggers:**
- "kick off"
- "start work"
- "start the day"
- "morning sync"
- "let's go"

---

### `/code-review`

Performs a structured, multi-dimensional code review on a PR or branch. Checks architecture alignment (ADR compliance, layer violations), coding standards compliance, test coverage adequacy, security (lightweight scan), and acceptance criteria verification. Produces a scored verdict: APPROVED, CHANGES REQUESTED, or BLOCKED.

**When to use:** Before merging any PR, or when an agent completes a task and needs peer review.

**Example triggers:**
- "review this PR"
- "code review"
- "is this ready to merge"
- "check this branch"

---

### `/capture-screenshots`

Captures before/after screenshots for PRs with UI changes. Detects the project's platform(s) (Android/iOS/Web), switches to the base branch to capture "before" screenshots, switches back to capture "after" screenshots, and generates a comparison table for the PR description.

Supports three screenshot tools:
- **Android**: Paparazzi (JVM-only, no emulator)
- **iOS**: swift-snapshot-testing (Point-Free)
- **Web**: Playwright visual comparisons

Falls back to manual screenshot instructions when automated tools aren't configured.

**When to use:** Before creating a PR that includes UI changes. Also invoked automatically by `/create-pr` when it detects UI changes and no visual evidence is present.

**Example triggers:**
- "capture screenshots"
- "take before/after screenshots"
- "generate visual diff"
- "screenshot this UI change"

---

### `/lint-changed`

Runs detekt on **only the files the current branch changed**, and diffs the SARIF output against the base branch so the report contains only the violations this branch introduced. A workaround for repos where full-repo detekt does not return clean — hundreds of pre-existing violations and no committed baseline — which otherwise drowns a real finding in noise.

**When to use:** the project's `./gradlew detekt` is red on `main`, and you need to know whether *your* branch made things worse.

**Example triggers:**
- "lint changed"
- "detekt changed files"
- "lint diff"
- "check my changes for lint issues"

---

### `/health-check`

Runs a comprehensive project health audit. Checks lint/static analysis, force-unwraps, TODO hygiene, test suite health and coverage, dependency vulnerabilities, board hygiene (stale tasks, WIP violations), documentation staleness, feature flag cleanup, and CI/hook installation. Produces a letter-grade health report with prioritized action items.

**When to use:** Weekly, before a release, or when the codebase feels like it's drifting.

**Example triggers:**
- "health check"
- "project health"
- "audit the project"
- "how healthy is the codebase"
- "run diagnostics"

---

### `/onboard-agent`

Fast-tracks an agent onto a feature they haven't worked on before. Loads all feature documentation (PRD, BRD, ADR, RFC, design specs, incidents), reviews recent git history and open branches, checks board state for related tasks, identifies key contacts from git blame, and produces a comprehensive onboarding briefing.

**When to use:** When an agent is new to a feature, picking up someone else's work, or doing a cross-functional review.

**Example triggers:**
- "onboard me to this feature"
- "catch me up on user-auth"
- "get up to speed"
- "what do I need to know about checkout"

---

### `/extract-library`

Extracts a module from an app into a standalone, published KMP library. Covers the full arc: scoping the library seam (engine vs app integration layer), scaffolding the standalone repo with samples, package rename, Maven Central Portal publishing (release tags plus per-push snapshots), swapping the app onto the artifact, and the ongoing dev flow (gated composite build for the inner loop, Renovate for version bumps). Encodes the gotchas learned shipping pagecurl-cmp: AGP parity for composite builds, explicit dependency substitution for KMP, the per-namespace snapshot toggle, Central's multi-hour first-release sync, and JitPack's inability to build iOS klibs.

**When to use:** Promoting in-repo code to its own library, open-sourcing a module, or publishing anything to Maven Central.

**Example triggers:**
- "extract the journal into a standalone lib"
- "promote this module to a library"
- "publish this to maven central"
- "open source this module"

---

### `/dependency-upgrade`

Manages the full lifecycle of dependency upgrades: audit current dependencies for vulnerabilities and outdated packages, classify by urgency (P0 critical vuln → P4 Kotlin version upgrade), assess risk for major bumps, execute the upgrade with cross-platform verification (KMP), and document a rollback plan. Handles both individual upgrades and monthly batch updates.

**When to use:** When a vulnerability is reported, dependencies are outdated, or it's time for the monthly dependency maintenance window.

**Example triggers:**
- "upgrade dependencies"
- "check for vulnerabilities"
- "bump Kotlin version"
- "monthly dependency update"
- "security patch needed"

---

### `/rfc`

Writes a structured Request for Comments (RFC) for large features or significant technical changes. Produces a comprehensive proposal with goal, background, proposed plan (architecture, implementation steps, data model, API changes, feature flags), alternatives considered, open questions, security considerations, testing strategy, migration plan, estimated scope, and rollback plan. Required per `shared-standards.md` for any epic or large user story spanning multiple tasks or modules.

**When to use:** Before implementing a feature that spans multiple modules, introduces a new architectural pattern, requires data model changes, or is estimated at >2 weeks of work.

**Example triggers:**
- "write an RFC"
- "technical proposal for payments"
- "design doc for the new feature"
- "request for comments"
- "this feature needs upfront design"

---

### `/sprint-report`

Generates a quantitative sprint or time-period report. Gathers data from the board, git log, health reports, and post-mortems to compute throughput (stories completed, commits), cycle times (median, p90, max for lead/work/review/block time), agent utilization, and quality signals (reviews, incidents, hotfixes). Compares against the previous period to show trends. Flags risks like stale tasks, overloaded agents, and cycle time spikes.

**When to use:** End of sprint, monthly review, or whenever you want a data-driven snapshot of team performance.

**Example triggers:**
- "sprint report"
- "how did we do this sprint"
- "team metrics"
- "show me throughput"
- "performance report for last 2 weeks"

---

### `/tech-task`

Kicks off a technical or infrastructure task that isn't a product feature. Skips the product discovery chain (no Morgan/Diana) and routes directly to the appropriate engineer(s) via Sage. For small tasks, goes straight to the owning agent. For medium tasks, Sage evaluates whether an ADR is needed. For large tasks, requires an RFC first.

Covers: tooling improvements, CI/CD changes, refactoring, design system creation, tech debt cleanup, developer experience work, infrastructure setup, and any engineering initiative that doesn't start from a user story.

**When to use:** Any engineering work that doesn't have a product feature driving it.

**Example triggers:**
- "improve the git hooks"
- "create a reusable design system"
- "refactor the authentication module"
- "set up monitoring dashboards"
- "clean up tech debt in the data layer"
- "upgrade to Kotlin 2.1"
- "add screenshot tests to the CI pipeline"

---

## Parallel Execution

### `/dispatch`

Dispatches one or more tasks to run in parallel using git worktrees. Each task gets its own isolated worktree and branch so agents don't interfere with each other's work. Handles the full lifecycle: parse the task list, resolve the base branch per task, create worktrees with proper branch naming, hand off to the assigned agent, and track progress. After work is complete, the agent pushes and creates a PR. Worktrees are cleaned up after merge.

**Base branch resolution (per task):** the branch a worktree cuts off from is also the branch its PR merges into. Resolved in order: explicit `--base <branch>` (or saying "branch off X") → epic integration branch (`epic/{EPIC-ID}-{slug}`, confirmed with you if inferred) → hotfix release tag → `main`. Different tasks in one multi-dispatch can have different bases. See `.claude/rules/shared/worktree-first.md` § Base Branch Resolution.

**When to use:** When you have multiple independent tasks that can be worked on simultaneously — e.g., two features on different modules, a backend task and a frontend task, or any set of tasks that don't share files.

**Example triggers:**
- "dispatch these tasks in parallel"
- "work on these at the same time"
- "run these tasks simultaneously"
- "parallel execution: US-042 and US-043"
- "dispatch @Kai the checkout screen, branch off the epic branch"

**Arguments:** Provide the task list — either task IDs from the board or inline descriptions with assigned agents. Optionally `--base <branch>` to branch off (and PR back into) an epic integration branch instead of `main`.

---

### `/dispatch-task`

Meta-skill that combines upfront planning with parallel worktree execution — effectively `/tech-task` (or `/new-feature`, `/investigate-bug`, `/investigate-crash`) followed by `/dispatch`. **Phase 1** runs the full planning chain for the given task type in the main repo — docs (RFC/BRD/ADR/triage report), board tasks, agent routing — and stops for explicit @Zeyad approval. **Phase 2** creates one worktree per implementation task off the approved base branch and hands off to each agent in parallel, same mechanics as `/dispatch`.

**When to use:** When a piece of work needs both planning AND parallel implementation. Use `/dispatch` instead when planning is already done, and the plain planning skills (`/tech-task`, `/new-feature`, …) when the implementation is sequential.

**Example triggers:**
- "/dispatch-task --type tech-task 'migrate the design system to tokens'"
- "dispatch a new feature"
- "plan then dispatch"
- "plan this and parallelize the implementation"

**Arguments:** `--type <new-feature | tech-task | investigate-bug | investigate-crash>` (inferred from the description if omitted), optionally `--base <branch>` for epic work, and the task description.

---

## Board Management

### `/update-board`

Updates the Kanban board when a task changes status and commits the board change on the current branch. This ensures the board state is always part of the branch history — when the PR merges, the board update merges with the code.

Supports all lifecycle transitions: Ready → In Progress, In Progress → Blocked, Blocked → In Progress, In Progress → Review, Review → Done. Infers the task ID from the branch name or recent commits if not provided.

**When to use:** Every time a task changes status — picking up a task, getting blocked, sending to review, or completing work. Other skills (`/pick-up-task`, `/kick-off`, `/tech-task`, `/code-review`, `/dispatch`) invoke this automatically, but you can also call it directly.

**Example triggers:**
- "update board"
- "move task to review"
- "mark task done"
- "task is blocked"
- "commit board change"

**Arguments:** Optionally provide the task ID and target column: `/update-board US-042 → Review`

---

### `/create-pr`

Creates a pull request with a standardized format. The PR title includes the task ID (e.g., `[US-042] Add email validation`), and the body lists the primary authoring agent and all participating agents, a summary of changes, related docs, a test plan, and a review checklist. Suggests reviewers based on the code review matrix. The PR base is resolved dynamically (Pre-flight 0): `--base <branch>` if passed, else auto-detected (an `epic/*` integration branch the current branch was cut from, confirmed with you), else `main` — and the branch is rebased onto that base before the PR opens.

**When to use:** After an agent finishes a task and the board has been updated to Review. Other skills (`/pick-up-task`, `/kick-off`, `/tech-task`, `/dispatch`) invoke this automatically, but you can also call it directly.

**Example triggers:**
- "create PR"
- "open a pull request"
- "submit PR for this branch"
- "push and create PR"
- "ready for review"

**Arguments:** None required — infers task ID, branch, and agents from the current context. Optionally `--base <branch>` to target an epic integration branch instead of `main` (dispatched agents receive this from `/dispatch` / `/dispatch-task`).

---

## End-to-End Delivery

### `/ship-it`

End-to-end feature delivery in one command, as a **pure composition** of the agency's skills — it re-implements nothing. Routes to the appropriate kickoff (`/new-feature`, `/tech-task`, `/investigate-bug`, or `/investigate-crash`) based on intent, drives implementation through to passing tests, updates the board, then hands the ready branch to **`/ship-pr`** for the entire back half: open the PR (`/create-pr`), review and address feedback (`/review-and-address`), and merge. No inline self-review — the code review happens downstream inside `/review-and-address` against the open PR.

**Human gates kept:** after the kickoff plan, before code is written; and the push-approval gate (inside `/ship-pr`) before the PR is opened.

**Flags:**
- `--auto-merge` — forwarded through `/ship-pr` to `/review-and-address`; merges the PR once all quality gates are green. Without it, the run stops at the merge gate.

**When to use:** Any time you'd otherwise type `/new-feature`, work through it, then manually open and close out the PR.

**Example triggers:**
- "ship it: add dark mode toggle to settings"
- "ship a feature for offline mode"
- "end to end this bug fix"
- "take this all the way and merge it" (implies `--auto-merge`)

**Arguments:** Free-text description, optionally prefixed with `feature:` / `tech-task:` / `bug:` to skip the work-type prompt. Optional `--auto-merge`.

---

### `/ship-pr`

The back two-thirds of `/ship-it` for an **already-implemented branch** — code committed, no PR yet. A thin composition that opens the PR via `/create-pr`, then reviews and addresses all feedback via `/review-and-address`, merging when `--auto-merge` is passed and all gates pass. This is `/ship-it` without the kickoff/implement front end.

Preflight guards: refuses if you're on the default branch, if there are no commits ahead of `main`, or if a PR already exists for the branch (in which case it points you to `/review-and-address`).

**Human gate kept:** the push-approval gate before `/create-pr` opens the PR.

**Flags:**
- `--auto-merge` — forwarded to `/review-and-address`; merges once all quality gates are green. Without it, stops at the merge gate.

**When to use:** The code is done and committed on a branch, and you want it opened, reviewed, addressed, and (optionally) merged in one command.

**Example triggers:**
- "ship pr"
- "take this branch to merge"
- "PR this and review it"
- "open and close this PR with auto-merge" (implies `--auto-merge`)

**Arguments:** None required (infers branch/task). Optional `--auto-merge`.

---

### `/review-and-address`

Close out an **existing** PR in two clean-context phases: **Phase 1** runs `/code-review` and posts the verdict to the PR; **Phase 2** runs `/address-feedback` to resolve every comment and failing check. Between them it waits (background poll, zero idle turns) for Copilot's review — an **optional gate**: it first probes whether Copilot is actually available for the repo (request pending, or has ever reviewed there) and silently skips the wait when it isn't, reserving the halt for a review that is genuinely still in flight. It does **not** request Copilot; `/create-pr` is the single Copilot requester at PR-open time. Each phase starts from a clean context so neither the review nor the fix work is biased by the current session.

**Flags:**
- `--auto-merge` — passed through to Phase 2; merges once everything is green and resolved. Without it, stops at the merge gate.

**When to use:** A PR already exists and you want it reviewed and driven to mergeable in one command. (To go from a ready branch → PR → merged, use `/ship-pr`; from nothing → implemented → merged, use `/ship-it`.)

**Example triggers:**
- "review and address"
- "close out this PR"
- "land this PR" (implies `--auto-merge`)
- "review then fix PR #123"

**Arguments:** Optional PR number (defaults to the current branch's PR). Optional `--auto-merge`.

---

### `/address-feedback`

Back half of the delivery loop. After external review is in (Copilot, human reviewers, CI results), this skill fetches every unresolved review comment, failing check, and `CHANGES_REQUESTED` review verdict; deduplicates overlapping findings; classifies them as REQUIRED vs RECOMMENDED; applies fixes (small recommendations inline, large ones filed as tech debt); pushes; re-watches checks until green; and stops at the merge gate.

Pairs with `/ship-it` — you don't have to babysit the PR while review is pending; come back to it when feedback is in.

**Flags:**
- `--auto-merge` — merges automatically once everything is green and resolved. Without the flag, stops at a final approval gate ("Merge now? y/n").

**When to use:** After `/ship-it` (or any PR creation), once review feedback and CI results are in.

**Example triggers:**
- "address feedback"
- "address PR feedback"
- "resolve PR #123"
- "finish PR and merge it" (implies `--auto-merge`)

**Arguments:** Optional PR number (defaults to the current branch's PR). Optional `--auto-merge`.

---

## Setup & Configuration

### `/setup-repo`

Sets up a repository with the full Tech Agency configuration. Works for both new and existing projects — auto-detects the project mode, audits what's already in place, and only installs the missing pieces.

**For new projects:** Scaffolds the full project structure from scratch — Git init, directory layout, all agency rules/skills, git hooks, CI/CD pipelines, branch protection, initial commit, and optional GitHub repo creation.

**For existing projects:** Audits the current setup against the full Tech Agency configuration, reports what's present and what's missing, then gap-fills only the missing components (rules, skills, hooks, CI workflows, docs) without overwriting anything already in place.

It also writes the `extraKnownMarketplaces` and `enabledPlugins` entries into `.claude/settings.json`, which is how the plugin reaches **cloud** Claude Code sessions — those have no `/plugin` command, so committed settings are the only lever. See `../setup-guide.md` § Cloud sessions for the caveat that a first-time install may still be needed.

**When to use:** Setting up a brand new project, or onboarding an existing codebase onto the Tech Agency framework.

**Example triggers:**
- "set up this project with tech agency"
- "scaffold a new KMP project"
- "add tech agency to my existing repo"
- "initialize the agency setup"

---

### `/audit-memory`

Audits Claude Code's auto-memory store for stale, duplicate, or wrong entries. Auto-memory persists user preferences and project context across sessions — over time it drifts (file paths change, feedback rules get superseded, project facts go stale). Run this periodically to keep it accurate.

The skill enumerates every memory file, evaluates each for truth/usefulness/specificity/uniqueness, proposes per-memory verdicts (KEEP / DELETE / MERGE / EDIT), waits for approval per change, then applies. Stamps `.claude/.last-memory-audit` on completion — the SessionStart hook reads this and stays quiet for 30 days.

**When to use:** every ~30 days (SessionStart hook reminds when overdue), after a major refactor that invalidates project memories, or when you notice a feedback memory being consistently overridden in-session (suggests it's wrongly framed).

**Example triggers:**
- "audit memory"
- "check memory"
- "review memories"
- "clean up memory"
- (or just respond to the "Memory audit overdue" reminder at session start)

---

### `/sync-rule`

Mirrors edits to `.claude/rules/` between a consumer project and the canonical tech-agency repo, in either direction. The tech-agency repo owns the rule files; `/setup-repo` copies the shared policy rules into each consumer project, and a consumer may edit its copy in place when something project-specific comes up. Without explicit syncing the two drift, and the next `/setup-repo` or plugin update silently reintroduces the old text.

**When to use:** immediately after editing any file under `.claude/rules/` in either repo.

**Example triggers:**
- "sync rule"
- "mirror rule"
- "sync to tech-agency"
- "sync from tech-agency"
- "apply rule change to both repos"

---

## Quick Reference

| Command | What it does | How often |
|---------|-------------|-----------|
| `/daily-sync` | Board status, blockers, WIP check | Daily |
| `/replenish` | Prioritize and fill the Ready column | Weekly |
| `/retro` | Retrospective with cycle time analysis | Per feature / monthly |
| `/new-product` | Full kickoff: PRD → BRD → ADR → Board | Per product |
| `/new-feature` | Feature kickoff, adapts to scope | Per feature |
| `/write-prd` | Standalone PRD from Morgan — no chain into BRD/ADR/board | Per feature / idea |
| `/release` | Full release checklist and deploy | Per release |
| `/hotfix` | Emergency fix pipeline | As needed |
| `/investigate-crash` | Crash triage and post-mortem | As needed |
| `/investigate-bug` | Functional bug investigation and fix plan | As needed |
| `/postmortem` | 5 Whys root cause analysis and prevention tasks | After investigations |
| `/pick-up-task` | Pull next task from board and begin work | As needed |
| `/kick-off` | Daily sync + replenish + pick up task | Daily |
| `/code-review` | Structured code review with verdict | Per PR |
| `/capture-screenshots` | Before/after screenshots for UI changes | Per UI PR |
| `/lint-changed` | Detekt on changed files only, SARIF-diffed against base | Per PR on a noisy repo |
| `/health-check` | Project health audit with action items | Weekly / pre-release |
| `/onboard-agent` | Fast-track agent onto a feature | As needed |
| `/dependency-upgrade` | Audit, upgrade, and verify dependencies | Monthly / as needed |
| `/extract-library` | Extract a module into a standalone published KMP library | Per extraction |
| `/rfc` | Write an RFC for large features | Per epic / large feature |
| `/sprint-report` | Sprint metrics, throughput, cycle times, trends | Per sprint / monthly |
| `/tech-task` | Technical/infrastructure task kickoff | As needed |
| `/dispatch` | Dispatch parallel tasks via git worktrees (dynamic base: `--base` / epic branch / main) | As needed |
| `/dispatch-task` | Plan (tech-task/new-feature/bug/crash chain) then dispatch to parallel worktrees | As needed |
| `/update-board` | Update board status and commit on branch | Per transition |
| `/create-pr` | Create standardized PR with task ID and agents | Per task |
| `/ship-it` | End-to-end: kickoff → implement → `/ship-pr` (PR → review → merge); `--auto-merge` flag | Per task |
| `/ship-pr` | Ready branch → PR → review-and-address → merge; `--auto-merge` flag | Per ready branch |
| `/review-and-address` | Existing PR → `/code-review` → `/address-feedback`; `--auto-merge` flag | Per PR close-out |
| `/address-feedback` | Resolve all PR comments + checks; `--auto-merge` flag | Per PR review cycle |
| `/setup-repo` | Set up repo with Tech Agency (new or existing) | Per project — **required after install** |
| `/sync-rule` | Mirror `.claude/rules/` edits between consumer and tech-agency | After any rule edit |
| `/audit-memory` | Audit Claude Code's auto-memory for stale/duplicate entries | Every 30 days |

All 34 first-party commands are listed above.
