---
name: investigate-crash
description: "Investigate a Crashlytics crash spike. Analyzes recent commits, crash data, identifies the culprit, suggests a fix and rollback, then produces a post-mortem document. Use when the user says 'crash spike', 'investigate crash', 'crashes are up', 'Crashlytics alert', 'app is crashing', or 'triage crash'."
---

# Crash Spike Investigation

This skill follows the crash investigation protocol defined in `@.claude/rules/shared/crash-investigation.md`. Read that file first for the full post-mortem template.

## Step 1: Gather Context

```bash
# Recent commits
git log --oneline -20

# Check for Crashlytics data
cat .claude/crashlytics-context.md 2>/dev/null || echo "No crashlytics context file found"
```

If `.claude/crashlytics-context.md` exists, parse it for: stack traces, affected OS versions, device models, crash counts, timeline.

If it doesn't exist, ask the user for: stack trace, affected platform, approximate start time of the spike, crash count if known.

## Step 2: Identify the Culprit

Cross-reference the crash timeline with recent commits:

```bash
# Commits around the time of the spike
git log --oneline --after="[spike start time - 24h]" --before="[spike start time]"

# Inspect suspicious commits
git show [hash]
git diff [hash]~1 [hash]

# Blame the crashing file/line
git blame [file] -L [start],[end]
```

Prioritize commits that:
- Touch code paths in the stack trace
- Modify shared KMP code (affects multiple platforms)
- Change error handling, null safety, or data parsing
- Were merged without full review

Explain clearly WHY this commit is the likely cause.

## Step 3: Recommend Resolution

Provide two options:

**Targeted fix:**
- Exact file, line, and proposed change
- Why this fixes the root cause (not just the symptom)

**Rollback candidate:**
```bash
# Last known-good commit
git log --oneline [culprit-hash]~1 -1

# Rollback command
git revert [culprit-hash]
```

## Step 4: Generate Post-Mortem

Follow the exact template in `@.claude/rules/shared/crash-investigation.md`. The post-mortem is the sole deliverable of this investigation.

Key sections:
- Incident title and date
- Severity (P0: >5% sessions, P1: 1-5%, P2: <1%)
- Timeline (detection → investigation → fix)
- Root cause (detailed, referencing commits and code)
- Impact (platforms, estimated affected users)
- Resolution: immediate fix + prevention action points (with owners from git blame, covering tests, CI, monitoring, architecture)
- Contributing factors
- Lessons learned

Save to `docs/post-mortem/{Task-Id}-Post Mortem-{Title}.md` — e.g. `docs/post-mortem/BUG-017-Post Mortem-NPE User Profile Load.md`. This is the canonical location mandated by `@.claude/rules/shared/crash-investigation.md` and the handoff protocol; create the folder if it does not exist. Post-mortems are project artifacts under version control, not Claude Code configuration, so they never live under `.claude/`.

Append one row to `docs/post-mortem/INDEX.md` (create it with the header row if new):

```
| Date | Incident | Severity | Report |
|------|----------|----------|--------|
| YYYY-MM-DD | {Incident Title} | {Severity} | [Post Mortem](./{filename}.md) |
```

This four-column schema is the single index schema for the agency. `/postmortem` writes rows in exactly this shape when it deepens this document with the 5 Whys.

## Step 5: Next Steps

After the post-mortem is written:
- **Run `/postmortem`** to deepen the analysis with the 5 Whys methodology — this traces how the issue was introduced AND how it escaped every quality gate to reach production, producing systemic prevention actions
- If the fix is ready, suggest triggering the `/hotfix` workflow
- If the fix needs design review, route to @Sage
- Notify @Atlas to schedule a retro on this incident

## Step 6: Create Board Tasks from Prevention Action Points (MANDATORY)

Every "Prevention Action Points" row in the post-mortem MUST become a tracked task. Use the board adapter (`@.claude/rules/shared/board-adapter.md`) — read `board_backend` from `.claude/settings.json` first (absent → `markdown`).

1. For each action point, run `board.create_task()` targeting the Backlog column, whose schema is `| Task ID | Priority | Description | Requested By |`:
   - **Requested By**: the "Suggested Owner" from the post-mortem table (or @Atlas if unassigned)
   - **Priority**: match the post-mortem (P0/P1/P2/P3)
   - **Description**: the action text, suffixed with the source reference `[Post-mortem: docs/post-mortem/{Task-Id}-Post Mortem-{Title}.md]`
   - **Due date**: P0 = 48 hours, P1 = 1 week, P2 = 2 weeks, P3 = next sprint — record it via `board.add_comment()` on backends that have no due-date field

2. Verify: count the action points in the post-mortem table and confirm `board.read_column("Backlog")` returns the same number of new tasks.

3. If this incident is a recurrence (check `docs/post-mortem/INDEX.md`), flag it explicitly in the post-mortem under "Contributing Factors" and add a P0 task: "Investigate why previous prevention actions did not prevent recurrence — @Atlas".

The board edit ships inside the PR that carries the post-mortem document (`@.claude/rules/shared/board-in-pr.md`) — commit `board-context.md` on the same branch as `docs/post-mortem/…`, never as a board-only PR and never on `main`.

This step ensures that post-mortem lessons become real work items with owners and SLAs, not just documentation. Reference `docs/incident-response.md` for the full feedback loop closure policy.
