---
name: migrate-board
description: "Migrate a markdown Kanban board (board-context.md + docs/board/) to GitHub Issues + Projects v2, and switch board_backend to github. Repairs table corruption first, dry-runs before writing, is safe to re-run, and never deletes the markdown files — it freezes them as history. Use when the user says 'migrate board', 'move to github issues', 'migrate to github projects', 'switch board backend', or 'the markdown board is not scaling'."
---

# Migrate Board — Markdown → GitHub Issues + Projects v2

Moves a project's task tracking from `board-context.md` + `docs/board/` to GitHub Issues, with a
repo-scoped Projects v2 board when the token allows it. Runs on any repo with a GitHub remote.

**Two guarantees this skill must never break:**

1. **Nothing is deleted.** The markdown files stay in the repo, frozen with a banner. A migration
   that loses history is not a migration.
2. **Re-running is safe.** Every create is preceded by a search for the task's `[TASK-ID]` title
   prefix. A run interrupted halfway is resumed by running it again, not by cleaning up by hand.

See `@.claude/rules/shared/board-adapter.md` § `"github"` for the column mapping, identity rules,
and operation translations this skill establishes.

## Step 1: Preflight

Stop on any failure here — a partial migration is worse than none.

```bash
gh auth status                       # authenticated?
gh repo view --json nameWithOwner,hasIssuesEnabled   # remote exists, Issues enabled?
grep -n '"board_backend"' .claude/settings.json      # current backend
ls board-context.md docs/board/ 2>/dev/null          # is there a board to migrate?
```

- **Issues disabled** → stop and ask the user to enable them; nothing else works.
- **`board_backend` already `github`** → this repo is migrated. Run Step 7 (verify) only, and report.
- **No `board-context.md`** → nothing to migrate. Offer to set `board_backend` to `github` and
  create the labels (Step 3) so the repo starts on GitHub with an empty board.

Check the Projects v2 scope separately, because its absence is **not** a failure:

```bash
gh project list --owner "$(gh repo view --json owner --jq .owner.login)" >/dev/null 2>&1 \
  && echo "PROJECT_SCOPE=yes" || echo "PROJECT_SCOPE=no"
```

`no` means the migration runs label-only and skips Step 6. Say so once, and tell the user
`gh auth refresh -s project` unlocks the board view later — re-running this skill will then create
it. Do not treat it as an error and do not stop.

## Step 2: Repair, then parse

Markdown boards corrupt silently — a merge can leave separator rows before their headers, or
sections the schema no longer has, and nothing detects it. Validate before trusting the contents:

```bash
python3 .claude/skills/migrate-board/parse_board.py --check
```

If it reports problems, **fix them and commit that repair as its own commit** before migrating.
A repair mixed into the migration commit is invisible in history, and the repair is worth reviewing
on its own. Then parse:

```bash
python3 .claude/skills/migrate-board/parse_board.py --json > /tmp/board.json
```

Show the user the counts per column and **stop for confirmation** before any write. This is the
dry run: creating dozens of issues is hard to undo.

## Step 3: Create the labels

Idempotent — `--force` updates an existing label rather than failing.

```bash
for l in "status:backlog:ededed" "status:ready:0e8a16" "status:in-progress:1d76db" \
         "status:review:fbca04" "status:blocked:d93f0b" \
         "priority:P0:b60205" "priority:P1:d93f0b" "priority:P2:fbca04" "priority:P3:c2e0c6" \
         "tech-debt:5319e7" "severity:high:b60205" "severity:medium:fbca04" "severity:low:c2e0c6"; do
  name="${l%:*}"; color="${l##*:}"
  gh label create "$name" --color "$color" --force
done
```

There is deliberately no `status:done` label — Done is the issue being **closed**, which is what
makes `Closes #N` in a PR body perform the transition (`@.claude/rules/shared/board-in-pr.md`).

Agent labels are created on demand in Step 4 as `agent:{name}`.

## Step 4: Create the issues

For each task in `/tmp/board.json`, in this order — **Backlog, Ready, In Progress, Review, Blocked,
then Done** — so that parents exist before Step 5 links their children.

**Always search before creating:**

```bash
existing=$(gh issue list --search "\"[$TASK_ID]\" in:title" --state all --json number --jq '.[0].number')
if [ -n "$existing" ]; then echo "skip $TASK_ID -> #$existing"; continue; fi
```

Then create:

```bash
gh issue create \
  --title "[$TASK_ID] $DESCRIPTION" \
  --body "$BODY" \
  --label "status:$COLUMN" \
  --label "agent:$AGENT" \
  --label "priority:$PRIORITY"
```

