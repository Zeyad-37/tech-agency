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
2. **Re-running is safe.** Every create is preceded by a lookup that matches the task's exact
   `[TASK-ID] ` title prefix client-side (Step 4) — never a bare search hit. A run interrupted halfway is resumed by running it again, not by cleaning up by hand.

See `@.claude/rules/shared/board-adapter.md` § `"github"` for the column mapping, identity rules,
and operation translations this skill establishes.

## Step 1: Preflight

Stop on any failure here — a partial migration is worse than none.

**First, locate the parser.** `parse_board.py` ships inside the installed plugin, not in the repo
being migrated, so a repo-relative path finds it only inside tech-agency itself. Resolve it the
same way the `pre-push` hook resolves `mirror.sh`: a local copy, then `$CLAUDE_PLUGIN_ROOT`, then
the newest installed version in the plugin cache.

```bash
# resolve-parser: parse_board.py lives in the installed plugin, not in this repo.
PARSER=""
for c in ".claude/skills/migrate-board/parse_board.py" \
         "${CLAUDE_PLUGIN_ROOT:-}/skills/migrate-board/parse_board.py"; do
  [ -n "$c" ] && [ -f "$c" ] && PARSER="$c" && break
done
if [ -z "$PARSER" ]; then
  PARSER=$(find "$HOME/.claude/plugins/cache" -maxdepth 6 \
             -path '*/tech-agency/*/skills/migrate-board/parse_board.py' 2>/dev/null \
           | sort -V | tail -1)
fi
if [ -z "$PARSER" ]; then
  echo "STOP: parse_board.py not found. Install the plugin (claude plugin install tech-agency@tech-agency) or set CLAUDE_PLUGIN_ROOT."
  exit 1
fi
echo "Using $PARSER"
```

Every later step runs `python3 "$PARSER"`. Each shell starts fresh, so re-run this block in any new
shell rather than typing a path by hand.

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

**Ask the user two questions before going further** — both change what gets written, and neither
has a safe default to assume silently:

1. **Done history** — `DONE_MODE=issues` creates every Done row as a closed issue, so the full
   history is searchable in GitHub and epics roll up correctly. `DONE_MODE=freeze` leaves Done rows
   as markdown history only: far fewer writes on a long-lived board, at the cost of an epic whose
   stories are partly done showing fewer children than it had.
2. **Tech debt** — migrate the debt backlog too (`DEBT=yes`), or leave it as a file (`DEBT=no`).

```bash
DONE_MODE=freeze          # or: issues
DEBT_FLAG=--include-tech-debt   # or empty when DEBT=no
```

The debt backlog is found at `docs/guides/tech-debt/backlog.md`, or at `docs/tech-debt/backlog.md`
on repos set up before the docs reorganisation. **Both present is an error**: importing either
alone would drop the other's items, so merge them first.

## Step 2: Repair, then parse

Markdown boards corrupt silently — a merge can leave separator rows before their headers, or
sections the schema no longer has, and nothing detects it. Validate before trusting the contents:

```bash
python3 "$PARSER" --check --done "$DONE_MODE" $DEBT_FLAG
```

`--done` matters here, not only at parse time. Under `freeze` a Done row is never migrated, so its
ID cell is **not** validated: legacy commentary such as `T-013 (Phase 3 pilot)` stays as written in a
closed quarter instead of forcing an edit to history. Its table structure still is — a cut-off row or
a wrong header damages the frozen archive as much as the live board. Under `issues` every Done row
becomes an issue and must carry a real Task ID.

If it reports problems, **fix them and commit that repair as its own commit** before migrating.
A repair mixed into the migration commit is invisible in history, and the repair is worth reviewing
on its own.

**Older consumers need the most repair**, because their board predates the layout the parser
expects. The classes seen on real boards, and what fixes each:

