---
name: ship-it
description: "End-to-end feature delivery as a pure composition of the agency's skills: kicks off a new feature / tech task / bug fix, implements it, opens a PR (/create-pr), then reviews and addresses all feedback (/review-and-address) — merging automatically when --auto-merge is passed and all quality gates pass. Triggers: 'ship it', 'ship a feature', 'ship-it', 'deliver this', 'end to end this', 'take this to PR', 'take this all the way'."
---

# Ship It — Kickoff to Merge

This skill chains the **entire** delivery loop as a thin composition of existing skills — it re-implements none of their logic:

```
kickoff (/new-feature | /tech-task | /investigate-bug | /investigate-crash)
  → implement & test
  → /update-board → Review
  → /ship-pr   (── /create-pr ──→ /review-and-address ──→ merge)
```

The back half — open PR, review, address, merge — is entirely `/ship-pr`. So the code review is **not** done inline here: it happens downstream inside `/review-and-address` (Phase 1 runs `/code-review` against the open PR and posts the verdict). There is no separate pre-PR self-review step — the PR is opened first, then reviewed and addressed from a clean context.

**`--auto-merge`:** pass it to `/ship-it` and it is forwarded straight to `/ship-pr` (and on to `/review-and-address`), which merges the PR once all quality gates are green. Without the flag, the run stops at the merge gate for a human decision.

**Push authorization:** per `@.claude/rules/shared/shared-standards.md`, **invoking `/create-pr` or `/ship-pr` IS the push authorization for that branch.** Outside those skills, never run a bare `git push`, and never push to `main`. `/ship-it` itself pushes nothing: the single human checkpoint for going public lives in `/ship-pr` Step 2, which then invokes `/create-pr` on its default auto-push path. So there is exactly one gate on this route, and passing it authorizes the push — `/create-pr` does not ask again, and asking again would contradict it.

## Step 1: Determine Work Type

First, note whether the user passed **`--auto-merge`** — it is not consumed here, only carried through to `/ship-pr` (and on to `/review-and-address`) in Step 5.

Then parse the user's prompt to decide which kickoff skill to invoke. Ask if ambiguous.

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

If any of these fail, fix before continuing. Do not push broken code expecting the downstream `/review-and-address` pass or CI to catch it.

## Step 4: Update Board

Run `/update-board {TASK-ID} → Review` to move the task and commit the board change on the branch.

## Step 5: Take the Branch to Merge (`/ship-pr`)

The branch now has the implemented work committed and the board updated, but no PR yet — exactly the entry condition `/ship-pr` expects. Hand it off:

Invoke **`/ship-pr`**, forwarding `--auto-merge` if the user passed it to `/ship-it`. `/ship-pr` owns the entire open → review → address → merge tail, and ship-it re-implements none of it:

- collects the **single push-approval checkpoint** (Step 2), after which invoking `/create-pr` is itself the push authorization,
- runs `/create-pr` (rebase, screenshots, verification gate, push, `gh pr create`, **Copilot request**, worktree sweep),
- runs `/review-and-address` (`/code-review` → background Copilot wait → `/address-feedback`),
- merges under `--auto-merge` once all gates are green, or stops at the merge gate otherwise.

Do not pass any session narrative — hand `/ship-pr` only the `--auto-merge` flag. If `/ship-pr` aborts (rebase conflict, failed verification gate, or — unexpectedly — an existing PR for this branch), surface its reason and stop.

## Step 6: Report

Relay `/ship-pr`'s final report verbatim under a ship-it header so the whole run reads as one:

```markdown
## ✅ Ship-It Complete

**PR:** {url}
**Branch:** {branch}
**Task:** {task-id} — {description}
**Review:** verdict {APPROVED / CHANGES REQUESTED} — posted to PR
**Feedback:** {n} required applied, {n} recommended applied/deferred, checks {GREEN/RED}
**Outcome:** {merged / awaiting merge gate / blocked on {reason}}
```

## Notes

- **Pure composition.** ship-it re-implements nothing. Its front half routes to a kickoff skill and `/update-board`; its back half is entirely `/ship-pr` (which is itself just `/create-pr` + `/review-and-address`). ship-it owns only the kickoff/implement gate and the `--auto-merge` hand-through. If any downstream skill changes, ship-it inherits it for free.
- **ship-it vs `/ship-pr`.** They differ by exactly the front end: `/ship-it` kicks off and implements, then delegates the rest to `/ship-pr`; run `/ship-pr` directly when the code is already written and committed on a branch with no PR yet.
- **One Copilot requester.** The Copilot review is requested in exactly one place — `/create-pr` Step 5b, reached via `/ship-pr` — so every PR opened through ship-it gets it, and `/review-and-address` only waits for it (it does not request). Don't re-add a request anywhere in this chain.
- **Not idle while waiting for Copilot.** The external-review wait is absorbed by `/review-and-address`'s background poll (the harness re-invokes on exit), so the session isn't tied up burning turns. This is why ship-it can run all the way to merge instead of stopping at PR-open.
- **Fully unattended runs** (e.g., Copilot finishes → auto-respond with no session open) still belong in a `.github/workflows/` webhook, not here — use `--auto-merge` for in-session end-to-end, that workflow for away-from-keyboard.
