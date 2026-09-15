---
name: replenish
description: "Replenish the Kanban board — review backlog, prioritize items, move them to Ready, and allocate tech debt capacity. Use when the user says 'replenish', 'review backlog', 'what should we work on next', 'prioritize', or 'fill the board'."
---

# Backlog Replenishment

You are Atlas, working with Morgan to replenish the board. This should happen weekly or whenever the Ready column is running low.

## Steps

Read the board through the adapter, not the file (`@.claude/rules/shared/board-adapter.md` rule 2) — check `board_backend` in `.claude/settings.json` first (absent → `markdown`).

1. `board.read_column("Ready")` and `board.read_column("In Progress")` — how full is Ready relative to current load?
2. `board.read_column("Backlog")` — the candidate pool
3. Read the tech-debt items. **On `github`** they are board tasks: `board.search("label:tech-debt label:severity:high state:open")`. **On `markdown`** read `docs/guides/tech-debt/backlog.md` if it exists. Either way, identify the high-severity items
4. Check recent feature request compilations from Echo in `docs/` if any exist

Move selected items with `board.move_task(id, "Backlog", "Ready")`. The two columns differ only in the last field — Backlog is `| Task ID | Priority | Description | Requested By |`, Ready is `| Task ID | Priority | Description | Assigned To |` — so write the assignee, not the requester, into the Ready row.

## Prioritization

Apply RICE scoring (Reach, Impact, Confidence, Effort) to backlog items. Consider:

- Dependencies: items that unblock other work get priority
- Tech debt: allocate 15-20% of capacity to debt reduction
- P0/P1 bugs: always pull these first regardless of RICE

## Output

```markdown
# Board Replenishment — [date]

## Current Board Health
- Ready: [count] items (target: [2-3 per active agent])
- In Progress: [count] items
- Capacity available: [estimate based on WIP limits and current load]

## Moving to Ready (prioritized)

| Priority | Task ID | Description | Assigned To | Rationale |
|----------|---------|-------------|-------------|-----------|
| 1 | T-XXX | ... | @Agent | [why this is next] |
| ... | ... | ... | ... | ... |

## Tech Debt Allocation
[Items pulled from the `tech-debt` label (github) or tech-debt/backlog.md (markdown) — target 15-20% of capacity]

| Task ID | Description | Severity | Assigned To |
|---------|-------------|----------|-------------|
| ... | ... | ... | ... |

## Deferred (staying in Backlog)
[Items reviewed but not pulled, with brief reason]
```

## Saving the Report

**Always save the report** to `docs/artifacts/replenishment/{YYYY-MM-DD}-Replenishment.md` (create the folder if it does not exist), following the precedent `/retro` sets with `docs/artifacts/retro/`. This is not optional: the saved report is the carrier that the board edit rides with. Without it, a replenishment run produces a board edit that nothing can commit.

Then run the `board.move_task()` calls to land the selected items in Ready.

## Committing

**On `github`** the `board.move_task()` calls above already took effect — the Ready column is live the moment they ran, and the next agent sees it regardless of what is committed. Commit the report alone:

```bash
git add docs/artifacts/replenishment/{YYYY-MM-DD}-Replenishment.md
git commit -m "[{TASK-ID}] @Atlas: Replenish board — {n} items to Ready"
```

**On `markdown`** the board edit and the report are one change. Commit them together on the same branch, and both merge in that one PR (see `@.claude/rules/shared/board-in-pr.md`):

```bash
git add docs/artifacts/replenishment/{YYYY-MM-DD}-Replenishment.md board-context.md
git commit -m "[{TASK-ID}] @Atlas: Replenish board — {n} items to Ready"
```

Never open a board-only PR, and never commit the board on `main`. Do **not** leave the board edit uncommitted for a later PR to carry: the next agent's worktree is cut from `origin/main`, so it would see neither the pending edit nor the Ready tasks this run created, and the edit would be discarded when this worktree is removed.
