---
name: capture-screenshots
description: "Capture before/after screenshots for UI changes using Paparazzi (Android), swift-snapshot-testing (iOS), and Playwright (Web). Produces a visual comparison table for PR review. Use when the user says 'capture screenshots', 'visual diff', 'before after screenshots', 'screenshot comparison', or when a PR has UI changes that need visual evidence."
---

# Capture Screenshots — Automated Visual Evidence for UI Changes

This skill generates before/after screenshots to visually demonstrate UI changes. It detects which platforms are affected, runs the appropriate screenshot tooling on both the base branch and the feature branch, and produces a markdown comparison table that can be included in the PR.

## When to Use

- Before running `/create-pr` when the branch contains UI changes
- When `/create-pr` detects UI changes and prompts for visual evidence
- When a reviewer requests visual proof of a UI change
- Manually, when the user says "capture screenshots" or "visual diff"

## Step 1: Detect Affected Platforms

Analyze the changed files to determine which platforms have UI changes:

```bash
# Get all changed files on this branch vs main
CHANGED_FILES=$(git diff --name-only main..HEAD)

# Detect platforms
HAS_ANDROID=$(echo "$CHANGED_FILES" | grep -E '\.(kt)$' | grep -iE '(Screen|Content|Component|View|Composable|Preview|Theme|Color|Type|Spacing|designsystem)' | head -1)
HAS_IOS=$(echo "$CHANGED_FILES" | grep -E '\.(swift)$' | grep -iE '(Screen|View|Component|Preview|Theme|Color|Typography|Spacing|DesignSystem)' | head -1)
HAS_WEB=$(echo "$CHANGED_FILES" | grep -E '\.(tsx|jsx)$' | grep -iE '(page|component|screen|layout|ui/)' | head -1)
```

Report which platforms were detected:

```
Platforms with UI changes detected:
  - Android (Compose): YES/NO
  - iOS (SwiftUI): YES/NO
  - Web (React): YES/NO
```

If no UI changes are detected, inform the user and exit:

```
No UI-related file changes detected on this branch. Visual evidence is not required for this PR.
If you believe UI changes are present but were not detected, you can provide screenshots manually.
```

## Step 2: Capture Screenshots — Per Platform

For each detected platform, capture screenshots on the **base branch** (before) and the **feature branch** (after).

### General Flow (All Platforms)

```
1. Record the current branch name
2. Stash any uncommitted changes
3. Checkout the base branch (main)
4. Run screenshot capture for the base state → save to .screenshots/before/
5. Checkout back to the feature branch
6. Pop stashed changes (if any)
7. Run screenshot capture for the feature state → save to .screenshots/after/
8. Generate diff comparison
```

```bash
FEATURE_BRANCH=$(git branch --show-current)
mkdir -p .screenshots/before .screenshots/after

# Stash uncommitted changes if any
git stash --include-untracked 2>/dev/null

# Capture "before" on base branch
git checkout main
# ... run platform-specific capture (see below) ...

# Return to feature branch
git checkout "$FEATURE_BRANCH"
git stash pop 2>/dev/null

# Capture "after" on feature branch
# ... run platform-specific capture (see below) ...
```

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
# Record golden images (captures screenshots of all Paparazzi tests)
# Run only for the affected module(s) to save time
AFFECTED_MODULES=$(echo "$CHANGED_FILES" | grep '\.kt$' | sed 's|/src/.*||' | sort -u)

for module in $AFFECTED_MODULES; do
  # Before (on main)
  ./gradlew "${module}:recordPaparazziDebug" 2>&1
  cp -r "${module}/src/test/snapshots" ".screenshots/before/${module##*/}/" 2>/dev/null
done

# After switching back to feature branch:
for module in $AFFECTED_MODULES; do
  ./gradlew "${module}:recordPaparazziDebug" 2>&1
  cp -r "${module}/src/test/snapshots" ".screenshots/after/${module##*/}/" 2>/dev/null
done
```

**If specific screens are known**, run only the relevant Paparazzi test classes:

```bash
./gradlew "${module}:testDebugUnitTest" --tests "*${ScreenName}ScreenshotTest" 2>&1
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
# Record snapshots by running snapshot tests with record mode
# Before (on main):
cd iosApp
xcodebuild test \
  -scheme "AppTests" \
  -destination "platform=iOS Simulator,name=iPhone 16,OS=latest" \
  -only-testing:"AppTests/SnapshotTests" \
  2>&1 | xcpretty
cp -r "Tests/__Snapshots__" "../.screenshots/before/ios/" 2>/dev/null
cd ..

