# Board Adapter — Platform-Agnostic Board Operations

The board backend is configured per-project in `.claude/settings.json` via the `board_backend` field. All agents and skills MUST use the operations defined here instead of directly reading/writing `board-context.md`. This abstraction allows the agency to work with markdown Kanban, Jira, Linear, Asana, or any other board tool.

## Configuration

```json
// .claude/settings.json
{
  "board_backend": "markdown"
}
```

Supported values: `"markdown"` (default), or any external tool accessible via MCP (e.g., `"jira"`, `"linear"`, `"asana"`). If the field is missing, default to `"markdown"`.

## Board Operations

Every skill that interacts with the board MUST use these abstract operations. The agent reads `board_backend` from `.claude/settings.json` and translates each operation to the appropriate backend.

### Read Operations

| Operation | What it does |
|-----------|-------------|
| `board.read_all()` | Read the full board state (all columns) |
| `board.read_column(column)` | Read tasks in a specific column (Backlog, Ready, In Progress, Review, Done, Blocked) |
| `board.read_task(task_id)` | Read a specific task by ID |
| `board.read_agent_wip(agent)` | Read all In Progress tasks assigned to an agent |
| `board.search(query)` | Search tasks by keyword, assignee, or label |

### Write Operations

| Operation | What it does |
|-----------|-------------|
| `board.move_task(task_id, from_column, to_column)` | Move a task between columns |
| `board.assign_task(task_id, agent)` | Assign or reassign a task to an agent |
| `board.create_task(task)` | Create a new task (with description, priority, assignee, acceptance criteria) |
| `board.update_task(task_id, fields)` | Update task fields (description, priority, labels, etc.) |
| `board.add_comment(task_id, comment)` | Add a comment or note to a task |
| `board.add_blocker(task_id, reason)` | Mark a task as blocked with a reason |
| `board.remove_blocker(task_id)` | Unblock a task |

## Backend Translations

### `"markdown"` (default)

When `board_backend` is `"markdown"`, the board is stored across a **hot file and three archives**:

| File | Holds | Read when |
|---|---|---|
| `board-context.md` | Ready, In Progress, Review, Blocked | Every agent task (preamble step 1), `/pick-up-task`, `/daily-sync` |
| `docs/board/backlog.md` | Backlog | `/replenish`, triage — not on the hot path |
| `docs/board/done-{YYYY}-Q{N}.md` | Done, one file per quarter | `/sprint-report`, `/retro`, release notes |
| `docs/board/decisions-log.md` | Decisions Log | When a prior decision needs checking |

**Why the split.** `board-context.md` is read at the start of *every* agent task. Everything an agent needs to pick up work — what is ready, what is in flight, what is blocked — is in the four live columns. Done, Backlog, and the decisions log are history: valuable, occasionally consulted, and never needed to answer "what should I do next". Keeping them in the hot file taxes every single task with the cost of the whole project's history. In the reference consumer this was 249 KB read per task, of which under 10% was live.

The live file must stay small to stay useful. Two rules keep it that way:

1. **One row per task, no prose.** A row carries the task ID, agent, one-line description, and a link to its artifact (`docs/artifacts/code-review/…`). Review notes, acceptance-criteria walkthroughs, and discussion live in the linked document, never inline in the board.
2. **Done is archived on the transition, not in a later cleanup.** `move_task(..., → Done)` appends to the current quarter's file. The task never sits in a Done column in the hot file.

#### Operation translations

