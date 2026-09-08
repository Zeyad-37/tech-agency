---
name: sync-rule
description: "Mirror edits to the shared rules in .claude/rules/shared/ between a consumer project and the canonical tech-agency plugin. Use after editing a shared rule so the two don't drift. Triggers: 'sync rule', 'mirror rule', 'sync to tech-agency', 'sync from tech-agency', 'apply rule change to both repos'."
---

# Sync Rule — Mirror Shared-Rule Edits Between Consumer and Tech-Agency

Tech-agency is the canonical owner of the **shared rules** under `rules/shared/` (ten core rules, plus any the plugin has added since). `/setup-repo` copies them into a consumer's `.claude/rules/shared/`, where they auto-load every session and where a project may edit one in place when something project-specific comes up. Without explicit syncing, the two diverge.

This skill finds the corresponding file on the other side, shows the diff, and applies the same change — with a genericization step when going consumer → tech-agency so the canonical version stays clean.

## When to Use

- After editing any `.claude/rules/shared/*.md` file in a consumer repo — sync it up to tech-agency.
- After editing any `rules/shared/*.md` file in tech-agency — propagate it down (see "Reverse Direction" below).
- Before committing on either side, if you suspect drift.

## Scope: shared rules only

| Rule set | Synced? |
|---|---|
| The shared rules (`rules/shared/*.md`) | **Yes** — they exist on both sides |
| The 8 language coding standards (`rules/mobile/…`, `rules/backend/…`, `rules/web/…`) | **No** — they exist only in the plugin and are read on demand from `${CLAUDE_PLUGIN_ROOT}/rules/<path>.md`. There is no consumer copy to sync with |

If a consumer holds a local copy of a coding standard, that is drift, not a mirror. Tell the user to delete it and read the plugin's copy instead — a stale local copy silently shadows the canonical one.

## Path Mapping — identity, not flattening

The nested layout is canonical **everywhere**, consumers included:

| Consumer | Tech-agency |
|---|---|
| `.claude/rules/shared/<name>.md` | `<plugin root>/rules/shared/<name>.md` |

The path below `rules/` is byte-identical on both sides. Earlier versions of this skill documented a flat consumer layout (`.claude/rules/<name>.md`) as intentional; that dual layout is dead. Never write or expect a flat path — every rule cross-reference in the agency is `@.claude/rules/shared/<name>.md`, and a flat file satisfies none of them.

## Step 1: Resolve both sides

The consumer is the current working directory (or the path passed as an argument). The tech-agency side resolves from the installed plugin, an explicit override, or the repo itself — never from a hardcoded absolute path, which is valid on exactly one machine.

```bash
CONSUMER="${1:-$(pwd)}"          # optional first argument: the consumer repo path
CONSUMER="$(cd "$CONSUMER" && pwd)"

resolve_tech_agency() {
    # 1. tech-agency installed as a plugin — CLAUDE_PLUGIN_ROOT is its `.claude/`.
    if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -d "${CLAUDE_PLUGIN_ROOT}/rules/shared" ]; then
        printf '%s\n' "${CLAUDE_PLUGIN_ROOT%/}"; return 0
    fi
    # 2. Explicit override: a local tech-agency checkout.
    if [ -n "${TECH_AGENCY_PATH:-}" ] && [ -d "${TECH_AGENCY_PATH}/.claude/rules/shared" ]; then
        printf '%s\n' "${TECH_AGENCY_PATH%/}/.claude"; return 0
    fi
    # 3. We are standing in the tech-agency repo itself.
    if [ -f ".claude-plugin/plugin.json" ] && [ -d ".claude/rules/shared" ]; then
        printf '%s\n' "$(pwd)/.claude"; return 0
    fi
    return 1
}

TA_ROOT="$(resolve_tech_agency)" || {
    echo "ERROR: cannot locate the tech-agency rules."
    echo "Install the plugin, or point TECH_AGENCY_PATH at a local tech-agency checkout:"
    echo "  TECH_AGENCY_PATH=~/code/tech-agency  # then re-run"
    exit 1
}

if [ "$TA_ROOT" = "${CONSUMER}/.claude" ]; then
    DIRECTION="none"
    echo "The consumer and tech-agency resolve to the same directory — nothing to mirror."
    echo "Pass the consumer repo path as an argument, or cd into it and re-invoke."
    exit 1
fi
DIRECTION="consumer-to-template"
echo "consumer=$CONSUMER"
echo "tech-agency rules=$TA_ROOT/rules"
```

Note that when tech-agency is installed as a plugin, `$TA_ROOT` is the installed copy — edits there are overwritten on the next plugin update. For a change meant to become canonical, set `TECH_AGENCY_PATH` to a real tech-agency checkout so the edit can be committed and PR'd.

## Step 2: Identify shared-rule files that changed

```bash
cd "$CONSUMER"

CHANGED_RULES=$( {
  git diff --name-only -- '.claude/rules/shared/*.md'
  git diff --cached --name-only -- '.claude/rules/shared/*.md'
  git diff --name-only HEAD~1..HEAD -- '.claude/rules/shared/*.md' 2>/dev/null
} | sort -u | grep -v '^$' )

echo "$CHANGED_RULES"
```

