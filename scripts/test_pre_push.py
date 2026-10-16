#!/usr/bin/env python3
"""Behavioural tests for hooks/pre-push. Standard library only.

Each test builds a throwaway repository, then runs the hook exactly as git does:
`pre-push <remote> <url>` with one `<local ref> <local sha> <remote ref> <remote sha>`
line per pushed ref on stdin. Remote-tracking refs are written with update-ref,
so no network and no real remote are involved.

Run:  python3 -m unittest discover -s scripts -p 'test_*.py'
"""
from __future__ import annotations

import os
import shutil
import stat
import subprocess
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOK = os.path.join(ROOT, "hooks", "pre-push")
ZERO = "0" * 40
GOOD = "[T-1] @Kai: Good subject"
BAD = "no tag here"

ENV = {
    **os.environ,
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "test@example.com",
    "GIT_COMMITTER_NAME": "Test", "GIT_COMMITTER_EMAIL": "test@example.com",
}


class Repo:
    def __init__(self, path: str) -> None:
        self.path = path
        subprocess.run(["git", "init", "-q", "-b", "main", path], env=ENV, check=True)

    def git(self, *args: str) -> str:
        return subprocess.run(["git", "-C", self.path, *args], env=ENV, check=True,
                              capture_output=True, text=True).stdout.strip()

    def commit(self, subject: str, filename: str = "f.txt") -> str:
        with open(os.path.join(self.path, filename), "a") as fh:
            fh.write(subject + "\n")
        self.git("add", "-A")
        self.git("commit", "-q", "--no-verify", "-m", subject)
        return self.git("rev-parse", "HEAD")

    def remote_has(self, branch: str, sha: str) -> None:
        """Pretend origin/<branch> is at <sha>."""
        self.git("update-ref", f"refs/remotes/origin/{branch}", sha)

    def push(self, *refspecs: tuple[str, str, str, str], extra_path: str = "") -> subprocess.CompletedProcess:
        stdin = "".join(" ".join(r) + "\n" for r in refspecs)
        env = dict(ENV)
        if extra_path:
            env["PATH"] = extra_path + os.pathsep + env["PATH"]
        return subprocess.run(["bash", HOOK, "origin", "git@example.com:o/r.git"], cwd=self.path,
                              input=stdin, env=env, capture_output=True, text=True)


def fake_tool(directory: str, name: str, body: str) -> None:
    path = os.path.join(directory, name)
    with open(path, "w") as fh:
        fh.write("#!/usr/bin/env bash\n" + body + "\n")
    os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR)


