---
name: health-check
description: "Run a project health audit — checks test coverage trends, lint warnings, dependency vulnerabilities, dead code, board hygiene, documentation staleness, and produces a health report with action items. Use when the user says 'health check', 'project health', 'audit the project', 'how healthy is the codebase', 'quality check', or 'run diagnostics'."
---

# Project Health Check

This skill runs a comprehensive project health audit. Think of it as a periodic "are we doing things right" scan that catches drift before it becomes technical debt. Run weekly, before a release, or whenever things feel off.

## Step 1: Detect Project Stack

Identify the project's technology stack from file signatures:

```bash
# Detect platforms and tools
ls -la gradlew gradle.properties 2>/dev/null && echo "GRADLE_PROJECT"
ls -la Package.swift 2>/dev/null && echo "SWIFT_PROJECT"
ls -la package.json 2>/dev/null && echo "NODE_PROJECT"
ls -la pyproject.toml requirements.txt 2>/dev/null && echo "PYTHON_PROJECT"
ls -la build.gradle.kts settings.gradle.kts 2>/dev/null && echo "KMP_PROJECT"
cat settings.gradle.kts 2>/dev/null | grep -i "iosArm64\|androidTarget\|wasmJs" && echo "KMP_MULTIPLATFORM"
```

This determines which checks apply.

## Step 2: Code Quality

### 2a. Lint & Static Analysis

Run the project's lint tools and collect results:

```bash
# Kotlin/KMP/Android
./gradlew detekt 2>&1 | tail -20

# Swift/iOS
swiftlint lint --reporter json 2>/dev/null | head -50

# Node.js/React
npx eslint src/ --format json 2>/dev/null | head -50

# Python
ruff check src/ --statistics 2>/dev/null || echo "ruff not configured"
```

Report:

```markdown
### Lint & Static Analysis

| Tool | Errors | Warnings | Status |
|------|--------|----------|--------|
| [tool] | [n] | [n] | PASS/WARN/FAIL |
```

- **PASS**: 0 errors, <10 warnings
- **WARN**: 0 errors, 10+ warnings
- **FAIL**: Any errors

### 2b. Force-Unwraps & Unsafe Code

```bash
# Kotlin !! usage (excluding tests and comments)
grep -rn '!!' --include="*.kt" src/ | grep -v '/test/' | grep -v '// safe:' | wc -l

# Swift ! usage (excluding tests and comments)
grep -rn '[^!]![^=!]' --include="*.swift" Sources/ | grep -v '/Tests/' | grep -v '// safe:' | wc -l
```

### 2c. TODO/FIXME Audit

```bash
# TODOs without story IDs
grep -rn 'TODO\|FIXME' --include="*.kt" --include="*.swift" --include="*.ts" --include="*.tsx" --include="*.py" src/ | grep -v 'TODO(' | grep -v 'FIXME\[' | wc -l

# TODOs with story IDs (good)
grep -rn 'TODO(\|FIXME\[' --include="*.kt" --include="*.swift" --include="*.ts" --include="*.tsx" --include="*.py" src/ | wc -l
```

Report:

```markdown
### Code Hygiene

| Check | Count | Status |
|-------|-------|--------|
| Force-unwraps (Kotlin `!!`) | [n] | [PASS if 0, WARN if 1-5, FAIL if >5] |
| Force-unwraps (Swift `!`) | [n] | [PASS if 0, WARN if 1-5, FAIL if >5] |
| TODOs without story ID | [n] | [PASS if 0, WARN if 1-10, FAIL if >10] |
| TODOs with story ID | [n] | [INFO] |
```

## Step 3: Test Health

### 3a. Test Suite Execution

```bash
# Run tests and capture results
# Kotlin/KMP
./gradlew test 2>&1 | tail -30

# Node.js
npm test -- --reporter=json 2>/dev/null | tail -30

# Python
pytest --tb=no -q 2>/dev/null | tail -10

# Swift
swift test 2>&1 | tail -20
```

