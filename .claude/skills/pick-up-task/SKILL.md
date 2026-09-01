---
name: pick-up-task
description: "Pick up the next available task from the Kanban board. Reads board-context.md, selects the highest-priority Ready task matching the agent's domain, moves it to In Progress, reads all relevant feature context, and begins work. Use when an agent says 'pick up task', 'what should I work on next', 'grab next task', 'start next item', 'pull from board', or 'what's ready for me'."
---

# Pick Up Task from Board

This skill instructs an agent to pull the next available task from the Kanban board and begin working on it. It enforces WIP limits, priority ordering, and the context-loading discipline from the agent preamble.

## Step 1: Check Current WIP

Read `board-context.md` and check your current Work In Progress:

```bash
cat board-context.md
```

**WIP limit: 2 items per agent.** If you already have 2 items in "In Progress", you CANNOT pick up a new task. Instead:

1. Report your current WIP to the user
2. Identify which in-progress task is closest to completion
3. Suggest finishing or unblocking that task first
4. Stop here — do not proceed to Step 2

## Step 2: Select the Next Task

From the "Ready" column in `board-context.md`, select a task using this priority order:

1. **P0/P1 bugs or incidents** — always first, regardless of domain
2. **Tasks explicitly assigned to you** — your name appears in the "Assigned To" field
3. **Tasks matching your domain** — pick based on your agent role:

| Agent | Domain Match |
|-------|-------------|
| @Kai | Android, Compose, androidApp module |
| @Swift | iOS, SwiftUI, iosApp module |
| @Link | KMP shared, Ktor server, commonMain, web targets |
| @Nova | React, Next.js, web frontend |
| @Flux | Node.js, Fastify backend |
| @Pyra | Python, FastAPI backend |
| @Forge | JVM, Spring Boot backend |
| @Pixel | Design system, UI/UX, tokens, components |
| @Shield | Security review, auth, encryption, compliance |
| @Apex | Testing, QA, release sign-off |
| @Sentinel | CI/CD, deployment, monitoring |
| @Scroll | Documentation, runbooks, guides |
| @Echo | Support escalation, feature request compilation |
| @Pipeline | Data engineering, dbt, analytics |
| @Neuron | ML pipeline, model training, inference |
| @Sage | Architecture, ADRs, system design, RFCs |
| @Diana | BRDs, user stories, requirements |
| @Morgan | PRDs, roadmap, prioritization |
| @Atlas | Board management, coordination, unblocking |

4. **Highest priority among remaining** — P0 > P1 > P2 > P3
5. **Oldest task first** — if multiple tasks share the same priority, pick the one added earliest

If no tasks in "Ready" match your domain:
- Inform the user that no matching tasks are available
- Suggest running `/replenish` to refill the Ready column
- Stop here

## Step 3: Validate the Task

Before pulling the task, verify it's ready for work:

1. **Acceptance criteria exist** — the task must have clear criteria for "done". If missing, ask @Diana or @Morgan to clarify before starting. Do not guess.
2. **Dependencies are met** — check if the task depends on upstream work that isn't complete yet. If blocked, skip to the next eligible task.
3. **Required artifacts exist** — check if the task references PRDs, BRDs, ADRs, design specs, or API contracts that you need. If missing, request them from the producing agent via @Atlas.

If the task fails validation:
- Add it to the "Blocked" section of `board-context.md` with the reason
- Notify @Atlas
- Return to Step 2 and pick the next task

## Step 4: Pull the Task

Update `board-context.md`:

1. Move the task from "Ready" to "In Progress"
2. Add your agent name to the "Assigned To" field
3. Add the current date to the "Started" field

```markdown
## In Progress

| Task ID | Description | Assigned To | Priority | Started |
|---------|-------------|-------------|----------|---------|
| T-XXX   | {task description} | @{YourAgent} | P{n} | YYYY-MM-DD |
```

## Step 5: Load Context

Follow the agent preamble's context-loading discipline:

