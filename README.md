# Tech Agency

**AI-powered multi-agent development team for fullstack product delivery.**

Tech Agency is a Claude Code plugin that provides 19 specialized AI agents, 49 skills (35 first-party workflows + 14 vendored Google/JetBrains skills), and 8 language coding standards to orchestrate end-to-end software development across Mobile (KMP), Web, and Server platforms.

**Author:** Zeyad Gasser

---

## What Is Tech Agency?

Tech Agency simulates a complete engineering organization inside Claude Code. Each agent has a defined role, coding standards to follow, and handoff protocols for collaborating with other agents. Work is tracked on a Kanban board (`board-context.md`), and agents communicate through structured handoff templates.

The system is designed around Kotlin Multiplatform (KMP) projects but supports the full stack: Android (Compose), iOS (SwiftUI), Web (React/Next.js), and multiple backend frameworks (Ktor, Spring Boot, Fastify, FastAPI).

---

## What Ships vs. What You Bootstrap

This is the single most important thing to understand before installing. **Installing the plugin is only half the setup.**

| Component | Ships with the plugin? | How you get it |
|---|---|---|
| 19 agent definitions | **Yes** | Available immediately after install |
| 49 skills (slash commands) | **Yes** | Available immediately after install |
| 8 language coding standards | **Yes**, but **read on demand** | Stay in the plugin; an agent reads the one matching its task's stack. Never auto-loaded — see [Rules delivery](#rules-delivery) |
| 11 shared policy rules | Ship in the plugin, but must be **copied into your project** | `/setup-repo` copies them to your `.claude/rules/shared/`, where they auto-load every session |
| `board-context.md` Kanban board | **No** | `/setup-repo` creates it from a template |
| Git hooks (`hooks/`) | **No** | `/setup-repo` writes them into your repo; you then run `./hooks/install-hooks.sh` once to symlink them into `.git/hooks/` |
| `.claude/settings.json` (sandbox, permissions, board backend, model routing, plus the marketplace/plugin declaration for [cloud sessions](#use-in-cloud-sessions)) | **No** | `/setup-repo` writes it into your project. The plugin's own `settings.json` does **not** configure your sandbox — Claude Code reads only a narrow set of keys from a plugin's settings file |
| `docs/` scaffolding (`docs/prd/`, `docs/adr/`, `docs/post-mortem/`, …) | **No** | Created on demand by `/setup-repo` and by the agents that file artifacts |

> **`/setup-repo` is a required post-install step, not an optional one.** Until you run it, your project has agents and skills but no board, no git hooks, no sandbox, and none of the shared policy rules in context. Agents will reference rules your session has never loaded.

Run it once per project, from the project root:

```
/setup-repo
```

### Rules delivery

Rules reach you by two different mechanisms, and the distinction matters:

- **Shared policy rules (11 files)** — copied into your project's `.claude/rules/shared/` by `/setup-repo`, then auto-loaded every session. These govern process, not code: worktrees, the board, handoffs, push policy, quality gates, hooks.
- **Language coding standards (8 files)** — stay in the plugin and are **read on demand** by the agent whose task is in that language. This is deliberate: loading all eight every session cost ~79k tokens regardless of stack, so an Android-only repo was paying for the React and FastAPI standards on every turn. The split cuts always-on rule context to roughly 14k.

The consequence: **an agent must read its stack's coding standard before writing code in that stack.** It is an action, not an ambient fact. The full model — reference forms, the `${CLAUDE_PLUGIN_ROOT}` resolution snippet, and the per-standard owner table — is in [`.claude/rules/shared/rules-delivery.md`](.claude/rules/shared/rules-delivery.md).

---

## Two Constraints That Surprise People

These are the two rules agents enforce most aggressively. If you install the plugin and are confused by an agent's behavior, it is almost certainly one of these.

### 1. Worktree-first — agents refuse to work in the main checkout

**Every task runs in its own git worktree. No exceptions.** The main checkout is an orchestration root only: it holds the canonical `.git` directory and parents the worktrees. Nothing else happens there.

Before its first file write, an agent creates a worktree at `../{repo}-worktrees/{branch-slug}/`, `cd`s into it, and verifies `pwd` + `git branch --show-current`. If you ask an agent to edit a file while standing in the main checkout, it will create a worktree first — that is correct behavior, not confusion.

Why: multiple Claude Code sessions can run in parallel on the same repo with no native way to discover each other. Requiring a worktree from the first action is the entire arbitration mechanism — no lock files, no busy-checks, no shared in-flight state.

Cleanup is automatic: every `/create-pr` run sweeps all worktrees and removes any whose PR has already merged.

The three narrow exceptions (read-only Q&A, initial `/setup-repo`, and the cleanup sweep itself) and the full protocol are in [`.claude/rules/shared/worktree-first.md`](.claude/rules/shared/worktree-first.md).

### 2. Board-in-PR — board updates ship inside the PR that carries the change

**There is no board-only PR, and no board commit on `main`.** A `board-context.md` edit is committed on the branch carrying the change it describes and merges in that change's PR. `→ Done` is written as the *final pre-merge commit* on the PR branch — not after the merge.

A direct consequence you should expect: **a checkout of `main` shows a stale or empty "In Progress" column.** In-flight transitions live on unmerged branches. The merged board is an accurate record of *completed* work; live state is derived from open PRs (`gh pr list`), not read from the file.

Full policy — where each transition commits, the `→ Done` sequencing at the merge gate, and conflict resolution — is in [`.claude/rules/shared/board-in-pr.md`](.claude/rules/shared/board-in-pr.md).

---

## Agents

### Product & Design

| Agent | Role | Key Skills |
|-------|------|------------|
| **Morgan** | Product Owner | Write PRDs, prioritize backlog, competitive analysis, release notes |
| **Diana** | Business Analyst | Write BRDs, user stories (Given/When/Then), gap analysis |
| **Sage** | Solutions Architect | Write ADRs, system design, API design, tech selection |
| **Pixel** | UI/UX Designer | Design tokens, component specs, wireframes, accessibility audits, user flows |

### Engineering

| Agent | Role | Key Skills |
|-------|------|------------|
| **Link** | KMP Engineer | Create KMP modules, expect/actual declarations, integration guides |
| **Kai** | Android Engineer | Implement Compose screens, API integration, crash investigation |
| **Swift** | iOS Engineer | Implement SwiftUI screens, API integration, crash investigation |
| **Nova** | Frontend Web Engineer | Implement React components/pages, API integration, performance audits |
| **Flux** | Backend Engineer (Node.js) | Implement Fastify endpoints, database migrations, BullMQ workers |
| **Pyra** | Backend Engineer (Python) | Implement FastAPI endpoints, database migrations, Celery tasks |
| **Forge** | Backend Engineer (JVM) | Implement Spring Boot endpoints, database migrations, services |

### Quality & Operations

| Agent | Role | Key Skills |
|-------|------|------------|
| **Atlas** | Orchestrator | Board setup, daily sync, replenishment, retrospectives |
| **Apex** | QA Engineer | Test plans, E2E tests, bug triage, release sign-off |
| **Shield** | Security Engineer | Security reviews, threat modeling, compliance audits |
| **Sentinel** | DevOps/SRE | Deploy services, Terraform, incident response, post-mortems |
| **Scroll** | Technical Writer | API docs, user guides, changelogs |
| **Echo** | Support Engineer | Ticket resolution, bug triage, feature request compilation |

### Data & AI

| Agent | Role | Key Skills |
|-------|------|------------|
| **Neuron** | AI/ML Engineer | Model cards, ML pipeline design, prompt engineering, RAG design |
| **Pipeline** | Data Engineer | Data model design, dbt models, pipeline design |

**Total: 19 agents.**

---

## Skills

49 skills ship with the plugin, all invoked as slash commands. 34 are first-party Tech Agency workflows; 14 are vendored from Google and JetBrains.

### First-party workflows (34)

#### Planning & requirements

| Command | Description |
|---------|-------------|
| `/new-product` | Kick off a brand new product from scratch (PRD → BRD → ADR → board) |
| `/new-feature` | Add a feature to an existing product (BRD or ADR depending on scope) |
| `/write-prd` | Dispatch Morgan to write a standalone PRD — no chain into BRD/ADR/board |
| `/tech-task` | Start a technical/infrastructure task that isn't a product feature |
| `/rfc` | Write a Request for Comments for a large feature or technical change |

#### Board & flow

| Command | Description |
|---------|-------------|
| `/kick-off` | Start the day — runs daily sync, replenishes board, picks up next task |
| `/daily-sync` | Aggregate status from all agents, flag blockers and WIP violations |
| `/pick-up-task` | Pick the next available task from the Kanban board |
| `/update-board` | Move a task between board columns (In Progress, Blocked, Review, Done) |
| `/migrate-board` | Migrate a markdown board to GitHub Issues + Projects v2; repairs, dry-runs, never deletes |
| `/replenish` | Review backlog, prioritize items, move them to Ready |
| `/sprint-report` | Generate a sprint report with metrics and trends |
| `/retro` | Run a retrospective analyzing cycle times, throughput, and blockers |

#### Parallel execution

| Command | Description |
|---------|-------------|
| `/dispatch` | Dispatch a task to an agent in an isolated git worktree for parallel execution |
| `/dispatch-task` | Plan (tech-task / new-feature / bug / crash chain) then dispatch the implementation in parallel |

#### Ship a change

| Command | Description |
|---------|-------------|
| `/ship-it` | End-to-end delivery: kickoff → implement → `/ship-pr` (PR → review → merge); `--auto-merge` flag |
| `/ship-pr` | Ready branch → open PR → `/review-and-address` → merge; `--auto-merge` flag |
| `/create-pr` | Create a pull request with standardized format. Auto-pushes by default; `--no-push` stops at the pre-push gate |
| `/code-review` | Perform a structured code review on a PR or branch, in a fresh-context subagent |
| `/review-and-address` | Existing PR → `/code-review` (post verdict) → `/address-feedback`; `--auto-merge` flag |
| `/address-feedback` | Resolve all PR comments + failing checks; `--auto-merge` flag to merge once green |
| `/capture-screenshots` | Capture before/after screenshots for UI changes (Paparazzi / swift-snapshot-testing / Playwright) |
| `/lint-changed` | Run detekt per-changed-file via SARIF diff — reports only violations the branch introduced |

#### Diagnose & respond

| Command | Description |
|---------|-------------|
| `/investigate-bug` | Investigate a functional bug with root cause analysis |
| `/investigate-crash` | Investigate a Crashlytics crash spike and identify the culprit commit |
| `/postmortem` | Write a 5-Whys post-mortem tracing both how the issue was introduced and how it escaped each gate |
| `/hotfix` | Trigger the hotfix process for a critical production bug |
| `/health-check` | Run a project health audit (coverage, lint, vulnerabilities, docs) |

#### Maintain the system

| Command | Description |
|---------|-------------|
| `/setup-repo` | Set up a repository with Tech Agency configuration — **required after install** |
| `/onboard-agent` | Rapidly onboard an agent onto an existing feature or codebase area |
| `/dependency-upgrade` | Evaluate and upgrade project dependencies |
| `/extract-library` | Extract a module into a standalone published KMP library (Maven Central, consumer swap, composite-build dev flow) |
| `/sync-rule` | Mirror edits in `.claude/rules/` between a consumer project and this canonical repo, so the two don't drift |
| `/release` | Execute the full release checklist across all agents |
| `/audit-memory` | Audit Claude Code's auto-memory store for stale or duplicate entries (run every ~30 days) |

### Vendored skills (14)

Copied (not submoduled) into `.claude/skills/`, version-pinned to an upstream commit. Both sets are Apache-2.0; provenance, commit pins, and attribution are recorded in [`.claude/skills/VENDORED-SKILLS.md`](.claude/skills/VENDORED-SKILLS.md).

**From [github.com/android/skills](https://github.com/android/skills) — Google LLC (10):**

| Skill | Use it for |
|---|---|
| `/android-cli` | Driving the `android` CLI — emulators, deploys, SDK management, docs search |
| `/android-compose-theming` | Compose Styles API, design-system theming, `Modifier.styleable` |
| `/android-compose-adaptive` | Adaptive/responsive UI across phones, tablets, foldables, TV, XR |
| `/android-xml-to-compose` | Migrating a legacy XML View to Compose |
| `/android-navigation-3` | Navigation 3 — deep links, multi-backstack, scenes |
| `/android-edge-to-edge` | Edge-to-edge migration, system-bar and IME inset bugs |
| `/android-testing-setup` | Standing up Android test infrastructure and harnesses |
| `/android-r8-analyzer` | Auditing R8 keep rules, app-size optimization |
| `/android-perfetto-trace-analysis` | Root-causing jank, latency, and memory from a Perfetto trace |
| `/android-perfetto-sql` | Translating a data question into Perfetto SQL against a trace |

**From [github.com/Kotlin/kotlin-agent-skills](https://github.com/Kotlin/kotlin-agent-skills) — JetBrains (4):**

| Skill | Use it for |
|---|---|
| `/kotlin-backend-jpa-entity-mapping` | JPA/Hibernate entity design, N+1 and `LazyInitializationException` diagnosis |
| `/kotlin-tooling-java-to-kotlin` | Framework-aware Java → idiomatic Kotlin conversion |
| `/kotlin-tooling-agp9-migration` | AGP 9.0+ upgrades and KMP + AGP incompatibilities |
| `/kotlin-tooling-cocoapods-spm-migration` | Migrating KMP iOS interop from CocoaPods to Swift Package Manager |

---

## Rules

19 rule files ship with the plugin, in two sets with two different delivery mechanisms. See [Rules delivery](#rules-delivery) above, and [`.claude/rules/shared/rules-delivery.md`](.claude/rules/shared/rules-delivery.md) for the authoritative model.

### Shared policy rules (11) — copied into your project, auto-loaded every session

| Rule | Scope |
|------|-------|
| [`shared/rules-delivery.md`](.claude/rules/shared/rules-delivery.md) | Which rules live where, how to reference each, and the on-demand read obligation |
| [`shared/agent-preamble.md`](.claude/rules/shared/agent-preamble.md) | Steps every agent must perform at the start and end of any task |
| [`shared/worktree-first.md`](.claude/rules/shared/worktree-first.md) | Every task runs in its own git worktree; branch naming; base-branch resolution |
| [`shared/board-in-pr.md`](.claude/rules/shared/board-in-pr.md) | Board edits ship inside the PR carrying the change they describe |
| [`shared/board-adapter.md`](.claude/rules/shared/board-adapter.md) | Platform-agnostic board operations (markdown, Jira, Linear, Asana) |
| [`shared/shared-standards.md`](.claude/rules/shared/shared-standards.md) | Communication, quality gates, git + push policy, security/observability/testing baselines, Kanban protocol |
| [`shared/operational-standards.md`](.claude/rules/shared/operational-standards.md) | API versioning, feature flags, DB change safety, SLOs, incident severity, privacy |
| [`shared/handoff-protocol.md`](.claude/rules/shared/handoff-protocol.md) | 19 handoff templates for structured agent-to-agent communication |
| [`shared/crash-investigation.md`](.claude/rules/shared/crash-investigation.md) | Crash spike investigation and post-mortem protocol |
| [`shared/git-hooks.md`](.claude/rules/shared/git-hooks.md) | Commit message format, pre-commit checks, pre-push checks |
| [`shared/kotlin-agent-skills.md`](.claude/rules/shared/kotlin-agent-skills.md) | When to route a Kotlin task through a JetBrains Kotlin Agent Skill |

### Language coding standards (8) — stay in the plugin, read on demand

| Standard | Owner | Scope |
|----------|-------|-------|
| [`mobile/shared/kmp-coding-standards.md`](.claude/rules/mobile/shared/kmp-coding-standards.md) | Link | KMP shared code — Clean Architecture, MVI pattern, Konsist enforcement, expect/actual |
| [`mobile/android/compose-coding-standards.md`](.claude/rules/mobile/android/compose-coding-standards.md) | Kai | Android/Jetpack Compose — Hilt DI, Retrofit, Navigation, Material 3 |
| [`mobile/ios/swiftui-coding-standards.md`](.claude/rules/mobile/ios/swiftui-coding-standards.md) | Swift | iOS/SwiftUI — MVVM, async/await, NavigationStack, accessibility |
| [`web/react-coding-standards.md`](.claude/rules/web/react-coding-standards.md) | Nova | React/Next.js — App Router, React Query, Zustand, Tailwind, Playwright |
| [`backend/nodejs/node-coding-standards.md`](.claude/rules/backend/nodejs/node-coding-standards.md) | Flux | Node.js/Fastify — Prisma, BullMQ, Zod validation, Pino logging |
| [`backend/python/python-coding-standards.md`](.claude/rules/backend/python/python-coding-standards.md) | Pyra | Python/FastAPI — SQLAlchemy 2.0, Pydantic v2, Celery, structlog |
| [`backend/jvm/jvm-coding-standards.md`](.claude/rules/backend/jvm/jvm-coding-standards.md) | Forge | Spring Boot/JVM — JPA, Flyway, Resilience4j, Testcontainers |
| [`backend/kotlin/ktor-server-coding-standards.md`](.claude/rules/backend/kotlin/ktor-server-coding-standards.md) | Link | Ktor Server — Exposed ORM, Koin DI, shared client-server KMP types |

The nested directory layout above is canonical in the plugin and in every consumer project. The old flat layout (`.claude/rules/<name>.md`) is dead.

---

## Repository Structure

```
tech-agency/
├── .claude-plugin/
│   └── marketplace.json         # Marketplace manifest — publishes the plugin below
├── .claude/                     # ← the tech-agency plugin itself (marketplace source)
│   ├── agents/                  # 19 agent definition files
│   ├── rules/
│   │   ├── shared/              # 11 shared policy rules (copied into consumers by /setup-repo)
│   │   ├── mobile/{shared,android,ios}/   # KMP, Compose, SwiftUI standards
│   │   ├── web/                 # React standard
│   │   └── backend/{nodejs,python,jvm,kotlin}/  # Fastify, FastAPI, Spring, Ktor standards
│   ├── skills/                  # 49 skills — 35 first-party + 14 vendored
│   │   ├── VENDORED-SKILLS.md   # Provenance, commit pins, licensing for the vendored 14
│   │   └── LICENSE-APACHE-2.0.txt
│   ├── hooks.json               # Session hooks
│   └── settings.json            # This repo's own config — NOT applied to installing users
├── docs/
│   ├── setup-guide.md           # Install + /setup-repo walkthrough
│   ├── migration-guide.md       # Incremental adoption for existing projects
│   ├── skills-catalog.md        # Per-agent inline skill catalog
│   ├── prompts/                 # Slash command reference + prompting cheat sheet
│   └── references/              # Testing and observability deep references
├── hooks/                       # Git hooks (commit-msg, pre-commit, pre-push, install-hooks.sh)
├── board-context.md             # This repo's own Kanban board
├── VERSION
└── README.md
```

---

## Installation

Tech Agency is distributed as a Claude Code plugin from this GitHub repo. Installing at user scope makes it available in every project on the machine.

These steps are for the **terminal**. For cloud Claude Code sessions — which have no `/plugin` command — see [Use in cloud sessions](#use-in-cloud-sessions).

### 1. Register the marketplace and install (once per machine)

```bash
claude plugin marketplace add github:Zeyad-37/tech-agency --scope user
claude plugin install tech-agency@tech-agency --scope user
```

The marketplace name and the plugin name are both `tech-agency`, hence `tech-agency@tech-agency`.

### 2. Bootstrap each project (required, once per project)

Open Claude Code in your project and run:

```
/setup-repo
```

This writes the shared policy rules into `.claude/rules/shared/`, creates `board-context.md`, installs the git hooks into `hooks/`, and writes `.claude/settings.json` (sandbox, permissions, board backend, model routing). Then install the git hooks into `.git/`:

```bash
./hooks/install-hooks.sh
```

**Skipping step 2 leaves you with agents and skills but no board, no hooks, no sandbox, and no policy rules in context.**

### 3. Verify

```
/daily-sync
```

should read your new board and report status. Then `/kick-off` to start work.

### Auto-updates

Add this to your `~/.claude/settings.json` to pull the latest version at the start of every session:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "claude plugin update tech-agency --scope user 2>/dev/null || true"
          }
        ]
      }
    ]
  }
}
```

Any change merged to `main` on this repo is then picked up automatically the next time you open Claude Code.

### Manual update

```bash
claude plugin update tech-agency --scope user
```

---

## Use in Cloud Sessions

The steps above are terminal-only. **Cloud Claude Code sessions have no `/plugin` command** — the docs are explicit that commands which only run in the terminal interface, such as `/plugin` or `/resume`, aren't available there. To change what a cloud session loads you use environment variables or settings files committed to the repository. This section is how you get the agency into a cloud session.

This repo is **public**, so the marketplace clone needs no credentials. (A private marketplace would need a git credential helper or a token URL rewrite configured in the cloud environment — public avoids that entirely.)

### 1. Declare the marketplace and plugin in the repo (the primary answer)

In every repo where you want the agency, commit this to `.claude/settings.json`:

```json
{
  "extraKnownMarketplaces": {
    "tech-agency": { "source": { "source": "github", "repo": "Zeyad-37/tech-agency" } }
  },
  "enabledPlugins": { "tech-agency@tech-agency": true }
}
```

`/setup-repo` writes both keys for you, merging them into whatever `.claude/settings.json` already has. Once a team member trusts the repository folder, Claude Code adds the marketplace without a further prompt — that part is automatic.

### 2. The caveat — read this before you rely on step 1

Declaring an external-source plugin in project settings **registers the marketplace but does not by itself install the plugin.** As of Claude Code v2.1.195, a plugin that only the project's `.claude/settings.json` enables, and that comes from an external source such as a GitHub repository, does not load until the team member installs it. Until then Claude Code reports the plugin as not installed and prints the `claude plugin install` command to run.

So step 1 is necessary but not always sufficient. On a machine or cloud environment that has never installed tech-agency, expect the first session to report it missing. The two supported ways to close that gap are below — pick one if you need the agency present unattended.

### 3a. Cloud environment setup script

In claude.ai → **cloud environments**, add to the environment's setup script:

```bash
claude plugin install tech-agency@tech-agency --scope user
```

`--scope user` installs it for the environment's user rather than a single project, so every cloud session provisioned from that environment starts with it. This is the documented way to close the gap in step 2: the setup script runs before your sessions do, so the plugin is already installed by the time one starts. It composes with step 1: the repo settings still declare the marketplace and express intent.

### 3b. Seed directory (containers and CI)

For images you build yourself, pre-populate a plugins directory at build time and point Claude Code at it as a read-only seed:

```dockerfile
# Build time — install normally, then snapshot ~/.claude/plugins as the seed
RUN claude plugin marketplace add Zeyad-37/tech-agency \
 && claude plugin install tech-agency@tech-agency \
 && cp -R "$HOME/.claude/plugins" /opt/claude-seed \
 && chmod -R a-w /opt/claude-seed

