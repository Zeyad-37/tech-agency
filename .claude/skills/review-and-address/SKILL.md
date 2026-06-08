---
name: review-and-address
description: "End-to-end PR close-out in two clean-context phases: first runs a fresh-context code review and posts the verdict to the PR, then addresses all resulting feedback (the posted review + any external review comments + failing checks), applies fixes, pushes, and watches checks until green. Each phase starts from a clean context so neither the review nor the fix work is biased by the current session. Pass --auto-merge to merge automatically once green. Use after a PR exists and you want it reviewed and driven to mergeable in one command. Triggers: 'review and address', 'review and resolve', 'review then fix', 'close out this PR', 'review and land', 'land this PR', 'finish this PR end to end'."
---

# Review and Address — Review a PR, Then Address All Feedback

This skill closes out a PR in two phases, each starting from a **clean context** so bias from the current session never leaks in:

1. **Review** — run `/code-review` on the PR. It self-isolates in a fresh-context subagent (diff-only, no session memory) and posts its verdict directly to the PR.
2. **Address** — run `/address-feedback` on the same PR. Its bias-sensitive work also self-isolates in a fresh-context subagent. It gathers *every* source of feedback — including the review just posted — applies fixes, pushes, and watches checks.

This skill is a thin orchestrator. It does **not** re-implement the review or the fix logic — it sequences the two child skills and passes the PR target and flags through. The clean-context guarantee comes from each child's own Step 0; this skill must not inject any "what we did / why" narrative from the session into either phase.

It assumes a PR already exists. To go from nothing → implemented → PR, use `/ship-it` first, then this skill.

## Step 1: Parse Arguments

From the user's prompt, resolve:

- **PR number / branch** — e.g. `#123` or `123`. If absent, infer from the current branch:
  ```bash
  gh pr view --json number,url,headRefName,baseRefName
  ```
  If no PR exists for the current branch, stop and tell the user — this skill needs an open PR. Suggest `/create-pr` (or `/ship-it`) first.
- **`--auto-merge` flag** — passed straight through to Phase 2 (`/address-feedback`). If present, Phase 2 auto-approves its fix plan and merges once everything is green. If absent, Phase 2 stops at its final merge gate.

Confirm in one line, then proceed:

```
Review & Address → PR #123 (branch: feature/foo)  |  Auto-merge: ON/OFF
```

## Step 2: Phase 1 — Review (clean context)

Invoke the `/code-review` skill targeting the resolved PR/branch.

- `/code-review` Step 0 spawns its own fresh-context subagent that sees only the diff and committed docs, performs Steps 1–9, and **posts the verdict directly to the PR** (approve / request-changes, with the findings in the body).
- Pass it only the review target (PR number or branch). Do **not** pass any session rationale.
- Relay the returned verdict to the user verbatim — do not soften or second-guess it.

Capture the verdict for Step 3's branch decision: `APPROVED`, `CHANGES REQUESTED`, or `BLOCKED`.

## Step 3: Decide Whether to Continue to Phase 2

The review is now on the PR. Decide how to proceed:

- **Verdict was APPROVED and there is no other open feedback or failing check** — there may be nothing for Phase 2 to do. Still run Phase 2 (it is cheap and authoritative): `/address-feedback` re-derives the full feedback set fresh and will simply report "zero required items" and drop to its merge gate. This keeps the merge decision in one place.
- **Verdict was CHANGES REQUESTED or BLOCKED** — proceed to Phase 2 to address it.
- **The review hit the self-review fallback** (GitHub rejects approving/requesting-changes on your own PR, so `/code-review` posted the verdict as a regular issue comment instead) — that comment is still feedback. Phase 2's gathering step (`/address-feedback` Step 3b, issue-level comments) picks it up. Proceed normally.

If `--auto-merge` is **off**, briefly confirm with the user before starting Phase 2:

```
Review posted (verdict: CHANGES REQUESTED). Proceed to address all feedback now? (y/n)
```

If `--auto-merge` is **on**, proceed without asking.

## Step 4: Phase 2 — Address (clean context)

Invoke the `/address-feedback` skill targeting the same PR, forwarding the `--auto-merge` flag if it was set.

`/address-feedback` runs its own Step 0 fresh-context flow:

- **Subagent pass A** (fresh): gather all feedback — the review verdict posted in Phase 1, any external/human/bot review comments, and failing checks — classify and plan.
- **Parent relays** the plan-confirmation gate to the user (auto-approved under `--auto-merge`).
- **Subagent pass B** (fresh): apply fixes, reply to threads, push, watch checks (loops on new failures, cap 3).
- **Parent relays** the merge gate and performs the mechanical merge + cleanup (auto under `--auto-merge`).

Do not pass session narrative into `/address-feedback` either — hand it only the PR number and the flag.

## Step 5: Report

Summarize the full run:

```markdown
## Review & Address — PR #{n}

**Phase 1 (Review):** verdict {APPROVED / CHANGES REQUESTED / BLOCKED} — posted to PR
**Phase 2 (Address):** {required fixes applied} applied, {recommended} applied/deferred, checks {GREEN/RED}
**Outcome:** {merged / awaiting merge gate / blocked on {reason}}
```

Each phase ran from a clean context: the Phase 1 verdict was produced with no session memory, and the Phase 2 fixes were judged with no session memory — so neither the review nor the fix work was biased by this conversation.

## Notes

- **Why two phases instead of one big subagent:** the review must be posted to the PR *before* feedback is gathered, so that Phase 2 sees the review as one of its inputs. Folding them into a single context would also re-introduce the bias this skill exists to prevent — the agent that wrote the review would then be the one judging how to address it.
- **Relationship to `/ship-it`:** `/ship-it` takes implemented code → self-review → fixes → **opens** a PR and stops. `/review-and-address` starts from an **existing** PR and takes it review → addressed → mergeable. They compose: `/ship-it` to open, then `/review-and-address` to close out.
- **Idempotent:** safe to re-run on the same PR. Phase 1 posts a fresh review; Phase 2 re-derives feedback from the live PR state each time.
