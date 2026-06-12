---
name: experiment
description: Design, register, and analyze marketing experiments. Use whenever the user wants to test anything — copy, channels, pricing page, subject lines, store listing, ad creative — or says "experiment", "A/B test", "try", "test whether". Every experiment MUST be logged in the shared experiment log; this skill is the only writer to that log.
---

# Marketing experiments

The experiment log is the system's training data. No experiment runs unregistered; no result goes unanalyzed.

## Designing an experiment

Every experiment entry requires, BEFORE launch:

- **Hypothesis** — falsifiable, mechanism included: "Benefit-led store listing title will beat feature-led because browsers decide in <3s on outcome words."
- **Prediction** — the user's own prediction, captured via mentor-mode predict-then-reveal. Their calibration history is part of the education.
- **Metric + minimum detectable effect** — what number moves, by how much, measured where.
- **Sample/duration floor** — when we're allowed to call it. With steady.club's early volumes, most tests need weeks, not days; say so honestly. If expected n is too small for significance, label the experiment `directional` upfront rather than pretending.
- **Stage** — which AARRR stage this targets (should match the current bottleneck per weekly-sync).

Append to `shared-context/experiment-log.md` using the template's row format, status `running`.

## Analyzing

When an experiment hits its floor or duration:

1. Record the result next to the prediction. Right/wrong/unclear — all three are fine.
2. Classify confidence: `validated` (adequate n, clear effect), `directional` (suggestive, low n), `noise`.
3. Only `validated` findings may be promoted into `shared-context/learnings.md` by marketing-retro. Directional findings stay in the log as candidate hypotheses for re-testing.
4. Mentor-mode Craft note: what this result teaches about the audience or the craft (e.g., survivorship bias, novelty effects, regression to the mean — pick the one actually relevant).

## Anti-patterns to enforce

- No simultaneous experiments on the same metric (confounded reads).
- No peeking-based early stops — calling a winner at n=15 is the marketing equivalent of benchmarking on one run.
- No "we'll just feel it out" — if it can't be measured even roughly, reframe it as a build task, not an experiment.
