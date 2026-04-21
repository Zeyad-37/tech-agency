#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# Install Git Hooks
# Run from the project root: ./hooks/install-hooks.sh
# =============================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
GIT_HOOKS_DIR="$PROJECT_ROOT/.git/hooks"

# Verify we're in a git repo
if [ ! -d "$PROJECT_ROOT/.git" ]; then
    echo -e "${RED}Error: Not a git repository. Run from the project root.${NC}"
    exit 1
fi

# Create .git/hooks if it doesn't exist
mkdir -p "$GIT_HOOKS_DIR"

echo "Installing git hooks..."

HOOKS=("pre-commit" "pre-push" "commit-msg")

for hook in "${HOOKS[@]}"; do
    SOURCE="$SCRIPT_DIR/$hook"
    TARGET="$GIT_HOOKS_DIR/$hook"

    if [ -f "$SOURCE" ]; then
        # Remove existing hook (symlink or file)
        if [ -e "$TARGET" ] || [ -L "$TARGET" ]; then
            rm "$TARGET"
        fi

        # Create symlink
        ln -s "$SOURCE" "$TARGET"
        chmod +x "$SOURCE"

        echo -e "  ${GREEN}✓${NC} Installed $hook"
    else
        echo -e "  ${YELLOW}⚠${NC} Skipped $hook (source not found)"
    fi
done

echo ""
echo -e "${GREEN}✅ Git hooks installed successfully.${NC}"
echo ""
echo "Hooks installed:"
echo "  pre-commit  — Secrets check, force-unwrap detection, lint, large files"
echo "  commit-msg  — Commit message format: [STORY-ID] @Agent: description"
echo "  pre-push    — Branch naming, commit format, tests, build verification"
echo ""
echo "To bypass in emergencies: git commit --no-verify / git push --no-verify"
