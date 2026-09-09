---
name: onboard-agent
description: "Rapidly onboard an agent onto an existing feature or codebase area. Loads all relevant context — PRD, BRD, ADR, RFC, recent commits, board state, open PRs, team contacts — and produces a briefing document. Use when the user says 'onboard', 'catch me up', 'get up to speed', 'context on this feature', 'bring me up to date', or 'what do I need to know'."
---

# Onboard Agent to Feature

This skill fast-tracks an agent into a feature or codebase area they haven't worked on before. Instead of the agent piecing together context from scattered docs and git history, this command builds a comprehensive briefing in one shot.

## Step 1: Identify the Scope

Ask the user (or extract from context):

- **Feature name**: Which feature or area? (e.g., "user-auth", "push-notifications", "checkout")
- **Your agent role**: Which agent are you? (e.g., @Kai, @Nova, @Shield)
- **Reason for onboarding**: New to the team? Picking up someone else's work? Cross-functional review?

If the feature name maps to a directory in `docs/`, use that. Otherwise, ask the user to clarify.

## Step 2: Load Feature Documentation

Read all available documentation for the feature:

Documents are filed by type per `@.claude/rules/shared/handoff-protocol.md`, as `docs/{doc-type}/{Task-Id}-{Doc Type}-Title.md`. Find every document for this feature in one pass, then read each hit:

```bash
grep -ril "{TASK-ID}\|{feature-name}" \
  docs/artifacts/prd/ docs/artifacts/brd/ docs/artifacts/adr/ docs/artifacts/rfc/ docs/artifacts/design-spec/ \
  docs/artifacts/api-contract/ docs/artifacts/incident-notes/ docs/artifacts/post-mortem/ 2>/dev/null \
  || echo "No documents found for this feature"
```

Summarize each document found:

```markdown
### Feature Documentation

| Document | Status | Key Points |
|----------|--------|------------|
| PRD | [Found/Missing] | [1-2 sentence summary of what the feature does and why] |
| BRD | [Found/Missing] | [Key user stories and acceptance criteria] |
| ADR(s) | [n found] | [Key architectural decisions — especially constraints] |
| RFC | [Found/Missing] | [Implementation approach and open questions] |
| Design specs | [Found/Missing] | [UI/UX notes] |
| Incidents | [n found] | [Past issues and their resolutions] |
| Bug reports | [n found] | [Known issues] |
```

## Step 3: Understand the Architecture

Read relevant ADRs and identify how this feature fits into the system:

```bash
# Architecture-level docs for this feature
grep -ril "{TASK-ID}\|{feature-name}" docs/artifacts/adr/ docs/artifacts/rfc/ 2>/dev/null

# Check which modules this feature touches
grep -rl "{feature-name}" --include="*.kt" --include="*.swift" --include="*.ts" --include="*.tsx" --include="*.py" src/ | head -20
```

Produce:

```markdown
### Architecture Overview

**Modules involved:**
- [List each module/directory this feature touches]

**Key decisions (from ADRs):**
- [Decision 1 — what was chosen and why]
- [Decision 2 — what was chosen and why]

**Constraints:**
- [Things you MUST follow — tech choices, patterns, APIs]
- [Things you MUST NOT do — anti-patterns, deprecated approaches]

**Dependencies:**
- Upstream: [What this feature depends on]
- Downstream: [What depends on this feature]
```

## Step 4: Review Recent History

```bash
# Recent commits on this feature
git log --oneline --all --since="2 weeks ago" -- {affected-dirs-and-files} | head -30

# Open branches related to this feature
git branch -a | grep -i "{feature-name}" | head -10

# Recent activity by agent
git log --oneline --all --since="1 month ago" --grep="@" -- {affected-dirs-and-files} | head -20
```

Produce:

```markdown
### Recent Activity

**Last 2 weeks:**
- [Commit summary grouped by agent — who did what]

**Open branches:**
- [List active branches related to this feature]

**Key recent changes:**
- [Any significant refactors, migrations, or breaking changes]
```

## Step 5: Check Board State

Read the board through the adapter, not the file (`@.claude/rules/shared/board-adapter.md` rule 2) — check `board_backend` in `.claude/settings.json` (absent → `markdown`), then run `board.search("{feature-name}")`, falling back to `board.read_all()` if the backend has no search.

