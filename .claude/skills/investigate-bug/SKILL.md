---
name: investigate-bug
description: "Investigate a functional bug where the app behaves incorrectly but does not crash. Analyzes expected vs actual behavior, traces the issue through recent commits and feature specs, identifies the root cause, and produces a fix plan. Use when the user says 'bug', 'not working as expected', 'wrong behavior', 'investigate bug', 'feature broken', 'regression', 'functional issue', or 'something is off'."
---

# Functional Bug Investigation

This skill investigates non-crashing bugs — cases where the app runs but produces incorrect behavior. For crash spikes, use `/investigate-crash` instead.

## Step 1: Gather Context

Ask the user for (or extract from the report):

- **Expected behavior**: What should happen?
- **Actual behavior**: What happens instead?
- **Steps to reproduce**: Exact sequence of actions
- **Affected platform(s)**: Android, iOS, Web, Backend, or multiple
- **Affected feature/screen**: Which part of the app
- **Regression?**: Did this work before? If so, approximately when did it break?

Then gather technical context:

```bash
# Recent commits in the affected area
git log --oneline -20

# Check for existing feature docs
grep -rl "{Task-Id}" docs/artifacts/ 2>/dev/null || echo "No artifacts found for this task"

# Check board for related tasks
cat board-context.md 2>/dev/null | head -100
```

Read the relevant feature documentation:
- PRD (`docs/artifacts/prd/{Task-Id}-PRD-{Title}.md`) — what was the intended behavior?
- BRD (`docs/artifacts/brd/{Task-Id}-BRD-{Title}.md`) — what are the acceptance criteria and user stories?
- ADR (`docs/artifacts/adr/{Task-Id}-*.md`) — any architectural decisions that constrain the fix?

## Step 2: Reproduce and Locate

Trace the bug through the codebase:

```bash
# Find the affected code path
grep -r "{relevant function or class}" --include="*.kt" --include="*.swift" --include="*.ts" --include="*.tsx" --include="*.py" -l

# If regression — find when it broke
git log --oneline --all -- {affected-file}
git bisect start  # (suggest to user if applicable)
```

For KMP shared code bugs:
- Check if the bug manifests on all platforms or just one
- If platform-specific, check the `actual` implementation in the relevant source set
- If cross-platform, focus on `commonMain` code

For backend bugs:
- Check request/response shapes against the API contract (OpenAPI spec or shared DTOs)
- Inspect service layer logic — is the business rule implemented correctly?
- Check database queries — is the data being fetched/written correctly?

For frontend/mobile bugs:
- Check state management — is the ViewModel/store producing the correct state?
- Check the rendering logic — is the UI correctly reflecting the state?
- Check data flow — is the API response being mapped correctly to domain models?

## Step 3: Identify the Root Cause

Cross-reference the bug with recent changes:

```bash
# Commits that touched the affected files
git log --oneline --since="2 weeks ago" -- {affected-files}

# Inspect the most likely culprit
git show {hash}
git diff {hash}~1 {hash}

# Blame the specific line/function
git blame {file} -L {start},{end}
```

Classify the root cause:

| Category | Examples |
|----------|---------|
| Logic error | Wrong condition, missing edge case, off-by-one |
| State management | Race condition, stale state, missing state transition |
| Data mapping | DTO → domain mapping drops/transforms a field incorrectly |
| API contract mismatch | Client expects field X, server sends field Y |
| Missing validation | Invalid input passes through unchecked |
| Regression | A recent change inadvertently broke existing behavior |
| Spec ambiguity | The PRD/BRD didn't cover this scenario — behavior is undefined |

Explain clearly:
1. **What** is wrong (the specific code/logic error)
2. **Why** it produces the incorrect behavior
3. **When** it was introduced (commit hash if regression, or "original implementation" if always broken)

## Step 4: Recommend Fix

Provide a clear fix plan:

### Fix Details

- **File(s) to change**: List each file and the specific function/method
- **What to change**: Describe the exact modification (or provide a diff)
- **Why this fixes it**: Connect the change to the root cause — not just the symptom

### Test Plan

Every fix MUST include tests that would have caught this bug:

1. **Unit test**: Test the specific logic that was wrong (service/use case/InputHandler level)
2. **Integration test**: Test the full flow that the user reported as broken
3. **Edge cases**: List any related edge cases that should also be tested
4. **Regression guard**: If this is a regression, add a test named `when_{scenario}_then_{correct_behavior}` that explicitly covers the broken case

### Verification Steps

1. Reproduce the bug on the current code (confirm it's broken)
2. Apply the fix
3. Verify the bug is resolved
4. Run the full test suite — no regressions
5. If KMP shared code: verify on all consuming platforms (see cross-platform testing rules in `kmp-coding-standards.md`)

## Step 5: Assess Severity and Decide Output

Not every functional bug needs a full post-mortem. Use this decision tree:

| Condition | Action |
|-----------|--------|
| Bug affects >5% of users or blocks a critical flow | P0 — Write bug report + post-mortem (Step 6) |
| Bug affects 1-5% of users or degrades a key feature | P1 — Write bug report + brief incident note |
| Bug affects <1% of users, has workaround | P2 — Write bug report, add to backlog |
| Edge case, cosmetic, minor inconvenience | P3 — Write bug report, add to backlog |

**Bug report** (always produced — this is the minimum deliverable):

Save to `docs/artifacts/incident-notes/{Task-Id}-Incident-Notes-{slug}.md`:

```markdown
# Bug Report: {Title}

**Date:** YYYY-MM-DD
**Severity:** P0/P1/P2/P3
**Reported by:** {user/agent/automated test}
**Investigator:** {agent name}

## Description

**Expected:** {what should happen}
**Actual:** {what happens instead}
**Steps to reproduce:** {numbered steps}

## Root Cause

{Detailed explanation referencing specific code, commits, and files}

## Fix

**Files changed:**
- `{file}` — {what changed and why}

**Tests added:**
- `{test file}` — {what the test verifies}

## Impact

- **Platforms affected:** {iOS / Android / Web / Backend / All}
- **Users affected:** {estimate}
- **Workaround:** {if any}
```

## Step 6: Post-Mortem (P0/P1 Only)

For severe bugs (P0/P1), produce a full post-mortem following the template in `.claude/rules/crash-investigation.md`, adapted for functional bugs:

- Replace "Crash spike detected" with "Bug reported" in the timeline
- Replace "Crash-free rate drop" with "Affected users/sessions" in the Impact section
- Severity is based on user impact, not crash percentages
- Prevention Action Points should focus on: missing test coverage, spec gaps, validation gaps, review process

Save to `docs/artifacts/post-mortem/YYYY-MM-DD_{bug-slug}.md`.
Update `docs/artifacts/post-mortem/INDEX.md` with a new entry.

## Step 7: Create Board Tasks (MANDATORY)

Every investigation produces at least these board tasks in `board-context.md`:

1. **The fix itself** — assigned to the appropriate engineer (from git blame or domain ownership)
2. **Tests to add** — assigned to the fixing engineer or @Apex
3. **Any prevention actions** from the post-mortem (if produced) — with owners, priorities, and due dates per the feedback loop closure policy in `docs/incident-response.md`

If the root cause is **spec ambiguity**:
- Add a task for @Diana or @Morgan to clarify the spec
- Add a task for @Apex to add acceptance test coverage for the clarified scenario

If the bug is a **regression**:
- Add a P1 task: "Investigate why existing tests did not catch regression in {feature}" — assigned to @Apex
- Add a task to strengthen CI gates if applicable — assigned to @Sentinel

## Step 8: Next Steps

After the investigation is complete:

- **For P0/P1 bugs:** Run `/postmortem` to conduct a 5 Whys root cause analysis — this traces how the bug was introduced AND how it escaped every quality gate to reach production, producing systemic prevention actions
- If the fix is straightforward and the engineer is available → implement immediately
- If the fix requires design review (e.g., changes to shared KMP contracts) → route to @Sage
- If the fix is P0 and needs expedited release → suggest triggering the `/hotfix` workflow
- If the root cause is a spec gap → route to @Morgan and @Diana before fixing
- Notify @Atlas to update the board and track resolution
