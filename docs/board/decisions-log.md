# Decisions Log

Decisions that shape how the agency works, newest last. An agent that suspects a prior decision covers its task reads this file before proposing a contradicting approach (see `@.claude/rules/shared/shared-standards.md` § Context Continuity).

| Date | Decision | Decided By | ADR Ref |
|------|----------|------------|---------|
| 2026-08-13 | Every board edit ships inside the PR carrying the change it describes — no board-only PRs, no board commits on `main`. `→ Done` is the final pre-merge commit on the PR branch. | @Zeyad | `.claude/rules/shared/board-in-pr.md` |
| 2026-08-26 | Worktree base branches resolve dynamically: explicit `--base` → epic integration branch (`epic/{EPIC-ID}-{slug}`) → hotfix release tag → `main`. Branch-off and PR-into are always the same branch. | @Zeyad | `.claude/rules/shared/worktree-first.md` § Base Branch Resolution |
| 2026-09-01 | The board is split: `board-context.md` holds only live columns; Backlog, Done (per quarter), and the decisions log move to `docs/board/`. Board rows are one line and link to their artifact rather than carrying prose. | @Zeyad | `.claude/rules/shared/board-adapter.md` |
