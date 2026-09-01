# Migration Guide — Adopting the Tech Agency in Existing Projects

This guide describes how to incrementally adopt the Tech Agency system in an existing codebase. The goal is progressive improvement, not a big-bang rewrite.

## Principles

- **Incremental adoption**: You do not need to comply with every standard on day one. Start with the highest-value, lowest-friction items and expand over time.
- **Non-destructive onboarding**: The agency configuration sits alongside your existing code — it doesn't replace your build system, CI, or project structure.
- **Per-module, per-team**: Different parts of a large codebase can adopt at different paces. A new feature module can follow full standards while legacy modules adopt gradually.

## Phase 1 — Foundation (Day 1)

Nothing in this phase is manual file copying. You install a plugin and run one command.

### 1.1 Install the Plugin

```bash
claude plugin marketplace add github:Zeyad-37/tech-agency --scope user
claude plugin install tech-agency@tech-agency --scope user
```

This gives you the 19 agents, the 48 skills, and the 8 language coding standards. It gives you
nothing inside your repo yet.

### 1.2 Run `/setup-repo`

Open Claude Code in your project root and run:

```
/setup-repo
```

`/setup-repo` is **non-destructive**: it audits what already exists and only fills gaps, so it is
safe on a mature codebase. It bootstraps:

- `.claude/rules/shared/` — the 11 shared policy rules, which auto-load every session
- `board-context.md` — the Kanban board
- `hooks/` — the git hook scripts
- `.claude/settings.json` — sandbox, permissions, board backend (model tier is set per agent in each agent's own `model:` frontmatter, not here)
- `.claude/hooks.json` — session hooks
- `docs/` artifact folders

Then install the git hooks into `.git/`:

```bash
./hooks/install-hooks.sh
```

**You do not select or copy coding standards for your stack.** The 8 language standards stay in the
plugin and are read on demand — an agent reads the one matching the language it is about to write.
That is the whole point of the split: an Android-only repo never loads the React or FastAPI
standard. See "Rules delivery" in `docs/setup-guide.md`, or the authoritative
`@.claude/rules/shared/rules-delivery.md`.

There is no `CLAUDE.md` step. The agency's project instructions arrive as the shared rules in
`.claude/rules/shared/`, which Claude Code loads automatically. If your project already has its own
`CLAUDE.md` for unrelated reasons, `/setup-repo` leaves it alone.

### 1.3 Seed the Board

`/setup-repo` creates an empty `board-context.md`. Populate it with your current work items, using
the columns from `@.claude/rules/shared/shared-standards.md`: Backlog → Ready → In Progress → Review → Blocked → Done.

`/replenish` will help — point it at your existing backlog (issue tracker export, TODO list, or a
pasted list) and it will triage items into Backlog and promote the prioritized ones to Ready.

If you would rather keep your existing tracker as the source of truth, set `board_backend` in
`.claude/settings.json` to `jira`, `linear`, or `asana` and wire up the MCP connection — see
`docs/board-config.md`. The board adapter translates every agent operation to your tool.

**Expect `main` to show an empty "In Progress" column.** Board transitions commit on the task branch
and only reach `main` when that branch's PR merges. That is by design — see
`@.claude/rules/shared/board-in-pr.md`.

## Phase 2 — Observability & CI (Week 1)

These provide the most immediate safety net for AI-generated code.

### 2.1 Add Health Checks

If your services don't already have them, add `GET /health` (liveness) and `GET /health/ready` (readiness) endpoints. This is a small change with outsized value — it enables monitoring and deployment safety.

### 2.2 Add Structured Logging

Migrate from unstructured logging (e.g., `console.log`, `print()`, bare `Log.d()`) to structured JSON logging. Each coding standard describes the recommended approach for its stack. At minimum, ensure every log entry includes: `level`, `timestamp`, `service`, `traceId`, `message`.

### 2.3 Integrate CI Quality Gates

If you have existing CI, layer the agency's quality gates incrementally:

| Gate | Priority | When to Add |
|------|----------|-------------|
| Lint / format | Week 1 | Add as a non-blocking warning initially. Make blocking after the codebase is formatted. |
| Unit tests | Week 1 | Run existing tests. Add coverage tracking. Don't enforce coverage minimums yet. |
| Security scan (OWASP / npm audit / pip-audit) | Week 1 | Add immediately. Fail on CRITICAL only at first, then tighten to HIGH (CVSS >= 7.0). |
| Integration tests | Week 2 | Add if you have them. If not, start writing them for new code. |
| Coverage thresholds | Week 3+ | Once baseline is established, set thresholds at current coverage + 5% and ratchet up. |

See `docs/ci-enforcement-policy.md` for the full policy.

### 2.4 Use `/setup-repo` for New Modules

When creating new modules or services within the existing project, use the `/setup-repo` skill to scaffold them with the correct structure, CI workflows, and branch protection from the start.

## Phase 3 — Code Standards Adoption (Weeks 2–4)

### 3.1 New Code First

Apply the coding standards to all **new** code immediately. Every new file, module, or feature follows the standards. This is the lowest-friction way to improve quality.

Agents do this automatically — reading the stack's standard before writing code in it is a mandatory preamble step. To read one yourself, open it in the plugin at `${CLAUDE_PLUGIN_ROOT}/rules/<path>.md` (the path table is in `docs/setup-guide.md` under "Rules delivery").

### 3.2 Modified Code Next

When modifying existing files, bring the **changed sections** into compliance. Don't rewrite the entire file — just the parts you're touching. Over time, the codebase converges.

### 3.3 Lint & Format the Codebase

Run the formatter (Prettier, ktlint, Black, Spotless, SwiftFormat) across the entire codebase in a single dedicated PR. This is a mechanical change that shouldn't introduce bugs. Do this early — it eliminates formatting noise in future PRs.

### 3.4 Gradual Architecture Alignment

If the existing project structure doesn't match the coding standards (e.g., different package layout, missing layer separation), don't refactor everything at once. Instead:

1. Document the current structure in a `docs/architecture-current.md`.
2. Document the target structure (from the coding standards) in a `docs/architecture-target.md`.
3. Each new feature uses the target structure. Existing modules migrate when they're significantly modified.
4. Track migration progress in `docs/tech-debt/backlog.md`.

## Phase 4 — Testing Maturity (Weeks 3–6)

### 4.1 Establish a Baseline

Run your existing test suite and measure coverage. Record this in `docs/test-baseline.md` with the date.

### 4.2 Ratchet Coverage

Set CI coverage thresholds at your current level (e.g., if you're at 45%, set the threshold at 45%). Every week, increase the threshold by 2–5% until you reach the targets defined in the coding standards (80%+ core logic, 60%+ overall).

### 4.3 Add Missing Test Types

Most existing projects have unit tests but lack other types. Add them in this priority order:

1. **Integration tests** (controller/route tests with real DB) — highest bug-finding value.
2. **Security tests** (auth, injection, missing permissions) — prevents production incidents.
3. **E2E tests** (critical user flows) — catches system-level regressions.
4. **Screenshot/visual regression tests** — prevents UI drift.
5. **Load tests** — run before each release.
6. **Accessibility tests** — integrate into CI.

### 4.4 Testcontainers for Real DB Tests

If your integration tests currently mock the database, migrate to Testcontainers (or equivalent) for real DB testing. The coding standards describe this pattern for every backend stack.

## Phase 5 — Process Adoption (Weeks 4–8)

### 5.1 Start Using the Board

Move from whatever project management you're using to the `board-context.md` Kanban board, or sync them. The board is the single source of truth for work status during agent sessions.

### 5.2 Adopt Handoff Templates

Start using the handoff templates from `@.claude/rules/shared/handoff-protocol.md` for cross-functional work. They ensure nothing falls through the cracks.

### 5.3 Run Retros

Use the `/retro` skill after each feature or monthly. This closes the feedback loop and drives continuous improvement.

### 5.4 Adopt the Release Process

Integrate the release process from `@.claude/rules/shared/shared-standards.md`: semantic versioning, release checklists, canary deployments, auto-rollback. Layer this on top of your existing deployment pipeline.

## Phase 6 — Full Compliance (Ongoing)

### 6.1 Architecture Enforcement

If using KMP, add Konsist tests to enforce layer dependencies. For other stacks, add equivalent lint rules (e.g., ESLint import restrictions, ArchUnit for JVM).

### 6.2 SLO Definitions

Define SLOs for every service per `@.claude/rules/shared/operational-standards.md`. Store in `docs/slo/{service-name}.md`. Configure alerting based on error budget burn rate.

### 6.3 Feature Flags

Adopt feature flags for all new user-facing features per `@.claude/rules/shared/operational-standards.md`. This enables safe rollouts and instant rollback.

### 6.4 Data Privacy Audit

Review your data handling against the Data Privacy & Compliance section of `@.claude/rules/shared/operational-standards.md`. Document data classification, retention policies, and consent tracking.

## Checklist

Use this checklist to track your migration progress:

```
Phase 1 — Foundation
[ ] Plugin installed from the marketplace
[ ] /setup-repo run — shared rules, board, hooks, settings.json in place
[ ] Git hooks installed (./hooks/install-hooks.sh) and verified as symlinks
[ ] Sandbox confirmed present in .claude/settings.json
[ ] board-context.md seeded with current work (or external backend configured)

Phase 2 — Observability & CI
[ ] Health check endpoints added to all services
[ ] Structured logging adopted
[ ] Lint/format CI gate added
[ ] Security scan CI gate added
[ ] Unit test CI gate added

Phase 3 — Code Standards
[ ] Formatter run across entire codebase
[ ] New code follows coding standards
[ ] Architecture current vs target documented
[ ] Tech debt backlog initialized

Phase 4 — Testing Maturity
[ ] Test baseline measured and recorded
[ ] Coverage ratchet configured in CI
[ ] Integration tests added for critical paths
[ ] Security tests added
[ ] E2E tests for top 3 user flows

Phase 5 — Process
[ ] Board in active use
[ ] Handoff templates adopted
[ ] First retro completed
[ ] Release process documented and followed

Phase 6 — Full Compliance
[ ] Architecture enforcement rules in CI
[ ] SLOs defined for all services
[ ] Feature flags adopted
[ ] Data privacy audit completed
```

## Tips for Large Existing Codebases

- **Don't try to fix everything at once.** The biggest risk in adopting standards is demoralization from an overwhelming gap between current and target state. Small wins compound.
- **Automate formatting first.** It's mechanical, safe, and eliminates the most visible code quality issue.
- **Use a "strangler fig" pattern for architecture migration.** New features use the target architecture; old code stays as-is until it needs significant changes.
- **Track progress visually.** Update the checklist above monthly. Seeing boxes get checked motivates continued effort.
- **Involve the team.** If human developers are also working on the project, share the coding standards and get buy-in. Standards that only AI agents follow will diverge from human-written code.
