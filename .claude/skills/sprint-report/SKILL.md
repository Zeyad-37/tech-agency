---
name: sprint-report
description: "Generate a sprint or period report with throughput, cycle times, agent utilization, quality signals, and trends against the previous period. Use when the user says 'sprint report', 'period report', 'sprint summary', 'how did the sprint go', 'throughput report', 'cycle time report', 'team metrics', or 'end of sprint review'."
---

# /sprint-report — Sprint Report Generator

You are **Atlas** (Orchestrator). Generate a comprehensive sprint or time-period report covering team throughput, cycle times, agent utilization, blockers, and trends.

## Input

Ask the user (if not provided):
- **Period**: sprint dates or "last 2 weeks" / "this month" (default: last 14 days)
- **Scope**: all features or a specific feature/epic

## Step 1 — Gather Raw Data

Read these sources:

1. **Board state** — Read board via board adapter (`read_all`). Count tasks per column.
2. **Git log** — `git log --since="<start>" --until="<end>" --oneline --format="%h|%ai|%s"` to get all commits in the period.
3. **Done column history** — Count tasks that moved to Done during the period. Extract story IDs from commit messages (`[STORY-ID]`).
4. **Retro reports** — Check `docs/artifacts/retro/` for any retros run during the period.
5. **Health reports** — Check `docs/artifacts/health-report/` for the most recent health check.
6. **Post-mortems** — Check `docs/artifacts/post-mortem/INDEX.md` for any incidents during the period.

## Step 2 — Compute Metrics

### Throughput
- **Stories completed**: count of tasks moved to Done in the period
- **Commits**: total commit count
- **Commits per story**: average (flag outliers — stories with >20 commits may indicate scope creep)

### Cycle Time (per completed story)
- If timestamps are available (board comments, git history), calculate:
  - **Lead time**: Ready → Done (total elapsed)
  - **Work time**: In Progress → Done (active work)
  - **Review time**: Review → Done (review queue)
  - **Block time**: total time spent in Blocked column
- Report: **median**, **p90**, and **max** for each
- If precise timestamps aren't available, estimate from git history (first commit on story → last commit)

### Agent Utilization
For each agent with commits in the period:
- Stories touched
- Commits authored (parse `@AgentName` from commit messages)
- Current WIP (tasks in In Progress assigned to them)
- Flag agents with 0 commits (idle) or >2 WIP (overloaded)

### Quality Signals
- **Reviews**: count of reviews actually posted on PRs during the period. `/code-review` posts its verdict to the PR and deliberately writes **no** review markdown into the repo, so counting files would report 0 forever:

  ```bash
  gh pr list --state all --search "merged:>=<start>" --json number \
    --jq '.[].number' \
  | while read -r pr; do gh pr view "$pr" --json reviews --jq '.reviews | length'; done \
  | paste -sd+ - | bc
  ```

  If `gh` is unavailable or unauthenticated, report the metric as "n/a (gh unavailable)" — never as 0, which reads as "nobody reviewed anything".
- **Incidents**: count of rows added to `docs/artifacts/post-mortem/INDEX.md` during the period
- **Health grade**: latest from health report (if available)
- **Hotfixes**: count of hotfix branches merged in the period (`git log --merges --since=<start> --until=<end> --oneline | grep -c 'hotfix/'`)

## Step 3 — Identify Trends

Compare against previous period (if data exists in `docs/artifacts/sprint-report/`):
- Throughput trending up/down/stable
- Cycle time trending up/down/stable
- Block time trending up/down/stable
- Incident count trending up/down/stable

Use simple arrows: **up arrow** (improving), **down arrow** (degrading), **steady** (within 10% of previous)

Note: "improving" means different things per metric:
- Throughput up = improving
- Cycle time down = improving
- Block time down = improving
- Incidents down = improving

## Step 4 — Flag Risks

Flag any of the following:
- Stories in progress for >5 days without a commit
- Agents with >2 WIP items
- Blocked tasks with no recent activity
- Cycle time p90 > 3x median (inconsistency signal)
- Any P0/P1 incidents in the period
- Health grade below B

## Step 5 — Generate Report

Save to `docs/artifacts/sprint-report/YYYY-MM-DD.md` with this structure:

```markdown
# Sprint Report — [Start Date] to [End Date]

## Summary
- **Stories completed**: X
- **Total commits**: X
- **Median cycle time**: X days
- **Incidents**: X
- **Health grade**: X

## Throughput

| Metric | This Period | Previous | Trend |
|--------|------------|----------|-------|
| Stories completed | X | X | arrow |
| Commits | X | X | arrow |
| Avg commits/story | X | X | arrow |

## Cycle Times

| Metric | Median | P90 | Max |
|--------|--------|-----|-----|
| Lead time (Ready → Done) | X | X | X |
| Work time (In Progress → Done) | X | X | X |
| Review time | X | X | X |
| Block time | X | X | X |

## Agent Activity

| Agent | Stories | Commits | Current WIP | Status |
|-------|---------|---------|-------------|--------|
| @AgentName | X | X | X | active/idle/overloaded |

## Quality

| Signal | Count | Trend |
|--------|-------|-------|
| Code reviews | X | arrow |
| Incidents | X | arrow |
| Hotfixes | X | arrow |
| Health grade | X | — |

## Risks & Action Items
- [ ] Risk description → suggested action

## Board Snapshot
[Current column counts from board]
```

## Step 6 — Present to User

Display the summary section inline in the conversation. Link to the full report file for details.

If this is the first sprint report (no previous data), note that trends will be available starting next period.

## Notes

- This command is read-only — it does not modify the board or any project files (except creating the report)
- For accuracy, encourage the team to use consistent commit message format: `[STORY-ID] @AgentName: description`
- The more consistent the board hygiene, the more accurate cycle time calculations will be
- Pair with `/retro` for qualitative analysis — this command focuses on quantitative metrics
