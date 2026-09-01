# Tech Agency — Setup Guide

Tech Agency is installed as a **Claude Code plugin from a marketplace**. There is no directory to
copy by hand: you install the plugin, then run `/setup-repo` once per project to bootstrap the
pieces that must live in *your* repo.

> If you are looking for the old `cp -r project-template/* …` instructions: that directory never
> existed in this repo and the instructions did not work. The plugin + `/setup-repo` flow below
> replaces them.

---

## Step 1 — Install the plugin (once per machine)

```bash
claude plugin marketplace add github:Zeyad-37/tech-agency --scope user
claude plugin install tech-agency@tech-agency --scope user
```

The marketplace and the plugin share the name `tech-agency`, hence `tech-agency@tech-agency`.
`--scope user` makes the agents and skills available in every project on the machine.

This repo's marketplace also publishes a sibling plugin, `marketing-agency`. Install it only if you
want it:

```bash
claude plugin install marketing-agency@tech-agency --scope user
```

### What you now have

- **19 agents** — available immediately, loaded on demand when invoked.
- **48 skills** (slash commands) — 34 first-party workflows + 14 vendored Google/JetBrains skills.
- **8 language coding standards** — shipped inside the plugin, **read on demand**, not auto-loaded.

### What you do NOT yet have

- No `board-context.md`.
- No git hooks.
- No `.claude/settings.json` — **and therefore no sandbox**. The plugin ships its own
  `settings.json`, but Claude Code reads only a narrow set of keys from a plugin's settings file;
  `sandbox`, `permissions`, and `board_backend` are not among them. Nothing in the plugin configures
  your project.
- None of the 11 shared policy rules in your session context.

Step 2 fixes all of that.

---

## Step 2 — Bootstrap the project (required, once per project)

Open Claude Code in your project root and run:

```
/setup-repo
```

`/setup-repo` audits what already exists and fills the gaps. It never overwrites a file you already
have. After it runs, your project looks like this:

```
your-project/
├── board-context.md                # Kanban board state
├── .claude/
│   ├── settings.json               # Sandbox, permissions, board backend
│   ├── hooks.json                  # Session hooks
│   └── rules/
│       └── shared/                 # The 11 shared policy rules — auto-load every session
│           ├── rules-delivery.md   # Which rules live where and how to reference them
│           ├── agent-preamble.md   # Session start/end checklist for every agent
│           ├── worktree-first.md   # Every task runs in its own git worktree
│           ├── board-in-pr.md      # Board edits ship inside the PR carrying the change
│           ├── board-adapter.md    # Board backend adapter (markdown / Jira / Linear / …)
│           ├── shared-standards.md # Communication, QA, git + push policy, security, Kanban
│           ├── operational-standards.md  # API versioning, flags, DB safety, SLOs, privacy
│           ├── handoff-protocol.md # Handoff templates + docs/{doc-type}/ filing convention
│           ├── crash-investigation.md    # Crash triage & post-mortem protocol
│           ├── git-hooks.md        # What the git hooks enforce
│           └── kotlin-agent-skills.md    # Routing Kotlin tasks to JetBrains skills
├── hooks/                          # Git hooks — written here, installed in step 3
│   ├── pre-commit                  # Secrets, force-unwraps, lint, large files
│   ├── commit-msg                  # Commit message format validation
│   ├── pre-push                    # Branch naming, direct-push-to-main block, tests, build
│   └── install-hooks.sh            # Installer (symlinks into .git/hooks/)
└── docs/                           # Artifact folders, created as agents file into them
    ├── prd/  brd/  adr/  rfc/  design-spec/
    ├── post-mortem/  incident-notes/  release-record/
    └── tech-debt/
```

**Note what is *not* copied: the 8 language coding standards.** They stay in the plugin. Agents read
the one matching their task's stack, on demand. See [Rules delivery](#rules-delivery) below.

---

## Step 3 — Install the git hooks

`/setup-repo` writes the hook scripts into `hooks/`, but symlinking them into `.git/hooks/` is a
local action you run yourself:

```bash
./hooks/install-hooks.sh
```

Verify:

```bash
ls -l .git/hooks/pre-commit .git/hooks/commit-msg .git/hooks/pre-push
```

Each should be a symlink into `hooks/`. What they enforce is documented in
`@.claude/rules/shared/git-hooks.md` — most importantly the commit format `[ID] @Agent: description`,
where `[ID]` is letters optionally followed by `-<digits>` (`[US-042]`, `[T-015]`, `[TECH]`) and the
`@Agent:` tag is optional.

---

## Step 4 — Verify

