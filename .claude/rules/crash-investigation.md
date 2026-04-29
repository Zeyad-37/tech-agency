# Crashlytics Crash Spike Investigation Protocol

This rule activates when a crash spike investigation is triggered (e.g., "Investigate crash spike", "Crash spike detected", "Triage crash").

## Investigation Steps

### 1. Gather Context

- Run `git log --oneline -20` to list recent commits
- Check if `.claude/crashlytics-context.md` exists. If it does, read and parse it — this file contains the latest crash data injected by a SessionStart hook (stack traces, affected OS versions, device models, crash counts, timeline)
- If the file does not exist, ask the user to provide crash details (stack trace, affected platform, approximate start time)

### 2. Identify the Culprit

- Cross-reference the crash timeline with recent commit timestamps
- Prioritize commits that touch code paths appearing in the stack trace
- Use `git show <hash>` and `git diff <hash>~1 <hash>` to inspect suspicious commits
- Run `git blame` on the crashing file/line to confirm authorship
- Explain clearly why this commit is the most likely cause — connect the code change to the crash signature

### 3. Recommend Resolution

Provide two options:

- **Targeted fix**: A minimal code change that addresses the root cause. Include the exact file, line, and proposed change.
- **Rollback candidate**: Identify the last known-good commit before the culprit using `git log --oneline`. Provide the exact hash and the rollback command: `git revert <culprit-hash>`.

### 4. Generate Post Mortem

After completing the investigation, generate a post mortem document as the **sole output** of the session. Save it to `docs/post-mortem/{Task-Id}-Post Mortem-Title.md` (e.g., `docs/post-mortem/BUG-017-Post Mortem-NPE User Profile Load.md`).

If `docs/post-mortem/` does not exist, create it.

The post mortem must follow this structure exactly:

```markdown
# <Incident Title>

**Date:** YYYY-MM-DD
**Severity:** P0/P1/P2 (based on crash spike magnitude — P0: >5% sessions, P1: 1-5%, P2: <1%)
**Investigator:** <agent name>

## Timeline

| Time | Event |
|------|-------|
| ... | Crash spike detected (source: Crashlytics / user report) |
| ... | Investigation started |
| ... | Culprit commit identified |
| ... | Fix identified / rollback recommended |

## Root Cause

<Detailed explanation of what went wrong at the code level, referencing specific commits, files, and lines.>

## Impact

- **Platforms affected:** <iOS / Android / both>
- **Estimated affected users:** <count or percentage if available from crashlytics-context.md>
- **Crash-free rate drop:** <if available>

## Resolution

### Immediate Fix

<The specific code change or rollback, including commit hash. Show the diff or describe the change precisely.>

### Prevention Action Points

| # | Action | Priority | Suggested Owner | Layer |
|---|--------|----------|-----------------|-------|
| 1 | <e.g., Add unit test for null-safety on UserProfile.load()> | P0 | <from git blame> | Testing |
| 2 | <e.g., Add CI lint rule to flag force-unwraps in shared KMP code> | P1 | <DevOps/Link> | CI |
| 3 | <e.g., Tighten crash rate alerting threshold from 2% to 0.5%> | P1 | <Sentinel> | Monitoring |
| ... | ... | ... | ... | ... |

Action points must cover all relevant layers: unit/integration tests, CI checks or lint rules, code review guidelines, monitoring/alerting thresholds, and architectural or defensive coding improvements (especially in shared KMP code). Use git blame to suggest owners where possible.

## Contributing Factors

<What conditions allowed this bug to ship — e.g., missing test coverage, no null-safety lint rule, insufficient crash alerting threshold, WIP pressure.>

## Lessons Learned

<What the team should take away from this incident. Keep it constructive and actionable.>
```

### 5. Update the Index

Append a one-line entry to `docs/post-mortem/INDEX.md` (create the file if it doesn't exist):

```
| YYYY-MM-DD | <Incident Title> | <Severity> | [Post Mortem](./filename.md) |
```

If INDEX.md is new, add a header row first:

```
| Date | Incident | Severity | Report |
|------|----------|----------|--------|
```
