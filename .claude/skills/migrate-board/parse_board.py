#!/usr/bin/env python3
"""Parse, validate and verify a markdown Kanban board for /migrate-board.

Modes:
  --check      Validate table integrity. Exits 1 if the board is corrupt.
  --json       Emit every task as JSON on stdout. Refuses (exit 1) on a corrupt board.
  --tech-debt  Emit the active tech-debt items as JSON. Refuses (exit 1) on a
               corrupt board or a corrupt tech-debt file.
  --verify     Compare the parsed board against GitHub Issues, both directions.
               Exits 1 on any mismatch. Refuses (exit 1) on a corrupt board.

Options:
  --done issues|freeze   `issues` (default) migrates Done rows as closed issues.
                         `freeze` leaves them as markdown history: --json omits
                         them and --verify does not expect them on GitHub.
  --include-tech-debt    --check also validates the tech-debt file; --verify
                         also checks every active debt item on GitHub.

The board's shape is defined in .claude/rules/shared/board-adapter.md; the
per-column schemas in .claude/skills/update-board/SKILL.md.

Tests: .claude/skills/migrate-board/test_parse_board.py (stdlib unittest).
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import subprocess
import sys
from collections import Counter

LIVE = "board-context.md"

# column -> (source file globs, in lookup order; expected header fields)
# Backlog normally lives in docs/board/backlog.md, but /setup-repo's scaffold has
# historically put a `## Backlog` section in the live file — read both, so those
# tasks are never silently dropped.
COLUMNS: dict[str, tuple[list[str], list[str]]] = {
    "backlog":     (["docs/board/backlog.md", LIVE], ["Task ID", "Priority", "Description", "Requested By"]),
    "ready":       ([LIVE],                          ["Task ID", "Priority", "Description", "Assigned To"]),
    "in-progress": ([LIVE],                          ["Task ID", "Agent", "Description", "Started", "Cycle Day"]),
    "review":      ([LIVE],                          ["Task ID", "Agent", "Description", "Reviewer", "Waiting Since"]),
    "blocked":     ([LIVE],                          ["Task ID", "Agent", "Blocker", "Waiting On", "Blocked Since"]),
    "done":        (["docs/board/done-*.md"],        ["Task ID", "Agent", "Description", "Output", "Completed"]),
}
HEADING = {
    "ready": "Ready", "in-progress": "In Progress", "review": "Review",
    "blocked": "Blocked", "backlog": "Backlog", "done": "Done",
}
KNOWN_HEADERS = [h for _, h in COLUMNS.values()] + [["Date", "Decision", "Decided By", "ADR Ref"]]
PLACEHOLDER = "—"
SEPARATOR = re.compile(r"^\|[\s:|-]+\|$")
TASK_ID = re.compile(r"^[A-Za-z]+-\d+(\.\d+)?$")
TITLE_ID = re.compile(r"^\[([A-Za-z]+-\d+(?:\.\d+)?)\] ")

# Tech debt: the current location first, then the pre-reorganisation one that
# older consumers still use. Both present is an error, not a preference — importing
# either alone silently drops the other's items.
DEBT_FILES = ["docs/guides/tech-debt/backlog.md", "docs/tech-debt/backlog.md"]
# "TD-337" (prefixed) or "3" (a bare `#` column); both normalise to TD-<n>.
DEBT_ID = re.compile(r"^(?:TD-(\d+)|(\d+))$")
SEVERITIES = ("high", "medium", "low")
DEBT_LABEL = "tech-debt"
# A header cell that names an ID without being one the parser keys on (`Task ID`).
LOOSE_ID = re.compile(r"\bid\b", re.IGNORECASE)


class BoardError(Exception):
    """The board is not safe to parse."""


UNESCAPED_PIPE = re.compile(r"(?<!\\)\|")


def cells(line: str) -> list[str]:
    """A table row's cells. Splits only on unescaped pipes, as GitHub does, and
    reads each `\\|` back as a literal `|` inside its cell."""
    row = line.strip()
    if row.startswith("|"):
        row = row[1:]
    if row.endswith("|") and not row.endswith("\\|"):
        row = row[:-1]
    return [c.strip().replace("\\|", "|") for c in UNESCAPED_PIPE.split(row)]


def read_lines(path: str) -> list[str]:
    with open(path, encoding="utf-8") as fh:
        return fh.read().split("\n")


def find_files(root: str, pattern: str) -> list[str]:
    full = os.path.join(root, pattern)
    if "*" in pattern:
        return sorted(glob.glob(full))
    return [full] if os.path.exists(full) else []


def section(lines: list[str], heading: str) -> tuple[int, int] | None:
    """Line range of a '## {heading}' section, exclusive of the next '## ' heading."""
    start = None
    for i, line in enumerate(lines):
        if line.startswith("## ") and line[3:].strip().split(" (")[0] == heading:
            start = i
            break
    if start is None:
        return None
    for j in range(start + 1, len(lines)):
        if lines[j].startswith("## "):
            return start, j
    return start, len(lines)


def table_blocks(lines: list[str], offset: int = 0) -> list[tuple[int, list[str]]]:
    """Runs of consecutive '|' lines, as (first line index, lines)."""
    blocks: list[tuple[int, list[str]]] = []
    cur: list[str] = []
    start = 0
    for i, line in enumerate(lines):
        if line.startswith("|"):
            if not cur:
                start = i
            cur.append(line)
        elif cur:
            blocks.append((start + offset, cur))
            cur = []
    if cur:
        blocks.append((start + offset, cur))
    return blocks


def region(col: str, rel: str, lines: list[str]) -> tuple[int, int] | None:
    """Where a column's table lives in a file. The live file must carry the
    column's '## ' section; an archive file may be the table as a whole."""
    rng = section(lines, HEADING[col])
    if rng:
        return rng
    return None if rel == LIVE else (0, len(lines))


