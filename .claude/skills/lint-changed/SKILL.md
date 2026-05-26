---
name: lint-changed
description: "Run detekt per-changed-file via SARIF diff when full-repo detekt is broken (no baseline, hundreds of pre-existing violations). Reports only NEW violations introduced by the current branch — not the noise from pre-existing violations on main. Triggers: 'lint changed', 'detekt changed files', 'lint diff', 'check my changes for lint issues'."
---

# Lint Changed Files — Per-File Detekt via SARIF Diff

This skill is a **workaround** for projects where `./gradlew detekt` doesn't return clean on the full repo (e.g., hundreds of pre-existing violations, no baseline file committed). Instead of running detekt across everything and drowning in noise, it lints only the files changed on the current branch and diffs the SARIF output against the base branch to surface only the NEW violations the branch introduced.

> **Retirement note.** The proper fix is to generate and commit a detekt baseline (`./gradlew detektBaseline`) so the full-repo run works. Once that exists, this skill is no longer needed — delete it.

## When to Use

- Before committing a Kotlin change in a project where full-repo `detekt` is broken.
- As a pre-push gate (can be invoked from `/create-pr`'s verification step when applicable).
- During code review of a PR that touches Kotlin files.

## Prerequisites

- The project has detekt configured (any version).
- `jq` is installed (for SARIF diffing).
- The current branch is rooted on `main` (or another base — adjust `BASE` below).

## Step 1: Identify changed Kotlin files

```bash
BASE="${BASE:-main}"
CHANGED=$(git diff --name-only "${BASE}..HEAD" -- '*.kt' '*.kts' | grep -v '/build/' | grep -v 'generated/')

if [ -z "$CHANGED" ]; then
  echo "No Kotlin files changed vs ${BASE}. Skipping lint."
  exit 0
fi

COUNT=$(echo "$CHANGED" | wc -l | tr -d ' ')
echo "Linting ${COUNT} changed file(s) vs ${BASE}…"
```

## Step 2: Run detekt with SARIF output on the changed files (current state)

The exact detekt invocation depends on project setup. Two common patterns:

**Pattern A — Gradle task with file-input property:**

```bash
mkdir -p .lint-tmp
./gradlew detekt \
  -PdetektInput="$(echo "$CHANGED" | tr '\n' ',' | sed 's/,$//')" \
  -PdetektReport=sarif \
  -PdetektOutput=".lint-tmp/after.sarif" || true   # detekt returns non-zero on violations; capture anyway
```

**Pattern B — Detekt CLI directly (no gradle):**

```bash
mkdir -p .lint-tmp
detekt-cli \
  -i "$(echo "$CHANGED" | tr '\n' ',' | sed 's/,$//')" \
  -r sarif:.lint-tmp/after.sarif \
  -c detekt.yml \
  || true
```

If the project uses a non-standard setup, ask the user for the right invocation and document it in the project's `CLAUDE.md` or a project-local memory.

## Step 3: Generate baseline SARIF from the base branch

We only care about violations the branch INTRODUCED — pre-existing violations on `main` should not be reported.

```bash
git stash push -u -m "lint-changed-stash" 2>/dev/null

CURRENT_BRANCH=$(git branch --show-current)
git checkout "$BASE" 2>/dev/null

# Run detekt against the same files on the base branch (skip files that don't exist there yet).
EXISTING_ON_BASE=""
for f in $CHANGED; do
  [ -f "$f" ] && EXISTING_ON_BASE="${EXISTING_ON_BASE}${f}\n"
done
EXISTING_ON_BASE=$(printf "$EXISTING_ON_BASE" | grep -v '^$')

if [ -n "$EXISTING_ON_BASE" ]; then
  ./gradlew detekt \
    -PdetektInput="$(echo "$EXISTING_ON_BASE" | tr '\n' ',' | sed 's/,$//')" \
    -PdetektReport=sarif \
    -PdetektOutput=".lint-tmp/before.sarif" || true
else
  # All changed files are new on this branch — no baseline.
  echo '{"runs":[{"results":[]}]}' > .lint-tmp/before.sarif
fi

# Restore branch state
git checkout "$CURRENT_BRANCH" 2>/dev/null
git stash pop 2>/dev/null
```

## Step 4: Diff the SARIF files

Extract `(file, line, ruleId, message)` tuples from each SARIF; report tuples present in `after` but not in `before`.

```bash
extract_violations() {
  jq -r '
    .runs[].results[]? |
    "\(.locations[0].physicalLocation.artifactLocation.uri):\(.locations[0].physicalLocation.region.startLine):\(.ruleId):\(.message.text)"
  ' "$1" 2>/dev/null | sort -u
}

extract_violations .lint-tmp/after.sarif  > .lint-tmp/after.tuples
extract_violations .lint-tmp/before.sarif > .lint-tmp/before.tuples

NEW_VIOLATIONS=$(comm -23 .lint-tmp/after.tuples .lint-tmp/before.tuples)

if [ -z "$NEW_VIOLATIONS" ]; then
  echo "✅ No new detekt violations introduced by this branch."
else
  COUNT=$(echo "$NEW_VIOLATIONS" | wc -l | tr -d ' ')
  echo "❌ ${COUNT} new detekt violation(s) introduced by this branch:"
  echo ""
  echo "$NEW_VIOLATIONS" | sed 's/^/  /'
  echo ""
  echo "Fix these before pushing. Pre-existing violations on ${BASE} are not reported (this skill only surfaces new ones)."
fi
```

## Step 5: Cleanup

```bash
rm -rf .lint-tmp
```

## Caveats

- **File-scoped detekt may differ from full-repo detekt.** Rules that operate on cross-file context (e.g., unused-public-API checks) may not fire when invoked on individual files. Treat this skill as best-effort; a baseline-driven full-repo run is more correct.
- **Renamed files** look like new files to this skill — they may show violations that existed on `main` under the old name. Manual judgment.
- **If the detekt gradle task name or input flag differs** in your project, ask the user for the right invocation. The two patterns above are common but not universal.
- **The stash + checkout dance is risky if anything else is uncommitted.** Step 3 uses `git stash push -u` to include untracked files, but verify by hand if the branch state is unusual.

## Recommended Followup

The right long-term move is to retire this skill by generating a baseline:

```bash
./gradlew detektBaseline
git add config/detekt/baseline.xml   # path varies — wherever your detekt config writes it
git commit -m "[tech] Generate detekt baseline to snapshot pre-existing violations"
```

After that, `./gradlew detekt` returns clean on `main`, new violations naturally fail CI, and per-file diffing is no longer needed. Delete this skill once the baseline exists.

## Related Memories

- Consumer-specific memory documenting the broken detekt config (e.g., `project_detekt_no_baseline_failing` in Steady).
- `feedback_promote_repeated_workflows_to_tech_agency` — the meta-rule that spawned this skill.
