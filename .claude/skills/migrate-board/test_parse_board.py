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

    def test_cells_split_only_on_unescaped_pipes(self) -> None:
        self.assertEqual(pb.cells(r'| TD-1 | a \| b | low |'), ['TD-1', 'a | b', 'low'])
        self.assertEqual(pb.cells('| TD-1 | a | b | low |'), ['TD-1', 'a', 'b', 'low'])

    def test_escaped_pipe_in_a_board_row_is_valid(self) -> None:
        self.valid_board(live(READY.replace("Ready task", r"Ready \| task"), IN_PROGRESS, REVIEW, BLOCKED))
        self.assertEqual(pb.check(self.root), [])
        by_id = {t["task_id"]: t for t in pb.parse(self.root)}
        self.assertEqual(by_id["T-001"]["description"], "Ready | task")

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

    def test_single_board_row_cut_off_by_a_blank_line_is_not_dropped(self) -> None:
        # A one-row fragment has no second line, so a check keyed on the second
        # line never fired and the row was silently skipped.
        self.valid_board(live(READY, IN_PROGRESS, REVIEW.replace("| T-003.1 |", "\n| T-003.1 |"), BLOCKED))
        self.assertProblem("1 row(s) starting at 'T-003.1' are cut off")

    def test_table_line_inside_a_code_fence_on_the_board_is_not_a_table(self) -> None:
        self.valid_board(live(READY, IN_PROGRESS, REVIEW, BLOCKED, "## Notes\n\n```\n| a | b |\n```\n"))
        self.assertEqual(pb.check(self.root), [])

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


class DoneFreeze(BoardDir):
    """--done freeze: Done rows stay markdown history."""

    def setUp(self) -> None:
        super().setUp()
        self.valid_board(live(READY, IN_PROGRESS, """## Review

| Task ID | Agent | Description | Reviewer | Waiting Since |
|---------|-------|-------------|----------|---------------|
| T-005.1 | @Kai | Story whose epic is Done | @Zeyad | 2026-09-02 |
| T-003.1 | @Swift | Story whose epic is not on the board | @Zeyad | 2026-09-02 |
""", BLOCKED))

    def test_issues_mode_keeps_done_rows(self) -> None:
        cols = {t["column"] for t in pb.board_tasks(self.root, "issues")}
        self.assertIn("done", cols)

    def test_freeze_omits_done_rows(self) -> None:
        tasks = pb.board_tasks(self.root, "freeze")
        self.assertNotIn("done", {t["column"] for t in tasks})
        self.assertNotIn("T-005", {t["task_id"] for t in tasks})

    def test_story_of_a_frozen_epic_is_flagged(self) -> None:
        by_id = {t["task_id"]: t for t in pb.board_tasks(self.root, "freeze")}
        self.assertTrue(by_id["T-005.1"]["parent_frozen"])
        # An epic that simply has no row is still created as before.
        self.assertFalse(by_id["T-003.1"]["parent_frozen"])

    def test_issues_mode_never_flags_parent_frozen(self) -> None:
        self.assertFalse(any(t["parent_frozen"] for t in pb.board_tasks(self.root, "issues")))

    def test_verify_freeze_does_not_expect_done_on_github(self) -> None:
        issues = [issue("T-004", status="backlog"), issue("T-001", status="ready"),
                  issue("T-002", status="in-progress"), issue("T-005.1", status="review"),
                  issue("T-003.1", status="review")]
        with mock.patch.object(pb, "fetch_issues", return_value=issues), \
                contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(pb.verify(self.root, "freeze"), 0, out.getvalue())
        self.assertIn("frozen", out.getvalue())
        with mock.patch.object(pb, "fetch_issues", return_value=issues), \
                contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(pb.verify(self.root, "issues"), 1)
        self.assertIn("MISSING 1: T-005", out.getvalue())


# tech-agency's column order: '#' first, Description before Severity.
DEBT_AGENCY = """# Tech Debt Backlog

| # | Description | Severity | Category | Affected Modules | Est. Effort | Discovered By |
|---|-------------|----------|----------|------------------|-------------|---------------|
| 1 | First agency item | low | Documentation | x | 1h | review |
| 3 | Third agency item | high | Architecture | y | 1d | review |
"""

