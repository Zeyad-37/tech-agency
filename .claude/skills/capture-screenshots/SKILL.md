---
name: capture-screenshots
description: "Capture before/after screenshots for UI changes using Paparazzi (Android), swift-snapshot-testing (iOS), and Playwright (Web). Produces a visual comparison table for PR review. Accepts --base <branch> to diff against a non-default base (epic integration branches). Invoked automatically and non-skippably by /create-pr on every UI PR; also usable directly when the user says 'capture screenshots', 'visual diff', 'before after screenshots', or 'screenshot comparison'."
---

# Capture Screenshots — Automated Visual Evidence for UI Changes

This skill generates before/after screenshots to visually demonstrate UI changes. It detects which platforms are affected, runs the appropriate screenshot tooling against both the base branch and the feature branch, and produces a markdown comparison table for the PR.

## When to Use

- **Automatically, from `/create-pr` Step 3b** — this is the primary caller, and the invocation is not optional (see "Called by `/create-pr`" below)
- When a reviewer requests visual proof of a UI change
- Manually, when the user says "capture screenshots" or "visual diff"

## Step 0: Parse Arguments and Resolve the Base

```bash
BASE_FLAG=""
while [ $# -gt 0 ]; do
  case "$1" in
    --base)
      # Check $# BEFORE `shift 2`: on a bare trailing `--base`, `shift 2` fails
      # and shifts nothing, so an unguarded loop spins forever.
      [ $# -ge 2 ] && [ -n "$2" ] || { echo "❌ --base requires a branch name."; exit 1; }
      BASE_FLAG="$2"; shift 2 ;;
    --base=*)
      BASE_FLAG="${1#--base=}"
      [ -n "$BASE_FLAG" ] || { echo "❌ --base= requires a branch name."; exit 1; }
      shift ;;
    *)        shift ;;
  esac
done

if [ -n "$BASE_FLAG" ]; then
  BASE="$BASE_FLAG"
else
  BASE=$(git remote show origin 2>/dev/null | sed -n 's/.*HEAD branch: //p')
  [ -n "$BASE" ] || BASE=main
fi

git fetch origin "$BASE"
echo "Capture base: origin/$BASE"
```

**Never hardcode `main`.** `/create-pr` always passes `--base "$BASE"`; a branch cut from an epic integration branch would otherwise be diffed against the wrong tree and produce a "before" state that never existed. Every diff and every capture below runs against `origin/$BASE`, never a local `main` ref — under the worktree-first rule the default branch is checked out in the main repo and cannot be checked out again here anyway.

## Step 1: Detect Affected Platforms

Use the **canonical UI-change detection** defined in `/create-pr` Pre-flight 0b — the single source of truth for "is this a UI change" across the ship path. It is restated here only because this skill can be invoked standalone; if the two ever diverge, `/create-pr`'s copy is authoritative and this one is the bug.

```bash
UI_EXT_RE='\.(kt|kts|swift|tsx|jsx|vue|css|scss)$'
UI_NAME_RE='([Ss]creen|[Cc]ontent|Composable|Preview|Theme|Typography|Spacing|Colors?\.|[Dd]esign[Ss]ystem|View\.(swift|kt)|/[Uu][Ii]/|/[Cc]omponents?/|/[Vv]iews?/|/[Ss]tyles?/|\.(css|scss)$|page\.(tsx|jsx)|layout\.(tsx|jsx))'
UI_EXCLUDE_RE='(ViewModel|Contract|InputHandler|Repository|UseCase|Mapper|Dto|Api|Service)\.(kt|kts|swift|ts|tsx)$'

CHANGED_FILES=$(git diff --name-only "origin/$BASE"..HEAD \
  | grep -E "$UI_EXT_RE" | grep -E "$UI_NAME_RE" | grep -vE "$UI_EXCLUDE_RE")

# Split the canonical set by platform — no second detection pass, just a partition.
HAS_ANDROID=$(echo "$CHANGED_FILES" | grep -E '\.(kt|kts)$' | head -1)
HAS_IOS=$(echo "$CHANGED_FILES"     | grep -E '\.swift$'    | head -1)
HAS_WEB=$(echo "$CHANGED_FILES"     | grep -E '\.(tsx|jsx|vue|css|scss)$' | head -1)
```

