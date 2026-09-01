# RFC: Plugin Audit Remediation

**Task ID:** T-018 (epic)
**Author:** @Claude
**Date:** 2026-09-01
**Status:** Proposed — awaiting @Zeyad approval
**Integration branch:** `epic/T-018-plugin-audit-remediation`

---

## Goal

Fix the defects found by the deep review of the `tech-agency` plugin (2026-08-31): 159
adversarially-verified findings, of which 9 are P0 and 13 are P1.

The review's verdict was that the plugin's *content* is strong but its *plumbing* is broken in ways
that make roughly half of what the repo promises non-functional for anyone who installs it — and
that several safety gates report `OK` while executing nothing.

This epic exists to make the plugin's advertised behavior true.

---

## Background

Five structural causes generate roughly 70% of the individual findings:

| | Cause | Principal symptom |
|---|---|---|
| **A** | `.claude/` is simultaneously this repo's project config *and* the plugin payload | `settings.json` (sandbox, permissions, `board_backend`) never reaches an installed user, while `shared-standards.md` tells every agent it is sandboxed |
| **B** | A rules reorganization from flat to nested was never propagated | ~30 `@.claude/rules/…` references resolve to nothing, including all 8 coding standards in `code-review` and `pick-up-task` |
| **C** | The enforcement gates are inert | Secret scan flags nothing with 2+ staged files; force-unwrap gates abort on macOS; all 5 plugin hooks are malformed; no validation CI |
| **D** | The flagship ship-path contradicts itself | `create-pr` auto-pushes by design while three skills still say it will not; `--base` documented but never parsed |
| **E** | Every fact is asserted in 4–6 places and no two agree | Four different version values; release CI versions the one file the plugin system does not read |

Two facts made the case urgent:

1. **Version drift is already costing users.** `claude plugin update` reports "already up to date"
   forever because the release workflow bumps `VERSION` while the plugin system reads
   `.claude/.claude-plugin/plugin.json`. A hand-written `tech-agency-autoupdate.sh` on the author's
   machine works around this by diffing git SHAs; that script is not in the repo, so nobody else has it.
2. **The gates never fired.** 0 of the last 28 non-merge commits pass this repo's own `commit-msg`
   hook, and only `pre-commit` was ever symlinked into `.git/hooks/`.

Full report: the audit artifact published 2026-08-31.

---

## Proposed Plan

One epic integration branch, seven story branches merging into it, then a single reviewed PR from
the integration branch to `main`.

```
epic/T-018-plugin-audit-remediation  ──────────────────────────────►  main  (one reviewed PR)
   ▲      ▲      ▲      ▲      ▲      ▲      ▲
 T-019  T-020  T-021  T-022  T-023  T-024  T-025
```

Story branches have **strictly disjoint file ownership**, so they can be worked in parallel worktrees
without conflicting:

| Story | Scope | Files owned |
|---|---|---|
| **T-019** | Release integrity & validation CI | `.claude-plugin/**`, `.claude/.claude-plugin/**`, `VERSION`, `.github/**`, `LICENSE`, `.gitignore` |
| **T-020** | Enforcement gates | `hooks/**`, `.claude/hooks.json`, `rules/shared/git-hooks.md` |
| **T-021** | Agent definitions | `.claude/agents/**`, `.claude/settings.json` |
| **T-022** | Coding standards & references | `rules/{mobile,backend,web}/**`, `docs/references/**` |
| **T-023** | Shared rules, push policy, docs | `rules/shared/**` (less `git-hooks.md`), `README.md`, `docs/*.md`, `docs/prompts/**` |
| **T-024** | Ship-path skills | `skills/{create-pr,capture-screenshots,code-review,address-feedback,review-and-address,ship-it,ship-pr,lint-changed}` |
| **T-025** | Planning & board skills | all other first-party `skills/**` |

The 14 vendored `android-*` / `kotlin-*` skills are **out of scope** and stay byte-identical to
upstream, per their Apache-2.0 redistribution terms.

`board-context.md` is owned by the epic branch, not by the stories — see *Board updates* below.