def structural_problems(rel: str, lines: list[str]) -> list[str]:
    """Merge-corruption class: separators out of place, headers with no
    separator, header rows inside a table body."""
    problems: list[str] = []
    for start, block in table_blocks(lines):
        if not SEPARATOR.match(block[0]) and (len(block) == 1 or not SEPARATOR.match(block[1])):
            first = cells(block[0])[0]
            if TASK_ID.match(first) or DEBT_ID.match(first):
                # Not a header at all: data rows split off their table by a blank line
                # or a '---'. Markdown renders the first as a header, and every row in
                # the fragment — including a lone single row — would be dropped.
                problems.append(f"{rel}:{start + 1}: {len(block)} row(s) starting at '{first}' are cut "
                                f"off from their table by a blank line or '---' above — join them back")
            else:
                problems.append(f"{rel}:{start + 1}: table header with no separator row after it")
        for k, line in enumerate(block):
            n = start + k + 1
            is_sep = bool(SEPARATOR.match(line))
            if k == 0 and is_sep:
                problems.append(f"{rel}:{n}: separator row with no header above it — the table will not render")
            elif k > 1 and is_sep:
                problems.append(f"{rel}:{n}: separator row inside a table body — two tables have merged")
            elif k > 1 and cells(line) in KNOWN_HEADERS:
                problems.append(f"{rel}:{n}: header row inside a table body — two tables have merged")
    return problems


def column_tables(root: str, col: str) -> list[dict]:
    """Every table found for a column: its file, declared vs actual header, rows."""
    sources, header = COLUMNS[col]
    found: list[dict] = []
    for pattern in sources:
        for path in find_files(root, pattern):
            rel = os.path.relpath(path, root)
            lines = read_lines(path)
            rng = region(col, rel, lines)
            if rng is None:
                continue
            for start, block in table_blocks(lines[rng[0]:rng[1]], offset=rng[0]):
                found.append({
                    "col": col, "source": rel, "line": start + 1,
                    "header": header, "actual": cells(block[0]),
                    "rows": [(start + k + 1, l) for k, l in enumerate(block)
                             if k > 0 and not SEPARATOR.match(l)],
                })
    return found