# Steady's column order: ID first, Severity before Description, plus a Resolved table.
DEBT_STEADY = """# Tech Debt Backlog

## Active Debt Items

| ID | Severity | Category | Description | Affected Modules | Effort | Discovered By | Board Task |
|----|----------|----------|-------------|------------------|--------|---------------|------------|
| TD-337 | Low | Testing Gaps | Steady low item | ios | S | @Shield | — |
| TD-002 | **High** | Architecture | Steady high item already on the board | core | M | @Sage | T-002 |

## Resolved Debt

| ID | Description | Resolution | Resolved By | Date |
|----|-------------|------------|-------------|------|
| TD-001 | Old item | Fixed | @Kai | 2026-06-01 |
"""


class DebtDir(BoardDir):
    """Fixture base only — no tests, so subclasses do not re-run another class's cases."""

    def setUp(self) -> None:
        super().setUp()
        self.valid_board()

    def put(self, rel: str, text: str) -> None:
        os.makedirs(os.path.join(self.root, os.path.dirname(rel)), exist_ok=True)
        self.write(rel, text)


class TechDebtLocation(DebtDir):

    def test_current_path(self) -> None:
        self.put("docs/guides/tech-debt/backlog.md", DEBT_AGENCY)
        self.assertEqual(pb.parse_debt(self.root, pb.parse(self.root))["file"],
                         "docs/guides/tech-debt/backlog.md")

    def test_legacy_path_is_not_silently_skipped(self) -> None:
        self.put("docs/tech-debt/backlog.md", DEBT_STEADY)
        debt = pb.parse_debt(self.root, pb.parse(self.root))
        self.assertEqual(debt["file"], "docs/tech-debt/backlog.md")
        self.assertEqual(len(debt["items"]), 2)

    def test_both_paths_is_an_error(self) -> None:
        self.put("docs/guides/tech-debt/backlog.md", DEBT_AGENCY)
        self.put("docs/tech-debt/backlog.md", DEBT_STEADY)
        with self.assertRaises(pb.BoardError) as cm:
            pb.parse_debt(self.root, pb.parse(self.root))
        self.assertIn("both", str(cm.exception))

    def test_no_debt_file_is_empty_not_an_error(self) -> None:
        debt = pb.parse_debt(self.root, pb.parse(self.root))
        self.assertEqual((debt["file"], debt["items"]), (None, []))


