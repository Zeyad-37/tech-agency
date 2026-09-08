---
name: release
description: "Execute the full production release checklist for a version: coordinates Apex (QA sign-off), Shield (security review), Scroll (docs), Morgan (release notes), and Sentinel (staging → canary → production deployment and tagging). Use when the user says 'release', 'cut a release', 'release vX.Y.Z', 'deploy to production', 'ship the release', or 'are we ready to ship'. NOT for taking a single feature or branch to a merged PR — that is /ship-it."
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
Cross-reference with board-context.md Done column.
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
- Save release record to `docs/releases/v[X.Y.Z].md`
- **Release feed for downstream consumers (conditional — skip silently when absent).** Some products keep a *shared context directory* that downstream tooling reads to turn a shipped release into launch work. It is identified by shape, not by name: a directory containing both `releases.md` and `config.md`, typically a `*-shared-context` sibling of this repo. If — and only if — such a directory exists, append one row to its `releases.md`:

  | Column | Value |
  |---|---|
  | Date | release date |
  | Version | `vX.Y.Z` |
  | Summary | the user-facing summary from the release notes |
  | Size | `patch` / `minor` / `major` / `tier-1` |
  | Consumed | `no` |

  This is a plain file append into a directory that already exists outside this repo. It installs nothing, requires no plugin, and creates nothing when the directory is absent — in that case do not create it, do not mention it, and move on.

  The reader of this feed is whatever downstream tooling the product has configured; the `marketing-agency` plugin's `launch-from-release` is one such reader. That plugin is **not** part of tech-agency: it lives in its own repository, ships from its own marketplace, and is installed separately. Nothing here installs it, and its absence is the normal case — the shared-context directory is the entire contract between the two.
- Update `board-context.md` — clear Done column, note the release. This is a board edit, so it rides with the release record above rather than landing on `main` on its own (see `@.claude/rules/shared/board-in-pr.md`): commit `board-context.md` on the **same branch** as `docs/releases/v[X.Y.Z].md` and open one PR carrying both. Do not commit the Done-column clear directly on `main` as a post-merge cleanup step.