def check(root: str) -> list[str]:
    """Every reason the board is not safe to migrate. Empty list == valid."""
    problems: list[str] = []
    seen: set[str] = set()
    for sources, _ in COLUMNS.values():
        for pattern in sources:
            for path in find_files(root, pattern):
                rel = os.path.relpath(path, root)
                if rel not in seen:
                    seen.add(rel)
                    problems += structural_problems(rel, read_lines(path))

    for col in COLUMNS:
        for t in column_tables(root, col):
            if t["actual"] != t["header"]:
                problems.append(
                    f"{t['source']}:{t['line']}: {HEADING[col]} header is "
                    f"| {' | '.join(t['actual'])} | but the schema is "
                    f"| {' | '.join(t['header'])} | — cells would be mapped to the wrong fields")
                continue
            for n, line in t["rows"]:
                c = cells(line)
                if c and c[0] in t["header"][:1]:
                    continue  # a stray header row; reported structurally
                if len(c) != len(t["header"]):
                    problems.append(f"{t['source']}:{n}: row has {len(c)} cells, {HEADING[col]} expects {len(t['header'])}")
                elif c[0] != PLACEHOLDER and not TASK_ID.match(c[0]):
                    problems.append(f"{t['source']}:{n}: '{c[0]}' is not a Task ID — the row would be dropped")

    live = os.path.join(root, LIVE)
    if os.path.exists(live):
        lines = read_lines(live)
        for heading, home in (("Done", "docs/board/done-{YYYY}-Q{N}.md"),
                              ("Decisions Log", "docs/board/decisions-log.md")):
            if section(lines, heading):
                problems.append(
                    f"{LIVE}: '## {heading}' must not be in the live board — it belongs in "
                    f"{home} (board-adapter.md)")
    return problems


def notices(root: str) -> list[str]:
    """Non-fatal findings --check reports alongside a valid board. A `## Backlog`
    section in the live file is off-layout but lossless: its rows are parsed and
    migrated like docs/board/backlog.md's, so it must be seen, not block."""
    found: list[str] = []
    live = os.path.join(root, LIVE)
    if os.path.exists(live) and section(read_lines(live), "Backlog"):
        n = sum(1 for t in column_tables(root, "backlog") if t["source"] == LIVE
                for _, l in t["rows"] if cells(l)[0] != PLACEHOLDER)
        found.append(f"{LIVE}: has a '## Backlog' section ({n} task(s)) — board-adapter.md keeps "
                     f"Backlog in docs/board/backlog.md. Its rows ARE parsed and will be migrated.")
    return found


def parse(root: str) -> list[dict]:
    """Tasks in migration order (COLUMNS order). Raises BoardError on a corrupt board."""
    problems = check(root)
    if problems:
        raise BoardError("\n".join(problems))
    tasks: list[dict] = []
    for col in COLUMNS:
        for t in column_tables(root, col):
            for _, line in t["rows"]:
                c = cells(line)
                if c[0] == PLACEHOLDER:
                    continue
                row = dict(zip(t["header"], c))
                tasks.append({
                    "task_id": c[0],
                    "column": col,
                    "description": row.get("Description") or row.get("Blocker", ""),
                    "agent": row.get("Agent") or row.get("Assigned To", ""),
                    "priority": row.get("Priority", ""),
                    "fields": row,
                    "source": t["source"],
                    "parent": c[0].rsplit(".", 1)[0] if "." in c[0] else None,
                })
    return tasks


def debt_file(root: str) -> str | None:
    """The tech-debt backlog to import, relative to root, or None if there is none."""
    present = [p for p in DEBT_FILES if os.path.exists(os.path.join(root, p))]
    if len(present) > 1:
        raise BoardError(
            f"tech debt exists at both {present[0]} and {present[1]} — merge them into "
            f"{DEBT_FILES[0]} first; importing either alone drops the other's items")
    return present[0] if present else None


def normalize_debt_id(raw: str) -> str | None:
    m = DEBT_ID.match(raw.strip())
    if not m:
        return None
    return f"TD-{m.group(1) if m.group(1) is not None else m.group(2)}"


