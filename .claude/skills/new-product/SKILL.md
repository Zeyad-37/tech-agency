---
name: new-product
description: "Plan a brand new product from scratch, running the full discovery chain: Morgan (PRD) → Diana (BRD) → Sage (ADR + system design) → Atlas (board setup). Use when the user says 'new product', 'build me an app', 'I want to create', 'start a new project', or describes a product idea that does not exist yet. NOT for starting the working day on an existing product — that is /kick-off — and not for adding a feature to an existing product, which is /new-feature."
---

# New Product Kickoff

This skill orchestrates the full planning chain for a new product: Morgan → Diana → Sage → Atlas.

## Step 1: Gather Product Vision

Before invoking Morgan, collect these from the user (ask if not provided):

- **What** is the product? (1-2 sentence description)
- **Who** is it for? (target audience/personas)
- **Core capabilities** (3-5 must-have features)
- **Target platforms** (iOS, Android, Web, all via KMP?)
- **Any constraints?** (timeline, budget, compliance, existing systems)

## Step 2: Morgan — Write PRD

Invoke the `morgan-product-owner` agent:

```
Write a PRD for [product description].
Target audience: [who].
Core capabilities: [list].
Target platforms: [platforms].
Constraints: [any].
```

Save the PRD to `docs/artifacts/prd/{Task-Id}-PRD-{Title}.md` per `@.claude/rules/shared/handoff-protocol.md`. If no task ID exists yet, use the product slug and note that @Atlas assigns an ID at board setup.

**STOP: Present the PRD to @Zeyad for approval before continuing.**

## Step 3: Diana — Write BRD

After PRD approval, invoke the `diana-business-analyst` agent:

```
Write a BRD based on the approved PRD at docs/artifacts/prd/{Task-Id}-PRD-{Title}.md.
Break down all features into user stories with Given/When/Then acceptance criteria.
Include NFRs, data dictionary, and risk assessment.
```

Save the BRD to `docs/artifacts/brd/{Task-Id}-BRD-{Title}.md`.

**STOP: Present the BRD to @Zeyad for approval before continuing.**

## Step 4: Sage — Architecture

After BRD approval, invoke the `sage-solutions-architect` agent:

```
Design the system architecture based on:
- PRD: docs/artifacts/prd/{Task-Id}-PRD-{Title}.md
- BRD: docs/artifacts/brd/{Task-Id}-BRD-{Title}.md
Target platforms: [platforms].
Produce ADRs for key technical decisions and a high-level system design.
```

Save each ADR to `docs/artifacts/adr/{Task-Id}-ADR-{Title}.md` and the system design to `docs/artifacts/adr/{Task-Id}-ADR-System Design.md`.

There is no `docs/by-type/` cross-reference tree — the type folder *is* the index.

**STOP: Present architecture docs to @Zeyad for approval before continuing.**

## Step 5: Atlas — Set Up the Board

After architecture approval, invoke the `atlas-orchestrator` agent:

```
Set up the Kanban board for {product-name}.
Break down the BRD user stories into tasks via board.create_task().
Assign to agents based on the system design.
Reference: docs/artifacts/brd/{Task-Id}-BRD-{Title}.md and docs/artifacts/adr/{Task-Id}-ADR-System Design.md
New tasks land in Backlog: | Task ID | Priority | Description | Requested By |
```

This populates the board and the team is ready to start pulling work.

The board edit ships with the planning documents that produced it: commit `board-context.md` on the same branch as the PRD, BRD and ADRs, and merge them in one PR (`@.claude/rules/shared/board-in-pr.md`). Do not leave it uncommitted — the first agent to pick up a task works in a worktree cut from `origin/main` and would see neither the board tasks nor the docs.

## After Kickoff

Remind the user:
- Run `/daily-sync` regularly to track progress
- Run `/replenish` weekly to keep the Ready column full
- Run `/kick-off` to start each working day (sync → replenish → pick up next task)
- Each handoff document needs approval before the next agent acts
