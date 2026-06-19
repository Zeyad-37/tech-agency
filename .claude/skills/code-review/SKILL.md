---
name: code-review
description: "Perform a structured code review on a PR or branch. Checks architecture alignment, coding standards compliance, test coverage, security concerns, and produces an approval or change-request verdict. Every invocation runs in a fresh-context subagent (diff-only, no session memory) so the current conversation can never bias the verdict. The review is posted directly on the PR as one GitHub review carrying both the summary verdict and inline comments on the specific flagged file lines — no Markdown file is written to the repo. Use when the user says 'review this PR', 'code review', 'review this branch', 'check this code', 'review before merge', or 'is this ready to merge'."
---

# Code Review

This skill performs a structured, multi-dimensional code review. It goes beyond "does the code work" to verify that it aligns with architecture decisions, follows coding standards, has adequate test coverage, and doesn't introduce security risks.

## Step 0: Run the Review in a Fresh Context (mandatory, unconditional)

A reviewer who carries the session conversation in context is biased — it already "knows" why each choice was made and tends to rubber-stamp its own work. The review MUST be performed by an agent that has no memory of the current session and sees **only the diff** plus the project's committed docs.

**Always run the review in a fresh-context subagent — every invocation, no exceptions.** Do not review inline, even if the current session looks "clean." The point is a guaranteed clean slate that never includes this conversation, so the verdict cannot be influenced by anything said or done in the session. Spawn the subagent with the `Agent` tool using `subagent_type: general-purpose` (or a dedicated reviewer agent if the project defines one):

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

Then relay the subagent's verdict to the user verbatim. The orchestrating agent does not second-guess or soften the findings — it reports them as-is.

The only thing the orchestrating agent passes to the subagent is the review target (branch name or PR number the user named, defaulting to the current branch vs `main`). It passes **no** rationale, summary, or "what we did" narrative from the session — that narrative is exactly the bias being excluded.

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
| T-013 render decisions | UI decisions use typed structures (sealed state, polymorphic props), not `if`/`else` over scalars — see T-013 check below |

### T-013 Typed-Render-Decisions Compliance (UI Changes Only)

Per T-013, every UI render decision must resolve to a typed structure — a sealed type, a polymorphic property, or a sealed component-prop type — never an `if`/`else` chain over scalar fields (see `@.claude/rules/shared/shared-standards.md` "UI Render Decisions Belong to Typed Structures"). The principle is platform-agnostic; the enforcement plumbing is platform-specific — Compose/KMP enforce it via Konsist + custom Detekt rules, and those rules ship without a baseline, so any new violation is a CI failure, not a soft warning.

Reviewer checklist (skip if the PR has no UI changes):

1. **Rule (a) — `*State` types must be sealed.** A State type with multiple data-driven shapes (loading/empty/error/success) must be a sealed hierarchy with an exhaustive `when`/`switch` at the screen root, not parallel `isLoading`/`isEmpty` flags.
2. **Rule (b) — no domain type-checks in feature UI.** An `is *PM` / `is *Domain` discriminator at a UI call site should be a polymorphic property on the domain type instead. Accept an inline allow-list marker (`// type-discriminator-needed: <reason>`) only if the domain refactor is genuinely out of scope.
3. **Rule (c) — no variant Booleans on design-system components.** Patterns like `useXStyle` / `isXVariant` / `*Mode: Boolean` should be a sealed/enum prop type. Accept `// component-boolean-justified: <reason>` only for a genuine binary choice where a sealed type would be heavier than the smell.
4. **Rule (d) — no 3+ parallel `show*: Boolean` props on a `*State`.** Collapse mutually-exclusive sub-state into a single sealed field (e.g. `dialog: ActiveDialog?`); see the project's `*Contract.kt` for the reference pattern.

Any allow-list marker added in a PR requires the reviewer to evaluate whether the deferral is justified — markers are "I know, here's why," not free passes.

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

### Record a location for every actionable finding

In addition to listing findings in the report, capture each actionable finding (Required Change, Blocking Issue, or location-specific Recommendation) as a structured record so Step 8 can post it **inline on the file**:

```
{ path, line, side, severity, body }
```

- `path` — repo-relative file path exactly as it appears in the diff (e.g. `app/src/main/kotlin/.../NotesViewModel.kt`).
- `line` — the line number in the **new** version of the file (the right side of the diff). For a finding about a *removed* line, use the old-file line number and set `side: "LEFT"`.
- `side` — `"RIGHT"` for added/context lines (default), `"LEFT"` for removed lines.
- `severity` — `required`, `blocking`, or `recommended` (prefix the inline body with this, e.g. `**[required]**`).
- `body` — the specific, actionable comment for that line.

