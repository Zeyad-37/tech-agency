---
name: dispatch
description: "Dispatch a task to an agent for parallel execution. Dispatched agents run in the cloud by default — each gets its own remote environment, branch, and PR. Falls back to a local git worktree, with a warning, when remote execution is unavailable. Use when you want to run multiple tasks simultaneously without agents conflicting. Triggers: 'dispatch', 'run in parallel', 'parallel task', 'worktree', 'dispatch @Agent', 'run these tasks at the same time', 'do these in parallel'."
---

# Dispatch — Parallel Task Execution in the Cloud

This skill runs any task in an isolated environment so multiple agents can work simultaneously without stepping on each other's files. Each dispatched task gets its own branch and merges back via PR.

**Dispatched work runs in the cloud.** Each agent is spawned with the `Agent` tool's `isolation: "remote"`, which launches it in a remote cloud environment with its own clone of the repository. Nothing is created on the local machine — no worktree, no branch, no build output. The local session stays free while dispatched work runs.

**Local worktrees are the fallback, not the default.** Remote execution is a gated capability: it may be unavailable for an account or an environment. When it is, this skill says so loudly and then creates local worktrees exactly as it used to, so a dispatch never hard-fails. See Step 0.

> **CRITICAL — Isolation Rule (both modes):**
> A dispatched agent works in exactly one place and never reaches outside it.
> - **Cloud mode:** the agent's own remote environment. It must verify it is on its own branch, cut from `origin/{BASE}`, before writing anything.
> - **Local mode:** its assigned worktree. It MUST `cd` there as the very first command, and verify with `pwd` and `git branch --show-current`. Agents must NEVER operate in the main working directory or another agent's worktree.

## How It Works

```
/dispatch @Kai implement login screen
/dispatch @Sentinel set up monitoring dashboards
/dispatch @Link refactor the network module
/dispatch --base epic/US-100-checkout @Kai implement checkout summary screen
/dispatch --local @Kai implement login screen        ← force the local-worktree path

→ Each runs in its own cloud environment, own branch, own PR
→ No file conflicts between agents, and nothing lands on the local machine
→ Branches off (and PRs back into) the resolved base — main by default,
  an epic integration branch when working inside an epic
```

## Step 0: Resolve the Execution Mode

Decide **cloud** or **local** once per dispatch run, before parsing anything else.

1. **Cloud is the default.** Every dispatched agent is spawned with `isolation: "remote"`.
2. **`--local` forces local mode.** If the user passes `--local` (or says "run this locally", "don't use the cloud"), skip the cloud path entirely and use the worktree mechanics in Step 2b. State that you are honouring an explicit local request.
3. **Fall back on unavailability.** Remote execution is gated. If the first remote spawn is refused — the capability is not enabled for this account, no cloud environment is configured, or the tool reports remote isolation unavailable — do **not** silently retry or abandon the dispatch. Warn, then fall back:

   ```
   ⚠️  Cloud execution unavailable — {reason reported by the tool}.
       Falling back to LOCAL git worktrees for this dispatch.
       Work will run on this machine and create worktrees under ../{repo}-worktrees/.
       To dispatch to the cloud, enable a cloud environment for this account
       (see the plugin README § Use in Cloud Sessions).
   ```

   Then run Step 2b and Step 3b for every task in this dispatch. Do not mix modes within one dispatch run — a half-cloud, half-local batch is confusing to track and makes the conflict rules in "Conflict Prevention" harder to reason about.

Record the resolved mode in the dispatch tracker so the user can see at a glance where their work is running.

## Step 1: Parse the Task

Extract from the user's request:

- **Agent**: Which agent should own this? (e.g., `@Kai`, `@Sentinel`, `@Link`)
- **Task description**: What should the agent do?
- **Branch type**: Determine the prefix based on the work:
  - Feature work → `{STORY-ID}/{short-description}`
  - Tech task → `tech/{short-description}`
  - Dependency upgrade → `deps/{short-description}`
  - Hotfix → `hotfix/{version}/{short-description}`

