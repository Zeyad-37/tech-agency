---
name: sync-rule
description: "Manage a consumer repo's .claude/rules/ mirror of the tech-agency plugin: check it for drift, refresh it, or promote a local rule edit upstream. Use after editing any rule, when a push is blocked by the mirror check, or when the plugin has been updated. Triggers: 'sync rule', 'mirror rule', 'rules drift', 'refresh rules', 'sync to tech-agency', 'sync from tech-agency', 'apply rule change to both repos'."
---

# Sync Rule — Keep the Consumer Rules Mirror Honest

Tech-agency owns every `.claude/rules/*.md` file. A consumer repo keeps a **flattened, generated mirror** of them, because plugin-supplied rules do not auto-load as project instructions — only the ones in the repo's own `.claude/rules/` do.

The contract is in `@.claude/rules/shared/rules-mirror.md`. Read it before doing anything here. The short version: the mirror is generated, `.claude/rules-local/` is authored, and the two must never be confused.

Most of this skill's work is done by `mirror.sh`, which sits beside this file. Reach for the manual flow in Part B only when a change has to travel *upstream*.

## Part A — Routine: check, refresh, resolve drift

Run from the consumer repo root:

```bash
.claude/skills/sync-rule/mirror.sh status
```

Then pick the branch that matches what `status` and `check` report.

### A1. The mirror is not initialised

The repo has rules but no `.synced-from`. This is the state every pre-mirror consumer starts in. Before the first `pull`, find out what would be lost:

```bash
.claude/skills/sync-rule/mirror.sh diff
```

Every file reported `outdated` differs from upstream. **Do not pull yet** — first triage each one, because a pull overwrites local edits:

```bash
SRC=$(.claude/skills/sync-rule/mirror.sh status | awk '/^source:/{print $2}')
for f in .claude/rules/*.md; do
  b=$(basename "$f")
  up=$(find "$SRC" -name "$b" | head -1)
  [ -n "$up" ] && ! diff -q "$up" "$f" >/dev/null && { echo "=== $b ==="; diff "$up" "$f"; }
done
```

For each difference, decide with the user which of three it is:

| The local edit is… | Where it goes |
|---|---|
| A genuine improvement for all projects | Promote upstream via Part B, release, then pull |
| True only for this project | Move to `.claude/rules-local/`, naming the rule it overrides |
| Stale — upstream has since moved past it | Discard; the pull handles it |

Only once every difference is classified: `mirror.sh pull`.

### A2. `check` reports drift (a push was blocked)

Someone edited a mirrored file. Show them what changed and route it the same way:

```bash
git diff .claude/rules/
```

Then either move the edit into `.claude/rules-local/`, or promote it upstream (Part B). Finish with `mirror.sh pull` to restore the mirror. Never resolve a blocked push by editing `.synced-from` — the manifest is generated, and rewriting it to match a hand-edited file is how the drift becomes permanent.

### A3. `diff` reports upstream is ahead

The plugin was updated. Read what changed, then pull:

```bash
.claude/skills/sync-rule/mirror.sh diff
.claude/skills/sync-rule/mirror.sh pull
git diff .claude/rules/   # review before committing
```

Check whether anything in `.claude/rules-local/` is now redundant — a local override often exists only because upstream lacked something it has since gained.

## Part B — Promoting a rule change upstream

Use this when a consumer discovered something every project should follow. This is the only flow that writes to tech-agency.

### B1. Locate tech-agency

```bash
TECH_AGENCY="${TECH_AGENCY_PATH:-}"
if [ -z "$TECH_AGENCY" ]; then
  for c in ~/StudioProjects/tech-agency ~/AndroidStudioProjects/tech-agency ~/src/tech-agency ../tech-agency; do
    [ -d "$c/.claude/rules" ] && TECH_AGENCY="$c" && break
  done
fi
[ -n "$TECH_AGENCY" ] || { echo "Set TECH_AGENCY_PATH to your tech-agency checkout."; exit 1; }
echo "tech-agency: $TECH_AGENCY"
```

Promoting a change needs a **checkout** — the plugin cache is read-only and gets overwritten on update. If there is no checkout, clone one; do not edit the cache.

### B2. Map the file to its domain path

Consumer paths are flat, tech-agency groups by domain:

| Consumer | Tech-agency |
|---|---|
| `.claude/rules/<name>.md` | `.claude/rules/<domain>/<name>.md` |

```bash
BASENAME=<name>.md
find "$TECH_AGENCY/.claude/rules" -name "$BASENAME" -not -path '*/worktrees/*'
```

No match means the rule is new upstream — place it under the domain that owns it (`shared/`, `mobile/android/`, `backend/python/`, …) and add it to the rules table in `README.md`. Multiple matches: ask which one before writing.

### B3. Genericize before writing

Tech-agency is a clean template. A consumer-flavoured identifier there misleads every other consumer.

| Pattern | Action in tech-agency |
|---|---|
| Project-specific type names (`AgendaEntry`, `RoutinePM`, `SteadyButton`) | Use the doc's running example (Notes/NotesList) or `<Placeholder>` |
| Hardcoded module paths (`features/agenda/…`) | `features/<feature>/…`, `<design-system-module>/…` |
| Commit hashes | Strip — meaningless outside the source repo |
| Rollout date stamps (`rule rollout (2026-05-14)`) | Strip, or "during initial rollout" |
| Task/ticket IDs (`TD-012`, `US-042`) | Strip the subsection or genericize |
| "Pilot examples" / "Migration discipline" sections describing one project's rollout | Strip from tech-agency — keep them in the consumer's `rules-local/` |
| Consumer-specific tool class names (`AppKonsistTest.kt`) | Strip the file reference, keep the tool name |

Show the user each flagged line and **wait for approval**. Never genericize silently — a concrete reference may be intentional.

### B4. Apply, then close the loop

Use `Edit` with the genericized old/new pairs. If the surrounding context doesn't match, tech-agency has moved on: show both versions and agree a resolution rather than overwriting.

Then, in tech-agency: commit, PR, merge, release. Then back in the consumer: `mirror.sh pull` — which is what actually makes the consumer's copy match. A promoted rule is not done until the mirror has been re-pulled.

## What never syncs

- **`rules-local/`** — project-specific by definition.
- **Framework-only rules** (plugin manifest, marketplace, versioning) — these live in tech-agency and are not mirrored.
- **`CLAUDE.md`, `board-context.md`** — project-specific, and not under `.claude/rules/` anyway.

## Reporting

Close with what changed and what is still owed:

```
Mirror: 17 files, pinned to tech-agency v1.1.0 (was: uninitialised)

Promoted upstream (1):
  compose-coding-standards.md → mobile/android/ — 3 identifiers genericized

Moved to rules-local (1):
  steady-overrides.md — Paper-theme Konsist exemption (overrides compose-coding-standards)

Discarded as stale (2):
  git-hooks.md, agent-preamble.md — upstream had already moved past the local edit

Still owed:
  tech-agency PR #NN must merge and release before the mirror can re-pin to a version.
```
