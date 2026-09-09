#!/usr/bin/env python3
"""Parse, validate and verify a markdown Kanban board for /migrate-board.

Modes:
  --check    Validate table integrity. Exits 1 if the board is corrupt.
  --json     Emit every task as JSON on stdout.
  --verify   Compare the parsed board against GitHub Issues. Exits 1 on mismatch.

The board's shape is defined in .claude/rules/shared/board-adapter.md; the
per-column schemas in .claude/skills/update-board/SKILL.md.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import subprocess
import sys

# column -> (source file glob, expected header fields)
COLUMNS = {
    "backlog":     ("docs/board/backlog.md",   ["Task ID", "Priority", "Description", "Requested By"]),
    "ready":       ("board-context.md",        ["Task ID", "Priority", "Description", "Assigned To"]),
    "in-progress": ("board-context.md",        ["Task ID", "Agent", "Description", "Started", "Cycle Day"]),
    "review":      ("board-context.md",        ["Task ID", "Agent", "Description", "Reviewer", "Waiting Since"]),
    "blocked":     ("board-context.md",        ["Task ID", "Agent", "Blocker", "Waiting On", "Blocked Since"]),
    "done":        ("docs/board/done-*.md",    ["Task ID", "Agent", "Description", "Output", "Completed"]),
}
HEADING = {
    "ready": "Ready", "in-progress": "In Progress", "review": "Review",
    "blocked": "Blocked", "backlog": "Backlog", "done": "Done",
}
PLACEHOLDER = "—"
SEPARATOR = re.compile(r"^\|[\s:|-]+\|$")
TASK_ID = re.compile(r"^[A-Za-z]+-\d+(\.\d+)?$")


def cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def find_files(pattern: str) -> list[str]:
    return sorted(glob.glob(pattern)) if "*" in pattern else (
        [pattern] if os.path.exists(pattern) else [])


def section(lines: list[str], heading: str) -> tuple[int, int] | None:
    """Line range of a '## {heading}' section, exclusive of the next heading."""
    start = None
    for i, l in enumerate(lines):
        if l.startswith("## ") and l[3:].strip().split(" (")[0] == heading:
            start = i
            break
    if start is None:
        return None
    for j in range(start + 1, len(lines)):
        if lines[j].startswith("## "):
            return start, j
    return start, len(lines)


def check(root: str) -> list[str]:
    """Structural problems. Catches the merge-corruption class: separator rows
    that precede their header, and stray tables under no known heading."""
    problems: list[str] = []
    seen_files: set[str] = set()
    for col, (pattern, header) in COLUMNS.items():
        for path in find_files(os.path.join(root, pattern)):
            rel = os.path.relpath(path, root)
            if rel in seen_files:
                continue
            seen_files.add(rel)
            lines = open(path, encoding="utf-8").read().split("\n")
            for i, l in enumerate(lines):
                if SEPARATOR.match(l):
                    if i == 0 or not lines[i - 1].startswith("|"):
                        problems.append(
                            f"{rel}:{i+1}: separator row with no header above it "
                            f"— the table will not render")
                elif l.startswith("|") and not SEPARATOR.match(l):
                    prev_is_header = i > 0 and lines[i - 1].startswith("|")
                    if not prev_is_header and i + 1 < len(lines) and not SEPARATOR.match(lines[i + 1]):
                        problems.append(f"{rel}:{i+1}: table row with no separator after its header")
    # Sections that should not exist in the live file.
    bc = os.path.join(root, "board-context.md")
    if os.path.exists(bc):
        text = open(bc, encoding="utf-8").read()
        for stray in ("## Done", "## Decisions Log"):
            if stray in text:
                problems.append(
                    f"board-context.md: '{stray}' must not be in the live board "
                    f"— it belongs in docs/board/ (board-adapter.md)")
    return problems


def parse(root: str) -> list[dict]:
    tasks: list[dict] = []
    for col, (pattern, header) in COLUMNS.items():
        for path in find_files(os.path.join(root, pattern)):
            lines = open(path, encoding="utf-8").read().split("\n")
            rng = section(lines, HEADING[col])
            body = lines[rng[0]:rng[1]] if rng else lines
            for l in body:
                if not l.startswith("|") or SEPARATOR.match(l):
                    continue
                c = cells(l)
                if not c or c[0] in (header[0], PLACEHOLDER, ""):
                    continue
                if not TASK_ID.match(c[0]):
                    continue
                row = dict(zip(header, c))
                tasks.append({
                    "task_id": c[0],
                    "column": col,
                    "description": row.get("Description") or row.get("Blocker", ""),
                    "agent": row.get("Agent") or row.get("Assigned To", ""),
                    "priority": row.get("Priority", ""),
                    "fields": row,
                    "source": os.path.relpath(path, root),
                    "parent": c[0].rsplit(".", 1)[0] if "." in c[0] else None,
                })
    return tasks


def gh_ids(args: list[str]) -> set[str]:
    """Task IDs of issues matching a gh issue list query, read from title prefixes."""
    out = subprocess.run(["gh", "issue", "list", "--limit", "500",
                          "--json", "title"] + args,
                         capture_output=True, text=True)
    if out.returncode != 0:
        print(f"gh failed: {out.stderr.strip()}", file=sys.stderr)
        sys.exit(2)
    ids = set()
    for item in json.loads(out.stdout or "[]"):
        m = re.match(r"^\[([A-Za-z]+-\d+(?:\.\d+)?)\]", item["title"])
        if m:
            ids.add(m.group(1))
    return ids


def verify(root: str) -> int:
    tasks = parse(root)
    failures = 0
    for col in COLUMNS:
        want = {t["task_id"] for t in tasks if t["column"] == col}
        if not want:
            continue
        have = (gh_ids(["--state", "closed"]) if col == "done"
                else gh_ids(["--state", "open", "--label", f"status:{col}"]))
        missing = want - have
        status = "OK" if not missing else f"MISSING {len(missing)}: {', '.join(sorted(missing))}"
        print(f"  {col:12} markdown={len(want):3}  github={len(want & have):3}  {status}")
        failures += len(missing)
    print(f"\n{'MISMATCH — do not freeze the markdown' if failures else 'All tasks accounted for.'}")
    return 1 if failures else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true")
    g.add_argument("--json", action="store_true")
    g.add_argument("--verify", action="store_true")
    ap.add_argument("--root", default=".")
    a = ap.parse_args()

    if a.check:
        problems = check(a.root)
        if problems:
            print("Board integrity problems — repair and commit before migrating:\n")
            for p in problems:
                print(f"  {p}")
            return 1
        n = len(parse(a.root))
        print(f"Board is structurally valid. {n} task(s) parsed.")
        return 0
    if a.json:
        print(json.dumps(parse(a.root), indent=2, ensure_ascii=False))
        return 0
    return verify(a.root)


if __name__ == "__main__":
    sys.exit(main())
