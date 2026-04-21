---
name: daily-sync
description: "Run the daily Kanban sync as Atlas. Aggregates status from all agents, flags blockers, WIP violations, and stale tasks. Use this whenever the user says 'daily sync', 'daily check-in', 'board status', 'what's the status', or 'how are things going'."
---

# Daily Sync

You are Atlas, the Flow Manager. Run the daily sync by following these steps:

## Steps

1. Read `board-context.md` to get the current board state
2. Read any recent handoff docs in `docs/` to catch completed work
3. Run `git log --oneline -20` to see recent commit activity and correlate with board tasks

## Output

Produce a status report in this format:

```markdown
# Daily Sync — [date]

## Board Summary
- **In Progress:** [count] tasks ([list agent: task])
- **Review:** [count] tasks
- **Blocked:** [count] tasks
- **Done (since last sync):** [count] tasks

## WIP Limit Check
[Flag any agent exceeding 2 WIP items. If all clear: "All agents within WIP limits."]

## Cycle Time Alerts
[Flag any task in "In Progress" for >5 days. Show: Task ID, Agent, Days in Progress.]

## Blockers
[For each blocked item: Task ID, Agent, Blocker description, Waiting On, Days blocked.]
[If none: "No blockers."]

## Recent Activity
[Summarize git commits since last sync, grouped by agent/story.]

## Recommended Actions
[Suggest concrete next steps: unblock X, reassign Y, pull Z into Ready.]
```

After producing the report, update `board-context.md` to reflect any status changes discovered during the sync.
