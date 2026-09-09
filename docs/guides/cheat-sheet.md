# Prompting Cheat Sheet

## Before Anything Else

Install the plugin, then bootstrap the project. **Both steps are required.**

```bash
claude plugin marketplace add github:Zeyad-37/tech-agency --scope user
claude plugin install tech-agency@tech-agency --scope user
```

Then, in Claude Code from your project root:

```
/setup-repo
```

followed by `./hooks/install-hooks.sh`. Until `/setup-repo` runs, you have agents and skills but no
board, no git hooks, no sandbox, and none of the shared policy rules in context. Full walkthrough:
`../setup-guide.md`.

---

## Command Index

34 first-party commands ship with the plugin. Full documentation:
[`commands-reference.md`](commands-reference.md).

| Group | Commands |
|---|---|
| Planning | `/new-product` `/new-feature` `/write-prd` `/tech-task` `/rfc` |
| Board & flow | `/kick-off` `/daily-sync` `/pick-up-task` `/update-board` `/migrate-board` `/replenish` `/sprint-report` `/retro` |
| Parallel | `/dispatch` `/dispatch-task` |
| Ship | `/ship-it` `/ship-pr` `/create-pr` `/code-review` `/review-and-address` `/address-feedback` `/capture-screenshots` `/lint-changed` |
| Diagnose | `/investigate-bug` `/investigate-crash` `/postmortem` `/hotfix` `/health-check` |
| Maintain | `/setup-repo` `/onboard-agent` `/dependency-upgrade` `/extract-library` `/sync-rule` `/release` `/audit-memory` |

Plus 14 vendored skills — `/android-*` (Google) and `/kotlin-*` (JetBrains) — for Compose theming,
adaptive layout, Navigation 3, edge-to-edge, R8, Perfetto traces, JPA mapping, Java→Kotlin, and the
AGP 9 / SPM migrations.

---

## Starting a New Product

The entry point is always Morgan. Describe what you want, who it's for, and which platforms.

```
I want to build [what it is] for [who]. It should [core capabilities].
Target platforms: [iOS/Android/Web/all via KMP].
Start with Morgan to write the PRD.
```

**Example:**
```
I want to build a habit tracker for health-conscious adults. It should let users
create daily habits, track streaks, get reminders, and see weekly progress charts.
Target platforms: iOS and Android via KMP, with a web dashboard.
Start with Morgan to write the PRD.
```

After Morgan produces the PRD, you approve it, then the chain flows naturally:
Morgan (PRD) → Diana (BRD) → Sage (ADR) → Pixel (design) → Engineers → QA → Deploy

---

## Starting a New Feature (on an existing product)

Skip Morgan if you already know the requirements. Go straight to Diana or Sage.

```
Using Diana, write a BRD for adding [feature] to [product].
Context: [what exists today, what's changing, why].
```

**Example:**
```
Using Diana, write a BRD for adding social sharing to the habit tracker.
Context: Users currently track habits privately. We want them to share
streaks with friends via a feed. This needs a new social graph and feed API.
```

---

## Assigning a Specific Engineering Task

Point directly at the agent you need. Include the story ID, reference any existing docs.

```
Using [agent], implement [what]. User story: [ID]: [description].
Refer to docs/[feature]/[relevant-doc].md for context.
```

**Examples:**

```
Using Link, create a KMP module for habit streak calculation.
User story US-012: As a user I want to see my current streak for each habit.
Refer to docs/habit-tracker/adr-003.md for the data model.
```

```
Using Kai, implement the streak screen in Compose.
User story US-013: As a user I want to see a visual streak calendar.
Refer to docs/habit-tracker/design-spec.md for Pixel's component spec
and docs/habit-tracker/adr-003.md for the data model.
```

```
Using Flux, implement POST /api/v1/habits with validation, DB insert, and streak initialization.
User story US-008. Refer to docs/habit-tracker/adr-002.md for the API contract.
```

---

## Parallel Work (Dispatch)

Run independent tasks simultaneously — each in its own git worktree, branch, and PR.

```
/dispatch @Kai implement the streak screen (US-013)
/dispatch @Flux implement the habits API (US-008)
```

Working inside an epic? Point the dispatch at the epic's integration branch — the worktree
branches off it and the PR merges back into it (not `main`):

