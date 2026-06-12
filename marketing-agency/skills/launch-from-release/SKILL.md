---
name: launch-from-release
description: Bridge from tech-agency to marketing-agency. Use whenever a release ships, the user says "we released", "announce this", "launch content", or when weekly-sync finds unconsumed entries in the shared releases feed. Turns every release into proportionate launch content — changelog, social, email, store listing updates — so shipping continuously feeds distribution.
---

# Launch from release

Every ship is free marketing material. This skill consumes `shared-context/releases.md` (written by tech-agency's release flow) and produces a proportionate launch package.

## Sizing the launch (don't over-launch)

- **Patch / invisible fix** → changelog entry only. Silence is correct; announcing trivia trains the audience to ignore you.
- **Minor feature** → changelog + one social post + mention in the next onboarding/newsletter email.
- **Major feature** → mini-launch: changelog, announcement post, 2-3 social posts staggered over a week (different angles: problem, demo, behind-the-scenes), email to trial + paid users, store listing "What's new" update, and consider a directory/community post where relevant.
- **Tier-1 launch** (new product, pricing change, platform expansion) → full launch plan; pull in the upstream `launch` skill from marketingskills for the complete checklist.

## Content rules

1. Lead with the user's problem, not the feature. "Stop losing your streak when traveling" beats "Added timezone-aware scheduling."
2. Reuse positioning language from `shared-context/product-context.md` verbatim where possible — consistency compounds; novelty in messaging is a cost, not a virtue.
3. Apply anything relevant in `local-overrides/` (validated channel/format learnings) before generic best practices.
4. Each piece gets a UTM/tracking convention so results land in the metrics snapshots and the experiment log.

## Process

1. Read unconsumed entries in `releases.md`; mark consumed with date + links to produced assets.
2. Draft all assets in one pass for user review — never auto-publish (sending/posting always requires explicit approval).
3. Log notable launches as `directional` experiments (channel × angle), so launch performance feeds the learning cycle.
4. Craft note per mentor-mode: first time, teach launch sizing and audience attention as a budget; later, teach angle selection or the "echo launch" (re-announcing to non-openers).
