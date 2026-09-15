# Kanban Board Context

Live columns only. Backlog, completed work, and the decisions log live in [`docs/board/`](docs/board/README.md) — see `@.claude/rules/shared/board-adapter.md`.

Keep rows to one line. Review notes and walkthroughs belong in the linked artifact, not here.

## Ready

| Task ID | Priority | Description | Assigned To |
|---------|----------|-------------|-------------|
| T-027.8 | P2 | Migrate this repo's own board to GitHub Issues with `/migrate-board` (first real run of the `gh` write path) | @Claude |

## In Progress (WIP limit: 2 per agent)

| Task ID | Agent | Description | Started | Cycle Day |
|---------|-------|-------------|---------|-----------|
| T-027.10 | @Claude | `/migrate-board` for legacy consumers: freeze-Done mode, tech-debt import (both paths, header-driven, merges debt already on the board) | 2026-09-15 | 1 |
| T-016 | @Claude | Epic: file organization — rules mirror, board split, doc taxonomy, single version source (integration branch `epic/T-016-file-organization`) | 2026-09-01 | 1 |

## Review

| Task ID | Agent | Description | Reviewer | Waiting Since |
|---------|-------|-------------|----------|---------------|
| T-016.10 | @Claude | Promote the task-ID-title rule the mirror gate caught in the consumer | @Zeyad | 2026-09-08 |
| T-016.9 | @Claude | mirror.sh: refuse a silent downgrade before writing anything | @Zeyad | 2026-09-08 |
| T-016.8 | @Claude | Reconcile T-016 with the merged T-018 plugin audit | @Zeyad | 2026-09-08 |
| T-004 | @Claude | Auto-create GitHub release on push/merge to main | @Zeyad | 2026-06-10 |
| T-014 | @Claude | Board updates ship inside the PR carrying the change (no board-only PRs) | @Zeyad | 2026-08-13 |
| T-016.1 | @Claude | Rules mirror: generated `.claude/rules/` + `rules-local/`, `mirror.sh`, pre-push drift gate | @Zeyad | 2026-09-01 |
| T-016.2 | @Claude | Board split: live columns in `board-context.md`, history in `docs/board/` | @Zeyad | 2026-09-01 |
| T-016.3 | @Claude | One doc taxonomy: `docs/artifacts/{type}/`, closed type list, `by-type`/feature folders removed | @Zeyad | 2026-09-01 |
| T-016.4 | @Claude | Single version source + generated inventories + CI consistency checks | @Zeyad | 2026-09-01 |
| T-016.5 | @Claude | tech-agency's own `docs/` moved to the lifecycle structure | @Zeyad | 2026-09-01 |
| T-016.6 | @Claude | Promote stranded consumer improvements upstream (hooks, executeInParallel, release gate) | @Zeyad | 2026-09-01 |
| T-016.7 | @Claude | pre-push resolves mirror.sh from the plugin instead of silently skipping | @Zeyad | 2026-09-01 |
| T-018 | @Claude | **Epic** — Plugin audit remediation (159 verified findings; 9 P0, 13 P1). All 7 stories merged into `epic/T-018-plugin-audit-remediation`; validation CI green 8/8 on the assembled branch. See `docs/rfc/T-018-RFC-Plugin Audit Remediation.md` | @Zeyad | 2026-09-01 |

## Blocked

| Task ID | Agent | Blocker | Waiting On | Blocked Since |
|---------|-------|---------|------------|---------------|
| — | — | — | — | — |