### 3b. Coverage Report

```bash
# Kotlin/KMP (if Koverage or JaCoCo configured)
./gradlew koverReport 2>/dev/null && cat build/reports/kover/report.xml 2>/dev/null | head -20

# Node.js
npm test -- --coverage --reporter=json 2>/dev/null | tail -20

# Python
pytest --cov=src --cov-report=term-missing 2>/dev/null | tail -20
```

Report:

```markdown
### Test Health

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Tests passing | [n]/[total] | 100% | PASS/FAIL |
| Core logic coverage | [n]% | 80% | PASS/WARN/FAIL |
| Overall coverage | [n]% | 60% | PASS/WARN/FAIL |
| Flaky tests | [n] | 0 | PASS/WARN |
```

### 3c. Missing Test Coverage

Identify code areas with no tests:

```bash
# Find source files with no corresponding test file
find src/main -name "*.kt" -o -name "*.ts" -o -name "*.py" | while read f; do
  base=$(basename "$f" | sed 's/\.\(kt\|ts\|py\)$//')
  test_count=$(find . -name "*${base}*Test*" -o -name "*${base}*test*" -o -name "test_*${base}*" 2>/dev/null | wc -l)
  if [ "$test_count" -eq 0 ]; then
    echo "NO TESTS: $f"
  fi
done | head -20
```

## Step 4: Dependency Health

### 4a. Vulnerability Scan

```bash
# Node.js
npm audit --json 2>/dev/null | head -30

# Python
pip-audit 2>/dev/null || echo "pip-audit not installed"

# Kotlin/Gradle
./gradlew dependencyCheckAnalyze 2>/dev/null || echo "OWASP check not configured"
```

### 4b. Outdated Dependencies

```bash
# Node.js
npm outdated --json 2>/dev/null | head -30

# Python
pip list --outdated 2>/dev/null | head -20

# Kotlin (if dependency updates plugin configured)
./gradlew dependencyUpdates 2>/dev/null | tail -20
```

Report:

```markdown
### Dependency Health

| Check | Count | Status |
|-------|-------|--------|
| Critical vulnerabilities | [n] | [PASS if 0, FAIL if >0] |
| High vulnerabilities | [n] | [PASS if 0, WARN if 1-2, FAIL if >2] |
| Outdated (major) | [n] | [WARN if >0] |
| Outdated (minor/patch) | [n] | [INFO] |
```

## Step 5: Board Hygiene

Read the board through the adapter, not the file (`@.claude/rules/shared/board-adapter.md` rule 2) — check `board_backend` in `.claude/settings.json` (absent → `markdown`), then run `board.read_all()`.

Check:

| Check | What to Look For |
|-------|-----------------|
| Stale In Progress | Tasks in "In Progress" for >5 days |
| WIP violations | Agents with >2 items in progress |
| Orphaned tasks | Tasks with no assignee in In Progress |
| Missing acceptance criteria | Ready tasks without clear criteria |
| Blocked items age | Items in Blocked for >3 days |
| Done without handoff | Completed tasks missing handoff reference |

Report:

```markdown
### Board Hygiene

| Check | Count | Status |
|-------|-------|--------|
| Stale tasks (>5 days in progress) | [n] | [PASS if 0, WARN if 1-2, FAIL if >2] |
| WIP violations | [n] agents | [PASS if 0, FAIL if >0] |
| Orphaned tasks | [n] | [PASS if 0, WARN if >0] |
| Missing acceptance criteria | [n] | [PASS if 0, WARN if >0] |
| Long-blocked items (>3 days) | [n] | [PASS if 0, WARN if >0] |
```

## Step 6: Documentation Staleness

