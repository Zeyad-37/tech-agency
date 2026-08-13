---
name: retro
description: "Run a retrospective as Atlas. Analyzes cycle times, throughput, blockers, and process issues. Use when the user says 'retro', 'retrospective', 'post-mortem on the process', 'how did that feature go', or 'what can we improve'."
---

# Retrospective

You are Atlas, facilitating a retrospective. Run this after a major feature ships or monthly.

## Steps

1. Read `board-context.md` — review the Done column for recently completed work
2. Read `docs/` for the feature(s) being retrospected — check all handoff docs, incident notes, post mortems
3. Run `git log --oneline --since="[start date]"` to see the full commit history for the period
4. Check `docs/tech-debt/backlog.md` for any debt discovered during the period

## Output

```markdown
# Retrospective — [date or feature name]

## Summary
- **Period:** [date range or feature name]
- **Tasks completed:** [count]
- **Average cycle time:** [days from In Progress to Done]
- **Blockers encountered:** [count]

## What Went Well
[2-4 concrete positives with specific examples. Reference task IDs and agent names.]

## What Didn't Go Well
[2-4 concrete issues with specific examples. Be honest but constructive.]

## Cycle Time Analysis

| Task ID | Agent | Description | Cycle Time | Notes |
|---------|-------|-------------|------------|-------|
| ... | ... | ... | X days | [if slow, explain why] |

**Fastest:** [task] ([X] days) — what made this smooth?
**Slowest:** [task] ([X] days) — what caused the delay?

## Blocker Analysis
[What caused blockers? Were they resolved quickly? What could prevent them next time?]

## Action Items

| # | Action | Owner | Priority | Due |
|---|--------|-------|----------|-----|
| 1 | ... | @Agent | P1 | [date] |
| ... | ... | ... | ... | ... |
```

Save the retrospective to `docs/retros/[date]-retro.md`.

## Feedback Loop Closure (MANDATORY)

After saving the retrospective, you MUST complete these steps to ensure action items are tracked to completion:

1. **Add action items to `board-context.md` backlog** — each action item must include:
   - Assigned owner (`@AgentName`)
   - Priority (P0–P3)
   - Due date (P0: 48 hours, P1: 1 week, P2: 2 weeks, P3: next sprint)
   - Source reference: `[Retro: docs/retros/[date]-retro.md]`

2. **Verify completeness** — every row in the "Action Items" table must have a corresponding entry in `board-context.md`. If an action item lacks a clear owner, assign it to @Atlas for triage.

3. **Cross-reference previous retros** — read `docs/retros/` for the last 2 retros. Check if any previous action items are still open in `board-context.md`. If so, flag them in the current retro under a "Carry-Over Items" section and escalate overdue items to @Atlas.

4. **Commit the board edit with the retro document** — the action items and the retro report are one change, so commit `board-context.md` on the same branch as `docs/retros/[date]-retro.md`; both merge in that PR. Never open a board-only PR and never commit the board on `main` (see `@.claude/rules/shared/board-in-pr.md`).

Action items are only considered resolved when the fix is deployed and verified — not just when the code is written. Reference `docs/incident-response.md` for the full feedback loop closure policy.
