#!/usr/bin/env python3
"""Fail when the plugin tells anyone to push, or to create a branch, in a way that
can land commits on main.

Why: a branch cut from origin/main tracks main by default. In a repo with
push.default=upstream, a push that names no destination follows that upstream —
to main. It happened on a real consumer. So every push names its destination as
`refs/heads/<branch>`, and every branch created from a start point is --no-track.

What is scanned: every tracked skill, agent, rule, hook, script, workflow and
top-level guide. In shell and YAML every non-comment line is scanned, including
text inside `echo` strings, because a printed instruction is still an instruction.
In markdown only code is scanned: fenced blocks and inline code spans. A span
holding just `git push`, with no arguments, names the command rather than
instructing it.

Exemption: a line carrying `push-safety: allow <reason>` — in a shell comment, or
in a markdown HTML comment outside any code span (inside one it would render
literally). The marker is the only exemption; there is no substring allow-list.

Standard library only. Run:  python3 scripts/check_push_safety.py
Tests:                       python3 -m unittest discover -s scripts -p 'test_*.py'
"""
from __future__ import annotations

import os
import re
import subprocess
import sys

PATHSPECS = [
    ".claude/skills/*/SKILL.md", ".claude/rules/*.md", ".claude/rules/**/*.md",
    ".claude/agents/*.md", "hooks/*", "scripts/*", ".github/workflows/*",
    "README.md", "CLAUDE.md", "docs/guides/*.md", "docs/guides/**/*.md",
]
# Files that quote unsafe commands on purpose, as test input.
SELF = {"scripts/check_push_safety.py", "scripts/test_check_push_safety.py"}

MARKER = "push-safety: allow"
MAIN_REFS = {"main", "refs/heads/main", "master", "refs/heads/master"}
TAG = re.compile(r"^(refs/tags/|v[\dA-Z{$])")
SPAN = re.compile(r"`([^`\n]+)`")
FENCE = re.compile(r"^\s*(```|~~~)")
STOP = set(";&|`()<>\n")
PLACEHOLDER = re.compile(r"<[A-Za-z][\w.-]*>")

PUSH_VALUE_OPTS = {"-o", "--push-option", "--repo", "--receive-pack", "--exec"}
GIT_VALUE_OPTS = {"-C", "-c", "--git-dir", "--work-tree", "--namespace"}
BRANCH_NONCREATE = {"-d", "-D", "--delete", "-m", "-M", "--move", "-c", "-C", "--copy",
                    "-l", "--list", "-a", "--all", "-r", "--remotes", "--show-current",
                    "-u", "--set-upstream-to", "--unset-upstream", "--edit-description",
                    "--merged", "--no-merged", "--contains", "--no-contains", "-v", "-vv"}


def tokens(text: str) -> list[str]:
    """Shell-ish words from the start of `text` up to the end of the command:
    an unquoted ; & | ` ( ) < >, or a quote that is never closed (the end of an
    enclosing echo string). A redirect's fd number (the 2 in 2>&1) is dropped."""
    out: list[str] = []
    cur, i, in_word = "", 0, False
    while i < len(text):
        ch = text[i]
        if ch in "\"'":
            j = text.find(ch, i + 1)
            if j < 0:
                break
            cur += text[i + 1:j]
            in_word, i = True, j + 1
            continue
        if ch == "<" and (ph := PLACEHOLDER.match(text, i)):
            cur += ph.group(0)  # a documentation placeholder such as <branch>, not a redirect
            in_word, i = True, ph.end()
            continue
        if ch in STOP:
            if ch in "<>" and cur.isdigit():
                cur, in_word = "", False
            break
        if ch.isspace():
            if in_word:
                out.append(cur)
            cur, in_word = "", False
        else:
            cur += ch
            in_word = True
        i += 1
    if in_word:
        out.append(cur)
    return out


def git_commands(segment: str) -> list[list[str]]:
    """Each `git …` invocation in a segment, as [subcommand, *args]."""
    found = []
    for m in re.finditer(r"(?<![\w./-])git(?=\s)", segment):
        words = tokens(segment[m.end():])
        i = 0
        while i < len(words) and words[i].startswith("-"):
            i += 2 if words[i] in GIT_VALUE_OPTS else 1
        if i < len(words):
            found.append(words[i:])
    return found


