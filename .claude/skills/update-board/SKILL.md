---
name: update-board
description: "Update the Kanban board when a task changes status and commit the board change so it's included in the branch history. Supports all lifecycle transitions: picked up (→ In Progress), blocked (→ Blocked), review (→ Review), and done (→ Done). Use when the user says 'update board', 'move task', 'mark task done', 'task is blocked', 'send to review', 'complete task', 'finish task', 'board update', or 'commit board change'."
---

# Update Board — Task Lifecycle Transitions

This skill updates `board-context.md` when a task changes status and commits the change so the board state is always part of the branch history. This means when a PR merges, the board update merges with it — keeping the board in sync with the code.

**Board edits never get their own PR.** Every transition commits on the branch that carries the change it describes, and lands in that change's PR. Never commit `board-context.md` on `main`, and never open a PR whose only change is the board. Full policy: `@.claude/rules/shared/board-in-pr.md`.

## When to Use

Call `/update-board` at every task lifecycle transition:

| Transition | Column Change | Typical Trigger |
|-----------|---------------|-----------------|
| Task picked up | Ready → In Progress | Agent starts work (`/pick-up-task`, `/kick-off`) |
| Task blocked | In Progress → Blocked | Agent hits a dependency or blocker |
| Task unblocked | Blocked → In Progress | Blocker resolved |
| Task sent to review | In Progress → Review | Agent finishes implementation |
| Task completed | Review → Done | Checks green and merge approved — **before** the merge runs |

`→ Done` is the last commit pushed to the PR branch before `gh pr merge`, so it merges together with the change. It is not written at code-review-approval time (checks may still fail) and never after the merge (that would be a board change outside the PR). If the merge gate is declined, the task stays in Review and no Done commit is made.

## Step 1: Identify the Transition

Determine from the user's request or the current context:

- **Task ID**: Which task is being updated? (e.g., `T-042`, `US-042`)
- **Target column**: Where should the task move to?
- **Agent**: Who is performing the update?
- **Metadata** (varies by transition):
  - **→ In Progress**: Add agent name to "Assigned To", add current date to "Started"
  - **→ Blocked**: Add blocker reason
  - **→ Review**: Add PR link if available
  - **→ Done**: Add completion date, link to output artifact

If the user doesn't specify the task ID, infer it from:
1. The current branch name (e.g., `US-042/login-screen` → `US-042`)
2. The most recent commit's story ID prefix
3. The agent's current WIP items on the board

## Step 2: Update the Board

Use the board adapter operations (see `@.claude/rules/board-adapter.md`):

### Ready → In Progress
```
board.move_task(task_id, "Ready", "In Progress")
board.assign_task(task_id, "@AgentName")
board.update_task(task_id, { started: "YYYY-MM-DD" })
```

### In Progress → Blocked
```
board.add_blocker(task_id, "Reason for blocker")
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
board.add_comment(task_id, "PR: #{pr_number} — ready for review")
```

### Review → Done

Only at the merge gate — checks green and merge approved, immediately before `gh pr merge`:
```
board.move_task(task_id, "Review", "Done")
board.update_task(task_id, { completed: "YYYY-MM-DD", artifact: "PR #{pr_number}" })
```
Push right after committing (see Step 3), then let the pushed commit's required checks go green before merging — the board commit is a new head and re-triggers CI.

## Step 3: Commit the Board Change

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

## Planning-Only Board Edits

Some board edits have no code change to accompany: `/replenish` moving Backlog → Ready, `/new-feature` or `/tech-task` creating tasks, `/retro` filing action items.

- If the planning run produced a document (PRD, BRD, ADR, RFC, retro report), commit the board edit on the **same branch as that document** — both merge in one PR.
- If it produced no document, **leave the board edit uncommitted**. Do not commit it to `main` and do not open a PR for it. Tell the user it's pending, and let the first implementation PR for those tasks carry it: the agent picking up the task commits the pending edit alongside its own `→ In Progress` transition.

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