# After (on feature branch):
cd iosApp
# Set RECORD_MODE environment variable to regenerate snapshots
SNAPSHOT_TESTING_RECORD=1 xcodebuild test \
  -scheme "AppTests" \
  -destination "platform=iOS Simulator,name=iPhone 16,OS=latest" \
  -only-testing:"AppTests/SnapshotTests" \
  2>&1 | xcpretty
cp -r "Tests/__Snapshots__" "../.screenshots/after/ios/" 2>/dev/null
cd ..
```

**Alternative — if using SwiftUI Previews with a snapshot helper:**

```bash
# Some projects have a dedicated snapshot target
xcodebuild test \
  -scheme "SnapshotTests" \
  -destination "platform=iOS Simulator,name=iPhone 16,OS=latest" \
  2>&1 | xcpretty
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

```bash
# Determine affected pages/routes from changed files
AFFECTED_PAGES=$(echo "$CHANGED_FILES" | grep -E '\.(tsx|jsx)$' | grep -E 'app/.*page\.' | sed 's|src/app||;s|/page\.tsx$||;s|/page\.jsx$||' | sort -u)

# Before (on main):
npm ci --silent
npm run build --silent 2>/dev/null || npm run dev &
DEV_PID=$!
sleep 5  # wait for server

for page_route in $AFFECTED_PAGES; do
  SAFE_NAME=$(echo "$page_route" | tr '/' '_' | sed 's/^_//')
  npx playwright screenshot "http://localhost:3000${page_route}" ".screenshots/before/web/${SAFE_NAME}.png" 2>/dev/null
  # Dark mode
  npx playwright screenshot --color-scheme=dark "http://localhost:3000${page_route}" ".screenshots/before/web/${SAFE_NAME}-dark.png" 2>/dev/null
  # Mobile viewport
  npx playwright screenshot --viewport-size="375,812" "http://localhost:3000${page_route}" ".screenshots/before/web/${SAFE_NAME}-mobile.png" 2>/dev/null
done

kill $DEV_PID 2>/dev/null

# After (on feature branch) — repeat the same process
npm ci --silent
npm run build --silent 2>/dev/null || npm run dev &
DEV_PID=$!
sleep 5

for page_route in $AFFECTED_PAGES; do
  SAFE_NAME=$(echo "$page_route" | tr '/' '_' | sed 's/^_//')
  npx playwright screenshot "http://localhost:3000${page_route}" ".screenshots/after/web/${SAFE_NAME}.png" 2>/dev/null
  npx playwright screenshot --color-scheme=dark "http://localhost:3000${page_route}" ".screenshots/after/web/${SAFE_NAME}-dark.png" 2>/dev/null
  npx playwright screenshot --viewport-size="375,812" "http://localhost:3000${page_route}" ".screenshots/after/web/${SAFE_NAME}-mobile.png" 2>/dev/null
done

kill $DEV_PID 2>/dev/null
```

**For component-level screenshots** (if Storybook is available):

```bash
# Check for Storybook
if grep -q "storybook" package.json; then
  npx storybook build --quiet -o .storybook-static
  npx http-server .storybook-static -p 6006 &
  STORYBOOK_PID=$!
  sleep 5
  # Screenshot specific stories
  npx playwright screenshot "http://localhost:6006/iframe.html?id=${component-story-id}" ".screenshots/after/web/${component}.png"
  kill $STORYBOOK_PID 2>/dev/null
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

After capturing (or failing to capture) screenshots for all platforms:

```
Visual evidence captured:

  Android (Paparazzi): {N} screenshots captured / MANUAL NEEDED / NOT APPLICABLE
  iOS (swift-snapshot-testing): {N} screenshots captured / MANUAL NEEDED / NOT APPLICABLE
  Web (Playwright): {N} screenshots captured / MANUAL NEEDED / NOT APPLICABLE

Screenshots saved to .screenshots/before/ and .screenshots/after/

Next steps:
  - Review the screenshots to confirm the changes look correct
  - Run `/create-pr` to include the visual evidence in the PR
```

## Integration with Other Skills

### Called by `/create-pr`

When `/create-pr` detects UI changes (Step 1 detection logic), it should prompt:

```
UI changes detected. Run `/capture-screenshots` to generate visual evidence?
```

If the user confirms, run this skill before building the PR body. The Visual Changes section from Step 3 is then included in the PR body.

### Checked by `/code-review`

During code review, `/code-review` checks:
1. Does the PR have UI changes? (same detection logic as Step 1)
2. If yes, is there a "Visual Changes" section in the PR body?
3. If missing, flag it as a required change

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

```bash
# Install
npm install -D @playwright/test
npx playwright install chromium

# playwright.config.ts — add a screenshot project
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
