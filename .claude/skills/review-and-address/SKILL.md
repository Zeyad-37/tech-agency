---
name: review-and-address
description: "End-to-end PR close-out in two clean-context phases: first runs a fresh-context code review and posts the verdict to the PR, then addresses all resulting feedback (the posted review + any external review comments + failing checks), applies fixes, pushes, and watches checks until green. Each phase starts from a clean context so neither the review nor the fix work is biased by the current session. Pass --auto-merge to merge automatically once green. Use after a PR exists and you want it reviewed and driven to mergeable in one command. Triggers: 'review and address', 'review and resolve', 'review then fix', 'close out this PR', 'review and land', 'land this PR', 'finish this PR end to end'."
---

# Review and Address — Review a PR, Then Address All Feedback

This skill closes out a PR in two phases, each starting from a **clean context** so bias from the current session never leaks in:

1. **Review** — run `/code-review` on the PR. It self-isolates in a fresh-context subagent (diff-only, no session memory) and posts its verdict directly to the PR.
2. **Address** — run `/address-feedback` on the same PR. Its bias-sensitive work also self-isolates in a fresh-context subagent. It gathers *every* source of feedback — including the review just posted — applies fixes, pushes, and watches checks.

This skill is a thin orchestrator. It does **not** re-implement the review or the fix logic — it sequences the two child skills and passes the PR target and flags through. The clean-context guarantee comes from each child's own Step 0; this skill must not inject any "what we did / why" narrative from the session into either phase.

Between the two phases it also handles the **external Copilot review**. Copilot is *not* requested here — it was already requested upstream when the PR was opened (`/create-pr` Step 5b is the single Copilot requester), and Copilot auto-re-reviews on every push. This skill only **waits** for that review to land: it records the current-HEAD baseline up front, then runs a short data-driven background poll before Phase 2 so `/address-feedback`'s single gather pass actually sees Copilot's comments (instead of missing them and forcing a re-run). The poll runs in the background, so no conversation turns are burned sitting idle.

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

## Step 2: Capture the Copilot Review Baseline (parallel with Phase 1)

Copilot's review latency on this org's PRs is tightly clustered — **median ~4m, P90 ~6m, max observed ~9m** (measured across 64 PRs on `Zeyad-37/Steady`). The request that triggers that review is **not** issued here — `/create-pr` (Step 5b) already requested Copilot when the PR was opened, and Copilot re-reviews automatically on every push. This skill's job is only to *wait* for the review for the current HEAD, and to let that wait overlap Phase 1 instead of becoming idle time.

So capture the review baseline now — the latest commit time. Because Copilot re-reviews on every push, the wait gate (Step 5) must key on a review submitted **after the current HEAD**, not just "any Copilot review":

```bash
PR={n}; REPO={owner}/{repo}
HEAD_TIME=$(gh pr view "$PR" --repo "$REPO" --json commits --jq '.commits[-1].committedDate')
```

Carry `HEAD_TIME` forward to Step 5. Do not block here — move straight to Phase 1, so Copilot's latency elapses *while* `/code-review` does its work.

> If this skill is ever run on a PR that was **not** opened via `/create-pr` (so Copilot was never requested), the Step 5 poll will simply hit its `COPILOT_REVIEW_TIMEOUT` path and ask the user how to proceed — no review is silently lost. Re-open the PR through `/create-pr`, or request Copilot manually, if you need the review.

## Step 3: Phase 1 — Review (clean context)

Invoke the `/code-review` skill targeting the resolved PR/branch.

- `/code-review` Step 0 spawns its own fresh-context subagent that sees only the diff and committed docs, performs Steps 1–9, and **posts the verdict directly to the PR** (approve / request-changes, with the findings in the body).
- Pass it only the review target (PR number or branch). Do **not** pass any session rationale.
- Relay the returned verdict to the user verbatim — do not soften or second-guess it.

