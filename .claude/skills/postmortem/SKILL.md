---
name: postmortem
description: "Write a structured post-mortem using the 5 Whys methodology after a bug or crash investigation. Traces the root cause chain from symptom to systemic failure, analyzes how the issue was introduced AND how it escaped each quality gate to reach production, then creates prevention tasks. Use when the user says 'postmortem', 'post-mortem', '5 whys', 'root cause analysis', 'why did this reach production', 'write a postmortem', or after completing an /investigate-crash or /investigate-bug session."
---

# 5 Whys Post-Mortem

This skill produces a structured post-mortem document using the **5 Whys** root cause analysis methodology. It goes beyond the immediate technical root cause to uncover the systemic failures that allowed the issue to be introduced AND to escape every quality gate on its way to production.

Run this after `/investigate-crash` or `/investigate-bug`, or standalone when you have enough context about an incident.

## Step 1: Gather Incident Context

Check for existing investigation artifacts:

```bash
# Check for recent post-mortems from /investigate-crash or /investigate-bug
ls docs/post-mortem/ 2>/dev/null
cat docs/post-mortem/INDEX.md 2>/dev/null

# Check for bug reports and incident notes
find docs/incident-notes docs/post-mortem -name '*.md' -mtime -7 2>/dev/null

# Check for recent investigation commits
git log --oneline -20
```

Read the board for related tasks through the adapter, not by reading the file (`@.claude/rules/shared/board-adapter.md` rule 2) — read `board_backend` from `.claude/settings.json` (absent → `markdown`), then run `board.read_all()`.

If a post-mortem or bug report already exists from a prior investigation:
- Read it to extract: the immediate root cause, the fix applied, the timeline, and any prevention action points already identified
- This skill will **deepen** that analysis with the 5 Whys — it does not replace the prior investigation

If no prior investigation exists, ask the user for:
- **What happened**: The symptom (crash, wrong behavior, data loss, etc.)
- **When it happened**: Timeline of detection and impact
- **What was the immediate fix**: Revert, hotfix, or pending
- **Severity**: P0/P1/P2/P3 based on user impact

## Step 2: Conduct the 5 Whys Analysis

The 5 Whys traces two parallel chains:

### Chain A: How Was the Issue Introduced?

Start from the immediate technical root cause and ask "Why?" repeatedly:

| # | Question | Answer |
|---|----------|--------|
| Why 1 | Why did the issue occur? | *(The immediate code-level cause — e.g., "NullPointerException on UserProfile.load() because `address` field was null")* |
| Why 2 | Why was the code written this way? | *(e.g., "The developer assumed `address` would always be populated by the API, but the endpoint was changed to make it optional")* |
| Why 3 | Why was this assumption not validated? | *(e.g., "No null-safety check was required by the coding standards for API response fields, and the shared DTO in commonMain didn't mark it as nullable")* |
| Why 4 | Why didn't the coding standards cover this? | *(e.g., "The KMP coding standards require @SerialName but don't enforce nullability analysis on DTO fields that map to optional API fields")* |
| Why 5 | Why was there no systemic safeguard? | *(e.g., "No detekt rule or Konsist test validates that DTO fields match the API contract's nullability")* |

### Chain B: How Did It Escape to Production?

Start from "the issue reached production" and trace through each quality gate:

| # | Quality Gate | Did It Catch It? | Why Not? |
|---|-------------|-------------------|----------|
| 1 | **Unit Tests** | No | *(e.g., "No unit test for the null case — test only covered the happy path with a fully populated UserProfile")* |
| 2 | **Integration Tests** | No | *(e.g., "Integration test used a mock API that always returns all fields — didn't simulate the optional field scenario")* |
| 3 | **Code Review** | No | *(e.g., "Reviewer focused on the feature logic, didn't cross-reference the API contract for field nullability")* |
| 4 | **CI/Lint Checks** | No | *(e.g., "Detekt doesn't flag non-null assertions on deserialized fields; no custom rule for API contract validation")* |
| 5 | **QA / Manual Testing** | No | *(e.g., "QA tested with a fully provisioned test account — the null address scenario only occurs for new users who skip onboarding")* |
| 6 | **Staging / Canary** | No | *(e.g., "Staging environment has seed data with all fields populated — doesn't reflect production data variety")* |
| 7 | **Monitoring / Alerting** | Partial | *(e.g., "Crash alerting threshold was set at 2% — the spike only hit 1.5% before investigation started")* |

**Guidelines for the 5 Whys:**
- Keep asking "Why?" until you reach a systemic or process-level cause, not just a code-level one
- If a chain converges before 5 levels, stop — don't force artificial depth
- If a chain needs more than 5 levels, continue — 5 is a minimum, not a maximum
- Each "Why" answer must be specific and evidence-based (reference commits, files, test names, CI configs)
- Avoid blame — focus on systems, processes, and gaps, not individuals

