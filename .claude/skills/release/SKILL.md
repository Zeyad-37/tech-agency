---
name: release
description: "Execute the full release checklist for a version. Detects the project type first: a mobile app ships through the app stores (version-bump PR, annotated tag, CI builds/signs/uploads a draft, the exact shipped artifact is verified, a human presses Publish), and a web service or backend deploys through staging to production. Coordinates Apex (QA and the exact-artifact check), Shield (security), Scroll (changelog), Morgan (release notes) and Sentinel (deploy). Asks every release whether to use a staged rollout. Use when the user says 'release', 'cut a release', 'release vX.Y.Z', 'ship to the stores', 'submit to the App Store', 'publish to Google Play', 'deploy to production', 'ship the release', or 'are we ready to ship'. NOT for taking a single feature or branch to a merged PR — that is /ship-it."
---

# Release Process

You are Atlas, coordinating a release. The gates run **in order**, and each one is a **hard stop**: when a gate fails, stop, report what failed and who owns the fix, and do not start the next gate.

There are two paths, chosen in Step 0:

| Path | What ships | How it reaches users |
|---|---|---|
| **Store** (mobile) | Signed app bundles / IPAs | Version-bump PR → annotated tag → CI builds, signs and uploads a **draft** → exact-artifact check → @Zeyad presses Publish / Release in the store console |
| **Service** (web / backend) | Images, deployables, packages | Staging → production, through a canary when the rollout is staged |

Rules that hold on both paths:

- **Nothing project-specific is hardcoded.** Tag format, workflow files, store track names, version locations, verification scripts and runbook paths are **discovered from the repo** in Step 0, or asked for. Never guess one.
- **Committing actions in a store console are always the human's.** Publish, Send for review, Submit for Review, Release this version, and every rollout-percentage increase are @Zeyad's clicks. The agent stages everything and stops at the button.
- **The agent never signs a release build and never touches signing material** — keystores, key passwords, certificates, provisioning profiles, store API keys. Signing happens in CI, from secrets only CI holds — or, for a local iOS archive, by @Zeyad.
- **A local archive, sign and upload is @Zeyad's step, never the agent's.** When CI does not produce the iOS build (3.5), the agent prepares a clean worktree of the tag and stops; it never runs `xcodebuild archive` or an export with a distribution identity, and never uploads to a store.
- **Staged rollout is asked about every release** (Gate 6). Never apply one, and never skip one, without asking.
- @Zeyad approves the release notes and gives the final go/no-go. Any gate may be **waived** only by @Zeyad; a waiver is recorded, never assumed.

Every decision, waiver, failed run and tag move goes into the release record (§ Release Record) as it happens, not reconstructed afterwards.

## Step 0: Detect the Project Type and Discover the Release Setup

### Project type

```bash
# Android app module: a Gradle module applying the application plugin
grep -rlE 'com\.android\.application|androidApplication' --include='*.gradle.kts' --include='*.gradle' --include='*.toml' . 2>/dev/null | grep -v '/build/'
# Xcode project
find . -name '*.xcodeproj' -not -path '*/Pods/*' -not -path '*/build/*' -maxdepth 4
# Release workflow triggered by a tag push — a structural check of `on.push.tags`, not a grep
# for "tags:", which also matches branch filters, job steps and comments. Needs mikefarah yq.
yq --version 2>/dev/null | grep -q mikefarah || echo "mikefarah yq not available — ask which workflow releases"
for f in .github/workflows/*.y*ml; do
  [ "$(yq '.on.push.tags != null' "$f" 2>/dev/null)" = "true" ] && echo "$f"
done
```