### Two decisions taken up front

**1. Rules delivery — split model.** (@Zeyad, 2026-09-01)

- The **10 shared rules** are copied by `/setup-repo` into the consumer's `.claude/rules/shared/`,
  where they auto-load every session. Referenced as `@.claude/rules/shared/<name>.md`.
- The **8 language coding standards** stay in the plugin and are **read on demand** via
  `${CLAUDE_PLUGIN_ROOT}/rules/<path>.md`, falling back to `.claude/rules/<path>.md` when
  `CLAUDE_PLUGIN_ROOT` is unset.
- Rationale: fixes delivery to installed users (cause A) *and* cuts always-on context from ~79k
  tokens to ~14k. Today all eight standards load in every session regardless of stack — a React
  standard in an Android repo.
- **Consequence that must be handled everywhere:** standards are no longer preloaded, so every agent
  and every skill that judges or writes stack-specific code must now *explicitly read* its standard.
  An unmodified `pick-up-task` or `code-review` would otherwise operate with no standard at all.
- The nested layout is canonical **everywhere**, consumers included. The flat layout is dead.

**2. Commit format — widened to match reality.** (@Zeyad, 2026-09-01)

`^\[[A-Za-z]+(-[0-9]+)?\][[:space:]]+(@[A-Za-z]+:[[:space:]]+)?.{3,}`

Accepts `[T-015] @Claude: …`, `[TECH] @Claude: …`, `[tech] …`, `[US-042] @Kai: …`; the agent tag is
optional. This passes the existing history and the release bot's own messages, where the previous
`[A-Z]+-[0-9]+` requirement passed none of them.

### Per-story summary

- **T-019** — Delete the dead root `plugin.json`; set `VERSION` and the governing manifest both to
  `1.2.0`; make the release workflow bump *both* and fail on pre-existing drift; add
  `.github/workflows/validate.yml` (manifest parsing, source resolution, version equality, skill and
  agent frontmatter, a `@`-path reference resolver, and count-drift detection); add a root `LICENSE`
  that states the proprietary terms and carves out the vendored Apache-2.0 directories; gitignore
  `.claude/settings.local.json`.
- **T-020** — Rewrite the secret scan to read staged *content* with a correct quote class and real
  token-shape patterns; `grep -vE` for the force-unwrap gates; explicit grep exit-code handling
  instead of blanket `|| true`; widened `commit-msg` regex with first-line-only skip rules;
  `pre-push` consuming stdin refspecs; worktree-aware `install-hooks.sh`; correct `hooks.json` schema
  and removal of the personal `~/.claude-personal` hook.
- **T-021** — Grant `Write, Edit` to the five authoring agents; delete the non-canonical
  `agentModelRouting` key (frontmatter `model:` becomes the single source of truth, with no behavior
  change); repair rule references and apply the on-demand-standards instruction to every engineering agent.
- **T-022** — ~35 corrections to the coding standards and reference docs, security-relevant ones
  first: the KMP `SecureStorage` iOS actual writing secrets to `NSUserDefaults`; the Ktor `post`
  route outside `authenticate("jwt")`; then the ~15 non-compiling samples and the MVI/T-013
  self-contradictions.
- **T-023** — New `rules/shared/rules-delivery.md`; settle the push policy in one sentence; make the
  sandbox claim honest; align the error-envelope `details` shape with the backends; correct every
  README count and add the "what ships vs. what you bootstrap" table; rewrite the setup and migration
  guides around the real model (no `project-template/`, no `CLAUDE.md`).
- **T-024** — Untrusted-input boundary for `/address-feedback` (and `review-and-address`,
  `code-review`); guard or eliminate the `capture-screenshots` stash; fix its hardcoded `main`,
  Gradle task path and dev-server invocation; parse `--base`; point `code-review` at the real PR base
  and the canonical doc paths.