```
/dispatch --base epic/US-100-checkout @Kai implement the checkout summary screen
```

Need planning first? `/dispatch-task` runs the planning chain (tech-task, new-feature,
investigate-bug, or investigate-crash), waits for your approval, then dispatches the
resulting implementation tasks in parallel:

```
/dispatch-task --type tech-task "migrate all screens to the new design tokens"
/dispatch-task --type new-feature --base epic/US-100-checkout "add promo codes to checkout"
```

---

## Architecture & Design

```
Using Sage, design the system architecture for [feature/product].
Requirements: [summary or reference to BRD].
Key constraints: [scale, latency, platforms, compliance].
```

```
Using Sage, write an ADR for choosing between [option A] vs [option B].
Context: [why this decision matters, what's at stake].
```

```
Using Pixel, design the [screen/flow] for [feature].
Target platforms: [iOS/Android/Web].
Refer to docs/[feature]/brd.md for user stories.
```

---

## Board Management (Atlas)

```
Set up the board for [feature name]
```

```
Run daily sync
```

```
Replenish the backlog
```

```
Run retrospective
```

---

## Quality & Security

```
Using Apex, write a test plan for [feature].
Cover: [specific areas — happy path, edge cases, performance, accessibility].
Refer to docs/[feature]/brd.md for acceptance criteria.
```

```
Using Shield, review the auth implementation in [PR/branch/module].
Focus on: [OWASP top 10 / data handling / dependency vulnerabilities].
```

```
Using Apex, sign off on release vX.Y.Z.
Run regression suite and report results.
```

---

## Operations & Incidents

```
There's a crash spike on [platform] affecting [screen/feature].
Use the crash investigation protocol.
```

```
Using Sentinel, deploy vX.Y.Z to staging.
Rollback plan: revert to [commit hash].
```

```
Using Sentinel, set up monitoring for [new service].
Define SLOs: [availability target, latency P99, error rate].
```

---

## Documentation & Support

```
Using Scroll, write API documentation for [service/module].
Source: docs/[feature]/openapi-spec.yaml
```

```
Using Scroll, write a user guide for [feature].
Audience: [end users / developers / operators].
```

```
Using Echo, compile customer feedback from the last [time period].
Categorize by: feature requests, bugs, UX complaints.
```

---

## Release

```
Using Morgan, write release notes for vX.Y.Z.
Included stories: [list or reference to board].
```

```
Release vX.Y.Z. Run the full release checklist.
```

---

## Hotfix

```
Critical bug in production: [description]. Trigger the hotfix process.
Affected version: vX.Y.Z. Affected platform: [iOS/Android/Web/API].
```

---

## Shipping a Change End to End

Once code is written on a branch, one command takes it to merged:

```
/ship-pr
```

It opens the PR, runs a fresh-context code review, addresses every resulting comment and failing
check, and stops at a final approval gate. Add `--auto-merge` to merge as soon as everything is
green. `/ship-it` is the same thing with the kickoff and implementation on the front:

```
/ship-it --auto-merge add a dark mode toggle to settings
```

**Invoking `/create-pr` or `/ship-pr` is itself the authorization to push that branch** — you will
not be asked again. Nothing ever pushes to `main`.

---

## Tips

- **You are the approval gate.** Every document (PRD, BRD, ADR, RFC, design spec, security review) waits for your sign-off before the next agent acts. Review and approve quickly to keep flow moving.
- **Reference existing docs.** The more context you give (story IDs, doc paths, ADR numbers), the less back-and-forth.
- **For big features, start with an RFC.** Tell any engineer: "This is an epic — write an RFC first before coding."
- **Use Atlas for coordination.** If you're unsure who should do what, ask Atlas: "Break down [feature] into tasks and assign agents."
- **Check the board.** Run "daily sync" periodically to see where things stand and catch blockers early.
- **Expect a worktree.** Every task creates its own git worktree at `../{repo}-worktrees/{branch-slug}/` before its first write. Agents will not work in the main checkout — that is the mechanism that lets several sessions run in parallel safely.
- **Expect `main` to look idle.** Board transitions commit on the task branch and only reach `main` when the PR merges, so the merged "In Progress" column under-reports in-flight work. Use `gh pr list` for live state.