def check_push(args: list[str]) -> str | None:
    flags, positional, i = set(), [], 0
    while i < len(args):
        a = args[i]
        if a in PUSH_VALUE_OPTS:
            i += 2
            continue
        if a.startswith("-"):
            flags.add(a.split("=", 1)[0])
        else:
            positional.append(a)
        i += 1
    if flags & {"--all", "--mirror"}:
        return "pushes every branch (--all/--mirror)"
    if not positional:
        return "names no remote or destination, so it follows the branch's upstream — possibly main"
    refspecs = [r.lstrip("+") for r in positional[1:]]
    if not refspecs:
        if "--tags" in flags:
            return None
        return "names no destination ref, so it follows the branch's upstream — possibly main"
    deleting = bool(flags & {"--delete", "-d"})
    for r in refspecs:
        dest = r.rsplit(":", 1)[-1]
        if dest in MAIN_REFS:
            return f"writes to main ({r})"
        if deleting or TAG.match(r):
            continue
        if ":" not in r:
            return f"'{r}' names no destination ref — use HEAD:refs/heads/<branch>"
        if not dest.startswith(("refs/heads/", "refs/tags/")):
            return f"destination '{dest}' is not a full refs/heads/ ref"
    return None


def check_branch(sub: str, args: list[str]) -> str | None:
    """A branch created from a start point must be --no-track."""
    if "--track" in args or "-t" in args:
        return "creates a branch with --track"
    if "--no-track" in args or "--detach" in args:
        return None
    if sub == "branch":
        if set(args) & BRANCH_NONCREATE:
            return None
        positional = [a for a in args if not a.startswith("-")]
        start = positional[1] if len(positional) >= 2 else None
    elif sub in ("checkout", "switch"):
        create = {"checkout": {"-b", "-B"}, "switch": {"-c", "-C", "--create", "--force-create"}}[sub]
        idx = next((k for k, a in enumerate(args) if a in create), None)
        if idx is None:
            return None
        rest = [a for a in args[idx + 2:] if not a.startswith("-")]
        start = rest[0] if rest else None
    elif sub == "worktree" and args[:1] == ["add"]:
        rest, positional, created, i = args[1:], [], False, 0
        while i < len(rest):
            a = rest[i]
            if a in ("-b", "-B", "--reason"):
                created = created or a != "--reason"
                i += 2
                continue
            if not a.startswith("-"):
                positional.append(a)
            i += 1
        if not created:
            return None
        start = positional[1] if len(positional) >= 2 else None
    else:
        return None
    if start is None or TAG.match(start):
        return None
    return f"creates a branch from '{start}' without --no-track, so it tracks its start point"


def check_command(words: list[str]) -> str | None:
    sub, args = words[0], words[1:]
    if sub == "push":
        return check_push(args)
    if sub in ("branch", "checkout", "switch", "worktree"):
        return check_branch(sub, args)
    return None


def strip_shell_comment(line: str) -> str | None:
    """The command part of a shell/YAML line; None for a whole-line comment."""
    if line.lstrip().startswith("#"):
        return None
    quote = None
    for i, ch in enumerate(line):
        if quote:
            quote = None if ch == quote else quote
        elif ch in "\"'":
            quote = ch
        elif ch == "#" and (i == 0 or line[i - 1].isspace()):
            return line[:i]
    return line


def check_text(path: str, text: str) -> list[str]:
    errors: list[str] = []
    markdown = path.endswith(".md")
    fenced = False
    for n, line in enumerate(text.splitlines(), 1):
        def report(msg: str) -> None:
            errors.append(f"{path}:{n}: {msg}: {line.strip()[:120]}")

        segments: list[tuple[str, bool]] = []  # (code, is_bare_mention_allowed)
        if markdown and FENCE.match(line):
            fenced = not fenced
            continue
        if markdown and not fenced:
            outside = SPAN.sub("", line)
            if any(MARKER in s for s in SPAN.findall(line)):
                report("push-safety marker inside a code span renders literally — move it outside")
            if MARKER in outside:
                continue
            segments = [(s, True) for s in SPAN.findall(line)]
        else:
            if MARKER in line:
                continue
            code = strip_shell_comment(line)
            if code is None:
                continue
            segments = [(code, False)]
        for code, mention_ok in segments:
            for words in git_commands(code):
                if mention_ok and len(words) == 1:
                    continue  # `git push` named in prose, not instructed
                msg = check_command(words)
                if msg:
                    report(msg)
    return errors


def check_repo(root: str) -> list[str]:
    files = subprocess.run(["git", "-C", root, "ls-files", "--", *PATHSPECS],
                           capture_output=True, text=True, check=True).stdout.split("\n")
    errors: list[str] = []
    for rel in sorted(set(f for f in files if f and f not in SELF)):
        try:
            with open(os.path.join(root, rel), encoding="utf-8") as fh:
                errors += check_text(rel, fh.read())
        except (UnicodeDecodeError, FileNotFoundError):
            continue
    return errors


def main() -> int:
    root = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                          capture_output=True, text=True, check=True).stdout.strip()
    errors = check_repo(root)
    for e in errors:
        path, line, msg = e.split(":", 2)
        print(f"::error file={path},line={line}::{msg.strip()}")
    if not errors:
        print("Push safety: every push names a refs/heads/ destination; every branch from a start point is --no-track.")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