- **T-025** — Bind `/setup-repo`'s `{project-template}` placeholder and implement the split delivery;
  fix its rule audit and sandbox rewrite; replace `git checkout -b` with worktrees in six skills;
  commit `dispatch-task` Phase 1 artifacts before cutting worktrees; route the eight direct
  `cat board-context.md` reads through the board adapter; unify post-mortem paths and the board schema.

### Board updates

Per `board-in-pr.md`, board edits ship inside the PR carrying the change they describe. For an epic,
the carrier is the integration branch: `board-context.md` is maintained on
`epic/T-018-plugin-audit-remediation` alongside this RFC, and reaches `main` in the single
integration PR together with all seven stories. No board-only PR is opened and no board commit lands
on `main`. Story branches do not touch `board-context.md`, which also removes the seven-way conflict
that per-story board edits would otherwise cause.

---

## Alternatives Considered

**1. One large PR.**
*Rejected.* The change touches 100+ files across manifests, CI, shell scripts, agent definitions,
rules and skills. A single diff would be unreviewable, and a defect anywhere would block all of it.
The audit's own finding — that nothing in this repo is validated before it ships — argues for
smaller, individually reviewable units.

**2. Seven independent PRs straight to `main`.**
*Rejected.* The stories are interdependent by contract even though their files are disjoint: T-023
writes the push policy that T-024 must state consistently; T-023 defines the rules-delivery model
that T-021, T-022, T-024 and T-025 all implement; T-025's `/setup-repo` copies the shared-rule set
T-023 defines. Merging them to `main` one at a time would leave `main` in a state where the policy
and its implementations disagree — precisely the class of defect this epic exists to remove. An
integration branch lets the whole set land coherent, and matches the base-branch resolution already
specified in `worktree-first.md` § Base Branch Resolution.

**3. Fix only P0.**
*Rejected as the epic's scope,* though it is the sensible fallback if review runs long. P0 alone
leaves ~30 dead rule references, the untrusted-input hole partially open, and every advertised count
still wrong — and leaves no CI to stop the same drift recurring. The P1 set is what makes the P0
fixes durable.

**4. Keep all 18 rules always-on and only fix delivery.**
*Rejected* (this was option C in the decision above). It fixes cause A but preserves a ~79k-token
per-session tax paid on every task the plugin performs, in every project, regardless of stack.

---

## Open Questions

1. **Do the six model-tier mismatches represent the real intent?** `agentModelRouting` asked for
   sonnet/haiku on six agents whose frontmatter says opus/sonnet; all six drift upward in cost. T-021
   deletes the dead key without retiering, so behavior is unchanged. If the cheaper tiers were the
   intent, the frontmatter is now the single place to change them — @Zeyad to confirm.
2. **Should `/setup-repo` copy skills at all?** An installed plugin already exposes them as
   `/tech-agency:<skill>`. Copying may only make sense for vendored-repo (non-plugin) use. T-025 is
   asked to make the call explicitly rather than leave it ambiguous.
3. **`marketing-agency` version lockstep.** T-019 leaves it on its own `0.1.0` line rather than
   dragging it to `1.2.0`. If the two plugins should version together, that is a follow-up.
4. **Retiring `tech-agency-autoupdate.sh`.** Once T-019 lands, `claude plugin update` works normally.
   The local script should be removed from the author's machine — it is not in the repo, so no code
   change tracks this.

---

## Estimated Scope

| | |
|---|---|
| Stories | 7 |
| Findings addressed | 9 P0, 13 P1, plus the P2 cleanup set |
| Files touched | ~100 |
| Out of scope | The 14 vendored `android-*`/`kotlin-*` skills; `marketing-agency/**` beyond manifest validation |

Risk is concentrated in T-020 (shell scripts that must actually run) and T-025 (`/setup-repo`, which
no one can have run successfully since the `{project-template}` placeholder was introduced). Both
carry an explicit requirement to reproduce each defect and then prove the fix against the same
reproduction.

---

## Review

Per `shared-standards.md` § Approval Gate, this RFC requires @Zeyad's approval before the integration
branch merges to `main`. Each story PR is reviewed into the integration branch; the integration
branch is reviewed once into `main`.
