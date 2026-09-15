#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# Install Git Hooks
# Run from anywhere inside the repository: ./hooks/install-hooks.sh
#
# WORKTREE AWARENESS
# This project mandates that all work happens in a git worktree
# (.claude/rules/shared/worktree-first.md), so the installer must work from
# one. Two things break a naive installer inside a linked worktree:
#
#   1. `.git` is a FILE containing a `gitdir:` pointer, not a directory, so a
#      `[ -d "$ROOT/.git" ]` guard reports "not a git repository".
#   2. Hooks do not live in the worktree's own git dir. Git looks them up in
#      the COMMON dir (`git rev-parse --git-common-dir`), which is the main
#      checkout's .git. Installing into `$ROOT/.git/hooks` would put them
#      somewhere git never reads.
#
# Both are handled by asking git rather than probing the filesystem.
# =============================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

# Verify we're inside a git repo. Works in a main checkout (.git is a
# directory) and in a linked worktree (.git is a file).
if ! git rev-parse --git-dir >/dev/null 2>&1; then
    echo -e "${RED}Error: not inside a git repository (checked from $PROJECT_ROOT).${NC}"
    exit 1
fi

# Where git will actually look for hooks.
#   - core.hooksPath wins when set (and silently disables .git/hooks).
#   - Otherwise it is <common git dir>/hooks. --git-common-dir resolves to the
#     MAIN checkout's .git even when we are standing in a linked worktree, and
#     may be returned relative (typically ".git"), so normalise to absolute.
HOOKS_PATH_CONFIG="$(git config --get core.hooksPath || true)"

if [ -n "$HOOKS_PATH_CONFIG" ]; then
    GIT_HOOKS_DIR="$HOOKS_PATH_CONFIG"
    case "$GIT_HOOKS_DIR" in
        /*) ;;
        *)  GIT_HOOKS_DIR="$PROJECT_ROOT/$GIT_HOOKS_DIR" ;;
    esac
    echo -e "${YELLOW}core.hooksPath is set — installing into it instead of the default location.${NC}"
else
    GIT_COMMON_DIR="$(git rev-parse --git-common-dir)"
    case "$GIT_COMMON_DIR" in
        /*) ;;
        *)  GIT_COMMON_DIR="$PROJECT_ROOT/$GIT_COMMON_DIR" ;;
    esac
    GIT_COMMON_DIR="$(cd "$GIT_COMMON_DIR" && pwd)"
    GIT_HOOKS_DIR="$GIT_COMMON_DIR/hooks"
fi

mkdir -p "$GIT_HOOKS_DIR"

# Are we in a linked worktree? If so the symlinks we create point INTO this
# worktree, and removing the worktree later leaves them dangling for every
# other worktree that shares the same common dir.
IN_LINKED_WORKTREE=false
if [ "$(git rev-parse --git-dir)" != "$(git rev-parse --git-common-dir)" ]; then
    IN_LINKED_WORKTREE=true
fi

echo "Installing git hooks..."
echo "  source: $SCRIPT_DIR"
echo "  target: $GIT_HOOKS_DIR"

HOOKS=("pre-commit" "pre-push" "commit-msg")

for hook in "${HOOKS[@]}"; do
    SOURCE="$SCRIPT_DIR/$hook"
    TARGET="$GIT_HOOKS_DIR/$hook"

    if [ -f "$SOURCE" ]; then
        # Remove existing hook (symlink or file)
        if [ -e "$TARGET" ] || [ -L "$TARGET" ]; then
            rm -f "$TARGET"
        fi

        ln -s "$SOURCE" "$TARGET"
        chmod +x "$SOURCE"

        echo -e "  ${GREEN}✓${NC} Installed $hook"
    else
        echo -e "  ${YELLOW}⚠${NC} Skipped $hook (source not found)"
    fi
done

echo ""
echo -e "${GREEN}✅ Git hooks installed successfully.${NC}"

if $IN_LINKED_WORKTREE; then
    echo ""
    echo -e "${YELLOW}⚠ You installed from a linked worktree.${NC}"
    echo -e "${YELLOW}  Hooks are shared across every worktree of this repo, but the symlinks${NC}"
    echo -e "${YELLOW}  now point into THIS worktree. They will dangle once it is removed.${NC}"
    echo -e "${YELLOW}  Re-run this script from the main checkout to make the install durable.${NC}"
fi

echo ""
echo "Hooks installed:"
echo "  pre-commit  — Secret scan of staged content, sensitive-file block,"
echo "                force-unwrap detection, lint, large files;"
echo "                auto-bumps ./VERSION (patch) on commits to main"
echo "  commit-msg  — Subject format: [TAG] @Agent: description (@Agent optional)"
echo "  pre-push    — Branch naming (warning), refspec-aware main protection,"
echo "                commit format, tests, build verification"
echo ""
echo "To bypass in emergencies: git commit --no-verify / git push --no-verify origin \"HEAD:refs/heads/\$(git branch --show-current)\""
