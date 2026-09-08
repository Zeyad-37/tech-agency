---
name: lint-changed
description: "Run detekt per-changed-file via SARIF diff when full-repo detekt is broken (no baseline, hundreds of pre-existing violations). Reports only NEW violations introduced by the current branch — not the noise from pre-existing violations on the base. Accepts --base <branch>; reads the baseline from a detached worktree, so it is safe to run with uncommitted work and alongside concurrent sessions. Triggers: 'lint changed', 'detekt changed files', 'lint diff', 'check my changes for lint issues'."
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
- The current branch is rooted on a base branch resolved in Step 0 — never a hardcoded `main`.

## Step 0: Resolve the Base Branch

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
echo "Lint base: origin/$BASE"
```

A branch cut from an epic integration branch must diff against that branch — otherwise every violation the epic already carries is reported as "introduced by this branch", which is exactly the noise this skill exists to remove.

## Step 1: Identify changed Kotlin files

```bash
# Three dots: compare against the merge base, not the moving tip of the base.
CHANGED=$(git diff --name-only "origin/${BASE}...HEAD" -- '*.kt' '*.kts' | grep -v '/build/' | grep -v 'generated/')

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

We only care about violations the branch INTRODUCED — pre-existing violations on the base should not be reported.

The base state is read from a **throwaway detached worktree**, not by stashing and checking out. Two reasons, both fatal to the old approach:

1. **`git stash pop` on a clean tree pops someone else's stash.** `git stash push -u` creates no entry when there is nothing to stash, so the paired `git stash pop` then pops whatever was already on the stack — and the stash stack is shared across every worktree and concurrent session.
2. **`git checkout "$BASE"` cannot work under worktree-first.** The base branch is checked out in the main repo, so git refuses to check it out again here.

```bash
REPO_ROOT="$(pwd)"

BASE_WT="$(mktemp -d "${TMPDIR:-/tmp}/lint-base-XXXXXX")"
rm -rf "$BASE_WT"                       # worktree add requires the path to be absent
git worktree add --detach "$BASE_WT" "origin/$BASE"
trap 'git worktree remove --force "$BASE_WT" || git worktree prune' EXIT

# Run detekt against the same files as they exist on the BASE (skip files that
# are new on this branch — they have no baseline by definition).
EXISTING_ON_BASE=""
for f in $CHANGED; do
  [ -f "$BASE_WT/$f" ] && EXISTING_ON_BASE="${EXISTING_ON_BASE}${f}"$'\n'
done
EXISTING_ON_BASE=$(printf '%s' "$EXISTING_ON_BASE" | grep -v '^$' || true)

if [ -n "$EXISTING_ON_BASE" ]; then
  ( cd "$BASE_WT" && ./gradlew detekt \
      -PdetektInput="$(echo "$EXISTING_ON_BASE" | tr '\n' ',' | sed 's/,$//')" \
      -PdetektReport=sarif \
      -PdetektOutput="$REPO_ROOT/.lint-tmp/before.sarif" ) || true
else
  # All changed files are new on this branch — no baseline.
  echo '{"runs":[{"results":[]}]}' > .lint-tmp/before.sarif
fi

# A detekt run that produced no SARIF at all is a FAILURE, not an empty baseline.
# Treating it as empty would report every pre-existing violation as new.
if [ ! -s .lint-tmp/before.sarif ]; then
  echo "❌ Baseline detekt run produced no SARIF — cannot distinguish new violations from pre-existing ones."
  echo "   Fix the detekt invocation (see Caveats) and re-run. Reporting nothing is safer than reporting everything."
  exit 1
fi
```

The current worktree is never touched: no stash, no checkout, no branch switch. Uncommitted and untracked work in it survives untouched, and `git branch --show-current` is unchanged throughout.

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
  echo "Fix these before pushing. Pre-existing violations on origin/${BASE} are not reported (this skill only surfaces new ones)."
fi
```

## Step 5: Cleanup

```bash
rm -rf .lint-tmp
# The base worktree is removed by the EXIT trap set in Step 3; this is belt-and-braces.
git worktree prune
```

## Caveats

- **File-scoped detekt may differ from full-repo detekt.** Rules that operate on cross-file context (e.g., unused-public-API checks) may not fire when invoked on individual files. Treat this skill as best-effort; a baseline-driven full-repo run is more correct.
- **Renamed files** look like new files to this skill — they may show violations that existed on the base under the old name. Manual judgment.
- **If the detekt gradle task name or input flag differs** in your project, ask the user for the right invocation. The two patterns above are common but not universal. Note that a wrong invocation now **fails loudly** at the end of Step 3 rather than silently producing an empty baseline.
- **The base worktree is cold.** The detached worktree in Step 3 has never been built, so its first detekt run pays a full configuration cost. That is expected; it is not a hang.
- **No stash, no checkout.** Step 3 reads the base from a detached worktree, so it is safe to run with uncommitted or untracked work in the current tree, and safe to run concurrently with other sessions.

## Recommended Followup

The right long-term move is to retire this skill by generating a baseline:

```bash
./gradlew detektBaseline
git add config/detekt/baseline.xml   # path varies — wherever your detekt config writes it
git commit -m "[tech] Generate detekt baseline to snapshot pre-existing violations"
```

After that, `./gradlew detekt` returns clean on `main`, new violations naturally fail CI, and per-file diffing is no longer needed. Delete this skill once the baseline exists.

## Related Memories

- Consumer-specific memory documenting the broken detekt config (e.g., a `project_detekt_no_baseline_failing` key in the consumer repo that needs this workaround).
- `feedback_promote_repeated_workflows_to_tech_agency` — the meta-rule that spawned this skill.