Report which platforms were detected:

```
Platforms with UI changes detected (base: origin/{BASE}):
  - Android (Compose): YES/NO
  - iOS (SwiftUI): YES/NO
  - Web (React): YES/NO
```

**If `CHANGED_FILES` is empty**, exit with the distinguishable outcome token `SCREENSHOTS_NO_UI_DETECTED` so the caller can branch on it rather than guessing from an empty table:

```
SCREENSHOTS_NO_UI_DETECTED

No UI-related file changes detected vs origin/{BASE}. Visual evidence is not required.
If UI changes are present but were not detected, provide screenshots manually.
```

`/create-pr` treats this token as a **detection disagreement** and falls back to a review-blocking manual-evidence note — it does not silently open a UI PR with no visual evidence. See `/create-pr` Step 3b's outcome table.

## Outcome Tokens (the contract with `/create-pr`)

This skill's last line is always exactly one of these tokens. `/create-pr` Step 3b branches on it:

| Token | Meaning |
|---|---|
| `SCREENSHOTS_CAPTURED` | At least one before/after pair was produced; the comparison table follows. |
| `SCREENSHOTS_TOOLING_MISSING` | UI changes exist but the required tooling is not configured for an affected platform. Falls through to Step 4's manual request. |
| `SCREENSHOTS_NO_UI_DETECTED` | No UI changes found (see above). |

Emit the token even on partial success: if Android captured and iOS lacked tooling, emit `SCREENSHOTS_TOOLING_MISSING` and name the platform — a partially-empty table must never read as a clean pass.

## Step 2: Capture Screenshots — Per Platform

For each detected platform, capture screenshots against the **base branch** (before) and the **feature branch** (after).

### General Flow (All Platforms) — a detached worktree, never a stash

The "before" state is captured from a **throwaway detached worktree checked out at `origin/$BASE`**. The current worktree is never mutated: no stash, no checkout, no branch switch.

> **Why not stash + checkout?** Two reasons, both of which have bitten this skill:
>
> 1. **`git stash pop` on a clean tree pops someone else's stash.** `git stash --include-untracked` creates *no* entry when the tree is clean, so an unguarded `git stash pop` afterwards pops whatever was already on the stack — and the stash stack is **shared across every worktree and concurrent session**, which is exactly the configuration worktree-first encourages. Since `/create-pr` invokes this skill automatically and non-skippably on every UI PR, that failure mode is on the default path of every UI change.
> 2. **`git checkout $BASE` cannot work under worktree-first.** The default branch is checked out in the main repo, so git refuses to check it out again in a worktree. The capture would abort before taking a single screenshot.
>
> A detached worktree has neither problem: it needs no clean tree, touches no stash, and `--detach` means no branch is claimed, so it coexists with the main checkout.

```bash
FEATURE_BRANCH=$(git branch --show-current)
mkdir -p .screenshots/before .screenshots/after

# Create a throwaway worktree pinned to the base commit. --detach claims no
# branch, so this works even though origin/$BASE is checked out elsewhere.
BEFORE_WT="$(mktemp -d "${TMPDIR:-/tmp}/screenshots-before-XXXXXX")"
rm -rf "$BEFORE_WT"                      # mktemp -d created it; worktree add needs it absent
git worktree add --detach "$BEFORE_WT" "origin/$BASE"

# Always clean up the throwaway worktree, even if a capture step fails.
cleanup_before_wt() {
  git worktree remove --force "$BEFORE_WT" || git worktree prune
}
trap cleanup_before_wt EXIT

# 1. Capture "before" by running the platform tooling INSIDE $BEFORE_WT,
#    writing into this worktree's .screenshots/before/.
# 2. Capture "after" by running the same tooling in the current worktree,
#    writing into .screenshots/after/.
# Neither step switches branches or touches the stash.
```

Verification of this flow (run against a scratch repo with a dirty tree): the before-worktree resolves to the base content, the current worktree keeps the feature content, untracked files survive untouched, `git branch --show-current` is unchanged, and `git worktree remove --force` leaves the worktree list back at one entry.