Capture the verdict for Step 4's branch decision: `APPROVED`, `CHANGES REQUESTED`, or `BLOCKED`.

## Step 4: Decide Whether to Continue to Phase 2

The review is now on the PR. Decide how to proceed:

- **Verdict was APPROVED and there is no other open feedback or failing check** — there may be nothing for Phase 2 to do. Still run Phase 2 (it is cheap and authoritative): `/address-feedback` re-derives the full feedback set fresh and will simply report "zero required items" and drop to its merge gate. This keeps the merge decision in one place.
- **Verdict was CHANGES REQUESTED or BLOCKED** — proceed to Phase 2 to address it.
- **The review hit the self-review fallback** (GitHub rejects approving/requesting-changes on your own PR, so `/code-review` posted the verdict as a regular issue comment instead) — that comment is still feedback. Phase 2's gathering step (`/address-feedback` Step 3b, issue-level comments) picks it up. Proceed normally.

If `--auto-merge` is **off**, briefly confirm with the user before waiting on Copilot and starting Phase 2:

```
Review posted (verdict: CHANGES REQUESTED). Wait for Copilot, then address all feedback now? (y/n)
```

If `--auto-merge` is **on**, proceed without asking.

## Step 5: Wait for Copilot's Review (data-driven poll)

Phase 1 has now run, so several minutes have already elapsed against Copilot's ~4m median — often its review for this HEAD is already in. Confirm it (or wait out the remainder) before handing to Phase 2, so `/address-feedback`'s single gather pass sees Copilot's comments.

Run the poll as a **background** command so no conversation turns are spent idling — the harness re-invokes you the instant it exits:

```bash
PR={n}; REPO={owner}/{repo}; HEAD_TIME="{from Step 2}"
INITIAL=60; INTERVAL=30; TIMEOUT=600       # tuned to the measured distribution
deadline=$(( $(date +%s) + TIMEOUT )); first=1
while [ "$(date +%s)" -lt "$deadline" ]; do
  # Check first — if Copilot already reviewed this HEAD (e.g. auto-review on push),
  # pass immediately instead of waiting out INITIAL.
  hit=$(gh api "repos/$REPO/pulls/$PR/reviews" \
        | jq --arg t "$HEAD_TIME" \
          '[.[] | select(.user.login=="copilot-pull-request-reviewer[bot]" and .submitted_at > $t)] | length')
  if [ "${hit:-0}" -gt 0 ]; then echo "COPILOT_REVIEW_READY"; exit 0; fi
  if [ "$first" = 1 ]; then sleep "$INITIAL"; first=0; else sleep "$INTERVAL"; fi
done
echo "COPILOT_REVIEW_TIMEOUT"; exit 0
```

Schedule rationale (from the 64-PR sample): first check at **60s** catches the fast returns (a handful land in 1–2m); the **30s** cadence stays tight through the 3–6m cluster where ~84% land; the **600s** timeout sits comfortably past the 8m50s max, so a non-arrival by then is a real signal (Copilot disabled / errored), not "still thinking." These three constants are the only knobs — re-measure and adjust them if the distribution shifts.

- **`COPILOT_REVIEW_READY`** → proceed to Phase 2.
- **`COPILOT_REVIEW_TIMEOUT`** → Copilot is overdue past its historical max, which almost always means it's broken / disabled / not-requestable rather than just slow. **Notify the user and halt for their decision — in both modes, including `--auto-merge`.** The background poll exists precisely because the user has stepped away, so a chat-only prompt isn't enough; pull their attention back with a push notification, then wait. Send it with the `PushNotification` tool:

  ```
  PushNotification(
    status="proactive",
    message="PR #{n}: Copilot review didn't arrive in 10m (likely disabled/broken). Address without it, keep waiting, or abort?")
  ```

  Then present the same three options in chat and wait for the answer: **(a)** proceed to Phase 2 without Copilot — safe, since this skill is idempotent and a later Copilot review can be addressed by re-running; **(b)** keep waiting another poll cycle; **(c)** abort. **`--auto-merge` does not bypass this halt** — a timeout is exactly when an unattended merge must not happen: Copilot reviews are advisory (always `COMMENTED` state in practice, never a blocking `CHANGES_REQUESTED`), so auto-merging on Copilot's silence would ship without its comments ever being addressed and with no second chance once the PR is merged. Auto-merge resumes its autonomy only after the user picks (a).

