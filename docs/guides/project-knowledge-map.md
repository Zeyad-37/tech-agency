# Project Knowledge Map

This document specifies which project-specific artifacts each agent needs access to as work progresses. Unlike the static agent definitions, project knowledge is generated during development and uploaded as context grows.

## Knowledge Flow

As the agency works on a project, artifacts flow downstream:

```
Morgan (PRD) → upload to Diana
Diana (BRD) → upload to Sage + all engineers
Sage (ADRs) → upload to relevant engineers
Pixel (design tokens) → upload to Nova, Swift, Kai, Link
Backend (API specs) → upload to Nova, Swift, Kai, Link
```

## Per-Agent Knowledge Needs

### Atlas — Orchestrator
- board-context.md (always current)
- Active PRD, BRD, ADRs (for coordination context)

### Diana — Business Analyst
- Active PRD from Morgan
- BRD template (in agent definition skills)
- Domain glossary (if exists)
- Regulatory context (GDPR, HIPAA, PCI-DSS if applicable)

### Morgan — Product Owner
- Market research, competitive analysis
- Customer feedback summaries from Echo
- Product metrics dashboards

### Sage — Solutions Architect
- Active BRD from Diana
- Existing ADR log
- System design docs
- API standards reference

### Pixel — UI/UX Designer
- Active BRD/ADRs for feature context
- Existing design tokens (`design-tokens.json`)
- Component library inventory
- Platform guidelines (HIG, Material 3)

### Nova — Frontend Web
- Design specs + tokens from Pixel
- API contracts from backends
- Relevant ADRs from Sage

### Swift — iOS Engineer
- Design specs + tokens from Pixel
- KMP integration guides from Link
- API contracts from backends
- Relevant ADRs from Sage

### Kai — Android Engineer
- Design specs + tokens from Pixel
- KMP integration guides from Link
- API contracts from backends
- Relevant ADRs from Sage

### Link — KMP Engineer
- API contracts from backends
- Design specs from Pixel (for data models)
- Relevant ADRs from Sage
- Platform integration feedback from Swift/Kai

### Flux / Pyra / Forge — Backend Engineers
- Active BRD from Diana
- ADRs + API contracts from Sage
- Database schema docs

### Neuron — AI/ML Engineer
- ML requirements from Sage
- Data availability docs from Pipeline
- Model registry/catalog

### Pipeline — Data Engineer
- Data requirements from Sage
- Source system schemas
- Analytics requirements from Morgan

### Sentinel — DevOps/SRE
- Deployment configs from engineers
- Security sign-off from Shield
- SLO/SLI definitions
- Runbooks (self-maintained)

### Shield — Security Engineer
- Architecture docs from Sage
- Code/PRs from all engineers
- Compliance requirements
- Previous security review findings

### Apex — QA Engineer
- Acceptance criteria from Diana
- Design specs from Pixel
- API contracts from backends
- Performance budgets from Sage

### Scroll — Technical Writer
- OpenAPI specs from backends
- ADRs from Sage
- Runbooks from Sentinel
- Release notes from Morgan
- Known issues from Apex/Echo

### Echo — Support Engineer
- Documentation from Scroll
- Known issues from Apex
- Release notes from Morgan
- FAQ database (self-maintained)
