# Board Adapter — Platform-Agnostic Board Operations

The board backend is configured per-project in `.claude/settings.json` via the `board_backend` field. All agents and skills MUST use the operations defined here instead of directly reading/writing `board-context.md`. This abstraction allows the agency to work with markdown Kanban, Jira, Linear, Asana, or any other board tool.

## Configuration

```json
// .claude/settings.json
{
  "board_backend": "github"
}
```

| Value | Backend | When |
|---|---|---|
| `"github"` | GitHub Issues + Projects v2, driven by `gh` | **Default for new setups.** What `/setup-repo` writes for a repo with a GitHub remote and no existing board |
| `"markdown"` | `board-context.md` + `docs/board/` | Repos with no GitHub remote, repos with an existing markdown board not yet migrated, or an explicit opt-out |
| `"jira"` / `"linear"` / `"asana"` / … | External tool over MCP | Teams already living in that tool |

**If the field is missing, the backend is `"markdown"` — unconditionally.** Do not probe for a
GitHub remote and do not infer anything else. A missing key means the repo was set up before this
field existed, and every such repo keeps its board in `board-context.md`. Resolving it to `github`
would make every board skill read an empty issue list while the real board sits in the file, and
`board.create_task()` would start writing issues next to it.

`/setup-repo` always writes the key explicitly — on new and existing repos alike — so a repo moves to
`github` only by an explicit write: `/setup-repo` on a repo with no board, or `/migrate-board`.

Migrating an existing markdown board to GitHub is what `/migrate-board` does. It never deletes the
markdown files — it freezes them as history.

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

### `"github"` (default for new setups)

Tasks are GitHub Issues. Columns are a Projects v2 `Status` field, mirrored to `status:` labels so
the board still works when Projects v2 is unavailable. Epics are native sub-issues.

#### Column mapping

| Agency column | Projects v2 `Status` | Label | Issue state |
|---|---|---|---|
| Backlog | `Backlog` | `status:backlog` | open |
| Ready | `Ready` | `status:ready` | open |
| In Progress | `In Progress` | `status:in-progress` | open |
| Review | `In Review` | `status:review` | open |
| Blocked | `Blocked` | `status:blocked` | open |
| Done | `Done` | *(none)* | **closed** |

Done is issue-closed, not a label. That is what makes `Closes #N` in a PR body perform the
`→ Done` transition on merge, server-side and atomically.

#### Identity

**The agency Task ID stays the identity; the issue number is incidental.** Branch names
(`T-027/slug`), commit prefixes (`[T-027]`), and artifact filenames (`T-027-RFC-….md`) all key off
the agency ID, and the `commit-msg` hook enforces it. So the issue title is prefixed — `[T-027]
Title` — and `read_task("T-027")` resolves by searching that prefix. Nothing about the commit,
branch, or artifact conventions changes.

**Agency agents are not GitHub accounts.** @Kai, @Swift and @Atlas have no logins. The **human owner
is the GitHub assignee**; the agent is an `agent:{name}` label. `read_agent_wip` and the 2-item WIP
limit query the label, so assignee stays meaningful for notifications.

#### Operation translations

| Operation | Translation |
|-----------|-------------|
| `board.read_all()` | One `gh issue list` per column (see the degradation note on fanning out) |
| `board.read_column(column)` | `gh issue list --label "status:{column}" --json number,title,labels,assignees` — `Done` is `gh issue list --state closed` |
| `board.read_task(task_id)` | `gh issue list --state all --search "{task_id} in:title" --json number,title` piped to `jq -r --arg p "[{task_id}] " 'map(select(.title \| startswith($p))) \| .[0].number // empty'`, then `gh issue view {n} --json …`. The search only narrows candidates; the exact prefix match decides, so `[T-016]` never resolves to `[T-016.4]` |
| `board.read_agent_wip(agent)` | `gh issue list --label "agent:{agent},status:in-progress" --json number,title` |
| `board.search(query)` | `gh issue list --search "{query}" --state all` |
| `board.move_task(id, from, to)` | `gh issue edit {n} --remove-label "status:{from}" --add-label "status:{to}"`; `→ Done` is `gh issue close {n}`; when Projects v2 is available also `gh project item-edit --id {item} --field-id {status} --single-select-option-id {opt}` |
| `board.assign_task(id, agent)` | `gh issue edit {n} --add-assignee {human-owner} --add-label "agent:{agent}"` |
| `board.create_task(task)` | `gh issue create --title "[{task_id}] {desc}" --body {criteria} --label "status:backlog,priority:{p}"` |
| `board.update_task(id, fields)` | `gh issue edit {n} --title/--body/--add-label/--remove-label` |
| `board.add_comment(id, comment)` | `gh issue comment {n} --body "{comment}"` |
| `board.add_blocker(id, reason)` | `gh issue edit {n} --add-label status:blocked --remove-label status:in-progress` + `gh issue comment {n} --body "Blocked: {reason}"` |
| `board.remove_blocker(id)` | `gh issue edit {n} --add-label status:in-progress --remove-label status:blocked` |
| *(epic link)* | `gh issue edit {epic} --add-sub-issue {story}` |
| *(epic read)* | `gh issue view {epic} --json subIssues` |

#### Epics are native sub-issues

An epic (`T-016`) is a parent issue; its stories (`T-016.1 … T-016.10`) are sub-issues, which gives
real hierarchy and automatic progress rollup — mirroring the epic integration branch in
`@.claude/rules/shared/worktree-first.md`. `gh` supports this directly (`--parent`,
`--add-sub-issue`, `--remove-sub-issue`, `--remove-parent`); no GraphQL, and only the `repo` scope,
so **the hierarchy keeps working even when Projects v2 is not available**.

