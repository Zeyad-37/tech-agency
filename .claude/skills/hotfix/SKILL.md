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

## Step 2: Create the Hotfix Worktree

Speed does not exempt a hotfix from the worktree rule: `git checkout -b` in the main checkout would move whoever else is working there onto the hotfix branch mid-incident. Create a worktree (`@.claude/rules/shared/worktree-first.md`).

A hotfix is the one case where the base is a **release tag**, not a branch — cut from the tag, never from `origin/main`, so unreleased work on `main` cannot ride along into production.

```bash
MAIN_REPO="$(git rev-parse --show-toplevel)"

# Find the latest release tag
git -C "$MAIN_REPO" fetch --tags origin
git -C "$MAIN_REPO" tag --sort=-v:refname | head -5

VERSION="v[X.Y.Z]"                                     # the tag currently in production
BRANCH="hotfix/v[X.Y.Z+1]/[short-description]"         # e.g. hotfix/v1.2.1/fix-login-crash
WORKTREE_DIR="${MAIN_REPO}/../$(basename "$MAIN_REPO")-worktrees/${BRANCH//\//-}"

git -C "$MAIN_REPO" worktree add -b "$BRANCH" "$WORKTREE_DIR" "$VERSION"
cd "$WORKTREE_DIR"

# Verify BEFORE any write. If either check fails, STOP and report.
pwd                          # must equal $WORKTREE_DIR
git branch --show-current    # must equal $BRANCH
```

The branch naming convention is `hotfix/{version}/{short-description}`. The whole fix, its tests, and its board transitions happen inside `$WORKTREE_DIR`.

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

The hotfix must land on `main` too, or the next release regresses it. Merge via PR — never `git checkout main && git merge` in the main checkout, which commits directly on `main` and bypasses the required checks.

```bash
# From the hotfix worktree, once the tag is cut and production is verified:
cd "$WORKTREE_DIR"
/create-pr --base main
```

Open the PR from the hotfix branch into `main`, title it `[HOT-NNN] Hotfix v[X.Y.Z+1]: [description]`, and note in the body that the fix is already live in production so reviewers understand this is a back-merge, not a pending change. If the project keeps a long-lived release branch, open the second PR into that branch as well.

> **No Auto-Push:** Do not push to remote until @Zeyad explicitly approves. Present the PR plan and wait for confirmation.

## Step 8: Post-Mortem

The fixing engineer must write a post mortem within 24 hours.

Save it to `docs/artifacts/post-mortem/{Task-Id}-Post Mortem-{Title}.md` — the canonical location per `@.claude/rules/shared/crash-investigation.md` and the handoff protocol. Append a row to `docs/artifacts/post-mortem/INDEX.md`:

```
| YYYY-MM-DD | {Incident Title} | {Severity} | [Post Mortem](./{filename}.md) |
```

Schedule a brief retro with the team to capture prevention actions.

If this was a crash spike, follow the full crash investigation protocol in `@.claude/rules/shared/crash-investigation.md`. For a P0/P1, run `/postmortem` afterwards to deepen the analysis with the 5 Whys.
