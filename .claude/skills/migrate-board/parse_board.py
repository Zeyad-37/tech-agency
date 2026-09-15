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
import unicodedata
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
# The ID a legacy Done cell starts with — `T-013 (Phase 3 pilot)` is still epic T-013.
LEADING_ID = re.compile(r"^[A-Za-z]+-\d+(?:\.\d+)?(?![\w.])")

# Tech debt: the current location first, then the pre-reorganisation one that
# older consumers still use. Both present is an error, not a preference — importing
# either alone silently drops the other's items.
DEBT_FILES = ["docs/guides/tech-debt/backlog.md", "docs/tech-debt/backlog.md"]
# "TD-337" (prefixed, kept as written) or "3" (a bare `#` column, read as TD-3).
# Duplicates are compared by the number, so TD-002 and 2 are the same item.
DEBT_ID = re.compile(r"^(?:TD-(\d+)|(\d+))$")
SEVERITIES = ("high", "medium", "low")
TITLE_MAX = 256  # GitHub's issue-title cap
# Room left for the provenance line Step 4 appends.
BODY_MAX = 65536 - 1024  # GitHub's issue-body cap
# An @mention, not the domain of an email address; a suffix like "-owned" is not part of it.
AGENT = re.compile(r"(?<![\w.@])@([A-Za-z][A-Za-z0-9]*)")
WORD = re.compile(r"\b[A-Za-z][A-Za-z0-9]*\b")
# The agency's agents, read from the plugin's agents/ directory beside skills/ — the
# same tree whether this runs from the tech-agency repo or an installed plugin.
# Fallback for a copy run on its own. `Claude` is the generic agent.
AGENTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "agents")
KNOWN_AGENTS_FALLBACK = ("Apex Atlas Diana Echo Flux Forge Kai Link Morgan Neuron Nova Pipeline "
                         "Pixel Pyra Sage Scroll Sentinel Shield Swift").split()

PRIORITY = re.compile(r"\bP([0-3])\b")
DEBT_LABEL = "tech-debt"
# A header cell that names an ID without being one the parser keys on (`Task ID`).
LOOSE_ID = re.compile(r"\bid\b", re.IGNORECASE)
# A heading's status decides whether the tables under it are finished work.
# Open-markers are an explicit whole-word list, never a prefix pattern: `under`,
# `until` and `unless` are ordinary words, not negations.
RESOLVED_WORD = re.compile(r"\b(resolved|closed|done)\b", re.IGNORECASE)
OPEN_MARKER = re.compile(
    r"\b(not|unresolved|undone|unfixed|unfinished|open|active|pending|outstanding|remaining"
    r"|yet|todo|to\s+do|partially|partial|reopen|reopened|almost|nearly|close\s+to)\b"
    # A question ("Resolved?") asserts nothing, so it must not resolve either.
    r"|\?", re.IGNORECASE)
# Any heading of level 2 or deeper; group 1 is its hashes, group 2 its text.
HEADING_LINE = re.compile(r"^(#{2,})\s+(.*?)\s*#*\s*$")


def heading_status(heading: str) -> str | None:
    """`open` when the heading carries an open-marker, else `resolved` when it
    says resolved / closed / done, else None (the heading says nothing)."""
    if OPEN_MARKER.search(heading):
        return "open"
    if RESOLVED_WORD.search(heading):
        return "resolved"
    return None


def ancestor_headings(lines: list[str], index: int, code: set[int]) -> list[str]:
    """The headings enclosing line `index`, nearest first: the nearest heading
    above it, then the nearest above that of a strictly smaller level, and so on
    up to `##`. Lines inside fenced code are not headings."""
    found: list[str] = []
    level = None
    for i in range(index - 1, -1, -1):
        if i in code:
            continue
        m = HEADING_LINE.match(lines[i])
        if m and (level is None or len(m.group(1)) < level):
            found.append(m.group(2))
            level = len(m.group(1))
            if level == 2:
                break
    return found


