# Tech Debt Backlog

Tracked technical debt discovered outside the scope of active tasks. Each entry: description, severity (high/medium/low), category, affected modules, estimated effort, and discovering agent. See `@.claude/rules/shared/operational-standards.md` § "Technical Debt Tracking".

| # | Description | Severity | Category | Affected Modules | Est. Effort | Discovered By |
|---|-------------|----------|----------|------------------|-------------|---------------|
| 1 | `/create-pr` still references `/ship-it` as the `--no-push` parent that "owns the Copilot request" (lines ~3, 10, 307, 380). After PR #12, the ship chain reaches `/create-pr`'s push path via `/ship-pr`, so these references are stale. Refresh them so the single-Copilot-requester story reads cleanly. | low | Documentation | `.claude/skills/create-pr/SKILL.md` | ~30 min | code review on PR #12 |
| 2 | `/setup-repo` addresses the shared rules at a **flat** `.claude/rules/{name}.md` path (~12 references: the verification loop that tests `[ -f ".claude/rules/${rule}.md" ]`, and the scaffolding loop that runs `cp {project-template}/.claude/rules/{name}.md .claude/rules/`), and `docs/guides/setup-guide.md`'s directory tree shows the same flat layout. The rules actually live at `.claude/rules/shared/`, and 20+ cross-references across rules and skills use `@.claude/rules/shared/…`. Consequence: the verification loop reports every rule missing, and the scaffolding loop copies from a non-existent source into a destination where the `shared/` references would not resolve in the target project. Make setup-repo's loops, the setup-guide tree, and the scaffolded target layout consistently nested under `shared/`. Deliberately deferred from PR #14 (T-014), which only added two names to the existing loops and did not change the layout. | high | Documentation | `.claude/skills/setup-repo/SKILL.md`, `docs/guides/setup-guide.md` | ~1-2 h | code review on PR #14 |

## Stranded consumer improvements — not yet promoted (T-016.6, 2026-09-01)

Found while building the rules mirror: the reference consumer had rule content the plugin never received. These four are genuinely generic and should be promoted, but each needs careful genericization (they carry concrete module paths and project ticket IDs) and so were left out of T-016.6, which took only the corrections and the hooks.

| Item | Rule | Severity | Why it is generic |
|---|---|---|---|
| Presentation module split (`sharedPresentation` + `list`/`detail`/`form` per feature) | `mobile/shared/kmp-coding-standards.md` | Medium | A layering rule about surface modules, independent of any one feature |
| Pipeline Store for retained observation pipelines | `mobile/shared/kmp-coding-standards.md` | Medium | Keeps pipeline keys out of `State`; applies to any MVI screen with a long-lived `combine` |
| `*StateFactory.kt` file-organization suffix | `mobile/android/compose-coding-standards.md` | Low | Distinguishes construction-with-UI-decisions from pure translation (`*Mapper`) |
| Per-changed-module test running in pre-push (replacing `assemble`) | `shared/git-hooks.md` | Medium | `assemble` triggers the OOM-prone release/R8 build; per-module tests cover compilation more cheaply |

Discovered by: @Claude. The consumer keeps these in `.claude/rules-local/` until promoted.
