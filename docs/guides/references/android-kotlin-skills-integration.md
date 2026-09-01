# Android & Kotlin Agent Skills — Integration Guide

This document explains how Google's **Android Agent Skills** + **`android` CLI**
(`github.com/android/skills`, `developer.android.com/tools/agents`) and JetBrains'
**Kotlin Agent Skills** (`github.com/Kotlin/kotlin-agent-skills`) are integrated into the
Tech Agency, and how the agents use them.

## The mechanism (read this first)

The tech-agency worker agents — **Kai** (Android), **Link** (KMP/Ktor), **Forge** (JVM),
**Sentinel** (DevOps) — are sub-agents spawned with `tools: Read, Glob, Grep, Bash,
Write, Edit`. **They have no `Skill` tool**, so they cannot invoke a skill the way the
main session can. They consume this tooling in exactly two ways:

1. **Bash** — running the `android` CLI directly (`android docs search`, `android run`,
   `android emulator`, `android layout`, `android screen capture`, `android sdk`).
2. **Rule files** — the coding-standards rules are auto-injected into every agent's
   context as project instructions. Each relevant rule file has a
   **"Tooling: Android CLI & Agent Skills"** section that maps a task to the right
   vendored `SKILL.md`, which the agent then `Read`s and follows.

The main session / orchestrator (which *does* have the `Skill` tool) can additionally
invoke the vendored skills as normal skills.

So the integration is **vendor + rule-wire**, not "install a plugin and hope agents call
it." The rule wiring is the part that actually changes worker behaviour.

## What's vendored

The upstream `SKILL.md` folders are copied into `.claude/skills/` (version-pinned, ships
with the `tech-agency` plugin). Full inventory, upstream commit SHAs, and licensing are
in [`.claude/skills/VENDORED-SKILLS.md`](../../.claude/skills/VENDORED-SKILLS.md).

- **Android (`android-*`)**: `android-cli`, `android-compose-theming`,
  `android-compose-adaptive`, `android-xml-to-compose`, `android-navigation-3`,
  `android-edge-to-edge`, `android-testing-setup`, `android-r8-analyzer`,
  `android-perfetto-trace-analysis`, `android-perfetto-sql`.
- **Kotlin (`kotlin-*`)**: `kotlin-backend-jpa-entity-mapping`,
  `kotlin-tooling-agp9-migration`, `kotlin-tooling-java-to-kotlin`,
  `kotlin-tooling-cocoapods-spm-migration`.

Both upstreams are Apache-2.0; the license text is at
`.claude/skills/LICENSE-APACHE-2.0.txt`.

## Where the wiring lives

| Agent | Rule file (Tooling section) | Agent def (Tooling section) |
|---|---|---|
| Kai | `.claude/rules/mobile/android/compose-coding-standards.md` | `.claude/agents/kai-android-engineer.md` |
| Link | `.claude/rules/mobile/shared/kmp-coding-standards.md`, `.claude/rules/backend/kotlin/ktor-server-coding-standards.md` | `.claude/agents/link-kmp-engineer.md` |
| Forge | `.claude/rules/backend/jvm/jvm-coding-standards.md` | `.claude/agents/forge-backend-jvm.md` |
| Sentinel | (CI usage) | `.claude/agents/sentinel-devops-sre.md` |

**Precedence:** the vendored skills *complement* the agency's coding standards. On any
conflict, the agency standards win (MVI/KMP architecture, T-013 typed-render rules,
`process: (Input) -> Unit` callback shape, JPA entity patterns, Exposed-vs-JPA
distinction, etc.).

## Toolchain bootstrap

The skill *files* ship with the plugin and need no install. The `android` **CLI binary**
does need installing before agents can run it. `/setup-repo` Step 7b documents this for
Android/KMP projects:

1. Download the `android` CLI from `developer.android.com/tools/agents`, then
   `android update`.
2. To suppress per-call permission prompts, add `Bash(android *)` to
   `.claude/settings.json` → `permissions.allow` (use `/update-config`).
3. For the always-latest Kotlin set instead of the vendored pin:
   `claude plugin marketplace add Kotlin/kotlin-agent-skills` (no Node required; the
   `npx skills add` route does require Node).

If an agent finds `command -v android` empty, it treats the missing CLI as a blocker /
CI prerequisite rather than guessing API details from memory.

## Refreshing / extending the pin

See the runbook at the bottom of
[`.claude/skills/VENDORED-SKILLS.md`](../../.claude/skills/VENDORED-SKILLS.md). After any
change, bump `.claude/.claude-plugin/plugin.json` and have consumers run
`claude plugin update tech-agency`.
