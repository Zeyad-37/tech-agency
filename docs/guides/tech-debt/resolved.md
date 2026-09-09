# Resolved Tech Debt

Items moved here from [backlog.md](./backlog.md) once addressed, with the date and the approach taken. Kept as a record — a debt item that reappears is worth knowing about.

| Date | Item | Resolved By | Approach |
|------|------|-------------|----------|
| 2026-09-09 | Live board state (In Progress, Blocked) did not reach `main` — transitions sat on unmerged branches, so `/pick-up-task`'s WIP check and `/daily-sync`'s counts under-reported in-flight work | @Claude (T-027) | Structural, not a workaround. The `github` board backend makes every transition an API write, so reads are live by construction. The tracked fix was to derive state from `gh pr list` across branches; that is now only needed on the `markdown` backend, where both skills say so explicitly. See `.claude/rules/shared/board-adapter.md` § Known Limitation. |
