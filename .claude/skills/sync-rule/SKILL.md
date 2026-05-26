---
name: sync-rule
description: "Mirror edits in .claude/rules/ between this repo and the canonical tech-agency repo. Use after editing a rule file so the two repos don't drift. Triggers: 'sync rule', 'mirror rule', 'sync to tech-agency', 'sync from tech-agency', 'mirror to template', 'apply rule change to both repos'."
---

# Sync Rule — Mirror Rule Edits Between Consumer and Tech-Agency

The tech-agency repo is the canonical owner of all `.claude/rules/*.md` files. Consumer projects (e.g., Steady) copy these into their own `.claude/rules/` and may edit them in-place when something project-specific comes up. Without explicit syncing, the two diverge.

This skill detects which side of the mirror you're on, finds the corresponding file in the other repo, shows the diff, and applies the same change there — with a genericization step when going consumer → tech-agency so the canonical version stays clean.

## When to Use

- After editing any `.claude/rules/*.md` file in a consumer repo — sync to tech-agency.
- After editing any `.claude/rules/*.md` file in tech-agency — propagate to consumers (run from inside the consumer).
- Before committing in either repo, if you suspect drift.

## Path Mapping

The path layouts differ — consumers are flat, tech-agency is grouped by domain:

| Consumer (e.g. Steady) | Tech-agency |
|---|---|
| `.claude/rules/<name>.md` | `.claude/rules/<domain>/<name>.md` |

The domain is determined by file basename (e.g. `compose-coding-standards.md` lives under `mobile/android/`, `kmp-coding-standards.md` under `mobile/shared/`, `shared-standards.md` under `shared/`). The skill discovers the mapping dynamically via `find` — no hardcoded table.

## Step 1: Determine source, destination, and direction

```bash
SOURCE_REPO="$(pwd)"

# Default tech-agency location — override if it lives elsewhere on this machine.
TECH_AGENCY="${TECH_AGENCY_PATH:-/Users/freelance.zeyad.gasser/AndroidStudioProjects/tech-agency}"

if [ ! -d "$TECH_AGENCY/.claude/rules" ]; then
  echo "tech-agency not found at $TECH_AGENCY. Set TECH_AGENCY_PATH or update the skill."
  exit 1
fi

if [ "$SOURCE_REPO" = "$TECH_AGENCY" ]; then
  DIRECTION="template-to-consumer"
  echo "You are inside tech-agency. This skill works best invoked from the consumer repo."
  echo "If you want to propagate from tech-agency, cd into the consumer and re-invoke."
  exit 1
else
  DIRECTION="consumer-to-template"
fi
```

## Step 2: Identify rule files that changed

```bash
# Files modified in working tree, staged, or in the last commit.
CHANGED_RULES=$( {
  git diff --name-only -- '.claude/rules/**.md'
  git diff --cached --name-only -- '.claude/rules/**.md'
  git diff --name-only HEAD~1..HEAD -- '.claude/rules/**.md' 2>/dev/null
} | sort -u | grep -v '^$' )
```

If the user passed specific files as arguments, use those instead.

## Step 3: For each changed file, find its mirror in tech-agency

```bash
for f in $CHANGED_RULES; do
  BASENAME=$(basename "$f")
  MATCHES=$(find "$TECH_AGENCY/.claude/rules" -name "$BASENAME" -not -path '*/worktrees/*' 2>/dev/null)
  COUNT=$(echo "$MATCHES" | grep -c '.')

  case "$COUNT" in
    0) echo "⚠️  $BASENAME: no mirror in tech-agency. Skip or place manually." ;;
    1) echo "✅ $f ↔ ${MATCHES#$TECH_AGENCY/}" ;;
    *) echo "⚠️  $BASENAME: multiple matches in tech-agency — pick one:"
       echo "$MATCHES" | sed 's|^|    |' ;;
  esac
done
```

For ambiguous matches (count > 1), ask the user to choose before proceeding.

## Step 4: Genericize before mirroring (consumer → tech-agency only)

