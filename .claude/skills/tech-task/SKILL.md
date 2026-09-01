---
name: tech-task
description: "Kick off a technical or infrastructure task that isn't a product feature. Use for tooling improvements, refactoring, CI/CD changes, design system work, tech debt cleanup, dependency upgrades, DevOps tasks, or any engineering initiative that doesn't start with a PRD/BRD. Triggers: 'tech task', 'infrastructure task', 'improve [tooling]', 'set up [infrastructure]', 'refactor [module]', 'create a design system', 'fix the build pipeline', 'clean up tech debt'."
---

# Tech Task Kickoff

This skill handles planning and execution of technical tasks that don't go through the product discovery chain (no Morgan/Diana). These are engineering-driven initiatives: tooling, infrastructure, refactoring, CI/CD, design systems, tech debt, developer experience, etc.

## Step 1: Assess the Task

Ask the user (if not already clear):

- **What** is the task? (description)
- **Why?** (pain point, risk mitigation, developer velocity, quality improvement)
- **Scope?** (small = hours, medium = 1-3 days, large = multi-day/week)
- **Which codebase areas?** (to identify the right agent(s))

Check existing context:
- `docs/tech-debt/backlog.md` — is this already tracked as tech debt?
- Recent ADRs — does an existing decision constrain this work?
- `docs/ci-enforcement-policy.md` — relevant for CI/CD tasks

## Step 2: Create a Branch

Before any implementation, create a working branch. Always branch from the latest `origin/main`, never from the currently checked-out branch:

```bash
git fetch origin main
git checkout -b tech/{short-description} origin/main
# e.g., tech/improve-git-hooks, tech/design-system, tech/refactor-auth-module
```

If the task already has a board story ID, use the standard convention instead:
```bash
git fetch origin main
git checkout -b {STORY-ID}/{short-description} origin/main
```

## Step 3: Route by Scope

### Small task (< 1 day)

Skip ADR. Go straight to the relevant agent:

**Identify the owner by domain:**
| Domain | Agent |
|--------|-------|
| Git hooks, CI/CD, deployment, infrastructure | @Sentinel |
| Design system, tokens, component specs | @Pixel |
| Shared KMP modules, cross-platform tooling | @Link |
| Android tooling, Gradle, Compose infra | @Kai |
| iOS tooling, Xcode config, SwiftUI infra | @Swift |
| Web tooling, bundler, Next.js config | @Nova |
| Node.js backend infra, Fastify plugins | @Flux |
| Python backend infra, FastAPI middleware | @Pyra |
| JVM backend infra, Spring config | @Forge |
| Security hardening, audit tooling | @Shield |
| Test infrastructure, QA tooling | @Apex |
| Documentation tooling, doc generation | @Scroll |
| Data pipeline infra, dbt config | @Pipeline |
| ML infra, model serving setup | @Neuron |
| Architecture decisions, cross-cutting concerns | @Sage |

Create a board task via `board.create_task()`:
```
Task: [description]
Type: Tech Task
Priority: [P1-P3]
Assigned To: @[Agent]
Acceptance Criteria:
  - [specific, testable criteria]
```

Hand off directly:
```
@[Agent] — Implement [task description].
Context: [why this is needed].
Acceptance criteria: [list].
```

### Medium task (1-3 days)

Sage evaluates whether an ADR is needed:
```
@Sage — Evaluate this tech task:
Task: [description]
Goal: [why]
Affected areas: [modules/systems]

Determine:
1. Is an ADR needed? (Yes if: changes architecture, introduces new patterns, affects multiple modules, or has significant trade-offs)
2. Which agent(s) should own this?
3. Any risks or dependencies?
```

**If no ADR needed:** Create board task(s) and assign directly (same as small).

**If ADR needed:** Have Sage write an ADR first:
```
@Sage — Write an ADR for: [task description].
Focus on: approach, alternatives, trade-offs, affected modules.
Save to docs/artifacts/tech-task/{task-name}/adr.md.
```
**Get @Zeyad approval on the ADR.** Then create board tasks.

### Large task (multi-day/week)

This requires an RFC. Tell the assigned agent:
```
This is a significant technical initiative. Write an RFC before starting.
Save to docs/artifacts/tech-task/{task-name}/rfc.md.
Include: Goal, Background, Proposed Plan, Alternatives (2+), Open Questions, Estimated Scope.
```
**Get @Zeyad approval on the RFC.**

Then have Sage break it into tasks:
```
@Sage — Break down the RFC at docs/artifacts/tech-task/{task-name}/rfc.md into implementable tasks.
Assign each to the appropriate agent based on domain.
```

Then invoke Atlas for board setup:
```
@Atlas — Add the following tasks to the board for [task-name]:
[task list from Sage's breakdown]
```

## Step 4: Board Setup

For medium and large tasks, invoke Atlas:
```
@Atlas — Set up board tasks for tech task: [name].
Reference: docs/artifacts/tech-task/{task-name}/[adr or rfc].md
Assign agents based on domain expertise.
Type all tasks as "Tech Task" for tracking.
```

## Step 5: Design System Tasks (Special Case)

If the task involves creating or updating a design system:

1. Start with Pixel for design tokens and component specs:
```
@Pixel — Design the [component/token set] for the design system.
Target platforms: [platforms].
Output: Design tokens (JSON), component specs with variants/states/accessibility.
```
Save to `docs/artifacts/tech-task/{task-name}/design-spec.md`. **Get @Zeyad approval.**

2. Then fan out to platform engineers:
```
@Nova — Implement web design system components per spec.
@Swift — Implement iOS design system components per spec.
@Kai — Implement Android design system components per spec.
@Link — Implement shared KMP design tokens/components per spec.
```

## Step 6: Verification

After implementation:

1. The implementing agent runs relevant tests and verifies acceptance criteria
2. For CI/CD or infrastructure changes: @Sentinel verifies the change works in staging
3. For security-related changes: @Shield reviews
4. For cross-cutting changes: @Sage reviews for architectural consistency
5. For design system changes: @Pixel verifies against the spec

## Artifact Storage

All tech task artifacts go to `docs/artifacts/tech-task/{task-name}/`:
- `rfc.md` — RFC (large tasks only)
- `adr.md` — ADR (if architectural decisions were made)
- `design-spec.md` — Design spec (design system tasks)

## Handoff Reminders

- Every handoff doc needs @Zeyad approval before the next step
- Tag tasks as "Tech Task" on the board so sprint reports can distinguish feature work from infrastructure work
- If the task resolves tech debt, also update `docs/tech-debt/resolved.md` with the resolution
- Engineers should check existing docs and ADRs before starting (per agent-preamble.md)
- Use `/update-board` at every lifecycle transition (→ In Progress, → Blocked, → Review, → Done) to commit the board change on the branch so it merges with the code
- Use `/create-pr` after moving to Review to create a standardized pull request with the task ID in the title and participating agents in the body
