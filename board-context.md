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
| T-018 | @Claude | **Epic** — Plugin audit remediation (159 verified findings; 9 P0, 13 P1). All 7 stories merged into `epic/T-018-plugin-audit-remediation`; validation CI green 8/8 on the assembled branch. See `docs/rfc/T-018-RFC-Plugin Audit Remediation.md` | @Zeyad | 2026-09-01 |

## Blocked

| Task ID | Agent | Blocker | Waiting On | Blocked Since |
|---------|-------|---------|------------|---------------|
| — | — | — | — | — |

## Done (recent)

| Task ID | Agent | Description | Output | Completed |
|---------|-------|-------------|--------|-----------|
| T-025 | @Claude | `/setup-repo` placeholder + split delivery + sandbox rewrite; worktrees instead of `git checkout -b` in 6 skills; board-adapter compliance; unified post-mortem paths and board schema | PR #31 | 2026-09-01 |
| T-024 | @Claude | Untrusted-input boundary for `/address-feedback`; guarded the `capture-screenshots` stash; `--base` actually parsed; `code-review` uses the real PR base | PR #30 | 2026-09-01 |
| T-023 | @Claude | New `rules-delivery.md`; push policy settled; honest sandbox claim; error-envelope shape; README counts + "what ships vs. what you bootstrap"; setup/migration guides rewritten | PR #29 | 2026-09-01 |
| T-022 | @Claude | ~35 fixes to the 8 coding standards and 6 reference docs — `SecureStorage` Keychain, authenticated Ktor `post`, ~15 non-compiling samples, MVI/T-013 contradictions | PR #28 | 2026-09-01 |
| T-021 | @Claude | `Write, Edit` for the five authoring agents; `agentModelRouting` removed; on-demand-standards instruction added to every engineering agent | PR #27 | 2026-09-01 |
| T-020 | @Claude | Enforcement gates repaired — secret scan, force-unwrap gates, `commit-msg` regex, `pre-push` refspecs, worktree-aware installer, valid `hooks.json` | PR #26 | 2026-09-01 |
| T-019 | @Claude | Version single-source-of-truth, release CI bumps the governing manifest, new validation CI, root LICENSE | PR #25 | 2026-09-01 |
| T-015 | @Claude | Dynamic base-branch resolution for /dispatch, /dispatch-task, /create-pr (epic integration branches) + optional Copilot gate | PR #15 | 2026-08-26 |

## Decisions Log

| Date | Decision | Decided By | ADR Ref |
|------|----------|------------|---------|
| 2026-08-13 | Every board edit ships inside the PR carrying the change it describes — no board-only PRs, no board commits on `main`. `→ Done` is the final pre-merge commit on the PR branch. | @Zeyad | `.claude/rules/shared/board-in-pr.md` |
| 2026-08-26 | Worktree base branches resolve dynamically: explicit `--base` → epic integration branch (`epic/{EPIC-ID}-{slug}`) → hotfix release tag → `main`. Branch-off and PR-into are always the same branch. | @Zeyad | `.claude/rules/shared/worktree-first.md` § Base Branch Resolution |
| 2026-09-01 | **Rules delivery is split.** The 10 shared rules are copied into the consumer project by `/setup-repo` and auto-load; the 8 language coding standards stay in the plugin and are read on demand via `${CLAUDE_PLUGIN_ROOT}/rules/…`. Fixes delivery to installed users and cuts always-on context from ~79k to ~14k tokens. The nested rules layout is canonical everywhere — the flat consumer layout is retired. | @Zeyad | `.claude/rules/shared/rules-delivery.md` |
| 2026-09-01 | **Commit format widened** to `^\[[A-Za-z]+(-[0-9]+)?\][[:space:]]+(@[A-Za-z]+:[[:space:]]+)?.{3,}` — the agent tag is optional and `[TECH]`-style IDs are accepted. The previous `[A-Z]+-[0-9]+` requirement was passed by 0 of the last 28 commits, including every message the release workflow generates. | @Zeyad | `.claude/rules/shared/git-hooks.md` |
| 2026-09-01 | **Push authorization is skill-scoped.** Invoking `/create-pr` or `/ship-pr` *is* the push authorization for that branch; outside those skills, never run a bare `git push`; never push to `main`. Replaces the blanket "never push" rule that `agent-preamble` step 7 structurally contradicted. | @Zeyad | `.claude/rules/shared/shared-standards.md` |
