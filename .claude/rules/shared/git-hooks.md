# Git Hooks — What They Enforce

Git hooks are installed via `./hooks/install-hooks.sh` (symlinks `hooks/` scripts into `.git/hooks/`). Agents must write code that passes these checks. Knowing the rules upfront avoids failed commits and wasted retries.

## Commit Message Format (commit-msg hook)

Every commit message MUST follow this format:

```
[STORY-ID] @AgentName: Short description of what changed and why
```

Examples:
- `[US-042] @Kai: Add email validation to registration flow`
- `[BUG-017] @Swift: Fix null crash on profile load`
- `[T-003] @Link: Refactor shared DTO validation`

Exceptions (not validated): merge commits (`Merge ...`), initial commits (`Initial ...`), revert commits (`Revert ...`).

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
| Branch naming convention | Warning | Rename: `git branch -m {STORY-ID}/{description}` or `tech/{description}` or `deps/{package}` |
| Direct push to main | Yes | Create a PR instead: `gh pr create --base main` |
| Commit message format (all commits) | Yes | Amend: `git commit --amend` or interactive rebase |
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
