---
name: kick-off
description: "Start the day's work in one shot — runs daily sync, replenishes the board if needed, then picks up the next task. Use when the user says 'kick off', 'start work', 'start the day', 'morning sync', 'begin work', 'let's go', or 'what's next'."
---

# Kick Off Work

This skill chains three workflows into a single command: daily sync, conditional replenishment, and task pickup. It gets an agent from zero to productive in one step.

## Step 1: Daily Sync (as Atlas)

Read `board-context.md` and produce a compact status report:

```bash
cat board-context.md
git log --oneline -20
```

Produce this summary (abbreviated version of the full `/daily-sync` output):

```markdown
## Board Snapshot — [date]

| Column | Count | Details |
|--------|-------|---------|
| In Progress | [n] | [agent: task, ...] |
| Review | [n] | |
| Blocked | [n] | [task: reason, ...] |
| Done (since last sync) | [n] | |

**WIP violations:** [list any agent with >2 WIP items, or "None"]
**Stale tasks (>5 days):** [list, or "None"]
**Blockers:** [list, or "None"]
```

Update `board-context.md` with any status changes discovered. Each correction commits on the branch of the task it describes — never centrally and never on `main` (see `@.claude/rules/shared/board-in-pr.md`). A correction with no branch to ride with goes in the report for the owning agent to carry.

Note that the merged board under-reports in-flight work: In Progress and Blocked entries live on unmerged branches. Cross-check against open PRs and branches — see `board-in-pr.md` § "What the Committed Board Records".

## Step 2: Evaluate Board Health

Check the Ready column:

```
Ready column count: [n]
Active agents: [n]
Target: 2-3 items per active agent in Ready
```

**Decision gate:**

- If Ready column has **fewer than 2 items per active agent** → proceed to Step 3 (replenish)
- If Ready column is **healthy** (2+ items per active agent) → skip to Step 4 (pick up task)

Report the decision:

```markdown
**Ready column:** [n] items for [n] active agents → [Replenishing / Healthy, skipping replenish]
```

## Step 3: Quick Replenish (only if needed)

Run an abbreviated replenishment — enough to fill the Ready column without the full weekly analysis:

1. Read the backlog section of `board-context.md`
2. Check `docs/tech-debt/backlog.md` if it exists
3. Pull the top items into Ready using this priority:
   - P0/P1 bugs → always first
   - Items that unblock In Progress work → next
   - Highest RICE score items → fill remaining slots
   - 1 tech debt item per 5 regular items (15-20% allocation)

Produce:

```markdown
## Quick Replenish

| Task ID | Description | Priority | Assigned To | Rationale |
|---------|-------------|----------|-------------|-----------|
| T-XXX   | ...         | P[n]     | @Agent      | [why]     |
| ...     | ...         | ...      | ...         | ...       |

Moved [n] items to Ready. Tech debt: [n] items ([%] of total).
```

Save this quick-replenish report to `docs/artifacts/replenishment/{YYYY-MM-DD}-Replenishment.md` (create the folder if absent), then update `board-context.md` to move selected items to Ready.

The report is the carrier for the board edit — same rule as `/replenish` (see `@.claude/rules/shared/board-in-pr.md`). Commit both together on one branch:

```bash
git add docs/artifacts/replenishment/{YYYY-MM-DD}-Replenishment.md board-context.md
git commit -m "[{TASK-ID}] @Atlas: Replenish board — {n} items to Ready"
```

Never leave the board edit uncommitted for a later PR to carry: the agent picking up one of these tasks works in a worktree cut from `origin/main` and would see neither the pending edit nor the Ready tasks it created.

## Step 4: Pick Up Task

Now switch from Atlas to the invoking agent's role. Follow the full `/pick-up-task` workflow:

### 4a. Check WIP

If you already have 2 items in "In Progress":
- Report your current WIP
- Suggest finishing the closest-to-complete task
- Stop here — do not pick up a new task

### 4b. Select Task

From the "Ready" column, pick using this priority:

1. **P0/P1 bugs or incidents** — always first
2. **Tasks explicitly assigned to you**
3. **Tasks matching your domain** (see domain table in `/pick-up-task`)
4. **Highest priority among remaining**
5. **Oldest task first** (tiebreaker)

If no matching tasks exist:
- Report that no tasks match your domain
- Suggest running `/replenish` with a full review or reassigning tasks
- Stop here

### 4c. Validate

Before pulling:
1. Acceptance criteria exist → if missing, request from @Diana/@Morgan
2. Dependencies are met → if blocked, skip to next task
3. Required artifacts exist → if missing, request via @Atlas

### 4d. Pull and Context Load

1. Move the task to "In Progress" in `board-context.md` with your name and today's date
2. Read feature docs: PRD, BRD, ADR, RFC, design specs in `docs/artifacts/` (grep by Task ID)
3. Load relevant coding standards for your platform
4. Check recent git activity: `git log --oneline --since="3 days ago" -- {affected-dirs}`
5. Check for parallel work on the same code area

### 4e. Plan and Present

Produce a work plan for the user's approval:

```markdown
## Kick-Off Complete

### Board Status
[Summary from Step 1]

### Replenishment
[Summary from Step 3, or "Skipped — Ready column healthy"]

### Starting Task: T-XXX — {description}

**Scope:**
- What I will change
- What I will NOT change

**Approach:**
- Step-by-step plan
- Key decisions (referencing ADRs/RFCs)

**Test Plan:**
- Tests I will write/update
- How I verify acceptance criteria

**Estimated Effort:** Small / Medium / Large
```

Wait for user confirmation before writing any code.

## Step 5: Begin Work

Once confirmed:

1. Create feature branch from the latest `origin/main` (never from the current checkout): `git fetch origin main && git checkout -b {story-id}/{short-description} origin/main`
2. Implement following coding standards and ADR decisions
3. Write tests per the test plan
4. Commit after each logical change: `[STORY-ID] @{YourAgent}: description`
5. When done, run `/update-board {TASK-ID} → Review` to move the task and commit the board change on this branch
6. Run `/create-pr` to prepare a standardized pull request with the task ID in the title and participating agents in the body (the PR will NOT be pushed until @Zeyad approves)
7. Create a handoff and tag the reviewer
