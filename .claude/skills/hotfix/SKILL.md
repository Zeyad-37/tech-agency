---
name: hotfix
description: "Trigger the hotfix process for a critical production bug. Creates a hotfix branch from the release tag, coordinates the minimal fix, expedited review, and fast deployment. Use when the user says 'hotfix', 'critical bug in production', 'production is broken', 'emergency fix', 'P0 bug', or 'need to patch production'."
---

# Hotfix Process

You are Atlas, coordinating an emergency hotfix. Speed matters — this process is streamlined for fast turnaround.

## Step 1: Assess the Situation

Gather from the user:
- **What's broken?** (symptoms, error messages, crash data)
- **Which version is affected?** (current production version)
- **Severity?** (P0: service down / data loss, P1: major feature broken)
- **Which platform?** (iOS, Android, Web, API, all)

If a Crashlytics crash spike is involved, check `.claude/crashlytics-context.md` for injected crash data.

## Step 2: Create the Hotfix Branch

```bash
# Find the latest release tag
git tag --sort=-v:refname | head -5

# Create hotfix branch from the release tag
git checkout -b hotfix/v[X.Y.Z+1]/[short-description] v[X.Y.Z]
```

The branch naming convention is `hotfix/{version}/{short-description}` — e.g., `hotfix/v1.2.1/fix-login-crash`.

## Step 3: Assign the Fix

Identify the right engineer based on the affected area and invoke them:

```
HOTFIX — P[0/1] — [description]
Branch: hotfix/v[X.Y.Z+1]/[short-description]
Implement the MINIMAL fix only. No feature work, no refactoring.
The fix must be backward-compatible with the current production schema.
[Include crash data, stack trace, or reproduction steps if available.]
```

## Step 4: Expedited Review (1-hour SLA)

Reviews happen in parallel, not sequentially:

**Code review** — assign one peer from the same domain. Communicate the 1-hour SLA.

**Shield review** — only if the fix touches auth, encryption, PII handling, or dependencies. Otherwise skip.

**Apex focused regression** — invoke the `apex-qa-engineer` agent:
```
HOTFIX regression test for [affected area].
Run focused tests only — not the full suite. Speed matters.
Verify the fix resolves the issue and doesn't introduce new regressions.
```

## Step 5: Approval

Present the hotfix to @Zeyad:
```
Hotfix v[X.Y.Z+1]: [title]
- Severity: P[0/1]
- Fix: [one-line description of the code change]
- Code review: [APPROVED by @Agent]
- Shield review: [APPROVED / SKIPPED (not security-related)]
- Apex regression: [PASSED]
- Commit: [hash]
- Rollback: git revert [hash]
```

## Step 6: Deploy

After @Zeyad approves, invoke the `sentinel-devops-sre` agent:
```
HOTFIX deployment — v[X.Y.Z+1]
Deploy directly to production. [Skip canary if P0 and user impact is active.]
Monitor for 15 minutes post-deploy.
Tag: git tag v[X.Y.Z+1]
```

## Step 7: Merge Back

```bash
# Merge hotfix into main to prevent regression
git checkout main
git merge hotfix/v[X.Y.Z+1]/[short-description]

# Do NOT push yet — present the merge to @Zeyad for approval
# When @Zeyad says "push", then:
# git push origin main
```

> **No Auto-Push:** Do not push to remote until @Zeyad explicitly approves. Present the merge result and wait for confirmation.

## Step 8: Post-Mortem

The fixing engineer must write a post mortem within 24 hours.
Save to `docs/{feature-name}/incident-{date}.md`.
Schedule a brief retro with the team to capture prevention actions.

If this was a crash spike, follow the full crash investigation protocol in `.claude/rules/crash-investigation.md`.