## Step 6: Phase 2 — Address (clean context)

Invoke the `/address-feedback` skill targeting the same PR, forwarding the `--auto-merge` flag if it was set.

`/address-feedback` runs its own Step 0 fresh-context flow:

- **Subagent pass A** (fresh): gather all feedback — the review verdict posted in Phase 1, any external/human/bot review comments, and failing checks — classify and plan.
- **Parent relays** the plan-confirmation gate to the user (auto-approved under `--auto-merge`).
- **Subagent pass B** (fresh): apply fixes, reply to threads, push, watch checks (loops on new failures, cap 3).
- **Parent relays** the merge gate and performs the mechanical merge + cleanup (auto under `--auto-merge`).

Do not pass session narrative into `/address-feedback` either — hand it only the PR number and the flag.

## Step 7: Report

Summarize the full run:

```markdown
## Review & Address — PR #{n}

**Phase 1 (Review):** verdict {APPROVED / CHANGES REQUESTED / BLOCKED} — posted to PR
**Copilot:** {review arrived in {m}m{s}s / timed out after 10m — user notified, chose {proceed without / kept waiting / aborted}}
**Phase 2 (Address):** {required fixes applied} applied, {recommended} applied/deferred, checks {GREEN/RED}
**Outcome:** {merged / awaiting merge gate / blocked on {reason}}
```

Each phase ran from a clean context: the Phase 1 verdict was produced with no session memory, and the Phase 2 fixes were judged with no session memory — so neither the review nor the fix work was biased by this conversation.

## Notes

- **Why two phases instead of one big subagent:** the review must be posted to the PR *before* feedback is gathered, so that Phase 2 sees the review as one of its inputs. Folding them into a single context would also re-introduce the bias this skill exists to prevent — the agent that wrote the review would then be the one judging how to address it.
- **Relationship to `/ship-it`:** `/ship-it` now runs end-to-end — kickoff → implement → `/ship-pr`, which **opens** the PR (`/create-pr`) and then invokes `/review-and-address` to review, address, and merge. `/review-and-address` is the close-out for an **existing** PR. They still compose: `/ship-it`/`/ship-pr` reach this skill as their back half, and you can also run `/review-and-address` directly against any PR that already exists.
- **Idempotent:** safe to re-run on the same PR. Phase 1 posts a fresh review; Phase 2 re-derives feedback from the live PR state each time.
- **Why capture the baseline early then poll, instead of just polling:** Copilot was requested upstream by `/create-pr` at PR-open time, so its ~4m latency is already running *concurrently* with Phase 1's review work — by the time Step 5's gate runs the review is usually already in, and the poll then confirms rather than waits. Recording `HEAD_TIME` in Step 2 is what lets the poll key on a review `submitted_at` newer than the current HEAD commit, because Copilot re-reviews on every push; matching "any Copilot review" would falsely pass on a stale review from an earlier push. This skill does **not** request Copilot itself — `/create-pr` Step 5b is the single requester, so every PR-open path funnels through one place.
- **Background, not idle:** Step 5 runs as a backgrounded Bash loop. The harness re-invokes the agent when it exits, so the gap between "baseline captured" and "Phase 2 starts" collapses to Copilot's actual turnaround with zero turns burned polling-and-rechecking. This is the in-session, no-CI alternative to the GitHub Actions webhook approach (`pull_request_review` → headless Claude) noted in `address-feedback`'s Notes; use that workflow instead when the close-out must run while you're away from the session.
