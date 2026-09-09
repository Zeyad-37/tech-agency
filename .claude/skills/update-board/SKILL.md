---
name: update-board
description: "Update the Kanban board when a task changes status and commit the board change so it's included in the branch history. Supports all lifecycle transitions: picked up (→ In Progress), blocked (→ Blocked), review (→ Review), and done (→ Done). Use when the user says 'update board', 'move task', 'mark task done', 'task is blocked', 'send to review', 'complete task', 'finish task', 'board update', or 'commit board change'."
---

# Update Board — Task Lifecycle Transitions

This skill moves a task through its lifecycle transitions. **Read `board_backend` from `.claude/settings.json` first** — the two backends behave differently, and doing the wrong one is silently wrong rather than an error.

**On `github` (default):** a transition is an API write through the adapter. It takes effect immediately, there is no file to commit, and Step 3 is skipped entirely. `→ Done` is not written by this skill at all — `Closes #{issue}` in the PR body does it when the merge lands.

**On `markdown`:** a transition edits `board-context.md`, which is then committed on the branch carrying the change it describes so it lands in that change's PR. Board edits never get their own PR, and never a commit on `main`. Full policy: `@.claude/rules/shared/board-in-pr.md`.

## When to Use

Call `/update-board` at every task lifecycle transition:

| Transition | Column Change | Typical Trigger |
|-----------|---------------|-----------------|
| Task picked up | Ready → In Progress | Agent starts work (`/pick-up-task`, `/kick-off`) |
| Task blocked | In Progress → Blocked | Agent hits a dependency or blocker |
| Task unblocked | Blocked → In Progress | Blocker resolved |
| Task sent to review | In Progress → Review | Agent finishes implementation |
| Task completed | Review → Done | Checks green and merge approved — **before** the merge runs |

**On `github`,** `→ Done` needs no action here: `Closes #{issue}` in the PR body closes the issue when the merge lands, atomically and only if the merge actually happens. Verify the line is present before merging; that is the whole obligation.

**On `markdown`,** `→ Done` is the last commit pushed to the PR branch before `gh pr merge`, so it merges together with the change. It is not written at code-review-approval time (checks may still fail) and never after the merge (that would be a board change outside the PR). If the merge gate is declined, the task stays in Review and no Done commit is made.

## Step 1: Identify the Transition

Determine from the user's request or the current context:

- **Task ID**: Which task is being updated? (e.g., `T-042`, `US-042`)
- **Target column**: Where should the task move to?
- **Agent**: Who is performing the update?
- **Metadata** (varies by transition):
  - **→ In Progress**: agent name in "Agent", today's date in "Started", `1` in "Cycle Day"
  - **→ Blocked**: blocker reason in "Blocker", who/what unblocks it in "Waiting On", today's date in "Blocked Since"
  - **→ Review**: reviewer in "Reviewer", today's date in "Waiting Since"; PR link via `board.add_comment()`
  - **→ Done**: output artifact (PR number) in "Output", today's date in "Completed"

If the user doesn't specify the task ID, infer it from:
1. The current branch name (e.g., `US-042/login-screen` → `US-042`)
2. The most recent commit's story ID prefix
3. The agent's current WIP items on the board

## Step 2: Update the Board

Use the board adapter operations (see `@.claude/rules/shared/board-adapter.md`). Read `board_backend` from `.claude/settings.json` first (absent → `markdown`).

### On `github`

Each transition is one adapter call — swap the `status:` label, and close the issue for Done:

```bash
gh issue edit {n} --remove-label "status:{from}" --add-label "status:{to}"
```

Resolve `{n}` from the Task ID with `board.read_task()` (`gh issue list --search "[{TASK-ID}] in:title"`). When the `project` scope is available, the adapter also moves the Projects v2 `Status` field; when it is not, the labels alone are the board — that is a supported mode, not a failure (`@.claude/rules/shared/board-adapter.md`).

There is no row schema to get right, no placeholder rows, and no conflict handling — skip to Step 4.