Use a YAML 1.2 parser such as mikefarah `yq`. A YAML 1.1 parser (PyYAML, Ruby's Psych) reads the `on:` key as the boolean `true`, so `.on` comes back empty and every workflow looks untriggered. If no structural check can run, do not fall back to grep: list the workflow files and ask @Zeyad which one is the release workflow.

- **Store path** — the repo has an Android app module and/or an Xcode project, **and** a release workflow triggered by a tag push.
- **Service path** — anything else that deploys: a web app, an API, a worker, a published package.
- **Both** (e.g. a mobile app plus its backend in one repo) — ask @Zeyad which one this release ships. Run each path as its own release, with its own task and record.
- **App code but no tag-triggered release workflow** — stop. The store path depends on CI building and signing the artifact; without that workflow there is no safe way to produce one. Tell @Zeyad and offer to hand @Sentinel the job of building one. Do not fall back to a local signed build, and do not run the service path for an app.

### Release setup to discover

Read these from the repo and write them into the release record's **Setup** table. When one cannot be found, ask; do not invent a value.

| Item | Where to look |
|---|---|
| Tag format | `git tag --sort=-creatordate \| head -20` — bare `1.2.3` or `v1.2.3`, and any prefix |
| Release workflow (tag-triggered) | The `.github/workflows/*` file whose `on.push.tags` is set, by the structural check above (or @Zeyad's answer when it cannot run) — note its jobs, runner images and the Xcode version it selects |
| Main-verification workflow | The workflow that runs on pushes to `main` |
| PR CI workflow | The workflow that runs on `pull_request` — compare its jobs with the release workflow's |
| Android version | `versionCode` / `versionName` in the app module's build file or version catalog |
| iOS version | `MARKETING_VERSION` / `CURRENT_PROJECT_VERSION` in the Xcode project or an `.xcconfig` |
| Store tracks | The Play track the workflow uploads to; TestFlight / App Store for iOS |
| Artifact-verification scripts | `scripts/`, `tools/`, the release workflow — anything that checks a built AAB/APK/IPA |
| iOS archive runbook | `docs/artifacts/runbook/`, `docs/guides/` — how this project archives and uploads |
| Changelog | Wherever the project already keeps one (a `CHANGELOG.md`, a comment block above the version in the build file, GitHub Releases) |
| Feature-flag definitions | The project's flag source (`ff_*` names, remote-config defaults, build-config fields) |
| Local release additions | `.claude/rules-local/` — any section about a release checklist |

## Step 1: Version and Scope

### Version

1. Find the last release tag: `git tag --sort=-creatordate | head -5`.
2. **Keep the repo's tag format.** If existing tags are bare (`1.0.0`), the new tag is bare too — do not add a `v`. The release record's filename and the board label always use `vX.Y.Z` (they follow the plugin's naming convention, not the repo's tags).
3. Propose the semver bump from the changes below — breaking → major, features → minor, fixes only → patch — and confirm it with @Zeyad.

### What's included

Build the list from git and the merged PRs, **not** from `docs/board/done-*.md` (on the `github` board backend those files are frozen history):

```bash
git fetch origin main --tags
git log --oneline "<last-tag>..origin/main"

# The date search is only a coarse pre-filter: a PR merged on the tag's own day before the
# tag was cut matches it too. Keep only PRs whose merge commit is actually in the range.
RANGE=$(mktemp)
git rev-list "<last-tag>..origin/main" > "$RANGE"
gh pr list --state merged --base main --limit 200 \
  --search "merged:>=$(git log -1 --format=%cs <last-tag>)" \
  --json number,title,url,labels,mergedAt,mergeCommit \
  | jq --rawfile range "$RANGE" \
      '[ .[] | select(.mergeCommit.oid as $s | $range | split("\n") | index($s)) ]'
rm -f "$RANGE"
```

Present it as four tables, each row linking its PR:

| Table | Contains |
|---|---|
| **Features** | New or changed user-facing behaviour |
| **Bug fixes** | Fixes to shipped behaviour |
| **Tech / tooling** | Refactors, CI, build, tests, internal work |
| **Dependency updates** | Version bumps |

Columns: `PR | Title | Notes`. Two notes are mandatory:

- **Not user-visible** — the feature sits behind a feature flag that is off in release builds. Check by grepping the project's flag definitions for the flag the PR introduced. Flagged-off work stays in the record but stays out of the release notes.
- **Major bump — regression attention** — a dependency moved a major version. @Apex covers the areas it touches in Gate 2, and it triggers a full security review in Gate 3.

### Board task and worktree

- `board.search("Release X.Y.Z")` — reuse the task if one exists; otherwise `board.create_task` it as `[T-NNN] Release X.Y.Z`. Resolve both through the backend in `.claude/settings.json` (`@.claude/rules/shared/board-adapter.md`).
- That task ID names the release branch (`T-NNN/release-X.Y.Z`), prefixes its commits (`[T-NNN] @Atlas: …`), and names the release record.
- **Store path: the version bump gets its own sub-task.** `board.create_task` it as `[T-NNN.1] Version bump X.Y.Z`; on `github` make it a sub-issue of the release task (`gh issue edit <release issue> --add-sub-issue <bump issue>`). Its branch is `T-NNN.1/version-X.Y.Z` and its commits are prefixed `[T-NNN.1]`. This matters because `/create-pr` closes the issue whose title starts with the branch's exact `[TASK-ID] ` prefix: a bump PR on a `T-NNN/…` branch would close the release task the moment the bump merged — before anything was built, verified or published. On `T-NNN.1/…` it closes only the sub-task.
- **The release task's transitions:** → In Progress now, at Step 1 (`board.move_task`); it stays In Progress through Steps 2–4; → Done through the Step 5 release-record PR on `T-NNN/release-X.Y.Z`. On `github` that PR carries `Closes #<release issue>`, which closes the task when it merges; on `markdown` the Done commit rides in that PR (`@.claude/rules/shared/board-in-pr.md`).
- Create the release worktree per `@.claude/rules/shared/worktree-first.md`, cut from `origin/main`. The release record is drafted there now and updated at every step.

## Step 2: Pre-Release Gates

### Gate 1: Code complete

- Everything in the Step 1 tables is merged to `main`. If something expected is missing, stop and list it.
- Pick the commit that will be tagged (store path: the version-bump merge commit, so re-check this after Step 3.1). It needs a **green main-verification run on that exact SHA**:

  ```bash
  gh run list --workflow "<main-verification workflow>" --commit "<sha>" \
    --json databaseId,status,conclusion,url
  ```

  A green run on the previous commit does not count.
- **Run the release-only checks before tagging.** Compare the release workflow's jobs with PR CI's. Anything only the release workflow does must be run now, the same way it will run there — for example, if PR CI never compiles the iOS app target, compile it with the Xcode version the release runner selects. Otherwise the tag run is the first build that ever compiles it, and a failure there costs a tag move.

### Gate 2: QA — @Apex, scoped to the diff

Invoke the `apex-qa-engineer` agent:
```
Release sign-off for X.Y.Z (task T-NNN). Use handoff template #12.
Scope: the changes since <last-tag> — the Step 1 tables are attached. This is a
regression of those changes, not of the whole app.
- Regression-test each feature and fix, plus the areas each major dependency bump touches.
- Accessibility on every changed screen.
Report: pass/fail counts, open bugs by severity, accessibility results.
```
**STOP if critical or high bugs are open.** Route them to the responsible engineer.

### Gate 3: Security — @Shield, scoped to the diff

Invoke the `shield-security-engineer` agent:
```
Security review for release X.Y.Z (task T-NNN).
Review the security-sensitive changes since <last-tag> and run the dependency
vulnerability scan. A FULL review is required only if security-sensitive code changed
(auth, encryption, app lock, PII handling, billing) or a dependency had a major bump;
otherwise review the sensitive changes and the scan results.
```
**STOP if critical or high findings exist.**

### Waivers

@Zeyad may waive Gate 2 or Gate 3 — for example, a patch release whose only change is a copy fix. Record a waiver in the release record's **Decisions** table (what was waived, why, by whom) and mark the gate **Waived** in the **Gates** table. A waiver is never inferred from silence.

### Project release additions

Read `.claude/rules-local/` for a release-checklist section. Projects keep platform-specific checks there — typically on-device checks of the shipped build. Add **each item as its own gate**, labelled `L1`, `L2`, … in the Gates table, with its owner. Run each one where it fits: a check of the shipped artifact runs with Gate 7, anything else runs now. If there is no such section, say so in the record and move on.

### Gate 4: Documentation — @Scroll

Invoke the `scroll-technical-writer` agent:
```
Update documentation for release X.Y.Z.
Update the changelog the project already keeps: <location from Step 0>.
Do not create a CHANGELOG.md if the project has none.
Update API docs and user-facing guides only where this release changed them.
```

### Gate 5: Release notes — @Morgan

Invoke the `morgan-product-owner` agent:
```
Write release notes for X.Y.Z from the Step 1 tables (attached).
- User-facing changes only. Leave out flagged-off features and internal work.
- Store path: one version per store, within each store's limits:
    Google Play "What's new": at most 500 characters per locale.
    App Store "What's New": cannot be set on an app's first release.
- Service path: one version for the changelog / release page.
- Add a "Known issues" list: open bugs and tech debt that ship in this build.
```

Build **Known issues** from the board (`board.search` for open bugs) and the tech-debt backlog (`docs/guides/tech-debt/backlog.md`), keeping only items present in this build.

Before presenting, check the copy for AI-sounding phrasing — stock openers, empty intensifiers, "we're excited to", feature lists dressed as prose — and rewrite it plainly. Count characters per store and locale.

**Present the notes to @Zeyad for approval.** Approved text goes into the release record verbatim.

### Gate 6: Go / no-go, and the rollout question

Present the checklist:

```
Release X.Y.Z — T-NNN Release X.Y.Z ([store | service] path)
- [ ] Gate 1 Code complete — main-verification run <id> green on <sha>; release-only checks: [...]
- [ ] Gate 2 Apex QA (changes since <last-tag>): [PASS / FAIL / WAIVED]
- [ ] Gate 3 Shield security: [APPROVED / BLOCKED / WAIVED] ([full | scoped] review)
- [ ] L1..Ln Project release additions: [...]
- [ ] Gate 4 Scroll changelog updated
- [ ] Gate 5 Morgan release notes approved
- [ ] Gate 7 Exact artifact — runs after the build (store path) / on staging (service path)
- [ ] Store path: the tag's CI upload will submit [draft to <track> | edit commit to <track>] — approved by this go
- [ ] Rollout: [PENDING — see question below]
- [ ] @Zeyad go/no-go: [PENDING]
```

Then ask the rollout question as a **multiple-choice question** (AskUserQuestion), with your recommendation first:

| Path | Staged | Full |
|---|---|---|
| **Store** | Play: staged rollout percentages (e.g. 5% → 20% → 50% → 100%), halted if the crash-free rate drops. App Store: phased release over 7 days | Play: 100%. App Store: immediate release |
| **Service** | Staging → canary (5% traffic, 30-minute soak) → production, with auto-rollback | Staging → production |

How to recommend:

- **Full** when the app or service has no meaningful user base yet. A staged rollout to almost nobody only delays the release; it catches nothing.
- **Staged** once there are real users, or whenever the release carries risky changes — data migrations, billing, security controls, major dependency bumps — regardless of user count.
- Base it on **evidence you can read**: store install / active-user counts, crash-reporting session volume, service traffic. Quote the numbers. If you cannot read any of them, say so plainly and ask rather than guess.

Record the answer in the **Decisions** table. For a staged store rollout, also write the planned steps and the halt thresholds into the record (e.g. halt if crash-free sessions fall below 99.5% or ANRs rise above 0.5%).

**Do not start Step 3 until @Zeyad says go.**

## Step 3: Build and Stage

### Store path

**3.1 Version-bump PR.** In a worktree on `T-NNN.1/version-X.Y.Z` — the bump sub-task from Step 1, never the release task's ID — bump:

- Android `versionName` → `X.Y.Z` and `versionCode` → the next free code.
- iOS marketing version → `X.Y.Z` and build number → the next free build.

The platforms can drift, so take **each platform's** next free build number from what its store already holds — the highest code across all Play tracks, and the highest build in TestFlight / App Store Connect — not from the other platform and not from the last tag. If you cannot read them (no API access from this machine), ask @Zeyad for them. Commit, then open the PR with `/create-pr`; it merges through review like any change. **Never commit a version bump on `main`.**

Re-check Gate 1 against the bump's merge commit: it needs its own green main-verification run.

**3.2 Tag.** Create an annotated tag on that **exact SHA** in the repo's format, and push it with an explicit refspec:

```bash
git tag -a "<tag>" "<bump-merge-sha>" -m "Release X.Y.Z"
git push origin "refs/tags/<tag>:refs/tags/<tag>"
```

Push from a worktree whose branch is **not** `main` (the release worktree). Some pre-push hooks gate on the current branch rather than on the pushed ref, and will refuse a tag pushed from `main`. Pushing this one tag is the release-tag exception in `@.claude/rules/shared/shared-standards.md` § Push Policy, authorized by @Zeyad's Gate 6 go; this skill never pushes a branch — branches go through `/create-pr`.

**3.3 CI builds, signs and uploads a draft.** The tag workflow builds the release artifacts, signs them with keys held only in CI secrets, and uploads them to the store **as a draft**. Do not build or sign a release locally to "help": a local release build with no keystore configured can quietly fall back to the debug key and produce a binary that looks fine and is not the release. Watch the run by ID:

```bash
gh run list --workflow "<release workflow>" --branch "<tag>" --json databaseId,status,url
gh run watch "<run-id>" --exit-status
```

To abort, cancel the run **before its upload step** (`gh run cancel <run-id>`). A cancelled run uploads nothing.

**3.4 If the tag run fails before anything shipped**, fix it through a PR like any other change. Moving the tag to the fix commit needs @Zeyad's explicit approval; then:

```bash
# Capture what the REMOTE holds before rewriting anything. For an annotated tag that is the
# tag object's SHA, not the commit's — and a local rev-parse after `git tag -f` already
# returns the new object, which would make the lease check nothing.
OLD_TAG_OBJ=$(git ls-remote origin "refs/tags/<tag>" | cut -f1)
OLD_COMMIT=$(git ls-remote origin "refs/tags/<tag>^{}" | cut -f1)

git tag -fa "<tag>" "<fix-merge-sha>" -m "Release X.Y.Z"
git push --force-with-lease="refs/tags/<tag>:$OLD_TAG_OBJ" origin "refs/tags/<tag>:refs/tags/<tag>"

NEW_TAG_OBJ=$(git rev-parse "refs/tags/<tag>")
NEW_COMMIT=$(git rev-parse "refs/tags/<tag>^{commit}")
```

Record both runs, the approval, and the old and new tag-object SHAs with the commits they point at (`$OLD_TAG_OBJ` → `$OLD_COMMIT`, `$NEW_TAG_OBJ` → `$NEW_COMMIT`) under **What happened**. Never move a tag once any artifact built from it reached a store track — see 3.4a.

**3.4a Once anything reached a store, the version is spent.** When any artifact built from the tag reached a store track — any Play track, TestFlight or App Store Connect — or Gate 7 comes back **Not met** after the upload, that version and its build numbers are used up: the store keeps the build forever, and the tag must keep recording what was uploaded. Do not move the tag and do not reuse a build number. Instead:

1. Open a new bump PR — a new sub-task as in Step 1 (`[T-NNN.2] Version bump …`) — with each platform's next free build number, read from the stores as in 3.1.
2. Create a new tag on its merge commit, usually the next patch version.
3. Re-run the full gates against the new SHA, from Gate 1 through a fresh Gate 6 go to Gate 7 on the new artifact, including every `L` gate.
4. Record the spent version, why it was spent and the new version under **What happened**, and move the record's **Platforms** table to the new numbers.

Leave the old tag in place.

**3.5 iOS.** Follow the project's archive runbook (Step 0).

- If the release workflow builds and uploads the IPA, use **that** file.
- Otherwise the archive is **@Zeyad's step**. The agent prepares a **clean detached worktree of the tag** (`git worktree add --detach "<dir>" "refs/tags/<tag>"`) — never a working checkout — gives @Zeyad its path and the runbook section, and stops. @Zeyad archives, signs and uploads per the runbook. The agent never runs `xcodebuild archive` or `-exportArchive` with a distribution identity, never imports, exports or reads certificates, profiles or keys, and never uploads.
- When @Zeyad hands back the uploaded IPA, the agent runs the project's IPA verification script on that exact file and records the file, the script's result, the build number and who archived it in **Provenance**. A failing script after the upload means the version is spent (3.4a).

**3.6 Store submission rules.**

- Some store APIs submit for review when an edit is committed. **Treat an API commit as a submission**, and make one only when @Zeyad has approved that submission.
- **@Zeyad's Gate 6 go is the approval for any submission the tag-triggered CI upload performs** — for example, a Play edit commit while managed publishing is on. The tag push starts that upload, so when asking for the go, name exactly what the workflow will submit and to which track. If the workflow would submit more than that (say, commit straight to production with managed publishing off), cancel the run before its upload step and stop. Any other API commit needs its own approval.
- A first production release needs its countries / regions set in the console, and the CI service account needs permission to release to production. Check both before the tag, not after the upload fails.
- On the App Store, the first in-app purchase must be submitted together with an app version.

**3.7 Release mode.** Google Play: draft upload with **managed publishing** on, so nothing goes live until it is published. App Store: **manual release** of the approved version. Both wait for Step 4.

### Service path

After @Zeyad's go, invoke the `sentinel-devops-sre` agent:
```
Deploy X.Y.Z (task T-NNN) to staging. Artifact: <image / package from the main-verification run on <sha>>.
Rollout chosen at go/no-go: [staged | full].
Hold at staging for Gate 7. Include the rollback plan (handoff template #13).
```

## Gate 7: The Exact Artifact — @Apex

`@.claude/rules/shared/shared-standards.md` § Release Process item 7. Every earlier gate can pass against a different binary than the one that ships; this one checks **the** binary.

Invoke the `apex-qa-engineer` agent:
```
Verify the exact artifact for release X.Y.Z. Report each check as Met, Partly met (with the
follow-up named) or Not met. Never report Met for a check that did not run.
```

**Store path**

1. **Install the artifact being shipped**, fresh, on a device with no app data, and cold-launch it. That means the AAB/APK from the tag's CI run or the store-delivered build, and the uploaded IPA via TestFlight or a device. A build from the same tag is not the same artifact. A debug build is not the release build.
2. **Device classes**: a phone **and** a tablet on each platform. App Review tests iPhone-only apps on an iPad.
3. **Run the project's artifact-verification script** on that same file if one exists (for example, an IPA check that the production keys and the version are baked in).
4. **Prove the bytes where the store exposes a hash.** Google Play: the Play Developer API exposes the uploaded bundle's SHA-256; compare it with `shasum -a 256 <file>`. App Store Connect exposes no hash of an uploaded build, so iOS provenance is the CI run ID (or @Zeyad's local archive, 3.5), the build number App Store Connect shows, and the verification script's result on the uploaded file. iOS is **not** Partly met merely for lacking a store hash. Write the artifact, its hash or iOS provenance, and the source run into **Provenance**.
5. When a check cannot run, mark the gate **Partly met** and name the follow-up. Typical cases: a Play-signed APK with a licence check will not launch on an emulator without a signed-in account; an App Store IPA cannot run on a simulator. Never mark it Met.

**Service path** — verify the artifact on staging is the one that will be promoted: the image digest (or package checksum) on staging equals the digest CI built from the tagged commit, it cold-starts cleanly, and the smoke checks pass. Record digest and source run in **Provenance**.

Run the `L` gates that check the shipped artifact here too.

**STOP on Not met.** Partly met goes to @Zeyad with the named follow-up; it is their call.

## Step 4: Publish

Re-present the Gate 6 checklist with Gate 7 and every `L` gate filled in.

**Store path.** Ask @Zeyad to publish, giving the exact action:

- **Google Play:** publish the managed-publishing change (100%, or the first staged percentage).
- **App Store:** two clicks, both @Zeyad's, with a wait between them. Gate 7 completes **before** submission, so the build Apple reviews is the one already verified. First, Submit for Review (with the approved What's New); then wait for Apple's approval; then Release this version (immediately, or with phased release). Report the review status while waiting, and treat a rejection as a failed gate.

