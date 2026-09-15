#!/usr/bin/env bash
# Fails when a skill or shared rule tells an agent to push, or to create a task
# branch, in a way that can land commits on main.
#
# Why: a branch cut from origin/main tracks main by default. In a repo with
# push.default=upstream, `git push origin <branch>` (no destination) and a bare
# `git push` both follow that upstream — to main. It happened on a real consumer.
# The fix is structural: push with an explicit `HEAD:refs/heads/<branch>` refspec,
# and create branches with --no-track so they never track main in the first place.
set -uo pipefail
cd "$(git rev-parse --show-toplevel)"

FILES=$(git ls-files '.claude/skills/*/SKILL.md' '.claude/rules/shared/*.md')
fail=0

# 1. Pushes that name no destination ref. Allowed: an explicit ':refs/heads/' refspec,
#    tag pushes, --delete, and prose describing a push the hook blocks.
while IFS= read -r hit; do
  [ -n "$hit" ] || continue
  line=${hit#*:*:}
  case "$line" in [[:space:]]\#*|\#*) continue ;; esac
  case "$line" in
    # push-safety marker: a prose line that mentions a push without instructing one.
    # " origin main": pushing main BY NAME is explicit (only /setup-repo's first push does it).
    *":refs/heads/"*|*"<!-- push-safety:"*|*" origin main"*|*"--delete"*|*"--tags"*|*" v1."*|*" v{"*|*"HEAD:main"*|*"is blocked"*) continue ;;
    # Policy prose naming the forbidden form, not instructing it.
    *"never run a bare"*|*"no bare"*) continue ;;
  esac
  echo "::error::push without an explicit destination ref — ${hit%%:*}:$(echo "$hit" | cut -d: -f2): ${line:0:110}"
  fail=1
done < <(printf '%s\n' "$FILES" | xargs grep -nE 'git (-C [^ ]+ )?push( |`|$)' 2>/dev/null)

# 2. Task branches created from a remote-tracking start point without --no-track.
while IFS= read -r hit; do
  [ -n "$hit" ] || continue
  line=${hit#*:*:}
  case "$line" in *"--no-track"*|*"--detach"*) continue ;; esac
  echo "::error::branch created tracking its start point — ${hit%%:*}:$(echo "$hit" | cut -d: -f2): ${line:0:110}"
  fail=1
done < <(printf '%s\n' "$FILES" | xargs grep -nE 'worktree add (.* )?-b |git branch [^-]+ origin/' 2>/dev/null)

if [ "$fail" = 0 ]; then echo "Push safety: every push names its destination; every branch is --no-track."; fi
exit $fail