If the user dispatches multiple tasks at once, parse each one separately.

## Step 1b: Resolve the Base Branch (Branch-Off = Branch-Into)

The base branch is both where the task branches **off from** and where its PR merges **into**. They are always the same branch — a branch cut from an integration branch must PR back into that integration branch, never straight to `main`. Resolve it per task, in this order:

1. **Explicit override** — the user passed `--base <branch>` or said it in words ("branch off the epic branch", "cut this from `epic/US-100-checkout`"). Use exactly what they named. Verify it exists on the remote (`git ls-remote --heads origin <branch>`); if it doesn't, stop and ask rather than guessing.
2. **Epic integration branch** — the task belongs to an epic that has an integration branch. Convention: `epic/{EPIC-ID}-{slug}` (e.g., `epic/US-100-checkout`). Detect by (a) the board task referencing an epic, or (b) a matching `origin/epic/*` branch existing. When detection is inferred rather than user-stated, **confirm with the user before dispatching**: "This task looks like part of epic US-100 — branch off `epic/US-100-checkout` instead of `main`?"
3. **Hotfix** — branch from the release tag `v{X.Y.Z}` instead of a branch (per `worktree-first.md`). The PR base follows the hotfix process (merge into both the release branch and `main`).
4. **Default** — `origin/main`.

Set `BASE` once per task and carry it through the environment setup, the agent prompt, and the PR:

```bash
BASE="main"                    # or "epic/US-100-checkout", or "v1.2.0" for a hotfix
case "$BASE" in
  v*) git ls-remote --tags  origin "$BASE" | grep -q . || { echo "Base tag $BASE not on remote"; exit 1; } ;;
  *)  git ls-remote --heads origin "$BASE" | grep -q . || { echo "Base branch $BASE not on remote"; exit 1; } ;;
esac
```

Different tasks in one multi-dispatch may have different bases (e.g., two epic stories off `epic/US-100-checkout`, one tech task off `main`). Resolve each independently.

**In cloud mode this check is load-bearing, not a formality.** A remote environment clones from the remote — it has no access to this machine. A base that exists only locally produces an agent that cannot start.

## Step 2a: Cloud Pre-Flight (default mode)

Nothing is created locally in cloud mode. What has to be true instead is that **everything the dispatched agents need is already on the remote**, because that is all their environments can see.

```bash
MAIN_REPO="$(git rev-parse --show-toplevel)"

# 1. The base must exist on the remote (Step 1b already verified this).
git -C "$MAIN_REPO" fetch origin "$BASE"

# 2. Nothing the agents depend on may be sitting unpushed on this machine.
#    Local commits and uncommitted edits are invisible to a cloud environment.
git -C "$MAIN_REPO" status --porcelain
git -C "$MAIN_REPO" log --oneline "origin/${BASE}..HEAD" 2>/dev/null
```

If either command reports anything the dispatched tasks depend on — a spec, a board task, a shared module the agents will build against — **stop and land it on `origin/$BASE` first**. Dispatching over unpushed work produces agents whose prompts reference files that do not exist in their clone. (This is the same failure `/dispatch-task` Phase 1 Step 5 guards against; in cloud mode it applies to plain `/dispatch` too.)

Uncommitted local work that is unrelated to the dispatched tasks is fine to leave alone — say so rather than demanding a clean tree.

Then confirm the target environment:

- **Repository access.** The cloud environment needs a clone of this repository and credentials to push and open PRs, since every dispatched agent ends with `/create-pr`.
- **Plugin availability.** The shared rules in `.claude/rules/shared/` are committed in the repo and load in any cloud session. The **language coding standards do not** — they live in the plugin, and a cloud environment that has never installed tech-agency has `CLAUDE_PLUGIN_ROOT` unset (`@.claude/rules/shared/rules-delivery.md` § 5). The agent preamble below instructs the agent to stop and report rather than write code without its standard. If that happens repeatedly, fix it once at the environment level — see the plugin README § "Use in Cloud Sessions" § 3a (cloud environment setup script).
- **Board backend.** On `github`, board transitions are `gh` API writes and need an authenticated `gh` in the cloud environment. On `markdown`, they are commits on the agent's own branch and need nothing extra.