class TechDebtParsing(DebtDir):
    def items(self, text: str, rel: str = "docs/tech-debt/backlog.md") -> dict:
        self.put(rel, text)
        return {d["task_id"]: d for d in pb.parse_debt(self.root, pb.parse(self.root))["items"]}

    def assertDebtProblem(self, text: str, fragment: str) -> None:
        self.put("docs/tech-debt/backlog.md", text)
        problems = pb.debt_check(self.root, pb.parse(self.root))
        self.assertTrue(any(fragment in p for p in problems), f"{fragment!r} not in {problems}")
        with self.assertRaises(pb.BoardError):
            pb.parse_debt(self.root, pb.parse(self.root))

    def test_agency_column_order_maps_by_name(self) -> None:
        got = self.items(DEBT_AGENCY)
        self.assertEqual(set(got), {"TD-1", "TD-3"})  # bare '#' normalises to TD-<n>
        self.assertEqual(got["TD-3"]["severity"], "high")
        self.assertEqual(got["TD-3"]["description"], "Third agency item")
        self.assertEqual(got["TD-3"]["category"], "Architecture")

    def test_steady_column_order_maps_by_name(self) -> None:
        got = self.items(DEBT_STEADY)
        self.assertEqual(got["TD-337"]["severity"], "low")
        self.assertEqual(got["TD-337"]["description"], "Steady low item")
        self.assertEqual(got["TD-002"]["severity"], "high")  # bold markers stripped

    def test_long_description_gets_a_title_within_githubs_cap(self) -> None:
        words = " ".join(f"word{i:03}" for i in range(40))  # 319 characters
        got = self.items(DEBT_STEADY.replace("Steady low item", words))["TD-337"]
        self.assertLessEqual(len(got["title"]), 256)
        self.assertTrue(got["title"].startswith("[TD-337] word000 "))
        stem = got["title"].removesuffix("…").removeprefix("[TD-337] ")
        self.assertTrue(words.startswith(stem + " "), "title is not cut on a word boundary")
        self.assertEqual(got["description"], words)  # full text is kept
        self.assertIn(words, got["fields"].values())

    def test_short_description_title_is_unchanged(self) -> None:
        self.assertEqual(self.items(DEBT_STEADY)["TD-337"]["title"], "[TD-337] Steady low item")

    def test_resolved_table_is_not_migrated_but_reported(self) -> None:
        self.put("docs/tech-debt/backlog.md", DEBT_STEADY)
        debt = pb.parse_debt(self.root, pb.parse(self.root))
        self.assertNotIn("TD-001", {d["task_id"] for d in debt["items"]})
        self.assertEqual(debt["not_migrated"], [{"heading": "Resolved Debt", "line": 12, "rows": 1}])

    def test_item_already_a_live_board_task_is_marked_on_board(self) -> None:
        # Own ID: TD-002 is itself a live board task, so it is merged onto itself.
        self.write("board-context.md", live(READY, IN_PROGRESS.replace("T-002", "TD-002"), REVIEW, BLOCKED))
        got = self.items(DEBT_STEADY)
        self.assertEqual((got["TD-002"]["on_board"], got["TD-002"]["board_task"]), (True, "TD-002"))
        self.assertEqual((got["TD-337"]["on_board"], got["TD-337"]["board_task"]), (False, None))

    def test_board_task_column_merges_onto_that_task(self) -> None:
        # DEBT_STEADY's TD-002 names T-002 in its Board Task column; T-002 is live.
        got = self.items(DEBT_STEADY)
        self.assertEqual((got["TD-002"]["on_board"], got["TD-002"]["board_task"]), (True, "T-002"))

    def test_board_task_id_is_found_amid_text(self) -> None:
        got = self.items(DEBT_STEADY.replace("| T-002 |", "| T-002 · PR #584 |"))
        self.assertEqual(got["TD-002"]["board_task"], "T-002")

    def test_board_task_own_id_wins_over_the_column(self) -> None:
        self.write("board-context.md", live(READY, IN_PROGRESS.replace("T-002", "TD-002"), REVIEW, BLOCKED))
        got = self.items(DEBT_STEADY.replace("| T-002 |", "| T-001 |"))  # T-001 is live too
        self.assertEqual(got["TD-002"]["board_task"], "TD-002")

    def test_board_task_not_on_the_board_gets_its_own_issue(self) -> None:
        got = self.items(DEBT_STEADY.replace("| T-002 |", "| T-999 |"))
        self.assertEqual((got["TD-002"]["on_board"], got["TD-002"]["board_task"]), (False, None))

    def test_board_task_that_is_done_gets_its_own_issue_and_a_note(self) -> None:
        self.put("docs/tech-debt/backlog.md", DEBT_STEADY.replace("| T-002 |", "| T-005 |"))  # T-005 is Done
        debt = pb.parse_debt(self.root, pb.parse(self.root))
        item = {d["task_id"]: d for d in debt["items"]}["TD-002"]
        self.assertEqual((item["on_board"], item["board_task"]), (False, None))
        self.assertTrue(any("TD-002" in n and "T-005" in n and "Done" in n for n in debt["notes"]), debt["notes"])

    def test_board_task_naming_two_live_tasks_is_a_problem(self) -> None:
        self.assertDebtProblem(DEBT_STEADY.replace("| T-002 |", "| T-001 / T-002 |"),
                               "names 2 live board tasks")

    def test_several_debt_items_may_share_one_board_task(self) -> None:
        got = self.items(DEBT_STEADY.replace("| Testing Gaps | Steady low item | ios | S | @Shield | — |",
                                             "| Testing Gaps | Steady low item | ios | S | @Shield | T-002 |"))
        self.assertEqual({got["TD-337"]["board_task"], got["TD-002"]["board_task"]}, {"T-002"})

    def test_unescaped_pipe_is_rejected(self) -> None:
        self.assertDebtProblem(DEBT_STEADY.replace("Steady low item", "Steady | low item"),
                               "unescaped '|'")

    def test_escaped_pipe_is_accepted_and_unescaped(self) -> None:
        # The repair the unescaped-pipe message tells users to make must pass.
        text = DEBT_STEADY.replace("Steady low item", r"uses a \| b")
        self.put("docs/tech-debt/backlog.md", text)
        self.assertEqual(pb.debt_check(self.root, pb.parse(self.root)), [])
        self.assertEqual(self.items(text)["TD-337"]["description"], "uses a | b")

    def test_rows_split_off_by_a_blank_line_are_named_as_such(self) -> None:
        split = DEBT_STEADY.replace("| TD-002 |", "\n| TD-002 |")
        self.assertDebtProblem(split, "cut off from their table")
        self.put("docs/tech-debt/backlog.md", split)
        self.assertFalse(any("table header with no separator" in p
                             for p in pb.debt_check(self.root, pb.parse(self.root))))

    def test_bad_debt_id(self) -> None:
        self.assertDebtProblem(DEBT_STEADY.replace("| TD-337 |", "| TD-337 (follow-up) |"),
                               "is not a tech-debt ID")

    def test_bad_severity(self) -> None:
        self.assertDebtProblem(DEBT_STEADY.replace("| Low |", "| Urgent |"), "severity 'Urgent'")

    def test_duplicate_active_id(self) -> None:
        self.assertDebtProblem(DEBT_STEADY.replace("| TD-002 |", "| TD-337 |"), "listed 2 times")

    def test_duplicate_across_prefixed_and_bare_ids(self) -> None:
        # TD-002 in an ID table and `2` in a `#` table are the same item.
        api = ("\n## Active — API\n\n| # | Severity | Description |\n|---|---|---|\n"
               "| 2 | Low | Same item, bare ID |\n")
        self.put("docs/tech-debt/backlog.md", DEBT_STEADY + api)
        problems = pb.debt_check(self.root, pb.parse(self.root))
        self.assertTrue(any("TD-002" in p and "TD-2" in p and "listed 2 times" in p for p in problems), problems)

    def test_zero_padded_id_is_kept_as_written(self) -> None:
        self.assertIn("TD-002", self.items(DEBT_STEADY))

    def test_active_and_resolved_contradiction_across_id_formats(self) -> None:
        self.assertDebtProblem(DEBT_STEADY.replace("| TD-001 | Old item", "| TD-0337 | Old item"),
                               "both active and resolved")

    def test_active_and_resolved_contradiction(self) -> None:
        self.assertDebtProblem(DEBT_STEADY.replace("| TD-001 | Old item", "| TD-337 | Old item"),
                               "both active and resolved")

    def test_active_debt_whose_board_task_is_done(self) -> None:
        self.write("docs/board/done-2026-Q3.md", DONE_FILE.replace("T-005", "TD-337"))
        self.assertDebtProblem(DEBT_STEADY, "board task is Done")

    def test_table_without_a_recognised_id_column_is_a_problem(self) -> None:
        second = "\n## More Debt\n\n| Task ID | Severity | Description |\n|---|---|---|\n| TD-9 | low | Dropped |\n"
        self.assertDebtProblem(DEBT_STEADY + second, "is missing an '#' or 'ID' column")

    def test_format_documentation_table_is_not_flagged(self) -> None:
        # Verbatim shape of a real consumer's `## Format` section: it has a
        # Description column but describes the file, it is not debt.
        fmt = ("# Tech Debt Backlog\n\n## Format\n\n| Field | Description |\n|-------|-------------|\n"
               "| **ID** | TD-NNN (sequential) |\n| **Severity** | High / Medium / Low |\n\n")
        self.put("docs/tech-debt/backlog.md", fmt + DEBT_STEADY.split("\n", 1)[1])
        problems = pb.debt_check(self.root, pb.parse(self.root))
        self.assertFalse(any("under 'Format'" in p for p in problems), problems)

    def test_table_keyed_by_td_rows_without_an_id_header_is_flagged(self) -> None:
        second = "\n## More\n\n| Ref | Summary |\n|---|---|\n| TD-9 | Dropped |\n"
        self.assertDebtProblem(DEBT_STEADY + second, "is missing an '#' or 'ID' column")

    def test_unrelated_table_without_id_or_description_is_ignored(self) -> None:
        # The shape of tech-agency's own "Stranded consumer improvements" table.
        other = ("\n## Stranded\n\n| Item | Rule | Severity | Why it is generic |\n"
                 "|---|---|---|---|\n| A split | kmp.md | Medium | generic |\n")
        self.put("docs/tech-debt/backlog.md", DEBT_STEADY + other)
        self.assertEqual(pb.debt_check(self.root, pb.parse(self.root)), [])

    def test_table_without_severity_under_an_active_heading_is_a_problem(self) -> None:
        mobile = ("\n## Active — Mobile\n\n| ID | Priority | Description |\n|---|---|---|\n"
                  "| TD-50 | P1 | Open mobile item |\n| TD-51 | P2 | Another |\n")
        self.assertDebtProblem(DEBT_STEADY + mobile, "under 'Active — Mobile' is missing a Severity column")

    def test_table_without_severity_under_a_closed_heading_is_not_migrated(self) -> None:
        closed = "\n## Closed\n\n| ID | Description |\n|---|---|\n| TD-60 | Finished item |\n"
        self.put("docs/tech-debt/backlog.md", DEBT_STEADY + closed)
        debt = pb.parse_debt(self.root, pb.parse(self.root))
        self.assertIn("Closed", {nm["heading"] for nm in debt["not_migrated"]})
        self.assertNotIn("TD-60", {d["task_id"] for d in debt["items"]})

    def test_resolved_heading_wins_over_a_severity_column(self) -> None:
        # A resolved table that kept its Severity column is history, not active debt.
        done = ("\n## Resolved (2026)\n\n| ID | Severity | Description | Resolution |\n|---|---|---|---|\n"
                "| TD-900 | High | Old finished thing | Fixed in PR #9 |\n")
        self.put("docs/tech-debt/backlog.md", DEBT_STEADY + done)
        self.assertEqual(pb.debt_check(self.root, pb.parse(self.root)), [])
        debt = pb.parse_debt(self.root, pb.parse(self.root))
        self.assertNotIn("TD-900", {d["task_id"] for d in debt["items"]})
        self.assertIn("Resolved (2026)", {nm["heading"] for nm in debt["not_migrated"]})

    def test_id_and_severity_without_description_is_a_problem(self) -> None:
        web = "\n## Active — Web\n\n| ID | Severity | Title |\n|---|---|---|\n| TD-901 | High | Web item |\n"
        self.assertDebtProblem(DEBT_STEADY + web, "is missing a Description column")

    def test_hash_item_severity_without_description_is_a_problem(self) -> None:
        web = "\n## Active — Web\n\n| # | Item | Severity |\n|---|---|---|\n| 7 | Web item | Low |\n"
        self.assertDebtProblem(DEBT_STEADY + web, "is missing a Description column")

    def test_negated_done_heading_is_not_resolved(self) -> None:
        open_ = "\n## Not done yet\n\n| ID | Description |\n|---|---|\n| TD-950 | still open |\n"
        self.assertDebtProblem(DEBT_STEADY + open_, "under 'Not done yet' is missing a Severity column")

    def test_negated_done_heading_with_every_column_is_active(self) -> None:
        open_ = ("\n## Not done yet\n\n| ID | Severity | Description |\n|---|---|---|\n"
                 "| TD-951 | low | still open |\n")
        self.assertIn("TD-951", self.items(DEBT_STEADY + open_))

    def test_unresolved_heading_is_not_resolved(self) -> None:
        open_ = "\n## Unresolved\n\n| ID | Description |\n|---|---|\n| TD-952 | still open |\n"
        self.assertDebtProblem(DEBT_STEADY + open_, "under 'Unresolved' is missing a Severity column")

    def test_resolved_subheading_is_resolved(self) -> None:
        sub = "\n## Archive\n\n### Resolved\n\n| ID | Description |\n|---|---|\n| TD-960 | finished |\n"
        self.put("docs/tech-debt/backlog.md", DEBT_STEADY + sub)
        self.assertEqual(pb.debt_check(self.root, pb.parse(self.root)), [])
        debt = pb.parse_debt(self.root, pb.parse(self.root))
        self.assertIn("Resolved", {nm["heading"] for nm in debt["not_migrated"]})

    def test_table_line_inside_a_code_fence_is_not_a_table(self) -> None:
        for fence in ("```", "~~~"):
            with self.subTest(fence=fence):
                example = f"\n## Format\n\n{fence}\n| a | b |\n{fence}\n"
                self.put("docs/tech-debt/backlog.md", DEBT_STEADY + example)
                self.assertEqual(pb.debt_check(self.root, pb.parse(self.root)), [])

    def test_cut_off_row_outside_a_fence_is_still_reported(self) -> None:
        text = DEBT_STEADY.replace("| TD-002 |", "\n| TD-002 |") + "\n```\n| a | b |\n```\n"
        self.assertDebtProblem(text, "cut off from their table")

    def test_file_with_no_active_table(self) -> None:
        self.assertDebtProblem("# Tech Debt\n\nNothing here yet.\n", "no tech-debt table")


