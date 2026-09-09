# Board Updates Ship Inside the PR (`markdown` backend)

**Applies to the `markdown` backend only.** Check `board_backend` in `.claude/settings.json` before
applying anything here — see `@.claude/rules/shared/board-adapter.md`.

**Rule:** every `board-context.md` edit is committed on the branch that carries the change it describes, and merges to `main` as part of that change's PR. There is no board-only PR. There is no board commit directly on `main`.

## On the `github` backend, this rule is unnecessary

There is no file to commit. A transition is an API write that takes effect immediately, and `→ Done`
is performed by GitHub itself:

```
Closes #47
```

in the PR body. On merge, the issue closes — atomically, server-side, and only if the merge actually
happens. Every mechanism below exists to emulate that by hand:

| This rule's machinery | What GitHub does instead |
|---|---|
| `→ Done` as the final pre-merge commit | `Closes #N` closes the issue on merge |
| The reset loop when the post-Done check run fails | No Done commit exists to reset; a failed check just means no merge |
| § Conflicts — resolving two branches editing one file | No shared file |
| § Planning-Only Board Edits needing a carrier document | Planning writes go straight to the API |

**The one obligation that carries over:** every PR completing a task must have `Closes #{issue}` in
its body. That *is* the Done transition. `/create-pr` adds it; if you write a PR body by hand, it is
on you.

The rest of this document is the `markdown` backend's implementation of the same intent.

## Why

A board update is a description of a change, not a change of its own. When the two travel separately, the board and the code disagree for as long as the second PR is open — and a board-only PR is pure overhead: it needs a branch, a review, and a merge to record something that was already true. Keeping them in one PR means the board is correct the instant the change lands, and reverting the PR reverts the board entry with it.

## Where Each Transition Commits

| Transition | Commits on | Lands in |
|---|---|---|
| Ready → In Progress | The task branch, as the first commit after the worktree is created | The task's PR |
| In Progress → Blocked | The task branch | The task's PR (or stays unmerged while blocked) |
| Blocked → In Progress | The task branch | The task's PR |
| In Progress → Review | The task branch, before `/create-pr` runs | The task's PR |
| Review → Done | The task branch, as the **final pre-merge commit** — see below | The task's PR |

All five are ordinary commits in the worktree, following the `[STORY-ID] @Agent: …` commit format. None of them warrants its own PR.

## The `→ Done` Transition

*(`markdown` only — on `github`, `Closes #N` does this.)*

`→ Done` is written **after the PR's checks are green and the merge is approved, but before the merge runs**. The sequence at the merge gate is:

1. Checks green, review resolved, merge approved (by @Zeyad or `--auto-merge`).
2. `/update-board {TASK-ID} → Done` — commits on the PR branch.
3. `git push` — the Done commit joins the PR.
4. `gh pr merge` — the change and its Done state land together.

Do **not** write `→ Done` at code-review-approval time: an approved PR whose checks later fail would leave the board claiming Done for work that never merged. And do **not** write it after the merge — a post-merge board commit on `main` is exactly the separate change this rule exists to prevent.

### If the post-Done check run fails

Step 3 pushes a new head, so the required checks run again against a branch that already contains the Done commit. If that run fails:

1. Drop the Done commit off the branch — `git reset --hard HEAD~1` (the Done commit is the branch tip) followed by `git push --force-with-lease`.
2. Move the task back to Review.
3. Re-enter `/address-feedback` Step 3 with the new failure as feedback.

That loop is bounded by the same **3-iteration cap** as `/address-feedback` Step 7c: on the third failed run, stop and surface it to the user rather than cycling again.

**Invariant:** the board never records Done for work that did not merge. Both exits from the merge gate preserve it — a declined gate means the Done commit is never made, and a failed post-Done check means the Done commit is removed and the task returns to Review.

## Planning-Only Board Edits

*(`markdown` only — on `github`, planning writes go straight to the API and need no carrier.)*

Some board edits have no code change to ride with: `/replenish` moving Backlog → Ready, `/new-feature` or `/tech-task` creating tasks during planning, `/retro` filing action items.

These ride with the **documents they produced**. A planning run that writes a PRD, BRD, ADR, RFC, retro report, or replenishment report commits the board edit on the same branch as those docs, and both merge in that PR — the docs are the change, and the board edit describes it.

**There is always a carrier.** Every planning run saves a document, so no planning board edit is ever left uncommitted: `/replenish` saves `docs/artifacts/replenishment/{YYYY-MM-DD}-Replenishment.md`, `/retro` saves `docs/artifacts/retro/{date}-retro.md`, and `/new-feature` / `/tech-task` produce a PRD, BRD, ADR, or RFC. A run that would otherwise produce nothing must save its report rather than deferring the board edit. Leaving the edit uncommitted does not work: the next agent's worktree is cut from its resolved base branch (`origin/main`, or an epic integration branch — see `@.claude/rules/shared/worktree-first.md` § Base Branch Resolution), so it never sees the pending edit — nor the Ready tasks the edit created — and the edit is discarded when the planning worktree is removed.

## Conflicts

*(`markdown` only — `github` has no shared file to conflict on.)*

Two branches editing `board-context.md` will conflict on the second merge. That is expected. Resolve by keeping every task movement from both sides — board edits are additive.

If the same task appears in different columns on the two sides, keep the entry that sits **further along the column sequence**: Backlog → Ready → In Progress → Review → Done. Blocked is outside that sequence and is never dropped by a resolution — if either side has the task Blocked, the resolved board keeps it Blocked until the blocker is cleared.

The split introduced by `board-adapter.md` makes these conflicts rarer and easier. Completed work is appended to `docs/board/done-{YYYY}-Q{N}.md`, so two branches finishing tasks in the same quarter conflict on append-only lines rather than on a shared Done table — keep both rows. A `→ Done` transition touching both files still conflicts on `board-context.md` if the other side moved the same task; resolve with the sequence rule above, then check the quarter file has exactly one row for that task.

## What the Committed Board Records

*(`markdown` only. On `github` the board is live, and the tech-debt item tracking the gap below is
retired — see `@.claude/rules/shared/board-adapter.md` § Known Limitation.)*

Because every transition merges with the change it describes, the archives on `main` are an accurate record of **completed** work — `docs/board/done-*.md`, the decisions log, and the task inventory. `board-context.md` is not a live view of in-flight work: a task's `→ In Progress` or `→ Blocked` commit sits on an unmerged branch until that branch's PR lands, so a checkout of `main` shows an empty or stale In Progress column.

Live state is therefore **derived**, not read: open PRs and their branches are the source of truth for what is In Progress, in Review, or Blocked (`gh pr list`, `git branch -r`, and each branch's own `board-context.md`).

Known limitation: the consumers that report live state — `/pick-up-task`'s 2-item WIP check and `/daily-sync`'s In Progress count, WIP violations, blockers, and cycle-time alerts — still read those columns straight from the merged file, and will therefore under-report in-flight work. Reworking them onto the derived source is tracked in `docs/guides/tech-debt/backlog.md` and is out of scope for this rule.

## What This Rule Forbids

On the `markdown` backend:

- Opening a PR whose only change is `board-context.md`.
- Committing `board-context.md` on `main`, including post-merge cleanup steps.
- An "Atlas updates the board centrally" path that bypasses the task branch.
- Deferring a task's board transition to a later PR than the one carrying its change.

On the `github` backend:

- Writing a local mirror of the board into the repo (`board-adapter.md` rule 4).
- Opening a PR that completes a task without `Closes #{issue}` in its body.
- Editing frozen post-migration board files as though they were live.
