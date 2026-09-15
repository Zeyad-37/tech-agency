#!/usr/bin/env python3
"""Tests for parse_board.py. Standard library only.

Run:  python3 -m unittest discover -s .claude/skills/migrate-board -p 'test_*.py'
      (`python3 -m unittest <path>` cannot import from a dot-directory like .claude/)

The corruption fixtures reproduce, class by class, the board as it stood at
6d7f42c (`git show 6d7f42c:board-context.md`) — a merge that left separator rows
before their headers, two tables fused into one, and Done / Decisions Log
sections in the live file with archive rows stranded under the wrong heading.
"""
from __future__ import annotations

import contextlib
import io
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import parse_board as pb  # noqa: E402

READY = """## Ready

| Task ID | Priority | Description | Assigned To |
|---------|----------|-------------|-------------|
| T-001 | P1 | Ready task | @Kai |
"""
IN_PROGRESS = """## In Progress (WIP limit: 2 per agent)

| Task ID | Agent | Description | Started | Cycle Day |
|---------|-------|-------------|---------|-----------|
| T-002 | @Kai | In-flight task | 2026-09-01 | 1 |
"""
REVIEW = """## Review

| Task ID | Agent | Description | Reviewer | Waiting Since |
|---------|-------|-------------|----------|---------------|
| T-003 | @Swift | Reviewed task | @Zeyad | 2026-09-02 |
| T-003.1 | @Swift | Story of an epic | @Zeyad | 2026-09-02 |
"""
BLOCKED = """## Blocked

| Task ID | Agent | Blocker | Waiting On | Blocked Since |
|---------|-------|---------|------------|---------------|
| — | — | — | — | — |
"""
BACKLOG_FILE = """# Backlog

| Task ID | Priority | Description | Requested By |
|---------|----------|-------------|--------------|
| T-004 | P2 | Backlog task | @Morgan |
"""
DONE_FILE = """# Done — 2026 Q3

| Task ID | Agent | Description | Output | Completed |
|---------|-------|-------------|--------|-----------|
| T-005 | @Claude | Finished task | PR #5 | 2026-09-03 |
"""

# The tail of the 6d7f42c board, verbatim in shape: a Done section whose
# separator has no header, a Decisions Log section whose separator is followed
# by the Done header, archive rows, and the Decisions Log header fused into the
# same table.
PRE_REPAIR_TAIL = """| — | — | — | — | — |
## Done (recent)
|---------|-------------|-------------|--------|-----------|
## Decisions Log
|------|----------|------------|---------|
| Task ID | Agent | Description | Output | Completed |
| T-026 | @Claude | Stranded archive row | PR #33 | 2026-09-01 |
| T-025 | @Claude | Stranded archive row | PR #31 | 2026-09-01 |
| Date | Decision | Decided By | ADR Ref |
| 2026-08-13 | A decision | @Zeyad | `board-in-pr.md` |
"""


def live(*sections: str) -> str:
    return "# Kanban Board Context\n\n" + "\n".join(sections)


