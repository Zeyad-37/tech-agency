# Tech Debt Backlog

Tracked technical debt discovered outside the scope of active tasks. Each entry: description, severity (high/medium/low), category, affected modules, estimated effort, and discovering agent. See `@.claude/rules/shared/operational-standards.md` § "Technical Debt Tracking".

| # | Description | Severity | Category | Affected Modules | Est. Effort | Discovered By |
|---|-------------|----------|----------|------------------|-------------|---------------|
| 1 | `/create-pr` still references `/ship-it` as the `--no-push` parent that "owns the Copilot request" (lines ~3, 10, 307, 380). After PR #12, the ship chain reaches `/create-pr`'s push path via `/ship-pr`, so these references are stale. Refresh them so the single-Copilot-requester story reads cleanly. | low | Documentation | `.claude/skills/create-pr/SKILL.md` | ~30 min | code review on PR #12 |
