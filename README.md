# Tech Agency

**AI-powered multi-agent development team for fullstack product delivery.**

Tech Agency is a Claude Code plugin that provides 19 specialized AI agents, 24 slash commands, and 15 coding standards to orchestrate end-to-end software development across Mobile (KMP), Web, and Server platforms.

**Version:** 1.0.0 | **Author:** Zeyad Gasser

---

## What Is Tech Agency?

Tech Agency simulates a complete engineering organization inside Claude Code. Each agent has a defined role, coding standards to follow, and handoff protocols for collaborating with other agents. Work is tracked on a Kanban board (`board-context.md`), and agents communicate through structured handoff templates.

The system is designed around Kotlin Multiplatform (KMP) projects but supports the full stack: Android (Compose), iOS (SwiftUI), Web (React/Next.js), and multiple backend frameworks (Ktor, Spring Boot, Fastify, FastAPI).

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

---

## Slash Commands

| Command | Description |
|---------|-------------|
| `/kick-off` | Start the day — runs daily sync, replenishes board, picks up next task |
| `/daily-sync` | Aggregate status from all agents, flag blockers and WIP violations |
| `/new-product` | Kick off a brand new product from scratch (PRD → BRD → ADR → board) |
| `/new-feature` | Add a feature to an existing product (BRD or ADR depending on scope) |
| `/tech-task` | Start a technical/infrastructure task that isn't a product feature |
| `/rfc` | Write a Request for Comments for a large feature or technical change |
| `/pick-up-task` | Pick the next available task from the Kanban board |
| `/update-board` | Move a task between board columns (In Progress, Blocked, Review, Done) |
| `/replenish` | Review backlog, prioritize items, move them to Ready |
| `/dispatch` | Dispatch a task to an agent in an isolated git worktree for parallel execution |
| `/code-review` | Perform a structured code review on a PR or branch |
| `/create-pr` | Create a pull request with standardized format |
| `/investigate-bug` | Investigate a functional bug with root cause analysis |
| `/investigate-crash` | Investigate a Crashlytics crash spike and identify the culprit commit |
| `/hotfix` | Trigger the hotfix process for a critical production bug |
| `/dependency-upgrade` | Evaluate and upgrade project dependencies |
| `/health-check` | Run a project health audit (coverage, lint, vulnerabilities, docs) |
| `/release` | Execute the full release checklist across all agents |
| `/retro` | Run a retrospective analyzing cycle times, throughput, and blockers |
| `/sprint-report` | Generate a sprint report with metrics and trends |
| `/onboard-agent` | Rapidly onboard an agent onto an existing feature or codebase area |
| `/setup-repo` | Set up a repository with Tech Agency configuration |
| `/postmortem` | Generate a post-mortem document for an incident |
| `/capture-screenshots` | Capture screenshots for documentation or review |

---

## Coding Standards & Rules

Tech Agency includes 15 coding standards files that agents follow when writing code. These live in `.claude/rules/` and are automatically loaded as project instructions.

| Standard | Scope |
|----------|-------|
| `shared-standards.md` | Communication protocol, quality gates, git policy, security/observability/testing baselines |
| `kmp-coding-standards.md` | KMP shared code — Clean Architecture, MVI pattern, Konsist enforcement, expect/actual |
| `compose-coding-standards.md` | Android/Jetpack Compose — Hilt DI, Retrofit, Navigation, Material 3 |
| `swiftui-coding-standards.md` | iOS/SwiftUI — MVVM, async/await, NavigationStack, accessibility |
| `react-coding-standards.md` | React/Next.js — App Router, React Query, Zustand, Tailwind, Playwright |
| `node-coding-standards.md` | Node.js/Fastify — Prisma, BullMQ, Zod validation, Pino logging |
| `python-coding-standards.md` | Python/FastAPI — SQLAlchemy 2.0, Pydantic v2, Celery, structlog |
| `jvm-coding-standards.md` | Spring Boot/JVM — JPA, Flyway, Resilience4j, Testcontainers |
| `ktor-server-coding-standards.md` | Ktor Server — Exposed ORM, Koin DI, shared client-server KMP types |
| `operational-standards.md` | API versioning, feature flags, DB change safety, SLOs, incident severity |
| `handoff-protocol.md` | 19 handoff templates for structured agent-to-agent communication |
| `agent-preamble.md` | Steps every agent must perform at the start and end of any task |
| `board-adapter.md` | Platform-agnostic board operations (markdown, Jira, Linear, Asana) |
| `git-hooks.md` | Commit message format, pre-commit checks, pre-push checks |
| `crash-investigation.md` | Crashlytics crash spike investigation and post-mortem protocol |

