# marketing-agency

A proactive, self-improving, *educational* marketing system for Claude Code — the demand-side counterpart to `tech-agency`.

## Architecture

```
┌─────────────────┐   release feed    ┌───────────────────┐
│   tech-agency   │ ────────────────▶ │  marketing-agency │
│ builds & ships  │ ◀──────────────── │  drives demand    │
└────────┬────────┘    tech tasks     └─────────┬─────────┘
         │                                      │
         ▼                                      ▼
┌──────────────────────────────────────────────────────────┐
│                   shared-context/  (dashed = shared)     │
│  product-context.md · experiment-log.md · learnings.md   │
│  concepts-learned.md · releases.md · metrics/ · syncs/   │
│  retros/ · local-overrides/ · config.md                  │
└──────────────────────────────────────────────────────────┘
```

Three design principles:

1. **Two plugins, one shared domain layer.** Workflows stay separate (different boards, cadences, metrics); only the domain context is shared — the KMP pattern applied to org design.
2. **Orchestration here, execution upstream.** This plugin decides *what* to do and *why*; the broad execution knowledge lives in [coreyhaines31/marketingskills](https://github.com/coreyhaines31/marketingskills) (~45 skills) and optionally [AgriciDaniel/claude-seo](https://github.com/AgriciDaniel/claude-seo) for deep SEO/AEO audits. Upstream is never edited; accumulated knowledge lives in `shared-context/local-overrides/`.
3. **Three loops:**
   - *Proactive loop* — `weekly-sync` (cron-able via `automation/weekly-sync.yml`) reads metrics → finds the funnel bottleneck → proposes 3-5 tasks/experiments as a PR.
   - *Learning loop* — `experiment` logs everything; `marketing-retro` promotes validated findings into `learnings.md` and `local-overrides/`. Skills are the weights; retro is the training step.
   - *Teaching loop* — `mentor-mode` makes every output explain its framework, tracks depth in `concepts-learned.md`, and calibrates your predictions against outcomes.

## Skills

| Skill | Role |
|---|---|
| `marketing-setup` | Idempotent bootstrap: deps, shared context, product interview, board, wiring |
| `mentor-mode` | Cross-cutting educational contract (Craft notes, predict-then-reveal, curriculum) |
| `weekly-sync` | Proactive engine: bottleneck-driven task proposals |
| `funnel-audit` | AARRR diagnosis with numbers; one bottleneck verdict |
| `experiment` | Sole writer of the experiment log; design + analysis discipline |
| `marketing-retro` | Monthly learning step; prediction calibration; writes local-overrides |
| `handoff-tech` | Marketing → tech-agency task bridge (what/why, never how) |
| `launch-from-release` | Tech-agency releases → proportionate launch content |

## Install

```bash
# In your plugin marketplace repo, add this directory, then:
claude plugin install marketing-agency@<your-marketplace>

# Dependencies (execution layer):
claude plugin marketplace add coreyhaines31/marketingskills
claude plugin install marketing-skills
```

Then run `marketing setup` in a session — it detects what exists and fills the gaps, starting with the product-context interview (don't skip it; it's the foundation everything reads).

## Handoff checklist for Claude Code integration

1. Drop this directory into your plugin marketplace repo next to `tech-agency`.
2. Run `marketing-setup`; point `config.md` at the tech-agency board.
3. Add one line to tech-agency's `release` skill: append a row to `shared-context/releases.md` on release.
4. Wire a metrics snapshot script (RevenueCat + analytics + Play Console) writing to `shared-context/metrics/`.
5. Adapt and enable `automation/weekly-sync.yml`.
6. Test triggering: "what should I work on this week" → weekly-sync; "trials aren't converting" → funnel-audit; "we just released 1.4" → launch-from-release.
