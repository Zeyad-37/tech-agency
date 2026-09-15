#!/usr/bin/env python3
"""Parse, validate and verify a markdown Kanban board for /migrate-board.

Modes:
  --check    Validate table integrity. Exits 1 if the board is corrupt.
  --json     Emit every task as JSON on stdout. Refuses (exit 1) on a corrupt board.
  --verify   Compare the parsed board against GitHub Issues, both directions.
             Exits 1 on any mismatch. Refuses (exit 1) on a corrupt board.

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


class BoardError(Exception):
    """The board is not safe to parse."""


def cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


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
        for k, line in enumerate(block):
            n = start + k + 1
            is_sep = bool(SEPARATOR.match(line))
            if k == 0 and is_sep:
                problems.append(f"{rel}:{n}: separator row with no header above it — the table will not render")
            elif k == 1 and not is_sep and not SEPARATOR.match(block[0]):
                problems.append(f"{rel}:{n - 1}: table header with no separator row after it")
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


def verify(root: str) -> int:
    tasks = parse(root)
    issues = fetch_issues()
    failures = 0

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
        have = Counter(m.group(1) for i in issues
                       if issue_column(i) == col and (m := TITLE_ID.match(i["title"])))
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

    print(f"\n{'MISMATCH — do not freeze the markdown' if failures else 'All tasks accounted for.'}")
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true")
    g.add_argument("--json", action="store_true")
    g.add_argument("--verify", action="store_true")
    ap.add_argument("--root", default=".")
    a = ap.parse_args(argv)

    try:
        if a.check:
            n = len(parse(a.root))
            for note in notices(a.root):
                print(f"  note: {note}")
            print(f"Board is structurally valid. {n} task(s) parsed.")
            return 0
        if a.json:
            print(json.dumps(parse(a.root), indent=2, ensure_ascii=False))
            return 0
        return verify(a.root)
    except BoardError as e:
        print("Board integrity problems — repair and commit before migrating:\n", file=sys.stderr)
        for p in str(e).split("\n"):
            print(f"  {p}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
