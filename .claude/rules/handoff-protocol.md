# Handoff Protocol & Templates

## General Rules

- Every handoff uses a template from this file
- Include all required metadata fields
- Action items tagged with `@AgentName`
- Priority levels: P0 (critical), P1 (high), P2 (medium), P3 (low)
- Receiving agent acknowledges within 1 daily sync cycle
- Every handoff document must be saved to `docs/{feature-name}/{handoff-doc-type}.md` (e.g., `docs/user-auth/prd.md`, `docs/user-auth/brd.md`, `docs/user-auth/adr-001.md`). This groups all artifacts for a feature together in the repo.
- Additionally, maintain a cross-reference index at `docs/by-type/{handoff-doc-type}/{feature-name}.md` that symlinks or re-exports the source document (e.g., `docs/by-type/prd/user-auth.md` → `../../user-auth/prd.md`). This provides a unified view by document type across all features. Each index file should contain a single line: `See @docs/{feature-name}/{handoff-doc-type}.md` pointing to the canonical source.

## Templates

### 1. Morgan → Diana: PRD Handoff
```
**From:** @Morgan | **To:** @Diana | **Date:** YYYY-MM-DD
**PRD:** [Name] | **Version:** X.Y | **Priority:** P[0-3]
**Sections:** Vision, Personas, Features (with RICE scores), MVP Scope, Success Metrics
**Action:** @Diana — Produce BRD with user stories, NFRs, data dictionary. Flag ambiguities.
```

### 2. Diana → Sage: BRD Handoff
```
**From:** @Diana | **To:** @Sage | **Date:** YYYY-MM-DD
**BRD:** [Name] | **Version:** X.Y
**Includes:** Functional Reqs, User Stories (Given/When/Then), NFRs, Data Dictionary, Risks
**Action:** @Sage — Produce ADRs, system design, API contracts. Identify tech debt risks.
```

### 3. Sage → Engineers: ADR Handoff
```
**From:** @Sage | **To:** @[Engineer] | **Date:** YYYY-MM-DD
**ADR:** ADR-[NNN]-[title] | **Status:** Accepted
**Includes:** Context, Decision, Consequences, Alternatives Considered, API Contracts
**Action:** @[Engineer] — Implement per ADR. Raise if constraints conflict.
```

### 4. Sage → Pixel: Design Brief
```
**From:** @Sage | **To:** @Pixel | **Date:** YYYY-MM-DD
**Feature:** [Name] | **User Stories:** [refs]
**Includes:** Constraints, platform targets, accessibility requirements, data shapes
**Action:** @Pixel — Produce design tokens, component specs, wireframes. CC: @Nova, @Swift, @Kai
```

### 5. Sage → Pipeline: Data Model Handoff
```
**From:** @Sage | **To:** @Pipeline | **Date:** YYYY-MM-DD
**Feature:** [Name] | **Data Requirements:** [summary]
**Action:** @Pipeline — Design dimensional model, create dbt models, define quality checks.
```

### 6. Sage → Neuron: ML Requirements
```
**From:** @Sage | **To:** @Neuron | **Date:** YYYY-MM-DD
**Feature:** [Name] | **ML Task:** [classification/generation/etc.]
**Includes:** Data availability, latency requirements, accuracy targets
**Action:** @Neuron — Design ML pipeline, write model card, define inference API.
```

### 7. Pixel → Engineers: Design Spec
```
**From:** @Pixel | **To:** @Nova/@Swift/@Kai/@Link | **Date:** YYYY-MM-DD
**Component/Screen:** [Name] | **Design Tokens:** [ref]
**Includes:** Component tree, props/states/variants, responsive breakpoints, accessibility, animations
**Action:** Implement per spec. Flag deviations before proceeding.
```

### 8. Backend → Frontend: API Contract
```
**From:** @Flux/@Pyra/@Forge | **To:** @Nova/@Swift/@Kai/@Link
**Endpoint:** [METHOD /path] | **OpenAPI Spec:** [ref]
**Includes:** Request/response schemas, auth requirements, rate limits, error codes
**Action:** Integrate endpoint. Report any schema mismatches.
```

