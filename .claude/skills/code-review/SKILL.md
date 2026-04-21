---
name: code-review
description: "Perform a structured code review on a PR or branch. Checks architecture alignment, coding standards compliance, test coverage, security concerns, and produces an approval or change-request verdict. Use when the user says 'review this PR', 'code review', 'review this branch', 'check this code', 'review before merge', or 'is this ready to merge'."
---

# Code Review

This skill performs a structured, multi-dimensional code review. It goes beyond "does the code work" to verify that it aligns with architecture decisions, follows coding standards, has adequate test coverage, and doesn't introduce security risks.

## Step 1: Gather Review Context

Determine what to review:

```bash
# If reviewing a branch against main
git log --oneline main..HEAD
git diff --stat main..HEAD
git diff main..HEAD

# If reviewing a specific PR (ask user for branch name or PR number)
git log --oneline main..{branch}
git diff --stat main..{branch}
git diff main..{branch}
```

Then gather project context:

1. **Identify the story/task**: Extract the story ID from commit messages (e.g., `[US-042]`)
2. **Read the acceptance criteria**: Check `board-context.md` for the task description and criteria
3. **Read feature docs**: Load PRD, BRD, ADR, RFC from `docs/{feature-name}/` if they exist
4. **Identify the author agent**: Extract from commit messages (`@AgentName`)
5. **Determine the review scope**: Which platforms, modules, and layers are affected

## Step 2: Architecture Alignment

Check that the implementation follows the project's architectural decisions:

### ADR Compliance

- Read all ADRs in `docs/{feature-name}/adr-*.md`
- Verify the implementation follows the decisions recorded there
- Flag any deviation from an accepted ADR — these require an explicit change request to @Sage

### Layer Violations

- **Clean Architecture**: Does the dependency direction flow correctly? (domain ← data, domain ← presentation)
- **No layer skipping**: Controllers don't call repositories directly, ViewModels don't import data layer types
- **Module boundaries**: No cross-feature imports that bypass the domain layer

### API Contract Compliance

- If the change touches API endpoints, verify they match the OpenAPI spec or shared KMP DTOs
- Check request/response shapes, status codes, error envelopes
- Verify backward compatibility — no breaking changes to existing endpoints without versioning

Report:

```markdown
### Architecture Alignment

| Check | Status | Notes |
|-------|--------|-------|
| ADR compliance | PASS/FAIL | [details] |
| Layer dependencies | PASS/FAIL | [details] |
| Module boundaries | PASS/FAIL | [details] |
| API contract | PASS/FAIL | [details] |
```

## Step 3: Coding Standards Compliance

Load the relevant coding standards based on the affected platform:

- Android: `@.claude/rules/compose-coding-standards.md`
- iOS: `@.claude/rules/swiftui-coding-standards.md`
- KMP: `@.claude/rules/kmp-coding-standards.md`
- Ktor: `@.claude/rules/ktor-server-coding-standards.md`
- React: `@.claude/rules/react-coding-standards.md`
- Node.js: `@.claude/rules/node-coding-standards.md`
- Python: `@.claude/rules/python-coding-standards.md`
- JVM/Spring: `@.claude/rules/jvm-coding-standards.md`

Check for:

| Category | What to Look For |
|----------|-----------------|
| Naming | Classes, functions, files follow the conventions table |
| Structure | Files are in the correct directories per project structure |
| Patterns | Correct use of MVI/MVVM, repository pattern, use cases |
| Error handling | Typed errors, no raw exceptions, global handler used |
| Null safety | No force-unwraps (`!!`, `!`), proper optional handling |
| State management | 4 states (loading/success/empty/error) on every screen |
| DI | Dependencies injected, not constructed inline |
| Code style | Immutability, no `var` where `val` works, proper access modifiers |
| Visual evidence | Before/after screenshots provided for UI changes |

### Visual Evidence Check (UI Changes Only)

If the PR contains UI changes (detect using the same logic as `/capture-screenshots` Step 1):

```bash
UI_CHANGES=$(git diff --name-only main..HEAD | grep -iE '(Screen|Content|Component|View|Composable|Preview|page\.tsx|page\.jsx|layout\.tsx|designsystem|DesignSystem|Theme|Color|Typography|Spacing)' | head -5)
```

If `UI_CHANGES` is non-empty, check:

1. **Visual Changes section exists** in the PR body — look for `## Visual Changes` heading
2. **Before/after images are present** — the section contains actual image references, not just a placeholder or warning
3. **All affected platforms are covered** — if Android files changed, Android screenshots should be included; same for iOS and Web
4. **Key states are shown** — at minimum: the default/loaded state; ideally also dark mode and empty/error states

If visual evidence is missing or incomplete:
- Mark as **CHANGES REQUESTED** with a specific ask: "Add before/after screenshots for the UI changes. Run `/capture-screenshots` to generate them."
- This is a **blocking** requirement, not a recommendation

Report:

```markdown
### Coding Standards

| Category | Status | Issues |
|----------|--------|--------|
| Naming conventions | PASS/WARN/FAIL | [details] |
| Project structure | PASS/WARN/FAIL | [details] |
| Design patterns | PASS/WARN/FAIL | [details] |
| Error handling | PASS/WARN/FAIL | [details] |
| Null safety | PASS/WARN/FAIL | [details] |
| State management | PASS/WARN/FAIL | [details] |
| DI | PASS/WARN/FAIL | [details] |
| Code style | PASS/WARN/FAIL | [details] |
| Visual evidence | PASS/WARN/FAIL/N/A | [details — N/A if no UI changes] |
```