# Run time — read from it
ENV CLAUDE_CODE_PLUGIN_SEED_DIR=/opt/claude-seed
```

The seed is a copy of `~/.claude/plugins` and must keep that layout (`known_marketplaces.json`, `marketplaces/<name>/`, `cache/<marketplace>/<plugin>/<version>/`) — which is why the recipe above populates it by installing normally and copying the result, rather than by hand-assembling directories. At run time it is read-only and needs no network. It composes with step 1: when `extraKnownMarketplaces` or `enabledPlugins` declare a marketplace that already exists in the seed, Claude Code uses the seed copy instead of cloning.

### 4. The zero-machinery fallback

`.claude/skills/*/SKILL.md`, `.claude/agents/*.md` and `.claude/rules/**/*.md` committed directly in a repo are loaded as ordinary project config — no plugin, no marketplace, no auth, no install step. The cloud docs confirm it: subagents defined in your repo's `.claude/agents/` are picked up automatically. This always works, including in cloud sessions.

The cost is a copy per repo that drifts from upstream. `/setup-repo` already uses exactly this mechanism for the 11 shared policy rules, and `/sync-rule` exists to reconcile the drift. Vendoring the agents and skills the same way is the escape hatch when you cannot run an install step at all.

### Which mechanism to use

| Mechanism | Works in cloud | Needs auth | Unattended | Drifts |
|---|---|---|---|---|
| Repo `.claude/settings.json` (§1) | Yes — registers the marketplace | No (repo is public) | Only if the plugin is already installed | No |
| Cloud environment setup script (§3a) | Yes | No | Yes | No |
| Seed directory (§3b) | Yes | No (network-free at run time) | Yes | Only at image rebuild |
| Vendored `.claude/` (§4) | Yes | No | Yes | Yes — per-repo copy |

The practical recommendation: commit §1 in every repo, and add §3a to your cloud environment once. §3b is for self-built container images; §4 is the fallback when neither is available.

---

## Companion marketing plugin

A companion **marketing-agency** plugin lives in its own separate private repository and installs from its own marketplace; see that repo for its install instructions. It is not published from this marketplace.

---

## How It Works

### Kanban Board

All work is tracked in `board-context.md` with columns: Backlog → Ready → In Progress → Review → Blocked → Done. Agents pull tasks from Ready, update the board as they work, and hand off deliverables using structured templates. WIP limit is 2 items per agent. Board updates ship inside the PR carrying the change — see [Board-in-PR](#2-board-in-pr--board-updates-ship-inside-the-pr-that-carries-the-change).

### Handoff Protocol

Agents communicate through 19 handoff templates defined in `handoff-protocol.md`. Each handoff includes metadata (from, to, date, priority), the deliverable, and explicit action items tagged with `@AgentName`. Examples: Morgan hands a PRD to Diana, Diana hands a BRD to Sage, Sage hands ADRs to engineers.

### Approval Gate

All handoff documents (PRD, BRD, ADR, RFC, design specs, security reviews) require explicit approval from @Zeyad before the receiving agent may act on them.

### Branch Strategy & Push Policy

Work happens on branches named by task type: `{STORY-ID}/{slug}`, `tech/{slug}`, `deps/{slug}`, `hotfix/{version}/{slug}`, `{BUG-ID}/{slug}`.

**Invoking `/create-pr` or `/ship-pr` is itself the authorization to push that branch** — those skills commit, run the pre-push gate, push, and open the PR without asking again. Outside them, agents never run a bare `git push`; they commit locally and let the skill push. Nothing ever pushes to `main`.

Git hooks enforce the commit message format `[ID] @Agent: description` — where `[ID]` is letters optionally followed by `-<digits>` (`[US-042]`, `[T-015]`, `[TECH]`) and the `@Agent:` tag is optional — plus secret detection, force-unwrap blocking in Kotlin/Swift, lint, and branch-name checks.

### Parallel Execution

`/dispatch` creates isolated git worktrees so multiple agents can work simultaneously without file conflicts. Each agent gets its own branch and working directory. Worktrees branch off — and PR back into — a dynamically resolved base: an explicit `--base <branch>`, an epic integration branch (`epic/{EPIC-ID}-{slug}`), a hotfix release tag, or `main` by default.

`/dispatch-task` layers planning on top: it runs the appropriate planning chain (`/tech-task`, `/new-feature`, `/investigate-bug`, or `/investigate-crash`) first, waits for approval, then dispatches the resulting implementation tasks to parallel worktrees.

---

## Documentation

| Doc | What it covers |
|---|---|
| [`docs/setup-guide.md`](docs/setup-guide.md) | Install, `/setup-repo`, what lands where, verification |
| [`docs/migration-guide.md`](docs/migration-guide.md) | Phased adoption in an existing codebase |
| [`docs/prompts/commands-reference.md`](docs/prompts/commands-reference.md) | Full reference for every slash command |
| [`docs/prompts/cheat-sheet.md`](docs/prompts/cheat-sheet.md) | Copy-pasteable prompts for common workflows |
| [`docs/skills-catalog.md`](docs/skills-catalog.md) | Per-agent inline skills (natural-language triggered) |
| [`docs/board-config.md`](docs/board-config.md) | Board backend configuration (markdown / Jira / Linear / Asana) |
| [`docs/ci-enforcement-policy.md`](docs/ci-enforcement-policy.md) | Quality gates, thresholds, ratchet mechanism |
| [`docs/incident-response.md`](docs/incident-response.md) | Escalation, on-call, runbooks, feedback loops |
| [`docs/tool-integrations.md`](docs/tool-integrations.md) | MCP connections per agent |
| [`docs/project-knowledge-map.md`](docs/project-knowledge-map.md) | What context each agent needs |

---

## License

Source-available, all rights reserved — the repository is public so the marketplace can be cloned, but the author's own work carries no usage grant. Vendored skills under `.claude/skills/` are Apache-2.0 and are explicitly carved out. Full terms: [`LICENSE`](LICENSE); provenance for the vendored skills: [`.claude/skills/VENDORED-SKILLS.md`](.claude/skills/VENDORED-SKILLS.md).
