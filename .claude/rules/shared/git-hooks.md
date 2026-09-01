# Git Hooks — What They Enforce

Git hooks are installed via `./hooks/install-hooks.sh` (symlinks `hooks/` scripts into `.git/hooks/`). Agents must write code that passes these checks. Knowing the rules upfront avoids failed commits and wasted retries.

## Commit Message Format (commit-msg hook)

Every commit message should follow this format:

```
[STORY-ID] @AgentName: Short description of what changed and why
```

Examples:
- `[US-042] @Kai: Add email validation to registration flow`
- `[BUG-017] @Swift: Fix null crash on profile load`
- `[T-016.1] @Link: Refactor shared DTO validation`

The hook **auto-normalizes** a non-conforming message instead of blocking it — a rejected commit costs the author a retype and teaches nothing, while a rewrite lands the commit and shows the correct form:

- **STORY-ID**: an explicit `[ID]` already in the message wins; otherwise it is derived from the branch (`US-016/foo` → `US-016`); if the branch carries no ID (`tech/`, `deps/`, `main`, …) the token `CHORE` is used. Number-less tokens like `CHORE`/`TECH` are accepted, and dotted sub-task IDs (`T-016.1`) are valid — the accepted format is `[A-Z]+(-[0-9]+(\.[0-9]+)?)?`. Without the dotted suffix, every sub-task commit is silently relabelled `[CHORE]`, destroying traceability on exactly the epics that use sub-task IDs.
- **@Agent**: an `@Agent` already leading the message is kept; otherwise it defaults to the git user's first name (`@Zeyad`). A mid-sentence `@mention` is not mistaken for the agent.
- **description**: the original first line with any leading `[..]` / `@agent` fragments stripped. The body is preserved untouched.

Exceptions (left untouched): merge commits (`Merge ...`), initial commits (`Initial ...`), revert commits (`Revert ...`).

## Pre-Commit Checks (run on every commit)

| Check | Blocking? | How to Fix |
|-------|-----------|------------|
| Secrets/credentials in staged files | Yes | Remove hardcoded secrets, use env vars |
| .env files staged | Yes | `git reset HEAD .env`, add to .gitignore |
| TODO/FIXME without story ID | Warning | Use `TODO(STORY-123)` or `FIXME[US-042]` |
| Kotlin `!!` force-unwraps | Yes | Use `?.`, `?:`, `require()`, or `checkNotNull()`. Escape hatch: `// safe: <reason>` |
| Swift `!` force-unwraps | Warning | Use `guard let`, `if let`, `??` |
| Lint/format (detekt, eslint, ruff, swiftlint) | Yes | Run the fixer: `./gradlew detekt`, `npx eslint --fix`, `ruff check --fix` |
| Large files (>5MB) | Yes | Use Git LFS or exclude from repo |
| Auto version bump on `main` | No (action, not a check) | Patch segment of `./VERSION` is incremented and staged into the commit when committing on `main`. To bump minor/major, edit `VERSION` manually and stage it — the hook leaves an already-staged `VERSION` untouched. Client-side only: GitHub-side PR merges (`gh pr merge`, merge button) do not run it. |

## Pre-Push Checks (run before push)

| Check | Blocking? | How to Fix |
|-------|-----------|------------|
| Branch naming convention | Warning | Rename: `git branch -m {STORY-ID}/{description}` — also accepts `epic/{EPIC-ID}-{slug}`, `tech/`, `deps/`, `hotfix/`, and sub-task IDs (`T-016.1/…`) |
| Direct push to main | Yes | Create a PR instead: `gh pr create --base main` |
| Commit message format (branch's own commits) | Yes | Amend: `git commit --amend` or interactive rebase. Only commits **unique to the branch** are validated — commits already reachable from the remote main branch are exempt, so a rebase onto `origin/main` does not drag main's squash-merge subjects and bot commits into the check and force `--no-verify`. The commit-msg hook already normalizes at commit time; this is the backstop for commits that bypassed it |
| Rules mirror integrity | Yes (consumers only) | A file in `.claude/rules/` was hand-edited. See `@.claude/rules/rules-mirror.md` — move the edit to `.claude/rules-local/` or promote it upstream, then `.claude/skills/sync-rule/mirror.sh pull`. Runs only where `.claude/rules/.synced-from` exists. `mirror.sh` is resolved from a local copy, `$CLAUDE_PLUGIN_ROOT`, or the installed plugin cache — if none is found the hook says so loudly rather than passing silently |
| Tests for affected modules | Yes | Fix failing tests |
| Build verification | Yes | Fix build errors |

## Emergency Bypass

In critical situations (hotfix, production incident), hooks can be skipped:

```bash
git commit --no-verify -m "[HOT-001] @Kai: Emergency fix for crash"
git push --no-verify
```

**This must be documented**: add a note in the post-mortem explaining why hooks were bypassed. @Sentinel and @Apex must verify the skipped checks manually before the next release.

## Agent Guidelines

To avoid hook failures:

1. **Before committing**: Run your platform's lint/format tool first.
2. **Commit messages**: Always include `[STORY-ID] @YourName:` prefix. The story ID comes from `board-context.md`.
3. **No secrets**: Use environment variables. Refer to the project README or environment configuration docs for the required variables.
4. **No force-unwraps**: Use safe alternatives. If truly safe, add `// safe: <reason>` on the same line.
5. **Before pushing**: Run the test suite for your module. The hook will run it anyway, but catching failures early saves time.
