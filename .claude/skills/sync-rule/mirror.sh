#!/usr/bin/env bash
# =============================================================================
# mirror.sh — manage a consumer repo's .claude/rules/ mirror
#
# The canonical rules live in the tech-agency plugin. A consumer repo keeps a
# FLATTENED copy under .claude/rules/ because plugin-supplied rules do NOT
# auto-load as project instructions — only the ones in the repo's own
# .claude/rules/ do. That copy is therefore load-bearing, and it is GENERATED:
# never hand-edited. Project-specific rules live in .claude/rules-local/.
#
# Usage:
#   mirror.sh check    # verify the mirror matches its manifest (exit 1 on drift)
#   mirror.sh pull     # refresh the mirror from the resolved source
#   mirror.sh status   # print the resolved source and manifest summary
#   mirror.sh diff     # show per-file differences against the source
#
# Source resolution order (first hit wins):
#   1. $TECH_AGENCY_RULES                    — explicit path to a rules/ dir
#   2. $CLAUDE_PLUGIN_ROOT/rules             — set when running inside the plugin
#   3. newest ~/.claude/plugins/cache/*/tech-agency/*/rules
#   4. $TECH_AGENCY_PATH/.claude/rules       — a local tech-agency clone
# =============================================================================
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; DIM='\033[2m'; NC='\033[0m'

MIRROR_DIR=".claude/rules"
LOCAL_DIR=".claude/rules-local"
MANIFEST="${MIRROR_DIR}/.synced-from"

# ---------------------------------------------------------------------------
# Source resolution
# ---------------------------------------------------------------------------
resolve_source() {
  if [ -n "${TECH_AGENCY_RULES:-}" ] && [ -d "$TECH_AGENCY_RULES" ]; then
    echo "$TECH_AGENCY_RULES"; return 0
  fi

  if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -d "${CLAUDE_PLUGIN_ROOT}/rules" ]; then
    echo "${CLAUDE_PLUGIN_ROOT}/rules"; return 0
  fi

  # Newest installed plugin version. Versions sort naturally enough for
  # semver-with-single-digit segments; -V handles the general case.
  local cached
  cached=$(find "$HOME/.claude/plugins/cache" \
             -maxdepth 4 -type d -path '*/tech-agency/*/rules' 2>/dev/null \
           | sort -V | tail -1)
  if [ -n "$cached" ]; then echo "$cached"; return 0; fi

  if [ -n "${TECH_AGENCY_PATH:-}" ] && [ -d "${TECH_AGENCY_PATH}/.claude/rules" ]; then
    echo "${TECH_AGENCY_PATH}/.claude/rules"; return 0
  fi

  return 1
}

