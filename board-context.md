# Kanban Board Context

Live columns only. Backlog, completed work, and the decisions log live in [`docs/board/`](docs/board/README.md) — see `@.claude/rules/shared/board-adapter.md`.

Keep rows to one line. Review notes and walkthroughs belong in the linked artifact, not here.

## Ready

| Task ID | Priority | Description | Assigned To |
|---------|----------|-------------|-------------|
| — | — | — | — |

## In Progress (WIP limit: 2 per agent)

| Task ID | Agent | Description | Started | Cycle Day |
|---------|-------|-------------|---------|-----------|
| T-016 | @Claude | Epic: file organization — rules mirror, board split, doc taxonomy, single version source (integration branch `epic/T-016-file-organization`) | 2026-09-01 | 1 |

## Review

| Task ID | Agent | Description | Reviewer | Waiting Since |
|---------|-------|-------------|----------|---------------|
| T-004 | @Claude | Auto-create GitHub release on push/merge to main | @Zeyad | 2026-06-10 |
| T-014 | @Claude | Board updates ship inside the PR carrying the change (no board-only PRs) | @Zeyad | 2026-08-13 |
| T-016.1 | @Claude | Rules mirror: generated `.claude/rules/` + `rules-local/`, `mirror.sh`, pre-push drift gate | @Zeyad | 2026-09-01 |
| T-016.2 | @Claude | Board split: live columns in `board-context.md`, history in `docs/board/` | @Zeyad | 2026-09-01 |
| T-016.3 | @Claude | One doc taxonomy: `docs/artifacts/{type}/`, closed type list, `by-type`/feature folders removed | @Zeyad | 2026-09-01 |
| T-016.4 | @Claude | Single version source + generated inventories + CI consistency checks | @Zeyad | 2026-09-01 |
| T-016.5 | @Claude | tech-agency's own `docs/` moved to the lifecycle structure | @Zeyad | 2026-09-01 |

## Blocked

| Task ID | Agent | Blocker | Waiting On | Blocked Since |
|---------|-------|---------|------------|---------------|
| — | — | — | — | — |
