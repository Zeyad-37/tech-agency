#!/usr/bin/env python3
"""Tests for check_push_safety.py. Standard library only.

Run:  python3 -m unittest discover -s scripts -p 'test_*.py'
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_push_safety as cps  # noqa: E402


def sh(line: str) -> list[str]:
    return cps.check_text("x.sh", line + "\n")


def md(text: str) -> list[str]:
    return cps.check_text("x.md", text)


class Pushes(unittest.TestCase):
    def assertFlagged(self, line: str) -> None:
        self.assertTrue(sh(line), f"not flagged: {line}")

    def assertClean(self, line: str) -> None:
        self.assertEqual(sh(line), [], line)

    def test_explicit_refspec_is_clean(self) -> None:
        self.assertClean('git push origin "HEAD:refs/heads/$BRANCH"')
        self.assertClean('git push -u origin "HEAD:refs/heads/T-1/x"')
        self.assertClean('git push --force-with-lease origin "HEAD:refs/heads/$BRANCH"')
        self.assertClean('git -C "$WT" push origin refs/heads/epic/X:refs/heads/epic/X')

    def test_push_without_destination_is_flagged(self) -> None:
        self.assertFlagged("git push")
        self.assertFlagged("git push --no-verify")
        self.assertFlagged('git push -u origin "$BRANCH"')
        self.assertFlagged("git push origin {branch}")
        self.assertFlagged("git -c push.default=current push origin feature")

    def test_a_trailing_comment_does_not_whitelist(self) -> None:
        self.assertFlagged('git push -u origin "$BRANCH"  # never push origin main')

    def test_pushes_to_main_are_flagged(self) -> None:
        self.assertFlagged("git push origin main")
        self.assertFlagged("git push origin HEAD:main")
        self.assertFlagged("git push -u origin feature:refs/heads/main")
        self.assertFlagged("git push origin --delete main")

    def test_tags_only_when_nothing_else_is_pushed(self) -> None:
        self.assertClean("git push origin --tags")
        self.assertClean("git push origin v1.2.3")
        self.assertClean('git push origin "v${VERSION}"')
        self.assertFlagged("git push origin v1.2.3 feature")
        self.assertFlagged("git push origin --tags feature")

    def test_all_and_mirror_are_flagged(self) -> None:
        self.assertFlagged("git push --all origin")
        self.assertFlagged("git push --mirror origin")

    def test_delete_of_a_branch_is_clean(self) -> None:
        self.assertClean('git push origin --delete "$BRANCH"')
        self.assertClean("git push origin --delete <branch>")

    def test_placeholder_is_a_word_and_redirects_are_not(self) -> None:
        self.assertFlagged("git push origin <branch>")
        self.assertClean('git push origin "HEAD:refs/heads/$B" 2>&1 | tail -3')

    def test_push_inside_an_echo_is_checked(self) -> None:
        self.assertFlagged('echo -e "${YELLOW}To bypass (emergency only): git push --no-verify${NC}"')

    def test_shell_comment_lines_are_not_commands(self) -> None:
        self.assertClean('# Never `git push -u origin "$BRANCH"`: it may track main')

    def test_allow_marker_exempts_the_line(self) -> None:
        self.assertClean("git push origin HEAD:main  # push-safety: allow bot version bump")


class Branches(unittest.TestCase):
    def test_start_point_needs_no_track(self) -> None:
        for line in ('git worktree add -b "$BRANCH" "$DIR" "origin/$BASE"',
                     "git branch epic/US-100-checkout origin/main",
                     'git checkout -b feature "origin/$BASE"',
                     "git switch -c feature origin/main",
                     'git worktree add -B "$BRANCH" "$DIR" origin/main',
                     "git branch --track feature origin/main"):
            self.assertTrue(sh(line), f"not flagged: {line}")

    def test_no_track_detach_and_no_start_point_are_clean(self) -> None:
        for line in ('git worktree add --no-track -b "$BRANCH" "$DIR" "origin/$BASE"',
                     "git branch --no-track epic/US-100-checkout origin/main",
                     'git worktree add --detach "$WT" "origin/$BASE"',
                     'git worktree add "$WT" "$BRANCH"',
                     "git checkout -b feature",
                     "git checkout -b hotfix/v1.2.1/fix v1.2.1",
                     "git branch -D feature",
                     "git branch -m old new",
                     "git branch --show-current"):
            self.assertEqual(sh(line), [], line)


class Markdown(unittest.TestCase):
    def test_fenced_commands_are_checked(self) -> None:
        self.assertTrue(md("```bash\ngit push -u origin \"$BRANCH\"\n```\n"))

    def test_inline_spans_are_checked(self) -> None:
        self.assertTrue(md("Then run `git push origin HEAD:main` to publish.\n"))

    def test_prose_outside_code_is_not_a_command(self) -> None:
        self.assertEqual(md("Pushes from git push default to upstream.\n"), [])

    def test_a_bare_name_in_a_span_is_a_mention(self) -> None:
        self.assertEqual(md("Never run a bare `git push` outside these skills.\n"), [])

    def test_marker_outside_a_span_exempts_the_line(self) -> None:
        self.assertEqual(md("`git push origin HEAD:main` is blocked. <!-- push-safety: allow prose -->\n"), [])

    def test_marker_inside_a_span_is_rejected(self) -> None:
        self.assertTrue(md("`git push origin <!-- push-safety: allow prose --> x` wraps\n"))


class Repository(unittest.TestCase):
    def test_single_file_repo_reports_its_path(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            subprocess.run(["git", "init", "-q", root], check=True)
            os.makedirs(os.path.join(root, "hooks"))
            with open(os.path.join(root, "hooks", "pre-push"), "w") as fh:
                fh.write('echo "git push --no-verify"\n')
            subprocess.run(["git", "-C", root, "add", "."], check=True)
            errors = cps.check_repo(root)
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith("hooks/pre-push:1:"), errors[0])


if __name__ == "__main__":
    unittest.main()
