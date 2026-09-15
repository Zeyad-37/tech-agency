# Git Hooks — What They Enforce

Git hooks are installed via `./hooks/install-hooks.sh`, which symlinks the `hooks/` scripts into the location git actually reads. Agents must write code that passes these checks. Knowing the rules upfront avoids failed commits and wasted retries.

## Installation

```bash
./hooks/install-hooks.sh
```

The installer asks git where hooks belong rather than assuming `.git/hooks`:

- **Main checkout** — installs into `$(git rev-parse --git-common-dir)/hooks`, which resolves to `.git/hooks`.
- **Linked worktree** — `.git` is a *file* there, not a directory, and hooks live in the **common** dir (the main checkout's `.git/hooks`), shared by every worktree. The installer resolves that correctly and works from inside a worktree, which matters because `@.claude/rules/shared/worktree-first.md` mandates that all work happens in one.
- **`core.hooksPath` set** — installs there instead, because that setting silently disables `.git/hooks`.

Installing from a worktree prints a warning: the symlinks then point into that worktree and will dangle once it is removed. Re-run from the main checkout to make the install durable.

## Commit Message Format (commit-msg hook)

Every commit subject MUST match:

```
[TAG] @AgentName: Short description of what changed and why
```

Canonical regex — `hooks/commit-msg` and `hooks/pre-push` both use it verbatim:

```
^\[[A-Za-z]+(-[0-9]+)?\][[:space:]]+(@[A-Za-z]+:[[:space:]]+)?.{3,}
```

The hook **auto-normalizes** a non-conforming message instead of blocking it — a rejected commit costs the author a retype and teaches nothing, while a rewrite lands the commit and shows the correct form:

- **STORY-ID**: an explicit `[ID]` already in the message wins; otherwise it is derived from the branch (`US-016/foo` → `US-016`); if the branch carries no ID (`tech/`, `deps/`, `main`, …) the token `CHORE` is used. Number-less tokens like `CHORE`/`TECH` are accepted, and dotted sub-task IDs (`T-016.1`) are valid — the accepted format is `[A-Z]+(-[0-9]+(\.[0-9]+)?)?`. Without the dotted suffix, every sub-task commit is silently relabelled `[CHORE]`, destroying traceability on exactly the epics that use sub-task IDs.
- **@Agent**: an `@Agent` already leading the message is kept; otherwise it defaults to the git user's first name (`@Zeyad`). A mid-sentence `@mention` is not mistaken for the agent.
- **description**: the original first line with any leading `[..]` / `@agent` fragments stripped. The body is preserved untouched.

Exceptions (left untouched): merge commits (`Merge ...`), initial commits (`Initial ...`), revert commits (`Revert ...`).

| Part | Rule |
|------|------|
| `TAG` | Letters in square brackets, optionally followed by `-` and a number. Both `[US-042]` and bare `[TECH]` are valid. Case is not enforced, so `[tech]` passes too. |
| `@AgentName` | **Optional.** Present on agent-authored commits, absent on tooling-authored ones (the release automation emits `[TECH] @Claude: …`, but a bare `[tech] …` is equally valid). When present it must be `@Name` followed by a colon. |
| description | At least 3 characters. Says what changed and why. |

Examples that pass:

- `[US-042] @Kai: Add email validation to registration flow`
- `[BUG-017] @Swift: Fix null crash on profile load`
- `[T-015] @Claude: Dynamic base-branch resolution for dispatch`
- `[TECH] @Claude: Auto-bump VERSION to 0.1.12`
- `[tech] Tidy up the pre-push hook`

Examples that fail: `chore: bump deps` (no tag), `[US-042]` (no description), `[tech-task] @Atlas: …` (the tag suffix must be digits).

**Only the subject line is validated**, and the skip rules below are also applied to the subject only — a body line beginning with "Merge notes: …" does not exempt the commit.

Exceptions (not validated): subjects beginning `Merge `, `Initial `, or `Revert ` — git generates these itself and they cannot carry a tag.

## Pre-Commit Checks (run on every commit)

All content checks scan the **index** (staged content), never the working tree. Staging a secret and then editing it out of the file on disk does not produce a pass.

| Check | Blocking? | How to Fix |
|-------|-----------|------------|
| Secrets in staged content | Yes | Move the value to an env var or secret manager. False positive: add the path to `.secret-scan-ignore` (one path per line) |
| Sensitive files by name | Yes | `git reset HEAD <file>`, then add it to `.gitignore` |
| TODO/FIXME without story ID | Warning | Use `TODO(STORY-123)` or `FIXME[US-042]` |
| Kotlin `!!` force-unwraps | Yes | Use `?.`, `?:`, `require()`, or `checkNotNull()`. Escape hatch: `// safe: <reason>` on the same line |
| Swift `!` force-unwraps | Warning | Use `guard let`, `if let`, `??` |
| Lint/format (detekt, eslint, ruff, swiftlint) | Yes | Run the fixer: `./gradlew detekt`, `npx eslint --fix`, `ruff check --fix`, `swiftlint` |
| Large files (>5MB) | Yes | Use Git LFS or exclude from the repo. The **staged blob** is measured, not the file on disk |
| Auto version bump on `main` | No (action, not a check) | See below |

### What the secret scan detects

Two independent rules run over the added lines of the staged diff:

1. **Credential assignment** (case-insensitive) — `password`, `passwd`, `secret`, `api_key`, `apikey`, `access_token`, `auth_token`, `refresh_token`, `private_key`, `client_secret`, `aws_secret_access_key` assigned with `=` or `:` to a quoted value of 8+ characters. Both quote styles count.
2. **Credential token shapes** (case-sensitive) — GitHub tokens (`ghp_`/`gho_`/`ghu_`/`ghs_`/`ghr_` + 36 chars, and `github_pat_…`), AWS access key IDs (`AKIA` + 16), Stripe live keys (`sk_live_…`), PEM private-key headers (`-----BEGIN … PRIVATE KEY-----`), and JWTs (an `eyJ…` header segment followed by two dot-separated segments).

The offending line is **not** echoed to the terminal — only the file path and which rule matched. Inspect with `git diff --cached -- <file>`.

### Sensitive files blocked by name

Content scanning cannot help with a binary keystore, so these are blocked on filename:

`.env` and `.env.<anything>`, `id_rsa`, `id_dsa`, `id_ecdsa`, `id_ed25519`, and any `*.pem`, `*.p12`, `*.jks`, `*.keystore`.

Explicitly allowed: `.env.example`, `.env.template`, `.env.sample`, and `*.pub` public keys. `.secret-scan-ignore` also applies here, for genuine test fixtures.

### Auto version bump on `main`

The patch segment of `./VERSION` is incremented and staged into the commit when committing on `main`. To bump minor or major instead, edit `VERSION` by hand and stage it — an already-staged `VERSION` is left untouched.

It is **idempotent across amends**: `git commit --amend` re-runs the hook against a HEAD that already contains the bump, and two guards stop it bumping a second time — VERSION already staged, or an index identical to HEAD (which cannot be an ordinary commit, since git refuses empty commits). Residual gap: an amend that *also* stages new content is indistinguishable from an ordinary commit using git state alone and will bump; correct it by editing `VERSION` by hand.

Client-side only. GitHub-side PR merges (`gh pr merge`, the merge button) do not run local hooks — that path is covered by `.github/workflows/release-on-main.yml`.

## Pre-Push Checks (run before push)

The hook reads the refspecs git supplies on **stdin** (`<local ref> <local sha> <remote ref> <remote sha>`), which is the only sound source of "what is going where". Deciding from the current branch name is wrong in both directions.

| Check | Blocking? | How to Fix |
|-------|-----------|------------|
| Branch naming convention | Warning | Rename: `git branch -m {STORY-ID}/{description}` |
| Push onto — or deletion of — `refs/heads/main` | Yes | Create a PR instead: `gh pr create --base main` |
| Commit subject format (commits **unique to the branch**) | Yes | Amend: `git commit --amend`, or an interactive rebase. Commits already reachable from the remote main branch are exempt, so a rebase onto `origin/main` does not drag main's squash-merge subjects and bot commits into the check and force `--no-verify`. The commit-msg hook normalizes at commit time; this is the backstop for commits that bypassed it |
| Shared-rules copy integrity | Yes (consumers only) | A file in `.claude/rules/shared/` was hand-edited. See `@.claude/rules/shared/rules-delivery.md` — move the edit to `.claude/rules-local/` or promote it upstream, then re-sync. Runs only where `.claude/rules/shared/.synced-from` exists; the checker resolves from a local copy, `$CLAUDE_PLUGIN_ROOT`, or the installed plugin cache, and reports loudly if it cannot be found rather than passing silently |
| Tests for affected modules | Yes | Fix failing tests |
| Build verification | Yes | Fix build errors |

Consequences of reading the refspecs, all of which are the intended behaviour:

- `git push origin HEAD:main` from a feature branch **is blocked** — it is a push to main.
- `git push origin v1.2.3` from `main` **is allowed** — a tag is not a branch, and releases are tagged on main by design.
- `git push origin --delete <branch>` **is allowed**, and the content checks are skipped: a deletion pushes no commits. The one exception is `--delete main`, which is blocked by the same gate as a push onto main — a deletion is still a direct, destructive write to the branch.

Accepted branch-name prefixes (warning only when unmatched): `main`, `develop`, `{STORY-ID}/…` (e.g. `US-042/…`, `T-016.1/…`), `hotfix/…`, `release/…`, `tech/…`, `deps/…`, `epic/…`, `claude/…`, `triage/…`.

Because stdin is consumed by the hook, every subcommand it runs is given `</dev/null`.

## A Check That Cannot Run Is Not a Pass

Every security-relevant `grep` in `pre-commit` distinguishes three outcomes: exit 0 (matched), exit 1 (no match — OK), exit **2 or higher (grep itself failed)**. On the third, the hook prints a FATAL message and **aborts the commit**. grep's own stderr is never suppressed.

This exists because the previous version wrapped every check in `2>/dev/null || true`, which made a broken check indistinguishable from a clean one. Two gates were silently dead on macOS for exactly that reason.

If you hit this FATAL, fix the hook or the environment. Do not route around it with `--no-verify`.

## Emergency Bypass

In critical situations (hotfix, production incident), hooks can be skipped:

```bash
git commit --no-verify -m "[HOT-001] @Kai: Emergency fix for crash"
git push --no-verify origin "HEAD:refs/heads/$(git branch --show-current)"
```

**This must be documented**: add a note in the post-mortem explaining why hooks were bypassed. @Sentinel and @Apex must verify the skipped checks manually before the next release.

## Agent Guidelines

To avoid hook failures:

1. **Before committing**: Run your platform's lint/format tool first.
2. **Commit messages**: Always include the `[TAG]` prefix; add `@YourName:` when you are an agent. The tag comes from `board-context.md`.
3. **No secrets**: Use environment variables. Refer to the project README or environment configuration docs for the required variables.
4. **No force-unwraps**: Use safe alternatives. If truly safe, add `// safe: <reason>` on the same line.
5. **Before pushing**: Run the test suite for your module. The hook will run it anyway, but catching failures early saves time.
6. **Never `--no-verify` a FATAL**: a gate that could not run is a broken environment, not a false positive.