| Operation | Translation |
|-----------|-------------|
| `board.read_all()` | `cat board-context.md` — live columns only. Add the archives explicitly if history is genuinely needed. |
| `board.read_column(column)` | Live column → parse `## {Column}` in `board-context.md`. `Backlog` → `docs/board/backlog.md`. `Done` → the current quarter file, or all `done-*.md` if the caller needs full history. |
| `board.read_task(task_id)` | Find the row in `board-context.md`; if absent, search `docs/board/` (the task is done or still in the backlog). |
| `board.read_agent_wip(agent)` | Parse "In Progress" in `board-context.md`, filter by agent. Never touches the archives. |
| `board.search(query)` | `grep -ri "{query}" board-context.md docs/board/` |
| `board.move_task(...)` | Between live columns → edit `board-context.md` only. `Backlog → Ready` → remove from `docs/board/backlog.md`, add to Ready. `Review → Done` → remove from `board-context.md`, append to `docs/board/done-{current-quarter}.md`, creating that file with a header row if it does not exist. |
| `board.assign_task(...)` | Edit the "Assigned To" field in whichever file holds the task. |
| `board.create_task(...)` | Append to `docs/board/backlog.md` (new work) or to Ready in `board-context.md` (immediately actionable). |
| `board.update_task(...)` | Edit the matching row in whichever file holds the task. |
| `board.add_comment(...)` | Append to the task's artifact document and link it from the row. Do **not** grow the board row. |
| `board.add_blocker(...)` | Move the task to "Blocked" in `board-context.md` with a reason. |
| `board.remove_blocker(...)` | Move back to "In Progress" in `board-context.md`. |

#### File formats

`board-context.md` — the live board:

```markdown
## Ready
## In Progress (WIP limit: 2 per agent)
## Review
## Blocked
```

`docs/board/` — the archives:

```markdown
docs/board/backlog.md          ## Backlog
docs/board/done-2026-Q3.md     ## Done — 2026 Q3
docs/board/decisions-log.md    ## Decisions Log
```

Each column contains a markdown table with columns: Task ID, Description, Assigned To, Priority, Started/Added date.

#### Quarter boundaries

A quarter file is created lazily by the first `→ Done` transition in that quarter. Never backfill or rewrite a closed quarter — an archive that changes after the fact is no longer a record. `docs/board/README.md` indexes the quarter files.

### External Tool (Jira, Linear, Asana, etc.)

When `board_backend` is set to an external tool, translate operations to MCP tool calls. The specific MCP tool names depend on the connected tool:

| Operation | MCP Call Pattern |
|-----------|-----------------|
| `board.read_all()` | Call the tool's "list issues/tasks" endpoint with the project filter |
| `board.read_column(column)` | Call "list issues" filtered by status mapping (see Status Mapping below) |
| `board.read_task(task_id)` | Call "get issue" by ID |
| `board.read_agent_wip(agent)` | Call "list issues" filtered by assignee + status "In Progress" |
| `board.search(query)` | Call the tool's search/JQL/filter endpoint |
| `board.move_task(...)` | Call "transition issue" or "update status" |
| `board.assign_task(...)` | Call "update issue" with assignee field |
| `board.create_task(...)` | Call "create issue" with mapped fields |
| `board.update_task(...)` | Call "update issue" with changed fields |
| `board.add_comment(...)` | Call "add comment" on the issue |
| `board.add_blocker(...)` | Call "update issue" to set blocked flag/status + add comment with reason |
| `board.remove_blocker(...)` | Call "update issue" to clear blocked flag/status |

### Status Mapping

Map the agency's column names to external tool statuses:

| Agency Column | Jira (typical) | Linear (typical) | Asana (typical) |
|---------------|----------------|-------------------|-----------------|
| Backlog | Backlog | Backlog | Not Started |
| Ready | To Do / Selected for Dev | Todo | Upcoming |
| In Progress | In Progress | In Progress | In Progress |
| Review | In Review | In Review | In Review |
| Blocked | Blocked (custom) | Blocked (label) | On Hold |
| Done | Done | Done | Completed |

The exact mapping depends on the project's board configuration. When setting up an external backend, document the status mapping in `docs/guides/board-config.md`.

## Agent Guidelines

0. **Board writes ship inside the PR carrying the change.** Whatever the backend, a `board-context.md` write is committed on the branch that carries the change it describes and merges in that change's PR — never as a board-only PR, never as a commit on `main`. See `@.claude/rules/shared/board-in-pr.md`. (External backends like Jira write through their API, where this doesn't apply; the local mirror still follows the rule.)

