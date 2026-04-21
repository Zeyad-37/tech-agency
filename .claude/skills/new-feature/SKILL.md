---
name: new-feature
description: "Kick off a new feature on an existing product. Starts with Diana (BRD) or Sage (ADR) depending on scope, then sets up board tasks. Use when the user says 'add a feature', 'new feature', 'I want to add', 'implement [something] for [product]', or describes a feature to add to an existing codebase."
---

# New Feature Kickoff

This skill handles the planning chain for adding a feature to an existing product. It's lighter than a full product kickoff — it may skip Morgan (PRD) if the user already knows what they want.

## Step 1: Assess Scope

Ask the user (if not already clear):

- **What** feature? (description)
- **Why?** (user need / business goal)
- **Which product/codebase?** (to find existing docs)
- **Rough size?** (small = 1-2 stories, medium = 3-5, large/epic = 6+)

Check `docs/` for existing context on this product (PRD, BRD, ADRs, system design).

## Step 2: Route by Size

### Small feature (1-2 stories)
Skip BRD. Go straight to the relevant engineer:
```
Using [agent], implement [feature].
User story: [ID]: [description].
Refer to docs/[product]/[relevant-docs].md for context.
```

### Medium feature (3-5 stories)
Start with Diana for a focused BRD:
```
Write a BRD for adding [feature] to [product].
Context: [what exists, what's changing].
Existing architecture: docs/[product]/system-design.md
```
Save to `docs/{feature-name}/brd.md`. **Get @Zeyad approval.**

Then have Sage review if architectural changes are needed. If yes, write an ADR. If the feature fits within existing architecture, skip Sage and go to Atlas for board setup.

### Large feature / Epic
This is an RFC situation. Tell the implementing agent:
```
This is an epic. Write an RFC before any code.
Save to docs/{feature-name}/rfc.md.
Include: Goal, Background, Proposed Plan, Alternatives (2+), Open Questions, Estimated Scope.
```
**Get @Zeyad approval on the RFC.**

Then follow the full chain: Diana (BRD) → Sage (ADR if needed) → Atlas (board setup).

## Step 3: Create a Branch

Before any implementation begins, create a feature branch:

```bash
git checkout -b {STORY-ID}/{short-description}
# e.g., US-042/social-sharing, FEAT-007/push-notifications
```

For small features that skip board setup, create the branch immediately after routing to the engineer. For medium/large features, create the branch after board tasks are set up (so the story ID is available).

## Step 4: Board Setup

For medium and large features, invoke Atlas:
```
Break down the [feature] into tasks and add to the board.
Reference: docs/{feature-name}/brd.md [and adr/rfc if applicable].
Assign agents based on the work involved.
```

## Step 5: Design (if UI is involved)

If the feature has a user-facing component, invoke Pixel:
```
Design the [screens/components] for [feature].
Reference: docs/{feature-name}/brd.md for user stories.
Target platforms: [platforms].
```
Save to `docs/{feature-name}/design-spec.md`. **Get @Zeyad approval.**

## Handoff Reminders

- All docs saved to `docs/{feature-name}/` with cross-references in `docs/by-type/`
- Every handoff doc needs @Zeyad approval before the next step
- Engineers should read all existing feature docs before starting (per agent-preamble.md)