def debt_tables(root: str, rel: str) -> list[dict]:
    """Tables in the debt file, located by header NAME rather than position —
    consumers order the columns differently. A table with an ID and Description
    column is debt; it is `active` when it also has Severity, else `resolved`."""
    lines = read_lines(os.path.join(root, rel))
    found: list[dict] = []
    for start, block in table_blocks(lines):
        if len(block) < 2 or not SEPARATOR.match(block[1]):
            continue  # structural_problems reports this
        header = cells(block[0])
        lower = [h.lower().strip("* ") for h in header]
        id_col = next((i for i, h in enumerate(lower) if h in ("#", "id")), None)
        heading = next((l[3:].strip() for l in reversed(lines[:start]) if l.startswith("## ")), "")
        if id_col is None:
            # Looks like debt (a Description, or an ID-ish column such as `Task ID`)
            # but has no column the parser keys on: report it, never drop it silently.
            # A table with neither — e.g. `| Item | Rule | Severity | … |` — is not debt.
            if "description" in lower or any(LOOSE_ID.search(h) for h in lower):
                found.append({"source": rel, "line": start + 1, "heading": heading,
                              "header": header, "kind": "no_id", "rows": []})
            continue
        if "description" not in lower:
            continue
        found.append({
            "source": rel, "line": start + 1, "heading": heading, "header": header,
            "kind": "active" if "severity" in lower else "resolved",
            "id_col": id_col,
            "severity_col": lower.index("severity") if "severity" in lower else None,
            "description_col": lower.index("description"),
            "category_col": lower.index("category") if "category" in lower else None,
            "rows": [(start + k + 1, l) for k, l in enumerate(block)
                     if k > 0 and not SEPARATOR.match(l)],
        })
    return found


def debt_check(root: str, board: list[dict]) -> list[str]:
    """Every reason the tech-debt file is not safe to import. Empty == valid or absent."""
    try:
        rel = debt_file(root)
    except BoardError as e:
        return [str(e)]
    if rel is None:
        return []
    problems = structural_problems(rel, read_lines(os.path.join(root, rel)))
    tables = debt_tables(root, rel)
    if not any(t["kind"] == "active" for t in tables):
        problems.append(f"{rel}: no tech-debt table with ID, Description and Severity columns "
                        f"— nothing would be imported")
    for t in tables:
        if t["kind"] == "no_id":
            problems.append(f"{rel}:{t['line']}: table under '{t['heading']}' has no '#' or 'ID' column "
                            f"— its rows would not be imported")
    active: Counter[str] = Counter()
    resolved: set[str] = set()
    for t in tables:
        if t["kind"] not in ("active", "resolved"):
            continue
        for n, line in t["rows"]:
            c = cells(line)
            if c[0] == PLACEHOLDER:
                continue
            if len(c) != len(t["header"]):
                problems.append(f"{rel}:{n}: row has {len(c)} cells, its table header has "
                                f"{len(t['header'])} — an unescaped '|' inside a cell splits it; "
                                f"write it as '\\|'")
                continue
            tid = normalize_debt_id(c[t["id_col"]])
            if tid is None:
                problems.append(f"{rel}:{n}: '{c[t['id_col']]}' is not a tech-debt ID "
                                f"(expected TD-<n>, or <n> in a '#' column)")
                continue
            if t["kind"] == "resolved":
                resolved.add(tid)
                continue
            active[tid] += 1
            sev = c[t["severity_col"]].strip("* ").lower()
            if sev not in SEVERITIES:
                problems.append(f"{rel}:{n}: {tid} severity '{c[t['severity_col']]}' is not one of "
                                f"{', '.join(SEVERITIES)}")
    for tid, k in sorted(active.items()):
        if k > 1:
            problems.append(f"{rel}: {tid} is listed {k} times as active debt")
    for tid in sorted(set(active) & resolved):
        problems.append(f"{rel}: {tid} is listed as both active and resolved — decide which is true")
    done = {t["task_id"] for t in board if t["column"] == "done"}
    for tid in sorted(set(active) & done):
        problems.append(f"{rel}: {tid} is active debt but its board task is Done — mark the debt "
                        f"resolved, or reopen the task")
    return problems


def parse_debt(root: str, board: list[dict]) -> dict:
    """Active debt items to import. Raises BoardError on a corrupt debt file.

    `on_board` marks an item whose ID is already a live board task. It must NOT
    become a second issue: the board task's issue is labelled as debt instead,
    otherwise the search-before-create guard finds one [TD-n] and silently skips
    the other."""
    problems = debt_check(root, board)
    if problems:
        raise BoardError("\n".join(problems))
    rel = debt_file(root)
    result: dict = {"file": rel, "items": [], "not_migrated": []}
    if rel is None:
        return result
    live_ids = {t["task_id"] for t in board if t["column"] != "done"}
    for t in debt_tables(root, rel):
        if t["kind"] not in ("active", "resolved"):
            continue  # debt_check has already refused these
        rows = [(n, cells(l)) for n, l in t["rows"] if cells(l)[0] != PLACEHOLDER]
        if t["kind"] == "resolved":
            result["not_migrated"].append({"heading": t["heading"], "line": t["line"], "rows": len(rows)})
            continue
        for n, c in rows:
            tid = normalize_debt_id(c[t["id_col"]])
            result["items"].append({
                "task_id": tid,
                "severity": c[t["severity_col"]].strip("* ").lower(),
                "category": c[t["category_col"]] if t["category_col"] is not None else "",
                "description": c[t["description_col"]],
                "fields": dict(zip(t["header"], c)),
                "source": rel, "line": n,
                "on_board": tid in live_ids,
            })
    return result