1. **Read feature docs**: If this task belongs to a feature, read everything in `docs/artifacts/` (grep by Task ID):
   - PRD (product requirements)
   - BRD (business requirements, user stories, acceptance criteria)
   - ADR (architecture decisions — follow them, don't contradict)
   - RFC (if an RFC exists, your implementation must align with it)
   - Design specs (from @Pixel)
   - Previous incident notes
   - Previous bug reports

2. **Read coding standards**: Load the relevant coding standards for your platform:
   - Android: `@.claude/rules/compose-coding-standards.md`
   - iOS: `@.claude/rules/swiftui-coding-standards.md`
   - KMP: `@.claude/rules/kmp-coding-standards.md`
   - Ktor: `@.claude/rules/ktor-server-coding-standards.md`
   - React: `@.claude/rules/react-coding-standards.md`
   - Node.js: `@.claude/rules/node-coding-standards.md`
   - Python: `@.claude/rules/python-coding-standards.md`
   - JVM/Spring: `@.claude/rules/jvm-coding-standards.md`

3. **Check recent activity**:
   ```bash
   git log --oneline -20
   git log --oneline --since="3 days ago" -- {affected-files-or-dirs}
   ```

4. **Check for related tasks**: Look for tasks in "In Progress" or "Review" that touch the same code area — coordinate to avoid conflicts.

## Step 6: Plan and Announce

Before writing any code, produce a brief work plan:

```markdown
## Task: T-XXX — {description}

### Scope
- What I will change (files, modules, functions)
- What I will NOT change (explicit scope boundaries)

### Approach
- Step-by-step implementation plan
- Key decisions (referencing ADRs/RFCs if applicable)

### Test Plan
- What tests I will write/update
- How I will verify the acceptance criteria

### Estimated Effort
- Small (< 2 hours) / Medium (2-8 hours) / Large (> 8 hours)
```

Present this plan to the user for confirmation before proceeding with implementation.

## Step 7: Begin Work

Once the user confirms the plan:

1. Create a feature branch following the branch strategy. Always branch from the latest resolved base on the remote — `origin/main` by default, or the epic integration branch (`epic/{EPIC-ID}-{slug}`) when the task belongs to an epic (see `.claude/rules/shared/worktree-first.md` § Base Branch Resolution) — never from the currently checked-out branch:
   ```bash
   BASE="main"   # or the epic integration branch per the resolution order
   git fetch origin "$BASE"
   git checkout -b {story-id}/{short-description} "origin/$BASE"
   ```

2. Implement the task following:
   - The relevant coding standards
   - The ADR/RFC decisions for this feature
   - The design specs from @Pixel (if UI work)
   - The acceptance criteria from the BRD

3. Write tests as specified in your test plan

4. Commit after each logical change:
   ```bash
   git commit -m "[{STORY-ID}] @{YourAgent}: {description of what changed and why}"
   ```

## Step 8: Complete and Hand Off

When the task is done:

1. Run `/update-board` to move the task to "Review" and commit the board change on this branch:
   ```
   /update-board {TASK-ID} → Review
   ```
   This ensures the board update is included in the merge commit when the PR lands.
2. Run the full relevant test suite — verify all tests pass
3. Run `/create-pr` to prepare a standardized pull request:
   ```
   /create-pr
   ```
   The PR title will include the task ID (e.g., `[US-042] Add email validation`) and the body will list you as the primary author along with any participating agents. The PR will NOT be pushed until @Zeyad approves.
4. Create a handoff using the appropriate template from `.claude/rules/handoff-protocol.md`
5. Tag the reviewer and @Atlas

If the task is a code change that requires security review (auth, encryption, PII), also tag @Shield per the code review matrix in `shared-standards.md`.

**Note:** `/update-board` should also be used at Step 4 (pulling the task → In Progress) and whenever the task becomes blocked. The board commit travels with the branch so the board state stays in sync with code changes.
