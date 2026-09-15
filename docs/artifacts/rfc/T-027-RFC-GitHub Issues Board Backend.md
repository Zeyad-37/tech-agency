# RFC: GitHub Issues + Projects v2 as the Default Board Backend

**Task ID:** T-027 GitHub Issues board backend
**Author:** @Claude
**Status:** Accepted — approved by @Zeyad on 2026-09-09, before implementation began. Recorded in `docs/board/decisions-log.md`.
**Date:** 2026-09-09
**Supersedes:** nothing. **Rescopes:** tech-debt item #3 (derived live state) to the `markdown` backend — it no longer applies on `github`, and stays open for repos still on `markdown`.

## Goal

Replace the markdown Kanban board with GitHub Issues + Projects v2 as the **default** `board_backend`, keep the existing markdown files as frozen history rather than deleting them, and ship a reusable `/migrate-board` command so any consumer repo can perform the same migration.

Markdown remains a supported backend — for repos with no GitHub remote, and for anyone who declines the migration.

## Background

### The board does not scale, and we have the receipts

Three independent failures, all already documented in-repo:

**1. Context tax on every task.** `board-adapter.md` § "Why the split" records the reference consumer reading **249 KB per task, under 10% of it live**. The T-016.2 split cut the hot file down but did not change the shape of the problem: every agent still reads the whole live board to answer "what is mine?".

**2. One file, many branches.** `board-in-pr.md` § Conflicts exists solely because every task edits the same file. The rule ships a conflict-resolution procedure (keep the entry further along the column sequence; Blocked always survives) because conflicts are expected, routine, and unavoidable.

**3. Live state does not reach `main`.** Tech-debt item #3, `board-adapter.md` § "Known Limitation", and `board-in-pr.md` § "What the Committed Board Records" all document the same defect from different angles: `→ In Progress` and `→ Blocked` sit on unmerged branches, so a checkout of `main` shows an empty In Progress column. `/pick-up-task`'s WIP check and `/daily-sync`'s In Progress count, WIP violations, blockers, and cycle-time alerts therefore **under-report in-flight work**. The tracked remedy is a half-day rework onto `gh pr list` — a workaround for the file's inability to hold live state.

### The board is corrupt right now

`board-context.md` lines 42–59 are wreckage:

| Symptom | Detail |
|---|---|
| Section that must not exist | `## Done (recent)` in the live file, which `board-adapter.md` moved to `docs/board/done-{YYYY}-Q{N}.md` |
| Malformed tables | Separator rows at lines 43 and 45 precede their header rows; the tables do not render |
| Stranded Done rows | T-019 … T-026 sit in the live file; `docs/board/done-2026-Q3.md` contains only T-015 |
| Divergent decisions log | The rules-delivery decision exists **only** in the corrupt block; the board-split decision exists **only** in `docs/board/decisions-log.md` |

Root cause: commits `d3491c8` and `45d2fa5` (both `[T-018]`) appended Done rows and decisions to a schema that the T-016.2 split had already removed on another branch. The merge resolved textually and produced a file that is valid Markdown, renders as garbage, and silently lost eight archive rows.

Nothing detected this. There is no schema, no parser, and no CI check — a corrupt board is indistinguishable from a healthy one until a human reads it. **This is the argument for the migration in one artifact:** the failure mode is not "the file got big", it is "the file has no integrity guarantees and the conflict procedure we shipped invites exactly this".

### Why GitHub specifically

`gh` 2.96 is already load-bearing — `/create-pr`, `/address-feedback`, `/ship-pr`, and `/code-review` all shell out to it. No new dependency, no new auth (with one exception, below), no MCP server. Free and uncapped for private repos; Linear's free tier caps at 250 issues, Jira free at 10 users.

Most importantly, `Closes #N` in a PR body performs the `→ Done` transition on merge, atomically, server-side. `board-in-pr.md` § "The `→ Done` Transition" is a careful hand-built emulation of exactly that — including a reset loop for when the post-Done check run fails. That whole section becomes markdown-only.

## Proposed Plan

### Column mapping

| Agency column | Projects v2 `Status` | Label fallback | Issue state |
|---|---|---|---|
| Backlog | `Backlog` | `status:backlog` | open |
| Ready | `Ready` | `status:ready` | open |
| In Progress | `In Progress` | `status:in-progress` | open |
| Review | `In Review` | `status:review` | open |
| Blocked | `Blocked` | `status:blocked` | open |
| Done | `Done` | — | **closed** |

Done is issue-closed, not a label. That is what makes `Closes #N` work.

### Operation translations

All twelve operations from `board-adapter.md` map to `gh` with no GraphQL for the Issues half. Only Projects v2 field mutation needs `gh project item-edit`.

