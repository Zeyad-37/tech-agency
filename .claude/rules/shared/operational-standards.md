# Operational Standards

## API Versioning & Deprecation

- All APIs versioned: `/api/v1/`, `/api/v2/`, etc.
- When introducing a breaking change, create a new version — never modify an existing version's contract
- Deprecated versions must return a `Sunset` header with the retirement date and a `Deprecation` header with the date deprecation was announced
- Minimum deprecation notice: 3 months before sunset for external APIs, 2 weeks for internal-only APIs
- @Scroll documents migration guides for each version bump in `docs/api-migration/{Task-Id}-API Migration-v{old}-to-v{new}.md`
- @Sentinel monitors traffic on deprecated versions — do not retire until traffic drops below 1% or the sunset date passes
- After retirement, deprecated endpoints return `410 Gone` with a body pointing to the new version

## Dependency Management

- All third-party dependencies pinned to exact versions (no floating ranges)
- Kotlin version catalog (`libs.versions.toml`) is the single source of truth for KMP projects
- Dependency update cadence: security patches within 48 hours (P0 if critical), minor updates monthly, major updates evaluated as needed
- @Shield runs `snyk test` or equivalent on every PR that modifies dependency files
- Before upgrading a major version: @Sage writes an ADR evaluating the upgrade (breaking changes, migration effort, alternatives). @Zeyad approves
- KMP-specific: Kotlin version upgrades require coordinated testing across iOS, Android, and backend targets. @Link owns the upgrade, @Swift and @Kai verify integration

## Feature Flags

- All new user-facing features must ship behind a feature flag
- Flag naming: `ff_{feature_name}` (e.g., `ff_new_onboarding`, `ff_dark_mode`)
- Flag states: `off` (default for new flags), `percentage` (gradual rollout), `on` (fully enabled)
- Feature flag lifecycle: created at implementation → enabled gradually at release → removed after 4 weeks of stable `on` state
- Dead flags (>4 weeks at `on` with no issues) must be cleaned up — remove the flag and the conditional code. @Atlas tracks flag cleanup as tech debt tasks
- Flags must be evaluable server-side and client-side. Never hardcode flag values — always read from the flag service
- Rollback via flag: if a feature causes issues post-release, disable the flag before considering a code revert. This is faster than a hotfix

## Database Change Safety

- All schema migrations must be backward-compatible with the currently deployed code (expand-and-contract pattern)
- **Expand phase** (deploy first): add new columns/tables, make them nullable or with defaults. Old code continues working
- **Migrate phase**: backfill data, deploy new code that writes to both old and new columns
- **Contract phase** (deploy last): remove old columns/tables only after all code references are removed and verified
- Never rename or drop a column in the same deploy as the code change that stops using it
- Destructive migrations (drops, renames) require @Sage approval and must include a rollback migration
- Large data migrations (>1M rows) must run as background jobs, not in the migration itself — coordinate with @Pipeline
- Every migration must be tested against a production-sized dataset in staging before release

## Performance Regression Detection

- Every PR that touches rendering, data fetching, or KMP shared code must include before/after benchmark results in the PR description
- Web (@Nova): run Lighthouse CI on affected pages. Block merge if LCP regresses >200ms, CLS regresses >0.05, or bundle size increases >5KB without justification
- Mobile (@Swift, @Kai): profile with Instruments (iOS) or Android Studio Profiler. Block merge if frame drop rate exceeds 5% or startup time increases >100ms
- KMP (@Link): benchmark shared module initialization and critical-path operations. Document results in the PR
- Backend (@Flux, @Pyra, @Forge): load test endpoints affected by the change using k6. Block merge if P99 latency regresses >50ms under expected load
- @Apex includes performance verification in the release sign-off checklist
- Performance budgets are defined per project in `docs/performance-budgets.md` — @Sage sets initial values, @Zeyad approves changes

## Accessibility Testing Gate

- Accessibility is a release-blocking quality gate, not optional polish
- @Apex must verify accessibility as part of release sign-off:
  - Web: automated axe-core scan (zero critical/serious violations) + manual keyboard navigation test
  - iOS: VoiceOver walkthrough of all new/changed screens + Dynamic Type at largest setting
  - Android: TalkBack walkthrough of all new/changed screens + font scale at 200%
- Every component spec from @Pixel must include accessibility annotations (roles, labels, focus order, touch targets)
- @Nova, @Swift, @Kai must include accessibility attributes in implementation — missing labels or roles are treated as bugs, not enhancements
- Accessibility regressions are P1 bugs — same priority as functional bugs

## Data Privacy & Compliance

- Default to privacy: collect only data that is necessary for the feature. If in doubt, don't collect
- All PII fields must be documented in the data dictionary (maintained by @Diana per feature in the BRD)
- Data classification levels: **Public** (no restrictions), **Internal** (auth required), **Confidential** (encrypted at rest + in transit, access-logged), **Restricted** (all of Confidential + explicit consent, retention limits, deletion support)
- Every Confidential/Restricted field must support: right-to-deletion (GDPR Art. 17), data export (GDPR Art. 20), and consent withdrawal
- Data retention: define retention period per data type in `docs/data-retention-policy.md`. @Pipeline implements automated purge jobs. No indefinite retention without justification
- Consent tracking: store consent grants with timestamp, scope, and version. Users must be able to view and revoke consent
- @Shield audits data handling in security reviews. @Diana flags compliance requirements in BRDs. @Sage ensures architecture supports privacy requirements
- Third-party data sharing: no PII sent to third-party services without @Shield review and @Zeyad approval. Document all third-party data flows in `docs/data-flow-map.md`

## Monitoring & Alerting Baselines