def table_status(ancestors: list[str]) -> tuple[bool, str]:
    """Whether a table under these headings (nearest first) is resolved, and the
    heading to name it by. The nearest heading that has a status decides; with no
    status anywhere the table is not resolved. The name runs from the deciding
    heading down to the nearest (`Resolved › 2026 Q2`)."""
    for depth, heading in enumerate(ancestors):
        status = heading_status(heading)
        if status is not None:
            name = " › ".join(reversed(ancestors[:depth + 1]))
            return status == "resolved", name
    return False, ancestors[0] if ancestors else ""


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


FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})")


def fenced(lines: list[str]) -> set[int]:
    """Indices of lines inside a fenced code block, the fence lines included. A
    fence closes on the same character repeated at least as many times."""
    inside: set[int] = set()
    opener: str | None = None
    for i, line in enumerate(lines):
        m = FENCE.match(line)
        if opener is None:
            if m:
                opener = m.group(1)
                inside.add(i)
        else:
            inside.add(i)
            if m and m.group(1)[0] == opener[0] and len(m.group(1)) >= len(opener) \
                    and not line.strip()[len(m.group(1)):].strip():
                opener = None
    return inside


def table_blocks(lines: list[str], offset: int = 0) -> list[tuple[int, list[str]]]:
    """Runs of consecutive '|' lines, as (first line index, lines). Lines inside
    fenced code are examples, not tables, and are skipped."""
    blocks: list[tuple[int, list[str]]] = []
    cur: list[str] = []
    start = 0
    code = fenced(lines)
    for i, line in enumerate(lines):
        if line.startswith("|") and i not in code:
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


def check(root: str, done_mode: str = "issues") -> list[str]:
    """Every reason the board is not safe to migrate. Empty list == valid.

    Under `freeze` a Done row is never migrated, so its ID is not validated: a
    legacy cell like `T-013 (Phase 3 pilot)` stays readable history rather than
    forcing an edit to a closed quarter. Its table structure still is — a cut-off
    row or a wrong header corrupts the frozen archive just as surely."""
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
                elif col == "done" and done_mode == "freeze":
                    continue
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


def done_task_ids(board: list[dict]) -> set[str]:
    """The Task IDs the Done archive records. A legacy cell names its task by its
    leading ID — `T-013 (Phase 3 pilot)` is T-013 — and a cell with none (`T-PICKER-THEME`)
    names no task another row could refer to."""
    return {m.group(0) for t in board if t["column"] == "done" and (m := LEADING_ID.match(t["task_id"]))}


def agent_notices(tasks: list[dict]) -> list[str]:
    """Agent cells that name no agency agent: their issue gets no agent: label."""
    by_cell: dict[str, list[str]] = {}
    for t in tasks:
        if not t.get("agents") and t["agent"].strip() not in ("", PLACEHOLDER):
            by_cell.setdefault(t["agent"].strip(), []).append(t["task_id"])
    return [f"Agent cell '{cell}' names no agency agent, so {len(ids)} issue(s) get no agent: label "
            f"({', '.join(ids)}). Humans such as the owner are the assignee, not a label."
            for cell, ids in by_cell.items()]


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


def parse(root: str, done_mode: str = "issues") -> list[dict]:
    """Tasks in migration order (COLUMNS order). Raises BoardError on a corrupt board."""
    problems = check(root, done_mode)
    if problems:
        raise BoardError("\n".join(problems))
    tasks: list[dict] = []
    agents = known_agents()
    for col in COLUMNS:
        for t in column_tables(root, col):
            for _, line in t["rows"]:
                c = cells(line)
                if c[0] == PLACEHOLDER:
                    continue
                row = dict(zip(t["header"], c))
                description = row.get("Description") or row.get("Blocker", "")
                agent = row.get("Agent") or row.get("Assigned To", "")
                priority = row.get("Priority", "")
                tasks.append({
                    "task_id": c[0],
                    "column": col,
                    "description": description,
                    "title": issue_title(c[0], description),
                    "agent": agent,
                    # One `agent:@Name` label per agent the cell names — a label
                    # cannot be "@Kai (with @Link, @Swift)".
                    "agents": agent_names(agent, agents),
                    "priority": priority,
                    # "**P1**" or "P3 (stretch)" → P1 / P3; Step 3 creates only P0–P3.
                    "priority_label": (m := PRIORITY.search(priority)) and f"P{m.group(1)}" or "",
                    "fields": row,
                    "body": issue_body(row, t["source"]),
                    "source": t["source"],
                    "parent": c[0].rsplit(".", 1)[0] if "." in c[0] else None,
                })
    problems = duplicate_problems(tasks, done_mode)
    if problems:
        raise BoardError("\n".join(problems))
    return tasks


