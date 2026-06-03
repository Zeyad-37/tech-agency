---
name: dependency-upgrade
description: "Evaluate and upgrade project dependencies — vulnerability patches, minor/major version bumps, Kotlin version upgrades. Handles risk assessment, cross-platform testing coordination (KMP), and rollback planning. Use when the user says 'upgrade dependencies', 'update packages', 'vulnerability fix', 'outdated dependencies', 'bump kotlin version', 'dependency audit', or 'security patch'."
---

# Dependency Upgrade

This skill manages the full lifecycle of a dependency upgrade: audit, risk assessment, upgrade execution, cross-platform verification, and rollback planning. It's especially important for KMP projects where a single dependency change can break iOS, Android, Web, and Server targets.

## Step 1: Audit Current State

Identify what needs upgrading:

```bash
# Kotlin/KMP/Gradle
./gradlew dependencyUpdates 2>/dev/null | tail -40
./gradlew dependencyCheckAnalyze 2>/dev/null | tail -20

# Node.js
npm outdated --json 2>/dev/null | head -40
npm audit --json 2>/dev/null | head -40

# Python
pip list --outdated 2>/dev/null | head -20
pip-audit 2>/dev/null | head -20

# Swift
swift package update --dry-run 2>/dev/null | head -20
```

Produce:

```markdown
## Dependency Audit — [date]

### Vulnerabilities (fix immediately)

| Package | Current | Fixed In | Severity | CVE |
|---------|---------|----------|----------|-----|
| ... | ... | ... | Critical/High/Medium | CVE-XXXX-XXXX |

### Outdated (major)

| Package | Current | Latest | Breaking Changes? |
|---------|---------|--------|-------------------|
| ... | ... | ... | [Yes — see changelog] |

### Outdated (minor/patch)

| Package | Current | Latest | Risk |
|---------|---------|--------|------|
| ... | ... | ... | Low |
```

## Step 2: Classify and Prioritize

Classify each upgrade by urgency:

| Category | SLA | Examples |
|----------|-----|---------|
| **P0 — Critical vulnerability** | Within 48 hours | CVSS >= 9.0, actively exploited |
| **P1 — High vulnerability** | Within 1 week | CVSS 7.0-8.9 |
| **P2 — Major version bump** | Evaluate this sprint | New major version of a core dependency |
| **P3 — Minor/patch updates** | Monthly batch | Non-breaking improvements |
| **P4 — Kotlin version upgrade** | Coordinate with all platforms | Requires KMP-wide testing |

**Decision gate:**

- P0/P1 vulnerabilities → proceed immediately, skip to Step 4
- P2 major bumps → proceed to Step 3 (risk assessment)
- P3 minor/patch → batch together, skip to Step 4
- P4 Kotlin upgrade → proceed to Step 3 with full KMP coordination

## Step 3: Risk Assessment (Major Bumps & Kotlin Upgrades)

For major version bumps and Kotlin upgrades, assess the risk before proceeding:

### 3a. Read the Changelog

```bash
# Check the changelog or release notes
# For Gradle dependencies, check Maven Central or GitHub releases
# For npm, check the package's CHANGELOG.md or GitHub releases
```

Document:

```markdown
### Risk Assessment: {package} {current} → {target}

**Breaking changes:**
- [List specific breaking changes from the changelog]

**Migration required:**
- [List code changes needed — API renames, removed features, new patterns]

**Affected modules:**
- [List which project modules import this dependency]

**Affected platforms (KMP):**
- [Android / iOS / Web / Server / All]

**Estimated effort:** Small / Medium / Large

**Recommendation:** Proceed / Defer / Skip with reason
```

### 3b. Check Ecosystem Compatibility (KMP)

For Kotlin version upgrades or KMP dependencies:

```bash
# Check if all KMP plugins support the target Kotlin version
cat gradle/libs.versions.toml | grep -i kotlin
cat build.gradle.kts | grep -i kotlin

# Check Compose Multiplatform compatibility
# Check Ktor version compatibility
# Check kotlinx-serialization compatibility
# Check Room/SQLDelight compatibility
```

**Kotlin upgrade rule** (from `operational-standards.md`): Kotlin version upgrades require coordinated testing across iOS, Android, and backend targets. @Link owns the upgrade, @Swift and @Kai verify integration.

### 3c. Write ADR (if major)

For significant upgrades (Kotlin version, framework major bump), write an ADR per `shared-standards.md`:

```markdown
# ADR-XXX: Upgrade {dependency} from {old} to {new}

## Status: Proposed

## Context
[Why we need to upgrade — vulnerability, feature need, EOL]

## Decision
[Upgrade to version X. Migration steps.]

## Consequences
[Breaking changes, required code modifications, testing impact]

## Alternatives Considered
1. Stay on current version — [risk: vulnerability / EOL / missing features]
2. Switch to alternative library — [trade-offs]
```

