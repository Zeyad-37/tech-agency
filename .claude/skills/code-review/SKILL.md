---
name: code-review
description: "Perform a structured code review on a PR or branch. Checks architecture alignment, coding standards compliance, test coverage, security concerns, and produces an approval or change-request verdict. When invoked in the same conversation that wrote the code, the review runs in a fresh-context subagent (diff-only, no implementation memory) to stay unbiased. The review is posted directly as a comment on the PR — no Markdown file is written to the repo. Use when the user says 'review this PR', 'code review', 'review this branch', 'check this code', 'review before merge', or 'is this ready to merge'."
---

# Code Review

This skill performs a structured, multi-dimensional code review. It goes beyond "does the code work" to verify that it aligns with architecture decisions, follows coding standards, has adequate test coverage, and doesn't introduce security risks.

## Step 0: Run the Review in a Fresh Context (mandatory)

A reviewer who carries the implementation conversation in context is biased — it already "knows" why each choice was made and tends to rubber-stamp its own work. The review MUST be performed by an agent that has no memory of how the code was written and sees **only the diff**.

**If this skill was invoked inside a conversation that also planned or wrote the code under review** (e.g. directly after implementing, or as part of `/ship-it`), do not review inline. Instead spawn a fresh subagent and have it run Steps 1–9. Use the `Agent` tool with `subagent_type: general-purpose` (or a dedicated reviewer agent if the project defines one):

```
Prompt to the subagent:
  You are performing an unbiased code review. You have NO prior context —
  review only what is in the diff and the project's committed docs/standards.
  Do not assume any rationale that is not evidenced in the code or docs.

  1. Run `git diff main..HEAD` (or the branch/PR the user named) to see the change.
  2. Read board-context.md to find the task ID and acceptance criteria.
  3. Locate feature docs in docs/{prd,brd,adr,rfc,design-spec}/ matching the task ID.
  4. Apply every step of the /code-review skill (Steps 1–9 in
     .claude/skills/code-review/SKILL.md), including posting the verdict to the PR.
  5. Return the verdict and the list of findings.
```

Then relay the subagent's verdict to the user. The orchestrating agent does not second-guess or soften the findings — it reports them as-is.

**If this skill was invoked in a clean/standalone session** (the reviewer did not plan or write this code — e.g. a reviewer agent picking up a PR cold), there is no bias to clear: proceed directly with Steps 1–9 inline.

When in doubt about whether the current context is "tainted," prefer the subagent path — a fresh review is never wrong, only slightly slower.

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

Resolve the target PR number now — the verdict will be posted there in Step 8:

```bash
# PR for the current branch, or pass an explicit number if the user gave one
PR_NUMBER=$(gh pr view --json number -q .number 2>/dev/null)
echo "Target PR: ${PR_NUMBER:-<none — see Step 8 fallback>}"
```

If no PR exists for the branch yet, note it — Step 8 explains the fallback (create the PR first, or print the review inline).

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

## Step 8: Post the Review to the PR

The review verdict from Step 7 is posted **directly as a comment on the PR**. Do NOT write a Markdown file into the repo — no `docs/.../review-*.md`, nothing added to the working tree or any commit.

Write the full Step 7 report to a temp file (keeps Markdown intact, avoids shell-quoting issues) and post it with `gh`:

```bash
REVIEW_BODY_FILE=$(mktemp /tmp/code-review-XXXXXX.md)
# ... write the complete Step 7 report into "$REVIEW_BODY_FILE" ...

case "$VERDICT" in
  APPROVED)
    gh pr review "$PR_NUMBER" --approve --body-file "$REVIEW_BODY_FILE" ;;
  "CHANGES REQUESTED"|BLOCKED)
    gh pr review "$PR_NUMBER" --request-changes --body-file "$REVIEW_BODY_FILE" ;;
  *)
    gh pr review "$PR_NUMBER" --comment --body-file "$REVIEW_BODY_FILE" ;;
esac

rm -f "$REVIEW_BODY_FILE"
```

Notes:
- `gh pr review` maps the verdict to GitHub's review states: APPROVED → approve, CHANGES REQUESTED/BLOCKED → request-changes (GitHub has no "blocked" state — the body text carries the BLOCKED designation and blocking issues).
- The temp file lives in `/tmp`, never inside the repo, and is deleted after posting.
- **Fallback — `gh pr review` rejects self-review** ("Can not request changes / approve your own pull request"): post the same body as a regular issue comment instead, so the review is still recorded on the PR:
  ```bash
  gh pr comment "$PR_NUMBER" --body-file "$REVIEW_BODY_FILE"
  ```
- **Fallback — no PR exists for the branch** (`PR_NUMBER` is empty from Step 1): do not create a file. Either run `/create-pr` first and then post, or, if the user only wanted the review, output the full report inline in the response and tell them no PR was found to post to.

After posting:

1. Tag the author agent and @Atlas with the verdict (in the PR comment body or the response).
2. If BLOCKED, also tag @Sage (architecture issues) or @Shield (security issues).
3. If APPROVED and the change is security-sensitive, confirm @Shield has separately reviewed.
4. Run `/update-board` to update the board and commit that board change:
   - If **APPROVED**: `/update-board {TASK-ID} → Done` — the board commit will be included in the merge
   - If **CHANGES REQUESTED**: task stays in Review (no board update needed)
   - If **BLOCKED**: `/update-board {TASK-ID} → Blocked` with the blocking reason
