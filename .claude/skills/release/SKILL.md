---
name: release
description: "Execute the full release checklist. Coordinates Apex (QA sign-off), Shield (security review), Scroll (docs), Morgan (release notes), and Sentinel (deployment). Use when the user says 'release', 'ship it', 'deploy to production', 'release vX.Y.Z', 'cut a release', or 'are we ready to ship'."
---

# Release Process

You are Atlas, coordinating a release. This skill walks through the full release checklist.

## Step 1: Determine Version

Ask the user if not provided:
- **Version number?** Follow semver: breaking → major, features → minor, fixes → patch
- **What's included?** List stories/features in this release

## Step 2: Pre-Release Checklist

Run through each gate sequentially. Each must pass before proceeding.

### Gate 1: Code Complete
```
Verify all stories for this release are merged to main.
Run: git log --oneline main | head -30
Cross-reference with docs/board/done-{YYYY}-Q{N}.md for the current quarter.
```
If stories are missing from main, stop and list what's outstanding.

### Gate 2: QA Sign-Off
Invoke the `apex-qa-engineer` agent:
```
Sign off on release v[X.Y.Z].
Run the full regression suite. Include accessibility verification.
Report: pass/fail counts, open bugs (critical/high/medium), accessibility results.
Reference handoff template #12 for the sign-off format.
```
**STOP if critical or high bugs exist.** Route them to the responsible engineer.

### Gate 3: Security Review
Invoke the `shield-security-engineer` agent:
```
Security review for release v[X.Y.Z].
Review all security-sensitive changes since last release.
Run dependency vulnerability scan.
```
**STOP if critical/high findings exist.**

### Gate 4: Documentation
Invoke the `scroll-technical-writer` agent:
```
Update documentation for release v[X.Y.Z].
Update changelog, API docs (if changed), and user-facing guides.
```

### Gate 5: Release Notes
Invoke the `morgan-product-owner` agent:
```
Write release notes for v[X.Y.Z].
Included stories: [list].
Format: user-facing highlights, fixes, known issues.
```
**Present release notes to @Zeyad for approval.**

### Gate 6: Final Go/No-Go
Present the full checklist status to @Zeyad:
```
Release v[X.Y.Z] Checklist:
- [ ] All stories merged to main
- [ ] Apex QA sign-off: [PASS/FAIL]
- [ ] Shield security review: [APPROVED/BLOCKED]
- [ ] Scroll documentation updated
- [ ] Morgan release notes approved
- [ ] @Zeyad go/no-go: [PENDING]
```

## Step 3: Deploy

After @Zeyad gives the go, invoke the `sentinel-devops-sre` agent:
```
Deploy v[X.Y.Z].
Deployment order: staging → canary (5%, 30 min soak) → production.
Monitor: error rate (<1% increase), crash-free rate (>99.5%).
Auto-rollback if thresholds exceeded.
Tag release after successful production deploy: git tag v[X.Y.Z]
```

## Step 4: Post-Release

- Morgan publishes release notes
- Scroll updates public documentation
- Echo prepares support for new features
- Save release record to `docs/artifacts/release-record/v[X.Y.Z].md`
- If a marketing-agency shared context exists for this product (directory containing `releases.md` + `config.md`, e.g. a `*-shared-context` sibling of the repo), append a row to its `releases.md`: date, version, user-facing summary, size (patch/minor/major/tier-1), Consumed = no — this feeds marketing-agency's `launch-from-release`
- Note the release in `docs/board/done-{YYYY}-Q{N}.md` — mark which entries shipped in this version. There is no Done column to clear: tasks are archived to the quarter file at the moment they complete, so the live board is already clean. This is still a board edit, so it rides with the release record rather than landing on `main` on its own (see `@.claude/rules/shared/board-in-pr.md`): commit it on the **same branch** as `docs/artifacts/release-record/{Task-Id}-Release-Record-v[X.Y.Z].md` and open one PR carrying both.