Save to `docs/{feature-or-infra}/adr-XXX-upgrade-{package}.md`. Get @Zeyad approval before proceeding.

## Step 4: Execute the Upgrade

### 4a. Create a Branch

Always branch from the latest `origin/main`, never from the currently checked-out branch:

```bash
git fetch origin main
git checkout -b deps/{package}-{version} origin/main
# Or for batched minor updates:
git checkout -b deps/monthly-update-{date} origin/main
```

### 4b. Apply the Upgrade

**Kotlin/Gradle (version catalog):**
```bash
# Edit gradle/libs.versions.toml
# Update the version entry
# Run sync
./gradlew --refresh-dependencies
```

**Node.js:**
```bash
# Single package
npm install {package}@{version}
# Or for all minor/patch
npm update
# Lock file must be committed
```

**Python:**
```bash
# Update pyproject.toml or requirements.txt
pip install {package}=={version} --break-system-packages
# Regenerate lock file
pip freeze > requirements.lock
```

### 4c. Fix Compilation Errors

After upgrading, fix any compilation errors introduced by the new version:

1. Read the migration guide from the changelog
2. Apply required code changes
3. Follow the project's coding standards for the affected platform

### 4d. Run Tests

```bash
# Kotlin/KMP — ALL targets
./gradlew test
./gradlew :androidApp:test
./gradlew :iosTest  # if configured
./gradlew :server:test

# Node.js
npm test

# Python
pytest
```

**All tests must pass before proceeding.**

## Step 5: Cross-Platform Verification (KMP)

If the upgrade affects KMP shared code (`commonMain` dependencies, Kotlin version, or kotlinx libraries):

```markdown
### Cross-Platform Verification Required

| Platform | Agent | Status | Notes |
|----------|-------|--------|-------|
| Android | @Kai | [ ] | Run full test suite + build |
| iOS | @Swift | [ ] | Run full test suite + framework build |
| Web | @Nova | [ ] | Run web target tests (if applicable) |
| Server | @Link | [ ] | Run Ktor server tests (if applicable) |
```

Follow the cross-platform testing coordination rules from `kmp-coding-standards.md`:

1. Tag @Swift and @Kai for review
2. CI must build and test ALL targets
3. All platform agents must approve before merge

## Step 6: Commit and PR

```bash
git add gradle/libs.versions.toml  # or package.json, requirements.txt
git add -A  # include code changes for migration
git commit -m "[DEPS-XXX] @{YourAgent}: Upgrade {package} from {old} to {new}

Reason: {vulnerability fix / major upgrade / monthly patch batch}
Breaking changes: {none / list}
Migration: {none / list of code changes}"
```

Create a PR with:

```markdown
## Dependency Upgrade: {package} {old} → {new}

**Reason:** {vulnerability CVE-XXXX / major version upgrade / monthly maintenance}
**Risk:** {Low / Medium / High}
**Breaking changes:** {None / List}

### Changes
- Updated {package} from {old} to {new}
- [Migration changes if any]

### Test Results
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] Cross-platform build verification (KMP)
- [ ] No performance regressions

### Rollback Plan
Revert this PR: `git revert {commit-hash}`
```

## Step 7: Rollback Plan

Every dependency upgrade must have a documented rollback:

```markdown
### Rollback

1. Revert the commit: `git revert {hash}`
2. Regenerate lock file: `./gradlew --refresh-dependencies` / `npm install` / `pip install -r requirements.txt`
3. Run tests to verify rollback: `./gradlew test` / `npm test` / `pytest`
4. If the vulnerability was critical, document that the rollback reintroduces it and create a P0 task to find an alternative fix
```

## Step 8: Post-Upgrade Tasks

After merge:

1. **Update board**: Mark the upgrade task as Done in `board-context.md`
2. **Monitor**: Watch error rates and crash-free rates for 24 hours post-deploy
3. **Clean up**: If a major upgrade introduced deprecation warnings, create follow-up tasks for cleanup
4. **Document**: For Kotlin version upgrades, update `docs/kotlin-upgrade-history.md` (create if missing) with the version, date, and any issues encountered

## Batch Update Template

For monthly minor/patch batches:

```markdown
## Monthly Dependency Update — [date]

### Updated

| Package | From | To | Type |
|---------|------|----|------|
| ... | ... | ... | patch/minor |

### Skipped (requires evaluation)

| Package | From | Available | Reason |
|---------|------|-----------|--------|
| ... | ... | ... | Major bump — needs ADR |

### Vulnerabilities Resolved

| Package | CVE | Severity | Fixed In |
|---------|-----|----------|----------|
| ... | ... | ... | ... |

All tests passing. No breaking changes.
```
