# CI Enforcement Policy

This document defines which quality gates are mandatory (blocking) in CI, their thresholds, and the timeline for adoption.

## Gate Definitions

### Tier 1 — Always Blocking (from day one)

These gates MUST pass before any PR can merge to `main`. No exceptions without @Zeyad approval.

| Gate | Tool | Threshold | Applies To |
|------|------|-----------|------------|
| **Lint** | ktlint, ESLint, Black, SwiftLint, detekt | Zero errors | All code |
| **Format** | Prettier, Spotless, Black, SwiftFormat | Zero violations | All code |
| **Build** | Gradle, npm, pip, xcodebuild | Must compile | All code |
| **Unit tests** | JUnit, Vitest, pytest, XCTest, kotlin.test | 100% pass | All code |
| **Security: Critical CVEs** | OWASP dependency-check, npm audit, pip-audit, Snyk | Zero CRITICAL (CVSS >= 9.0) | All dependencies |

### Tier 2 — Blocking After Baseline (within 2 weeks of adoption)

These gates become blocking once the initial baseline is established.

| Gate | Tool | Threshold | Applies To |
|------|------|-----------|------------|
| **Security: High CVEs** | OWASP dependency-check, npm audit, pip-audit | Zero HIGH+ (CVSS >= 7.0) | All dependencies |
| **Integration tests** | Testcontainers, MockWebServer, Fastify inject | 100% pass | All PR-affecting modules |
| **Static analysis** | detekt, ESLint security rules, Bandit, SpotBugs | Zero errors (warnings allowed) | All code |
| **Code coverage (floor)** | JaCoCo, Istanbul/c8, coverage.py, Koverage | No regression below current baseline | Changed files |

### Tier 3 — Blocking at Maturity (within 4 weeks)

| Gate | Tool | Threshold | Applies To |
|------|------|-----------|------------|
| **Code coverage (target)** | JaCoCo, Istanbul/c8, coverage.py | 80%+ services, 60%+ overall | All code |
| **Screenshot tests** | Paparazzi, swift-snapshot-testing, Playwright | Golden images match (0.1% tolerance) | UI components |
| **Accessibility** | axe-core, Compose semantics, XCUITest | Zero critical/serious violations | UI code |
| **Performance (web)** | Lighthouse CI | LCP < 2.5s, CLS < 0.1, bundle < 150KB gz | Web pages |
| **Architecture** | Konsist, ArchUnit, ESLint import rules | Zero violations | Module boundaries |

### Tier 4 — Blocking at Release Only

These gates run on every PR for visibility but only block release builds.

| Gate | Tool | Threshold | Applies To |
|------|------|-----------|------------|
| **E2E tests** | Playwright, Maestro, XCUITest | 100% pass | Critical user flows |
| **Load tests** | k6, Gatling, Locust | P95 < 500ms, P99 < 1000ms, error < 1% | API endpoints |
| **OWASP ZAP** | OWASP ZAP | Zero high-severity findings | Staging environment |
| **Contract tests** | Pact, Spring Cloud Contract, Schemathesis | 100% pass | API contracts |

## Coverage Ratchet Mechanism

Coverage thresholds increase over time to prevent regression and encourage improvement:

1. **Baseline measurement**: On adoption, measure current coverage. Record in `docs/test-baseline.md`.
2. **Floor enforcement**: CI fails if coverage drops below the baseline for any module.
3. **Ratchet increment**: Every 2 weeks, increase the floor by 2% until the target is reached.
4. **Per-module tracking**: Each module has its own threshold. New modules start at the coding standard targets (80%/60%).
5. **Exceptions**: If a module genuinely cannot meet the target (e.g., generated code, thin wrappers), document the exception in `docs/test-exceptions.md` with justification. @Sage and @Zeyad must approve.

## PR Quality Gate Workflow

The `verify-prs.yml` GitHub Actions workflow runs on every pull request to `main`:

```
PR opened/updated
  ├── Lint & Format check
  ├── Build (all affected platforms)
  ├── Unit tests
  ├── Integration tests
  ├── Security scan (dependency + static analysis)
  ├── Coverage check (against ratchet floor)
  ├── Screenshot tests (if UI changed)
  ├── Accessibility tests (if UI changed)
  └── Architecture enforcement (if module boundaries touched)

All must pass → PR is mergeable
Any failure → PR is blocked with clear error message
```

## Verify-Main Workflow

The `verify-main.yml` workflow runs on every push to `main` (post-merge):

```
Push to main
  ├── Full test suite (all tiers, all platforms)
  ├── Build artifacts
  ├── Coverage report (uploaded to dashboard)
  └── On failure → Slack notification to team channel
```

## Release Workflow

The `release-on-tag.yml` workflow runs on `v*.*.*` tag pushes:

```
Tag pushed
  ├── Validate: tag is on main, version is valid semver
  ├── Full test suite (all tiers)
  ├── Security audit (full OWASP ZAP if applicable)
  ├── Load tests (against staging)
  ├── E2E tests (full suite)
  ├── Build & publish artifacts
  ├── Create GitHub Release with auto-changelog
  └── Deploy (staging → canary → production)
```

## Hotfix Workflow

Hotfix branches (`hotfix/**`) are validated by `verify-prs.yml` (same as regular PRs) with an expedited review process:

```
Hotfix branch push
  ├── Lint & build
  ├── Unit + integration tests (affected modules only)
  ├── Focused regression tests
  ├── Quick security scan (dependencies only)
  └── Build artifacts (ready for expedited deploy)
```

## Exception Process

If a quality gate must be bypassed for an emergency:

1. The engineer documents the reason in the PR description.
2. @Shield (for security gates) or @Apex (for test gates) acknowledges the risk.
3. @Zeyad approves the exception.
4. A follow-up task is created in `board-context.md` to restore the gate within 48 hours.
5. The exception is logged in `docs/ci-exceptions-log.md` with date, gate bypassed, reason, and resolution date.

Exceptions are never silent. Every bypass is tracked and resolved.

## Threshold Tuning

Thresholds in this document are starting points. They should be tuned per project:

- **Stricter** for high-traffic production services, financial data handling, healthcare, or public-facing APIs.
- **Slightly relaxed** for internal tools, prototypes, or exploration-phase projects — but never below Tier 1.

Changes to thresholds require @Sage review and @Zeyad approval. Document changes in an ADR.