def board_tasks(root: str, done_mode: str) -> list[dict]:
    """parse(), shaped for migration. Under `freeze`, Done rows stay markdown
    history; a live story whose epic is one of them is flagged `parent_frozen`,
    because creating that epic would resurrect finished work as an open issue."""
    tasks = parse(root)
    done_ids = {t["task_id"] for t in tasks if t["column"] == "done"}
    if done_mode == "freeze":
        tasks = [t for t in tasks if t["column"] != "done"]
    for t in tasks:
        t["parent_frozen"] = done_mode == "freeze" and t["parent"] in done_ids
    return tasks


def fetch_issues() -> list[dict]:
    """Every issue in the repo (PRs excluded), fully paginated — no --limit to
    silently truncate at."""
    out = subprocess.run(
        ["gh", "api", "--paginate", "repos/{owner}/{repo}/issues?state=all&per_page=100",
         "--jq", ".[] | select(.pull_request | not) | "
                 "{title, state, state_reason, labels: [.labels[].name]}"],
        capture_output=True, text=True)
    if out.returncode != 0:
        print(f"gh failed: {out.stderr.strip()}", file=sys.stderr)
        sys.exit(2)
    return [json.loads(l) for l in out.stdout.splitlines() if l.strip()]


def issue_column(issue: dict) -> str | None:
    if issue["state"] == "closed":
        # Done is a completed close. "not planned" is not Done; a null reason
        # predates GitHub recording one and is treated as completed.
        return None if issue.get("state_reason") == "not_planned" else "done"
    for label in issue["labels"]:
        if label.startswith("status:") and label[7:] in COLUMNS:
            return label[7:]
    return None


def verify(root: str, done_mode: str = "issues", include_debt: bool = False) -> int:
    tasks = parse(root)
    debt = parse_debt(root, tasks) if include_debt else None
    issues = fetch_issues()
    failures = 0

    # An issue labelled as debt whose ID is not a board task belongs to the debt
    # import, not a board column — it carries status:backlog, and counting it there
    # would report every imported debt item as a Backlog EXTRA.
    board_ids = {t["task_id"] for t in tasks}

    def debt_only(i: dict) -> bool:
        m = TITLE_ID.match(i["title"])
        return DEBT_LABEL in i["labels"] and not (m and m.group(1) in board_ids)

    # A duplicate closed as "not planned" is the remedy, so it no longer counts.
    gh_ids = [m.group(1) for i in issues
              if i.get("state_reason") != "not_planned" and (m := TITLE_ID.match(i["title"]))]
    for tid, n in sorted(Counter(gh_ids).items()):
        if n > 1:
            print(f"  DUPLICATE on GitHub: [{tid}] appears {n} times — close the extras as not planned")
            failures += 1
    for tid, n in sorted(Counter(t["task_id"] for t in tasks).items()):
        if n > 1:
            print(f"  DUPLICATE in markdown: {tid} appears {n} times")
            failures += 1

    for col in COLUMNS:
        want = Counter(t["task_id"] for t in tasks if t["column"] == col)
        if col == "done" and done_mode == "freeze":
            print(f"  {col:12} markdown={sum(want.values()):3}  frozen — kept as markdown history, "
                  f"not expected on GitHub")
            continue
        have = Counter(m.group(1) for i in issues
                       if issue_column(i) == col and not debt_only(i)
                       and (m := TITLE_ID.match(i["title"])))
        missing = sorted(set(want) - set(have))
        extra = sorted(set(have) - set(want))
        notes = []
        if missing:
            notes.append(f"MISSING {len(missing)}: {', '.join(missing)}")
        if extra:
            notes.append(f"EXTRA {len(extra)}: {', '.join(extra)}")
        if not want:
            sources = [p for s in COLUMNS[col][0] for p in find_files(root, s)]
            if sources and not column_tables(root, col):
                notes.append(f"NO TABLE: {', '.join(os.path.relpath(p, root) for p in sources)} "
                             f"exists but no {HEADING[col]} table was found in it")
        print(f"  {col:12} markdown={sum(want.values()):3}  github={sum(have.values()):3}  "
              f"{'; '.join(notes) or 'OK'}")
        failures += len(notes)

    if debt is not None:
        failures += verify_debt(debt, issues)

    print(f"\n{'MISMATCH — do not freeze the markdown' if failures else 'All tasks accounted for.'}")
    return 1 if failures else 0