**Error handling:** every command below runs **without `2>/dev/null`**. A silenced failure here is worse than a loud one — it produces an empty `.screenshots/` directory, which renders as a Visual Changes table with no rows, which still satisfies `/code-review`'s "does a Visual Changes section exist" check. A capture that fails must say so and must drive the `SCREENSHOTS_TOOLING_MISSING` outcome.

---

### Android — Paparazzi

**Tool:** [Paparazzi](https://github.com/cashapp/paparazzi) — JVM-only screenshot testing for Jetpack Compose. No emulator or device required.

**Prerequisites:**
- Paparazzi Gradle plugin configured in the module's `build.gradle.kts`
- `@Preview` composables or dedicated Paparazzi test classes for the changed screens

**How to detect if Paparazzi is set up:**

```bash
grep -r "paparazzi" --include="*.gradle.kts" --include="*.gradle" -l
```

If Paparazzi is not configured, fall back to manual screenshots (see Step 4).

**Capture commands:**

```bash
# Record golden images (captures screenshots of all Paparazzi tests).
# Run only for the affected module(s) to save time.
AFFECTED_MODULES=$(echo "$CHANGED_FILES" | grep -E '\.kts?$' | sed 's|/src/.*||' | sort -u)

CAPTURE_FAILED=0

# Gradle TASK PATHS are colon-separated, not slash-separated: a module directory
# `features/notes/ui` is the task path `:features:notes:ui`. Passing the raw
# directory produces `features/notes/ui:recordPaparazziDebug`, which Gradle
# rejects as an unknown project — the same conversion /create-pr Step 4b does.
gradle_path() { printf ':%s' "$(echo "$1" | tr '/' ':')"; }

# --- Before: run inside the detached base worktree ---
for module in $AFFECTED_MODULES; do
  GP="$(gradle_path "$module")"
  echo "→ before: ${GP}:recordPaparazziDebug"
  if (cd "$BEFORE_WT" && ./gradlew "${GP}:recordPaparazziDebug"); then
    SRC="$BEFORE_WT/${module}/src/test/snapshots"
    if [ -d "$SRC" ]; then
      mkdir -p ".screenshots/before/${module##*/}"
      cp -R "$SRC/." ".screenshots/before/${module##*/}/"
    else
      echo "⚠️  No snapshots produced for ${module} on the base — treating as a new screen."
    fi
  else
    echo "❌ Paparazzi record failed for ${module} on origin/${BASE}."
    CAPTURE_FAILED=1
  fi
done

# --- After: run in the current worktree (the feature branch) ---
for module in $AFFECTED_MODULES; do
  GP="$(gradle_path "$module")"
  echo "→ after: ${GP}:recordPaparazziDebug"
  if ./gradlew "${GP}:recordPaparazziDebug"; then
    SRC="${module}/src/test/snapshots"
    if [ -d "$SRC" ]; then
      mkdir -p ".screenshots/after/${module##*/}"
      cp -R "$SRC/." ".screenshots/after/${module##*/}/"
    else
      echo "❌ Paparazzi reported success but produced no snapshots for ${module}."
      CAPTURE_FAILED=1
    fi
  else
    echo "❌ Paparazzi record failed for ${module} on ${FEATURE_BRANCH}."
    CAPTURE_FAILED=1
  fi
done
```

If `CAPTURE_FAILED` is 1, Android contributes `MANUAL NEEDED` to the Step 5 report and the run's outcome token becomes `SCREENSHOTS_TOOLING_MISSING`. Never swallow the Gradle exit code and never report captured screenshots that don't exist on disk.

**If specific screens are known**, run only the relevant Paparazzi test classes (same colon-path rule):

```bash
./gradlew "$(gradle_path "$module"):testDebugUnitTest" --tests "*${ScreenName}ScreenshotTest"
```

---

### iOS — swift-snapshot-testing

**Tool:** [swift-snapshot-testing](https://github.com/pointfreeco/swift-snapshot-testing) — Snapshot testing for SwiftUI previews and UIKit views.

**Prerequisites:**
- `swift-snapshot-testing` added as a Swift Package dependency
- Snapshot test files for the changed screens/components

**How to detect if swift-snapshot-testing is set up:**

```bash
grep -r "swift-snapshot-testing\|SnapshotTesting" --include="*.swift" --include="Package.swift" -l
```

If not configured, fall back to manual screenshots (see Step 4).

**Capture commands:**

```bash
REPO_ROOT="$(pwd)"

run_ios_snapshots() {   # $1 = worktree root to run in, $2 = destination dir
  local root="$1" dest="$2"
  ( set -o pipefail
    cd "$root/iosApp" && SNAPSHOT_TESTING_RECORD=1 xcodebuild test \
      -scheme "AppTests" \
      -destination "platform=iOS Simulator,name=iPhone 16,OS=latest" \
      -only-testing:"AppTests/SnapshotTests" 2>&1 | xcpretty )
  local rc=$?
  if [ "$rc" -ne 0 ]; then
    echo "❌ xcodebuild snapshot run failed in ${root} (exit ${rc})."
    return 1
  fi
  if [ ! -d "$root/iosApp/Tests/__Snapshots__" ]; then
    echo "❌ xcodebuild succeeded but produced no __Snapshots__ in ${root}."
    return 1
  fi
  mkdir -p "$dest"
  cp -R "$root/iosApp/Tests/__Snapshots__/." "$dest/"
}

# Before — the detached base worktree. After — the current worktree.
run_ios_snapshots "$BEFORE_WT"   "$REPO_ROOT/.screenshots/before/ios" || CAPTURE_FAILED=1
run_ios_snapshots "$REPO_ROOT"   "$REPO_ROOT/.screenshots/after/ios"  || CAPTURE_FAILED=1
```

`set -o pipefail` is required: without it the pipe into `xcpretty` masks `xcodebuild`'s exit code and a failed build reports success. Note the "before" run happens in a worktree that has never been built — expect a cold build, and do not interpret its duration as a hang.

**Alternative — if using SwiftUI Previews with a dedicated snapshot target**, substitute the scheme and keep the same structure (pipefail, exit-code check, existence check):

```bash
( set -o pipefail
  cd "$root/iosApp" && xcodebuild test \
    -scheme "SnapshotTests" \
    -destination "platform=iOS Simulator,name=iPhone 16,OS=latest" 2>&1 | xcpretty )
```

---

### Web — Playwright

**Tool:** [Playwright](https://playwright.dev/) — Headless browser screenshots for React/Next.js pages.

**Prerequisites:**
- Playwright installed (`npx playwright install` or in devDependencies)
- Dev server runnable (`npm run dev` or `npx next dev`)

**How to detect if Playwright is set up:**

```bash
grep -r "playwright" --include="package.json" -l
```

If not configured, fall back to manual screenshots (see Step 4).

**Capture commands:**

> **The `&` trap this section used to contain.** `npm run build --silent || npm run dev &` does **not** mean "build, else start the dev server in the background". `&` terminates the entire AND-OR list, so the whole `build || dev` list is backgrounded and `$!` is its PID, not the server's. Combined with a fixed `sleep 5` and `2>/dev/null` on every `playwright screenshot`, the result was: nothing ever served port 3000, every screenshot failed silently, and Step 5 still reported success. The two branches are now separate statements, the server readiness is **polled** rather than slept at, and no failure is silenced.

```bash
PORT="${PORT:-3000}"

# Poll until the server actually answers, instead of guessing with `sleep 5`.
wait_for_port() {
  local port="$1" timeout="${2:-90}" deadline
  deadline=$(( $(date +%s) + timeout ))
  while [ "$(date +%s)" -lt "$deadline" ]; do
    if curl -sSf -o /dev/null "http://localhost:${port}/"; then return 0; fi
    if command -v nc >/dev/null && nc -z 127.0.0.1 "$port"; then return 0; fi
    sleep 1
  done
  return 1
}

# Start a server for a given worktree root. Sets the global $DEV_PID on success.
#
# It must NOT return the PID on stdout. `DEV_PID=$(start_server …)` would
# deadlock: the backgrounded server inherits the command-substitution pipe and
# keeps it open, so the substitution never sees EOF and blocks until the server
# exits — which is never. (It would also splice all of npm's stdout into
# $DEV_PID.) Hence: a global, and every diagnostic on stderr.
DEV_PID=""
start_server() {   # $1 = worktree root; sets $DEV_PID, returns 0 on success
  local root="$1"
  DEV_PID=""
  ( cd "$root" && npm ci ) >&2 || { echo "❌ npm ci failed in $root" >&2; return 1; }
  # Prefer a production build + start; fall back to the dev server.
  # NOTE: these are separate statements precisely so `&` backgrounds only the
  # server, never the whole conditional.
  if ( cd "$root" && npm run build ) >&2; then
    ( cd "$root" && npm run start -- --port "$PORT" ) >&2 &
  else
    echo "⚠️  build failed — falling back to the dev server." >&2
    ( cd "$root" && npm run dev -- --port "$PORT" ) >&2 &
  fi
  DEV_PID=$!
  if ! wait_for_port "$PORT" 90; then
    echo "❌ No server answered on port $PORT within 90s (root=$root)." >&2
    kill "$DEV_PID" 2>/dev/null
    DEV_PID=""
    return 1
  fi
  return 0
}

# Determine affected pages/routes from changed files
AFFECTED_PAGES=$(echo "$CHANGED_FILES" | grep -E '\.(tsx|jsx)$' | grep -E 'app/.*page\.' \
  | sed 's|src/app||;s|/page\.tsx$||;s|/page\.jsx$||' | sort -u)

shoot() {   # $1 = phase (before|after)
  local phase="$1" route safe
  mkdir -p ".screenshots/${phase}/web"
  for route in $AFFECTED_PAGES; do
    safe=$(echo "$route" | tr '/' '_' | sed 's/^_//')
    [ -n "$safe" ] || safe="index"
    npx playwright screenshot "http://localhost:${PORT}${route}" \
      ".screenshots/${phase}/web/${safe}.png" \
      || { echo "❌ screenshot failed: ${phase} ${route}"; CAPTURE_FAILED=1; }
    npx playwright screenshot --color-scheme=dark "http://localhost:${PORT}${route}" \
      ".screenshots/${phase}/web/${safe}-dark.png" \
      || { echo "❌ screenshot failed: ${phase} ${route} (dark)"; CAPTURE_FAILED=1; }
    npx playwright screenshot --viewport-size="375,812" "http://localhost:${PORT}${route}" \
      ".screenshots/${phase}/web/${safe}-mobile.png" \
      || { echo "❌ screenshot failed: ${phase} ${route} (mobile)"; CAPTURE_FAILED=1; }
  done
}

# --- Before: serve the detached base worktree ---
# Call it as a plain command (never `$( )`) so the backgrounded server does not
# hold a command-substitution pipe open; $DEV_PID is set by the function.
if start_server "$BEFORE_WT"; then
  shoot before
  kill "$DEV_PID"; wait "$DEV_PID" 2>/dev/null
else
  CAPTURE_FAILED=1
fi

# --- After: serve the current worktree ---
if start_server "$REPO_ROOT"; then
  shoot after
  kill "$DEV_PID"; wait "$DEV_PID" 2>/dev/null
else
  CAPTURE_FAILED=1
fi
```

Both servers bind the same port, so they must not overlap — the "before" server is killed and reaped (`wait`) before the "after" server starts. If the project's dev server ignores `--port`, set `PORT` and let the framework's own env var pick it up instead.

**For component-level screenshots** (if Storybook is available):

```bash
if grep -q "storybook" package.json; then
  npx storybook build --quiet -o .storybook-static \
    || { echo "❌ storybook build failed"; CAPTURE_FAILED=1; }
  npx http-server .storybook-static -p 6006 &
  STORYBOOK_PID=$!
  if wait_for_port 6006 60; then
    npx playwright screenshot \
      "http://localhost:6006/iframe.html?id=${component_story_id}" \
      ".screenshots/after/web/${component}.png" \
      || { echo "❌ storybook screenshot failed"; CAPTURE_FAILED=1; }
  else
    echo "❌ Storybook static server never answered on 6006."
    CAPTURE_FAILED=1
  fi
  kill "$STORYBOOK_PID"; wait "$STORYBOOK_PID" 2>/dev/null
fi
```

## Step 3: Generate Comparison Table

After capturing both sets of screenshots, generate a markdown comparison table:

```bash
# List all screenshot files from 'after' (the feature branch defines what screens exist)
SCREENSHOTS=$(find .screenshots/after -type f -name '*.png' | sort)
```

Build the comparison markdown:

```markdown
## Visual Changes

| Screen | Before | After |
|--------|--------|-------|
| {screen-name} | ![before](.screenshots/before/{path}) | ![after](.screenshots/after/{path}) |
| {screen-name} (dark) | ![before](.screenshots/before/{path}) | ![after](.screenshots/after/{path}) |
| {screen-name} (mobile) | ![before](.screenshots/before/{path}) | ![after](.screenshots/after/{path}) |
```

**For new screens** (no "before" exists): show "N/A — new screen" in the Before column.

**For deleted screens** (no "after" exists): show "N/A — removed" in the After column.

### Uploading to PR

When the PR is pushed (via `/create-pr`), screenshots should be included. Two options:

**Option A — Commit to branch** (preferred for projects using Paparazzi/swift-snapshot-testing golden files):

```bash
git add .screenshots/
git commit -m "[${TASK_ID}] @${AGENT}: Add visual evidence screenshots"
```

**Option B — Upload as PR comment** (for projects that don't want screenshots in git):

```bash
# After PR is created, add a comment with the visual comparison
gh pr comment ${PR_NUMBER} --body "$(cat <<'EOF'
## Visual Changes

| Screen | Before | After |
|--------|--------|-------|
...
EOF
)"
```

> **Note:** GitHub renders images in PR comments from committed files or external URLs. If screenshots are committed to the branch, use relative paths. If using external hosting (e.g., S3, Imgur via CI), replace paths with URLs.

## Step 4: Fallback — Manual Screenshot Request

If automated screenshot tools are not configured for a detected platform, ask the user to provide screenshots manually:

```
Automated screenshot capture is not available for {platform}:
  - {reason: e.g., "Paparazzi is not configured in the Gradle build"}

To add visual evidence manually:
  1. Take screenshots of the affected screens on the base branch (before)
  2. Take screenshots on this branch (after)
  3. Save them to:
     - .screenshots/before/{platform}/{screen-name}.png
     - .screenshots/after/{platform}/{screen-name}.png
  4. Run `/capture-screenshots` again to generate the comparison table

Alternatively, you can paste screenshots directly into the GitHub PR description after it's created.
```

## Step 5: Report Results

After capturing (or failing to capture) screenshots for all platforms, count what is **actually on disk** — never report a number derived from what was attempted:

```bash
count_shots() { find ".screenshots/$1" -type f -name '*.png' 2>/dev/null | wc -l | tr -d ' '; }
echo "before: $(count_shots before)  after: $(count_shots after)"
```

```
Visual evidence (base: origin/{BASE}):

  Android (Paparazzi): {N} screenshots captured / MANUAL NEEDED / NOT APPLICABLE
  iOS (swift-snapshot-testing): {N} screenshots captured / MANUAL NEEDED / NOT APPLICABLE
  Web (Playwright): {N} screenshots captured / MANUAL NEEDED / NOT APPLICABLE

Screenshots saved to .screenshots/before/ and .screenshots/after/
```

Then emit exactly one outcome token as the final line:

- **`SCREENSHOTS_CAPTURED`** — `CAPTURE_FAILED` is 0 **and** at least one file exists under `.screenshots/after/`.
- **`SCREENSHOTS_TOOLING_MISSING`** — `CAPTURE_FAILED` is 1, or a detected platform had no tooling configured, or `.screenshots/after/` is empty despite UI changes. Name the platform and the reason.
- **`SCREENSHOTS_NO_UI_DETECTED`** — Step 1 found nothing (already emitted there).

A zero-file capture must never emit `SCREENSHOTS_CAPTURED`. That is precisely the failure the empty-table bug produced.

## Integration with Other Skills

### Called by `/create-pr` (automatic and non-skippable)

`/create-pr` Step 3b invokes this skill **automatically** whenever its canonical UI detection (Pre-flight 0b) finds UI changes, passing `--base "$BASE"`. This skill does **not** prompt the user, does not ask whether to run, and offers no opt-out — `/create-pr` is authoritative and its Step 3b states: *"Do NOT prompt the user to opt out and do NOT proceed without visual evidence."*

The contract is:

1. `/create-pr` detects UI changes and calls `/capture-screenshots --base "$BASE"`.
2. This skill captures what it can and returns a comparison table plus exactly one outcome token.
3. `/create-pr` branches on the token (see its Step 3b outcome table): embed the table, or emit the review-blocking manual-evidence note.

An earlier version of this section described a `UI changes detected. Run /capture-screenshots?` prompt. That was wrong and contradicted `/create-pr` — there is no such prompt. When invoked directly by a user, this skill still runs unconditionally; the only "should I run this" decision belongs to whoever typed the command.

### Checked by `/code-review`

During code review, `/code-review` checks:
1. Does the PR have UI changes? (using `/create-pr` Pre-flight 0b's canonical detection — the same regex, not a restatement)
2. If yes, is there a "Visual Changes" section in the PR body?
3. Does that section contain actual image references, not an empty table or a manual-evidence warning?
4. If missing or empty, flag it as a required change

Point 3 matters: an empty Visual Changes table satisfies a "section exists" check while carrying no evidence at all. `/code-review` must assert on rows, not on the heading.

## Cleanup

After the PR is merged or closed, clean up local screenshots:

```bash
rm -rf .screenshots/
```

Add `.screenshots/` to `.gitignore` if using Option B (PR comment upload) to avoid accidentally committing temporary files.

## Tool Setup Guides

If a project doesn't have the screenshot tools configured, here are setup pointers:

### Paparazzi (Android)

```kotlin
// build.gradle.kts (module level)
plugins {
    id("app.cash.paparazzi")
}

// Create a screenshot test
class NotesListScreenshotTest {
    @get:Rule
    val paparazzi = Paparazzi(
        deviceConfig = DeviceConfig.PIXEL_6,
        theme = "android:Theme.Material3.DayNight.NoActionBar",
    )

    @Test
    fun notesListScreen_loaded() {
        paparazzi.snapshot {
            AppTheme {
                NotesListContent(
                    state = NotesListState(
                        notes = previewNotes(),
                        isLoading = false,
                    ),
                    onLoadNotes = {},
                    onDeleteNote = {},
                    onRetry = {},
                    onNoteClick = {},
                )
            }
        }
    }

    @Test
    fun notesListScreen_empty() {
        paparazzi.snapshot {
            AppTheme {
                NotesListContent(
                    state = NotesListState(notes = emptyList(), isLoading = false),
                    onLoadNotes = {},
                    onDeleteNote = {},
                    onRetry = {},
                    onNoteClick = {},
                )
            }
        }
    }
}
```

### swift-snapshot-testing (iOS)

```swift
// Package.swift or SPM dependency
.package(url: "https://github.com/pointfreeco/swift-snapshot-testing", from: "1.15.0")

// SnapshotTests/NotesListSnapshotTests.swift
import SnapshotTesting
import SwiftUI
import XCTest

final class NotesListSnapshotTests: XCTestCase {
    func testNotesListScreen_loaded() {
        let view = NotesListContent(
            notes: .preview,
            isLoading: false,
            onNoteClick: { _ in }
        )
        assertSnapshot(of: view, as: .image(layout: .device(config: .iPhone13)))
    }

    func testNotesListScreen_dark() {
        let view = NotesListContent(notes: .preview, isLoading: false, onNoteClick: { _ in })
            .environment(\.colorScheme, .dark)
        assertSnapshot(of: view, as: .image(layout: .device(config: .iPhone13)))
    }
}
```

### Playwright (Web)

Install:

```bash
npm install -D @playwright/test
npx playwright install chromium
```

Then add a screenshot project to `playwright.config.ts`:

```typescript
export default defineConfig({
  projects: [
    {
      name: 'screenshots',
      testDir: './e2e/visual',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
```