For a staged rollout, each later percentage increase is also @Zeyad's click — list the planned steps and the halt thresholds each time, with the current crash-free rate.

**Service path.** On go, Sentinel promotes from staging per the chosen rollout:
- **Staged:** canary at 5% traffic, 30-minute soak, then production. Auto-rollback if the error rate rises more than 1% or the crash-free rate drops below 99.5%.
- **Full:** straight to production.

Then tag the deployed commit in the repo's format, annotated, with an explicit refspec as in 3.2 — the same Push Policy release-tag exception.

## Step 5: Post-Release

1. **Confirm it is published, not just uploaded.** Before announcing anything or telling testers, check **both** the store API and the console's track page (ask @Zeyad for the console check if you cannot see it). An upload that was never published is a real failure mode: testers spend a cycle re-reporting bugs that are already fixed. Service path: confirm production is serving the verified digest.
2. Morgan publishes the release notes. Scroll updates public documentation. Echo prepares support for the new features.
3. **Note the release on the board.** On `github` the shipped issues are already closed, so there is no Done column to clear — add the `released:vX.Y.Z` label to the issues in the release, or skip if the repo uses GitHub Releases for that. On `markdown` clear the Done column; this is a board edit, so it rides with the release record rather than landing on `main` on its own (see `@.claude/rules/shared/board-in-pr.md`): commit `board-context.md` on the **same branch** as the release record and open one PR carrying both. Do not commit the Done-column clear directly on `main` as a post-merge cleanup step.
4. **Release feed for downstream consumers (conditional — skip silently when absent).** Some products keep a *shared context directory* that downstream tooling reads to turn a shipped release into launch work. It is identified by shape, not by name: a directory containing both `releases.md` and `config.md`, typically a `*-shared-context` sibling of this repo. If — and only if — such a directory exists, append one row to its `releases.md`:

   | Column | Value |
   |---|---|
   | Date | release date |
   | Version | `vX.Y.Z` |
   | Summary | the user-facing summary from the release notes |
   | Size | `patch` / `minor` / `major` / `tier-1` |
   | Consumed | `no` |

   This is a plain file append into a directory that already exists outside this repo. It installs nothing, requires no plugin, and creates nothing when the directory is absent — in that case do not create it, do not mention it, and move on.

   The reader of this feed is whatever downstream tooling the product has configured; the `marketing-agency` plugin's `launch-from-release` is one such reader. That plugin is **not** part of tech-agency: it lives in its own repository, ships from its own marketplace, and is installed separately. Nothing here installs it, and its absence is the normal case — the shared-context directory is the entire contract between the two.
