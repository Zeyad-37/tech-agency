# Tech Agency — Setup Guide

## Structure

The agency is split between user-level (available in all projects) and project-level (per codebase). Agent definitions live at `~/.claude/agents/` and are loaded on demand. Everything else is copied into each project from the template.

```
your-project/                        # Copy project-template/ into each new project
├── CLAUDE.md                        # Agency overview, roster, workflow
├── board-context.md                # Kanban board state
├── .claude/
│   ├── settings.json                # Model routing (Opus/Sonnet/Haiku per agent) and permissions
│   ├── hooks.json                   # Session hooks (Crashlytics injection, commit reminders)
│   ├── post-mortems/
│   │   └── INDEX.md                 # Post-mortem index (date, incident, severity, report link)
│   ├── rules/
│   │   ├── agent-preamble.md        # Session start/end checklist for every agent
│   │   ├── shared-standards.md      # Communication, QA, security, releases, Kanban protocol
│   │   ├── operational-standards.md # API versioning, dependencies, feature flags, performance, privacy
│   │   ├── handoff-protocol.md      # All handoff templates + archiving convention
│   │   ├── crash-investigation.md   # Crash triage & post-mortem protocol
│   │   ├── worktree-first.md        # Every task runs in its own git worktree
│   │   ├── board-in-pr.md           # Board edits ship inside the PR carrying the change
│   │   ├── node-coding-standards.md # Node.js/Fastify/Prisma coding standards (Flux)
│   │   ├── python-coding-standards.md # Python/FastAPI/SQLAlchemy coding standards (Pyra)
│   │   ├── jvm-coding-standards.md  # JVM/Spring Boot/JPA coding standards (Forge)
│   │   ├── react-coding-standards.md # React/Next.js/TypeScript coding standards (Nova)
│   │   ├── swiftui-coding-standards.md # SwiftUI/iOS coding standards (Swift)
│   │   ├── compose-coding-standards.md # Jetpack Compose/Android coding standards (Kai)
│   │   ├── kmp-coding-standards.md  # Kotlin Multiplatform coding standards (Link/Kai/Swift/Nova)
│   │   ├── ktor-server-coding-standards.md # Ktor server coding standards (Link)
│   │   ├── git-hooks.md              # What git hooks enforce (reference for agents)
│   │   └── board-adapter.md         # Board backend adapter (markdown / Jira / Linear / etc.)
│   └── skills/                      # Slash commands (invoke with /command-name)
│       ├── daily-sync/SKILL.md      # Daily Kanban board sync
│       ├── replenish/SKILL.md       # Backlog prioritization & Ready column fill
│       ├── retro/SKILL.md           # Retrospective with cycle time analysis
│       ├── new-product/SKILL.md     # Full kickoff: PRD → BRD → ADR → Board
│       ├── new-feature/SKILL.md     # Feature kickoff, adapts to scope
│       ├── release/SKILL.md         # Full release checklist and deploy
│       ├── hotfix/SKILL.md          # Emergency fix pipeline
│       ├── investigate-crash/SKILL.md # Crash triage and post-mortem
│       ├── investigate-bug/SKILL.md   # Functional bug investigation and fix plan
│       ├── pick-up-task/SKILL.md      # Pull next task from board and begin work
│       ├── kick-off/SKILL.md          # Daily sync + replenish + pick up task
│       ├── code-review/SKILL.md       # Structured code review with verdict
│       ├── health-check/SKILL.md      # Project health audit with action items
│       ├── onboard-agent/SKILL.md     # Fast-track agent onto a feature
│       ├── dependency-upgrade/SKILL.md # Audit, upgrade, and verify dependencies
│       ├── rfc/SKILL.md               # Write an RFC for large features
│       ├── sprint-report/SKILL.md     # Sprint metrics, cycle times, agent utilization
│       ├── tech-task/SKILL.md         # Technical/infrastructure task kickoff
│       ├── dispatch/SKILL.md          # Dispatch parallel tasks via git worktrees
│       ├── dispatch-task/SKILL.md     # Plan (tech-task/feature/bug/crash) then dispatch in parallel
│       ├── update-board/SKILL.md      # Update board status and commit on branch
│       ├── create-pr/SKILL.md        # Create standardized PR with task ID and agents
│       ├── capture-screenshots/SKILL.md # Before/after screenshots for UI changes
│       ├── postmortem/SKILL.md        # 5 Whys root cause analysis post-mortem
│       └── setup-repo/SKILL.md       # Set up repo with Tech Agency (new or existing projects)
├── hooks/                           # Git hooks (symlinked into .git/hooks/)
│   ├── pre-commit                   # Secrets, force-unwraps, lint, large files
│   ├── commit-msg                   # Commit message format validation
│   ├── pre-push                     # Branch naming, tests, build verification
│   └── install-hooks.sh             # Installer script (run once after clone)
├── docs/                            # Reference (human + agent use)
│   ├── setup-guide.md               # This file
│   ├── migration-guide.md           # Incremental adoption for existing projects
│   ├── ci-enforcement-policy.md     # Quality gates, thresholds, ratchet mechanism
│   ├── incident-response.md         # Escalation, on-call, runbooks, feedback loops
│   ├── skills-catalog.md            # All agent skills
│   ├── tool-integrations.md         # MCP connections
│   ├── board-config.md              # Board backend configuration (markdown / Jira / Linear)
│   ├── project-knowledge-map.md     # What each agent needs
│   └── prompts/                     # Copy-pasteable prompt templates
│       ├── cheat-sheet.md           # Prompting guide for all workflows
│       └── commands-reference.md    # Slash command documentation
```

## How It Works

1. **Agents** at `~/.claude/agents/` are available across all projects, loaded only when invoked (zero startup cost)
2. **Project CLAUDE.md** loads at session start with the agency roster and workflow
3. **Rules** in `.claude/rules/` load on-demand when referenced
4. **Each agent is self-contained** — backend/frontend standards are inlined, so agents work without project-level rule files for their technical standards

## Initial Setup

### 1. Copy agents to user-level
```bash
cp agents/*.md ~/.claude/agents/
```

### 2. For each new project, copy the template
```bash
# From the tech-agency root, copy all project-template contents into your project
cp -r project-template/* /path/to/your-project/
cp -r project-template/.claude /path/to/your-project/
```

### 3. Configure MCP connections (if needed)
Only 9 agents need external tools — see @docs/guides/tool-integrations.md.

## Using the Agency

1. Start with **Morgan** — describe the product vision → PRD
2. Morgan → **Diana** — Diana breaks PRD into detailed BRD
3. Diana → **Sage** — Sage produces ADRs and tech spec
4. Sage fans out → **Pixel** (design), **Pipeline** (data), **Neuron** (ML), engineers
5. **Atlas** coordinates all tasks, blockers, handoffs
6. **Shield** reviews security before deployment
7. **Apex** validates quality and signs off
8. **Sentinel** deploys infrastructure and services
9. **Scroll** writes documentation
10. **Echo** monitors post-release support

## Verification

Test these to confirm the agency works:

- Morgan: "Write PRD for a task management app"
- Diana: Paste Morgan's PRD → should produce BRD
- Sage: Paste Diana's BRD → should produce ADRs
- Atlas: "Set up the board for user-auth feature" → structured Kanban board
- Flux: "Implement POST /api/users" → production-ready code
- Apex: "Write test plan for user auth" → structured test plan
