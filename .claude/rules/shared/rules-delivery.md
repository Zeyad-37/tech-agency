# Rules Delivery — Where Each Rule Lives and How to Reference It

Tech Agency ships two kinds of rule file, and they reach you by two different mechanisms. Getting
the mechanism wrong means either referencing a file that does not exist in the user's project, or
burning ~79k tokens of context on standards for languages the project does not use. This document
is the single authority on which is which.

**The nested directory layout below is canonical everywhere — inside this plugin and inside every
consumer project.** The old flat layout (`.claude/rules/<name>.md`, e.g.
`.claude/rules/compose-coding-standards.md`) is dead. Never emit a flat rule path, in a skill, an
agent file, a doc, or a message to the user.

---

## 1. Shared rules — copied into the consumer, auto-loaded every session

These eleven files are **policy**: they apply to every agent regardless of what language the task is
in. `/setup-repo` copies them from the plugin into the consumer project's `.claude/rules/shared/`,
where Claude Code auto-loads them as project instructions at the start of every session. You never
need to read them explicitly — they are already in your context.

| File | What it governs |
|---|---|
| `agent-preamble.md` | The start-of-task and end-of-task checklist every agent runs |
| `worktree-first.md` | Every task runs in its own git worktree; branch naming; base-branch resolution |
| `board-in-pr.md` | Board edits ship inside the PR carrying the change they describe |
| `board-adapter.md` | Platform-agnostic board operations (markdown / Jira / Linear / Asana) |
| `shared-standards.md` | Communication, quality gates, git + push policy, security/observability/testing baselines, Kanban protocol |
| `operational-standards.md` | API versioning, dependency management, feature flags, DB change safety, SLOs, incident severity |
| `handoff-protocol.md` | The 19 agent-to-agent handoff templates and the `docs/artifacts/{doc-type}/` filing convention (closed type list) |
| `crash-investigation.md` | Crash spike triage and the post-mortem document protocol |
| `git-hooks.md` | What the commit-msg / pre-commit / pre-push hooks enforce |
| `kotlin-agent-skills.md` | When to route a Kotlin task through a JetBrains Kotlin Agent Skill |
| `rules-delivery.md` | This file — which rules live where and how to reference them |

**The copy is generated, not authored.** `/setup-repo` writes it and `/sync-rule` refreshes it; a
manifest at `.claude/rules/shared/.synced-from` records the plugin version and a SHA-256 per file,
and `pre-push` fails when a copied file has been hand-edited. This matters because nothing else
notices: in the reference consumer, 13 of 15 copied rule files had silently forked from the plugin
before this gate existed, and the skill meant to catch it pointed at a directory that did not exist.
Project-specific rules go in `.claude/rules-local/`, which also auto-loads and wins on conflict.

**Reference form:** `@.claude/rules/shared/<name>.md`

This path resolves identically inside the tech-agency repo and inside a consumer project that has
run `/setup-repo`, because both keep the shared rules at the same location. Use it verbatim; do not
prefix it with `${CLAUDE_PLUGIN_ROOT}`.

---

## 2. Language coding standards — stay in the plugin, read on demand

These eight files are **stack-specific**. They stay in the plugin and are **not** copied into the
consumer project and **not** auto-loaded. An agent reads the one file matching the language it is
about to write, and no others.

| Standard | Path under the plugin root | Owner | Read it when the task is… |
|---|---|---|---|
| KMP shared code | `rules/mobile/shared/kmp-coding-standards.md` | @Link (consumed by @Kai, @Swift, @Nova) | Kotlin Multiplatform `commonMain` — domain, data, MVI ViewModels, expect/actual |
| Android / Compose | `rules/mobile/android/compose-coding-standards.md` | @Kai | Jetpack Compose UI, Hilt, Retrofit, Material 3, Android tests |
| iOS / SwiftUI | `rules/mobile/ios/swiftui-coding-standards.md` | @Swift | SwiftUI views, `@MainActor` ViewModels, URLSession, XCTest |
| Web / React | `rules/web/react-coding-standards.md` | @Nova | React / Next.js App Router, React Query, Zustand, Playwright |
| Node.js / Fastify | `rules/backend/nodejs/node-coding-standards.md` | @Flux | Fastify routes, Prisma, BullMQ, Zod, Pino |
| Python / FastAPI | `rules/backend/python/python-coding-standards.md` | @Pyra | FastAPI routers, SQLAlchemy 2.0, Pydantic v2, Celery, structlog |
| JVM / Spring Boot | `rules/backend/jvm/jvm-coding-standards.md` | @Forge | Spring Boot controllers, JPA, Flyway, Resilience4j, Testcontainers |
| Ktor server | `rules/backend/kotlin/ktor-server-coding-standards.md` | @Link | Ktor routes, Exposed ORM, Koin, KMP-shared client/server DTOs |

**Reference form:** `${CLAUDE_PLUGIN_ROOT}/rules/<path>.md`

`CLAUDE_PLUGIN_ROOT` is set by Claude Code to the installed plugin's root directory whenever a
plugin-provided skill or agent is running. When it is **unset** — which is the case when you are
working inside the tech-agency repo itself rather than as an installed plugin — fall back to
`.claude/rules/<path>.md`, which is the same tree at its in-repo location.

Resolve it like this before reading:

```bash
# $1 is the path under rules/, e.g. "mobile/android/compose-coding-standards.md"
resolve_standard() {
  local std="$1"
  if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -f "${CLAUDE_PLUGIN_ROOT}/rules/${std}" ]; then
    echo "${CLAUDE_PLUGIN_ROOT}/rules/${std}"
  elif [ -f ".claude/rules/${std}" ]; then
    echo ".claude/rules/${std}"
  else
    echo "coding standard not found: ${std}" >&2
    return 1
  fi
}

# Usage
STANDARD="$(resolve_standard mobile/android/compose-coding-standards.md)" || exit 1
```