1. **Always check `board_backend`** before any board interaction. Read `.claude/settings.json` at the start of any skill that touches the board.

2. **Use operations, not raw access.** Never write `cat board-context.md`, `grep … board-context.md`, or a direct `Edit` of `board-context.md` in a skill. Always name the operation instead. If the backend is markdown, the operation translates to exactly that command — but the skill must not encode the translation, because a skill that hardcodes `cat board-context.md` silently reads an empty board on a Jira-backed project.

   The operation names a skill may use are exactly those in the two tables above:

   - **Read:** `board.read_all()`, `board.read_column(column)`, `board.read_task(task_id)`, `board.read_agent_wip(agent)`, `board.search(query)`
   - **Write:** `board.move_task(task_id, from, to)`, `board.assign_task(task_id, agent)`, `board.create_task(task)`, `board.update_task(task_id, fields)`, `board.add_comment(task_id, comment)`, `board.add_blocker(task_id, reason)`, `board.remove_blocker(task_id)`

   A skill step reads: "`board.read_column('Ready')` — resolve via the backend in `.claude/settings.json`". It does not read: "run `cat board-context.md`".

3. **Handle both backends gracefully.** If an MCP tool is not available for the configured backend, report the error clearly: "Board backend is set to {tool} but the MCP connection is not available. Please check your MCP configuration or switch to markdown."

4. **Keep `board-context.md` as fallback.** Even when using an external tool, `board-context.md` can serve as a local cache or backup. If the external tool is unreachable, the agent may fall back to the last cached state in `board-context.md` and note that it's potentially stale.

5. **Sync after external operations.** When using an external backend, after any write operation, the agent should update `board-context.md` as a local mirror if it exists. This keeps the file useful for quick offline reference.

## Known Limitation — Live State Is Derived, Not Read

The read operations above return what the **merged** board says. On the `markdown` backend that is
not the same as what is actually in flight.

Per `@.claude/rules/shared/board-in-pr.md`, a task's `→ In Progress`, `→ Blocked`, and `→ Review`
transitions are committed on the task's own branch and do not reach `main` until that branch's PR
merges. A checkout of `main` therefore shows an empty or stale In Progress column even while several
agents are mid-task. The merged board is an accurate record of **completed** work (the Done column,
the decisions log, the task inventory); it is not a live view.

**Live state must be derived from open PRs and their branches**, not from the merged file:

```bash
gh pr list --state open --json number,title,headRefName,author
git branch -r --list 'origin/*'
# and, per branch, that branch's own board-context.md
```

Consumers that report live state — `/pick-up-task`'s 2-item WIP check, and `/daily-sync`'s In
Progress count, WIP violations, blockers, and cycle-time alerts — currently read the columns
straight from the merged file and will therefore **under-report in-flight work**. Treat their
In Progress numbers as a lower bound. Reworking those consumers onto the derived source is tracked
in `docs/tech-debt/backlog.md`.

This limitation is specific to the `markdown` backend. External backends (Jira, Linear, Asana) write
through their API immediately, so their reads are live.

## Adding a New Backend

To add support for a new board tool:

1. Configure the MCP connection for the tool (see `docs/guides/tool-integrations.md`)
2. Add the tool name as a valid `board_backend` value
3. Document the status mapping in `docs/guides/board-config.md`
4. Test with `/daily-sync` to verify read operations work
5. Test with `/pick-up-task` to verify write operations work
6. **Audit the skills for raw board access before trusting the new backend.** The adapter handles translation only for skills that actually go through it. Any skill that hardcodes `cat board-context.md` or edits the file directly bypasses the adapter and will read or write the wrong thing:

   ```bash
   grep -rn "board-context\.md" .claude/skills/ | grep -v "board\."
   ```

   Every hit is a skill that must be converted to a named operation from rule 2 before the backend switch is safe. This is the one step that is *not* free — the adapter removes the need to re-implement translation logic per skill, but it cannot rescue a skill that never called it.
