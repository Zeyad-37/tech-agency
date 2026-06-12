---
name: marketing-setup
description: Bootstrap the marketing-agency for a product. Use when the user says "set up marketing", "marketing setup", "initialize marketing-agency", or installs this plugin for the first time on a project. Detects what already exists and only creates the missing parts — shared context, dependencies, product context interview, board, automation.
---

# Marketing setup

Idempotent bootstrap, modeled on tech-agency's setup-repo. Detect, then fill gaps only.

## Steps

1. **Dependencies.** Check whether the upstream skill packs are installed; if not, instruct/run:
   - `claude plugin marketplace add coreyhaines31/marketingskills` + `claude plugin install marketing-skills` (broad marketing skills — the execution layer this plugin orchestrates)
   - Optionally `AgriciDaniel/claude-seo` for deep SEO/AEO audits.
2. **Shared context layer.** Create `shared-context/` (location from user; default: a sibling directory or repo readable by both agencies) and copy templates from this plugin's `context-templates/`:
   - `product-context.md`, `experiment-log.md`, `learnings.md`, `concepts-learned.md`, `releases.md`, `config.md`, `metrics/` dir, `syncs/` dir, `retros/` dir, `local-overrides/` dir.
3. **Product context interview.** If `product-context.md` is still template-blank, run the upstream `product-marketing` skill as a structured interview with the user (ICP, problem, positioning, pricing, voice, channels). This is the single highest-leverage artifact — do not let the user skip it. Per mentor-mode, teach positioning (level 1) during this interview.
4. **Board.** Create `marketing-board.md` from template if absent (Backlog / Ready / In Progress / Review / Done, WIP limit 2 for experiments).
5. **Tech-agency wiring.** Write into `config.md`: path to the tech-agency board (for handoff-tech) and confirm tech-agency's release skill appends to `releases.md` — if it doesn't yet, generate the one-line addition to that skill as a suggested PR for the user's tech-agency plugin.
6. **Measurement check.** Verify minimum instrumentation exists: RevenueCat API/exports reachable, site analytics present, Play Console access. Whatever is missing becomes the first handoff-tech task — growth work on broken instrumentation is forbidden (see weekly-sync).
7. **Automation (optional).** Offer to install `automation/weekly-sync.yml` as a GitHub Action running the headless weekly sync, adapted to the user's repo layout and their existing claude-code-action setup.

## Done criteria

Setup is complete when: product-context.md is filled, the board exists, config.md points at the tech-agency board, at least one metrics snapshot exists, and the user has received their first Craft note.
