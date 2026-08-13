# Kanban Board Context

## Backlog

| Task ID | Priority | Description | Requested By |
|---------|----------|-------------|--------------|
| — | — | — | — |

## Ready

| Task ID | Priority | Description | Assigned To |
|---------|----------|-------------|-------------|
| — | — | — | — |

## In Progress (WIP limit: 2 per agent)

| Task ID | Agent | Description | Started | Cycle Day |
|---------|-------|-------------|---------|-----------|
| — | — | — | — | — |

## Review

| Task ID | Agent | Description | Reviewer | Waiting Since |
|---------|-------|-------------|----------|---------------|
| T-004 | @Claude | Auto-create GitHub release on push/merge to main | @Zeyad | 2026-06-10 |
| T-014 | @Claude | Board updates ship inside the PR carrying the change (no board-only PRs) | @Zeyad | 2026-08-13 |

## Blocked

| Task ID | Agent | Blocker | Waiting On | Blocked Since |
|---------|-------|---------|------------|---------------|
| — | — | — | — | — |

## Done (recent)

| Task ID | Agent | Description | Output | Completed |
|---------|-------|-------------|--------|-----------|
| — | — | — | — | — |

## Decisions Log

| Date | Decision | Decided By | ADR Ref |
|------|----------|------------|---------|
| 2026-08-13 | Every board edit ships inside the PR carrying the change it describes — no board-only PRs, no board commits on `main`. `→ Done` is the final pre-merge commit on the PR branch. | @Zeyad | `.claude/rules/shared/board-in-pr.md` |