When syncing FROM a consumer repo TO tech-agency, scan the changed lines for project-specific identifiers. Tech-agency is meant to be a clean template — consumer-flavored identifiers there mislead other consumers.

**Patterns to flag** (non-exhaustive — apply judgment):

| Pattern | Action in tech-agency |
|---|---|
| Project name in code identifiers (e.g. `AgendaEntry`, `RoutinePM`, `SteadyButton`) | Replace with the doc's running-example domain (Notes/NotesList where used elsewhere) or `<Placeholder>` |
| Hardcoded module paths (e.g. `core/sharedUI/components/...`, `features/agenda/...`) | Replace with `<design-system-module>/...`, `features/<feature>/...` |
| Commit hashes (e.g. `commit 6033a076`) | Strip — meaningless outside the source repo |
| Date stamps tied to a specific rollout (e.g. `rule rollout (2026-05-14)`) | Strip or genericize to "during initial rollout" |
| Task/ticket IDs (e.g. `TD-012`, `US-042`) | Strip the entire subsection or genericize |
| Whole "Pilot examples" / "Migration discipline" / "Known out-of-scope" subsections describing project-specific rollouts | Strip entirely from tech-agency — keep them in the consumer only |
| Tool class names tied to the consumer (e.g. `AppKonsistTest.kt`) | Strip the file reference, keep the tool name |

Show the user a diff with each flagged line annotated, and **wait for approval** on the genericization before applying. Never genericize silently — the consumer may have intentionally used a concrete reference and want it kept.

## Step 5: Apply the edit to the mirror file

Use the `Edit` tool with the source diff's old_string / new_string pairs (genericized per Step 4 if applicable). The Edit tool will fail if surrounding context doesn't match — that's a feature, it tells you the mirror has drifted.

**On drift detection:**

1. Show the user both versions of the affected section.
2. Suggest a resolution: rebase one repo's edits onto the other, or document the divergence as intentional.
3. Update the relevant memory (`project_<consumer>_rules_synced_from_tech_agency`) if a section is intentionally divergent.

Never overwrite blindly when context doesn't match.

## Step 6: Report

```
Synced 2 rule(s) from <consumer-repo> to tech-agency:
  ✅ compose-coding-standards.md → mobile/android/compose-coding-standards.md
  ✅ kmp-coding-standards.md → mobile/shared/kmp-coding-standards.md

Genericization applied to 1 file:
  - mobile/android/compose-coding-standards.md: 3 identifiers replaced
    (AgendaFormScreen → NotesListScreen, etc.)

Next steps:
  1. Review tech-agency diff: cd $TECH_AGENCY && git diff .claude/rules/
  2. Commit + push in tech-agency when satisfied.
  3. The consumer repo's edit stays as-is — no changes there.
```

## Reverse Direction: Tech-Agency → Consumer

When tech-agency is the source of a canonical update being propagated to a consumer:

1. From inside tech-agency, identify the changed files (`git diff --name-only HEAD~1..HEAD -- '.claude/rules/'`).
2. cd into the consumer repo.
3. For each changed file, locate the flat-path destination (`.claude/rules/$(basename file).md`).
4. Apply the diff. **No genericization needed in this direction** — the tech-agency content is already generic.
5. The consumer may want to add back project-specific subsections it had stripped before (e.g., its own "Pilot examples"). Surface this to the user, don't decide unilaterally.

## What NOT to Sync

Some content legitimately belongs in only one repo:

- **Consumer-specific subsections** in coding standards (e.g., "Migration discipline" tied to a specific project's rollout) — keep in consumer only.
- **Tech-agency-only rules** about how the framework itself works (versioning, plugin manifest, marketplace) — never propagate to consumers.
- **CLAUDE.md, board-context.md** — project-specific by definition, not under `.claude/rules/` anyway.

## Related Memories

- Consumer-specific sync memory (e.g., `project_steady_rules_synced_from_tech_agency`) — documents the dual-repo convention and any known divergences.
- `feedback_promote_repeated_workflows_to_tech_agency` — the meta-rule that spawned this skill.
