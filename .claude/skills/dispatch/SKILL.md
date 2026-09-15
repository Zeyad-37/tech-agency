---
name: dispatch
description: "Dispatch a task to an agent in an isolated git worktree for parallel execution. Use when you want to run multiple tasks simultaneously without agents conflicting. Triggers: 'dispatch', 'run in parallel', 'parallel task', 'worktree', 'dispatch @Agent', 'run these tasks at the same time', 'do these in parallel'."
---

# Dispatch — Parallel Task Execution via Git Worktrees

This skill wraps any task in an isolated git worktree so multiple agents can work simultaneously without stepping on each other's files. Each dispatched task gets its own branch, its own working directory, and merges back via PR.

> **CRITICAL — Directory Isolation Rule:**
> Every dispatched agent MUST `cd` into its assigned worktree as the very first command before doing anything else. The agent must verify it is in the correct directory by checking `pwd` and `git branch --show-current`. If the agent is not in its worktree, it must stop and `cd` there before proceeding. Agents must NEVER operate in the main working directory or another agent's worktree.

## How It Works

```
/dispatch @Kai implement login screen
/dispatch @Sentinel set up monitoring dashboards
/dispatch @Link refactor the network module
/dispatch --base epic/US-100-checkout @Kai implement checkout summary screen

→ Each runs in its own worktree, own branch, own PR
→ No file conflicts between agents
→ Branches off (and PRs back into) the resolved base — main by default,
  an epic integration branch when working inside an epic
```

## Step 1: Parse the Task

Extract from the user's request:

- **Agent**: Which agent should own this? (e.g., `@Kai`, `@Sentinel`, `@Link`)
- **Task description**: What should the agent do?
- **Branch type**: Determine the prefix based on the work:
  - Feature work → `{STORY-ID}/{short-description}`
  - Tech task → `tech/{short-description}`
  - Dependency upgrade → `deps/{short-description}`
  - Hotfix → `hotfix/{version}/{short-description}`

If the user dispatches multiple tasks at once, parse each one separately and create a worktree for each.

## Step 1b: Resolve the Base Branch (Branch-Off = Branch-Into)

The base branch is both where the worktree branches **off from** and where its PR merges **into**. They are always the same branch — a worktree cut from an integration branch must PR back into that integration branch, never straight to `main`. Resolve it per task, in this order:

1. **Explicit override** — the user passed `--base <branch>` or said it in words ("branch off the epic branch", "cut this from `epic/US-100-checkout`"). Use exactly what they named. Verify it exists on the remote (`git ls-remote --heads origin <branch>`); if it doesn't, stop and ask rather than guessing.
2. **Epic integration branch** — the task belongs to an epic that has an integration branch. Convention: `epic/{EPIC-ID}-{slug}` (e.g., `epic/US-100-checkout`). Detect by (a) the board task referencing an epic, or (b) a matching `origin/epic/*` branch existing. When detection is inferred rather than user-stated, **confirm with the user before creating worktrees**: "This task looks like part of epic US-100 — branch off `epic/US-100-checkout` instead of `main`?"
3. **Hotfix** — branch from the release tag `v{X.Y.Z}` instead of a branch (per `worktree-first.md`). The PR base follows the hotfix process (merge into both the release branch and `main`).
4. **Default** — `origin/main`.

Set `BASE` once per task and carry it through worktree creation, the agent prompt, and the PR:

```bash
BASE="main"                    # or "epic/US-100-checkout", or "v1.2.0" for a hotfix
case "$BASE" in
  v*) git ls-remote --tags  origin "$BASE" | grep -q . || { echo "Base tag $BASE not on remote"; exit 1; } ;;
  *)  git ls-remote --heads origin "$BASE" | grep -q . || { echo "Base branch $BASE not on remote"; exit 1; } ;;
esac
```

Different tasks in one multi-dispatch may have different bases (e.g., two epic stories off `epic/US-100-checkout`, one tech task off `main`). Resolve each independently.

## Step 2: Create the Worktrees (Orchestrator)

The orchestrator (Atlas or the dispatching agent) creates ALL worktrees from the main working directory BEFORE handing off to any agent. This ensures worktrees are ready and isolated.

