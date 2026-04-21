# Skills Catalog

Skills are repeatable prompt routines with defined triggers, inputs, and output formats. There are two kinds:

1. **Slash commands** (`.claude/skills/*/SKILL.md`) — 24 project-level workflows invoked with `/command-name`. See `prompts/commands-reference.md` for full documentation.
2. **Agent skills** — inline skills defined in each agent file (`~/.claude/agents/`). These are triggered by natural-language prompts and run within the agent's domain.

This catalog lists agent skills. For slash commands, see the commands reference.

## Atlas — Orchestrator
| Skill | Trigger | Output |
|-------|---------|--------|
| `board-setup` | "Set up board for [feature]" | Kanban board: columns, WIP limits, task breakdown, assignments |
| `daily-sync` | "Run daily sync" | Aggregated status with blockers and cycle time flags |
| `replenishment` | "Replenish the backlog" | Prioritized items moved to Ready, WIP balanced |
| `retro` | "Run retrospective" | Went well, didn't, action items, cycle time analysis |

## Diana — Business Analyst
| Skill | Trigger | Output |
|-------|---------|--------|
| `write-brd` | "Write BRD for [feature]" | BRD: FRs, user stories, NFRs, data dict, risks |
| `write-user-stories` | "Write stories for [feature]" | Given/When/Then acceptance criteria |
| `gap-analysis` | "Gap analysis: current vs target" | Gap report with bridging actions |

## Morgan — Product Owner
| Skill | Trigger | Output |
|-------|---------|--------|
| `write-prd` | "Write PRD for [product]" | Vision, personas, features (RICE), MVP scope, metrics |
| `prioritize-backlog` | "Prioritize the backlog" | RICE-scored list with recommended pull order |
| `competitive-analysis` | "Analyze competitors for [product]" | Competitive matrix |
| `write-release-notes` | "Write release notes for vX.Y.Z" | User-facing highlights, fixes, known issues |

## Sage — Solutions Architect
| Skill | Trigger | Output |
|-------|---------|--------|
| `write-adr` | "Write ADR for [decision]" | ADR: Status, Context, Decision, Consequences |
| `system-design` | "Design system for [feature]" | Mermaid diagrams, API contracts, data model |
| `api-design` | "Design API for [resource]" | OpenAPI endpoint spec with schemas |
| `tech-selection` | "Evaluate [A] vs [B]" | Weighted comparison matrix |

## Pixel — UI/UX Designer
| Skill | Trigger | Output |
|-------|---------|--------|
| `design-tokens` | "Generate design tokens" | JSON: colors, typography, spacing, elevation |
| `component-spec` | "Spec component [name]" | Props, states, variants, accessibility |
| `wireframe` | "Wireframe [screen]" | Layout, component tree, breakpoints |
| `accessibility-audit` | "Audit accessibility" | WCAG 2.1 AA checklist |
| `user-flow` | "Map user flow for [journey]" | Mermaid flowchart |

## Nova — Frontend Web
| Skill | Trigger | Output |
|-------|---------|--------|
| `implement-component` | "Implement [component]" | React/TS component + tests + Storybook |
| `implement-page` | "Implement [page]" | Next.js page with data fetching |
| `api-integration` | "Integrate API [endpoint]" | React Query hook with types |
| `performance-audit` | "Audit performance" | Core Web Vitals report |

## Swift — iOS Engineer
| Skill | Trigger | Output |
|-------|---------|--------|
| `implement-screen` | "Implement [screen] in SwiftUI" | SwiftUI view + ViewModel + accessibility |
| `api-integration` | "Integrate API [endpoint] for iOS" | Async/await + Codable models |
| `crash-investigation` | "Investigate crash [ID]" | Root cause + fix |

## Kai — Android Engineer
| Skill | Trigger | Output |
|-------|---------|--------|
| `implement-screen` | "Implement [screen] in Compose" | Compose UI + ViewModel + accessibility |
| `api-integration` | "Integrate API [endpoint] for Android" | Retrofit + coroutines + DTOs |
| `crash-investigation` | "Investigate crash [ID]" | Root cause + fix |

## Link — KMP Engineer
| Skill | Trigger | Output |
|-------|---------|--------|
| `create-kmp-module` | "Create KMP module [name]" | Gradle + source sets + tests + integration guide |
| `expect-actual` | "Create platform abstraction for [X]" | expect/actual per target |
| `integration-guide` | "Write integration guide for [module]" | iOS + Android instructions |

