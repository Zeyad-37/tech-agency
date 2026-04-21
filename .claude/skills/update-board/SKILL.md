---
name: update-board
description: "Update the Kanban board when a task changes status and commit the board change so it's included in the branch history. Supports all lifecycle transitions: picked up (→ In Progress), blocked (→ Blocked), review (→ Review), and done (→ Done). Use when the user says 'update board', 'move task', 'mark task done', 'task is blocked', 'send to review', 'complete task', 'finish task', 'board update', or 'commit board change'."
---

# Update Board — Task Lifecycle Transitions

This skill updates `board-context.md` when a task changes status and commits the change so the board state is always part of the branch history. This means when a PR merges, the board update merges with it — keeping the board in sync with the code.

## When to Use

Call `/update-board` at every task lifecycle transition:

| Transition | Column Change | Typical Trigger |
|-----------|---------------|-----------------|
| Task picked up | Ready → In Progress | Agent starts work (`/pick-up-task`, `/kick-off`) |
| Task blocked | In Progress → Blocked | Agent hits a dependency or blocker |
| Task unblocked | Blocked → In Progress | Blocker resolved |
| Task sent to review | In Progress → Review | Agent finishes implementation |
| Task completed | Review → Done | Code review approved and merged |

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
```
board.move_task(task_id, "Review", "Done")
board.update_task(task_id, { completed: "YYYY-MM-DD", artifact: "PR #{pr_number}" })
```

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

## Step 4: Confirm the Update

Report the transition to the user:

```
Board updated: {task_id} moved to {target_column}
  Agent: @{AgentName}
  Branch: {current_branch}
  Commit: {short_hash}
```

## Multi-Task Updates

If updating multiple tasks at once (e.g., batch completion after a sprint), update all tasks in `board-context.md` and create a single commit:

```bash
git add board-context.md
git commit -m "[@Atlas] Update board — batch: US-042 → Done, US-043 → Done, T-005 → Review"
```

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
- `/code-review` — after approving a review (→ Done) or requesting changes (stays in Review)
- `/dispatch` — after each dispatched agent completes work (→ Review)

Agents can also invoke it directly at any time by saying "update board" or "move task to [column]".