class BoardDir(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = self._tmp.name
        os.makedirs(os.path.join(self.root, "docs", "board"))

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def write(self, rel: str, text: str) -> None:
        with open(os.path.join(self.root, rel), "w", encoding="utf-8") as fh:
            fh.write(text)

    def valid_board(self, live_text: str | None = None) -> None:
        self.write("board-context.md", live_text or live(READY, IN_PROGRESS, REVIEW, BLOCKED))
        self.write("docs/board/backlog.md", BACKLOG_FILE)
        self.write("docs/board/done-2026-Q3.md", DONE_FILE)

    def assertProblem(self, fragment: str) -> None:
        problems = pb.check(self.root)
        self.assertTrue(any(fragment in p for p in problems),
                        f"expected a problem containing {fragment!r}, got {problems}")
        with self.assertRaises(pb.BoardError):
            pb.parse(self.root)


class ValidBoard(BoardDir):
    def test_parses_every_column_in_migration_order(self) -> None:
        self.valid_board()
        self.assertEqual(pb.check(self.root), [])
        tasks = pb.parse(self.root)
        self.assertEqual([(t["task_id"], t["column"]) for t in tasks], [
            ("T-004", "backlog"), ("T-001", "ready"), ("T-002", "in-progress"),
            ("T-003", "review"), ("T-003.1", "review"), ("T-005", "done")])

    def test_fields_map_to_the_right_names(self) -> None:
        self.valid_board()
        by_id = {t["task_id"]: t for t in pb.parse(self.root)}
        self.assertEqual(by_id["T-002"]["agent"], "@Kai")
        self.assertEqual(by_id["T-002"]["description"], "In-flight task")
        self.assertEqual(by_id["T-002"]["priority"], "")
        self.assertEqual(by_id["T-001"]["priority"], "P1")
        self.assertEqual(by_id["T-003.1"]["parent"], "T-003")

    def test_placeholder_rows_are_not_tasks(self) -> None:
        self.valid_board()
        self.assertNotIn("blocked", {t["column"] for t in pb.parse(self.root)})

    def test_missing_live_section_is_not_read_as_the_whole_file(self) -> None:
        # No `## Ready`: Ready must be empty, not every table in the file.
        self.valid_board(live(IN_PROGRESS, REVIEW, BLOCKED))
        self.assertEqual([t for t in pb.parse(self.root) if t["column"] == "ready"], [])


class CorruptionClasses(BoardDir):
    """One fixture per corruption class found in the 6d7f42c board."""

    def test_separator_with_no_header_above(self) -> None:
        self.valid_board(live(READY, IN_PROGRESS, REVIEW, BLOCKED,
                              "## Parked\n|---------|------|\n| T-009 | x |\n"))
        self.assertProblem("separator row with no header above it")

    def test_header_row_inside_table_body(self) -> None:
        fused = REVIEW + "| Date | Decision | Decided By | ADR Ref |\n| 2026-08-13 | d | @Zeyad | x |\n"
        self.valid_board(live(READY, IN_PROGRESS, fused, BLOCKED))
        self.assertProblem("header row inside a table body")

    def test_separator_row_inside_table_body(self) -> None:
        fused = REVIEW + "|------|----------|------------|---------|\n"
        self.valid_board(live(READY, IN_PROGRESS, fused, BLOCKED))
        self.assertProblem("separator row inside a table body")

    def test_header_with_no_separator_after(self) -> None:
        broken = READY.replace("|---------|----------|-------------|-------------|\n", "")
        self.valid_board(live(broken, IN_PROGRESS, REVIEW, BLOCKED))
        self.assertProblem("table header with no separator row after it")

    def test_done_section_in_live_file(self) -> None:
        done = "## Done (recent)\n\n" + DONE_FILE.split("\n", 2)[2]
        self.valid_board(live(READY, IN_PROGRESS, REVIEW, BLOCKED, done))
        self.assertProblem("'## Done' must not be in the live board")

    def test_decisions_log_section_in_live_file(self) -> None:
        log = ("## Decisions Log\n\n| Date | Decision | Decided By | ADR Ref |\n"
               "|------|----------|------------|---------|\n| 2026-08-13 | d | @Zeyad | x |\n")
        self.valid_board(live(READY, IN_PROGRESS, REVIEW, BLOCKED, log))
        self.assertProblem("'## Decisions Log' must not be in the live board")

    def test_full_pre_repair_board_is_rejected_and_rows_are_not_emitted(self) -> None:
        self.valid_board(live(READY, IN_PROGRESS, REVIEW, BLOCKED.rstrip("\n").rsplit("\n", 1)[0] + "\n"
                              + PRE_REPAIR_TAIL))
        problems = pb.check(self.root)
        for fragment in ("separator row with no header above it",
                         "header row inside a table body",
                         "'## Done' must not be in the live board",
                         "'## Decisions Log' must not be in the live board"):
            self.assertTrue(any(fragment in p for p in problems), f"{fragment!r} not in {problems}")
        with self.assertRaises(pb.BoardError):
            pb.parse(self.root)
        stderr = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()) as out, contextlib.redirect_stderr(stderr):
            code = pb.main(["--json", "--root", self.root])
        self.assertEqual(code, 1)
        self.assertNotIn("T-026", out.getvalue())


class HeaderAndRowIntegrity(BoardDir):
    def test_header_drift_is_rejected_not_mis_mapped(self) -> None:
        drifted = IN_PROGRESS.replace("| Task ID | Agent | Description |", "| Task ID | Description | Agent |")
        self.valid_board(live(READY, drifted, REVIEW, BLOCKED))
        self.assertProblem("In Progress header is | Task ID | Description | Agent |")

    def test_row_arity_mismatch(self) -> None:
        short = IN_PROGRESS + "| T-006 | @Kai | Missing two cells |\n"
        self.valid_board(live(READY, short, REVIEW, BLOCKED))
        self.assertProblem("row has 3 cells, In Progress expects 5")

    def test_row_whose_first_cell_is_not_a_task_id(self) -> None:
        bad = IN_PROGRESS + "| TBD | @Kai | No ID | 2026-09-01 | 1 |\n"
        self.valid_board(live(READY, bad, REVIEW, BLOCKED))
        self.assertProblem("'TBD' is not a Task ID")