def debt_issue(tid: str, severity: str | None = "low", state: str = "open",
               board_status: str | None = "backlog") -> dict:
    labels = [pb.DEBT_LABEL] + ([f"severity:{severity}"] if severity else [])
    labels += [f"status:{board_status}"] if board_status else []
    return {"title": f"[{tid}] title", "state": state, "state_reason": None, "labels": labels}


class VerifyTechDebt(DebtDir):
    def setUp(self) -> None:
        super().setUp()
        self.write("board-context.md", live(READY, IN_PROGRESS.replace("T-002", "TD-002"), REVIEW, BLOCKED))
        self.put("docs/tech-debt/backlog.md", DEBT_STEADY)

    def board_issues(self) -> list[dict]:
        merged = issue("TD-002", status="in-progress")
        merged["labels"] += [pb.DEBT_LABEL, "severity:high"]  # the board task, labelled as debt
        return [issue("T-004", status="backlog"), issue("T-001", status="ready"), merged,
                issue("T-003", status="review"), issue("T-003.1", status="review"),
                issue("T-005", "closed", reason="completed")]

    def run_verify(self, issues: list[dict]) -> tuple[int, str]:
        with mock.patch.object(pb, "fetch_issues", return_value=issues), \
                contextlib.redirect_stdout(io.StringIO()) as out:
            code = pb.verify(self.root, "issues", include_debt=True)
        return code, out.getvalue()

    def test_matching_passes_and_debt_issue_is_not_a_backlog_extra(self) -> None:
        code, out = self.run_verify(self.board_issues() + [debt_issue("TD-337")])
        self.assertEqual(code, 0, out)
        self.assertIn("1 merged onto board tasks", out)
        self.assertIn("not migrated: 'Resolved Debt'", out)

    def test_missing_debt_issue(self) -> None:
        code, out = self.run_verify(self.board_issues())
        self.assertEqual(code, 1)
        self.assertIn("MISSING 1: TD-337", out)

    def test_board_task_merged_without_the_debt_label(self) -> None:
        issues = self.board_issues()
        issues[2]["labels"] = ["status:in-progress"]
        code, out = self.run_verify(issues + [debt_issue("TD-337")])
        self.assertEqual(code, 1)
        self.assertIn("NOT LABELLED tech-debt 1: TD-002", out)

    def test_wrong_severity(self) -> None:
        code, out = self.run_verify(self.board_issues() + [debt_issue("TD-337", severity="high")])
        self.assertEqual(code, 1)
        self.assertIn("WRONG SEVERITY 1: TD-337", out)

    def test_extra_debt_issue(self) -> None:
        code, out = self.run_verify(self.board_issues() + [debt_issue("TD-337"), debt_issue("TD-999")])
        self.assertEqual(code, 1)
        self.assertIn("EXTRA 1: TD-999", out)

    def test_item_merged_via_board_task_column_is_verified_on_that_issue(self) -> None:
        # Put the default board back (T-002 live) so TD-002 merges onto [T-002].
        self.write("board-context.md", live(READY, IN_PROGRESS, REVIEW, BLOCKED))
        issues = self.board_issues()
        issues[2] = issue("T-002", status="in-progress")
        issues[2]["labels"] += [pb.DEBT_LABEL, "severity:high"]
        code, out = self.run_verify(issues + [debt_issue("TD-337")])
        self.assertEqual(code, 0, out)
        self.assertIn("1 via the Board Task column", out)
        # The same board task without the debt label is caught, and [T-002] is not an EXTRA.
        issues[2]["labels"] = ["status:in-progress"]
        code, out = self.run_verify(issues + [debt_issue("TD-337")])
        self.assertEqual(code, 1)
        self.assertIn("NOT LABELLED tech-debt 1: TD-002", out)
        self.assertNotIn("EXTRA", out)

    def test_closed_active_debt(self) -> None:
        code, out = self.run_verify(self.board_issues() + [debt_issue("TD-337", state="closed")])
        self.assertEqual(code, 1)
        self.assertIn("CLOSED 1: TD-337", out)


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
