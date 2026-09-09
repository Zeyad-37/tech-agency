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
## Done (recent)
|---------|-------------|-------------|--------|-----------|
## Decisions Log
|------|----------|------------|---------|
| Task ID | Agent | Description | Output | Completed |
| T-026 | @Claude | Extract `marketing-agency` to its own private repo (clean break); `/setup-repo` writes `extraKnownMarketplaces` + `enabledPlugins` so the plugin is available at repo level incl. cloud sessions; public-readiness scrub + a CI check that keeps it scrubbed | PR #33 | 2026-09-01 |
| T-025 | @Claude | `/setup-repo` placeholder + split delivery + sandbox rewrite; worktrees instead of `git checkout -b` in 6 skills; board-adapter compliance; unified post-mortem paths and board schema | PR #31 | 2026-09-01 |
| T-024 | @Claude | Untrusted-input boundary for `/address-feedback`; guarded the `capture-screenshots` stash; `--base` actually parsed; `code-review` uses the real PR base | PR #30 | 2026-09-01 |
| T-023 | @Claude | New `rules-delivery.md`; push policy settled; honest sandbox claim; error-envelope shape; README counts + "what ships vs. what you bootstrap"; setup/migration guides rewritten | PR #29 | 2026-09-01 |
| T-022 | @Claude | ~35 fixes to the 8 coding standards and 6 reference docs — `SecureStorage` Keychain, authenticated Ktor `post`, ~15 non-compiling samples, MVI/T-013 contradictions | PR #28 | 2026-09-01 |
| T-021 | @Claude | `Write, Edit` for the five authoring agents; `agentModelRouting` removed; on-demand-standards instruction added to every engineering agent | PR #27 | 2026-09-01 |
| T-020 | @Claude | Enforcement gates repaired — secret scan, force-unwrap gates, `commit-msg` regex, `pre-push` refspecs, worktree-aware installer, valid `hooks.json` | PR #26 | 2026-09-01 |
| T-019 | @Claude | Version single-source-of-truth, release CI bumps the governing manifest, new validation CI, root LICENSE | PR #25 | 2026-09-01 |
| T-015 | @Claude | Dynamic base-branch resolution for /dispatch, /dispatch-task, /create-pr (epic integration branches) + optional Copilot gate | PR #15 | 2026-08-26 |
| Date | Decision | Decided By | ADR Ref |
| 2026-08-13 | Every board edit ships inside the PR carrying the change it describes — no board-only PRs, no board commits on `main`. `→ Done` is the final pre-merge commit on the PR branch. | @Zeyad | `.claude/rules/shared/board-in-pr.md` |
| 2026-08-26 | Worktree base branches resolve dynamically: explicit `--base` → epic integration branch (`epic/{EPIC-ID}-{slug}`) → hotfix release tag → `main`. Branch-off and PR-into are always the same branch. | @Zeyad | `.claude/rules/shared/worktree-first.md` § Base Branch Resolution |
| 2026-09-01 | **Rules delivery is split.** The 10 shared rules are copied into the consumer project by `/setup-repo` and auto-load; the 8 language coding standards stay in the plugin and are read on demand via `${CLAUDE_PLUGIN_ROOT}/rules/…`. Fixes delivery to installed users and cuts always-on context from ~79k to ~14k tokens. The nested rules layout is canonical everywhere — the flat consumer layout is retired. | @Zeyad | `.claude/rules/shared/rules-delivery.md` |