Then `Read` the resolved path. If neither location has the file, say so and stop — do not write
code in that stack from memory, and do not silently substitute a different standard.

---

## 3. The obligation this creates

Because the coding standards are no longer preloaded into your context, **reading them is now an
action you must take, not a fact you can assume.**

> **Hard rule:** before writing or modifying code in a given stack, the agent MUST read that stack's
> coding standard, resolved per §2. This applies on every task, including small ones. "I know the
> Compose conventions" is not a substitute — the standard carries this project's specific
> architecture (MVI contracts, T-013 typed-render rules, `process: (Input) -> Unit` callback shape,
> file-organization rules) that generic knowledge does not.

Practical consequences:

- A task touching two stacks (e.g. a KMP change consumed by Android) requires reading **both**
  standards — `rules/mobile/shared/kmp-coding-standards.md` and
  `rules/mobile/android/compose-coding-standards.md`, each resolved per §2.
- `/code-review` reviewing code in a stack must read that stack's standard before judging it against
  it. A review that cites a standard it did not read is not a review.
- If you cannot resolve the standard, that is a blocker to report, not a step to skip. This is most
  likely in a cloud session, where the plugin may be declared but not installed — see §5.

---

## 4. Why the split

**(a) The standards were not reaching installed users at all.** A `rules/` directory at the plugin
root is not auto-loaded into an installing user's context. Before this split, every coding standard
lived only in the plugin and was therefore invisible to anyone who installed tech-agency from the
marketplace — the agents were told to follow standards the user's session had never seen. Moving
the *policy* rules into the consumer's own `.claude/rules/shared/` (where project instructions
genuinely do auto-load) and making the *stack* standards an explicit on-demand read fixes both
halves of that gap.

**(b) Loading all eight standards every session cost ~79k tokens (~317KB) regardless of stack.** An
Android-only repo was paying for the React, FastAPI, Fastify, Spring Boot and SwiftUI standards on
every single turn. Splitting delivery cuts always-on rule context from roughly 79k tokens to roughly
14k — the shared policy rules only — and the stack standard is paid for once, on the task that
actually needs it.

---

## 5. Cloud sessions — the shared rules survive, the standards may not

Cloud Claude Code sessions have no `/plugin` command and no interactive install step. That splits the
two delivery mechanisms cleanly apart, and you need to know which half you are standing on.

**The eleven shared rules work unchanged, with no plugin machinery at all.** Once `/setup-repo` has
copied them in and that commit has landed, they are ordinary committed files in the project at
`.claude/rules/shared/*.md`, and Claude Code auto-loads `.claude/rules/**/*.md` recursively as
project configuration — the same way it loads `CLAUDE.md`, `.claude/agents/*.md`, and
`.claude/skills/*/SKILL.md`. Nothing has to be installed for them to apply. This is the load-bearing
reason the split model is cloud-safe: the policy that governs *how* an agent works is in the repo,
not in the plugin. (The copy is the precondition, and it is a one-time terminal step: a repo that has
never run `/setup-repo` has no shared rules to load in cloud either.)

**The eight coding standards resolve through `${CLAUDE_PLUGIN_ROOT}` only if the plugin is actually
installed in that environment.** A repo can *declare* the plugin in its `.claude/settings.json`
(`extraKnownMarketplaces` + `enabledPlugins`), and that is the documented way to express the intent,
but declaring is not installing: as of Claude Code v2.1.195 a plugin from an external source such as
a GitHub repository does not load until it has been installed, and Claude Code reports it as not
installed. In that state `CLAUDE_PLUGIN_ROOT` is unset — and the §2 fallback of
`.claude/rules/<path>.md` also misses, because `/setup-repo` deliberately does **not** copy the
standards into the consumer project.

So in a cloud session the standards can be genuinely absent. The rule for that case:

> **If you cannot resolve your stack's coding standard, say so before writing code — do not proceed
> without it.** Report it as a blocker, name the standard you could not read, and stop. A silently
> missing standard is the exact failure this whole delivery model exists to prevent: code written
> from generic knowledge, passing review, and violating this project's architecture in ways nobody
> notices for months.

What to tell the user when you hit it — the two supported ways to close the gap, both documented in
the plugin README:

- **Install the plugin in that environment** — a cloud environment setup script (configured under
  cloud environments on claude.ai) running
  `claude plugin install tech-agency@tech-agency --scope user`.
- **Seed the plugin cache** — point `CLAUDE_CODE_PLUGIN_SEED_DIR` at a pre-populated read-only copy
  of `~/.claude/plugins`. This composes with the settings declaration: when
  `extraKnownMarketplaces` / `enabledPlugins` name a marketplace that already exists in the seed,
  Claude Code uses the seed copy instead of cloning, so no network or git auth is needed.

Both routes end with `CLAUDE_PLUGIN_ROOT` set and §2 resolving normally. Until one of them is in
place, treat the standards as unavailable rather than optional.

---

## 6. Quick reference

| You want… | Do this |
|---|---|
| A policy rule (worktree, board, handoff, push policy, hooks) | It is already in context. Cite it as `@.claude/rules/shared/<name>.md` |
| A coding standard for the stack you are about to write | Resolve per §2, then `Read` it |
| To reference a standard in a skill or agent file | Write `${CLAUDE_PLUGIN_ROOT}/rules/<path>.md`, and note the `.claude/rules/<path>.md` fallback |
| To reference any rule at all | Use the nested path. Never `.claude/rules/<name>.md` |
| A standard that will not resolve (often a cloud session) | Stop and report it as a blocker — see §5. Never write the code anyway |