class PrePush(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp()
        self.repo = Repo(os.path.join(self.tmp, "repo"))
        # main, already on the remote, carrying the kind of subjects the hook must
        # never re-check: squash-merge titles and bot commits.
        self.repo.commit("Initial commit")
        self.main = self.repo.commit("CI: bump version [skip ci]")
        self.repo.remote_has("main", self.main)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp)

    def branch(self, name: str, *subjects: str, filename: str = "f.txt") -> str:
        self.repo.git("checkout", "-q", "-b", name, "main")
        sha = self.main
        for s in subjects:
            sha = self.repo.commit(s, filename)
        return sha

    def assertPasses(self, result: subprocess.CompletedProcess) -> None:
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def assertBlocked(self, result: subprocess.CompletedProcess, needle: str) -> None:
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn(needle, result.stdout)

    # --- the main gate ------------------------------------------------------

    def test_head_to_main_from_a_feature_branch_is_blocked(self) -> None:
        sha = self.branch("T-1/x", GOOD)
        r = self.repo.push(("HEAD", sha, "refs/heads/main", self.main))
        self.assertBlocked(r, "BLOCKED")

    def test_a_feature_branch_to_its_own_name_is_allowed(self) -> None:
        sha = self.branch("T-1/x", GOOD)
        self.assertPasses(self.repo.push(("refs/heads/T-1/x", sha, "refs/heads/T-1/x", ZERO)))

    def test_a_tag_pushed_while_standing_on_main_is_allowed(self) -> None:
        self.repo.git("tag", "v1.2.3")
        r = self.repo.push(("refs/tags/v1.2.3", self.main, "refs/tags/v1.2.3", ZERO))
        self.assertPasses(r)
        self.assertNotIn("BLOCKED", r.stdout)

    def test_a_feature_branch_pushed_while_standing_on_main_is_allowed(self) -> None:
        sha = self.branch("T-1/x", GOOD)
        self.repo.git("checkout", "-q", "main")
        self.assertPasses(self.repo.push(("refs/heads/T-1/x", sha, "refs/heads/T-1/x", ZERO)))

    def test_deleting_a_branch_is_allowed_and_skips_content_checks(self) -> None:
        # Standing on a branch full of malformed commits: none of them is pushed.
        self.branch("T-1/x", BAD)
        r = self.repo.push(("(delete)", ZERO, "refs/heads/old-branch", self.main))
        self.assertPasses(r)
        self.assertIn("SKIPPED (no commits pushed)", r.stdout)

    def test_deleting_main_is_blocked(self) -> None:
        r = self.repo.push(("(delete)", ZERO, "refs/heads/main", self.main))
        self.assertBlocked(r, "(delete)")

    def test_one_bad_refspec_among_good_ones_is_blocked(self) -> None:
        sha = self.branch("T-1/x", GOOD)
        r = self.repo.push(("refs/heads/T-1/x", sha, "refs/heads/T-1/x", ZERO),
                           ("refs/heads/T-1/x", sha, "refs/heads/main", self.main))
        self.assertBlocked(r, "BLOCKED")

    def test_manual_run_without_stdin_falls_back_to_the_current_branch(self) -> None:
        r = self.repo.push()  # empty stdin, standing on main
        self.assertBlocked(r, "BLOCKED")
        sha = self.branch("T-1/x", GOOD)
        self.assertTrue(sha)
        self.assertPasses(self.repo.push())

    # --- commit range is per refspec ---------------------------------------

    def test_malformed_commit_on_the_pushed_branch_fails(self) -> None:
        sha = self.branch("T-1/x", GOOD, BAD)
        r = self.repo.push(("refs/heads/T-1/x", sha, "refs/heads/T-1/x", ZERO))
        self.assertBlocked(r, BAD)

    def test_range_comes_from_the_refspec_not_the_current_branch(self) -> None:
        good = self.branch("T-1/good", GOOD)
        self.branch("T-2/bad", BAD)  # checked out, but not what is pushed
        self.assertPasses(self.repo.push(("refs/heads/T-1/good", good, "refs/heads/T-1/good", ZERO)))

        bad = self.repo.git("rev-parse", "HEAD")
        self.repo.git("checkout", "-q", "T-1/good")
        r = self.repo.push(("refs/heads/T-2/bad", bad, "refs/heads/T-2/bad", ZERO))
        self.assertBlocked(r, BAD)

    def test_only_commits_new_to_the_remote_branch_are_checked(self) -> None:
        old = self.branch("T-1/x", BAD)  # already on the remote; not re-checked
        self.repo.remote_has("T-1/x", old)
        new = self.repo.commit(GOOD)
        self.assertPasses(self.repo.push(("refs/heads/T-1/x", new, "refs/heads/T-1/x", old)))

    def test_commits_reachable_from_origin_main_are_not_checked_after_a_rebase(self) -> None:
        old = self.branch("T-1/x", GOOD)
        self.repo.remote_has("T-1/x", old)
        # main moves on with malformed squash/bot subjects; the branch rebases onto it.
        self.repo.git("checkout", "-q", "main")
        self.repo.commit("Feature title (#239)", "main.txt")
        self.main = self.repo.commit("CI: release 1.2.3 [skip ci]", "main.txt")
        self.repo.remote_has("main", self.main)
        self.repo.git("checkout", "-q", "T-1/x")
        self.repo.git("rebase", "-q", "main")
        new = self.repo.git("rev-parse", "HEAD")
        self.assertPasses(self.repo.push(("refs/heads/T-1/x", new, "refs/heads/T-1/x", old)))

    def test_a_tag_push_does_not_check_commits(self) -> None:
        sha = self.branch("T-1/x", BAD)
        self.repo.git("tag", "v9.9.9")
        r = self.repo.push(("refs/tags/v9.9.9", sha, "refs/tags/v9.9.9", ZERO))
        self.assertPasses(r)

    def test_revert_subjects_are_exempt(self) -> None:
        sha = self.branch("T-1/x", GOOD)
        self.repo.git("revert", "--no-edit", "--no-commit", "HEAD")
        self.repo.git("commit", "-q", "--no-verify", "-m", 'Revert "[T-1] @Kai: Good subject"')
        sha = self.repo.git("rev-parse", "HEAD")
        self.assertPasses(self.repo.push(("refs/heads/T-1/x", sha, "refs/heads/T-1/x", ZERO)))

    # --- branch naming uses the remote ref ---------------------------------

    def test_branch_naming_warns_on_the_pushed_name(self) -> None:
        sha = self.branch("T-1/x", GOOD)
        r = self.repo.push(("HEAD", sha, "refs/heads/random-name", ZERO))
        self.assertPasses(r)  # warning only
        self.assertIn("- random-name", r.stdout)

    def test_claude_and_triage_prefixes_are_accepted(self) -> None:
        sha = self.branch("T-1/x", GOOD)
        for name in ("claude/foo", "triage/crash-spike", "T-016.1/x"):
            r = self.repo.push(("HEAD", sha, f"refs/heads/{name}", ZERO))
            self.assertNotIn("WARNING", r.stdout, name)

    # --- changed files and stdin -------------------------------------------

    def test_test_runners_pick_from_the_pushed_commits_and_never_see_stdin(self) -> None:
        bin_dir = os.path.join(self.tmp, "bin")
        os.makedirs(bin_dir)
        marker = os.path.join(self.tmp, "pytest-ran")
        # Fails if any of git's refspec stream reaches it.
        fake_tool(bin_dir, "pytest",
                  f'touch "{marker}"\n'
                  'if IFS= read -r -t 1 line; then echo "STDIN LEAKED: $line"; exit 1; fi\n'
                  'exit 0')
        py = self.branch("T-1/py", GOOD, filename="mod.py")
        self.branch("T-2/txt", GOOD)  # current branch touches no .py

        r = self.repo.push(("refs/heads/T-1/py", py, "refs/heads/T-1/py", ZERO),
                           ("refs/heads/T-2/txt", self.repo.git("rev-parse", "HEAD"),
                            "refs/heads/T-2/txt", ZERO),
                           extra_path=bin_dir)
        self.assertPasses(r)
        self.assertTrue(os.path.exists(marker), "pytest was not run for a pushed .py change")
        self.assertNotIn("STDIN LEAKED", r.stdout)

    def test_files_on_the_current_branch_do_not_trigger_runners(self) -> None:
        bin_dir = os.path.join(self.tmp, "bin")
        os.makedirs(bin_dir)
        fake_tool(bin_dir, "pytest", "exit 1")
        txt = self.branch("T-1/txt", GOOD)
        self.branch("T-2/py", GOOD, filename="mod.py")  # checked out, not pushed
        r = self.repo.push(("refs/heads/T-1/txt", txt, "refs/heads/T-1/txt", ZERO), extra_path=bin_dir)
        self.assertPasses(r)


if __name__ == "__main__":
    unittest.main()