## Step 2b: Local Worktree Setup (fallback mode only)

Run this **only** when Step 0 resolved to local mode. The orchestrator creates ALL worktrees from the main working directory BEFORE handing off to any agent.

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

## Step 3a: Hand Off to Each Cloud Agent (default mode)

For EACH dispatched task, spawn a separate agent with the `Agent` tool using **`isolation: "remote"`**. Remote agents always run in the background — you will be notified as each completes. Do not pass `run_in_background: false`.

**Spawn every agent in a single message with multiple tool calls** so they run concurrently. Do NOT spawn them sequentially.

Include this **exact preamble** at the top of each task prompt:

```
## Mandatory Setup — Run FIRST before any other work

You are running in a cloud environment with your own clone of this repository.
No other agent shares it. Create your branch before writing anything.

git fetch origin [BASE]
git switch --no-track -c [BRANCH_NAME] origin/[BASE]

# Verify:
git branch --show-current
# Expected: [BRANCH_NAME]

git log --oneline -1
# Expected: the tip of origin/[BASE]

# If either check fails, STOP and report the error. Do NOT proceed on the wrong branch.
# `--no-track` is mandatory: a tracking branch can push to [BASE] itself.

---

## Your Task

@[Agent] — You are working in your own cloud environment.

Task: [task description]
Branch: [branch-name]
Base branch: [BASE] — your branch was cut from origin/[BASE] and its PR MUST target [BASE]

RULES:
1. You are on [BRANCH_NAME], cut from origin/[BASE] (verified above). Everything you need
   is on that base — this environment cannot see the dispatching machine.
2. FIRST COMMIT: run `/update-board [TASK-ID] → In Progress` and commit it on this branch —
   every board transition ships inside this task's PR, never separately
   (see .claude/rules/shared/board-in-pr.md)
3. Read the coding standard for this task's stack before writing code. It is NOT preloaded —
   it lives in the plugin and is read on demand:
     ${CLAUDE_PLUGIN_ROOT}/rules/mobile/android/compose-coding-standards.md    (Android / Compose)
     ${CLAUDE_PLUGIN_ROOT}/rules/mobile/ios/swiftui-coding-standards.md        (iOS / SwiftUI)
     ${CLAUDE_PLUGIN_ROOT}/rules/mobile/shared/kmp-coding-standards.md         (KMP shared)
     ${CLAUDE_PLUGIN_ROOT}/rules/backend/kotlin/ktor-server-coding-standards.md (Ktor)
     ${CLAUDE_PLUGIN_ROOT}/rules/web/react-coding-standards.md                 (React / Next.js)
     ${CLAUDE_PLUGIN_ROOT}/rules/backend/nodejs/node-coding-standards.md       (Node / Fastify)
     ${CLAUDE_PLUGIN_ROOT}/rules/backend/python/python-coding-standards.md     (Python / FastAPI)
     ${CLAUDE_PLUGIN_ROOT}/rules/backend/jvm/jvm-coding-standards.md           (JVM / Spring Boot)
   If CLAUDE_PLUGIN_ROOT is unset, read the same path under .claude/rules/.
   If NEITHER resolves — which is what a cloud environment without the plugin installed looks
   like — STOP and report it as a blocker. Do NOT write the code from generic knowledge
   (.claude/rules/shared/rules-delivery.md § 5).
   The shared rules in .claude/rules/shared/ are committed in the repo and already loaded —
   do not re-read them.
4. Commit with the standard format: [STORY-ID] @AgentName: description
5. When done: commit all changes, run `/update-board [TASK-ID] → Review` (committed on this
   branch), then `/create-pr --base [BASE]`, and report back with the PR link
```

If the task maps to an existing skill (e.g., the user says `/dispatch /tech-task improve git hooks`), include the skill invocation in the task prompt but keep the mandatory setup preamble above it.

## Step 3b: Hand Off to Each Local Agent (fallback mode only)