## Step 3: Identify the Systemic Root Cause

Synthesize both chains into a root cause statement:

> **Systemic Root Cause:** {One paragraph describing the deepest structural reason this issue was both introduced and undetected. This should be at the process/tooling/culture level, not the code level.}

Example: *"The project lacks automated validation that shared KMP DTO nullability matches the API contract. Combined with integration tests that use fully-populated mock data instead of production-representative fixtures, nullable API fields can be mapped to non-null Kotlin properties without any gate catching the mismatch."*

Classify the systemic root cause:

| Category | Description |
|----------|------------|
| **Testing Gap** | Missing test scenarios, unrealistic test data, insufficient coverage |
| **Tooling Gap** | Missing lint rule, CI check, or automated validation |
| **Process Gap** | Review checklist missing a check, no cross-reference step |
| **Knowledge Gap** | Team unaware of a contract change, missing documentation |
| **Architecture Gap** | Defensive coding pattern not enforced, missing abstraction layer |
| **Monitoring Gap** | Alert thresholds too lenient, missing metric, blind spot in dashboards |
| **Data Gap** | Test/staging data doesn't represent production variety |

## Step 4: Generate the Post-Mortem Document

Save to `docs/post-mortem/{Task-Id}-Post Mortem-{Title}.md` — the canonical location per `@.claude/rules/shared/crash-investigation.md` and the handoff protocol. If this deepens an existing post-mortem, **replace** the original file, keeping the same filename so the INDEX row keeps resolving.

If `docs/post-mortem/` does not exist, create it.

```markdown
# {Incident Title}

**Date:** YYYY-MM-DD
**Severity:** P0/P1/P2/P3
**Investigator:** {agent name}
**Method:** 5 Whys Root Cause Analysis

## Timeline

| Time | Event |
|------|-------|
| ... | Issue detected (source: Crashlytics / user report / automated test / monitoring) |
| ... | Investigation started |
| ... | Immediate cause identified |
| ... | Fix applied / rollback deployed |
| ... | 5 Whys analysis completed |

## Immediate Root Cause

{The direct code-level cause — what the /investigate-crash or /investigate-bug found. Reference specific commits, files, and lines.}

## 5 Whys Analysis

### Chain A: How Was the Issue Introduced?

| # | Why? | Answer | Evidence |
|---|------|--------|----------|
| 1 | Why did {symptom} occur? | {answer} | {commit hash, file:line, or doc reference} |
| 2 | Why {answer from 1}? | {answer} | {evidence} |
| 3 | Why {answer from 2}? | {answer} | {evidence} |
| 4 | Why {answer from 3}? | {answer} | {evidence} |
| 5 | Why {answer from 4}? | {answer} | {evidence} |

### Chain B: How Did It Escape to Production?

| # | Quality Gate | Caught? | Why Not? | Evidence |
|---|-------------|---------|----------|----------|
| 1 | Unit Tests | {Yes/No/Partial} | {explanation} | {test file or gap} |
| 2 | Integration Tests | {Yes/No/Partial} | {explanation} | {test file or gap} |
| 3 | Code Review | {Yes/No/Partial} | {explanation} | {PR link or review notes} |
| 4 | CI / Lint | {Yes/No/Partial} | {explanation} | {CI config or rule gap} |
| 5 | QA Testing | {Yes/No/Partial} | {explanation} | {test plan or gap} |
| 6 | Staging / Canary | {Yes/No/Partial} | {explanation} | {environment config or data gap} |
| 7 | Monitoring | {Yes/No/Partial} | {explanation} | {alert config or threshold} |

### Systemic Root Cause

> {One paragraph synthesizing both chains into the deepest structural cause.}

**Category:** {Testing Gap / Tooling Gap / Process Gap / Knowledge Gap / Architecture Gap / Monitoring Gap / Data Gap}

## Impact

- **Platforms affected:** {iOS / Android / Web / Backend / All}
- **Estimated affected users:** {count or percentage}
- **Duration:** {time from introduction to fix}
- **Data impact:** {any data corruption, loss, or inconsistency}

## Resolution

### Immediate Fix

{The code change or rollback that resolved the symptom. Reference commit hash.}

### Prevention Action Points

Each action addresses a specific "Why" from the analysis:

| # | Action | Addresses | Priority | Owner | Layer | Due |
|---|--------|-----------|----------|-------|-------|-----|
| 1 | {action} | Chain A, Why {N} | P{0-3} | @{Agent} | {Testing/CI/Process/Architecture/Monitoring} | {date per SLA} |
| 2 | {action} | Chain B, Gate {N} | P{0-3} | @{Agent} | {layer} | {date} |
| 3 | {action} | Chain B, Gate {N} | P{0-3} | @{Agent} | {layer} | {date} |
| ... | ... | ... | ... | ... | ... | ... |

**Every "Why" and every failed quality gate MUST have at least one prevention action.** No gap should be left unaddressed.

Priority SLAs:
- P0: 48 hours
- P1: 1 week
- P2: 2 weeks
- P3: Next sprint

## Contributing Factors

{What environmental, process, or cultural conditions made this failure more likely. Be specific — reference WIP pressure, missing documentation, team transitions, incomplete onboarding, tech debt accumulation, etc.}

## Lessons Learned

{Constructive takeaways. Focus on systemic improvements, not individual performance. Each lesson should map to a concrete action point above.}

## Recurrence Check

{Check `docs/post-mortem/INDEX.md` for similar past incidents. If this is a recurrence:}
- **Previous incident:** {link to prior post-mortem}
- **Previous prevention actions:** {were they completed? did they work?}
- **Why recurrence:** {what the previous actions missed}
```