If the user passed specific files as arguments, use those instead.

## Step 3: For each changed file, locate its mirror

The mapping is direct — same relative path under `rules/` — so no `find` search and no ambiguity.

```bash
# Iterate with `printf | while read`, not `for f in $CHANGED_RULES` — unquoted
# parameter expansion does not word-split in zsh, so the loop would run once
# with every filename concatenated into $f.
printf '%s\n' "$CHANGED_RULES" | grep -v '^$' | while read -r f; do
  REL="${f#.claude/rules/}"                 # e.g. shared/board-in-pr.md
  MIRROR="${TA_ROOT}/rules/${REL}"

  case "$REL" in
    shared/*)
      if [ -f "$MIRROR" ]; then
        echo "[OK]   $f  ->  rules/${REL}"
      else
        echo "[NEW]  $f  ->  rules/${REL} (does not exist in tech-agency — new shared rule?)"
      fi
      ;;
    *)
      echo "[SKIP] $f — not a shared rule. Coding standards live only in the plugin and are not synced."
      ;;
  esac
done
```

A `[NEW]` result is worth pausing on, but it needs **no** edit to `/setup-repo`. That skill enumerates `rules/shared/*.md` by glob rather than from a hardcoded list precisely so a rule added here is copied into the next project set up, with no second change. (Earlier versions of this skill told you to update a `SHARED_RULES` list in `/setup-repo`; that list no longer exists — do not go looking for it.)

What a `[NEW]` result *does* warrant: confirm with the user that the file really is a new canonical shared rule rather than a project-local one that belongs only in the consumer, and check whether it should join `/setup-repo`'s **core-set gate** — the named list of rules whose absence means the payload is incomplete. Rules outside that gate arrive through the glob and are healthy surplus, not a gap.

## Step 4: Genericize before mirroring (consumer → tech-agency only)

When syncing FROM a consumer repo TO tech-agency, scan the changed lines for project-specific identifiers. Tech-agency is meant to be a clean template — consumer-flavored identifiers there mislead other consumers.

**Patterns to flag** (non-exhaustive — apply judgment):

| Pattern | Action in tech-agency |
|---|---|
| Project name in code identifiers (e.g. `AgendaEntry`, `RoutinePM`, or any type carrying the app's own name as a prefix) | Replace with the doc's running-example domain (Notes/NotesList where used elsewhere) or `<Placeholder>` |
| The consumer app's or company's name anywhere in prose, paths, URLs, or examples | Replace with "the consumer", "a private production repo", or the running-example domain. Tech-agency is a **public** repo — a private consumer's name must not travel upstream in a sync |
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
Synced 2 shared rule(s) from <consumer-repo> to tech-agency:
  [OK] shared/board-in-pr.md      -> rules/shared/board-in-pr.md
  [OK] shared/worktree-first.md   -> rules/shared/worktree-first.md

Skipped (not synced — plugin-only, read on demand):
  - mobile/android/compose-coding-standards.md

Genericization applied to 1 file:
  - rules/shared/board-in-pr.md: 3 identifiers replaced
    (AgendaFormScreen -> NotesListScreen, etc.)

Next steps:
  1. Review the tech-agency diff: cd <tech-agency checkout> && git diff .claude/rules/
  2. Commit and PR in tech-agency when satisfied.
  3. The consumer repo's edit stays as-is — no changes there.
```

## Reverse Direction: Tech-Agency → Consumer

When tech-agency is the source of a canonical update being propagated to a consumer:

1. From the tech-agency checkout, identify the changed files: `git diff --name-only HEAD~1..HEAD -- '.claude/rules/shared/'`.
2. `cd` into the consumer repo.
3. For each changed file, the destination is the **same relative path**: `.claude/rules/${REL}` where `REL` is everything after `rules/` (e.g. `shared/board-in-pr.md`). No flattening, no basename lookup.
4. Apply the diff. **No genericization needed in this direction** — the tech-agency content is already generic.
5. The consumer may want to add back project-specific subsections it had stripped before (e.g., its own "Pilot examples"). Surface this to the user, don't decide unilaterally.
6. If the change added a new shared rule, nothing further is needed for `/setup-repo` to ship it — that skill globs `rules/shared/*.md`. Consider only whether the rule belongs in `/setup-repo`'s core-set gate (the named list whose absence signals an incomplete payload).

## What NOT to Sync

Some content legitimately belongs on only one side:

- **The 8 language coding standards** — they live only in the plugin and are read on demand. A consumer copy is drift; delete it rather than syncing it.
- **Consumer-specific subsections** in a shared rule (e.g., "Migration discipline" tied to one project's rollout) — keep in the consumer only.
- **Tech-agency-only rules** about how the framework itself works (versioning, plugin manifest, marketplace) — never propagate to consumers.
- **CLAUDE.md, board-context.md** — project-specific by definition, and not under `.claude/rules/` anyway.

## Related Memories

- Consumer-specific sync memory (e.g., `project_<consumer>_rules_synced_from_tech_agency`) — documents the dual-repo convention and any known divergences.
- `feedback_promote_repeated_workflows_to_tech_agency` — the meta-rule that spawned this skill.
