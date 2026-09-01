---
name: ship-pr
description: "Take an already-implemented branch all the way to merged, as a pure composition of two skills: opens the PR (/create-pr), then reviews and addresses all feedback (/review-and-address) — merging automatically when --auto-merge is passed and all quality gates pass. Use when the code is already written and committed on a branch but no PR exists yet. This is /ship-it without the kickoff/implement front end. Triggers: 'ship pr', 'ship-pr', 'open and close this PR', 'take this branch to merge', 'PR this and review it', 'create PR and review'."
---

# Ship PR — Open a PR, Then Review and Address to Merge

This skill takes a **ready branch** (code already implemented and committed, no PR yet) all the way to merged, as a thin composition of two existing skills — it re-implements none of their logic:

```
/create-pr            (opens the PR; requests Copilot; screenshots; worktree sweep)
  → /review-and-address   (code-review → wait for Copilot if available → address feedback → merge)
```

It is `/ship-it` minus the kickoff and implementation steps. Reach for `/ship-pr` when the work is already done on the branch and you just want it opened, reviewed, addressed, and (optionally) merged. If you still need to kick off and write the feature, use `/ship-it`. If a PR **already exists**, skip this and use `/review-and-address` directly.

**`--auto-merge`:** pass it to `/ship-pr` and it is forwarded straight to `/review-and-address`, which merges the PR once all quality gates are green. Without the flag, the run stops at `/review-and-address`'s merge gate for a human decision. The flag is autonomy over the *gates*, not over the *trust boundary*: `/address-feedback` disables it automatically if the feedback set includes untrusted input (issue-level comments, non-write-access authors, or text flagged as a possible injection), and the run then takes the manual gate. Forwarding the flag is not a guarantee of an unattended merge.

**`--base <branch>`:** forwarded to `/create-pr`, which resolves and validates it (Pre-flight 0). Pass it when the PR should target an epic integration branch rather than the repo default.

**Push authorization:** per `@.claude/rules/shared/shared-standards.md`, **invoking `/create-pr` or `/ship-pr` IS the push authorization for that branch.** Outside those skills, never run a bare `git push`, and never push to `main`. `/ship-pr` collects the human checkpoint **once**, at the PR-open gate (Step 2); passing it authorizes the push, and `/create-pr` then runs on its default auto-push path without asking again.

## Step 1: Parse Arguments and Preflight