### 9. Engineers → Shield: Security Review Request
```
**From:** @[Engineer] | **To:** @Shield | **Date:** YYYY-MM-DD
**Component:** [Name] | **PR:** [link]
**Scope:** [Auth/Data handling/API/Infrastructure]
**Action:** @Shield — Review for OWASP Top 10, auth logic, data handling, dependencies.
```

### 10. Shield → Engineers: Security Review Report
```
**From:** @Shield | **To:** @[Engineer] | **Date:** YYYY-MM-DD
**Status:** Approved / Conditional / Rejected
**Findings:** [Critical: N, High: N, Medium: N, Low: N]
**Action:** Fix critical/high before merge. Medium next in queue. Low in backlog.
```

### 11. Apex → Engineers: Bug Report
```
**From:** @Apex | **To:** @[Engineer] | **Date:** YYYY-MM-DD
**Bug ID:** BUG-[NNN] | **Severity:** Critical/High/Medium/Low
**Steps to Reproduce:** [numbered steps]
**Expected:** [behavior] | **Actual:** [behavior]
**Environment:** [OS, browser, device, version]
**Action:** @[Engineer] — Fix and notify @Apex for re-test.
```

### 12. Apex → Sentinel: Release Sign-Off
```
**From:** @Apex | **To:** @Sentinel | **Date:** YYYY-MM-DD
**Version:** vX.Y.Z | **Status:** APPROVED / BLOCKED
**Test Results:** [pass/fail counts] | **Open Bugs:** [critical: 0, high: 0]
**Action:** @Sentinel — Proceed with deployment / Hold pending fixes.
```

### 13. Engineers → Sentinel: Deployment Request
```
**From:** @[Engineer] | **To:** @Sentinel | **Date:** YYYY-MM-DD
**Service:** [name] | **Version:** vX.Y.Z | **Artifact:** [Docker image/tag]
**Changes:** [summary] | **Rollback Plan:** [steps]
**Action:** @Sentinel — Deploy to staging, then production with canary.
```

### 14. Sentinel → Scroll: Runbook Handoff
```
**From:** @Sentinel | **To:** @Scroll | **Date:** YYYY-MM-DD
**Service:** [name] | **Runbook Type:** [deployment/incident/scaling]
**Includes:** Procedures, monitoring dashboards, escalation contacts, recovery steps
**Action:** @Scroll — Document as operational guide. CC: @Echo
```

### 15. All → Scroll: Documentation Request
```
**From:** @[Agent] | **To:** @Scroll | **Date:** YYYY-MM-DD
**Doc Type:** [API ref/User guide/Architecture/Changelog]
**Source:** [OpenAPI spec/ADR/Code/Release notes]
**Audience:** [Developers/Operators/End users]
**Action:** @Scroll — Produce documentation. Review with source agent.
```

### 16. Echo → Engineers: Escalation
```
**From:** @Echo | **To:** @[Engineer] | **Date:** YYYY-MM-DD
**Ticket:** [ID] | **Customer Impact:** [N users affected]
**Issue:** [description] | **Steps Tried:** [list]
**Action:** @[Engineer] — Investigate and provide fix/workaround. CC: @Atlas
```

### 17. Echo → Morgan: Feature Request Compilation
```
**From:** @Echo | **To:** @Morgan | **Date:** YYYY-MM-DD
**Period:** [date range] | **Requests:** [count]
**Top Requests:** [ranked list with vote counts and customer quotes]
**Action:** @Morgan — Consider for roadmap prioritization.
```

### 18. Atlas → Any: Task Assignment
```
**From:** @Atlas | **To:** @[Agent] | **Date:** YYYY-MM-DD
**Task:** T-[NNN] | **Priority:** P[0-3]
**Description:** [what to do] | **Acceptance Criteria:** [list]
**Dependencies:** [blocked by / blocks] | **Due:** [date]
**Action:** @[Agent] — Acknowledge and pull when ready. Update board daily.
```

### 19. Any → Atlas: Status Update
```
**From:** @[Agent] | **To:** @Atlas | **Date:** YYYY-MM-DD
**Task:** T-[NNN] | **Status:** In Progress / Review / Done / Blocked
**Progress:** [summary] | **Blocker:** [if any]
**Next:** [planned work] | **ETA:** [date]
```
