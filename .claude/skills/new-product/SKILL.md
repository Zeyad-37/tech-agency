---
name: new-product
description: "Kick off a brand new product from scratch. Starts with Morgan (PRD), then chains through Diana (BRD), Sage (ADR), and sets up the board. Use when the user says 'new product', 'build me an app', 'I want to create', 'start a new project', 'kick off', or describes a product idea from scratch."
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

Save the PRD to `docs/{product-name}/prd.md`.
Create the cross-reference at `docs/by-type/prd/{product-name}.md`.

**STOP: Present the PRD to @Zeyad for approval before continuing.**

## Step 3: Diana — Write BRD

After PRD approval, invoke the `diana-business-analyst` agent:

```
Write a BRD based on the approved PRD at docs/{product-name}/prd.md.
Break down all features into user stories with Given/When/Then acceptance criteria.
Include NFRs, data dictionary, and risk assessment.
```

Save the BRD to `docs/{product-name}/brd.md`.
Create the cross-reference at `docs/by-type/brd/{product-name}.md`.

**STOP: Present the BRD to @Zeyad for approval before continuing.**

## Step 4: Sage — Architecture

After BRD approval, invoke the `sage-solutions-architect` agent:

```
Design the system architecture based on:
- PRD: docs/{product-name}/prd.md
- BRD: docs/{product-name}/brd.md
Target platforms: [platforms].
Produce ADRs for key technical decisions and a high-level system design.
```

Save ADRs to `docs/{product-name}/adr-NNN-{title}.md`.
Save system design to `docs/{product-name}/system-design.md`.
Create cross-references in `docs/by-type/adr/` and `docs/by-type/system-design/`.

**STOP: Present architecture docs to @Zeyad for approval before continuing.**

## Step 5: Atlas — Set Up the Board

After architecture approval, invoke the `atlas-orchestrator` agent:

```
Set up the Kanban board for {product-name}.
Break down the BRD user stories into tasks.
Assign to agents based on the system design.
Reference: docs/{product-name}/brd.md and docs/{product-name}/system-design.md
```

This populates `board-context.md` and the team is ready to start pulling work.

## After Kickoff

Remind the user:
- Run `/daily-sync` regularly to track progress
- Run `/replenish` weekly to keep the Ready column full
- Each handoff document needs approval before the next agent acts