## Step 5: Update the Index

There is exactly one index, `docs/post-mortem/INDEX.md`, with exactly one schema — the four-column form that `/investigate-crash` and `@.claude/rules/shared/crash-investigation.md` also write. Do not add a fifth column: a second schema makes the row-matching step below impossible.

If INDEX.md does not exist, create it with the header row:

```
| Date | Incident | Severity | Report |
|------|----------|----------|--------|
```

Then:

- **Deepening a prior investigation** (the usual case — this skill runs after `/investigate-crash` or `/investigate-bug`): a row for this incident already exists and already links to the file you just replaced. Leave it in place. Update only the Severity cell if the 5 Whys changed the assessment. Do **not** append a duplicate row.
- **Standalone run** (no prior investigation): append one new row.

```
| YYYY-MM-DD | {Incident Title} | {Severity} | [Post Mortem](./{filename}.md) |
```

The analysis method is recorded in the document itself (`**Method:** 5 Whys Root Cause Analysis` in the header), not in the index.

## Step 6: Create Board Tasks (MANDATORY)

Every prevention action point MUST become a tracked task. Use `board.create_task()` (see `@.claude/rules/shared/board-adapter.md`) for each action:

1. **Read board backend** from `.claude/settings.json` (absent → `markdown`) to determine the task creation method.

2. **Create one task per prevention action** in the Backlog column, whose schema is `| Task ID | Priority | Description | Requested By |`:
   - **Task ID**: `PM-{NNN}` (sequential, from the post-mortem action point number)
   - **Description**: the action text from the prevention table, prefixed with `[5-Whys]` and suffixed with the source reference `[Post-mortem: docs/post-mortem/{Task-Id}-Post Mortem-{Title}.md]`
   - **Requested By**: the "Owner" from the prevention table (or @Atlas if unassigned)
   - **Priority**: match the priority from the table
   - **Due date** and **labels** (`post-mortem`, `prevention`, `{category}`): set natively on backends that support them; on the markdown backend record them via `board.add_comment()`, since the Backlog table has no column for either

3. **Verify**: Count the action points in the post-mortem and confirm `board.read_column("Backlog")` returns the same number of new tasks.

4. **Recurrence escalation**: If this is a recurrence of a previous incident (found in Step 4's Recurrence Check), create an additional P0 task:
   - `[5-Whys] Investigate why previous prevention actions for {prior incident} did not prevent recurrence — @Atlas`

## Step 7: Next Steps

After the post-mortem and tasks are created:

- If the immediate fix is not yet deployed → suggest `/hotfix` workflow
- If architecture changes are needed → route the relevant prevention tasks to @Sage for ADR
- If test infrastructure changes are needed → route to @Apex and @Sentinel
- If coding standards need updating → route to @Sage with the specific rule change
- Notify @Atlas to schedule a brief retro focused on the systemic root cause
- If the incident is P0/P1 → recommend sharing the post-mortem with the full team

The board edits from Step 6 ship inside the PR that carries the post-mortem document (`@.claude/rules/shared/board-in-pr.md`) — commit `board-context.md` on the same branch as `docs/post-mortem/…` and `docs/post-mortem/INDEX.md`. Never open a board-only PR and never commit the board on `main`.

## When to Use This Skill

| Scenario | Action |
|----------|--------|
| After `/investigate-crash` completes | Run `/postmortem` to deepen the analysis with 5 Whys |
| After `/investigate-bug` completes (P0/P1) | Run `/postmortem` to trace how the bug escaped quality gates |
| Recurring incident detected | Run `/postmortem` — the recurrence check will flag prior failures |
| Near-miss (caught in staging/canary) | Run `/postmortem` to strengthen the gates that almost failed |
| @Zeyad requests a root cause analysis | Run `/postmortem` standalone with incident details |
