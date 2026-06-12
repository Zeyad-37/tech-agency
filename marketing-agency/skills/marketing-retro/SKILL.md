---
name: marketing-retro
description: The learning step of the marketing system. Use monthly, or when the user says "marketing retro", "what have we learned", "review experiments", or after several experiments conclude. Compares predictions to outcomes, promotes validated findings into learnings, updates the local skill overrides, and reviews the user's prediction calibration.
---

# Marketing retro

The retro is what makes this system improve with use. Skills are the weights; this is the training step.

## Process

1. **Read** `shared-context/experiment-log.md` (entries since last retro), `learnings.md`, latest metrics snapshots, and `concepts-learned.md`.
2. **Score predictions.** For each concluded experiment, compare the user's recorded prediction to the outcome. Track a simple calibration tally over time ("you've predicted 7/11 correctly; you tend to overestimate copy changes and underestimate distribution changes"). This is mentor-mode's feedback loop on the user's developing judgment — deliver it candidly and kindly.
3. **Promote findings.** Move `validated` results into `learnings.md` with: the pattern, the evidence (n, effect size, date), and a confidence tag. Re-tag old learnings if new evidence contradicts them — learnings are priors, not laws.
4. **Write back into skills.** For each promoted learning that should change future behavior, append it to the relevant file in `local-overrides/` (e.g., `local-overrides/social.md`: "Architecture-deep-dive posts outperform opinion posts ~3:1 for our audience — default to them"). NEVER edit upstream skill files (marketingskills, claude-seo installs) — upstream stays pristine so updates never clobber accumulated knowledge. Skills in this plugin reference `local-overrides/` explicitly.
5. **Prune.** Mark stale learnings (>6 months, low n, or contradicted) as `deprecated` rather than deleting — the history matters.
6. **Process retro.** Briefly: did the weekly-sync proposals get executed? Were efforts spread across stages despite the constraint rule? Did anything sit in WIP too long? Propose one process improvement, tech-agency-retro style.

## Output

A retro report in `shared-context/retros/YYYY-MM.md`: experiments scoreboard (hypothesis → prediction → outcome → confidence), promoted learnings, calibration summary, process notes, and a Craft note on the most instructive surprise of the period.

## Honesty rule

If the period's data is too thin to learn anything, say exactly that. "No conclusions this month; here's what we'll have enough data for next month" is a valid and valuable retro.