Note whether the user passed **`--auto-merge`** — it is not consumed here, only carried through to `/review-and-address` in Step 3. Note any **`--base <branch>`** too: it is not resolved here (that is `/create-pr`'s Pre-flight 0), but it must be forwarded in Step 2 and it changes what "commits to ship" means in guard 2.

Then confirm the branch is actually in the right shape for this skill:

```bash
# Parse the flags this skill forwards. --auto-merge is carried to Step 3;
# --base is carried to Step 2 and decides which range guard 2 counts.
BASE_FLAG=""
AUTO_MERGE="no"
while [ $# -gt 0 ]; do
  case "$1" in
    --base)
      # Check $# BEFORE `shift 2` — a bare trailing `--base` otherwise makes
      # `shift 2` fail without shifting, and the loop never terminates.
      [ $# -ge 2 ] && [ -n "$2" ] || { echo "❌ --base requires a branch name."; exit 1; }
      BASE_FLAG="$2"; shift 2 ;;
    --base=*)
      BASE_FLAG="${1#--base=}"
      [ -n "$BASE_FLAG" ] || { echo "❌ --base= requires a branch name."; exit 1; }
      shift ;;
    --auto-merge) AUTO_MERGE="yes"; shift ;;
    *)            shift ;;
  esac
done

BRANCH=$(git branch --show-current)
DEFAULT=$(git remote show origin | sed -n 's/.*HEAD branch: //p')
[ -n "$DEFAULT" ] || DEFAULT=main

# The branch this PR would target: an explicit --base wins, else the repo default.
# /create-pr re-resolves this authoritatively (including the epic gate); here it
# only decides which range guard 2 counts.
TARGET="${BASE_FLAG:-$DEFAULT}"
git fetch origin "$TARGET"

# Guard 1: not on the target branch.
[ "$BRANCH" = "$TARGET" ] && { echo "On $TARGET — create a feature branch first."; exit 1; }

# Guard 2: there are commits to ship.
# TWO dots. `rev-list A..B` counts commits reachable from B but not A — i.e.
# exactly this branch's commits since the merge base, which is what we want.
# THREE dots would be the *symmetric difference* and would add every commit the
# base has moved by, reporting "7 commits to ship" for a 2-commit branch.
# (The three-dot = merge-base shorthand holds for `git diff`, NOT for rev-walks.)
AHEAD=$(git rev-list --count "origin/$TARGET..HEAD" 2>/dev/null || echo 0)
[ "$AHEAD" -eq 0 ] && { echo "⚠️  No commits ahead of $TARGET — nothing to open a PR for."; exit 1; }

# Guard 3: no PR exists yet for this branch.
EXISTING=$(gh pr view "$BRANCH" --json number,url --jq '.number' 2>/dev/null)
```

- **A PR already exists** (`EXISTING` is non-empty) — stop and redirect: this skill opens a *new* PR. Tell the user to run `/review-and-address` directly on PR #`{EXISTING}` instead.
- **No commits ahead** — stop and tell the user; there is nothing to ship.
- **Otherwise** — proceed.

Confirm in one line:

```
Ship PR → branch {branch} ({AHEAD} commits) → {TARGET}  |  Auto-merge: ON/OFF
```

## Step 2: Open the PR (`/create-pr`)

**Push gate (the single human checkpoint):** present a one-line summary and wait for "push it" / "go ahead":

```
Ready to open PR for {task-id} — {AHEAD} commits on {branch}. Push and open the PR? (y/n)
```

This is the only approval collected on this route. Once given, invoking `/create-pr` **is** the push authorization — it does not re-prompt, and `/ship-pr` must not add a second gate before it.

On approval, invoke **`/create-pr`** on the default auto-push path — do **not** pass `--no-push`. (`--no-push` is a human-only escape hatch with no downstream consumer; taking it here would strand the run with a prepared-but-unpushed PR and nothing to complete it.) Forward `--base` if the user gave one. That single call owns everything PR-open:

- parses its flags (Pre-flight −1) and resolves the PR base (Pre-flight 0: `--base` flag → auto-detected epic integration branch, **which stops and asks before being used** → repo default branch) and rebases onto it if behind,
- captures before/after screenshots for any UI changes,
- runs the pre-push verification gate (iOS compile / host tests / screenshot-test compile),
- pushes the branch and runs `gh pr create` with the standard template,
- **requests the Copilot review** (its Step 5b — the single Copilot requester in the whole flow),
- sweeps any merged worktrees.

Capture the PR number / URL it reports and carry it to Step 3. If `/create-pr` aborts (rebase conflict or a failed verification gate), stop and surface the reason — do not proceed to Step 3.

## Step 3: Review and Address (`/review-and-address`)

Invoke **`/review-and-address`** against the PR just opened, forwarding `--auto-merge` if the user passed it to `/ship-pr`. This is the entire close-out, and it runs each phase from a clean context:

- **Phase 1 — Review:** runs `/code-review` against the open PR and posts the verdict.
- **Copilot wait (optional, availability-keyed):** records the HEAD baseline, probes whether Copilot is actually available for the repo, and background-polls for its review (already requested by `/create-pr` in Step 2) so Phase 2 sees its comments — skipping the wait entirely, without halting, when Copilot is unavailable (request dropped / disabled for repo). Zero idle turns.
- **Phase 2 — Address:** runs `/address-feedback` — gathers the posted verdict + all external/human/bot comments + failing checks, applies fixes, replies to threads, pushes, and watches checks until green.

Pass it only the PR number and the flag — no session narrative, so the clean-context guarantee holds.

## Step 4: Merge (handled by `/review-and-address`)

The merge is **not** a separate action `/ship-pr` performs — it lives inside `/review-and-address`:

- **With `--auto-merge`:** `/review-and-address` merges the PR automatically once all quality gates pass (it still halts for the user on a Copilot timeout, even under auto-merge).
- **Without `--auto-merge`:** `/review-and-address` stops at its merge gate and asks the user to confirm the merge.

`/ship-pr` does nothing here beyond having forwarded the flag in Step 3.

## Step 5: Report

Summarize the full run:

```markdown
## ✅ Ship-PR Complete

**PR:** {url}
**Branch:** {branch}
**Review:** verdict {APPROVED / CHANGES REQUESTED} — posted to PR
**Feedback:** {n} required applied, {n} recommended applied/deferred, checks {GREEN/RED}
**Outcome:** {merged / awaiting merge gate / blocked on {reason}}
```

## Notes

- **Pure composition.** `/ship-pr` re-implements nothing: `/create-pr` and `/review-and-address` each own their logic. This skill only sequences them and forwards `--auto-merge`. If either child skill changes, `/ship-pr` inherits it for free.
- **One Copilot requester.** The Copilot review is requested in exactly one place — `/create-pr` Step 5b — so every PR opened through `/ship-pr` gets it, and `/review-and-address` only waits for it (it does not request). Don't re-add a request anywhere in this chain.
- **Relationship to the other skills:**
  - `/ship-it` = kickoff → implement → **`/ship-pr`** (open → review → address → merge). Use it when the code isn't written yet.
  - `/ship-pr` = open a PR for a ready branch, then review and address to merge. Use it when the code is done but unopened.
  - `/review-and-address` = close out an **existing** PR. Use it when the PR is already open.
- **Not idle while waiting for Copilot.** The external-review wait is absorbed by `/review-and-address`'s background poll (the harness re-invokes on exit), so the session isn't tied up burning turns.
- **Fully unattended runs** (e.g., Copilot finishes → auto-respond with no session open) still belong in a `.github/workflows/` webhook, not here — use `--auto-merge` for in-session end-to-end, that workflow for away-from-keyboard.
