# Shared Standards — All Agents

## Where the Rules Live

This file is one of the **shared policy rules** — they are copied into every consumer project's
`.claude/rules/shared/` by `/setup-repo` and auto-load every session, so they are always already in
your context.

The **language coding standards** are not. They stay in the plugin and must be **read on demand**:
before writing code in a stack, read that stack's standard. The full model — which files are in
which set, the exact reference form for each, and the resolution snippet — is in
`@.claude/rules/shared/rules-delivery.md`. Read it before referencing any rule path.

The nested layout is canonical everywhere. Never emit a flat `.claude/rules/<name>.md` path.

## Communication Protocol

- Use `@AgentName` mentions in handoffs
- Handoff message format: "I've completed [artifact]. See [location]. Test plan: [checklist]. CC: @[Agent]."
- Ask clarifying questions before committing to work
- Communicate blockers within 1 hour of discovery
- Escalate to @Atlas if blocked >4 hours

## Quality Gates

- Every deliverable has acceptance criteria before work begins
- All code changes must be covered by tests on the same branch before the task moves to Review — no separate test tasks, no deferred coverage
- Tests must pass locally before committing. A task with failing tests must not be moved to Review
- Code reviews required before merge
- No deliverable ships without at least one other agent's review
- All artifacts version-controlled

## UI Render Decisions Belong to Typed Structures (platform-agnostic)

Every "what should the UI do here?" question must resolve to a typed structure — a sealed type, an enum, or a polymorphic property — not a chain of `if`/`else` over scalar fields. This applies across all UI platforms (Compose, SwiftUI, React).

Five categories of UI decision (RFC T-013):

| # | Category | Right answer |
|---|---|---|
| **a** | Data-driven screen shape (loading / empty / error / success) | Sealed `State` hierarchy + exhaustive `when`/`switch` at the screen root |
| **b** | Domain type capability ("does *this kind of entry* support *this action*?") | Polymorphic property on the sealed domain type, not `is FooPM` at the call site |
| **c** | Component variant / style ("how should this component look in *this slot*?") | Sealed enum prop type (`titleStyle: TitleStyle.Large`), not `useLargeTitleStyle: Boolean` |
| **d** | Mutually-exclusive sub-state ("which of N things is currently active?") | Single sealed field on State (`dialog: ActiveDialog?`), not N parallel Booleans |
| **e** | Pure UI-local ephemeral state (scroll, focus, animation frame) | Platform-native ephemeral state (`remember`/`@State`/`useState`); do not promote to ViewModel |

Each platform enforces this via its own static analysis: Kotlin/Compose uses Konsist + custom Detekt rules (see `${CLAUDE_PLUGIN_ROOT}/rules/mobile/android/compose-coding-standards.md` and `${CLAUDE_PLUGIN_ROOT}/rules/mobile/shared/kmp-coding-standards.md`; fall back to `.claude/rules/…` when `CLAUDE_PLUGIN_ROOT` is unset — see `@.claude/rules/shared/rules-delivery.md`). SwiftUI and React adopt equivalent enforcement when their teams reach this RFC. The principle is platform-agnostic; the enforcement plumbing is platform-specific.

## Git Commit Policy

- Commit after every logical change — do not batch unrelated changes
- Commit message format: `[ID] @AgentName: Short description of what changed and why`
  - `[ID]` is required. It is one or more letters, optionally followed by `-` and a number: `[US-042]`, `[T-015]`, `[BUG-017]`, `[TECH]`, `[tech]`
  - `@AgentName:` is **optional but strongly preferred** — include it whenever an agent authored the commit, so the change is traceable to its author. Omit it only for mechanical commits with no single agent author (automated version bumps, merge/revert commits)
  - The description must be at least 3 characters and say what changed and why
- Valid examples: `[US-042] @Kai: Add email validation to registration flow`, `[T-015] @Claude: Resolve dispatch base branch dynamically`, `[TECH] @Claude: Auto-bump VERSION to 0.1.12`, `[tech] Widen commit-msg regex`
- The ID must come from the task being implemented — the user story, tech task, or bug ID on the board
- If a change spans multiple stories, create separate commits per story
- The `commit-msg` hook enforces exactly this shape. See `@.claude/rules/shared/git-hooks.md` for the hook's canonical regex and its exemptions (merge, initial, revert commits)

## Security Baseline

- No secrets in code or logs — use environment variables / secret managers
- PII: never log plain emails, phone numbers, SSNs; mask in non-prod
- Input validation on all external boundaries
- HTTPS only; TLS 1.2+ minimum
- Authentication: JWT (RS256) with refresh token rotation, OAuth2 for third-party, API keys stored hashed

## Sandboxed Execution (Project Setup — Verify Before Relying On It)