Find all tasks related to this feature:

```markdown
### Board State for {feature-name}

| Column | Task ID | Description | Assigned To |
|--------|---------|-------------|-------------|
| In Progress | T-XXX | ... | @Agent |
| Ready | T-YYY | ... | unassigned |
| Blocked | T-ZZZ | ... | @Agent — blocked by: [reason] |
| Done (recent) | T-AAA | ... | @Agent |

**Active blockers:** [list or "None"]
**Parallel work happening:** [who else is working on related code]
```

## Step 6: Identify Contacts

Based on git blame and board assignments, identify who to coordinate with:

```bash
# Who has been working on this code
git log --format='%an' --since="1 month ago" -- {affected-dirs} | sort | uniq -c | sort -rn | head -5
```

```markdown
### Key Contacts

| Agent | Role | Recent Activity |
|-------|------|-----------------|
| @[Agent] | [role] | [what they've been doing on this feature] |
| @[Agent] | [role] | [what they've been doing on this feature] |

**Go-to for questions about:**
- Architecture/decisions → @Sage
- Requirements/acceptance criteria → @Diana / @Morgan
- Code in [module] → @[most active agent]
- Security concerns → @Shield
```

## Step 7: Load Platform Context

Based on the agent's role, load the relevant coding standards:

| Agent | Load These Standards |
|-------|---------------------|
| @Kai | compose-coding-standards.md + kmp-coding-standards.md |
| @Swift | swiftui-coding-standards.md + kmp-coding-standards.md |
| @Link | kmp-coding-standards.md + ktor-server-coding-standards.md |
| @Nova | react-coding-standards.md |
| @Flux | node-coding-standards.md |
| @Pyra | python-coding-standards.md |
| @Forge | jvm-coding-standards.md |
| @Shield | All standards (for security review) |
| @Apex | All standards (for QA review) |

Summarize the key patterns the agent needs to follow for this feature:

```markdown
### Coding Patterns for This Feature

- **State management**: [MVI / Zustand / etc. — what pattern is used]
- **Data flow**: [Repository → UseCase → ViewModel → UI]
- **Networking**: [Ktor / Retrofit / React Query — what's used]
- **Testing**: [Framework, coverage targets, test patterns]
- **Key conventions**: [Any feature-specific patterns beyond the standard]
```

## Step 8: Produce Onboarding Briefing

Compile everything into a single briefing document:

```markdown
# Onboarding Briefing: {feature-name}

**Agent:** @[YourAgent]
**Date:** YYYY-MM-DD
**Prepared for:** [reason — new to feature / picking up work / cross-functional review]

## TL;DR

[3-5 sentences: what the feature is, where it stands, what the agent needs to do next]

## Feature Overview
[From Step 2 — what the feature does, key user stories, success metrics]

## Architecture
[From Step 3 — modules, decisions, constraints, dependencies]

## Current State
[From Steps 4 & 5 — recent activity, board state, blockers, who's doing what]

## Your Domain
[From Step 7 — coding patterns, standards, key files you'll be working in]

## Key Contacts
[From Step 6 — who to talk to about what]

## Recommended First Steps

1. [Read specific file/doc]
2. [Review specific PR or recent commit]
3. [Pick up specific task from the board]
4. [Coordinate with specific agent about specific thing]

## Gotchas & Watch-Outs

- [Any known quirks, workarounds, or landmines in this area]
- [Past incidents to be aware of]
- [Decisions that might seem wrong but are intentional (with ADR refs)]
```

Save the briefing to `docs/artifacts/onboarding/{Task-Id}-Onboarding-{Agent}-{Date}.md` (create the folder if it does not exist), following the by-type convention in `@.claude/rules/shared/handoff-protocol.md`.

## Step 9: Announce

Notify @Atlas that the agent has been onboarded:

```markdown
@Atlas: @[Agent] has been onboarded to {feature-name}. Briefing saved to docs/artifacts/onboarding/{Task-Id}-Onboarding-{Agent}-{Date}.md. Ready to begin work.
```

If the agent should immediately pick up a task, suggest running `/pick-up-task` or `/kick-off` next.