**A finding can only be posted inline if its line is part of the diff.** Confirm with `gh pr diff "$PR_NUMBER"` (or the `git diff` from Step 1). Findings that refer to code *outside* the diff (e.g. "you should have also changed X elsewhere") can't be anchored — keep those in the summary body only. Every inline finding must also remain in the summary report, so the report stays a complete standalone record.

## Step 8: Post the Review to the PR (summary + inline comments)

The review is posted **directly on the PR** as a single GitHub review that carries **both** the summary report (the review body) **and** an inline comment on each file/line from Step 7's findings. Do NOT write a Markdown file into the repo — no `docs/.../review-*.md`, nothing added to the working tree or any commit.

A single review combining body + inline comments is created via the REST reviews endpoint (`gh pr review` cannot attach inline comments, so use `gh api`).

```bash
OWNER_REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)

# 1. Summary body — the full Step 7 report. Temp file keeps Markdown intact.
REVIEW_BODY_FILE=$(mktemp /tmp/code-review-XXXXXX.md)
# ... write the complete Step 7 report into "$REVIEW_BODY_FILE" ...

# 2. Inline comments — one object per actionable finding that anchors to a diff line
#    (built from the {path,line,side,severity,body} records captured in Step 7).
#    Prefix each body with its severity. Findings not anchorable to the diff are
#    omitted here and remain in the summary body only.
COMMENTS_JSON=$(jq -n '[
  { path: "app/.../NotesViewModel.kt", line: 42, side: "RIGHT",
    body: "**[required]** NPE when `user` is null — guard with `?: return`." },
  { path: "app/.../NotesApi.kt",       line: 10, side: "RIGHT",
    body: "**[recommended]** Hardcoded base URL — move to `BuildConfig.API_BASE_URL`." }
]')
# If there are no anchorable findings, use:  COMMENTS_JSON='[]'

# 3. Map the verdict to a review event.
case "$VERDICT" in
  APPROVED)              EVENT=APPROVE ;;
  "CHANGES REQUESTED"|BLOCKED) EVENT=REQUEST_CHANGES ;;
  *)                     EVENT=COMMENT ;;
esac

# 4. Assemble the payload and submit one review (body + inline comments together).
PAYLOAD=$(mktemp /tmp/code-review-payload-XXXXXX.json)
jq -n --rawfile body "$REVIEW_BODY_FILE" --arg event "$EVENT" --argjson comments "$COMMENTS_JSON" \
  '{body: $body, event: $event, comments: $comments}' > "$PAYLOAD"

gh api -X POST "repos/$OWNER_REPO/pulls/$PR_NUMBER/reviews" --input "$PAYLOAD"

rm -f "$REVIEW_BODY_FILE" "$PAYLOAD"
```

Notes:
- One review carries everything: the summary in the body and a threaded comment on each flagged line, so the author sees the specific ask in context **and** the overall verdict.
- `event` maps the verdict to GitHub's review states: APPROVED → `APPROVE`, CHANGES REQUESTED/BLOCKED → `REQUEST_CHANGES` (GitHub has no "blocked" state — the body text carries the BLOCKED designation and blocking issues), anything else → `COMMENT`.
- Inline `line` values MUST fall on lines that are part of the diff, or the API rejects the whole review. If a `comments` entry is rejected, drop that entry back to the summary body and re-submit. When in doubt, anchor to a line you can see in `gh pr diff "$PR_NUMBER"`.
- All temp files live in `/tmp`, never inside the repo, and are deleted after posting.
- **Fallback — self-review** ("Can not request changes / approve your own pull request"): GitHub blocks `APPROVE`/`REQUEST_CHANGES` on your own PR but **allows `COMMENT`**. Re-submit the same payload with `EVENT=COMMENT` — this keeps every inline comment and the full summary body; the verdict text inside the body still records the real APPROVED/CHANGES-REQUESTED/BLOCKED designation. (Only if even the `COMMENT` review fails, fall back to a plain `gh pr comment "$PR_NUMBER" --body-file "$REVIEW_BODY_FILE"`, which loses inline anchoring but still records the review.)
- **Fallback — no PR exists for the branch** (`PR_NUMBER` is empty from Step 1): do not create a file. Either run `/create-pr` first and then post, or, if the user only wanted the review, output the full report inline in the response and tell them no PR was found to post to.

After posting:

1. Tag the author agent and @Atlas with the verdict (in the PR comment body or the response).
2. If BLOCKED, also tag @Sage (architecture issues) or @Shield (security issues).
3. If APPROVED and the change is security-sensitive, confirm @Shield has separately reviewed.
4. Run `/update-board` to update the board and commit that board change:
   - If **APPROVED**: `/update-board {TASK-ID} → Done` — the board commit will be included in the merge
   - If **CHANGES REQUESTED**: task stays in Review (no board update needed)
   - If **BLOCKED**: `/update-board {TASK-ID} → Blocked` with the blocking reason
