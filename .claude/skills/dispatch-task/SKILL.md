---
name: dispatch-task
description: "Meta-skill that combines upfront planning with parallel worktree execution. Runs the full planning chain for a given task type (new-feature, tech-task, investigate-bug, investigate-crash) in the main repo, requires @Zeyad approval, then dispatches the resulting implementation tasks to agents in isolated git worktrees so they execute in parallel. Use when the user says '/dispatch-task', 'dispatch a new feature', 'dispatch a bug fix', 'dispatch a tech task', 'plan and parallelize', 'plan then dispatch', 'run planning then dispatch', or asks to plan a task type AND parallelize the implementation. Distinct from /dispatch (raw worktree parallelization with no planning) and from /new-feature, /tech-task, /investigate-bug, /investigate-crash (planning chains that do not use worktrees)."
---

# Dispatch Task — Plan Then Parallelize

This skill is a meta-skill that orchestrates two phases:

1. **Phase 1 (Planning)**: Runs the appropriate planning chain (`/new-feature`, `/tech-task`, `/investigate-bug`, or `/investigate-crash`) sequentially in the main working directory. Produces docs (RFC/BRD/ADR/triage report), creates board tasks, and identifies which agents will implement what. **Stops and waits for @Zeyad approval before continuing.**
2. **Phase 2 (Dispatch)**: Once approved, creates a git worktree per implementation task and hands off to each agent in parallel — same mechanics as `/dispatch`.

> **CRITICAL — Phase boundary:** Never create worktrees during Phase 1. Never run planning agents inside worktrees during Phase 1. Planning is sequential, in the main repo. Implementation is parallel, in worktrees. The boundary is the explicit user approval step.

## Invocation

```
/dispatch-task --type <task-type> "<description>"
```

Where `<task-type>` is one of: `new-feature`, `tech-task`, `investigate-bug`, `investigate-crash`.

If `--type` is omitted, infer from the description:
- "fix bug", "investigate bug", "regression", "not working" → `investigate-bug`
- "crash", "crash spike", "crashlytics" → `investigate-crash`
- "new feature", "add feature", "implement [user-facing thing]" → `new-feature`
- "refactor", "tech debt", "tooling", "infrastructure", "CI/CD" → `tech-task`

If type cannot be determined with confidence, ask the user before proceeding.

---

## Phase 1 — Planning (Main Repo, Sequential)

### Step 1: Parse arguments

- Extract `--type` and the task description from the invocation.
- If `--type` is missing, infer from the description per the rules above.
- If still ambiguous, ask the user.

### Step 2: Read board context

- Check `.claude/settings.json` for `board_backend` (per `.claude/rules/board-adapter.md`).
- Run `board.read_all()` to get the current board state.
- Identify any related tasks already on the board so planning can reference or extend them rather than duplicate.

### Step 3: Run the planning chain for the detected type

> Throughout Phase 1, all artifacts (RFC, BRD, ADR, triage report, bug report, post-mortem) are saved to the standardized paths under `docs/{doc-type}/{Task-Id}-{Doc Type}-Title.md` per `.claude/rules/handoff-protocol.md`. Every handoff doc requires explicit @Zeyad approval before the next step in the chain.

#### If type = `new-feature`

Assess size:

- **Small (< 1 day, 1 engineer):** Skip docs. Identify the engineer, create a board task with acceptance criteria, proceed to Phase 2 with a single dispatched task.
- **Medium (2–5 days, 1–2 engineers):** Create a board task. Assign to the appropriate engineer(s). If architectural decisions are involved, invoke `/rfc` first and require @Zeyad approval; otherwise have @Diana write a focused BRD (require @Zeyad approval) and @Sage decide whether an ADR is needed.
- **Large (> 5 days or cross-platform):** Invoke `/rfc` → @Zeyad approval → @Diana BRD → @Zeyad approval → @Sage ADR → @Zeyad approval. Each gate is blocking. Then have @Atlas break down the work into per-agent implementation tasks on the board.

Pair every implementation task with a corresponding test task per `.claude/skills/new-feature/SKILL.md`.

#### If type = `tech-task`

Assess scope and route by domain using this table:

| Domain | Agent |
|--------|-------|
| CI/CD, infrastructure, deployment | @Sentinel |
| Design system, tokens, component library | @Pixel (fan out to @Nova, @Swift, @Kai) |
| KMP shared module | @Link (notify @Swift and @Kai) |
| Android | @Kai |
| iOS | @Swift |
| Web frontend | @Nova |
| Node.js / Fastify backend | @Flux |
| Python / FastAPI backend | @Pyra |
| Spring Boot / JVM backend | @Forge |
| Ktor server | @Link |
| Data pipelines | @Pipeline |
| Security | @Shield |
| Documentation | @Scroll |
| Testing / QA | @Apex |