The OS sandbox is a **project-level setup step, not an ambient guarantee.** It is configured in the
**consumer project's** `.claude/settings.json`, which `/setup-repo` writes at bootstrap. A
`settings.json` shipped inside the plugin does **not** configure a sandbox for an installing user —
Claude Code reads only a narrow set of keys from a plugin's settings file, and `sandbox` is not one
of them.

**Never assume you are sandboxed.** Verify, then act accordingly:

```bash
# Is a sandbox configured for THIS project?
test -f .claude/settings.json && grep -q '"sandbox"' .claude/settings.json \
  && echo "sandbox configured" || echo "NO sandbox configured for this project"
```

- If it reports **no sandbox**: you are running unsandboxed. Treat every Bash command as capable of
  writing anywhere the user can write. Stay inside your worktree by discipline rather than by
  enforcement, and tell @Zeyad that `/setup-repo` has not yet written the sandbox block.
- If it reports **sandbox configured**: the settings below apply.

When a sandbox is configured (`sandbox.enabled: true`, `failIfUnavailable: true`):

- Every agent and every spawned subagent inherits the session's sandbox.
- Bash writes are confined to the worktree (cwd) + the allowlisted tool-cache paths, and network is restricted to the allowlisted registries/hosts. Sandboxed commands auto-run without extra permission prompts.
- When a build legitimately needs a host or write path that is blocked, **extend** `sandbox.network.allowedDomains` / `sandbox.filesystem.allowWrite` in a PR — do not disable the sandbox and do not reach for `dangerouslyDisableSandbox` as a workaround.
- VCS network operations (`git push/fetch/pull`, `gh`) are intentionally excluded from the sandbox so SSH/auth work; they remain gated by the push policy in "Branch Strategy" below.
- Linux/WSL2 runners require `bubblewrap` + `socat`; macOS uses built-in Seatbelt. With `failIfUnavailable: true`, Claude Code refuses to run unsandboxed if those deps are missing.

## Observability Baseline

- Structured JSON logging: `level`, `timestamp`, `service`, `traceId`, `userId`
- Request/response logging via middleware (body sanitized for PII)
- OpenTelemetry spans for database, HTTP, messaging operations
- Health check endpoints on all services

## Testing Baseline

- Unit tests: pure functions, mocked dependencies
- Integration tests: real database (testcontainers where available), mocked external services
- Coverage targets: 80%+ core logic, 60%+ overall
- Tests must be deterministic and independent

## Error Handling

Standard error response envelope:
```json
{
  "status": "error",
  "error": {
    "code": "VALIDATION_FAILED",
    "message": "User-friendly message",
    "details": { "email": "Invalid format", "name": "Name too short" }
  }
}
```

`details` is a **keyed object**, not an array: field name → message. For non-field errors, use any
descriptive key. It is optional — omit it or send `{}` when there is nothing to itemize.

Three of the four backend standards already type it exactly this way — Node as
`Record<string, unknown>`, Python as `dict`, JVM as `Map<String, Any>` — and the React client
standard parses it as `Record<string, unknown>`. A frontend written against this baseline works
against all three unchanged. The Ktor/KMP shared envelope is the exception: its `ApiError` currently
carries only `code` and `message` and has no `details` field at all. When a Ktor service needs to
itemize an error, add `details` to the shared `ApiError` as a serializable string-keyed map — do not
invent a different shape for it.

Never emit `details` as an array of `{field, message}` objects.

Standard success response envelope:
```json
{
  "status": "success",
  "data": {},
  "meta": { "timestamp": "ISO8601", "version": "1.0.0" }
}
```

## Documentation

- All public APIs documented with OpenAPI 3.1
- All architecture decisions recorded as ADRs
- Code comments explain "why", not "what"
- README in every module/service

## RFC Requirement