#### Degradation is a supported mode, not a failure

Projects v2 needs a `project` token scope that the `repo` scope does not include:

```bash
gh project list --owner {owner}
# error: your authentication token is missing required scopes [read:project]
```

That scope requires an interactive `gh auth refresh -s project`, which **no agent can perform**, and
a cloud session's token may never carry it. So every operation above is defined on labels first and
Projects v2 second. When the scope is absent, skip the `gh project` half and carry on — do not error,
and do not fall back to the markdown files. Say once that the board is running label-only and that
`gh auth refresh -s project` unlocks the project view.

#### Reads fan out; that is deliberate

`read_all()` is one `gh issue list` per column — about six calls. A single GraphQL query would do it
in one, but the translations above have to stay readable and adaptable by an agent, which matters
more than the round trips at this scale. If rate limits ever bite on a large board, one GraphQL
query behind `read_all()` is the known escape hatch and needs no redesign.

### `"markdown"` (no GitHub remote, or explicit opt-out)

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

| Agency Column | GitHub | Jira (typical) | Linear (typical) | Asana (typical) |
|---------------|--------|----------------|-------------------|-----------------|
| Backlog | `status:backlog` | Backlog | Backlog | Not Started |
| Ready | `status:ready` | To Do / Selected for Dev | Todo | Upcoming |
| In Progress | `status:in-progress` | In Progress | In Progress | In Progress |
| Review | `status:review` | In Review | In Review | In Review |
| Blocked | `status:blocked` | Blocked (custom) | Blocked (label) | On Hold |
| Done | *issue closed* | Done | Done | Completed |

The exact mapping depends on the project's board configuration. When setting up an external backend, document the status mapping in `docs/guides/board-config.md`.

## Agent Guidelines

0. **On the `markdown` backend, board writes ship inside the PR carrying the change.** A `board-context.md` write is committed on the branch that carries the change it describes and merges in that change's PR — never as a board-only PR, never as a commit on `main`. See `@.claude/rules/shared/board-in-pr.md`.

   **On `github` and other API-backed backends this rule does not apply**, because there is no file to commit. Transitions take effect the moment they are made, and `→ Done` is performed by `Closes #N` in the PR body when the PR merges. Put `Closes #{issue}` in every PR that completes a task — that *is* the Done transition, and it is the one thing a PR must carry for the board to stay correct.

1. **Always check `board_backend`** before any board interaction. Read `.claude/settings.json` at the start of any skill that touches the board.

2. **Use operations, not raw access.** Never write `cat board-context.md`, `grep … board-context.md`, or a direct `Edit` of `board-context.md` in a skill. Always name the operation instead. If the backend is markdown, the operation translates to exactly that command — but the skill must not encode the translation, because a skill that hardcodes `cat board-context.md` silently reads an empty board on a Jira-backed project.

   The operation names a skill may use are exactly those in the two tables above:

   - **Read:** `board.read_all()`, `board.read_column(column)`, `board.read_task(task_id)`, `board.read_agent_wip(agent)`, `board.search(query)`
   - **Write:** `board.move_task(task_id, from, to)`, `board.assign_task(task_id, agent)`, `board.create_task(task)`, `board.update_task(task_id, fields)`, `board.add_comment(task_id, comment)`, `board.add_blocker(task_id, reason)`, `board.remove_blocker(task_id)`

   A skill step reads: "`board.read_column('Ready')` — resolve via the backend in `.claude/settings.json`". It does not read: "run `cat board-context.md`".

3. **Handle a missing backend gracefully, but never silently.** On `github`, a missing `project` scope is a *supported degraded mode* — run label-only and say so once. Anything else is an error to report, not to route around: if `gh` is unauthenticated, or an MCP tool for the configured backend is unavailable, say plainly "Board backend is `{backend}` but {reason}" and stop. Do not fall back to reading the markdown files — on a migrated repo they are frozen history, and acting on them would silently operate on a board months out of date.

4. **Never mirror an API-backed board into the repo.** There is no local copy of a `github`, Jira, or Linear board, and no skill should write one. A mirror is stale from the moment it is written, and a stale mirror is worse than none — the next agent cannot tell it apart from a live board. Frozen files left behind by `/migrate-board` carry a banner saying so, and are never read by the adapter.

## Known Limitation — Live State Is Derived, Not Read (`markdown` only)

**This section applies only to the `markdown` backend.** On `github` the read operations are live by
construction: a transition is an API write that takes effect immediately, so there is no gap between
what the board says and what is in flight. The limitation below, and the tech-debt item tracking it,
are retired on the default backend.

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

This limitation is specific to the `markdown` backend. API-backed backends (GitHub, Jira, Linear,
Asana) write through their API immediately, so their reads are live. Migrating to `github` is the
structural fix; `/migrate-board` performs it.

## Adding a New Backend

To add support for a new board tool:

1. Configure access for the tool — an MCP connection (see `docs/guides/tool-integrations.md`), or a CLI already on `PATH` as `github` uses `gh`
2. Add the tool name as a valid `board_backend` value
3. Document the status mapping in `docs/guides/board-config.md`
4. Test with `/daily-sync` to verify read operations work
5. Test with `/pick-up-task` to verify write operations work
6. **Audit the skills for raw board access before trusting the new backend.** The adapter handles translation only for skills that actually go through it. Any skill that hardcodes `cat board-context.md` or edits the file directly bypasses the adapter and will read or write the wrong thing:

   ```bash
   grep -rn "board-context\.md" .claude/skills/ | grep -v "board\."
   ```

   Every hit is a skill that must be converted to a named operation from rule 2 before the backend switch is safe. This is the one step that is *not* free — the adapter removes the need to re-implement translation logic per skill, but it cannot rescue a skill that never called it.
