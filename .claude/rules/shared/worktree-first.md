# Worktree-First Workflow

**Rule:** All Claude Code work happens in a git worktree. The main checkout is never used for active task work. No exceptions.

The main checkout is an orchestration root only — it holds the canonical `.git` directory and serves as the parent of all worktrees. Nothing else.

## Why

Multiple Claude Code sessions can run in parallel on the same repo, and they have no native way to discover each other. The only safe, deterministic way to prevent two sessions from stomping on the same files (or each other's branches) is to require every session to operate in its own worktree from the very first action.

## What counts as "work"

Anything that writes a file in the repo: implementing code, editing docs, updating `board-context.md`, generating reports, running formatters, committing, branching. All of it happens in a worktree.

Pure read-only operations (running `git log`, reading files to answer a question) may run in the main checkout — but the moment the task transitions to producing output, a worktree is created before any write.

## Mandatory Setup — Step 0 of Every Task

Before any other action, every skill and every agent runs this protocol:

```bash
# 1. Determine you're in the main checkout (not already in a worktree).
MAIN_REPO="$(git rev-parse --show-toplevel)"
if [ "$MAIN_REPO" != "$(git rev-parse --git-common-dir | xargs dirname)" ]; then
  # We are already inside a worktree — verify it matches the current task and continue.
  echo "Already in worktree: $(pwd) on branch $(git branch --show-current)"
else
  # We are in the main checkout — create a worktree for this task.

  # 2. Derive the branch name from the task type. Use the existing conventions:
  #    Features:   {STORY-ID}/{short-description}        e.g. US-042/email-validation
  #    Tech:       tech/{short-description}              e.g. tech/improve-git-hooks
  #    Deps:       deps/{package-or-batch}               e.g. deps/kotlin-2.1
  #    Hotfix:     hotfix/{version}/{short-description}  e.g. hotfix/v1.2.1/fix-login-crash
  #    Bug:        {BUG-ID}/{short-description}          e.g. BUG-017/null-profile-crash
  #    Investigation/triage that does not yet have an ID: triage/{short-description}
  BRANCH="<derived-per-task>"

  # 3. Build the worktree path. Convention: ../{repo}-worktrees/{branch-slug}
  WORKTREE_DIR="${MAIN_REPO}/../$(basename "$MAIN_REPO")-worktrees/${BRANCH//\//-}"

  # 4. Resolve the base branch, make sure it's current, then create the worktree.
  #    BASE is main by default. It is an epic integration branch (epic/{EPIC-ID}-{slug})
  #    when the task belongs to an epic that has one — the worktree then branches off
  #    the integration branch AND its PR merges back into it. See "Base Branch
  #    Resolution" below.
  BASE="main"   # or "epic/US-100-checkout" when working inside an epic
  git -C "$MAIN_REPO" fetch origin "$BASE"
  git -C "$MAIN_REPO" worktree add -b "$BRANCH" "$WORKTREE_DIR" "origin/$BASE"

  # 5. Move into the worktree. EVERY subsequent command runs here.
  cd "$WORKTREE_DIR"

  # 6. Verify.
  pwd                              # must equal $WORKTREE_DIR
  git branch --show-current        # must equal $BRANCH
fi
```

If either verification fails, **stop immediately and report**. Do not proceed in the wrong directory. Do not modify files in the main checkout.

## Branch Naming — Quick Reference

| Task type | Branch pattern | Example |
|-----------|----------------|---------|
| User story / feature | `{STORY-ID}/{slug}` | `US-042/email-validation` |
| Tech task | `tech/{slug}` | `tech/improve-git-hooks` |
| Dependency upgrade | `deps/{package-or-batch}` | `deps/kotlin-2.1` |
| Hotfix | `hotfix/{version}/{slug}` | `hotfix/v1.2.1/fix-login-crash` |
| Bug fix | `{BUG-ID}/{slug}` | `BUG-017/null-profile-crash` |
| Triage before ID assigned | `triage/{slug}` | `triage/crash-spike-2026-05-21` |
| Epic integration branch | `epic/{EPIC-ID}-{slug}` | `epic/US-100-checkout` |

Hotfix branches cut from the release tag instead of `origin/main` — replace step 4 above with `git worktree add -b "$BRANCH" "$WORKTREE_DIR" v{X.Y.Z}`.

## Base Branch Resolution

The base branch — what a worktree branches **off from** and what its PR merges **into** — is the same branch on both ends (hotfixes excepted: they cut from a release tag and merge per the hotfix process), and is resolved per task in this order:

1. **Explicit instruction** — @Zeyad (or the dispatching skill) named a base: `--base <branch>` or "branch off `epic/US-100-checkout`". Use it verbatim after verifying it exists on the remote.
2. **Epic integration branch** — the task belongs to an epic with an `epic/{EPIC-ID}-{slug}` branch. Story branches for that epic cut from and PR back into the integration branch; the integration branch itself merges to `main` in one reviewed PR when the epic completes. If the epic linkage is inferred rather than stated, confirm before creating the worktree.
3. **Hotfix** — cut from the release tag `v{X.Y.Z}`; merge per the hotfix process (release branch + `main`).
4. **Default** — `origin/main`.

An epic integration branch is itself created from `origin/main` (`git branch epic/{EPIC-ID}-{slug} origin/main && git push -u origin epic/{EPIC-ID}-{slug}`) and is NOT a worktree task branch — no direct commits on it; it only receives story-branch PR merges and periodic `main` merges to stay current.

## Board Updates Happen in the Worktree

`board-context.md` is edited in the worktree alongside the task work. The board update commits onto the task branch and merges back to `main` via the same PR as the code change. There is no "Atlas updates the board in the main checkout" path — that would violate the worktree-first rule.

**Every board edit ships inside the PR that carries the change it describes.** There is no board-only PR, and no board commit directly on `main`. See `@.claude/rules/shared/board-in-pr.md` for the full policy — where each transition commits, when `→ Done` is written, and where planning-only board edits land.

If multiple worktrees touch `board-context.md` in parallel, the second PR to merge will hit a conflict and must rebase. That's expected and acceptable — the cost is small, the alternative (a privileged main-checkout writer) is worse.

## Parallel Sessions

This rule is the entire arbitration mechanism. Two sessions running at the same time will:

1. Each create their own worktree under `../{repo}-worktrees/...`, with distinct branch names derived from their respective task IDs.
2. Operate independently — no file conflicts, no branch conflicts, no shared in-flight state.
3. Each open a PR via `/create-pr` and merge back independently.

There is no lock file, no busy-check, no "who got here first" logic. The rule of "every task gets its own worktree" makes coordination unnecessary.

## Cleanup

Cleanup is automatic via `/create-pr`'s post-PR sweep: each `/create-pr` run enumerates `git worktree list`, checks each branch against `gh pr list --state merged`, and removes the worktree + safe-deletes the branch for any merged ones.

To abandon an unmerged worktree (failed task, wrong approach), run from the main checkout:

```bash
cd "$MAIN_REPO"
git worktree remove "$WORKTREE_DIR"     # add --force if uncommitted work
git branch -D "$BRANCH"                  # -D because the branch is unmerged
git worktree prune                       # if the directory was removed manually
```

## Exceptions

There are exactly three exceptions to the worktree-first rule, and they are narrow:

1. **Read-only Q&A.** Answering a question by reading files, running `git log`, inspecting state — no worktree needed. If the answer turns into "let's change this," create the worktree before the first write.
2. **Initial repo setup** (`/setup-repo`). The first scaffolding pass on a fresh repo happens in the main checkout because there's nothing to worktree from yet. After setup completes, the rule applies to all subsequent work.
3. **Worktree cleanup** (the `/create-pr` sweep). Removing a merged worktree runs from the main checkout by necessity — you can't `git worktree remove` the worktree you're standing in.

Any other "this case is special" claim is wrong. Push back and create the worktree.
