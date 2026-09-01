# The Consumer Rules Mirror

**Rule:** in a consumer repo, `.claude/rules/` is **generated**, not authored. It is a flattened mirror of the tech-agency plugin's `rules/`. Never hand-edit a file in it. Project-specific rules live in `.claude/rules-local/`.

## Why the copy exists at all

Only the `.claude/rules/` directory in the repo's own working tree is auto-loaded as project instructions. Rules that ship inside an installed plugin are **not** injected into a consumer's session — which is why `/setup-repo` copies them in, and why deleting the copy would silently strip every coding standard from every agent in that repo.

So the copy is load-bearing. The failure mode is not "the copy is redundant"; it is "the copy is a fork nobody notices". A rule edited in the consumer never reaches tech-agency, a rule edited in tech-agency never reaches the consumer, and both sides keep believing they are following the same standard.

## The two directories

| Directory | Who writes it | What belongs there |
|---|---|---|
| `.claude/rules/` | `/sync-rule` only | The mirror. Every file is byte-identical to its counterpart in the plugin. |
| `.claude/rules-local/` | You | Rules that are true for **this project only** and would be wrong for other consumers. |

Both auto-load, so an agent sees the union. When the two conflict, the local rule wins — say so explicitly in the local file rather than relying on load order.

The mirror is flat even though the plugin groups rules by domain (`backend/`, `mobile/`, `web/`, `shared/`). Flattening is deliberate: a consumer loads every rule regardless of which stacks it uses, and a flat directory makes the "is this file in the manifest?" check trivial.

## The manifest

`.claude/rules/.synced-from` records where the mirror came from and a SHA-256 per file:

```
source: /Users/…/.claude/plugins/cache/tech-agency/tech-agency/1.1.0/rules
version: 1.1.0
ref: fd7d01b
synced: 2026-09-01T15:56:31Z
---
9f2c…  agent-preamble.md
41ab…  shared-standards.md
```

`ref` appears only when the mirror was pulled from a checkout rather than a released plugin — useful while tracking an unreleased branch, and a signal that the mirror should be re-pinned to a release later.

## Commands

All four run from the consumer repo root:

```bash
.claude/skills/sync-rule/mirror.sh status   # what the mirror is pinned to
.claude/skills/sync-rule/mirror.sh check    # verify integrity — exits 1 on drift
.claude/skills/sync-rule/mirror.sh diff     # what upstream has that the mirror doesn't
.claude/skills/sync-rule/mirror.sh pull     # regenerate the mirror + manifest
```

`check` runs in the pre-push hook. A hand-edited mirror file blocks the push.

## Changing a rule

Decide which of the three it is, then take that path:

1. **It belongs to every project.** Change it in tech-agency, open a PR there, release, then `mirror.sh pull` in the consumer. This is the normal path, and it is the one that keeps every other consumer correct.
2. **It is true only here.** Put it in `.claude/rules-local/` and state which mirrored rule it overrides.
3. **You already edited the mirror by mistake.** `git diff .claude/rules/` shows the edit — move it to one of the two homes above, then `mirror.sh pull` to restore the file.

Editing the mirror and "syncing it later" is not a fourth option. That is exactly the drift this rule exists to prevent.

## Source resolution

`mirror.sh` finds the canonical rules in this order, first hit wins:

1. `$TECH_AGENCY_RULES` — an explicit path to a `rules/` directory.
2. `$CLAUDE_PLUGIN_ROOT/rules` — set automatically when running inside the plugin.
3. The newest `~/.claude/plugins/cache/*/tech-agency/*/rules` — the installed plugin. **This is the normal case and needs no configuration.**
4. `$TECH_AGENCY_PATH/.claude/rules` — a local tech-agency clone, for framework development.

A consumer therefore needs the plugin installed, not a clone of tech-agency.