```bash
# Check when key docs were last modified
# board-context.md is only a live doc on the `markdown` backend. After
# /migrate-board it is frozen history and will always read as stale, so it is
# excluded unless that backend is configured.
DOCS="CLAUDE.md docs/guides/setup-guide.md docs/guides/migration-guide.md"
grep -q '"board_backend": *"markdown"' .claude/settings.json 2>/dev/null \
  && DOCS="$DOCS board-context.md"

for doc in $DOCS; do
  if [ -f "$doc" ]; then
    mod_date=$(git log -1 --format="%ai" -- "$doc" 2>/dev/null || echo "untracked")
    echo "$doc: last modified $mod_date"
  fi
done

# Check for features with missing docs
ls docs/ | while read dir; do
  if [ -d "docs/$dir" ]; then
    has_prd=$([ -f "docs/$dir/prd.md" ] && echo "Y" || echo "N")
    has_brd=$([ -f "docs/$dir/brd.md" ] && echo "Y" || echo "N")
    has_adr=$(ls docs/$dir/adr-*.md 2>/dev/null | wc -l)
    echo "$dir: PRD=$has_prd BRD=$has_brd ADRs=$has_adr"
  fi
done
```

### Feature Flag Cleanup

```bash
# Find feature flags that might be stale (>4 weeks at 'on')
grep -rn 'ff_' --include="*.kt" --include="*.swift" --include="*.ts" --include="*.tsx" --include="*.py" src/ | head -20
```

Report:

```markdown
### Documentation & Flags

| Check | Status | Notes |
|-------|--------|-------|
| CLAUDE.md up to date | [PASS/WARN] | Last modified: [date] |
| Board context current | [PASS/WARN] | Last modified: [date] |
| Features with missing docs | [n] | [list] |
| Stale feature flags (>4 weeks on) | [n] | [list] |
```

## Step 7: Git Hooks & CI

```bash
# Check hooks are installed
ls -la .git/hooks/pre-commit .git/hooks/commit-msg .git/hooks/pre-push 2>/dev/null

# Check CI workflows exist
ls -la .github/workflows/ 2>/dev/null || ls -la .gitlab-ci.yml 2>/dev/null
```

Report:

```markdown
### Infrastructure

| Check | Status |
|-------|--------|
| Pre-commit hook installed | [YES/NO] |
| Commit-msg hook installed | [YES/NO] |
| Pre-push hook installed | [YES/NO] |
| CI/CD workflows present | [YES/NO] |
```

## Step 8: Health Report Summary

Compile the full report:

```markdown
# Project Health Report — [date]

## Overall Score: [A/B/C/D/F]

### Scoring
- **A**: All checks PASS, no WARN
- **B**: All checks PASS, some WARN
- **C**: 1-2 FAIL, several WARN
- **D**: 3+ FAIL
- **F**: Critical security vulnerabilities or tests failing

## Summary

| Area | Score | Critical Issues |
|------|-------|-----------------|
| Code quality | [A-F] | [summary] |
| Test health | [A-F] | [summary] |
| Dependency health | [A-F] | [summary] |
| Board hygiene | [A-F] | [summary] |
| Documentation | [A-F] | [summary] |
| Infrastructure | [A-F] | [summary] |

## Action Items (prioritized)

### P0 — Fix Immediately
[Critical vulnerabilities, failing tests, security issues]

### P1 — Fix This Sprint
[Test coverage gaps, WIP violations, stale blocked items]

### P2 — Fix This Month
[Outdated dependencies, documentation gaps, lint warnings]

### P3 — Backlog
[Code hygiene, feature flag cleanup, nice-to-haves]
```

## Step 9: Create Board Tasks

For every P0 and P1 action item, create a task via `board.create_task()` (`@.claude/rules/shared/board-adapter.md`):

- P0 items → Ready column immediately, with `board.assign_task()` to the appropriate agent
- P1 items → Backlog with a priority marker
- P2/P3 items → also `board.create_task()`, labelled `tech-debt` with the severity. On `github` tech debt lives on the board like any other work, which is what lets `/replenish` pull it by label. Only on `markdown` does it go to `docs/guides/tech-debt/backlog.md`.

Tag @Atlas to review the new tasks at the next daily sync.

Save the full report to `docs/artifacts/health-report/YYYY-MM-DD.md`.