Then route by size:

- **Small (< 1 day):** Create a board task, assign agent, proceed to Phase 2.
- **Medium (1–3 days):** Ask @Sage whether an ADR is needed. If yes: @Sage writes ADR → @Zeyad approval → create board task. If no: create board task directly.
- **Large (multi-day or cross-cutting):** Invoke `/rfc` → @Zeyad approval → @Sage breaks the RFC into per-agent implementation tasks → @Atlas adds them to the board.

#### If type = `investigate-bug`

- Check if `.claude/bug-context.md` exists; read it if so.
- Otherwise collect from the user: bug ID or description, affected platform, steps to reproduce, expected vs actual behavior.
- Run the bug investigation per `.claude/skills/investigate-bug/SKILL.md`: identify affected modules, classify the root cause, assign to the relevant domain engineer (use the same routing table as `tech-task`), create a `BUG-NNN` task on the board (and a paired test task).
- Output: a triage report including suspected root cause, affected files/modules, proposed assignee, severity (P0/P1/P2/P3), and estimated effort. For P0/P1 bugs, queue a `/postmortem` follow-up.

#### If type = `investigate-crash`

- Check if `.claude/crashlytics-context.md` exists; read it if so.
- Otherwise ask the user for: stack trace, affected platform (iOS/Android), approximate start time, crash count or rate.
- Cross-reference the crash timeline with recent commits:

  ```bash
  git log --oneline -20
  ```

- Identify the culprit commit per `.claude/rules/crash-investigation.md` and explain the connection between the code change and the crash signature.
- Output: a triage report including culprit commit, rollback command (`git revert <hash>`), targeted fix recommendation, and severity (P0: >5% sessions, P1: 1–5%, P2: <1%) per the crash-investigation rules. Plan board tasks for every Prevention Action Point.

### Step 4: Present the plan and STOP

After the planning chain completes, present a structured summary to the user. Do not proceed without explicit approval.

```
## Dispatch Plan

**Task type:** {type}
**Description:** {description}
**Size / scope:** {small | medium | large}

### Docs produced
- {RFC | BRD | ADR | Triage report | Bug report | Post-mortem} — `docs/{doc-type}/{Task-Id}-{Doc Type}-Title.md` (status: approved | pending @Zeyad)

### Board tasks created
| Task ID | Description | Assigned To | Priority |
|---------|-------------|-------------|----------|
| {ID}    | {desc}      | @{Agent}    | P{n}     |

### Triage summary (bugs / crashes only)
- Suspected root cause: {…}
- Culprit commit (if regression / crash): {hash}
- Severity: P{n}
- Recommended action: {targeted fix | rollback}

### Worktrees that will be created in Phase 2
| # | Agent | Branch | Worktree path |
|---|-------|--------|---------------|
| 1 | @{Agent} | {STORY-ID}/{slug} | ../{repo}-worktrees/{slug} |

---

Approve this plan to proceed with implementation? (yes / adjust / cancel)
```

**Do not proceed to Phase 2 until the user explicitly approves.** If a required upstream doc (RFC/BRD/ADR) has not been approved by @Zeyad, do not show the approval prompt — block and report what's still pending.

---

## Phase 2 — Dispatch (Worktrees, Parallel)

This phase mirrors `.claude/skills/dispatch/SKILL.md` mechanics. Run only after Phase 1 approval.

### Step 1: Create all worktrees from the main repo

Create every worktree sequentially from the main working directory before handing off to any agent.

```bash
MAIN_REPO="$(pwd)"

# Ensure main is current
git checkout main
git pull --rebase

# For each implementation task identified in Phase 1:
BRANCH="{STORY-ID}/{short-description}"   # use board task ID
WORKTREE_DIR="${MAIN_REPO}/../$(basename "$MAIN_REPO")-worktrees/${BRANCH//\//-}"
git worktree add -b "$BRANCH" "$WORKTREE_DIR"

# Repeat per task...

git checkout main
git worktree list   # verify
```

If a worktree path or branch already exists, warn the user and skip that worktree. Do not destroy existing work.

### Step 2: Hand off to each agent in parallel

Spawn one agent per implementation task using parallel `Agent` tool invocations (multiple tool calls in a single message). Each prompt MUST start with this exact mandatory preamble:

```
## Mandatory Setup — Run FIRST before any other work

1. cd into your assigned worktree:
   cd {WORKTREE_ABSOLUTE_PATH}

2. Verify your location:
   pwd
   # Expected: {WORKTREE_ABSOLUTE_PATH}

3. Verify the branch:
   git branch --show-current
   # Expected: {BRANCH_NAME}

4. If EITHER check fails, STOP and report the error. Do NOT proceed in the wrong directory.

---

## Your Task

@{Agent} — You are working in an isolated worktree at {WORKTREE_ABSOLUTE_PATH} on branch {BRANCH_NAME}.

Task: {specific implementation task from Phase 1}
Board task ID: {STORY-ID}

Reference docs from Phase 1:
- RFC: {path or "n/a"}
- BRD: {path or "n/a"}
- ADR: {path or "n/a"}
- Design spec: {path or "n/a"}
- Triage / bug report / post-mortem: {path or "n/a"}

Acceptance criteria:
- {criterion 1}
- {criterion 2}

Test plan (mandatory, on this branch):
- Unit tests: {what to cover}
- Integration tests: {what to cover}
- Edge cases: {empty / error / invalid input}

Rules:
1. ALL file reads, writes, and git operations happen in {WORKTREE_ABSOLUTE_PATH} only.
2. Do NOT cd to any other directory (especially not the main repo or another worktree).
3. Follow the coding standards in .claude/rules/ for the relevant stack.
4. Commit format: [{STORY-ID}] @{AgentName}: short description
5. When done: write tests, verify they pass, commit, run /update-board to move to Review on this branch, then run /create-pr.
```

Spawn all agents in a single message with multiple tool calls — do not wait for one to finish before starting the next.

### Step 3: Each agent's completion sequence

Inside its worktree, every dispatched agent must:

1. Verify location: `pwd && git branch --show-current`.
2. Implement the task and write tests on the same branch (per `.claude/rules/agent-preamble.md` and the relevant coding standards).
3. Run the project's quality gates (e.g., `./gradlew detekt`, the relevant test command). Do not raise a PR with failing checks.
4. Stage and commit with the standard format: `[{STORY-ID}] @{AgentName}: description`.
5. Run `/update-board` to move the task to Review and commit the board change on the branch so it merges with the code.
6. Run `/create-pr` to create the standardized PR.

### Step 4: Track active dispatches

Maintain a tracker in the conversation so the user can see all parallel work. Use absolute paths to remove ambiguity.

```
## Active Dispatches
| # | Agent | Branch | Worktree (absolute path) | Status | PR |
|---|-------|--------|--------------------------|--------|-----|
| 1 | @{Agent} | {branch} | {abs-path} | In Progress | — |
```

### Step 5: Cleanup (after PRs are merged)

For each merged dispatch:

```bash
cd "$MAIN_REPO"
git worktree remove "$WORKTREE_DIR"
git branch -d "$BRANCH"   # safe delete; fails if not merged
# If a directory was already removed manually:
git worktree prune
```

Do not clean up before merge — keep the worktree available in case review feedback requires changes.

---

## Error Handling

- **Pending upstream doc:** If Phase 1 produced docs that require @Zeyad approval (RFC, BRD, ADR) and approval has not been granted, block at Step 4 of Phase 1. Do not present the dispatch plan and do not create worktrees.
- **Existing worktree:** If `git worktree add` would collide with an existing branch or directory, warn the user, list the conflict, and skip that single worktree without aborting the rest of the dispatch.
- **User selects "adjust":** Re-run the relevant parts of Phase 1 with the requested changes (e.g., reassign an agent, split a task, drop one task) and present the plan again. Do not create worktrees in between.
- **User selects "cancel":** Roll back any board tasks created during Phase 1 (use `board.update_task()` or move them back to Backlog with a note that the dispatch was cancelled). Do not create any worktrees. Do not delete existing docs — they remain as historical context.
- **Same-file conflicts across dispatched tasks:** If two implementation tasks would touch the same files, flag this in the plan and recommend sequencing rather than parallelizing. Let the user decide.
- **Agent in the wrong directory mid-task:** Follow the troubleshooting steps in `.claude/skills/dispatch/SKILL.md` — stop, verify with `pwd` and `git branch --show-current`, `cd` to the correct worktree, revert any accidental edits in the wrong directory, resume.

---

## When NOT to use this skill

- **Pure planning, no implementation:** A standalone PRD/BRD/RFC/retro doesn't need worktrees. Use `/new-feature`, `/tech-task`, `/rfc`, or `/retro` directly.
- **Pure parallelization, no planning:** If the planning is already done (docs approved, tasks on the board), use `/dispatch` directly to skip Phase 1.
- **Single sequential task:** A task with no parallel siblings doesn't benefit from a worktree. Implement on a normal feature branch.
- **Tasks with hard sequential dependencies:** If task B needs task A's output, do not parallelize — let A finish first, then dispatch B.
- **Trivial fixes:** One-line changes don't need this overhead. Edit the branch directly.
