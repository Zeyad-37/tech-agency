---
name: ship-it
description: "End-to-end feature delivery: kicks off a new feature / tech task / bug fix, implements it, runs a fresh-context self-review, applies required fixes, and opens a PR ready for external review. Stops after the PR is opened — use /address-feedback to handle review comments and quality gates. Triggers: 'ship it', 'ship a feature', 'ship-it', 'deliver this', 'end to end this', 'take this to PR'."
---

# Ship It — Kickoff to PR

This skill chains the front half of the delivery loop: kickoff → implement → self-review → PR. It stops once the PR is open. The back half (addressing review comments and quality gates) is handled by `/address-feedback`.

## Step 1: Determine Work Type

Parse the user's prompt to decide which kickoff skill to invoke. Ask if ambiguous.

| User said | Kickoff |
|---|---|
| "feature: …", "add X to Y", "new feature" | `/new-feature` |
| "tech task: …", "refactor X", "improve tooling" | `/tech-task` |
| "bug: …", "X is broken", "investigate …" | `/investigate-bug` |
| "crash: …", "crash spike" | `/investigate-crash` |

If the user already has an In-Progress task on the board for this work, skip kickoff and continue from where they are. Confirm with the user before skipping.

## Step 2: Run the Kickoff

Invoke the chosen skill via the Skill tool. Follow the kickoff to its natural completion — typically that means a plan presented to the user and approved, then code written, tests passing, commits on a feature branch.

**Gate (human checkpoint):** After the plan is presented but before implementation begins, wait for explicit user approval. Do not auto-approve. This is the single most important checkpoint in the loop — it's where requirements get refined.

## Step 3: Implement and Test

Follow the implementation per the kickoff's standards. Hard requirements before moving to Step 4:

- All acceptance criteria covered by tests on the same branch
- Full test suite for affected modules passes locally
- `./gradlew detekt` (or equivalent lint for the touched stack) passes
- No `!!` in Kotlin / no force-unwraps in Swift
- Commits follow `[STORY-ID] @AgentName: description` format

If any of these fail, fix before continuing. Do not push broken code expecting the self-review or CI to catch it.

## Step 4: Update Board

Run `/update-board {TASK-ID} → Review` to move the task and commit the board change on the branch.

## Step 5: Fresh-Context Self-Review (subagent)

This is the step that replaces the manual "clear context, ask for code-review" loop. Spawn a fresh subagent that has no memory of the implementation conversation — it sees only the diff.

Use the `Agent` tool with `subagent_type: general-purpose` (or a more specific reviewer if available in the project):

```
description: "Pre-PR code review on current branch"
prompt: |
  You are performing a code review on the current branch before a PR is opened.
  You have no prior context — review only what's in the diff.

  Steps:
  1. Identify the base branch (usually `main`) and the current branch.
  2. Run: git diff main...HEAD --stat, then git diff main...HEAD for full diff.
  3. Read board-context.md to find the task ID and acceptance criteria.
  4. Locate any feature docs in docs/{prd,brd,adr,rfc,design-spec}/ matching the task ID.
  5. Apply the project's /code-review skill criteria:
     - Architecture / ADR compliance
     - Coding standards (see .claude/rules/*-coding-standards.md for the touched stack)
     - Test coverage adequacy vs acceptance criteria
     - Security (light pass — auth, input validation, secrets, PII in logs)
     - T-013 render-decision rules if Compose code is touched
     - Force-unwraps, hardcoded values, missing error states
  6. Produce a verdict: APPROVED / CHANGES REQUESTED / BLOCKED
  7. Group findings as REQUIRED (must fix before PR) and RECOMMENDED (nice to have).

  Report under 400 words. Be specific — include file:line for every finding.
```

## Step 6: Apply Required Fixes

Read the subagent's report. For every REQUIRED finding:

1. Apply the fix.
2. Re-run the relevant tests.
3. Commit per finding (or per logical group) with the standard commit format.

For RECOMMENDED findings, present them to the user and ask whether to apply now or defer. Default to applying small ones (rename, missing test) and deferring larger ones (refactors, broader cleanups) as follow-up tasks.

If the subagent returned BLOCKED, stop and surface the blocker to the user — do not open a PR.

## Step 7: Create the PR

Run `/create-pr --no-push`. This commits any uncommitted changes, runs the pre-push verification gate (Step 4b of `/create-pr`), and prepares the PR title and body — but does NOT push or call `gh pr create`. Per the project rule in `shared-standards.md`, wait for explicit user approval ("push it", "go ahead") before pushing.

After approval:
- `git push -u origin <branch>`
- `gh pr create` using the title and body `/create-pr` prepared
- Capture the PR URL and pass it to Step 8

## Step 8: Hand Off to `/address-feedback`

Print a clear handoff message:

```markdown
## ✅ Ship-It Complete

**PR:** {url}
**Branch:** {branch}
**Task:** {task-id} — {description}
**Self-review:** {n} required fixes applied, {n} recommended deferred

### Next Step

External review will run automatically (CI, Copilot, human reviewers).
When feedback is in, run:

    /address-feedback

Add `--auto-merge` if you want it to merge once everything is green and resolved:

    /address-feedback --auto-merge
```

Stop. Do not begin polling for feedback in this session.

## Notes

- This skill stops at PR creation by design. The wait for external review is wall-clock minutes-to-hours; tying up a session polling for it wastes tokens and gives no value over running `/address-feedback` when you're ready.
- If the user wants the back half automated event-driven (e.g., Copilot finishes → auto-respond), that lives in `.github/workflows/`, not in this skill.