def duplicate_problems(tasks: list[dict], done_mode: str) -> list[str]:
    """Task IDs that would become two issues with one title prefix. Under freeze a
    task repeated inside the Done archive creates nothing, so only live rows count —
    plus a Done row repeating a live task, which cannot be both finished and in flight."""
    live_ids = {t["task_id"] for t in tasks if t["column"] != "done"}
    if done_mode == "freeze":  # one Done row is enough to contradict a live task
        counted = [t["task_id"] for t in tasks if t["column"] != "done"] + sorted(
            {t["task_id"] for t in tasks if t["column"] == "done" and t["task_id"] in live_ids})
    else:
        counted = [t["task_id"] for t in tasks]
    return [f"{tid} appears {n} times — each row would become an issue with the same "
            f"[{tid}] title; give one a new ID" for tid, n in sorted(Counter(counted).items()) if n > 1]


def debt_file(root: str) -> str | None:
    """The tech-debt backlog to import, relative to root, or None if there is none."""
    present = [p for p in DEBT_FILES if os.path.exists(os.path.join(root, p))]
    if len(present) > 1:
        raise BoardError(
            f"tech debt exists at both {present[0]} and {present[1]} — merge them into "
            f"{DEBT_FILES[0]} first; importing either alone drops the other's items")
    return present[0] if present else None


def debt_number(tid: str) -> int:
    """The number a normalised debt ID names: `TD-002`, `TD-2` and a bare `2` are one item."""
    return int(tid.rsplit("-", 1)[1])


def normalize_debt_id(raw: str) -> str | None:
    m = DEBT_ID.match(raw.strip())
    if not m:
        return None
    return f"TD-{m.group(1) if m.group(1) is not None else m.group(2)}"


def utf16_len(text: str) -> int:
    """Length in UTF-16 code units: never less than the code-point count, so a title
    within it fits whichever unit GitHub counts."""
    return len(text.encode("utf-16-le")) // 2


def _continues_cluster(ch: str) -> bool:
    """A character that belongs to the one before it: a combining mark (accents,
    Indic vowel signs and viramas), zero-width joiner, variation selector, emoji
    skin tone, or a tag character of a subdivision flag."""
    return (unicodedata.combining(ch) > 0 or unicodedata.category(ch) in ("Mn", "Mc", "Me")
            or ch in "\u200d\ufe0e\ufe0f" or 0x1F3FB <= ord(ch) <= 0x1F3FF
            or 0xE0020 <= ord(ch) <= 0xE007F)


def cut16(text: str, units: int) -> str:
    """The longest prefix of `text` within `units` UTF-16 units that does not end
    inside a common character cluster: an accent, an Indic conjunct, a ZWJ emoji, a
    country or subdivision flag. (An approximation of Unicode grapheme clusters.)"""
    n = i = 0
    while i < len(text) and n + (w := 2 if ord(text[i]) > 0xFFFF else 1) <= units:
        n += w
        i += 1
    if i == len(text):
        return text
    # Back off while the next character would continue the one we end on.
    # A virama (combining class 9) joins the next consonant into a conjunct.
    while i > 0 and (_continues_cluster(text[i]) or text[i - 1] == "\u200d"
                     or unicodedata.combining(text[i - 1]) == 9):
        i -= 1
    ri = lambda c: 0x1F1E6 <= ord(c) <= 0x1F1FF  # noqa: E731 — regional indicator
    if i > 0 and ri(text[i - 1]) and ri(text[i]):
        run = i
        while run > 0 and ri(text[run - 1]):
            run -= 1
        if (i - run) % 2:  # an odd count before the cut splits a flag
            i -= 1
    return text[:i]