```bash
# Save the main repo path — all worktree creation happens from here
MAIN_REPO="$(pwd)"

# Ensure we're on main and up to date
git checkout main
git pull --rebase

# For EACH task, create a worktree:
BRANCH="tech/improve-git-hooks"  # example — use the appropriate prefix
BASE="main"                      # from Step 1b — may be an epic integration branch
WORKTREE_DIR="${MAIN_REPO}/../$(basename "$MAIN_REPO")-worktrees/${BRANCH//\//-}"
# Always branch from the resolved base on the remote — never from whatever happens to be checked out.
git fetch origin "$BASE"
git worktree add --no-track -b "$BRANCH" "$WORKTREE_DIR" "origin/$BASE"
# Hotfix exception: branch from the release tag instead:
#   git worktree add --no-track -b "$BRANCH" "$WORKTREE_DIR" "v{X.Y.Z}"

# Copy local.properties (gitignored) into the worktree so Gradle can resolve
# sdk.dir, Android SDK paths, and any other host-machine config. Without this,
# the first build in a fresh worktree fails with "SDK location not found".
[ -f "${MAIN_REPO}/local.properties" ] && cp "${MAIN_REPO}/local.properties" "${WORKTREE_DIR}/local.properties"

# Repeat for additional tasks (each gets its own BRANCH and WORKTREE_DIR)
# ...

# Return to main when done creating all worktrees
git checkout main

# Verify all worktrees were created
git worktree list
```

**Worktree directory convention:**
```
your-project/                          ← main working directory (orchestrator stays here)
your-project-worktrees/
├── tech-improve-git-hooks/            ← worktree for tech/improve-git-hooks
├── US-042-login-screen/               ← worktree for US-042/login-screen
└── deps-kotlin-2.1/                   ← worktree for deps/kotlin-2.1
```

## Step 3: Hand Off to Each Agent

For EACH dispatched task, spawn a separate agent using the `Task` tool (Claude Code subagent). The critical requirement is that the agent's **first action** is to `cd` into its worktree and verify the directory.

When spawning the agent, include this **exact preamble** at the top of the task prompt:

```
## Mandatory Setup — Run FIRST before any other work

cd [WORKTREE_ABSOLUTE_PATH]

# Verify you are in the correct worktree:
pwd
# Expected: [WORKTREE_ABSOLUTE_PATH]

git branch --show-current
# Expected: [BRANCH_NAME]

# If EITHER check fails, STOP and report the error. Do NOT proceed in the wrong directory.

---

## Your Task

@[Agent] — You are working in an isolated worktree.

Task: [task description]
Branch: [branch-name]
Base branch: [BASE] — this branch was cut from origin/[BASE] and its PR MUST target [BASE]
Working directory: [WORKTREE_ABSOLUTE_PATH]

RULES:
1. You MUST already be in [WORKTREE_ABSOLUTE_PATH] (verified above)
2. ALL file reads, writes, and git operations happen in THIS directory only
3. Do NOT cd to any other directory (especially not the main repo)
4. Do NOT read or modify files outside this worktree
5. FIRST COMMIT: run `/update-board [TASK-ID] → In Progress` and commit it on this branch — every board transition ships inside this task's PR, never separately (see .claude/rules/shared/board-in-pr.md)
6. Read the coding standard for this task's stack before writing code. It is NOT preloaded — it lives in the plugin and is read on demand:
     ${CLAUDE_PLUGIN_ROOT}/rules/mobile/android/compose-coding-standards.md    (Android / Compose)
     ${CLAUDE_PLUGIN_ROOT}/rules/mobile/ios/swiftui-coding-standards.md        (iOS / SwiftUI)
     ${CLAUDE_PLUGIN_ROOT}/rules/mobile/shared/kmp-coding-standards.md         (KMP shared)
     ${CLAUDE_PLUGIN_ROOT}/rules/backend/kotlin/ktor-server-coding-standards.md (Ktor)
     ${CLAUDE_PLUGIN_ROOT}/rules/web/react-coding-standards.md                 (React / Next.js)
     ${CLAUDE_PLUGIN_ROOT}/rules/backend/nodejs/node-coding-standards.md       (Node / Fastify)
     ${CLAUDE_PLUGIN_ROOT}/rules/backend/python/python-coding-standards.md     (Python / FastAPI)
     ${CLAUDE_PLUGIN_ROOT}/rules/backend/jvm/jvm-coding-standards.md           (JVM / Spring Boot)
   If CLAUDE_PLUGIN_ROOT is unset, read the same path under .claude/rules/.
   The shared rules in .claude/rules/shared/ are already loaded — do not re-read them.
7. Commit with the standard format: [STORY-ID] @AgentName: description
8. When done: commit all changes, run `/update-board [TASK-ID] → Review` (committed on this branch), then `/create-pr --base [BASE]` to prepare the PR summary, and report back
```