---

## Repository Structure

```
tech-agency/
├── .claude-plugin/
│   └── marketplace.json         # Marketplace manifest (makes this repo a plugin source)
├── .claude/
│   ├── .claude-plugin/
│   │   └── plugin.json          # Plugin identity and metadata
│   ├── agents/                  # 19 agent definition files
│   │   ├── atlas-orchestrator.md
│   │   ├── kai-android-engineer.md
│   │   ├── link-kmp-engineer.md
│   │   └── ... (16 more)
│   ├── rules/                   # 15 coding standards (auto-loaded)
│   │   ├── shared-standards.md
│   │   ├── kmp-coding-standards.md
│   │   └── ... (13 more)
│   ├── skills/                  # 24 slash command skills
│   │   ├── kick-off/
│   │   ├── daily-sync/
│   │   ├── new-product/
│   │   └── ... (21 more)
│   └── settings.json            # Board backend config
├── docs/
│   ├── skills-catalog.md        # Full agent skill catalog
│   ├── references/              # Testing and observability references
│   └── by-type/                 # Cross-reference index by document type
├── hooks/                       # Git hooks (commit-msg, pre-commit, pre-push)
├── prompts/                     # Agent prompt templates
├── board-context.md             # Live Kanban board state
└── README.md
```

---

## Installation

Tech Agency is distributed as a Claude Code plugin from this GitHub repo. Installing at user scope makes it available in every project on the machine.

### First-time setup (run once per machine)

```bash
# 1. Register the marketplace
claude plugin marketplace add github:Zeyad-37/tech-agency --scope user

# 2. Install the plugin
claude plugin install tech-agency@tech-agency --scope user
```

### Auto-updates

Add this to your `~/.claude/settings.json` to automatically pull the latest version at the start of every Claude Code session:

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

After this is in place, any changes merged to `main` on this repo will be picked up automatically the next time you open Claude Code.

### Manual update

```bash
claude plugin update tech-agency --scope user
```

### Verify

Open Claude Code and type `/kick-off` to start your first daily sync.

---

## How It Works

### Kanban Board

All work is tracked in `board-context.md` with columns: Backlog → Ready → In Progress → Review → Blocked → Done. Agents pull tasks from Ready, update the board as they work, and hand off deliverables using structured templates. WIP limit is 2 items per agent.

### Handoff Protocol

Agents communicate through 19 handoff templates defined in `handoff-protocol.md`. Each handoff includes metadata (from, to, date, priority), the deliverable, and explicit action items tagged with `@AgentName`. Examples: Morgan hands a PRD to Diana, Diana hands a BRD to Sage, Sage hands ADRs to engineers.

### Approval Gate

All handoff documents (PRD, BRD, ADR, RFC, design specs, security reviews) require explicit approval from @Zeyad before the receiving agent may act on them.

### Branch Strategy

Work happens on branches following the naming convention `{STORY-ID}/{description}`. Agents commit locally but never push to remote unless explicitly told to. Git hooks enforce commit message format (`[STORY-ID] @AgentName: description`), block secrets, and prevent force-unwraps in Kotlin/Swift code.

### Parallel Execution

The `/dispatch` command creates isolated git worktrees so multiple agents can work simultaneously without file conflicts. Each agent gets its own branch and working directory.

---

## License

Private — All rights reserved.
