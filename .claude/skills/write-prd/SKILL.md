---
name: write-prd
description: "Dispatch Morgan (product owner) to write a Product Requirements Document (PRD) following top industry standards — problem framing, personas, RICE-scored features, explicit MVP boundary, measurable success metrics, risks, and launch criteria. Use when the user says 'write a PRD', 'PRD for [feature/product]', 'create a PRD', 'draft product requirements', 'product spec', or 'requirements doc' — without wanting the full new-product planning chain."
---

# Write PRD — Product Requirements Document

This skill dispatches the `morgan-product-owner` agent to produce a standalone, industry-standard PRD. Unlike `/new-product`, it does NOT chain into BRD/ADR/board setup — it produces one approved PRD and stops. Use it for a new feature on an existing product, a product idea that needs definition before committing to a planning chain, or to backfill a PRD for work already in flight.

## Step 1: Gather Product Input

Collect from the user before dispatching Morgan (ask only for what's missing — don't interrogate if the request already contains it):

- **What** is the product/feature? (1-2 sentences)
- **Why now?** (business driver, customer evidence, OKR link)
- **Who** is it for? (target users/personas)
- **Core capabilities** (3-5 must-haves, if known)
- **Target platforms** (iOS, Android, Web, KMP-shared?)
- **Constraints** (timeline, budget, compliance, existing systems)
- **Competitors** (if known — Morgan will do competitive analysis for major features)

If a PRD, BRD, or related docs already exist for this feature, locate them first:

```bash
grep -ril "{feature-name}" docs/artifacts/prd/ docs/artifacts/brd/ docs/artifacts/adr/ docs/artifacts/rfc/ 2>/dev/null
cat board-context.md 2>/dev/null | grep -i "{feature-name}"
```

If a PRD already exists, ask whether to revise it or write a new version — never silently overwrite.

## Step 2: Dispatch Morgan

Invoke the `morgan-product-owner` agent with the gathered context:

```
Write a PRD for [product/feature description].

Context:
- Business driver: [why now / OKR link / customer evidence]
- Target audience: [who]
- Core capabilities: [list]
- Target platforms: [platforms]
- Constraints: [any]
- Existing docs: [paths found in Step 1, if any]

Follow the PRD structure below exactly. Every feature must carry a RICE score.
Every goal must have a measurable success metric with a baseline and target —
no vague goals like "improve engagement". The MVP boundary must be explicit
(in-scope AND out-of-scope with the deferral reason). Return the complete PRD
as markdown.
```

### Required PRD Structure (industry standard)

Morgan must produce the PRD with these sections, in order:

```markdown
# PRD: {Product/Feature Name}

**Author:** @Morgan
**Date:** YYYY-MM-DD
**Version:** 0.1 (Draft)
**Status:** Draft → In Review → Approved
**Stakeholders:** @Diana, @Sage, @{relevant agents}, @Zeyad (approver)

## 1. Executive Summary

[3-5 sentences a stakeholder can read in 30 seconds: the problem, the proposed
solution, who it serves, and the headline success metric.]

## 2. Problem Statement & Opportunity

[What user/business problem exists today? Back it with evidence: support
tickets, funnel data, user interviews, market research. Quantify the pain
where possible. State the cost of doing nothing.]

## 3. Goals & Non-Goals

### Goals
[3-5 outcomes, each tied to a measurable metric in Section 9.]

### Non-Goals
[What this explicitly does NOT try to solve — prevents scope creep and aligns
reviewers on boundaries.]

## 4. Personas & Target Users

[For each persona: name, role/context, core need, pain points, and the
job-to-be-done this feature addresses. 2-3 personas maximum — focus.]

## 5. User Stories (Outline)

[High-level user stories per persona: "As a {persona}, I want {capability}
so that {outcome}". Detailed Given/When/Then acceptance criteria are Diana's
job in the BRD — keep these at outline level.]

## 6. Features & Prioritization (RICE)

[Every feature scored. RICE = (Reach × Impact × Confidence) / Effort.]

| Feature | Reach (1-10) | Impact (1-10) | Confidence (1-10) | Effort (person-weeks) | RICE | Priority |
|---------|------|--------|------------|--------|------|----------|
| ... | ... | ... | ... | ... | ... | P0/P1/P2 |

[Per feature: 2-4 sentence description + business justification linking to a
goal or OKR. No feature without business justification.]

## 7. MVP Scope

### In MVP
[Explicit list. Each item maps to a P0/P1 feature above.]

### Out of MVP (deferred)
[Explicit list with the deferral reason and target version, e.g.
"Apple Sign-In — v1.1, pending iOS roadmap priority".]

## 8. Competitive Analysis

[Required for major features. Matrix: Feature | Competitor A | Competitor B |
Us (current) | Us (post-launch) | Differentiation. For minor features, a short
paragraph on the competitive context suffices.]

## 9. Success Metrics

[Every metric needs: baseline (current value), target, timeframe, and how it
will be measured. Include 1-2 guardrail metrics that must NOT regress
(e.g., crash-free rate, churn).]

| Metric | Baseline | Target | Timeframe | Source |
|--------|----------|--------|-----------|--------|
| ... | ... | ... | ... | ... |

## 10. Dependencies & Assumptions

[Upstream/downstream dependencies (teams, services, third parties, legal/
compliance review) and the assumptions this PRD rests on. Flag any assumption
that, if wrong, invalidates the plan.]

## 11. Risks & Mitigations

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|------------|
| 1 | ... | H/M/L | H/M/L | ... |

## 12. Launch Criteria & Rollout

[What must be true to ship: quality gates, accessibility sign-off, feature
flag (`ff_{feature_name}`) and rollout plan (off → canary → 100%), and the
go/no-go owner.]

## 13. Open Questions

| # | Question | Owner | Status |
|---|----------|-------|--------|
| 1 | ... | @Agent | Open |

## 14. Changelog

| Version | Date | Author | Change |
|---------|------|--------|--------|
| 0.1 | YYYY-MM-DD | @Morgan | Initial draft |
```

## Step 3: Save the PRD

Per the handoff protocol (`@.claude/rules/shared/handoff-protocol.md`):

```bash
mkdir -p docs/prd
```

Save to `docs/artifacts/prd/{Task-Id}-PRD-{Title}.md` (e.g., `docs/artifacts/prd/US-042-PRD-Social Login.md`). If no task ID exists yet, use the feature slug and note that @Atlas should assign an ID when the work is boarded.

## Step 4: Quality Check Before Presenting

Before presenting to @Zeyad, verify the PRD against Morgan's constraints:

- [ ] Every feature has a RICE score and a business justification
- [ ] Every goal maps to a measurable success metric with baseline + target
- [ ] MVP boundary is explicit — both in-scope and out-of-scope lists exist
- [ ] Non-goals section is present and non-empty
- [ ] Competitive analysis included (for major features)
- [ ] Risks have mitigations, not just a list of fears
- [ ] No vague language ("improve engagement", "better UX") without numbers

If any check fails, send the PRD back to Morgan with the specific gaps — do not present an incomplete PRD.

## Step 5: Submit for Approval

Per the approval gate in `shared-standards.md`, the PRD requires explicit approval from @Zeyad before any downstream agent acts on it.

**STOP: Present the PRD to @Zeyad for approval.** Summarize: the problem, MVP scope, top-3 RICE features, and headline success metric. Wait for approval or change requests. On change requests, revise via Morgan and re-submit.

## After Approval

Once approved:

1. Update the PRD header: `**Status:** Approved (YYYY-MM-DD)` and bump the version to 1.0
2. Offer the next step — but do not run it without being asked:
   - `/new-feature` to hand off to Diana (BRD) and continue the planning chain
   - `/replenish` if the work should be boarded directly
3. Use the Morgan → Diana handoff template (#1 in `handoff-protocol.md`) when the user proceeds