Same as above, but the agent's first action is to `cd` into its worktree rather than to create a branch. Spawn one agent per task, in parallel — the orchestrator already created the worktree in Step 2b, so no `isolation` is needed.

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
6. Read the coding standard for this task's stack before writing code — same list and same
   stop-and-report rule as the cloud preamble in Step 3a.
7. Commit with the standard format: [STORY-ID] @AgentName: description
8. When done: commit all changes, run `/update-board [TASK-ID] → Review` (committed on this branch), then `/create-pr --base [BASE]` to prepare the PR summary, and report back
```

## Step 4: Agent Completes Work

Identical in both modes. Board transitions ride inside the task's own PR (see `@.claude/rules/shared/board-in-pr.md`): the agent already committed `→ In Progress` as its first commit, and commits `→ Review` here before the PR — so the board history merges with the change it describes, never as a board-only PR or a commit on `main`. If the task gets blocked mid-flight, `/update-board {TASK-ID} → Blocked` also commits on this branch.

When the agent finishes implementation, it should (still on its own branch, in its own environment):

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
#    Run /create-pr --base {BASE}
#    This prepares a standardized PR summary with:
#    - Task ID in the title: [{TASK-ID}] {description}
#    - Authoring agent and any participating agents in the body
#    - Summary, test plan, and review checklist
#    NOTE: Invoking /create-pr IS the push authorization — it pushes the branch
#          and opens the PR. See shared-standards.md § Push Policy.
```

## Step 5: Clean Up

**Cloud mode: nothing to clean up locally.** The remote environment is disposable and the local machine never held a worktree or a branch for this task. The branch exists only on the remote once `/create-pr` pushes it, and is deleted by the normal post-merge branch cleanup.

**Local mode:** worktree cleanup is automatic — there is no separate cleanup command. The next time `/create-pr` runs in this repo, its Step 6 sweep enumerates every worktree, checks each branch against `gh pr list --state merged`, and removes the worktree + deletes the branch for any that are already merged. The worktree stays put until the PR is actually merged, so review feedback can still be addressed in place.

If you need to abandon a local dispatch before it merges (e.g., failed task, wrong approach), clean up manually from the main repo:

```bash
cd "$MAIN_REPO"
git worktree remove "$WORKTREE_DIR"          # add --force if the worktree has uncommitted work
git branch -D "$BRANCH"                       # -D since the branch isn't merged
git worktree prune                            # if the directory was already gone
```

To abandon a cloud dispatch, stop the remote agent and delete its remote branch if it got as far as pushing one.

## Tracking Active Dispatches

When multiple tasks are dispatched, maintain a dispatch tracker in the conversation. **Always name the mode** so the user knows where their work is running.

```
## Active Dispatches — mode: CLOUD
| # | Agent | Branch | Base | Where | Status | PR |
|---|-------|--------|------|-------|--------|-----|
| 1 | @Kai | US-042/login-screen | epic/US-040-auth | cloud (remote agent) | In Progress | — |
| 2 | @Sentinel | tech/monitoring | main | cloud (remote agent) | PR Created | #47 |
```

In local fallback mode, use absolute worktree paths so there is no ambiguity about which directory each agent is in:

```
## Active Dispatches — mode: LOCAL (cloud unavailable: {reason})
| # | Agent | Branch | Base | Where | Status | PR |
|---|-------|--------|------|-------|--------|-----|
| 1 | @Link | tech/refactor-network | main | /path/to/project-worktrees/tech-refactor-network | Done | #48 |
```

Report this table to the user after each dispatch operation so they have visibility into all parallel work.

## Multi-Dispatch (Batch Mode)

When the user dispatches multiple tasks at once:

```
/dispatch
  @Kai implement login screen
  @Sentinel set up monitoring
  @Nova build the dashboard page
```

**Cloud mode (default):** there is no per-task setup phase. Run the Step 2a pre-flight once for the whole batch, then spawn all three agents with `isolation: "remote"` in a single message with three tool calls. Each gets its own branch name and base in its prompt.

**Local fallback — Phase 1, create all worktrees (orchestrator, sequential):**

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