class BacklogInLiveFile(BoardDir):
    SCAFFOLD_BACKLOG = """## Backlog

| Task ID | Priority | Description | Requested By |
|---------|----------|-------------|--------------|
| T-007 | P3 | Scaffolded backlog task | @Morgan |
| T-008 | P2 | Another | @Morgan |
"""

    def test_rows_are_parsed_not_dropped(self) -> None:
        self.valid_board(live(self.SCAFFOLD_BACKLOG, READY, IN_PROGRESS, REVIEW, BLOCKED))
        backlog = [t["task_id"] for t in pb.parse(self.root) if t["column"] == "backlog"]
        self.assertEqual(backlog, ["T-004", "T-007", "T-008"])

    def test_check_reports_its_presence(self) -> None:
        self.valid_board(live(self.SCAFFOLD_BACKLOG, READY, IN_PROGRESS, REVIEW, BLOCKED))
        self.assertEqual(pb.check(self.root), [])
        notes = pb.notices(self.root)
        self.assertEqual(len(notes), 1)
        self.assertIn("'## Backlog' section (2 task(s))", notes[0])
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(pb.main(["--check", "--root", self.root]), 0)
        self.assertIn("note:", out.getvalue())

    def test_without_backlog_file_live_section_still_parsed(self) -> None:
        self.valid_board(live(self.SCAFFOLD_BACKLOG, READY, IN_PROGRESS, REVIEW, BLOCKED))
        os.remove(os.path.join(self.root, "docs/board/backlog.md"))
        backlog = [t["task_id"] for t in pb.parse(self.root) if t["column"] == "backlog"]
        self.assertEqual(backlog, ["T-007", "T-008"])


def issue(tid: str, state: str = "open", status: str | None = None,
          reason: str | None = None) -> dict:
    return {"title": f"[{tid}] title", "state": state, "state_reason": reason,
            "labels": [f"status:{status}"] if status else []}


MATCHING = [issue("T-004", status="backlog"), issue("T-001", status="ready"),
            issue("T-002", status="in-progress"), issue("T-003", status="review"),
            issue("T-003.1", status="review"), issue("T-005", "closed", reason="completed")]


class Verify(BoardDir):
    def run_verify(self, issues: list[dict]) -> tuple[int, str]:
        with mock.patch.object(pb, "fetch_issues", return_value=issues), \
                contextlib.redirect_stdout(io.StringIO()) as out:
            code = pb.verify(self.root)
        return code, out.getvalue()

    def test_exact_match_passes(self) -> None:
        self.valid_board()
        code, out = self.run_verify(MATCHING)
        self.assertEqual(code, 0, out)
        self.assertIn("All tasks accounted for.", out)

    def test_fails_on_duplicate_issue(self) -> None:
        self.valid_board()
        code, out = self.run_verify(MATCHING + [issue("T-002", status="in-progress")])
        self.assertEqual(code, 1)
        self.assertIn("DUPLICATE on GitHub: [T-002] appears 2 times", out)

    def test_duplicate_closed_as_not_planned_is_resolved(self) -> None:
        self.valid_board()
        code, out = self.run_verify(MATCHING + [issue("T-002", "closed", reason="not_planned")])
        self.assertEqual(code, 0, out)

    def test_fails_on_extras_on_github(self) -> None:
        self.valid_board()
        code, out = self.run_verify(MATCHING + [issue("T-099", status="ready")])
        self.assertEqual(code, 1)
        self.assertIn("EXTRA 1: T-099", out)

    def test_fails_on_missing(self) -> None:
        self.valid_board()
        code, out = self.run_verify([i for i in MATCHING if not i["title"].startswith("[T-003.1]")])
        self.assertEqual(code, 1)
        self.assertIn("MISSING 1: T-003.1", out)

    def test_epic_prefix_does_not_count_for_its_story(self) -> None:
        # [T-003] existing must not satisfy T-003.1.
        self.valid_board()
        code, out = self.run_verify([i for i in MATCHING if not i["title"].startswith("[T-003.1]")])
        self.assertIn("MISSING 1: T-003.1", out)

    def test_not_planned_close_is_not_done(self) -> None:
        self.valid_board()
        issues = [i for i in MATCHING if not i["title"].startswith("[T-005]")]
        code, out = self.run_verify(issues + [issue("T-005", "closed", reason="not_planned")])
        self.assertEqual(code, 1)
        self.assertIn("MISSING 1: T-005", out)

    def test_fails_when_a_column_table_is_missing_from_an_existing_source(self) -> None:
        self.valid_board()
        self.write("docs/board/backlog.md", "# Backlog\n\nNo table here.\n")
        code, out = self.run_verify([i for i in MATCHING if not i["title"].startswith("[T-004]")])
        self.assertEqual(code, 1)
        self.assertIn("NO TABLE", out)

    def test_empty_placeholder_column_is_not_a_failure(self) -> None:
        self.valid_board()
        code, out = self.run_verify(MATCHING)
        self.assertRegex(out, r"blocked\s+markdown=\s*0\s+github=\s*0\s+OK")


class FetchIssues(unittest.TestCase):
    def test_paginates_instead_of_limiting(self) -> None:
        completed = mock.Mock(returncode=0, stdout='{"title":"[T-1] a","state":"open","state_reason":null,"labels":[]}\n')
        with mock.patch.object(pb.subprocess, "run", return_value=completed) as run:
            self.assertEqual(len(pb.fetch_issues()), 1)
        argv = run.call_args.args[0]
        self.assertIn("--paginate", argv)
        self.assertNotIn("--limit", argv)


if __name__ == "__main__":
    unittest.main()