- Every service must define SLOs before production deployment:
  - **Availability**: target uptime (e.g., 99.9% = 43 min downtime/month)
  - **Latency**: P50, P95, P99 targets per endpoint
  - **Error rate**: maximum acceptable error percentage
- Alert thresholds derived from SLOs. Alert when the error budget burn rate threatens the SLO — not on individual errors
- Required monitors per service:
  - Health check (up/down) — alert after 2 consecutive failures
  - Error rate — alert if >1% over 5-minute window
  - Latency P99 — alert if >2x the SLO target over 5-minute window
  - Crash-free rate (mobile) — alert if drops below 99.5%
  - CPU/memory — alert at 80% sustained over 10 minutes
- @Sentinel configures monitoring for all services. Alert routing: P0 → PagerDuty (immediate), P1 → Slack + PagerDuty (15 min), P2 → Slack (next business day)
- Every new service deployment includes a monitoring verification step — @Sentinel confirms all dashboards and alerts are active before marking deployment complete
- SLO definitions and alert configs stored in `docs/slo/{service-name}.md`

## Incident Severity Definitions

- **P0 — Critical**: Service is down or data loss is occurring. Affects >5% of users or all users of a platform. Revenue impact. Response: immediate (within 15 minutes). All hands until resolved. @Zeyad notified immediately
- **P1 — High**: Major feature broken, significant degradation, crash spike >1%. Affects 1-5% of users. Response: within 1 hour. Dedicated engineer until resolved
- **P2 — Medium**: Non-critical feature broken, workaround exists, minor performance degradation. Affects <1% of users. Response: within 4 hours. Pull into queue as next priority item
- **P3 — Low**: Cosmetic issue, minor inconvenience, edge case. Response: add to backlog, pull when capacity allows
- Severity is assessed by @Atlas (or the first responder) based on user impact and scope. Escalation: if uncertain, default to one level higher
- On-call: @Sentinel maintains on-call rotation. On-call engineer is first responder for P0/P1. After-hours P0 pages via PagerDuty. P2/P3 wait for business hours
- Every P0/P1 incident gets a post mortem within 48 hours (see crash-investigation.md protocol)

## Technical Debt Tracking

- When an agent discovers tech debt outside their current scope, file it to `docs/tech-debt/backlog.md` with: description, severity (high/medium/low), affected modules, estimated effort, and the discovering agent's name
- Tech debt categories: **Code quality** (duplication, poor naming, missing abstractions), **Testing gaps** (low coverage, missing edge cases), **Architecture** (tight coupling, scalability limits), **Dependencies** (outdated, vulnerable, unmaintained), **Documentation** (missing, stale)
- @Atlas reviews the tech debt backlog weekly during replenishment and ensures 15-20% of WIP capacity goes to debt reduction
- High-severity debt (security vulnerabilities, architectural blockers, reliability risks) is treated as P1 — pulled into the queue immediately
- @Sage reviews architecture-level debt quarterly and proposes refactoring initiatives as RFCs
- Completed debt items are moved to `docs/tech-debt/resolved.md` with the resolution date and approach taken

## Security / Privacy Feature Classification

A **security/privacy feature** is any feature whose job is to protect user data or restrict access — e.g. app lock / biometric gating, encryption or secure storage, authentication/session handling, PII collection or export/deletion, consent management. These MUST NOT enter the codebase through the lightest path (a plain settings toggle, or a stray `expect`/`actual` stub that compiles but is never wired in). A security control that fails **silently** — no crash, no error, no signal — can ship broken and slip every quality gate that keys off errors, line coverage, or happy-path tests, and stay broken for a long time because nothing surfaces it.

When a feature is classified security/privacy, the following are **required before merge** (in addition to the normal Quality Gates):

1. **ADR** — @Sage records an ADR covering the threat it addresses, the platform mechanisms used **and their lifecycle/edge cases** (e.g. process death, backgrounding vs destruction, no-credential devices, token expiry), and the chosen defaults. @Zeyad approves. (Scope: required whenever the feature introduces a new security mechanism or changes a security-relevant default; a trivial tweak to an existing, already-ADR'd control may reference the existing ADR.)
2. **Cross-platform acceptance criteria** — explicit Given/When/Then for **every** platform the feature ships on (Android, iOS, Web, server), including the **negative cases** (disabled, no credential enrolled, backgrounded, cold start, expired/invalid). @Diana/@Apex own these.
3. **Behavioral test coverage** — not just a happy-path unit test. The control's decision logic is extracted into a **pure, unit-tested helper**, and at least one test exercises the real enable→enforce path per platform. A security control with no test is treated as not done.
4. **Observability** — the control emits a no-PII signal when it activates (e.g. prompt-shown / auth-success / auth-failure / skipped-disabled) so that "it silently never runs" is detectable in logs/metrics. A control with no signal is indistinguishable from one that was never built.
5. **Mandatory @Shield review** — regardless of which domain authored it. (This extends the Code Review Matrix's existing auth/encryption/PII rule to the full security/privacy-feature set, and makes the ADR + per-platform tests + observability explicit pre-merge gates.)

**PR checklist (paste into the PR description for any security/privacy feature):**

```
Security/Privacy feature — pre-merge gates:
- [ ] ADR recorded and @Zeyad-approved (or references an existing ADR for an unchanged mechanism)
- [ ] Per-platform acceptance criteria (incl. disabled / no-credential / backgrounded / cold-start)
- [ ] Decision logic extracted to a pure, unit-tested helper
- [ ] At least one per-platform test exercises the real enable→enforce path
- [ ] No-PII observability signal on activate / success / failure / skipped
- [ ] @Shield review completed
```

The implementing agent self-identifies a feature as security/privacy and applies this gate; reviewers (and @Atlas at sync) flag any security/privacy feature that arrived without it.