```bash
# Shared rules landed
ls .claude/rules/shared/            # expect 11 files

# Sandbox configured
grep -q '"sandbox"' .claude/settings.json && echo "sandbox OK" || echo "NO sandbox"

# Board exists
test -f board-context.md && echo "board OK"

# Hooks installed
test -L .git/hooks/pre-commit && echo "hooks OK"
```

Then in Claude Code:

```
/daily-sync
```

It should read your new board and report status. `/kick-off` starts the working loop (sync →
replenish → pick up a task).

---

## Rules delivery

Rules reach you by two different mechanisms. Confusing them is the most common source of "the agent
referenced a rule I don't have."

**Shared policy rules (11)** — copied into `.claude/rules/shared/` by `/setup-repo`, then auto-loaded
by Claude Code every session. Reference them as `@.claude/rules/shared/<name>.md`. They govern
process, not code.

**Language coding standards (8)** — stay in the plugin, **read on demand** by the agent whose task is
in that language. Reference them as `${CLAUDE_PLUGIN_ROOT}/rules/<path>.md`, falling back to
`.claude/rules/<path>.md` when `CLAUDE_PLUGIN_ROOT` is unset (i.e. when working inside the
tech-agency repo itself).

| Standard | Path under the plugin root | Owner |
|---|---|---|
| KMP shared code | `rules/mobile/shared/kmp-coding-standards.md` | Link |
| Android / Compose | `rules/mobile/android/compose-coding-standards.md` | Kai |
| iOS / SwiftUI | `rules/mobile/ios/swiftui-coding-standards.md` | Swift |
| Web / React | `rules/web/react-coding-standards.md` | Nova |
| Node.js / Fastify | `rules/backend/nodejs/node-coding-standards.md` | Flux |
| Python / FastAPI | `rules/backend/python/python-coding-standards.md` | Pyra |
| JVM / Spring Boot | `rules/backend/jvm/jvm-coding-standards.md` | Forge |
| Ktor server | `rules/backend/kotlin/ktor-server-coding-standards.md` | Link |

Why the split: a plugin-root `rules/` directory is not auto-loaded into an installing user's
context, so before this model the standards never reached installed users at all. And loading all
eight every session cost ~79k tokens regardless of stack — a React standard sitting in an Android
repo's context on every turn. The split cuts always-on rule context to roughly 14k.

The consequence, and it is a hard rule: **an agent must read its stack's coding standard before
writing code in that stack.** The authoritative model, including the shell snippet for resolving the
path, is in `@.claude/rules/shared/rules-delivery.md`.

The nested layout above is canonical in the plugin and in your project alike. Flat paths like
`.claude/rules/compose-coding-standards.md` are dead — never use one.

---

## Configure MCP connections (optional)

Only some agents need external tools (issue trackers, monitoring, design tools). See
`docs/tool-integrations.md` for which agent needs what and how to wire it up. If you want the board
backed by Jira, Linear, or Asana instead of `board-context.md`, see `docs/board-config.md`.

---

## Adopting in an existing codebase

`/setup-repo` is non-destructive and safe to run on an existing project — it skips anything already
present. For the phased rollout of the *standards* (which gates to turn on when, how to ratchet
coverage, how to migrate architecture gradually), see `docs/migration-guide.md`.

---

## Using the agency

The typical chain for new work:

1. **Morgan** — describe the product vision → PRD
2. Morgan → **Diana** — Diana breaks the PRD into a detailed BRD
3. Diana → **Sage** — Sage produces ADRs and the tech spec
4. Sage fans out → **Pixel** (design), **Pipeline** (data), **Neuron** (ML), and the engineers
5. **Atlas** coordinates tasks, blockers, and handoffs
6. **Shield** reviews security before deployment
7. **Apex** validates quality and signs off
8. **Sentinel** deploys infrastructure and services
9. **Scroll** writes documentation
10. **Echo** monitors post-release support

Every document in that chain waits for your approval before the next agent acts.

In practice you drive it with slash commands rather than by naming agents:
`/new-product`, `/new-feature`, `/tech-task` to plan; `/ship-it` to take a change from kickoff to
merged. See `docs/prompts/commands-reference.md` for all 34 first-party commands and
`docs/prompts/cheat-sheet.md` for copy-pasteable prompts.

---

## Two behaviors that will surprise you

- **Agents refuse to work in the main checkout.** Every task creates its own git worktree at
  `../{repo}-worktrees/{branch-slug}/` before its first file write. This is the entire mechanism
  preventing parallel sessions from stomping on each other. See
  `@.claude/rules/shared/worktree-first.md`.
- **`main` shows a stale "In Progress" column.** Board transitions are committed on the task's own
  branch and only reach `main` when that branch's PR merges. The merged board records *completed*
  work; live state is derived from open PRs. See `@.claude/rules/shared/board-in-pr.md`.