def verify_debt(debt: dict, issues: list[dict]) -> int:
    """Every active debt item is an open issue labelled tech-debt with its
    severity — its own issue, or the board task's it was merged onto."""
    live = [i for i in issues if i.get("state_reason") != "not_planned"]
    by_id: dict[str, list[dict]] = {}
    for i in live:
        if m := TITLE_ID.match(i["title"]):
            by_id.setdefault(m.group(1), []).append(i)
    want = {d["task_id"]: d for d in debt["items"]}
    missing, unlabelled, closed, severity = [], [], [], []
    for tid, d in sorted(want.items()):
        found = by_id.get(tid, [])
        if not found:
            missing.append(tid)
            continue
        i = found[0]
        if i["state"] != "open":
            closed.append(tid)
        if DEBT_LABEL not in i["labels"]:
            unlabelled.append(tid)
        elif f"severity:{d['severity']}" not in i["labels"]:
            severity.append(tid)
    extra = sorted({m.group(1) for i in live if DEBT_LABEL in i["labels"] and i["state"] == "open"
                    and (m := TITLE_ID.match(i["title"])) and m.group(1) not in want})
    notes = [f"{name} {len(v)}: {', '.join(v)}" for name, v in
             (("MISSING", missing), ("NOT LABELLED tech-debt", unlabelled),
              ("CLOSED", closed), ("WRONG SEVERITY", severity), ("EXTRA", extra)) if v]
    merged = sum(1 for d in want.values() if d["on_board"])
    print(f"  {'tech-debt':12} markdown={len(want):3}  ({merged} merged onto board tasks)  "
          f"{'; '.join(notes) or 'OK'}")
    for nm in debt["not_migrated"]:
        print(f"  {'':12} not migrated: '{nm['heading']}' ({nm['rows']} resolved row(s)) — stays in {debt['file']}")
    return len(notes)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true")
    g.add_argument("--json", action="store_true")
    g.add_argument("--verify", action="store_true")
    g.add_argument("--tech-debt", action="store_true")
    ap.add_argument("--done", choices=("issues", "freeze"), default="issues")
    ap.add_argument("--include-tech-debt", action="store_true")
    ap.add_argument("--root", default=".")
    a = ap.parse_args(argv)

    try:
        if a.check:
            tasks = parse(a.root)
            for note in notices(a.root):
                print(f"  note: {note}")
            print(f"Board is structurally valid. {len(tasks)} task(s) parsed.")
            if a.include_tech_debt:
                debt = parse_debt(a.root, tasks)
                if debt["file"] is None:
                    print("No tech-debt backlog found (looked in: " + ", ".join(DEBT_FILES) + ").")
                else:
                    merged = sum(1 for d in debt["items"] if d["on_board"])
                    print(f"Tech debt is structurally valid: {len(debt['items'])} active item(s) in "
                          f"{debt['file']}, {merged} already on the board.")
                    for nm in debt["not_migrated"]:
                        print(f"  note: '{nm['heading']}' ({nm['rows']} resolved row(s)) will not be migrated.")
            return 0
        if a.json:
            print(json.dumps(board_tasks(a.root, a.done), indent=2, ensure_ascii=False))
            return 0
        if a.tech_debt:
            print(json.dumps(parse_debt(a.root, parse(a.root)), indent=2, ensure_ascii=False))
            return 0
        return verify(a.root, a.done, a.include_tech_debt)
    except BoardError as e:
        print("Board integrity problems — repair and commit before migrating:\n", file=sys.stderr)
        for p in str(e).split("\n"):
            print(f"  {p}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