- When assigned an epic or a large user story (spanning multiple tasks or touching multiple modules), the implementing agent must write an RFC before writing any code
- Save the RFC to `docs/rfc/{Task-Id}-RFC-Title.md` (e.g., `docs/rfc/US-042-RFC-Shared Auth Module.md`)
- The RFC must include: **Goal** (what we're building and why), **Background** (relevant context), **Proposed Plan** (step-by-step implementation approach with affected modules/files), **Alternatives Considered** (at least 2, with trade-offs for each), **Open Questions** (unresolved decisions that need input), and **Estimated Scope** (rough size in story points or days)
- The RFC must be approved by @Zeyad before implementation begins

## Approval Gate

- All handoff documents (PRD, BRD, ADR, RFC, design specs, security reviews) require explicit approval from @Zeyad before the receiving agent may act on them
- The producing agent must present the document and wait for approval. Do not proceed to the next step until @Zeyad confirms
- If changes are requested, revise the document and re-submit for approval

## Context Continuity

- Before starting any task, search for existing docs across the relevant type folders (`docs/prd/`, `docs/brd/`, `docs/adr/`, `docs/rfc/`, etc.) using the Task ID or feature name to locate all related documents
- Check `board-context.md` for current board state, WIP items, and blockers
- If prior ADRs, BRDs, or RFCs exist for the feature, follow their decisions — do not contradict them without raising an explicit change request to @Sage and getting approval from @Zeyad
- When resuming work from a previous session, re-read the relevant handoff docs and your last status update to @Atlas

## Branch Strategy

- Never commit directly to `main` — all work happens on branches
- Branch naming by type:
  - Features: `{STORY-ID}/{short-description}` (e.g., `US-042/email-validation`)
  - Tech tasks: `tech/{short-description}` (e.g., `tech/improve-git-hooks`)
  - Dependency upgrades: `deps/{package}-{version}` or `deps/monthly-update-{date}`
  - Hotfixes: `hotfix/{version}/{short-description}` (e.g., `hotfix/v1.2.1/fix-login-crash`)
  - Releases: `release/{version}` (e.g., `release/v1.3.0`)
- One branch per user story. If a story is split across agents, use the same branch
- Merge to `main` only after: code review passed, Shield security review passed (if applicable), Apex QA sign-off received
- Delete the branch after merge

### Push Policy

**Invoking `/create-pr` or `/ship-pr` IS the push authorization for that branch.** No separate
confirmation is required. Those skills own the full sequence — commit, run the pre-push verification
gate, push the branch, open the PR — and the act of invoking them is the explicit instruction to do
it. `/ship-it` and `/dispatch` authorize the same thing transitively, because they invoke
`/create-pr` on your behalf.

**Outside those skills, never run a bare `git push`.** Commit locally on your task branch and let
the skill push. If you believe a branch needs pushing and no skill is running, ask @Zeyad rather
than pushing.

**Never push to `main`, under any circumstance.** Not with `--force`, not to "fix" a bad merge, not
as a shortcut. `main` changes only through a merged PR. The `pre-push` hook blocks direct pushes to
`main`; that hook is a backstop, not permission to try.

This is what `@.claude/rules/shared/agent-preamble.md` step 7 means when it routes every finished
task through `/create-pr`. If you want to prepare a PR without pushing — for example a parent skill
managing its own approval gate — pass `/create-pr --no-push`, which stops at the pre-push
verification gate.

## Worktree-First Workflow (Mandatory)

**All Claude Code work happens in a git worktree. No exceptions.** The main checkout is an orchestration root only — it holds the canonical `.git` directory and parents the worktrees. No task work runs there.

The full protocol — branch naming, creation commands, verification, exceptions — lives in `@.claude/rules/shared/worktree-first.md`. The agent preamble (`@.claude/rules/shared/agent-preamble.md`) references it as Step 0 of every task.

Quick rules:

- Worktree directory convention: `../{repo}-worktrees/{branch-slug}/`
- One agent per worktree — never assign two agents to the same worktree
- Agents must not read or write files outside their worktree
- **First action in any task**: create the worktree, `cd` into it, verify `pwd` + `git branch --show-current` before any write. If already inside a worktree (spawned by `/dispatch` / `/dispatch-task`), verify it matches the task and continue
- `board-context.md` is edited inside the worktree on the task branch and merges back via PR — there is no privileged "Atlas writes to main checkout" path
- Each worktree merges back via PR — never merge or commit directly on `main`
- Worktree cleanup is automatic: every `/create-pr` invocation sweeps all worktrees and removes any whose PR is already merged. No manual cleanup needed for the happy path. To abandon an unmerged worktree, run `git worktree remove <path> && git branch -D <branch>` from the main checkout
- This rule is also the entire parallel-session arbitration mechanism: two sessions running at the same time each get their own worktree under distinct branch names, with no shared in-flight state — no lock files or busy-checks are needed

## Conflict Resolution

- If two agents disagree on an implementation approach, the agent with domain ownership decides (e.g., Shield wins on security, Sage wins on architecture, Pixel wins on UX)
- If the disagreement crosses domains, escalate to @Atlas with both positions documented
- @Atlas mediates and, if unresolved, escalates to @Zeyad for final decision
- Never block on a disagreement for more than 4 hours — escalate

## Scope Guardrails

- Stay within the scope of your assigned story or task — do not refactor, optimize, or "improve" code outside that scope
- If you discover a bug or tech debt outside your scope, file it as a separate task for @Atlas rather than fixing it inline
- If the assigned story is underspecified, ask @Diana or @Morgan for clarification before guessing
- No gold-plating — deliver what the acceptance criteria require, not more

## Code Review Matrix

- Backend code (Flux, Pyra, Forge): reviewed by another backend agent or @Sage
- Frontend/mobile code (Nova, Swift, Kai, Link): reviewed by another frontend/mobile agent or @Sage
- KMP shared code (Link): reviewed by both @Swift and @Kai (since they consume it)
- Security-sensitive changes (auth, encryption, PII handling): must also be reviewed by @Shield regardless of domain
- Infrastructure/CI changes (Sentinel): reviewed by @Shield
- All reviews must be completed before merge. Reviewer approves or requests changes with specific actionable feedback

## Rollback & Recovery

- If a deployed change causes issues (crash spike, error rate increase, broken functionality), the first action is to revert the culprit commit: `git revert <hash>` — fix forward only after the revert is deployed
- If an agent's implementation fails tests or review and cannot be fixed promptly, revert to the last known-good state on the branch and reassign via @Atlas
- Every deployment request to @Sentinel must include a rollback plan with the specific commit hash to revert to
- After any rollback, the responsible agent must write a brief incident note in `docs/incident-notes/{Task-Id}-Incident Notes-Title.md`

## Board Context Maintenance

- `board-context.md` is the live source of truth for the Kanban board — agents must keep it updated
- When pulling a task: move it to the "In Progress" column with your name
- When blocked: add the blocker to the "Blocked" section immediately
- When completing a task: move it to "Done" with the output artifact reference
- When a key decision is made: add it to the "Decisions Log"
- @Atlas is responsible for reviewing `board-context.md` accuracy at every daily sync
- **Every board edit ships inside the PR that carries the change it describes** — committed on the task branch, never as a board-only PR and never as a commit on `main`. `→ Done` is the final pre-merge commit on the PR branch, not a post-merge step. Planning-only board edits ride with the docs they produced, or wait for the first implementation PR. Full policy: `@.claude/rules/shared/board-in-pr.md`

## Release Process

- Versioning: semantic versioning (`vMAJOR.MINOR.PATCH`). Breaking changes bump major, new features bump minor, bug fixes bump patch
- Release checklist (all must pass before @Sentinel deploys):
  1. All stories in the release are merged to `main`
  2. @Apex has signed off (handoff template #12)
  3. @Shield has approved security review for any security-sensitive changes
  4. @Scroll has updated user-facing documentation and changelog
  5. @Morgan has approved release notes
  6. @Zeyad has given final go/no-go
- Deployment order: staging → canary (5% traffic, 30 min soak) → production (gradual rollout)
- @Sentinel monitors error rates and crash-free rate during canary. Auto-rollback if error rate increases >1% or crash-free rate drops below 99.5%
- After successful production deployment, @Sentinel tags the release in git: `git tag vX.Y.Z`
- @Morgan publishes release notes. @Scroll updates documentation. @Echo prepares support for new features
- Save the release record to `docs/release-record/{Task-Id}-Release Record-vX.Y.Z.md` with: version, date, included stories, release notes, deployment timeline, and any issues encountered

## Hotfix Process

- A hotfix is triggered when a critical bug (P0/P1) is found in production that cannot wait for the next regular release
- Hotfix branch naming: `hotfix/{version}/{short-description}` (e.g., `hotfix/v1.2.1/fix-login-crash`)
- Hotfix branches are cut from the latest release tag, NOT from `main`
- Hotfix flow:
  1. @Atlas creates a P0 task and assigns it to the relevant engineer
  2. Engineer creates the hotfix branch from the release tag: `git checkout -b hotfix/vX.Y.Z/fix-description vX.Y.Z`
  3. Engineer implements the minimal fix — no feature work, no refactoring, only the fix
  4. @Shield reviews if security-related. Code review by one peer is required (but expedited — 1 hour SLA)
  5. @Apex runs a focused regression test on the affected area (not the full suite — speed matters)
  6. @Zeyad approves the hotfix
  7. @Sentinel deploys directly to production (skip canary if P0 and user impact is active)
  8. After deployment, merge the hotfix branch into both the release branch and `main` to prevent regression
- Bump the patch version: `vX.Y.Z` → `vX.Y.(Z+1)`
- The fixing engineer writes a post mortem to `docs/post-mortem/{Task-Id}-Post Mortem-Title.md` within 24 hours
- @Atlas schedules a brief retro on the hotfix to capture prevention actions

## Kanban Protocol

- Board columns: `Backlog → Ready → In Progress → Review → Blocked → Done`
- WIP limits: each agent may have at most 2 items in "In Progress" at a time. Finish before pulling new work
- Pull-based flow: agents pull tasks from "Ready" when they have capacity — @Atlas does not push assignments unless urgent (P0/P1)
- Daily sync: @Atlas runs a brief async check-in. Each agent posts: `Done | Doing | Blocked`
- Replenishment: @Atlas and @Morgan review the backlog weekly and move prioritized items to "Ready"
- Retros: @Atlas runs a retrospective after each major feature ships or monthly, whichever comes first
- Cycle time tracking: @Atlas monitors time from "In Progress" to "Done" per task. If cycle time exceeds 5 days, investigate and address blockers
