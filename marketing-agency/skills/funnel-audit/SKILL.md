---
name: funnel-audit
description: Diagnose the marketing/revenue funnel end to end and find the bottleneck. Use when the user asks "audit the funnel", "where are we losing people", "why aren't trials converting", "conversion is down", or whenever weekly-sync needs a deeper diagnosis of a weak stage. Also use for first-time funnel mapping of a product.
---

# Funnel audit

Find where prospects actually leak, with numbers, before anyone proposes fixes.

## The funnel model (freemium subscription app)

Map every available metric onto this chain; compute conversion between each adjacent pair:

```
Impression (store/web/social/AI-answer)
  → Store listing view / site visit
  → Install / signup
  → Activation (first core action completed)
  → Trial start
  → Trial engaged (used product ≥N times during trial)
  → Trial → paid
  → Month-2 retained
  → Referral / review left
```

Sources: Play Console (listing acquisition report), RevenueCat (trial/paid/churn), site analytics, email platform (open/click on onboarding sequence).

## Process

1. Build the chain with real numbers for the last full period. Mark unknown steps as `?` — unknowns are findings, not gaps to skip.
2. Compute stage-to-stage conversion and compare against (a) previous period and (b) rough category benchmarks. State benchmarks as ranges with low confidence — public benchmarks are noisy.
3. Identify the bottleneck: the stage with the largest gap × largest volume impact. One bottleneck. Resist naming three.
4. For the bottleneck stage, list candidate causes ranked by likelihood, separating: messaging causes, UX/product causes (→ handoff-tech), measurement causes.
5. Recommend 2-3 experiments for that stage only, formatted for the `experiment` skill.

## Engineering-shaped findings

Schema markup gaps, page speed, listing assets, paywall screen changes, onboarding flow changes, missing analytics events — these are tech-agency work. Output them as a handoff block for `handoff-tech`, never as marketing-board tasks.

## Output

A single report: the numeric chain, the bottleneck verdict with evidence, causes, proposed experiments, handoff block, and a mentor-mode Craft note (the funnel/AARRR concept itself on first run; deeper concepts like activation definitions or cohort vs. snapshot analysis on later runs).