def issue_title(task_id: str, description: str, limit: int = TITLE_MAX) -> str:
    """`[ID] description`, cut (with a trailing …) so the whole title fits GitHub's
    cap. The cut prefers a word boundary, unless that would throw away more than a
    quarter of the room — a long URL or path is hard-cut instead of dropped. The
    full text travels in the issue body. An empty description gets a placeholder,
    so the title never ends in the bare "[ID] " that GitHub would trim."""
    title = f"[{task_id}] {description.strip() or '(no description)'}"
    if utf16_len(title) <= limit:
        return title
    cut = cut16(title, limit - 1)  # room for the ellipsis
    prefix = len(task_id) + 3
    space = cut.rfind(" ", prefix)
    if space > prefix and space >= len(cut) * 3 // 4:
        cut = cut[:space]
    return cut.rstrip() + "…"


def issue_body(fields: dict[str, str], source: str, extra: str = "") -> str:
    """Every field of the row, one paragraph each, capped under GitHub's body limit.
    When over, the longest field is cut — or, if that cannot make it fit, the body as
    a whole — with a note saying where the full text is."""
    parts = dict(fields)
    note = f" … *(truncated — full text in {source})*"

    def render() -> str:
        text = "\n\n".join(f"**{k}:** {v}" for k, v in parts.items())
        return f"{extra}\n\n{text}".strip() if extra else text
    body = render()
    # Cut the longest field, which keeps the rest of the row readable. If even the
    # longest cannot absorb the excess, no field can: cut the body as a whole instead
    # (huge keys or `extra`, thousands of small fields). No loop, so nothing can hang.
    if utf16_len(body) > BODY_MAX and parts:
        key = max(parts, key=lambda k: utf16_len(parts[k]))
        keep = utf16_len(parts[key]) - (utf16_len(body) - BODY_MAX) - utf16_len(note)
        if keep > 0:
            parts[key] = cut16(parts[key], keep) + note
            body = render()
    if utf16_len(body) > BODY_MAX:
        body = cut16(body, BODY_MAX - utf16_len(note)) + note
    return body


def known_agents() -> dict[str, str]:
    """lower-case name → canonical `@Name`, for every agency agent plus Claude."""
    names = [f.split("-", 1)[0].capitalize() for f in os.listdir(AGENTS_DIR) if f.endswith(".md")] \
        if os.path.isdir(AGENTS_DIR) else []
    return {n.lower(): f"@{n}" for n in (names or KNOWN_AGENTS_FALLBACK) + ["Claude"]}


def agent_names(cell: str, known: dict[str, str] | None = None) -> list[str]:
    """Each agency agent a cell names, as its canonical `@Name`, once.

    @mentions of agents decide when there are any (`@Link (Claude)` is Link; any
    case). Otherwise capitalised bare words that are agent names count (`Kai / Link`,
    `Shield (review)`, `Kai (pairing w/ @Zeyad)`) — lower-case prose such as
    "link to PR" or "CI pipeline" does not. Anything else — TBD, N/A, a human such
    as @Zeyad, who is the assignee — is no agent label."""
    known = known if known is not None else known_agents()
    mentioned = [known[m.lower()] for m in AGENT.findall(cell) if m.lower() in known]
    if mentioned:
        return list(dict.fromkeys(mentioned))
    return list(dict.fromkeys(known[w.lower()] for w in WORD.findall(cell)
                              if w[0].isupper() and w.lower() in known))