# Version label for a resolved source, most precise first:
#   1. the version segment of a plugin cache path
#   2. the VERSION file at the root of a tech-agency checkout
#   3. "unknown"
source_version() {
  local src="$1" maybe
  # .../cache/<marketplace>/<plugin>/<version>/rules
  maybe=$(basename "$(dirname "$src")")
  if [[ "$maybe" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then echo "$maybe"; return; fi
  # <repo>/.claude/rules → <repo>/VERSION
  maybe="$(dirname "$(dirname "$src")")/VERSION"
  if [ -f "$maybe" ]; then echo "$(tr -d '[:space:]' < "$maybe")"; return; fi
  echo "unknown"
}

# Exact git ref of the source when it lives in a checkout, else empty. Lets a
# mirror pulled from an unreleased branch stay traceable to a commit.
source_ref() {
  local src="$1"
  git -C "$src" rev-parse --short HEAD 2>/dev/null || true
}

sha() {
  if command -v shasum >/dev/null 2>&1; then shasum -a 256 "$1" | cut -d' ' -f1
  else sha256sum "$1" | cut -d' ' -f1; fi
}

die() { echo -e "${RED}$*${NC}" >&2; exit 1; }

require_source() {
  SRC=$(resolve_source) || die "Cannot locate tech-agency rules.
  Set TECH_AGENCY_RULES=/path/to/rules, or install the plugin:
    claude plugin marketplace add Zeyad-37/tech-agency
    claude plugin install tech-agency@tech-agency"
}

# ---------------------------------------------------------------------------
# pull — regenerate the mirror
# ---------------------------------------------------------------------------
cmd_pull() {
  require_source
  local version; version=$(source_version "$SRC")
  mkdir -p "$MIRROR_DIR"

  # Flatten: the plugin groups rules by domain, the consumer keeps them flat so
  # every rule auto-loads regardless of which stacks the project uses.
  local copied=0 names=()
  while IFS= read -r f; do
    local base; base=$(basename "$f")
    for seen in "${names[@]:-}"; do
      [ "$seen" = "$base" ] && die "Duplicate rule basename '$base' in source — cannot flatten."
    done
    names+=("$base")
    cp "$f" "${MIRROR_DIR}/${base}"
    copied=$((copied + 1))
  done < <(find "$SRC" -name '*.md' -type f | sort)

  # Drop mirrored files that no longer exist upstream. Anything not listed in
  # the previous manifest is left alone — it was never ours to delete.
  if [ -f "$MANIFEST" ]; then
    while read -r _ old; do
      [ -z "${old:-}" ] && continue
      local still=false
      for n in "${names[@]}"; do [ "$n" = "$old" ] && still=true && break; done
      if ! $still && [ -f "${MIRROR_DIR}/${old}" ]; then
        rm "${MIRROR_DIR}/${old}"
        echo -e "  ${YELLOW}removed${NC} ${old} ${DIM}(no longer in source)${NC}"
      fi
    done < <(sed -n '/^---$/,$p' "$MANIFEST" | tail -n +2)
  fi

  local ref; ref=$(source_ref "$SRC")
  {
    echo "# Generated by /sync-rule — do not edit, and do not edit the .md files"
    echo "# beside it. Project-specific rules belong in ${LOCAL_DIR}/."
    echo "source: ${SRC}"
    echo "version: ${version}"
    [ -n "$ref" ] && echo "ref: ${ref}"
    echo "synced: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "---"
    for n in "${names[@]}"; do echo "$(sha "${MIRROR_DIR}/${n}")  ${n}"; done
  } > "$MANIFEST"

  echo -e "${GREEN}Mirror refreshed:${NC} ${copied} rule(s) from ${SRC} (v${version}${ref:+ @ $ref})"
}

# ---------------------------------------------------------------------------
# check — verify mirror integrity against its manifest
# ---------------------------------------------------------------------------
cmd_check() {
  [ -f "$MANIFEST" ] || {
    echo -e "${YELLOW}No mirror manifest at ${MANIFEST}.${NC}"
    echo "  Run: .claude/skills/sync-rule/mirror.sh pull"
    exit 1
  }

  local drift=0
  while read -r want name; do
    [ -z "${name:-}" ] && continue
    if [ ! -f "${MIRROR_DIR}/${name}" ]; then
      echo -e "  ${RED}missing${NC}  ${name}"; drift=$((drift + 1)); continue
    fi
    local got; got=$(sha "${MIRROR_DIR}/${name}")
    if [ "$got" != "$want" ]; then
      echo -e "  ${RED}edited${NC}   ${name}"; drift=$((drift + 1))
    fi
  done < <(sed -n '/^---$/,$p' "$MANIFEST" | tail -n +2)

  if [ "$drift" -gt 0 ]; then
    echo -e "${RED}Mirror drift: ${drift} file(s) differ from the manifest.${NC}"
    echo -e "${YELLOW}The mirror is generated. To change a rule:${NC}"
    echo "  - project-specific  → move the change into ${LOCAL_DIR}/"
    echo "  - belongs upstream  → change it in tech-agency, release, then 'mirror.sh pull'"
    echo "  - discard the edit  → .claude/skills/sync-rule/mirror.sh pull"
    return 1
  fi

  echo -e "${GREEN}Mirror intact${NC} ($(sed -n '/^---$/,$p' "$MANIFEST" | tail -n +2 | grep -c .) files)"
}

# ---------------------------------------------------------------------------
# diff — compare mirror against the current source
# ---------------------------------------------------------------------------
cmd_diff() {
  require_source
  local changed=0
  while IFS= read -r f; do
    local base; base=$(basename "$f")
    if [ ! -f "${MIRROR_DIR}/${base}" ]; then
      echo -e "  ${YELLOW}new upstream${NC}  ${base}"; changed=$((changed + 1))
    elif ! diff -q "$f" "${MIRROR_DIR}/${base}" >/dev/null 2>&1; then
      echo -e "  ${YELLOW}outdated${NC}      ${base}"; changed=$((changed + 1))
    fi
  done < <(find "$SRC" -name '*.md' -type f | sort)

  [ "$changed" -eq 0 ] && echo -e "${GREEN}Mirror is current with ${SRC}${NC}"
  return 0
}

# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------
cmd_status() {
  if SRC=$(resolve_source); then
    echo "source:  ${SRC} (v$(source_version "$SRC"))"
  else
    echo -e "source:  ${RED}unresolved${NC}"
  fi
  if [ -f "$MANIFEST" ]; then
    grep -E '^(version|ref|synced):' "$MANIFEST" | sed 's/^/mirror:  /'
    echo "files:   $(sed -n '/^---$/,$p' "$MANIFEST" | tail -n +2 | grep -c .)"
  else
    echo -e "mirror:  ${YELLOW}not initialised${NC}"
  fi
  if [ -d "$LOCAL_DIR" ]; then
    echo "local:   $(find "$LOCAL_DIR" -name '*.md' | wc -l | tr -d ' ') project-specific rule(s)"
  fi
}

case "${1:-}" in
  pull)   cmd_pull ;;
  check)  cmd_check ;;
  diff)   cmd_diff ;;
  status) cmd_status ;;
  *) echo "usage: mirror.sh {check|pull|diff|status}" >&2; exit 2 ;;
esac
