# Decisions Log

Decisions that shape how the agency works, newest last. An agent that suspects a prior decision covers its task reads this file before proposing a contradicting approach (see `@.claude/rules/shared/shared-standards.md` § Context Continuity).

| Date | Decision | Decided By | ADR Ref |
|------|----------|------------|---------|
| 2026-08-13 | Every board edit ships inside the PR carrying the change it describes — no board-only PRs, no board commits on `main`. `→ Done` is the final pre-merge commit on the PR branch. | @Zeyad | `.claude/rules/shared/board-in-pr.md` |
| 2026-08-26 | Worktree base branches resolve dynamically: explicit `--base` → epic integration branch (`epic/{EPIC-ID}-{slug}`) → hotfix release tag → `main`. Branch-off and PR-into are always the same branch. | @Zeyad | `.claude/rules/shared/worktree-first.md` § Base Branch Resolution |
| 2026-09-01 | The board is split: `board-context.md` holds only live columns; Backlog, Done (per quarter), and the decisions log move to `docs/board/`. Board rows are one line and link to their artifact rather than carrying prose. | @Zeyad | `.claude/rules/shared/board-adapter.md` |
| 2026-09-01 | **Rules delivery is split.** The 10 shared rules are copied into the consumer project by `/setup-repo` and auto-load; the 8 language coding standards stay in the plugin and are read on demand via `${CLAUDE_PLUGIN_ROOT}/rules/…`. Fixes delivery to installed users and cuts always-on context from ~79k to ~14k tokens. The nested rules layout is canonical everywhere — the flat consumer layout is retired. | @Zeyad | `.claude/rules/shared/rules-delivery.md` |
| 2026-09-09 | **GitHub Issues + Projects v2 is the default board backend for new setups** (RFC T-027 accepted). `/setup-repo` writes `board_backend` explicitly on every run; an absent key resolves to `markdown`, so existing repos are never silently switched. Existing markdown boards move only through `/migrate-board`, which repairs, dry-runs, never deletes, and freezes the markdown as history. On `github`, `Closes #{issue}` in the PR body is the Done transition. | @Zeyad | `docs/artifacts/rfc/T-027-RFC-GitHub Issues Board Backend.md` |
