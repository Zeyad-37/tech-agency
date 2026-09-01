# Vendored Agent Skills — Provenance, Licensing & Runbook

This file tracks third-party Agent Skills vendored into `.claude/skills/`. They are
**copied** (not submoduled) so they ship with the `tech-agency` plugin and are
version-pinned to the upstream commit recorded below.

> **How agents actually use these:** the tech-agency worker agents (Kai, Link, Forge,
> Sentinel) are sub-agents spawned with `tools: Read, Glob, Grep, Bash, Write, Edit` —
> they have **no `Skill` tool** and cannot invoke a skill directly. They consume this
> tooling two ways: (1) running the `android` CLI via **Bash**, and (2) reading the
> guidance wired into the rule files (see the "Tooling: Android CLI & Agent Skills"
> sections in the rules listed under *Rule wiring* below), which point them at the
> relevant `SKILL.md` to `Read`. The main session / orchestrator (which has the `Skill`
> tool) can invoke them as normal skills.

## Licensing

Both upstream sets are **Apache License 2.0**. The full license text is kept once at
`./LICENSE-APACHE-2.0.txt`. Per the Apache 2.0 redistribution terms, attribution is
recorded here and the original `name`/`license`/`metadata.author` frontmatter on each
`SKILL.md` is preserved unchanged (only the `name:` field was rewritten to match the
new folder name — see below).

## Android skills — from `github.com/android/skills`

- **Upstream commit:** `a8f3525d5a1f7fe250fecd0fca43a87755433c8f`
- **Author:** Google LLC · **License:** Apache-2.0
- The local folder is `android-`-prefixed for namespacing; the `SKILL.md` `name:` field
  was updated to match the folder. Each folder's `references/` (and `assets/` where
  present) were copied verbatim.

| Local folder (`.claude/skills/`) | Upstream path | Primary owner(s) |
|---|---|---|
| `android-cli` | `devtools/android-cli` | Kai, Link, Sentinel |
| `android-compose-theming` | `jetpack-compose/theming/styles` | Kai |
| `android-compose-adaptive` | `jetpack-compose/adaptive` | Kai |
| `android-xml-to-compose` | `jetpack-compose/migration/migrate-xml-views-to-jetpack-compose` | Kai |
| `android-navigation-3` | `navigation/navigation-3` | Kai |
| `android-edge-to-edge` | `system/edge-to-edge` | Kai |
| `android-testing-setup` | `testing/testing-setup` | Kai |
| `android-r8-analyzer` | `performance/r8-analyzer` | Kai, Sentinel |
| `android-perfetto-trace-analysis` | `profilers/perfetto-trace-analysis` | Kai |
| `android-perfetto-sql` | `profilers/perfetto-sql` | Kai |

## Kotlin agent skills — from `github.com/Kotlin/kotlin-agent-skills`

- **Upstream commit:** `17852d57f9ff9929d268a02940ac05ed76d24784`
- **Author:** JetBrains · **License:** Apache-2.0
- Folder names match upstream (already namespaced `kotlin-…`); `SKILL.md` copied verbatim.

| Local folder (`.claude/skills/`) | Upstream path (`skills/…`) | Primary owner(s) |
|---|---|---|
| `kotlin-backend-jpa-entity-mapping` | `kotlin-backend-jpa-entity-mapping` | Forge |
| `kotlin-tooling-agp9-migration` | `kotlin-tooling-agp9-migration` | Link, Kai, Sentinel |
| `kotlin-tooling-java-to-kotlin` | `kotlin-tooling-java-to-kotlin` | Forge, Link |
| `kotlin-tooling-cocoapods-spm-migration` | `kotlin-tooling-cocoapods-spm-migration` | Link |

## Deliberately excluded (add on demand)

These upstream skills were not vendored because they are situational for this agency's
stack. To add one, follow the *Refresh / extend* runbook below.

- **Android:** `camera/camera1-to-camerax`, `device-ai/appfunctions`,
  `identity/verified-email`, `play/engage-sdk-integration`,
  `play/play-billing-library-version-upgrade`, `wear/jetpack-compose-m3`,
  `xr/display-glasses-with-jetpack-compose-glimmer`, and `build/agp/agp-9-upgrade`
  (the Kotlin `kotlin-tooling-agp9-migration` covers AGP 9, so Android's was skipped to
  avoid duplication).

## Rule wiring (where the "use when needed" lives)

The task→skill mappings that drive worker behaviour are in:
- `.claude/rules/mobile/android/compose-coding-standards.md` (Kai)
- `.claude/rules/mobile/shared/kmp-coding-standards.md` (Link / Compose-MP)
- `.claude/rules/backend/jvm/jvm-coding-standards.md` (Forge)
- `.claude/rules/backend/kotlin/ktor-server-coding-standards.md` (Link)

Agent-level pointers live in `.claude/agents/{kai,link,forge,sentinel}-*.md`.
See also `docs/guides/references/android-kotlin-skills-integration.md`.

## Refresh / extend runbook

No `npx`/Node is required (the `npx skills add` route needs Node). To refresh a pin or
add an excluded skill, clone the upstream and copy the folder:

```bash
TMP="$(mktemp -d)"
git clone --depth 1 https://github.com/android/skills.git "$TMP/android-skills"
# add one (example: edge-to-edge already vendored — shown for pattern):
cp -R "$TMP/android-skills/<category>/<skill>" .claude/skills/android-<skill>
# rewrite the name: frontmatter to match the new folder name:
perl -0pi -e 's/^name: .*$/name: android-<skill>/m if !$done++' .claude/skills/android-<skill>/SKILL.md
```

For Kotlin skills, clone `github.com/Kotlin/kotlin-agent-skills` and copy from its
`skills/` dir (names already namespaced — no rename needed).

After adding/refreshing: update the tables and the commit SHA(s) above, confirm no file
exceeds the 5 MB pre-commit limit, and bump `.claude/.claude-plugin/plugin.json`.

> Users who prefer the always-latest Kotlin set over this pin can instead run
> `claude plugin marketplace add Kotlin/kotlin-agent-skills` (see `/setup-repo`).