If the task maps to an existing skill (e.g., the user says `/dispatch /tech-task improve git hooks`), include the skill invocation in the task prompt but keep the mandatory setup preamble above it.

**If spawning multiple agents, spawn them in parallel** — each agent gets its own `Task` invocation with its own worktree path. Do NOT spawn agents sequentially waiting for each to finish.

## Step 4: Agent Completes Work

Board transitions ride inside the task's own PR (see `@.claude/rules/shared/board-in-pr.md`): the agent already committed `→ In Progress` as its first commit (preamble rule 5), and commits `→ Review` here before the PR — so the board history merges with the change it describes, never as a board-only PR or a commit on `main`. If the task gets blocked mid-flight, `/update-board {TASK-ID} → Blocked` also commits on this branch.

When the agent finishes implementation, it should (still inside its worktree):

```bash
# Verify we're still in the right place
pwd
git branch --show-current

# 1. Stage and commit (agent does this as part of normal workflow)
git add -A
git commit -m "[STORY-ID] @AgentName: description"

# 2. Move the task to Review
#    Run /update-board {TASK-ID} → Review
#    On `github` this is an API write and is already live — nothing to commit.
#    On `markdown` /update-board stages and commits board-context.md itself so
#    the board change is included in the merge commit.

# 3. Prepare the PR using /create-pr
#    Run /create-pr
#    This prepares a standardized PR summary with:
#    - Task ID in the title: [{TASK-ID}] {description}
#    - Authoring agent and any participating agents in the body
#    - Summary, test plan, and review checklist
#    NOTE: Invoking /create-pr IS the push authorization — it pushes the branch
#          and opens the PR. See shared-standards.md § Push Policy.
```

## Step 5: Clean Up the Worktree (Automatic)

Worktree cleanup is automatic — there is no separate cleanup command. The next time `/create-pr` runs in this repo, its Step 6 sweep enumerates every worktree, checks each branch against `gh pr list --state merged`, and removes the worktree + deletes the branch for any that are already merged. The worktree stays put until the PR is actually merged, so review feedback can still be addressed in place.

If you need to abandon a dispatch before it merges (e.g., failed task, wrong approach), clean up manually from the main repo:

```bash
cd "$MAIN_REPO"
git worktree remove "$WORKTREE_DIR"          # add --force if the worktree has uncommitted work
git branch -D "$BRANCH"                       # -D since the branch isn't merged
git worktree prune                            # if the directory was already gone
```

## Tracking Active Dispatches

When multiple tasks are dispatched, maintain a dispatch tracker in the conversation:

```
## Active Dispatches
| # | Agent | Branch | Base | Worktree (absolute path) | Status | PR |
|---|-------|--------|------|--------------------------|--------|-----|
| 1 | @Kai | US-042/login-screen | epic/US-040-auth | /path/to/project-worktrees/US-042-login-screen | In Progress | — |
| 2 | @Sentinel | tech/monitoring | main | /path/to/project-worktrees/tech-monitoring | PR Created | #47 |
| 3 | @Link | tech/refactor-network | main | /path/to/project-worktrees/tech-refactor-network | Done | #48 |
```

Report this table to the user after each dispatch operation so they have visibility into all parallel work. **Use absolute paths** in the tracker so there's no ambiguity about which directory each agent is in.

## Multi-Dispatch (Batch Mode)

When the user dispatches multiple tasks at once:

```
/dispatch
  @Kai implement login screen
  @Sentinel set up monitoring
  @Nova build the dashboard page
```

**Phase 1 — Create all worktrees (orchestrator, sequential):**

```bash
MAIN_REPO="$(pwd)"
git checkout main && git pull --rebase

# Create all worktrees from the main repo — each branched from its resolved base
# (Step 1b). Bases can differ per task: here two epic stories branch off the
# epic integration branch and the tech task branches off main.
# "branch:base" pairs — plain arrays keep this portable to macOS's bash 3.2
# (declare -A needs bash 4+). Branch names contain "/", so colon is the delimiter:
# strip the base with ${pair##*:} and the branch with ${pair%:*}.
for pair in \
  "US-042/login-screen:epic/US-040-auth" \
  "tech/monitoring:main" \
  "US-043/dashboard:epic/US-040-auth"
do
  branch="${pair%:*}"
  base="${pair##*:}"
  WORKTREE_DIR="${MAIN_REPO}/../$(basename "$MAIN_REPO")-worktrees/${branch//\//-}"
  git fetch origin "$base"
  git worktree add --no-track -b "$branch" "$WORKTREE_DIR" "origin/$base"
  [ -f "${MAIN_REPO}/local.properties" ] && cp "${MAIN_REPO}/local.properties" "${WORKTREE_DIR}/local.properties"
done

# Return to main
git checkout main
git worktree list  # verify all 3 worktrees
```

**Phase 2 — Dispatch all agents (parallel):**

Spawn all agent `Task` invocations simultaneously. Each agent gets its own worktree path and branch in the prompt. Do NOT wait for agent #1 to finish before spawning agent #2.

## Conflict Prevention Rules

1. **One agent per worktree** — never assign two agents to the same worktree
2. **No cross-worktree file access** — agents must not read or write files outside their worktree. This is the most common source of bugs — an agent that doesn't `cd` into its worktree will operate in the main repo or the previous agent's worktree
3. **Shared dependencies** — if two tasks touch the same files (e.g., shared module, build config), flag this to the user before dispatching. Suggest sequencing them instead of parallelizing
4. **Board updates** — each agent moves its own task through `board.move_task()` (`@.claude/rules/shared/board-adapter.md`). On `github` that is an API write, so parallel agents never contend. On `markdown` it edits `board-context.md` inside the agent's own worktree and commits on its own task branch, so the board update merges with that agent's PR. There is no central @Atlas writer in the main checkout, and no board-only PR (see `@.claude/rules/shared/board-in-pr.md`). Parallel branches editing the board will conflict on the second merge — resolve by keeping every task movement from both sides
5. **Verify directory before every git operation** — if in doubt, run `pwd` and `git branch --show-current` to confirm you're in the right place

## When NOT to Use Dispatch

- **Sequential dependencies** — if task B depends on task A's output, don't dispatch in parallel. Use normal skill invocation
- **Same-file changes** — if two tasks will modify the same files, they'll create merge conflicts. Sequence them instead
- **Trivial tasks** — one-liner fixes don't need worktree overhead. Just do them on the branch directly
- **Planning-only work** — PRDs, BRDs, RFCs, retros don't produce code changes. No worktree needed

## Error Handling

If a dispatched task fails:

1. The agent reports the failure and what went wrong
2. The worktree is preserved (not cleaned up) so you can inspect the state
3. Options: fix and retry in the same worktree, or abandon and clean up:
   ```bash
   cd "$MAIN_REPO"  # always clean up from the main repo
   git worktree remove --force "$WORKTREE_DIR"
   git branch -D "$BRANCH"
   ```

## Troubleshooting: Agent Working in Wrong Directory

If an agent is operating in the main repo or another agent's worktree instead of its own:

1. **Stop immediately** — do not commit or modify any more files
2. Run `pwd` and `git branch --show-current` to confirm the current location
3. `cd` to the correct worktree (check the dispatch tracker for the absolute path)
4. Verify with `pwd` and `git branch --show-current` again
5. If files were modified in the wrong directory, revert them: `git checkout -- .` in that directory
6. Resume work in the correct worktree
