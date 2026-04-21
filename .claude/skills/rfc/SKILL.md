---
name: rfc
description: "Write a Request for Comments (RFC) for a large feature, epic, or significant technical change. Structures the proposal with problem statement, proposed plan, alternatives, migration plan, and review flow. Use when the user says 'write an RFC', 'RFC', 'proposal', 'technical proposal', 'design doc', 'request for comments', or when a feature is large enough to need upfront design."
---

# RFC — Request for Comments

This skill produces a structured RFC document for features or changes that are too large to implement without upfront design alignment. Per `shared-standards.md`, an RFC is required for any epic or large user story spanning multiple tasks or touching multiple modules.

## When to Write an RFC

An RFC is required when:

- The feature spans **multiple modules or services**
- The change touches **shared KMP code** that affects multiple platforms
- A **new architectural pattern** is being introduced
- The feature requires **data model changes** across services
- The estimated effort is **>2 weeks** of engineering work
- There are **multiple viable approaches** and the team needs to align on one

If the feature is small and the approach is obvious, skip the RFC and go straight to implementation.

## Step 1: Gather Context

Before writing:

```bash
# Check if feature docs already exist
ls docs/{feature-name}/ 2>/dev/null

# Read existing PRD and BRD
cat docs/{feature-name}/prd.md 2>/dev/null
cat docs/{feature-name}/brd.md 2>/dev/null

# Check for existing ADRs that constrain the design
ls docs/{feature-name}/adr-*.md 2>/dev/null

# Check the board for related tasks
cat board-context.md 2>/dev/null | grep -i "{feature-name}"

# Check the codebase for related modules
find . -type d -name "{feature-name}" 2>/dev/null | head -10
```

Identify:

- **Who requested this?** (Morgan's PRD, Diana's BRD, or direct user request)
- **What constraints exist?** (existing ADRs, platform requirements, timeline)
- **Who are the stakeholders?** (which agents will implement, review, or be affected)

## Step 2: Write the RFC

Produce the RFC following this structure exactly:

```markdown
# RFC: {Title}

**Author:** @{AgentName}
**Date:** YYYY-MM-DD
**Status:** Draft → In Review → Accepted / Rejected / Superseded
**Stakeholders:** @Sage, @{implementing agents}, @{affected agents}
**PRD:** docs/{feature-name}/prd.md (if exists)
**BRD:** docs/{feature-name}/brd.md (if exists)

## 1. Goal

[1-3 sentences: What are we building and why? What problem does it solve? What does success look like?]

## 2. Background

[Context that the reader needs to understand the proposal. Include: current state of the system, relevant user feedback, business drivers, technical constraints. Reference existing ADRs if they constrain the design.]

## 3. Proposed Plan

### 3.1 Architecture Overview

[High-level diagram or description of how the components fit together. For KMP projects, show which layers are in commonMain vs platform-specific.]

### 3.2 Implementation Steps

[Step-by-step plan with the affected modules and files. Be specific enough that an implementing agent can follow this without guessing.]

| Step | Description | Module | Agent | Depends On |
|------|-------------|--------|-------|------------|
| 1 | ... | ... | @Agent | — |
| 2 | ... | ... | @Agent | Step 1 |
| ... | ... | ... | ... | ... |

### 3.3 Data Model Changes

[New tables/columns, schema migrations, API contract changes. If no data changes, state "No data model changes required."]

### 3.4 API Changes

[New or modified endpoints. Include request/response shapes. If using shared KMP DTOs, note which shared types are affected.]

### 3.5 Feature Flags

[Which feature flags will gate this feature? What's the rollout strategy?]

Flag: `ff_{feature_name}`
Rollout: Off → 5% canary → 50% → 100% → Remove flag after 4 weeks stable

## 4. Alternatives Considered

[At least 2 alternatives with trade-offs for each. This section demonstrates that the proposal was thoughtfully evaluated.]

### Alternative A: {Name}

**Approach:** [description]
**Pros:** [list]
**Cons:** [list]
**Why not chosen:** [reason]

### Alternative B: {Name}

**Approach:** [description]
**Pros:** [list]
**Cons:** [list]
**Why not chosen:** [reason]

## 5. Open Questions

[Unresolved decisions that need input from stakeholders. Tag the relevant agent for each question.]

| # | Question | Decision Needed From | Status |
|---|----------|---------------------|--------|
| 1 | ... | @Agent | Open |
| 2 | ... | @Agent | Open |

## 6. Security & Privacy Considerations

[How does this feature handle auth, PII, data retention? What does @Shield need to review?]

- Authentication: [how users are authenticated for this feature]
- Authorization: [who can access what]
- PII: [what personal data is collected/stored]
- Data retention: [how long is data kept]
- Third-party data: [does data leave the system?]

If no security implications: "No new security or privacy implications beyond the existing baseline."

## 7. Testing Strategy

[How will this be tested? What coverage is needed?]

- Unit tests: [what logic needs unit tests]
- Integration tests: [what flows need integration tests]
- E2E tests: [what user journeys need end-to-end coverage]
- Performance: [any benchmarking needed?]
- Cross-platform (KMP): [which platforms need verification?]

## 8. Migration Plan

[How do we get from the current state to the proposed state? Especially important for data migrations and breaking API changes.]

- [ ] Phase 1: [expand — add new without removing old]
- [ ] Phase 2: [migrate — move data/traffic to new]
- [ ] Phase 3: [contract — remove old]

If no migration needed: "Greenfield implementation — no migration required."

## 9. Estimated Scope

| Area | Effort | Agent |
|------|--------|-------|
| Backend | X days | @Agent |
| Frontend/Mobile | X days | @Agent |
| Shared (KMP) | X days | @Agent |
| Testing | X days | @Agent |
| Documentation | X days | @Scroll |
| **Total** | **X days** | |

## 10. Rollback Plan

[If the feature causes issues after launch, how do we undo it?]

- Feature flag: disable `ff_{feature_name}`
- Data: [is the migration reversible?]
- API: [are old endpoints still available?]
```

## Step 3: Save the RFC

```bash
# Save to the feature docs directory
mkdir -p docs/{feature-name}
```

Save to `docs/{feature-name}/rfc.md`.

Create the cross-reference per handoff protocol:
```bash
mkdir -p docs/by-type/rfc
echo "See @docs/{feature-name}/rfc.md" > docs/by-type/rfc/{feature-name}.md
```

## Step 4: Submit for Review

The RFC requires approval before implementation begins (per `shared-standards.md`):

```markdown
## RFC Review Request

**RFC:** docs/{feature-name}/rfc.md
**Author:** @{AgentName}
**Status:** In Review

**Reviewers:**
- @Sage — Architecture alignment
- @Shield — Security & privacy (if applicable)
- @{Implementing agents} — Feasibility and effort estimates
- @Zeyad — Final approval

**Open questions:** [count] — see Section 5

Please review and provide feedback. Once all open questions are resolved and @Zeyad approves, the status will change to "Accepted" and implementation can begin.
```

Tag @Atlas to track the RFC review as a board item.

## Step 5: Handle Feedback

When feedback comes in:

1. **Address comments** — update the RFC document inline
2. **Resolve open questions** — update Section 5 status from "Open" to "Resolved: [decision]"
3. **Re-submit** if major changes were made
4. **Accept/reject** — once @Zeyad approves, update the status to "Accepted" and the date

After acceptance:

1. Update status: `**Status:** Accepted (YYYY-MM-DD)`
2. Create board tasks in `board-context.md` based on the implementation steps in Section 3.2
3. Assign tasks to the agents listed in the RFC
4. Notify @Atlas to begin coordination

## Step 6: Post-Implementation

After the feature ships:

1. Update RFC status to `**Status:** Implemented (YYYY-MM-DD)`
2. Link to the actual ADRs, PRs, and release notes produced during implementation
3. Note any deviations from the plan and why they were made
4. The RFC becomes a permanent record of the design decision — useful for future onboarding and retrospectives