| Reported | Cause | Repair |
|---|---|---|
| `'## Done' / '## Decisions Log' must not be in the live board` | Board never got the live/archive split | Move Done rows to `docs/board/done-{YYYY}-Q{N}.md` and the log to `docs/board/decisions-log.md` (`board-adapter.md` § markdown) |
| `Backlog header is \| Task ID \| Priority \| Description \|` | An older 3-column schema | Add the `Requested By` column to the header and every row |
| `row(s) starting at 'X' are cut off from their table` | A blank line or `---` split one table in two | Delete the blank line / `---` so the rows rejoin their table |
| `row has N cells, … an unescaped '\|'` | A literal `\|` inside a description | Put a backslash before it, `\\|` — the parser splits only on unescaped pipes and reads `\\|` back as a literal `\|` |
| `'T-053.7 (follow-up)' is not a Task ID` | Commentary in the ID cell of a row that will be migrated (any live column; Done under `DONE_MODE=issues`) | Move the commentary into the description |
| `table under 'X' is missing an '#' or 'ID' column` | A debt table keyed by `Task ID` or similar | Rename that header cell to `ID` |
| `table under 'X' is missing a Description column` | A debt table with the text under another name (`Title`, `Item`) | Rename that header cell to `Description` |
| `is listed N times as active debt` / `both active and resolved` / `board task is Done` | Contradictions in the debt data | **A human decides** which entry is true — never pick one automatically |
| `table under 'X' is missing a Severity column` | A debt table that may be open work or history | **A human decides**: add a Severity column if it is open, or put it under a resolved heading if it is finished (see *Resolved headings* below). A table under a resolved heading is history whatever its columns |

The two "a human decides" rows are different in kind: the rest are mechanical, but a duplicated,
contradictory or unclassifiable debt item is a question about what is actually true, so surface it
rather than resolving it.

**Resolved headings.** Whether a debt table is history is decided by its headings, not its columns:

- A heading is **open** if it contains an open-marker, a whole word (case-insensitive) from this
  list: `not`, `unresolved`, `undone`, `unfixed`, `unfinished`, `open`, `active`, `pending`,
  `outstanding`, `remaining`, `yet`, `todo`, `to do`, `partially`, `partial`, `reopen`, `reopened`,
  `almost`, `nearly`, `close to` — or a `?` anywhere in it, since a question asserts nothing. It is a
  list, not a prefix: `under`, `until` and `unless` are not open-markers.
- Otherwise it is **resolved** if it contains the whole word `resolved`, `closed` or `done`.
- Otherwise it has **no status**.

The parser walks the table's enclosing headings nearest-first — the nearest heading above it, then
the nearest above that of a strictly smaller level, up to `##`; headings inside fenced code do not
count — and the first heading with a status decides. With no status anywhere, the table is not
resolved. So `## Resolved` → `### 2026 Q2` is resolved, `## Resolved` → `### Still open` is not,
`## Resolved under T-027` and `## Closed until 2026-06` are resolved, and `## Not done yet`,
`## Unresolved` and `## Partially resolved` are not. Words the list does not know, such as
`Completed`, `Fixed` or `Archived`, give no status — a finished table under one is imported or reported as a
problem, never silently dropped; rename the heading if it is history.

Then parse:

```bash
BOARD_JSON=$(mktemp "${TMPDIR:-/tmp}/board-XXXXXX.json")
python3 "$PARSER" --json --done "$DONE_MODE" > "$BOARD_JSON"
# Only when migrating debt — DEBT_FLAG is set in Step 1:
if [ -n "$DEBT_FLAG" ]; then
  DEBT_JSON=$(mktemp "${TMPDIR:-/tmp}/debt-XXXXXX.json")
  python3 "$PARSER" --tech-debt --done "$DONE_MODE" > "$DEBT_JSON"
fi
```

Show the user the counts per column, the Done mode, and — when migrating debt — the active item
count, how many are already on the board (`on_board`, which become labels rather than issues — and
of those, how many via the `Board Task` column), the `notes` for debt whose Board Task is Done, and
which resolved tables will not migrate. **Stop for confirmation** before any write. This is the dry
run: creating dozens of issues is hard to undo.

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

`agent:{name}` labels are not in this list because the agent names come from the board itself. Step 4
creates each one — idempotently, with `--force` — immediately before the first issue that uses it,
so no `gh issue create` ever references a label that does not exist.

## Step 4: Create the issues

For each task in `$BOARD_JSON`, in this order — **Backlog, Ready, In Progress, Review, Blocked,
then Done** — so that parents exist before Step 5 links their children. `parse_board.py --json`
already emits tasks in that order.

**Always search before creating**, and decide on an **exact** title-prefix match made client-side.
The `--search` only narrows the candidates; whether GitHub's tokenizer lets `"[T-016]"` match
`[T-016.4] …` is not something this skill controls, so the search result is never trusted as the
answer. `startswith("[T-016] ")` — with the trailing space — cannot match `[T-016.4] …`.

