#!/usr/bin/env bash
# =============================================================================
# check-doc-types.sh — docs/artifacts/ may only contain declared types
#
# The type list in .claude/rules/shared/handoff-protocol.md is closed: adding a
# type is a rule change, not a mkdir. Nothing enforced that before, which is how
# a consumer reached 26 folders against 10 declared types. This reads the list
# out of the rule itself, so the rule stays the single source of truth.
#
# Usable from any repo that has the rule — consumers get it via their mirror.
# Exits 0 when docs/artifacts/ does not exist yet.
# =============================================================================
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

ART="docs/artifacts"
[ -d "$ART" ] || { echo -e "${GREEN}No ${ART}/ yet — nothing to check${NC}"; exit 0; }

# The rule lives at a domain path in tech-agency and flat in a consumer mirror.
RULE=""
for c in .claude/rules/shared/handoff-protocol.md .claude/rules/handoff-protocol.md; do
  [ -f "$c" ] && RULE="$c" && break
done
[ -n "$RULE" ] || { echo -e "${RED}handoff-protocol.md not found${NC}" >&2; exit 1; }

# Declared types are the first cell of each row in the type table: | `name` | … |
DECLARED=$(grep -oE '^\| `[a-z-]+` \|' "$RULE" | tr -d '|` ' | sort -u)
[ -n "$DECLARED" ] || { echo -e "${RED}Could not parse the type table from ${RULE}${NC}" >&2; exit 1; }

fail=0
for d in "$ART"/*/; do
  [ -d "$d" ] || continue
  name=$(basename "$d")
  if ! echo "$DECLARED" | grep -qx "$name"; then
    echo -e "  ${RED}undeclared${NC}  ${ART}/${name}/"
    fail=1
  fi
done

if [ "$fail" -ne 0 ]; then
  echo
  echo -e "${YELLOW}Every folder under ${ART}/ must be a type declared in ${RULE}.${NC}"
  echo "  - Wrong home?  Move the documents into an existing type."
  echo "  - Genuinely a new kind of artifact? Add a row to the table in that rule,"
  echo "    in the same PR, and say why it recurs."
  echo
  echo "Declared types:"
  echo "$DECLARED" | sed 's/^/  /'
  exit 1
fi

echo -e "${GREEN}All ${ART}/ folders are declared${NC} ($(echo "$DECLARED" | grep -c .) types available)"