5. **Finish the release record** and open its PR with `/create-pr` from the release worktree, on `T-NNN/release-X.Y.Z`. This PR is the release task's → Done (Step 1): on `github` its body carries `Closes #<release issue>`; on `markdown` the Done commit and the board edit from item 3 ride in it.

## Release Record

Path, per `@.claude/rules/shared/handoff-protocol.md`:

```
docs/artifacts/release-record/{Task-Id}-Release Record-vX.Y.Z.md
```

Template:

```markdown
# Release X.Y.Z

**Status:** [In progress | Published | Rolling out (N%) | Halted | Abandoned]
**Task:** T-NNN Release X.Y.Z
**Path:** [Store | Service]
**Base:** <last-tag> (<sha>) · **Tag:** <tag> on <sha>

## Platforms

| Platform | Version | Build number | Track / environment |
|---|---|---|---|
| Android | X.Y.Z | <versionCode> | <track> |
| iOS | X.Y.Z | <build> | TestFlight → App Store |

## Setup

<!-- What Step 0 discovered: tag format, workflows, version locations, scripts, runbook. -->

## Decisions

| Question | Decision | By |
|---|---|---|
| Rollout | [Staged: steps + halt thresholds | Full] — evidence: … | @Zeyad |
| <waived gate> | Waived — reason | @Zeyad |

## What's in it

<!-- The four Step 1 tables: Features, Bug fixes, Tech / tooling, Dependency updates. -->

## Known issues

## What happened

1. <!-- Numbered, in order: bump PR, tag, each CI run (ID, result), failures, tag moves and
        their approval, uploads, publish, rollout steps. -->

## Provenance

| Artifact | SHA-256 / digest | Source run | Store / registry match |
|---|---|---|---|

## Store listing changes

<!-- Only if any. -->

## Gates

| Gate | Owner | Result | Notes |
|---|---|---|---|
| 1 Code complete | @Atlas | Met / Partly met / Waived / Pending | |
| 2 QA | @Apex | | |
| 3 Security | @Shield | | |
| L1 … | | | |
| 4 Documentation | @Scroll | | |
| 5 Release notes | @Morgan | | |
| 6 Go / no-go | @Zeyad | | |
| 7 Exact artifact | @Apex | | |

## Bugs found during the release

## Release notes

### Google Play — What's new (<locale>, N/500 chars)

### App Store — What's New

<!-- Service path: the changelog / release-page text instead. -->
```