Labels are built as a bash array, so an empty `agent` or `priority` adds **no** flag at all rather
than a malformed `--label "priority:"`. On a board whose In Progress / Review / Blocked / Done
schemas have no `Priority` column, that is every task in those columns.

```bash
# Tasks are read on fd 3 so no gh call inside the loop can swallow the list from stdin.
while read -r task <&3; do
  TASK_ID=$(jq -r '.task_id' <<<"$task")
  COLUMN=$(jq -r '.column' <<<"$task")
  DESCRIPTION=$(jq -r '.description' <<<"$task")
  AGENT=$(jq -r '.agent // ""' <<<"$task")
  PRIORITY=$(jq -r '.priority // ""' <<<"$task")
  # Extend BODY with the row's remaining fields per the bullets below the block.
  BODY="Migrated from $(jq -r '.source' <<<"$task") on $(date +%F)."

  # Idempotency guard: exact "[TASK-ID] " prefix, decided client-side.
  existing=$(gh issue list --state all --limit 100 --search "$TASK_ID in:title" \
               --json number,title \
             | jq -r --arg p "[$TASK_ID] " \
                 'map(select(.title | startswith($p))) | .[0].number // empty')
  if [ -n "$existing" ]; then echo "skip $TASK_ID -> #$existing"; continue; fi

  labels=()
  # Done has no status label — Done is the issue being closed.
  [ "$COLUMN" != "done" ] && labels+=(--label "status:$COLUMN")
  if [ -n "$AGENT" ]; then
    gh label create "agent:$AGENT" --color "bfdadc" --force >/dev/null   # idempotent
    labels+=(--label "agent:$AGENT")
  fi
  [ -n "$PRIORITY" ] && labels+=(--label "priority:$PRIORITY")

  url=$(gh issue create --title "[$TASK_ID] $DESCRIPTION" --body "$BODY" "${labels[@]}")
  if [ "$COLUMN" = "done" ]; then
    gh issue close "${url##*/}" --reason completed
  fi
done 3< <(jq -c '.[]' "$BOARD_JSON")
```

- **Title** carries the Task ID prefix. That prefix is the identity — branch names, commit
  prefixes and artifact filenames all key off it, and `board.read_task()` resolves by searching it.
- **Body** carries whatever the row could not: acceptance criteria, links to
  `docs/artifacts/…`, the original `Started` / `Waiting Since` date, and a
  `Migrated from board-context.md on {date}` line for provenance.
- **Assignee** is the human owner (`gh repo view --json owner`), never the agency agent — @Kai and
  @Atlas have no GitHub accounts. The agent is the `agent:` label.
- **Done rows** exist in `$BOARD_JSON` only when `DONE_MODE=issues`. They are created and then
  closed: `gh issue close "$n" --reason completed`. Preserve the original completion date in the
  body; the close timestamp will be today's and that is fine, as the body holds the truth. Under
  `freeze` there are no Done rows to create — they stay in the frozen `docs/board/done-*.md`.
- **Blocked rows** get the blocker reason as a comment, not squeezed into the title.

## Step 4b: Import tech debt (skip when `DEBT_FLAG` is empty)

Before verification, so Step 7 can check it. Each item in `$DEBT_JSON` takes **one of two paths**:

- **`on_board: true`** — the item is already on the board, and `board_task` names the task: either
  the debt's own ID (some repos pull debt onto the board under that ID) or the one live task its
  `Board Task` column names. IDs are matched by number — `TD-002` is the board's `TD-2`, `T-02` is
  `T-2`, but `T-053.10` is not `T-053.1` — and `board_task` is the ID **as written on the board**,
  the title prefix its issue carries. Label **that task's issue**; do not create an issue for the debt. A
  second issue would either collide with `[TD-n]` — the search-before-create guard silently skips
  whichever came second — or sit unlinked beside the task that resolves it. Several debt items may
  share one task; the issue then carries **one** `severity:` label, `issue_severity` — the highest
  among them — never one per item. When `board_task` differs from the debt's ID, also leave a comment carrying the
  debt's ID, severity and description, so its detail is not lost with no `[TD-n]` issue to hold it.