- **Title** carries the Task ID prefix. That prefix is the identity — branch names, commit
  prefixes and artifact filenames all key off it, and `board.read_task()` resolves by searching it.
- **Body** carries whatever the row could not: acceptance criteria, links to
  `docs/artifacts/…`, the original `Started` / `Waiting Since` date, and a
  `Migrated from board-context.md on {date}` line for provenance.
- **Assignee** is the human owner (`gh repo view --json owner`), never the agency agent — @Kai and
  @Atlas have no GitHub accounts. The agent is the `agent:` label.
- **Done rows** are created and then closed: `gh issue close "$n" --reason completed`. Preserve the
  original completion date in the body; the close timestamp will be today's and that is fine, as
  the body holds the truth.
- **Blocked rows** get the blocker reason as a comment, not squeezed into the title.

## Step 5: Link epics as sub-issues

Any Task ID with a dotted suffix (`T-016.4`) is a child of its stem (`T-016`). `gh` supports this
directly — no GraphQL, and only the `repo` scope, so this works even when Step 6 is skipped:

```bash
gh issue edit "$PARENT_NUM" --add-sub-issue "$CHILD_NUM"
```

If the stem has no issue of its own, create one first as the epic, labelled with the column its
children mostly sit in. Re-running is safe: adding an existing sub-issue is a no-op.

## Step 6: Create the Projects v2 board (skip if `PROJECT_SCOPE=no`)

```bash
OWNER=$(gh repo view --json owner --jq .owner.login)
gh project create --owner "$OWNER" --title "$(gh repo view --json name --jq .name) Board"
```

Add a single-select `Status` field with options **Backlog, Ready, In Progress, In Review, Blocked,
Done**, matching `board-adapter.md`'s column mapping. Add every open issue as an item and set its
Status from the `status:` label. The labels remain the source of truth — the project is a view over
them, which is why losing the scope degrades cleanly rather than breaking the board.

## Step 7: Verify before freezing

Do not freeze the markdown until the counts match:

```bash
python3 .claude/skills/migrate-board/parse_board.py --verify
```

It re-parses the board and compares each column against `gh issue list` by label, Done against
closed issues, and reports any Task ID present in the markdown but missing from GitHub. **Any
mismatch stops the migration** with the markdown untouched — investigate, fix, and re-run from
Step 4, which will skip everything already created.

## Step 8: Freeze the markdown, flip the backend

Only after Step 7 is clean. Prepend to `board-context.md`, `docs/board/backlog.md`, and each
`docs/board/done-*.md`:

```markdown
> **Frozen {YYYY-MM-DD}.** This board moved to GitHub Issues. Kept as history; not updated.
> Live board: `gh issue list`, or the repo's Projects board.
> See `@.claude/rules/shared/board-adapter.md`.
```

**`docs/board/decisions-log.md` is NOT frozen.** It is a versioned document, not tracked work — it
stays live and in the repo. Same for everything under `docs/artifacts/`.

**`docs/guides/tech-debt/backlog.md`** is migrated like the board: each entry becomes an issue
labelled `tech-debt` plus its severity (the prose body transfers intact — an issue body has no
one-line constraint), and the file is frozen with the same banner. This is what lets `/replenish`
pull its 15–20 % debt allocation with a label query. `resolved.md` is a record; leave it alone.

Then flip the backend:

```json
// .claude/settings.json
{ "board_backend": "github" }
```

Commit the freeze banners, the settings change, and the repair from Step 2 (if it was not already
committed separately). Per `@.claude/rules/shared/board-in-pr.md` this is a documentation change
like any other — it goes through a PR.

## Step 9: Report

State plainly:

- Issues created, by column; how many were skipped as already present
- Epic links made
- Whether the Projects v2 board was created or skipped for scope, and the `gh auth refresh -s project` remedy
- Which files were frozen, and that nothing was deleted
- That `board_backend` is now `github`

## Notes

**Rate limits.** A large board is a lot of `gh issue create` calls. If you hit a secondary rate
limit, wait and re-run — Step 4's search-before-create makes resumption free.

**Issue numbers are not Task IDs.** Never renumber tasks to match issue numbers. The Task ID is the
identity; `#47` is an implementation detail that appears only in `Closes #47`.

**This skill never runs itself against another repo.** Migration writes to whichever repo `gh repo
view` resolves in the current directory. Confirm that is the intended repo in Step 1 before Step 4.
