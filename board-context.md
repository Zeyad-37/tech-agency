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
| T-018 | @Claude | **Epic** — Plugin audit remediation (159 verified findings; 9 P0, 13 P1). Integration branch `epic/T-018-plugin-audit-remediation`, 7 story PRs. See `docs/rfc/T-018-RFC-Plugin Audit Remediation.md` | 2026-09-01 | 1 |

### T-018 stories (merge into the integration branch, not `main`)

| Task ID | Branch | Scope | Status |
|---------|--------|-------|--------|
| T-019 | `T-019/release-integrity` | Version single-source-of-truth, release CI bumps the governing manifest, new validation CI, root LICENSE, gitignore `settings.local.json` | In Progress |
| T-020 | `T-020/hook-gates` | Secret scan reads staged content with correct patterns; force-unwrap gates use ERE; grep exit-code handling; widened `commit-msg` regex; `pre-push` reads stdin refspecs; worktree-aware installer; valid `hooks.json` schema | In Progress |
| T-021 | `T-021/agent-definitions` | `Write, Edit` for the five authoring agents; delete non-canonical `agentModelRouting`; repair rule references; on-demand-standards instruction | In Progress |
| T-022 | `T-022/standards-corrections` | ~35 fixes to the 8 coding standards and 6 reference docs — `SecureStorage` Keychain, unauthenticated Ktor `post`, ~15 non-compiling samples, MVI/T-013 self-contradictions | In Progress |
| T-023 | `T-023/shared-rules-and-docs` | New `rules-delivery.md`; settle push policy; honest sandbox claim; error-envelope shape; README counts + "what ships vs. what you bootstrap"; rewrite setup/migration guides | In Progress |
| T-024 | `T-024/ship-path-skills` | Untrusted-input boundary for `/address-feedback`; guard the `capture-screenshots` stash; parse `--base`; point `code-review` at the real PR base and canonical doc paths | In Progress |
| T-025 | `T-025/planning-board-skills` | Bind `/setup-repo`'s placeholder + split delivery + sandbox rewrite; worktrees instead of `git checkout -b` in 6 skills; board-adapter compliance; unify post-mortem paths and board schema | In Progress |

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
| T-015 | @Claude | Dynamic base-branch resolution for /dispatch, /dispatch-task, /create-pr (epic integration branches) + optional Copilot gate | PR #15 | 2026-08-26 |

## Decisions Log

| Date | Decision | Decided By | ADR Ref |
|------|----------|------------|---------|
| 2026-08-13 | Every board edit ships inside the PR carrying the change it describes — no board-only PRs, no board commits on `main`. `→ Done` is the final pre-merge commit on the PR branch. | @Zeyad | `.claude/rules/shared/board-in-pr.md` |
| 2026-08-26 | Worktree base branches resolve dynamically: explicit `--base` → epic integration branch (`epic/{EPIC-ID}-{slug}`) → hotfix release tag → `main`. Branch-off and PR-into are always the same branch. | @Zeyad | `.claude/rules/shared/worktree-first.md` § Base Branch Resolution |
| 2026-09-01 | **Rules delivery is split.** The 10 shared rules are copied into the consumer project by `/setup-repo` and auto-load; the 8 language coding standards stay in the plugin and are read on demand via `${CLAUDE_PLUGIN_ROOT}/rules/…`. Fixes delivery to installed users and cuts always-on context from ~79k to ~14k tokens. The nested rules layout is canonical everywhere — the flat consumer layout is retired. | @Zeyad | `.claude/rules/shared/rules-delivery.md` |
| 2026-09-01 | **Commit format widened** to `^\[[A-Za-z]+(-[0-9]+)?\][[:space:]]+(@[A-Za-z]+:[[:space:]]+)?.{3,}` — the agent tag is optional and `[TECH]`-style IDs are accepted. The previous `[A-Z]+-[0-9]+` requirement was passed by 0 of the last 28 commits, including every message the release workflow generates. | @Zeyad | `.claude/rules/shared/git-hooks.md` |
| 2026-09-01 | **Push authorization is skill-scoped.** Invoking `/create-pr` or `/ship-pr` *is* the push authorization for that branch; outside those skills, never run a bare `git push`; never push to `main`. Replaces the blanket "never push" rule that `agent-preamble` step 7 structurally contradicted. | @Zeyad | `.claude/rules/shared/shared-standards.md` |