| Operation | `gh` translation |
|---|---|
| `read_all()` | `gh issue list --state open --json number,title,labels,assignees` |
| `read_column(c)` | `gh issue list --label status:{c} --json …` |
| `read_task(id)` | `gh issue view {n} --json …` |
| `read_agent_wip(a)` | `gh issue list --label "agent:{a},status:in-progress"` |
| `search(q)` | `gh issue list --search "{q}"` |
| `move_task(…)` | `gh issue edit {n} --remove-label … --add-label …` (+ `gh project item-edit` for Status) |
| `assign_task(…)` | `gh issue edit {n} --add-assignee {human} --add-label agent:{name}` |
| `create_task(t)` | `gh issue create --title "[T-0NN] …" --label …` |
| `update_task(…)` | `gh issue edit {n}` |
| `add_comment(…)` | `gh issue comment {n}` |
| `add_blocker(…)` | move to `status:blocked` + comment with the reason |
| `remove_blocker(…)` | move to `status:in-progress` |
| *(epic link)* | `gh issue edit {epic} --add-sub-issue {story}` |
| *(epic read)* | `gh issue view {epic} --json subIssues` |

### Identity: two decisions worth stating explicitly

**Agency agents are not GitHub accounts.** @Kai, @Swift, @Atlas have no logins. Proposal: the **human owner is the GitHub assignee**, and the agency agent is an `agent:{name}` label. `read_agent_wip` and the 2-item WIP limit query the label. Assignee stays meaningful for notifications.

**The agency Task ID stays the identity, not the issue number.** Branch names (`T-027/slug`), commit prefixes (`[T-027]`), and artifact filenames (`T-027-RFC-….md`) all key off the agency ID, and the `commit-msg` hook regex enforces it. The issue title is therefore prefixed `[T-027] Title`, and the issue number is incidental — used only in `Closes #N`. Nothing about the commit or branch conventions changes.

### Prerequisite the agent cannot self-provision

Verified during this investigation:

```
$ gh project list --owner Zeyad-37
error: your authentication token is missing required scopes [read:project]
```

Your token carries `admin:public_key, gist, read:org, repo` — no `project`. Projects v2 needs a one-time human `gh auth refresh -s project`. This is an interactive browser flow; no agent can do it, and a **cloud session's token may never have it**.

Therefore the adapter must **degrade, not fail**: when `project` scope is absent it runs label-only, and every operation still works. Projects v2 gives the board UI and richer `/sprint-report` queries on top. This makes the labels-only path a permanently supported mode rather than a stepping stone, which is a better design than the phased option regardless.

### Stories

This is epic-sized. Integration branch `epic/T-027-github-board`, per `worktree-first.md` § Base Branch Resolution.

| ID | Story | Owner | Files |
|---|---|---|---|
| T-027.1 | Repair `board-context.md`; make `done-2026-Q3.md` whole; reconcile the decisions log | @Claude | `board-context.md`, `docs/board/*` |
| T-027.2 | `board-adapter.md`: add `github` backend, 12 translations, column/label map, scope degradation; drop rule 4's mirror | @Sage | `.claude/rules/shared/board-adapter.md` |
| T-027.3 | `board-in-pr.md`: scope the ship-inside-the-PR rule, § Conflicts, and the `→ Done` protocol to the markdown backend | @Sage | `.claude/rules/shared/board-in-pr.md` |
| T-027.4 | Convert ~24 raw `board-context.md` references across 12 skills to named `board.*` operations; move `/replenish`'s tech-debt pull onto a `tech-debt` label query | @Claude | 13 `SKILL.md` files |
| T-027.5 | `/update-board`: GitHub code path alongside the markdown one | @Claude | `.claude/skills/update-board/` |
| T-027.6 | **New `/migrate-board` skill** — reusable on any repo: repair → parse → dry-run → create issues → link sub-issues → create repo project → import tech debt → verify → freeze. Must be idempotent on re-run | @Claude | `.claude/skills/migrate-board/` |
| T-027.7 | `/setup-repo`: `github` becomes the default; markdown fallback when there is no GitHub remote | @Claude | `.claude/skills/setup-repo/` |
| T-027.8 | Dogfood — migrate tech-agency's own board and tech-debt backlog; wire T-016/T-018 sub-issues; add frozen-history banners | @Claude | `board-context.md`, `docs/board/*`, `docs/guides/tech-debt/*` |
| T-027.9 | Retire tech-debt #3: `/pick-up-task` WIP and `/daily-sync` read live GitHub state | @Claude | 2 `SKILL.md` files, `docs/guides/tech-debt/` |

T-027.1 is a standalone prerequisite and can merge on its own — the repair is worth having whether or not the rest proceeds.

### On the ~24 references

An earlier count of 38 was too blunt. Roughly 14 are legitimate and must **not** be converted: `/setup-repo`'s 8 scaffold the markdown board (that is the backend's own bootstrap), `/sync-rule` merely notes the board is not a rule file, `/health-check:227` is a doc-staleness check over filenames, and `/pick-up-task` and `/kick-off` already route through the adapter correctly while documenting what markdown resolves to. The real work is ~24 references across 12 skills.