## Step 4: Test Coverage Assessment

Check that the change includes adequate tests:

```bash
# Find test files related to the changed code
git diff --name-only main..HEAD | grep -E '\.kt$|\.swift$|\.ts$|\.tsx$|\.py$' | while read f; do
  test_path=$(echo "$f" | sed 's/src\/main/src\/test/' | sed 's/\.kt$/Test.kt/')
  echo "$f → $test_path ($([ -f "$test_path" ] && echo "EXISTS" || echo "MISSING"))"
done
```

Check:

| Test Type | Required? | Present? |
|-----------|-----------|----------|
| Unit tests for new/changed business logic | Yes | |
| Unit tests for new/changed ViewModels/InputHandlers | Yes | |
| Integration tests for new/changed API endpoints | Yes (if backend) | |
| UI tests for new/changed screens | Recommended | |
| Edge case tests mentioned in acceptance criteria | Yes | |
| Regression test if fixing a bug | Yes | |

Evaluate test quality:
- Do tests follow Given/When/Then structure?
- Do tests verify behavior, not implementation?
- Are tests deterministic and independent?
- Do tests cover error paths, not just happy paths?

Report:

```markdown
### Test Coverage

| Area | Tests Present | Quality | Notes |
|------|--------------|---------|-------|
| Business logic | YES/NO | GOOD/NEEDS WORK | [details] |
| ViewModels | YES/NO | GOOD/NEEDS WORK | [details] |
| API endpoints | YES/NO/N/A | GOOD/NEEDS WORK | [details] |
| UI components | YES/NO | GOOD/NEEDS WORK | [details] |
| Edge cases | YES/NO | GOOD/NEEDS WORK | [details] |
| Error paths | YES/NO | GOOD/NEEDS WORK | [details] |
```

## Step 5: Security Review (Lightweight)

This is not a full @Shield security review — it's a quick scan for common issues:

| Check | What to Look For |
|-------|-----------------|
| Secrets | Hardcoded API keys, passwords, tokens in the diff |
| Input validation | All user inputs validated at the boundary |
| SQL injection | Parameterized queries used (ORM usually handles this) |
| Auth | Protected endpoints require authentication |
| PII | No PII logged or exposed in error responses |
| Dependencies | Any new dependencies with known vulnerabilities |
| Force-unwraps | `!!` (Kotlin) or `!` (Swift) in production code |

**Escalate to @Shield** if the change touches:
- Authentication or authorization logic
- Encryption or key management
- PII handling or data retention
- Third-party data sharing
- Payment processing

Report:

```markdown
### Security (Quick Scan)

| Check | Status | Notes |
|-------|--------|-------|
| No hardcoded secrets | PASS/FAIL | |
| Input validation | PASS/WARN/FAIL | |
| SQL injection safe | PASS/FAIL | |
| Auth on protected routes | PASS/FAIL/N/A | |
| No PII in logs/errors | PASS/WARN | |
| Dependencies | PASS/WARN | |
| Null safety | PASS/WARN | |
| **Needs @Shield review** | YES/NO | [reason if yes] |
```

## Step 6: Acceptance Criteria Verification

Cross-reference the implementation against the acceptance criteria from the BRD or task:

```markdown
### Acceptance Criteria

| # | Criterion | Met? | Evidence |
|---|-----------|------|----------|
| 1 | [criterion from BRD/task] | YES/NO/PARTIAL | [which code/test proves it] |
| 2 | ... | ... | ... |
```

## Step 7: Verdict

Produce the final review report:

```markdown
# Code Review: [Story ID] — [Description]

**Reviewer:** @[YourAgent]
**Author:** @[AuthorAgent]
**Branch:** [branch name]
**Date:** YYYY-MM-DD

## Summary

[1-2 sentence overview of what the change does and overall quality assessment]

## Scores

| Dimension | Score | Notes |
|-----------|-------|-------|
| Architecture alignment | [1-5] | |
| Coding standards | [1-5] | |
| Test coverage | [1-5] | |
| Security | [1-5] | |
| Acceptance criteria | [1-5] | |

## Verdict: [APPROVED / CHANGES REQUESTED / BLOCKED]

### Required Changes (if CHANGES REQUESTED)

[Numbered list of specific, actionable changes the author must make]

1. [File:line] — [What to change and why]
2. ...

### Recommendations (non-blocking)

[Optional improvements that would be nice but don't block merge]

1. ...

### Blocking Issues (if BLOCKED)

[Critical issues that must be resolved — usually security or architecture violations]

1. ...
```

**Verdict criteria:**
- **APPROVED**: All dimensions score 3+, no FAIL on security, acceptance criteria met
- **CHANGES REQUESTED**: Any dimension scores 1-2, or missing tests, or coding standard violations
- **BLOCKED**: Security FAIL, architecture violation of an accepted ADR, or acceptance criteria not met

## Step 8: Follow Up

After producing the review:

1. Save the review to `docs/{feature-name}/review-{story-id}-{date}.md`
2. Tag the author agent and @Atlas with the verdict
3. If BLOCKED, also tag @Sage (architecture issues) or @Shield (security issues)
4. If APPROVED and change is security-sensitive, confirm @Shield has separately reviewed
5. Run `/update-board` to update the board and commit the change:
   - If **APPROVED**: `/update-board {TASK-ID} → Done` — the board commit will be included in the merge
   - If **CHANGES REQUESTED**: task stays in Review (no board update needed)
   - If **BLOCKED**: `/update-board {TASK-ID} → Blocked` with the blocking reason