**Local fallback — Phase 2, dispatch all agents (parallel):**

Spawn all agent invocations simultaneously. Each agent gets its own worktree path and branch in the prompt. Do NOT wait for agent #1 to finish before spawning agent #2.

## Conflict Prevention Rules

1. **One agent per environment** — never assign two agents to the same cloud environment or the same worktree
2. **No cross-environment file access** — in local mode this is the most common source of bugs: an agent that doesn't `cd` into its worktree will operate in the main repo or the previous agent's worktree. Cloud mode removes this failure entirely, because each agent's clone is unreachable from any other
3. **Everything must be on the remote before dispatching in cloud mode** — a cloud environment clones from `origin`; local commits and uncommitted edits do not exist as far as it is concerned (Step 2a)
4. **Shared dependencies** — if two tasks touch the same files (e.g., shared module, build config), flag this to the user before dispatching. Suggest sequencing them instead of parallelizing. This is true in both modes: isolation prevents file collisions during the work, not merge conflicts afterwards
5. **Board updates** — each agent moves its own task through `board.move_task()` (`@.claude/rules/shared/board-adapter.md`). On `github` that is an API write, so parallel agents never contend. On `markdown` it edits `board-context.md` in the agent's own environment and commits on its own task branch, so the board update merges with that agent's PR. There is no central @Atlas writer, and no board-only PR (see `@.claude/rules/shared/board-in-pr.md`). Parallel branches editing the board will conflict on the second merge — resolve by keeping every task movement from both sides
6. **Verify location before every git operation** — in local mode, run `pwd` and `git branch --show-current`; in cloud mode, `git branch --show-current` is enough

## When NOT to Use Dispatch

- **Sequential dependencies** — if task B depends on task A's output, don't dispatch in parallel. Use normal skill invocation
- **Same-file changes** — if two tasks will modify the same files, they'll create merge conflicts. Sequence them instead
- **Trivial tasks** — one-liner fixes don't need dispatch overhead. Just do them on the branch directly
- **Planning-only work** — PRDs, BRDs, RFCs, retros don't produce code changes. No dispatch needed
- **Work that depends on unpushed local state** — in cloud mode the agent cannot see it. Land it on the base first, or dispatch with `--local`
- **Work that needs host-machine resources** — a physical device, a local emulator, host-only credentials, or a gitignored local config the cloud environment has no copy of. Use `--local` and say why

## Error Handling

If a dispatched task fails:

1. The agent reports the failure and what went wrong
2. **Cloud mode:** the remote environment holds the state. Inspect the agent's report and the branch it pushed, if any. Re-dispatch with a corrected prompt rather than trying to resume a failed remote run
3. **Local mode:** the worktree is preserved (not cleaned up) so you can inspect the state. Options: fix and retry in the same worktree, or abandon and clean up:
   ```bash
   cd "$MAIN_REPO"  # always clean up from the main repo
   git worktree remove --force "$WORKTREE_DIR"
   git branch -D "$BRANCH"
   ```

If the **remote spawn itself** fails — as opposed to the task failing inside it — that is the Step 0 fallback path, not an error to report and stop on. Warn, switch the whole dispatch to local mode, and continue.

## Troubleshooting: Agent Working in Wrong Place

**Cloud mode — agent is on the wrong branch:**

1. Stop immediately — do not commit
2. Run `git branch --show-current` and `git log --oneline -1` to confirm where it is
3. `git switch --no-track -c {BRANCH_NAME} origin/{BASE}` to get onto the correct branch
4. If files were modified on the wrong branch, revert them there first: `git checkout -- .`

**Local mode — agent is in the main repo or another agent's worktree:**

1. **Stop immediately** — do not commit or modify any more files
2. Run `pwd` and `git branch --show-current` to confirm the current location
3. `cd` to the correct worktree (check the dispatch tracker for the absolute path)
4. Verify with `pwd` and `git branch --show-current` again
5. If files were modified in the wrong directory, revert them: `git checkout -- .` in that directory
6. Resume work in the correct worktree
