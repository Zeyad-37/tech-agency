---
name: investigate-crash
description: "Investigate a Crashlytics crash spike. Analyzes recent commits, crash data, identifies the culprit, suggests a fix and rollback, then produces a post-mortem document. Use when the user says 'crash spike', 'investigate crash', 'crashes are up', 'Crashlytics alert', 'app is crashing', or 'triage crash'."
---

# Crash Spike Investigation

This skill follows the crash investigation protocol defined in `.claude/rules/crash-investigation.md`. Read that file first for the full post-mortem template.

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

Follow the exact template in `.claude/rules/crash-investigation.md`. The post-mortem is the sole deliverable of this investigation.

Key sections:
- Incident title and date
- Severity (P0: >5% sessions, P1: 1-5%, P2: <1%)
- Timeline (detection → investigation → fix)
- Root cause (detailed, referencing commits and code)
- Impact (platforms, estimated affected users)
- Resolution: immediate fix + prevention action points (with owners from git blame, covering tests, CI, monitoring, architecture)
- Contributing factors
- Lessons learned

Save to `docs/artifacts/post-mortem/YYYY-MM-DD_{crash-slug}.md`.
Update `docs/artifacts/post-mortem/INDEX.md` with a new entry.

## Step 5: Next Steps

After the post-mortem is written:
- **Run `/postmortem`** to deepen the analysis with the 5 Whys methodology — this traces how the issue was introduced AND how it escaped every quality gate to reach production, producing systemic prevention actions
- If the fix is ready, suggest triggering the `/hotfix` workflow
- If the fix needs design review, route to @Sage
- Notify @Atlas to schedule a retro on this incident

## Step 6: Create Board Tasks from Prevention Action Points (MANDATORY)

Every "Prevention Action Points" row in the post-mortem MUST become a tracked task in `board-context.md`. For each action point:

1. Add to `docs/board/backlog.md` with:
   - **Owner**: The "Suggested Owner" from the post-mortem table (or @Atlas if unassigned)
   - **Priority**: Match the priority from the post-mortem (P0/P1/P2/P3)
   - **Due date**: P0 = 48 hours, P1 = 1 week, P2 = 2 weeks, P3 = next sprint
   - **Source**: `[Post-mortem: docs/artifacts/post-mortem/YYYY-MM-DD_{slug}.md]`
   - **Description**: The action text from the post-mortem table

2. Verify: count the action points in the post-mortem table and confirm the same number of tasks exist in `board-context.md`.

3. If this incident is a recurrence of a previous incident (check `docs/artifacts/post-mortem/INDEX.md`), flag it explicitly in the post-mortem under "Contributing Factors" and add a P0 task: "Investigate why previous prevention actions did not prevent recurrence — @Atlas".

This step ensures that post-mortem lessons become real work items with owners and SLAs, not just documentation. Reference `docs/incident-response.md` for the full feedback loop closure policy.
