#!/usr/bin/env bash
# =============================================================================
# sync-version.sh — VERSION is the single source of truth for the release line
#
# ./VERSION drives:
#   - the git tag cut by .github/workflows/release-on-main.yml
#   - .claude/.claude-plugin/plugin.json         (the tech-agency plugin)
#   - the "Version:" line in README.md
#
# marketing-agency versions independently (its own plugin, its own release
# cadence) and is deliberately NOT touched here.
#
# Usage:
#   sync-version.sh          # write VERSION into every manifest
#   sync-version.sh --check  # exit 1 if any manifest disagrees (CI)
# =============================================================================
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; NC='\033[0m'

cd "$(dirname "$0")/.."

[ -f VERSION ] || { echo -e "${RED}VERSION not found at repo root${NC}" >&2; exit 1; }
V="$(tr -d ' \t\r\n' < VERSION)"

echo "$V" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+$' \
  || { echo -e "${RED}VERSION is not semver: '$V'${NC}" >&2; exit 1; }

MANIFEST=".claude/.claude-plugin/plugin.json"
CHECK=false
[ "${1:-}" = "--check" ] && CHECK=true

fail=0

# --- plugin manifest --------------------------------------------------------
current=$(grep -oE '"version"[[:space:]]*:[[:space:]]*"[^"]+"' "$MANIFEST" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')
if [ "$current" != "$V" ]; then
  if $CHECK; then
    echo -e "  ${RED}drift${NC}  $MANIFEST has $current, VERSION says $V"; fail=1
  else
    # Only the version value changes; the rest of the manifest is hand-authored.
    tmp=$(mktemp)
    sed -E "s/(\"version\"[[:space:]]*:[[:space:]]*\")[0-9]+\.[0-9]+\.[0-9]+(\")/\1${V}\2/" "$MANIFEST" > "$tmp"
    mv "$tmp" "$MANIFEST"
    echo -e "  ${GREEN}synced${NC} $MANIFEST → $V"
  fi
else
  $CHECK && echo -e "  ${GREEN}ok${NC}     $MANIFEST"
fi

# --- README version line ----------------------------------------------------
readme_v=$(grep -oE '^\*\*Version:\*\* [0-9]+\.[0-9]+\.[0-9]+' README.md | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' || true)
if [ -n "$readme_v" ] && [ "$readme_v" != "$V" ]; then
  if $CHECK; then
    echo -e "  ${RED}drift${NC}  README.md has $readme_v, VERSION says $V"; fail=1
  else
    tmp=$(mktemp)
    sed -E "s/^(\*\*Version:\*\* )[0-9]+\.[0-9]+\.[0-9]+/\1${V}/" README.md > "$tmp"
    mv "$tmp" README.md
    echo -e "  ${GREEN}synced${NC} README.md → $V"
  fi
else
  $CHECK && echo -e "  ${GREEN}ok${NC}     README.md"
fi

if [ "$fail" -ne 0 ]; then
  echo -e "${RED}Version drift. Run: ./scripts/sync-version.sh${NC}" >&2
  exit 1
fi

$CHECK || echo -e "${GREEN}All manifests at $V${NC}"