## Flux — Backend Node.js
| Skill | Trigger | Output |
|-------|---------|--------|
| `implement-endpoint` | "Implement [METHOD /path]" | Fastify route + Zod + Prisma + tests |
| `database-migration` | "Create migration for [change]" | Prisma migration + rollback |
| `implement-worker` | "Implement worker for [job]" | BullMQ worker + retry + monitoring |

## Pyra — Backend Python
| Skill | Trigger | Output |
|-------|---------|--------|
| `implement-endpoint` | "Implement [METHOD /path]" | FastAPI route + Pydantic + tests |
| `database-migration` | "Create migration for [change]" | Alembic migration + rollback |
| `implement-task` | "Implement Celery task for [job]" | Celery task + retry + monitoring |

## Forge — Backend JVM
| Skill | Trigger | Output |
|-------|---------|--------|
| `implement-endpoint` | "Implement [METHOD /path]" | Spring controller + service + repo + tests |
| `database-migration` | "Create migration for [change]" | Flyway migration + JPA entity |
| `implement-service` | "Implement service for [domain]" | Spring service + DI + transactions |

## Neuron — AI/ML Engineer
| Skill | Trigger | Output |
|-------|---------|--------|
| `write-model-card` | "Write model card for [model]" | Purpose, data, metrics, limitations, bias |
| `design-ml-pipeline` | "Design pipeline for [task]" | Data flow, features, training, evaluation |
| `prompt-engineering` | "Design prompts for [use case]" | System prompt + few-shot + evaluation |
| `rag-design` | "Design RAG for [use case]" | Chunking, embedding, vector DB, retrieval |

## Pipeline — Data Engineer
| Skill | Trigger | Output |
|-------|---------|--------|
| `design-data-model` | "Design data model for [domain]" | ERD + DDL + docs + lineage |
| `write-dbt-model` | "Write dbt model for [entity]" | SQL + YAML schema + tests |
| `design-pipeline` | "Design pipeline for [source→target]" | DAG + transforms + scheduling |

## Sentinel — DevOps/SRE
| Skill | Trigger | Output |
|-------|---------|--------|
| `deploy-service` | "Deploy [service] vX.Y.Z" | Staging → canary → production + monitor |
| `write-terraform` | "Write Terraform for [resource]" | HCL module + variables + tests |
| `incident-response` | "Incident: [description]" | Assess → communicate → investigate → mitigate |
| `post-mortem` | "Post-mortem for [incident]" | Timeline, root cause, lessons, actions |

## Shield — Security Engineer
| Skill | Trigger | Output |
|-------|---------|--------|
| `security-review` | "Review [component/PR]" | OWASP findings + remediation plan |
| `threat-model` | "Threat model for [system]" | STRIDE analysis + risk matrix |
| `compliance-audit` | "Audit compliance for [standard]" | Controls review + gaps + remediation |

## Apex — QA Engineer
| Skill | Trigger | Output |
|-------|---------|--------|
| `write-test-plan` | "Write test plan for [feature]" | Scope, approach, data, schedule, criteria |
| `write-e2e-tests` | "Write E2E tests for [feature]" | Playwright/Appium test suite |
| `bug-triage` | "Triage bug [description]" | Reproduce, classify, document, assign |
| `release-signoff` | "Sign off release vX.Y.Z" | Quality gates → APPROVED/BLOCKED |

## Scroll — Technical Writer
| Skill | Trigger | Output |
|-------|---------|--------|
| `api-docs` | "Document API for [resource]" | Endpoint reference + examples + errors |
| `user-guide` | "Write user guide for [feature]" | Step-by-step + troubleshooting |
| `changelog` | "Write changelog for vX.Y.Z" | Added/Changed/Fixed/Security/Deprecated |

## Echo — Support Engineer
| Skill | Trigger | Output |
|-------|---------|--------|
| `resolve-ticket` | "Resolve ticket [ID]" | Diagnose → resolve/escalate → document |
| `triage-bug` | "Triage bug from [customer]" | Reproduce, classify, escalate |
| `feature-request-compilation` | "Compile feature requests" | Ranked list + votes + impact |
| `customer-feedback-analysis` | "Analyze feedback for [period]" | Trends, sentiment, recommendations |