def debt_tables(root: str, rel: str) -> list[dict]:
    """Tables in the debt file, located by header NAME rather than position —
    consumers order the columns differently.

    Every table that looks like debt gets exactly one `kind`; no path skips one
    silently:

    - `resolved` — the nearest enclosing heading that has a status (see
      `heading_status`, walking up `###` → `##`) says resolved / closed / done.
      Decided first, whatever the columns: a finished table that kept its
      Severity column is history, not active debt. `## Resolved` → `### 2026 Q2`
      is resolved; `## Resolved` → `### Still open` is not.
    - `active` — an exact `#`/`ID` column, a Description and a Severity column.
    - `problem` — anything else, with `missing` naming the absent columns. Open
      work is never guessed into history, and rows are never dropped unreported.

    A table looks like debt when it has an exact `#`/`ID` column, an ID-like
    header (`Task ID`), a data row keyed by a TD-<n> ID, or Description alongside
    Severity or Category. A bare Description column is not enough — a
    documentation table such as `| Field | Description |` has one — and
    `| Item | Rule | Severity | … |` meets none of these; both are ignored."""
    lines = read_lines(os.path.join(root, rel))
    code = fenced(lines)
    found: list[dict] = []
    for start, block in table_blocks(lines):
        if len(block) < 2 or not SEPARATOR.match(block[1]):
            continue  # structural_problems reports this
        header = cells(block[0])
        lower = [h.lower().strip("* ") for h in header]
        id_col = next((i for i, h in enumerate(lower) if h in ("#", "id")), None)
        looks_like_debt = (
            id_col is not None
            or any(LOOSE_ID.search(h) for h in lower)
            or any(re.match(r"^TD-\d+$", cells(l)[0]) for l in block[2:])
            or ("description" in lower and ("severity" in lower or "category" in lower)))
        if not looks_like_debt:
            continue
        resolved, heading = table_status(ancestor_headings(lines, start, code))
        missing = [name for name, present in (("an '#' or 'ID' column", id_col is not None),
                                              ("a Description column", "description" in lower),
                                              ("a Severity column", "severity" in lower)) if not present]
        found.append({
            "source": rel, "line": start + 1, "heading": heading, "header": header,
            "kind": ("resolved" if resolved
                     else "active" if not missing
                     else "problem"),
            "missing": missing,
            "id_col": id_col,
            "severity_col": lower.index("severity") if "severity" in lower else None,
            "description_col": lower.index("description") if "description" in lower else None,
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
        if t["kind"] == "problem":
            problems.append(f"{rel}:{t['line']}: table under '{t['heading']}' is missing "
                            f"{' and '.join(t['missing'])} and its heading does not say it is resolved "
                            f"— its rows would not be imported")
    # Keyed by the ID's number, so `TD-002` and a bare `2` are one item; each
    # value keeps the IDs as written, for the message and for display.
    active: dict[int, list[str]] = {}
    resolved: dict[int, list[str]] = {}
    for t in tables:
        if t["kind"] not in ("active", "resolved"):
            continue
        for n, line in t["rows"]:
            c = cells(line)
            if c[0] == PLACEHOLDER:
                continue
            if t["id_col"] is None:
                continue  # resolved, keyed by `Task ID` or the like: history, counted as a whole
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
                resolved.setdefault(debt_number(tid), []).append(tid)
                continue
            active.setdefault(debt_number(tid), []).append(tid)
            sev = c[t["severity_col"]].strip("* ").lower()
            if sev not in SEVERITIES:
                problems.append(f"{rel}:{n}: {tid} severity '{c[t['severity_col']]}' is not one of "
                                f"{', '.join(SEVERITIES)}")
    live_ids = {t["task_id"] for t in board if t["column"] != "done"}
    for t in tables:
        if t["kind"] != "active":
            continue
        for n, line in t["rows"]:
            c = cells(line)
            if c[0] == PLACEHOLDER or len(c) != len(t["header"]):
                continue
            tid = normalize_debt_id(c[t["id_col"]])
            live = live_refs(dict(zip(t["header"], c)), id_index(live_ids))
            if tid and task_key(tid) not in id_index(live_ids) and len(live) > 1:
                problems.append(f"{rel}:{n}: {tid}'s Board Task names {len(live)} live board tasks "
                                f"({', '.join(live)}) — keep the one that resolves it")
    for num, ids in sorted(active.items()):
        if len(ids) > 1:
            problems.append(f"{rel}: {' / '.join(dict.fromkeys(ids))} is listed {len(ids)} times as active debt")
    for num in sorted(set(active) & set(resolved)):
        both = " / ".join(dict.fromkeys(active[num] + resolved[num]))
        problems.append(f"{rel}: {both} is listed as both active and resolved — decide which is true")
    done = id_index(done_task_ids(board))
    for tid in sorted(i for ids in active.values() for i in set(ids) if task_key(i) in done):
        as_written = "" if done[task_key(tid)] == tid else f" (on the board as {done[task_key(tid)]})"
        problems.append(f"{rel}: {tid} is active debt but its board task is Done{as_written} — mark the "
                        f"debt resolved, or reopen the task")
    return problems


BOARD_TASK_REF = re.compile(r"\b([A-Za-z]+-\d+(?:\.\d+)?)\b")
TASK_KEY = re.compile(r"^([A-Za-z]+)-(\d+)(?:\.(\d+))?$")


def task_key(tid: str) -> tuple[str, int, int | None] | str:
    """A task ID compared by number: `TD-002`, `td-2` and `TD-2` share a key, while
    `T-053.10` and `T-053.1` do not. An unrecognised ID is its own key."""
    m = TASK_KEY.match(tid)
    if not m:
        return tid
    return (m.group(1).upper(), int(m.group(2)), int(m.group(3)) if m.group(3) else None)


def id_index(ids: set[str]) -> dict:
    """Board IDs by their task_key, so a match can be reported as written on the board."""
    return {task_key(i): i for i in ids}


def board_task_refs(fields: dict[str, str]) -> list[str]:
    """Task IDs named in a debt row's `Board Task` column, in order, deduplicated.
    The cell often carries text around the ID (`T-053.10 · PR #584`); `PR #584`
    has no hyphen, so it is never mistaken for a task."""
    for key, value in fields.items():
        if key.lower().strip("* ") == "board task":
            return list(dict.fromkeys(BOARD_TASK_REF.findall(value)))
    return []


def live_refs(fields: dict[str, str], ids: dict) -> list[str]:
    """Board tasks (as written on the board) that a Board Task column names, matched by number."""
    return list(dict.fromkeys(ids[task_key(r)] for r in board_task_refs(fields) if task_key(r) in ids))


def resolve_board_task(tid: str, fields: dict[str, str], live_ids: set[str]) -> str | None:
    """The live board task a debt item is merged onto: its own ID when that is a
    board task, else the one live task its Board Task column names. IDs match by
    number (`TD-002` is board row `TD-2`), and the result is the ID as written on
    the board, because the migration finds that issue by its title prefix."""
    ids = id_index(live_ids)
    if task_key(tid) in ids:
        return ids[task_key(tid)]
    live = live_refs(fields, ids)
    return live[0] if len(live) == 1 else None


def parse_debt(root: str, board: list[dict]) -> dict:
    """Active debt items to import. Raises BoardError on a corrupt debt file.

    `board_task` is the live board task the item is merged onto — its own ID when
    that is a board task, or the single live task its `Board Task` column names —
    and `on_board` is whether there is one. Such an item must NOT become an issue
    of its own: the board task's issue is labelled as debt instead. Several debt
    items may share one task; `issue_severity` is the highest severity among every
    item on the same issue, and is the one `severity:` label that issue carries. An
    item whose Board Task is Done gets its own issue and is listed in `notes`, since
    finished work cannot carry open debt."""
    problems = debt_check(root, board)
    if problems:
        raise BoardError("\n".join(problems))
    rel = debt_file(root)
    result: dict = {"file": rel, "items": [], "not_migrated": [], "notes": []}
    if rel is None:
        return result
    live_ids = {t["task_id"] for t in board if t["column"] != "done"}
    done_ids = done_task_ids(board)
    for t in debt_tables(root, rel):
        if t["kind"] not in ("active", "resolved"):
            continue  # debt_check has already refused these
        rows = [(n, cells(l)) for n, l in t["rows"] if cells(l)[0] != PLACEHOLDER]
        if t["kind"] == "resolved":
            result["not_migrated"].append({"heading": t["heading"], "line": t["line"], "rows": len(rows)})
            continue
        for n, c in rows:
            tid = normalize_debt_id(c[t["id_col"]])
            fields = dict(zip(t["header"], c))
            board_task = resolve_board_task(tid, fields, live_ids)
            if board_task is None:
                done_refs = live_refs(fields, id_index(done_ids))
                if done_refs:
                    result["notes"].append(
                        f"{tid}: its Board Task {', '.join(done_refs)} is Done but the debt is still "
                        f"active — it gets its own issue; mark it resolved if the task fixed it")
            result["items"].append({
                "task_id": tid,
                "severity": c[t["severity_col"]].strip("* ").lower(),
                "category": c[t["category_col"]] if t["category_col"] is not None else "",
                "title": issue_title(tid, c[t["description_col"]]),
                "description": c[t["description_col"]],
                "fields": fields,
                "body": issue_body(fields, f"{rel}:{n}"),
                "source": rel, "line": n,
                "board_task": board_task,
                "on_board": board_task is not None,
            })
    # One issue carries one severity: the highest among every item living on it.
    worst: dict[str, str] = {}
    for d in result["items"]:
        key = d["board_task"] or d["task_id"]
        if key not in worst or SEVERITIES.index(d["severity"]) < SEVERITIES.index(worst[key]):
            worst[key] = d["severity"]
    for d in result["items"]:
        d["issue_severity"] = worst[d["board_task"] or d["task_id"]]
    return result


def board_tasks(root: str, done_mode: str) -> list[dict]:
    """parse(), shaped for migration. Under `freeze`, Done rows stay markdown
    history; a live story whose epic is one of them is flagged `parent_frozen`,
    because creating that epic would resurrect finished work as an open issue."""
    tasks = parse(root, done_mode)
    # A task still live is not frozen, even if an earlier phase of it sits in Done:
    # it becomes an issue, and its stories must link to it.
    done_ids = done_task_ids(tasks) - {t["task_id"] for t in tasks if t["column"] != "done"}
    if done_mode == "freeze":
        tasks = [t for t in tasks if t["column"] != "done"]
    for t in tasks:
        t["parent_frozen"] = done_mode == "freeze" and t["parent"] in done_ids
    return synthesize_epics(tasks, done_ids)


def synthesize_epics(tasks: list[dict], frozen: set[str]) -> list[dict]:
    """An epic named only by its stories' IDs (T-054.1 with no T-054 row anywhere)
    gets a placeholder issue, so the stories have a parent to link to. It takes
    the column most of its stories sit in (ties go to the further-along column)
    and is placed before them."""
    ids = {t["task_id"] for t in tasks}
    children: dict[str, list[dict]] = {}
    for t in tasks:
        p = t["parent"]
        if p and p not in ids and p not in frozen:
            children.setdefault(p, []).append(t)
    order = [c for c in COLUMNS if c != "done"]
    out: list[dict] = []
    for t in tasks:
        p = t["parent"]
        if p in children:
            kids = children.pop(p)
            # Done only when every story is; otherwise the open stories vote, ties go to
            # the further-along column, and Blocked (outside the sequence) never wins one.
            open_kids = [k for k in kids if k["column"] != "done"]
            if open_kids:
                votes = Counter(k["column"] for k in open_kids)
                column = max(votes, key=lambda c: (votes[c], -1 if c == "blocked" else order.index(c)))
            else:
                column = "done"
            description = (f"Epic {p} — placeholder created by /migrate-board: its stories "
                           f"({', '.join(k['task_id'] for k in kids)}) had no epic row on the board")
            out.append({
                "task_id": p, "column": column, "description": description,
                "title": issue_title(p, f"Epic {p} (placeholder — no board row)"),
                "agent": "", "agents": [], "priority": "", "priority_label": "",
                "fields": {}, "source": "(synthesised from its stories' IDs)",
                "body": issue_body({"Stories": ", ".join(k["task_id"] for k in kids)},
                                   "the markdown board", extra=description),
                "parent": None, "parent_frozen": False,
                "synthetic": True, "children": [k["task_id"] for k in kids],
            })
        out.append(t)
    return out


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
    board = parse(root, done_mode)  # raises on duplicate IDs, before anything is compared
    debt = parse_debt(root, board) if include_debt else None
    # What the migration created: board_tasks() adds synthetic epics and, under
    # freeze, drops Done — which is still counted below, as frozen history.
    tasks = board_tasks(root, done_mode) + [t for t in board if t["column"] == "done" and done_mode == "freeze"]
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
    """Every active debt item is an open issue labelled tech-debt and exactly one
    severity label, `issue_severity` — its own issue, or the board task's it was
    merged onto."""
    live = [i for i in issues if i.get("state_reason") != "not_planned"]
    by_id: dict[str, list[dict]] = {}
    for i in live:
        if m := TITLE_ID.match(i["title"]):
            by_id.setdefault(m.group(1), []).append(i)
    want = {d["task_id"]: d for d in debt["items"]}
    # The issue an item lives on: the board task it was merged onto, else its own.
    expected = {d["board_task"] or d["task_id"] for d in want.values()}
    missing, unlabelled, closed, severity = [], [], [], []
    for tid, d in sorted(want.items()):
        found = by_id.get(d["board_task"] or tid, [])
        if not found:
            missing.append(tid)
            continue
        i = found[0]
        if i["state"] != "open":
            closed.append(tid)
        if DEBT_LABEL not in i["labels"]:
            unlabelled.append(tid)
        else:
            have = sorted(l for l in i["labels"] if l.startswith("severity:"))
            if have != [f"severity:{d['issue_severity']}"]:
                severity.append(f"{tid} (wants severity:{d['issue_severity']}, has "
                                f"{', '.join(have) or 'none'})")
    extra = sorted({m.group(1) for i in live if DEBT_LABEL in i["labels"] and i["state"] == "open"
                    and (m := TITLE_ID.match(i["title"])) and m.group(1) not in expected})
    notes = [f"{name} {len(v)}: {', '.join(v)}" for name, v in
             (("MISSING", missing), ("NOT LABELLED tech-debt", unlabelled),
              ("CLOSED", closed), ("WRONG SEVERITY", severity), ("EXTRA", extra)) if v]
    merged = sum(1 for d in want.values() if d["on_board"])
    via_column = sum(1 for d in want.values() if d["on_board"] and task_key(d["board_task"]) != task_key(d["task_id"]))
    print(f"  {'tech-debt':12} markdown={len(want):3}  ({merged} merged onto board tasks, "
          f"{via_column} via the Board Task column)  "
          f"{'; '.join(notes) or 'OK'}")
    for nm in debt["not_migrated"]:
        print(f"  {'':12} not migrated: '{nm['heading']}' ({nm['rows']} row(s) under a resolved/closed/done heading) — stays in {debt['file']}")
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
            tasks = parse(a.root, a.done)
            for note in notices(a.root) + agent_notices(tasks):
                print(f"  note: {note}")
            print(f"Board is structurally valid. {len(tasks)} task(s) parsed.")
            if a.include_tech_debt:
                debt = parse_debt(a.root, tasks)
                if debt["file"] is None:
                    print("No tech-debt backlog found (looked in: " + ", ".join(DEBT_FILES) + ").")
                else:
                    merged = sum(1 for d in debt["items"] if d["on_board"])
                    via = sum(1 for d in debt["items"] if d["on_board"] and task_key(d["board_task"]) != task_key(d["task_id"]))
                    print(f"Tech debt is structurally valid: {len(debt['items'])} active item(s) in "
                          f"{debt['file']}, {merged} already on the board ({via} via the Board Task column).")
                    for note in debt["notes"]:
                        print(f"  note: {note}")
                    for nm in debt["not_migrated"]:
                        print(f"  note: '{nm['heading']}' ({nm['rows']} row(s) under a resolved/closed/done heading) will not be migrated.")
            return 0
        if a.json:
            print(json.dumps(board_tasks(a.root, a.done), indent=2, ensure_ascii=False))
            return 0
        if a.tech_debt:
            print(json.dumps(parse_debt(a.root, parse(a.root, a.done)), indent=2, ensure_ascii=False))
            return 0
        return verify(a.root, a.done, a.include_tech_debt)
    except BoardError as e:
        print("Board integrity problems — repair and commit before migrating:\n", file=sys.stderr)
        for p in str(e).split("\n"):
            print(f"  {p}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
