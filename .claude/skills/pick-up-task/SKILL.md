---
name: pick-up-task
description: "Pick up the next available task from the Kanban board. Reads the board through the board adapter, selects the highest-priority Ready task matching the agent's domain, creates a worktree, moves the task to In Progress, loads the feature docs and the coding standard for the task's stack, and begins work. Use when an agent says 'pick up task', 'what should I work on next', 'grab next task', 'start next item', 'pull from board', or 'what's ready for me'."
---

# Pick Up Task from Board

This skill instructs an agent to pull the next available task from the Kanban board and begin working on it. It enforces WIP limits, priority ordering, and the context-loading discipline from the agent preamble.

## Step 1: Check Current WIP

Read the board **through the adapter**, never by reading `board-context.md` directly — `@.claude/rules/shared/board-adapter.md` rule 2 forbids raw file access so the same skill works on a Jira/Linear/Asana backend.

1. Read `board_backend` from `.claude/settings.json` (absent → `markdown`).
2. Run `board.read_agent_wip("@{YourAgent}")` for your current In Progress items.

On `github` the adapter resolves this to `gh issue list --label "agent:@{YourAgent},status:in-progress"`; on `markdown` it parses the `## In Progress` section of `board-context.md` and filters by the `Agent` column; on an external backend it becomes a "list issues by assignee + status" MCP call. Either way, go through the operation — the skill must not know which.

**Accuracy of the count differs by backend, and it matters here.** On `github` the answer is exact: a transition is an API write, so every in-flight task is visible the moment it starts. On `markdown` it is a **lower bound** — `→ In Progress` sits on an unmerged branch, so a worktree cut from `origin/main` cannot see other agents' in-flight work (`@.claude/rules/shared/board-adapter.md` § Known Limitation). On `markdown` only, cross-check `gh pr list --state open` before concluding you are under the limit.

**WIP limit: 2 items per agent.** If you already have 2 items in "In Progress", you CANNOT pick up a new task. Instead:

1. Report your current WIP to the user
2. Identify which in-progress task is closest to completion
3. Suggest finishing or unblocking that task first
4. Stop here — do not proceed to Step 2

## Step 2: Select the Next Task

Run `board.read_column("Ready")` and select a task from the result using this priority order:

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
- Run `board.add_blocker(task_id, reason)` to move it to Blocked with the reason
- Notify @Atlas
- Return to Step 2 and pick the next task

## Step 4: Pull the Task

Move the task from Ready to In Progress via `board.move_task(task_id, "Ready", "In Progress")` and `board.assign_task(task_id, "@{YourAgent}")` (see `@.claude/rules/shared/board-adapter.md`). On the default markdown backend this resolves to editing `board-context.md`; on a Jira/Linear backend it routes through MCP.

The two columns have **different** schemas — you are not moving a row, you are removing one and writing another. Match the target table's headers exactly, or the row misaligns and every later reader parses the wrong column:

```markdown
## Ready

| Task ID | Priority | Description | Assigned To |
|---------|----------|-------------|-------------|
```

```markdown
## In Progress (WIP limit: 2 per agent)

| Task ID | Agent | Description | Started | Cycle Day |
|---------|-------|-------------|---------|-----------|
| T-XXX   | @{YourAgent} | {task description} | YYYY-MM-DD | 1 |
```

`Agent` is the second column in In Progress — that is the field the adapter's "filter In Progress by agent name" reads. `Cycle Day` starts at 1 on the day you pull and is what `/daily-sync` and `/sprint-report` use for the >5-day stale-task alert. `Priority` does not survive the move; it lives in Ready and Backlog only.

Run `/update-board {TASK-ID} → In Progress` inside the worktree from Step 7 rather than editing anything by hand. **On `github`** that is an API write and takes effect immediately. **On `markdown`** it is the **first commit** on your task branch (`@.claude/rules/shared/board-in-pr.md`).

## Step 5: Load Context

Follow the agent preamble's context-loading discipline:

1. **Read feature docs**: Documents are filed by type per `@.claude/rules/shared/handoff-protocol.md`, as `docs/{doc-type}/{Task-Id}-{Doc Type}-Title.md`. Search by task ID and feature name across the type folders:

   ```bash
   grep -ril "{TASK-ID}\|{feature-name}" \
     docs/artifacts/prd/ docs/artifacts/brd/ docs/artifacts/adr/ docs/artifacts/rfc/ docs/artifacts/design-spec/ \
     docs/artifacts/api-contract/ docs/artifacts/incident-notes/ docs/artifacts/post-mortem/ 2>/dev/null
   ```

   Read every hit:
   - PRD (product requirements)
   - BRD (business requirements, user stories, acceptance criteria)
   - ADR (architecture decisions — follow them, don't contradict)
   - RFC (if an RFC exists, your implementation must align with it)
   - Design specs (from @Pixel)
   - Previous incident notes and post-mortems

2. **Read the coding standard for this task's stack — you MUST do this explicitly.**

   The eight language coding standards are **not** auto-loaded. They live in the plugin and are read on demand, precisely so that eight standards for eight stacks don't sit in context on every task. Nothing loads one for you: if you skip this step you implement with no standard at all.

   Use the `Read` tool on the row matching the task's stack (only that row — reading all eight defeats the point):

   | Stack | Read |
   |---|---|
   | Android / Compose | `${CLAUDE_PLUGIN_ROOT}/rules/mobile/android/compose-coding-standards.md` |
   | iOS / SwiftUI | `${CLAUDE_PLUGIN_ROOT}/rules/mobile/ios/swiftui-coding-standards.md` |
   | KMP shared | `${CLAUDE_PLUGIN_ROOT}/rules/mobile/shared/kmp-coding-standards.md` |
   | Ktor server | `${CLAUDE_PLUGIN_ROOT}/rules/backend/kotlin/ktor-server-coding-standards.md` |
   | React / Next.js | `${CLAUDE_PLUGIN_ROOT}/rules/web/react-coding-standards.md` |
   | Node / Fastify | `${CLAUDE_PLUGIN_ROOT}/rules/backend/nodejs/node-coding-standards.md` |
   | Python / FastAPI | `${CLAUDE_PLUGIN_ROOT}/rules/backend/python/python-coding-standards.md` |
   | JVM / Spring Boot | `${CLAUDE_PLUGIN_ROOT}/rules/backend/jvm/jvm-coding-standards.md` |

   If `CLAUDE_PLUGIN_ROOT` is unset — which is the case when working inside the tech-agency repo itself — read the same path under `.claude/rules/` instead. Resolve it once:

   ```bash
   RULES_ROOT="${CLAUDE_PLUGIN_ROOT:-.claude}/rules"
   ls "$RULES_ROOT/mobile" "$RULES_ROOT/backend" "$RULES_ROOT/web"
   ```

   Android and iOS tasks read **two** files: the platform standard above *and* `${CLAUDE_PLUGIN_ROOT}/rules/mobile/shared/kmp-coding-standards.md`, which is the architectural foundation both build on.

   The shared rules (`.claude/rules/shared/*.md`) are already loaded automatically — do not re-read them.

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

1. Create a **git worktree** for the task. All Claude Code work happens in a worktree — never `git checkout -b` in the main checkout, which is an orchestration root and shared with any parallel session (`@.claude/rules/shared/worktree-first.md`).

   Resolve the base first, per `worktree-first.md` § Base Branch Resolution: explicit `--base` → epic integration branch (`epic/{EPIC-ID}-{slug}`) → hotfix release tag → `origin/main`.

   ```bash
   MAIN_REPO="$(git rev-parse --show-toplevel)"

   BASE="main"                                # or the epic integration branch per the resolution order
   BRANCH="{story-id}/{short-description}"
   WORKTREE_DIR="${MAIN_REPO}/../$(basename "$MAIN_REPO")-worktrees/${BRANCH//\//-}"

   git -C "$MAIN_REPO" fetch origin "$BASE"
   git -C "$MAIN_REPO" worktree add --no-track -b "$BRANCH" "$WORKTREE_DIR" "origin/$BASE"
   cd "$WORKTREE_DIR"

   # Verify BEFORE any write. If either check fails, STOP and report.
   pwd                          # must equal $WORKTREE_DIR
   git branch --show-current    # must equal $BRANCH
   ```

   Every later step in this task — the board edit from Step 4, the implementation, the tests, the commits — happens inside `$WORKTREE_DIR`. The PR merges back into `$BASE`.

   If you were spawned into a worktree already (by `/dispatch` or `/dispatch-task` in local fallback mode), skip creation: verify the existing worktree matches this task and continue.

   If you were dispatched into a **cloud environment**, you already have your own clone and there is no worktree to create: `git switch --no-track -c "$BRANCH" "origin/$BASE"`, verify with `git branch --show-current`, and continue. Every later step happens on that branch.

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
   The PR title will include the task ID (e.g., `[US-042] Add email validation`) and the body will list you as the primary author along with any participating agents. Invoking `/create-pr` **is** the push authorization — it runs the pre-push verification gate, pushes the branch, and opens the PR. See `@.claude/rules/shared/shared-standards.md` § Push Policy.
4. Create a handoff using the appropriate template from `@.claude/rules/shared/handoff-protocol.md`
5. Tag the reviewer and @Atlas

If the task is a code change that requires security review (auth, encryption, PII), also tag @Shield per the code review matrix in `shared-standards.md`.

**Note:** `/update-board` should also be used at Step 4 (pulling the task → In Progress) and whenever the task becomes blocked. The board commit travels with the branch so the board state stays in sync with code changes.