### On `markdown`

**Every column has its own schema.** A transition is not a row move — it is a delete from one table and an insert into another, with different columns. Write exactly these headers:

| Column | Schema |
|---|---|
| Backlog | `\| Task ID \| Priority \| Description \| Requested By \|` |
| Ready | `\| Task ID \| Priority \| Description \| Assigned To \|` |
| In Progress | `\| Task ID \| Agent \| Description \| Started \| Cycle Day \|` |
| Review | `\| Task ID \| Agent \| Description \| Reviewer \| Waiting Since \|` |
| Blocked | `\| Task ID \| Agent \| Blocker \| Waiting On \| Blocked Since \|` |
| Done (recent) | `\| Task ID \| Agent \| Description \| Output \| Completed \|` |
| Decisions Log | `\| Date \| Decision \| Decided By \| ADR Ref \|` |

Appending a row shaped for the wrong column silently misaligns the table: a Ready-shaped row appended to In Progress puts the priority where the agent name belongs, and every consumer that filters In Progress by agent then reads the wrong field.

When a column is left with no rows, keep the placeholder row `| — | — | — | — |` (matching the column's arity) so the table stays valid markdown.

### Ready → In Progress
```
board.move_task(task_id, "Ready", "In Progress")
board.assign_task(task_id, "@AgentName")
board.update_task(task_id, { started: "YYYY-MM-DD", cycle_day: 1 })
```
`Priority` does not carry over — it exists in Backlog and Ready only. `Cycle Day` starts at 1 and is what `/daily-sync` and `/sprint-report` read for the >5-day stale-task alert.

### In Progress → Blocked
```
board.add_blocker(task_id, "Reason for blocker")
board.update_task(task_id, { waiting_on: "@Agent or external dependency", blocked_since: "YYYY-MM-DD" })
```
Also notify @Atlas:
```
@Atlas — Task {task_id} is blocked: {reason}. Needs: {what's needed to unblock}.
```

### Blocked → In Progress
```
board.remove_blocker(task_id)
```

### In Progress → Review
```
board.move_task(task_id, "In Progress", "Review")
board.update_task(task_id, { reviewer: "@Reviewer", waiting_since: "YYYY-MM-DD" })
board.add_comment(task_id, "PR: #{pr_number} — ready for review")
```

### Review → Done

**On `github`: do nothing.** `Closes #{issue}` in the PR body performs this transition when the merge lands. If that line is missing, add it to the PR body (`gh pr edit {pr} --body …`) rather than closing the issue by hand — closing it manually decouples the board from the merge, which is exactly the failure this design avoids.

**On `markdown`:** only at the merge gate — checks green and merge approved, immediately before `gh pr merge`:
```
board.move_task(task_id, "Review", "Done")
board.update_task(task_id, { output: "PR #{pr_number}", completed: "YYYY-MM-DD" })
```
This touches **two** files: the row leaves `board-context.md` and is appended to `docs/board/done-{YYYY}-Q{N}.md` (created on the quarter's first completion). Stage both in the same commit — a Done row that lands without leaving the live board double-counts the task. See `@.claude/rules/shared/board-adapter.md`.

Push right after committing (see Step 3), then let the pushed commit's required checks go green before merging — the board commit is a new head and re-triggers CI.

**If that re-triggered run fails**, the Done commit is on the branch while the PR is still open — the exact state this design exists to prevent. Undo it:

1. `git reset --hard HEAD~1` (the Done commit is the branch tip) then `git push --force-with-lease`.
2. Move the task back to Review.
3. Hand the failure back to `/address-feedback` Step 3 as new feedback.

Bounded by the same **3-iteration cap** as `/address-feedback` Step 7c — on the third failed run, stop and surface it to the user instead of looping again.

## Step 3: Commit the Board Change (`markdown` only)

**On `github` there is nothing to commit** — the transition is already live. Skip to Step 4.

After updating `board-context.md`, commit it on the current branch so the board state travels with the code:

```bash
git add board-context.md
git commit -m "[{TASK-ID}] @{AgentName}: Update board — {task_id} → {target_column}"
```

Examples:
- `[US-042] @Kai: Update board — US-042 → In Progress`
- `[US-042] @Kai: Update board — US-042 → Review (PR #47)`
- `[US-042] @Kai: Update board — US-042 → Done`
- `[T-003] @Sentinel: Update board — T-003 → Blocked (waiting on Shield review)`

This commit becomes part of the branch history. When the PR merges, the board update merges with it.

**Which branch:** the branch that carries the change this transition describes — the task branch for lifecycle transitions, the planning branch for board edits made during planning (they ride with the PRD/BRD/ADR/RFC/retro doc that produced them). Never `main`.

If the transition is `→ Done` at a merge gate, push immediately after committing so the Done commit is part of the PR before it merges:

```bash
git add board-context.md
git commit -m "[{TASK-ID}] @{AgentName}: Update board — {task_id} → Done"
git push
```

## Planning-Only Board Edits (`markdown` only)

*(On `github`, planning writes go straight to the API. There is no carrier requirement, and the tasks are visible to the next agent the moment they are created — regardless of what is committed.)*

Some board edits have no code change to accompany: `/replenish` moving Backlog → Ready, `/new-feature` or `/tech-task` creating tasks, `/retro` filing action items.

Every planning run saves a document, so **there is always a carrier** and a planning board edit is never left uncommitted:

- Commit the board edit on the **same branch as the document that run produced** — PRD, BRD, ADR, RFC, retro report (`docs/artifacts/retro/`), or replenishment report (`docs/artifacts/replenishment/`). Both merge in one PR.
- If a run looks like it produced no document, that run is incomplete: it must save its report first, then commit the board edit with it. Do **not** leave the edit uncommitted for a later PR to carry — the agent that would carry it works in a worktree cut from its resolved base branch (`origin/main` or an epic integration branch — see `.claude/rules/shared/worktree-first.md` § Base Branch Resolution), so it never sees the pending edit nor the Ready tasks the edit created, and the edit is discarded when the planning worktree is removed.
- Still never commit it to `main`, and never open a board-only PR.

## Step 4: Confirm the Update

Report the transition to the user:

```
Board updated: {task_id} moved to {target_column}
  Agent: @{AgentName}
  Branch: {current_branch}
  Commit: {short_hash}
```

## Multi-Task Updates

A batch commit is only valid when every task in it belongs to the **same** PR — e.g. one branch that closes out several tasks together:

```bash
git add board-context.md
git commit -m "[US-042] @Atlas: Update board — batch: US-042 → Done, US-043 → Done"
```

Do **not** batch transitions for tasks that live on different branches into one commit. Each task's transition belongs in that task's own PR; a cross-branch batch commit has to land somewhere (usually `main`), which is exactly the out-of-PR board change this skill forbids. Update each branch separately.

## Conflict Handling

If `board-context.md` has merge conflicts (common when multiple agents update the board on different branches):

1. The conflict will surface during PR merge — this is expected
2. Resolve by keeping all task movements from both branches (board updates are typically additive)
3. If the same task was moved to different columns on different branches, the later transition wins (e.g., if branch A moved to Review and branch B moved to Done, keep Done)

## Integration with Other Skills

This skill is automatically invoked by:
- `/pick-up-task` — after pulling a task (→ In Progress)
- `/kick-off` — after the task pickup step (→ In Progress)
- `/tech-task` — after creating and assigning a task (→ In Progress)
- `/code-review` — only when the verdict is BLOCKED (→ Blocked). An APPROVED verdict leaves the task in Review; Done comes at the merge gate
- `/address-feedback` — at the merge gate, after approval and before `gh pr merge` (→ Done)
- `/dispatch` — after each dispatched agent completes work (→ Review)

Agents can also invoke it directly at any time by saying "update board" or "move task to [column]".