- **`on_board: false`** — create it on the Backlog, with the same exact-prefix guard as Step 4.
  That includes items whose Board Task is **Done**: finished work cannot carry open debt, so those
  get their own issue, and the parser lists them in `notes` for the report.

```bash
# Exact "[ID] " title-prefix lookup, decided client-side (see Step 4).
issue_for() {
  gh issue list --state all --limit 100 --search "$1 in:title" --json number,title \
    | jq -r --arg p "[$1] " 'map(select(.title | startswith($p))) | .[0].number // empty'
}

STOPPED=""
while read -r item <&3; do
  TASK_ID=$(jq -r '.task_id' <<<"$item")
  SEVERITY=$(jq -r '.severity' <<<"$item")              # this item's own, for the comment
  ISSUE_SEVERITY=$(jq -r '.issue_severity' <<<"$item")  # the one label the issue carries
  BOARD_TASK=$(jq -r '.board_task // empty' <<<"$item")

  if [ -n "$BOARD_TASK" ]; then
    n=$(issue_for "$BOARD_TASK")
    if [ -z "$n" ]; then
      echo "STOP: $TASK_ID maps to $BOARD_TASK, which has no issue — run Step 4 first"
      STOPPED=1
      break
    fi
    gh issue edit "$n" --add-label tech-debt --add-label "severity:$ISSUE_SEVERITY"
    if [ "$BOARD_TASK" != "$TASK_ID" ]; then
      # Idempotent: the hidden marker stops a re-run posting the same comment twice.
      MARK="<!-- migrated-debt:$TASK_ID -->"
      if ! gh issue view "$n" --json comments --jq '.comments[].body' | grep -qF "$MARK"; then
        gh issue comment "$n" --body "$MARK"$'\n'"**Tech debt $TASK_ID** ($SEVERITY), resolved by this task:"$'\n\n'"$(jq -r '.description' <<<"$item")"
      fi
    fi
    continue
  fi

  existing=$(issue_for "$TASK_ID")
  if [ -n "$existing" ]; then echo "skip $TASK_ID -> #$existing"; continue; fi

  # Body: every field of the row, so the prose transfers intact.
  BODY=$(jq -r '.fields | to_entries | map("**\(.key):** \(.value)") | join("\n\n")' <<<"$item")
  BODY+=$'\n\n'"Migrated from $(jq -r '.source' <<<"$item"):$(jq -r '.line' <<<"$item") on $(date +%F)."
  # .title is "[TD-n] description", already cut to GitHub's 256-character cap.
  gh issue create --title "$(jq -r '.title' <<<"$item")" --body "$BODY" \
    --label status:backlog --label tech-debt --label "severity:$ISSUE_SEVERITY"
done 3< <(jq -c '.items[]' "$DEBT_JSON")

if [ -n "$STOPPED" ]; then
  echo "Tech-debt import halted. Do NOT continue to Step 5 — fix the cause above and re-run Step 4b." >&2
  exit 1
fi
```

Descriptions are often long, and GitHub caps titles at 256 characters. The parser's `title` field
is already cut at a word boundary (ending in `…`) to fit, and keeps the `[TD-n] ` prefix the
search-before-create guard matches on; the body carries the full description.

Resolved tables (`not_migrated` in the JSON) are never imported — an issue is open work, and those
rows are the record of work already finished.

## Step 5: Link epics as sub-issues

Any Task ID with a dotted suffix (`T-016.4`) is a child of its stem (`T-016`). `gh` supports this
directly — no GraphQL, and only the `repo` scope, so this works even when Step 6 is skipped:

```bash
gh issue edit "$PARENT_NUM" --add-sub-issue "$CHILD_NUM"
```

If the stem has no issue of its own, create one first as the epic, labelled with the column its
children mostly sit in. Re-running is safe: adding an existing sub-issue is a no-op.

**Except when `parent_frozen` is true.** Under `DONE_MODE=freeze`, a story whose epic is a Done row
has no epic issue on purpose — creating one would resurrect finished work as an open issue. Leave
that story unlinked and count it for the report.

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

Do not freeze the markdown until verification is clean:

```bash
python3 "$PARSER" --verify --done "$DONE_MODE" $DEBT_FLAG
```

It re-parses the board (refusing outright if `--check` would fail) and compares every column
against GitHub **in both directions**, over a fully paginated issue list — no `--limit` to truncate at:

- **MISSING** — a Task ID in the markdown with no issue in that column (Done = closed as completed;
  a close as *not planned* is not Done).
- **EXTRA** — an issue in that column whose Task ID is not in the markdown.
- **DUPLICATE** — a Task ID with more than one issue, the exact failure Step 4's guard exists to
  prevent. Closing the extras as *not planned* resolves it.
- **NO TABLE** — a column's source file exists but no table for that column was found in it, so a
  wholly dropped column cannot pass as an empty one. A table holding only the `—` placeholder is a
  genuinely empty column and passes.

Under `DONE_MODE=freeze` the Done line reads `frozen` and is not compared. With
`--include-tech-debt`, a `tech-debt` line checks every active item is an **open** issue carrying
`tech-debt` and exactly one `severity:` label, `issue_severity` (the highest among every item on that
issue) — its own issue, or the board task it was merged onto:

- **MISSING** — no issue for the item. **NOT LABELLED** — the issue the item lives on exists but
  lacks `tech-debt`, which is what a skipped `on_board` merge looks like. For a merged item that
  issue is its `board_task`'s, not a `[TD-n]` — so a board task carrying debt is never an EXTRA.
- **CLOSED** — active debt on a closed issue, invisible to `/replenish`'s label query.
- **WRONG SEVERITY** — the issue lacks `severity:{issue_severity}` or carries any other `severity:`
  label as well; the note names both. **EXTRA** — an open `tech-debt` issue that is not in the backlog.

Debt-only issues carry `status:backlog`, but they are **not** counted against the Backlog column —
otherwise every imported item would show as a Backlog EXTRA.

**Any mismatch stops the migration** with the markdown untouched — investigate, fix, and re-run from
Step 4, which will skip everything already created.

The parser has its own tests (standard library only):

```bash
# PYTHONDONTWRITEBYTECODE: the tests live in the installed plugin; do not litter its cache.
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s "$(dirname "$PARSER")" -p 'test_*.py'
```

## Step 8: Freeze the markdown, flip the backend

Only after Step 7 is clean. Prepend to `board-context.md`, `docs/board/backlog.md`, and each
`docs/board/done-*.md` (under `DONE_MODE=freeze`, add a line to the Done files saying their rows
were **not** migrated, so nobody goes looking for them in GitHub):

```markdown
> **Frozen {YYYY-MM-DD}.** This board moved to GitHub Issues. Kept as history; not updated.
> Live board: `gh issue list`, or the repo's Projects board.
> See `@.claude/rules/shared/board-adapter.md`.
```

**`docs/board/decisions-log.md` is NOT frozen.** It is a versioned document, not tracked work — it
stays live and in the repo. Same for everything under `docs/artifacts/`.

**The tech-debt backlog**, when imported in Step 4b, is frozen with the same banner — at whichever
path it was found (`$DEBT_JSON`'s `file`), including the legacy `docs/tech-debt/backlog.md`. That
is what lets `/replenish` pull its 15–20 % debt allocation with a label query. Note in the banner
that resolved tables in the file were not migrated. `resolved.md` is a record; leave it alone.

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
- The Done mode — and under `freeze`, how many Done rows stayed as markdown and how many stories
  were left unlinked because their epic is frozen
- Tech debt: issues created, items merged onto existing board tasks (own ID vs Board Task column),
  items whose Board Task is Done, resolved rows not migrated — or that debt was left as a file
- Epic links made
- Whether the Projects v2 board was created or skipped for scope, and the `gh auth refresh -s project` remedy
- Which files were frozen, and that nothing was deleted
- That `board_backend` is now `github`

## Notes

**Rate limits.** A large board is a lot of `gh issue create` calls, and a tech-debt import can
double it. GitHub throttles content creation at roughly 500 writes an hour, so a board plus a few
hundred debt items will hit it. When you hit a secondary rate limit, wait and re-run — Steps 4 and
4b both search before creating, so resumption is free. `DONE_MODE=freeze` is the biggest lever on
volume for a long-lived board.

**Issue numbers are not Task IDs.** Never renumber tasks to match issue numbers. The Task ID is the
identity; `#47` is an implementation detail that appears only in `Closes #47`.

**This skill never runs itself against another repo.** Migration writes to whichever repo `gh repo
view` resolves in the current directory. Confirm that is the intended repo in Step 1 before Step 4.
