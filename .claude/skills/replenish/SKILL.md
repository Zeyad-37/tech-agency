---
name: replenish
description: "Replenish the Kanban board — review backlog, prioritize items, move them to Ready, and allocate tech debt capacity. Use when the user says 'replenish', 'review backlog', 'what should we work on next', 'prioritize', or 'fill the board'."
---

# Backlog Replenishment

You are Atlas, working with Morgan to replenish the board. This should happen weekly or whenever the Ready column is running low.

## Steps

1. Read `board-context.md` — check how many items are in Ready vs In Progress
2. Read the backlog section of `board-context.md`
3. Read `docs/tech-debt/backlog.md` if it exists — identify high-severity debt items
4. Check recent feature request compilations from Echo in `docs/` if any exist

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
[Items pulled from tech-debt/backlog.md — target 15-20% of capacity]

| Task ID | Description | Severity | Assigned To |
|---------|-------------|----------|-------------|
| ... | ... | ... | ... |

## Deferred (staying in Backlog)
[Items reviewed but not pulled, with brief reason]
```

After producing the report, update `board-context.md` to move the selected items to Ready.
