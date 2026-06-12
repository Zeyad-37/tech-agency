---
name: handoff-tech
description: Bridge from marketing-agency to tech-agency. Use whenever marketing work surfaces engineering tasks — schema markup, llms.txt, meta tags, page speed, paywall or onboarding screen changes, store listing assets, analytics events, landing page changes. Also use when the user says "hand this to tech", "file this as a tech task", or a funnel-audit/weekly-sync produces an engineering-shaped finding.
---

# Handoff to tech-agency

Marketing defines WHAT and WHY; tech-agency owns HOW. This skill converts marketing findings into tasks formatted for the tech-agency board so they enter the normal engineering workflow (replenish → pick-up-task → review → done).

## Task format

Write each task in tech-agency's task format with these marketing-specific additions:

```
### [MKT-NNN] <imperative title>
**Origin:** <which audit/experiment/sync produced this, with link to the report>
**Why (business):** <the funnel stage and metric this serves — one sentence>
**What:** <precise acceptance criteria; no implementation prescriptions>
**Measurement:** <the metric/event that proves it worked; if a new analytics event is needed, that IS part of the task>
**Priority signal:** <impact estimate from the audit, S/M/L effort guess>
```

Rules:
- Never prescribe implementation. "Add Product + FAQ schema to the pricing page, valid per Google's Rich Results test" — not "edit `app/pricing/page.tsx`".
- Every task that changes user-facing behavior must include its measurement event. A change we can't measure cannot feed the experiment log, which starves the learning cycle.
- Batch related small items (e.g., all AEO crawler fixes: robots.txt AI-bot allowlist, llms.txt, SSR visibility check) into one task with a checklist.

## Where to write

Append tasks to the tech-agency board's backlog section (path configured in `shared-context/config.md`), then notify in the sync report. If the tech-agency board uses `update-board`-style commits, commit the board change with message `chore(board): marketing handoff MKT-NNN..MKT-MMM`.

## Closing the loop

When tech-agency marks a handoff task done (visible on its board), the originating experiment in the log moves from `blocked-on-tech` to `running`. Check for this during weekly-sync.

## Craft note duty

Per mentor-mode, when a handoff batch is created, add one Craft note explaining why this boundary exists in real marketing orgs (growth team vs. product engineering, and the classic failure modes when one side does the other's job).
