# Board Updates Ship Inside the PR

**Rule:** every `board-context.md` edit is committed on the branch that carries the change it describes, and merges to `main` as part of that change's PR. There is no board-only PR. There is no board commit directly on `main`.

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

`→ Done` is written **after the PR's checks are green and the merge is approved, but before the merge runs**. The sequence at the merge gate is:

1. Checks green, review resolved, merge approved (by @Zeyad or `--auto-merge`).
2. `/update-board {TASK-ID} → Done` — commits on the PR branch.
3. `git push` — the Done commit joins the PR.
4. `gh pr merge` — the change and its Done state land together.

Do **not** write `→ Done` at code-review-approval time: an approved PR whose checks later fail would leave the board claiming Done for work that never merged. And do **not** write it after the merge — a post-merge board commit on `main` is exactly the separate change this rule exists to prevent.

If the merge gate is declined, the task stays in Review and the Done commit is never made.

## Planning-Only Board Edits

Some board edits have no code change to ride with: `/replenish` moving Backlog → Ready, `/new-feature` or `/tech-task` creating tasks during planning, `/retro` filing action items.

These ride with the **documents they produced**. A planning run that writes a PRD, BRD, ADR, RFC, or retro report commits the board edit on the same branch as those docs, and both merge in that PR — the docs are the change, and the board edit describes it.

If a planning run produces no document at all (a bare replenishment, say), the board edit **waits**. It is not committed to `main` and does not get its own PR; it is carried by the first implementation PR for the tasks it created or moved. The agent picking up that task commits the pending board edit alongside its own `→ In Progress` transition.

## Conflicts

Two branches editing `board-context.md` will conflict on the second merge. That is expected. Resolve by keeping every task movement from both sides — board edits are additive. If the same task moved to different columns on the two branches, the later transition wins (Review on one branch, Done on the other → keep Done).

## What This Rule Forbids

- Opening a PR whose only change is `board-context.md`.
- Committing `board-context.md` on `main`, including post-merge cleanup steps.
- An "Atlas updates the board centrally" path that bypasses the task branch.
- Deferring a task's board transition to a later PR than the one carrying its change.
