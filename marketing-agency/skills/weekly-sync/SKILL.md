---
name: weekly-sync
description: The proactive engine of the marketing-agency. Use when the user says "weekly sync", "marketing sync", "what should I work on", "marketing status", "suggest marketing tasks", or when run headlessly on a schedule. Reads metrics, the marketing board, the experiment log, and learnings, then proposes a small prioritized set of marketing tasks and experiments targeting the weakest funnel stage.
---

# Weekly marketing sync

Generate this week's marketing priorities from evidence, not vibes. Modeled on tech-agency's replenish + daily-sync, but the backlog is *generated* from funnel analysis rather than pulled from a human-written list.

## Inputs (read all before proposing anything)

1. `shared-context/metrics/` — latest snapshot vs. previous (installs, trial starts, trial→paid, churn, traffic by channel, store listing conversion).
2. `shared-context/experiment-log.md` — running and recently finished experiments.
3. `shared-context/learnings.md` — validated patterns; treat as priors.
4. `shared-context/releases.md` — anything shipped since last sync (launch material opportunity).
5. `marketing-board.md` — WIP and stale items.
6. `shared-context/product-context.md` — positioning and ICP ground truth.

If metrics are missing or stale (>14 days), the FIRST proposed task is fixing measurement. Never propose growth work on top of broken instrumentation.

## Process

1. **Funnel pass.** Map metrics to AARRR stages (Acquisition → Activation → Retention → Revenue → Referral). Identify the single weakest stage by drop-off relative to benchmark or to last period. Invoke `funnel-audit` if a deeper diagnosis is needed.
2. **Constraint rule.** Propose experiments ONLY for the weakest stage (plus at most one always-on content/distribution task). Improving a non-bottleneck stage is wasted motion — this is theory-of-constraints applied to the funnel.
3. **Propose 3-5 tasks max**, each with: hypothesis, expected effort (S/M/L), expected impact, how we'll measure it, and which skill executes it. Anything that is engineering work goes through `handoff-tech` instead of onto the marketing board.
4. **Check WIP.** If more than 2 experiments are already running, propose finishing/analyzing before starting new ones.
5. **Releases.** If `releases.md` has unconsumed entries, include a launch task via `launch-from-release`.

## Output format

A short report: funnel snapshot (one line per stage with trend arrow), the bottleneck and the evidence for it, the proposed tasks table, and — per mentor-mode — a **Concept of the week**: one marketing concept tied to this week's actual bottleneck, taught at the right depth per `concepts-learned.md`.

In headless mode (cron / GitHub Action), write the report to `shared-context/syncs/YYYY-MM-DD.md` and open it as a PR or issue for the user to approve. Never start executing proposed tasks without approval.

## Confidence discipline

With small numbers, say so. "Trial→paid moved from 12% to 9% on n=34 trials" is noise until proven otherwise — flag low-n observations as `(low confidence)` and prefer experiments that increase n or run longer over reactive pivots.