### Frozen history, not deletion

`board-context.md` and `docs/board/**` stay in the repo. Each gains a banner:

> **Frozen 2026-09-09.** This board moved to GitHub Issues (T-027). Kept as history; not updated. Live board: `gh issue list` or the Projects board.

`docs/artifacts/**` and `docs/board/decisions-log.md` are unaffected by this migration in any case — they are versioned documents, not tracked work. The decisions log stays live and in-repo.

## Alternatives Considered

**1. Stay on markdown, split further.** We already did this (T-016.2). It fixed hot-file size and touched neither conflicts nor liveness — and the corruption above happened *after* the split, caused by it. Rejected: the remaining two failure modes are inherent to one-file-many-branches.

**2. Fix tech-debt #3 in place.** The tracked half-day rework derives live state from `gh pr list` and each branch's own `board-context.md`. Cheaper, and it works. But it means reading N branches to answer one question, and it leaves the corruption and conflict problems entirely untouched. It is a workaround for the file being the wrong container. Rejected — though note it is the fallback if this RFC is declined, and it stays in the debt backlog until T-027.9 lands.

**3. Linear.** Best UX of the options, official MCP server, genuine free tier. Rejected: 250-issue and 2-team caps are wrong for a plugin meant to run across many consumer repos, and it adds an MCP dependency and a second auth for something `gh` already covers.

**4. SQLite or JSON in-repo.** Gives schema and validation, killing the corruption class. Rejected: binary or dense-JSON merge conflicts are *worse* than Markdown's, it is unreadable in a PR diff, and it solves nothing for liveness.

**5. Projects v2 only, no label fallback.** Simpler adapter, one code path. Rejected on the evidence above — the scope is unavailable today and may be permanently unavailable in cloud sessions. A backend that cannot run in a cloud session is not a default.

## Resolved Decisions

Answered by @Zeyad, 2026-09-09. All four are folded into the stories above.

**1. Projects v2 board scope — repo-scoped, one per repo.** Matches today's per-repo board. `/migrate-board` creates the project during migration; no cross-repo permission surface.

**2. Tech debt migrates to issues.** Each entry in `docs/guides/tech-debt/backlog.md` becomes an issue labelled `tech-debt` plus its severity, and the file is frozen with the same banner as the board. `/replenish`'s 15–20 % WIP allocation becomes a label query instead of a file parse. The prose bodies survive intact — an issue body has no one-line constraint, unlike a board row. This adds `/replenish` to the T-027.4 conversion list and a second import path to T-027.6.

**3. Epics map to native sub-issues.** `T-016` is a parent issue; `T-016.1 … T-016.10` are its sub-issues, giving real hierarchy and automatic progress rollup that mirrors the epic integration branch model.

> **Correction to the draft.** This RFC first claimed sub-issue creation needs GraphQL and would fall back to an `epic:` label. That is wrong. `gh` 2.96 ships first-class flags — `--parent`, `--add-sub-issue`, `--remove-sub-issue`, `--remove-parent` — verified against the installed binary. Consequences, all favourable: no GraphQL in the adapter, no fallback path to build or document, and because sub-issues need only the `repo` scope, **the epic hierarchy keeps working in degraded label-only mode** where Projects v2 is unavailable. The dotted ID convention and the `commit-msg` regex are untouched.

**4. Read path fans out with `gh issue list`.** One call per column, six per full-board read. The translations in `board-adapter.md` stay readable and adaptable, which matters more than the round trips — an agent has to be able to follow and modify them. Revisit only if rate limits actually bite; a single GraphQL query is the known escape hatch and needs no design work now.

### What is still genuinely unknown

- **Rate limits at agency scale.** Unmeasured. `/daily-sync` across a large board is ~6 calls, which is fine; a consumer with several hundred open issues paginating is not yet characterised. Escape hatch above.
- **Migration idempotency.** `/migrate-board` re-run on a partially migrated repo must not duplicate issues. The plan is a `T-0NN` title-prefix search before each create, but this needs proving in T-027.6, not assuming.

## Estimated Scope

**5–6 days**, 9 stories, epic integration branch. The tech-debt import added by decision 2 is roughly half a day inside T-027.6. T-027.1 (repair) is ~1 hour and independently mergeable. T-027.4 (skill conversion) and T-027.6 (`/migrate-board`) are the two largest, roughly a day each.

**Risk:** medium. The rule and skill changes are mechanical and reviewable. The genuine risks are (a) the `project` scope prerequisite, mitigated by the label fallback being a first-class mode, and (b) migrating consumer repos, mitigated by `/migrate-board` running a dry-run and never deleting the markdown source.

---

**Approval:** Approved by @Zeyad on 2026-09-09, before implementation began.
