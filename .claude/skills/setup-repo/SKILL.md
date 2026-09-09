---
name: setup-repo
description: "Set up a repository with the Tech Agency configuration — works for both new and existing projects. Detects what's already in place and only sets up the missing parts, and declares the plugin in the project's .claude/settings.json so it is available in cloud Claude Code sessions (which have no /plugin command). Use when the user says 'setup repo', 'new repo', 'scaffold project', 'create a new project', 'initialize repo', 'bootstrap repo', 'add agency to project', 'integrate agency', 'make the plugin available in cloud sessions', or describes wanting to configure a codebase with the Tech Agency system."
---

# Setup Repository

You are Sentinel (DevOps/SRE) coordinating with Sage (Solutions Architect). This skill sets up a repository with the full Tech Agency system — project structure, coding standards, CI/CD pipelines, and git hooks.

**It works for both new and existing projects.** It detects what's already in place and only sets up what's missing.

## Step 0: Locate the Plugin Payload (mandatory — everything else copies from here)

Every file this skill installs is copied out of the tech-agency plugin. Resolve where that payload lives **before** doing anything else. There is no `project-template/` directory — that placeholder never existed.

```bash
resolve_plugin_root() {
    # 1. Normal case: tech-agency is installed as a plugin. Claude Code exports
    #    CLAUDE_PLUGIN_ROOT pointing at the installed copy of the plugin's
    #    `.claude/` directory (the marketplace manifest declares source "./.claude").
    if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -d "${CLAUDE_PLUGIN_ROOT}/rules/shared" ]; then
        printf '%s\n' "${CLAUDE_PLUGIN_ROOT%/}"
        return 0
    fi
    # 2. Fallback: we are running inside the tech-agency repo itself (development
    #    or vendored-checkout use). Identify it by its plugin manifest — NOT by the
    #    mere presence of `.claude/`, which every consumer also has and which would
    #    make the skill copy files onto themselves.
    if [ -f ".claude-plugin/plugin.json" ] && [ -d ".claude/rules/shared" ]; then
        printf '%s\n' "$(pwd)/.claude"
        return 0
    fi
    return 1
}

PLUGIN_ROOT="$(resolve_plugin_root)" || {
    echo "ERROR: cannot locate the tech-agency plugin payload."
    echo "Install the plugin, then re-run:"
    echo "  claude plugin marketplace add Zeyad-37/tech-agency"
    echo "  claude plugin install tech-agency@tech-agency"
    exit 1
}

# Assets that live OUTSIDE `.claude/` (git hook scripts, reference docs) sit one
# level up from the plugin root when the plugin was installed from a repo clone.
# Probe rather than assume — some install layouts ship only the `.claude/` subtree.
PAYLOAD_ROOT="$(cd "$PLUGIN_ROOT/.." && pwd)"
[ -d "$PAYLOAD_ROOT/hooks" ] && PAYLOAD_HAS_HOOKS=true || PAYLOAD_HAS_HOOKS=false
[ -d "$PAYLOAD_ROOT/docs" ]  && PAYLOAD_HAS_DOCS=true  || PAYLOAD_HAS_DOCS=false

echo "PLUGIN_ROOT=$PLUGIN_ROOT"
echo "PAYLOAD_ROOT=$PAYLOAD_ROOT (hooks=$PAYLOAD_HAS_HOOKS docs=$PAYLOAD_HAS_DOCS)"
```

Carry `$PLUGIN_ROOT`, `$PAYLOAD_ROOT`, `$PAYLOAD_HAS_HOOKS` and `$PAYLOAD_HAS_DOCS` through every later step. If either `PAYLOAD_HAS_*` is `false`, the corresponding step generates the file inline instead of copying — the step says so where it applies.

### What gets installed into the consumer, and what does not

The agency splits its rules two ways. This split is the whole reason the copy list below is short:

| Rule set | Count | Where it ends up | Why |
|---|---|---|---|
| **Shared rules** (`rules/shared/*.md`) | 10+ | **Copied** into the consumer's `.claude/rules/shared/` | Claude Code auto-loads project rules every session. These describe how the agency operates — preamble, board protocol, worktree protocol, standards — and every agent needs them resident. |
| **Language coding standards** (`rules/mobile/…`, `rules/backend/…`, `rules/web/…`) | 8 | **Stay in the plugin.** Read on demand from `${CLAUDE_PLUGIN_ROOT}/rules/<path>.md` | They are large. Auto-loading all eight costs roughly 65k tokens of context in every session, on every project, most of it for stacks the project does not use. An agent reads only the standard for the stack its task is in. |

Tell the user this explicitly in the final report — otherwise "my project has 10 rule files but the agency ships 18" reads like a broken install. Never quote a hard total: the counts are whatever the installed plugin ships, and the enumeration below globs the payload rather than hardcoding a list, so a rule added upstream arrives without this skill changing. Report the number the glob actually found.

When a skill or agent needs a coding standard, it references it as `${CLAUDE_PLUGIN_ROOT}/rules/<path>.md`, falling back to `.claude/rules/<path>.md` when `CLAUDE_PLUGIN_ROOT` is unset (which is the case when working inside the tech-agency repo itself).

The nested directory layout (`rules/shared/`, `rules/mobile/android/`, …) is canonical everywhere, consumers included. Never write a flat `.claude/rules/<name>.md` path.

## Step 1: Detect Project Mode

Check if we're working with an existing project or a new one:

```bash
# Check for existing project signals
ls -la .git/ 2>/dev/null && echo "GIT_EXISTS=true" || echo "GIT_EXISTS=false"
ls CLAUDE.md 2>/dev/null && echo "CLAUDE_MD_EXISTS=true" || echo "CLAUDE_MD_EXISTS=false"
ls -la .claude/rules/ 2>/dev/null && echo "RULES_EXIST=true" || echo "RULES_EXIST=false"
ls -la .claude/skills/ 2>/dev/null && echo "SKILLS_EXIST=true" || echo "SKILLS_EXIST=false"
ls -la hooks/ 2>/dev/null && echo "HOOKS_EXIST=true" || echo "HOOKS_EXIST=false"
ls -la .github/workflows/ 2>/dev/null && echo "CI_EXISTS=true" || echo "CI_EXISTS=false"
ls board-context.md 2>/dev/null && echo "BOARD_EXISTS=true" || echo "BOARD_EXISTS=false"
gh repo view --json nameWithOwner >/dev/null 2>&1 \
  && echo "GITHUB_REMOTE=true" || echo "GITHUB_REMOTE=false"   # picks the board backend
ls -la .git/hooks/pre-commit 2>/dev/null && echo "GIT_HOOKS_INSTALLED=true" || echo "GIT_HOOKS_INSTALLED=false"
```

Based on the results, set the mode:

- **New project**: No `.git/` directory. Start from scratch (Step 2).
- **Existing project**: Has `.git/` and source code. Run the audit (Step 3) to identify what's missing.

## Step 2: Gather Project Specs

Collect these from the user (ask if not provided):

- **Project name**: kebab-case identifier (e.g., `my-notes-app`)
- **Description**: 1-2 sentence summary
- **Target platforms**: Which of these? (select all that apply)
  - Android (Compose) — uses `compose-coding-standards.md`
  - iOS (SwiftUI) — uses `swiftui-coding-standards.md`
  - Web (React/Next.js) — uses `react-coding-standards.md`
  - KMP Shared — uses `kmp-coding-standards.md`
  - Backend: Node.js/Fastify — uses `node-coding-standards.md`
  - Backend: Python/FastAPI — uses `python-coding-standards.md`
  - Backend: JVM/Spring Boot — uses `jvm-coding-standards.md`
  - Backend: Ktor Server — uses `ktor-server-coding-standards.md`
- **GitHub visibility**: public or private (new projects only)
- **GitHub org or personal**: org name or personal account (new projects only)
- **Branch protection**: enable on `main`? (recommended: yes)

For existing projects, auto-detect platforms from the codebase:

```bash
# Auto-detect platforms
ls gradlew 2>/dev/null && echo "KOTLIN/GRADLE detected"
ls Package.swift 2>/dev/null && echo "SWIFT detected"
ls package.json 2>/dev/null && echo "NODE/REACT detected"
ls pyproject.toml setup.py requirements.txt 2>/dev/null && echo "PYTHON detected"
ls -d **/commonMain 2>/dev/null && echo "KMP detected"
ls -d **/androidApp 2>/dev/null && echo "ANDROID detected"
ls -d **/iosApp 2>/dev/null && echo "IOS detected"
cat settings.gradle.kts 2>/dev/null | grep -i "ktor" && echo "KTOR detected"
cat build.gradle.kts 2>/dev/null | grep -i "spring" && echo "SPRING detected"
```

Confirm detected platforms with the user before proceeding.

## Step 3: Audit Existing Setup (Existing Projects Only)

Run a comprehensive audit and build a checklist of what needs to be done:

```bash
echo "=== AGENCY SETUP AUDIT ==="

# 1. Git
echo "--- Git ---"
test -d .git && echo "[✓] Git repo exists" || echo "[✗] No git repo — need to initialize"

# 2. CLAUDE.md
echo "--- CLAUDE.md ---"
test -f CLAUDE.md && echo "[✓] CLAUDE.md exists" || echo "[✗] CLAUDE.md missing"

# 3. Board
echo "--- Board ---"
grep -q '"board_backend"' .claude/settings.json 2>/dev/null \
  && echo "[✓] board_backend set: $(grep -o '"board_backend"[^,}]*' .claude/settings.json)" \
  || echo "[✗] board_backend not set in .claude/settings.json"
# board-context.md is only expected on the markdown backend.
grep -q '"board_backend": *"markdown"' .claude/settings.json 2>/dev/null && {
  test -f board-context.md && echo "[✓] board-context.md exists" || echo "[✗] board-context.md missing"
}

# 4. Shared rules — everything the plugin ships under rules/shared/ gets copied
#    into the consumer. Enumerate by glob, never a hardcoded list: adding a rule
#    to the plugin must not require editing this skill.
#    Paths are NESTED (rules/shared/<name>.md). A flat `.claude/rules/<name>.md`
#    test reports every rule missing, because `.claude/rules/` holds only
#    directories.
#    NOTE: iterate via `find | while read`, not `for x in $VAR` — unquoted
#    parameter expansion does not word-split in zsh, so a space-separated list
#    would run the loop body exactly once with the whole string as $rule.
echo "--- Shared Rules ---"
find "${PLUGIN_ROOT}/rules/shared" -maxdepth 1 -name '*.md' -exec basename {} \; \
| sort | while read -r rule; do
    test -f ".claude/rules/shared/${rule}" \
        && echo "[✓] rules/shared/${rule}" \
        || echo "[✗] rules/shared/${rule} missing"
done

# 5. Language coding standards — NOT copied into the consumer. They are read on
#    demand from the plugin. Audit that the plugin can actually serve them, not
#    that the consumer holds a copy.
echo "--- Language Coding Standards (served from the plugin, not copied) ---"
find "${PLUGIN_ROOT}/rules" -mindepth 2 -name '*-coding-standards.md' \
| sed "s|^${PLUGIN_ROOT}/rules/||" | sort | while read -r std; do
    echo "[✓] served: ${std}"
done
[ "$(find "${PLUGIN_ROOT}/rules" -mindepth 2 -name '*-coding-standards.md' | grep -c .)" -ge 8 ] \
    || echo "[✗] fewer than 8 coding standards in the plugin — payload looks incomplete"
# A stray copy in the consumer is drift, not a gap — flag it so the user can delete it.
if [ -d .claude/rules ]; then
    find .claude/rules -name '*-coding-standards.md' 2>/dev/null \
        | sed 's|^|[!] stale local copy (delete — served by the plugin): |'
fi

# 6. Skills — enumerate what the plugin actually ships. Never a hardcoded list:
#    the previous 24-name list silently omitted 24 skills, and because the audit
#    and the copy shared that list the omission was invisible.
echo "--- Skills provided by the plugin ---"
PLUGIN_SKILLS="$(find "${PLUGIN_ROOT}/skills" -mindepth 2 -maxdepth 2 -name SKILL.md \
    -exec dirname {} \; | xargs -n1 basename | sort)"
echo "$PLUGIN_SKILLS" | tr '\n' ' ' | fold -s -w 100 | sed 's/^/    /'
echo "    ($(echo "$PLUGIN_SKILLS" | grep -c .) skills — invoked as /tech-agency:<name>)"

# 7. Settings & sandbox
echo "--- Settings ---"
test -f .claude/settings.json && echo "[✓] .claude/settings.json" || echo "[✗] .claude/settings.json missing"
if [ -f .claude/settings.json ]; then
    jq -e 'has("sandbox")' .claude/settings.json >/dev/null 2>&1 \
        && echo "[✓] sandbox block present" || echo "[✗] sandbox block missing"
    REPO="$(basename "$(git rev-parse --show-toplevel 2>/dev/null || pwd)")"
    jq -e --arg wt "../${REPO}-worktrees" \
        '(.sandbox.filesystem.allowWrite // []) | index($wt)' .claude/settings.json >/dev/null 2>&1 \
        && echo "[✓] worktree write path ../${REPO}-worktrees allowed" \
        || echo "[✗] worktree write path ../${REPO}-worktrees NOT allowed — worktree-first is blocked"
    # Cloud-session availability: the plugin must be declared in committed
    # settings, because cloud sessions have no /plugin command (see Step 6i).
    jq -e '.extraKnownMarketplaces["tech-agency"].source.repo == "Zeyad-37/tech-agency"' \
        .claude/settings.json >/dev/null 2>&1 \
        && echo "[✓] tech-agency marketplace declared (cloud sessions)" \
        || echo "[✗] tech-agency marketplace NOT declared — plugin unavailable in cloud sessions"
    jq -e '.enabledPlugins["tech-agency@tech-agency"] == true' \
        .claude/settings.json >/dev/null 2>&1 \
        && echo "[✓] tech-agency@tech-agency enabled (cloud sessions)" \
        || echo "[✗] tech-agency@tech-agency NOT enabled — plugin unavailable in cloud sessions"
fi

# 8. Hooks
echo "--- Git Hooks ---"
test -f hooks/pre-commit && echo "[✓] hooks/pre-commit" || echo "[✗] hooks/pre-commit missing"
test -f hooks/commit-msg && echo "[✓] hooks/commit-msg" || echo "[✗] hooks/commit-msg missing"
test -f hooks/pre-push && echo "[✓] hooks/pre-push" || echo "[✗] hooks/pre-push missing"
test -f hooks/install-hooks.sh && echo "[✓] hooks/install-hooks.sh" || echo "[✗] hooks/install-hooks.sh missing"
test -L .git/hooks/pre-commit && echo "[✓] hooks installed (symlinked)" || echo "[✗] hooks not installed"

# 9. CI/CD
echo "--- CI/CD Workflows ---"
test -f .github/workflows/pr-checks.yml && echo "[✓] PR quality gates" || echo "[✗] PR quality gates missing"
test -f .github/workflows/verify-main.yml && echo "[✓] Verify main" || echo "[✗] Verify main missing"
test -f .github/workflows/release.yml && echo "[✓] Release flow" || echo "[✗] Release flow missing"
test -f .github/workflows/hotfix.yml && echo "[✓] Hotfix flow" || echo "[✗] Hotfix flow missing"

# 10. Docs
echo "--- Reference Docs ---"
for doc in setup-guide migration-guide ci-enforcement-policy incident-response; do
    test -f "docs/${doc}.md" && echo "[✓] docs/${doc}.md" || echo "[✗] docs/${doc}.md missing"
done

echo ""
echo "=== AUDIT COMPLETE ==="
```

Present the audit results to the user. Then proceed to set up ONLY the items marked `[✗]`.

## Step 4: Initialize Git (New Projects Only)

Skip this step if `.git/` already exists.

```bash
mkdir {project-name}
cd {project-name}
git init
git branch -m main
```

Create the initial `.gitignore` appropriate for the selected platforms:

- KMP/Android/JVM/Ktor: Kotlin/Gradle ignores (`.gradle/`, `build/`, `local.properties`, `.idea/`)
- iOS: Xcode ignores (`*.xcuserdata`, `DerivedData/`, `Pods/`)
- React/Next.js: Node ignores (`node_modules/`, `.next/`, `.env.local`)
- Python: Python ignores (`__pycache__/`, `.venv/`, `*.pyc`, `.env`)
- Common: `.env`, `.DS_Store`, `*.log`, `.claude/crashlytics-context.md`

For existing projects, review `.gitignore` and suggest additions if agency-specific patterns are missing (e.g., `.claude/crashlytics-context.md`).

## Step 5: Create Project Structure (New Projects Only)

Skip this step for existing projects — they already have a project structure.

Based on the selected platforms, scaffold the directory structure following the coding standards.

For **each selected platform**, create the directory tree as defined in its coding standards file:

### KMP (if selected)
Read `${CLAUDE_PLUGIN_ROOT}/rules/mobile/shared/kmp-coding-standards.md` (fallback `.claude/rules/mobile/shared/kmp-coding-standards.md`) — Project Structure section:
```
project/
├── build-logic/plugins/
├── core/architecture/, core/database/, core/network/, core/test-base/, core/time/
├── features/{feature}/domain/, data/, sharedPresentation/
├── gradle/libs.versions.toml
```

### Android (if selected)
Read `${CLAUDE_PLUGIN_ROOT}/rules/mobile/android/compose-coding-standards.md` (fallback `.claude/rules/mobile/android/compose-coding-standards.md`) — Project Structure section:
```
androidApp/src/main/kotlin/com/example/{project}/
├── navigation/, features/, core/, designsystem/, shared/
```

### iOS (if selected)
Read `${CLAUDE_PLUGIN_ROOT}/rules/mobile/ios/swiftui-coding-standards.md` (fallback `.claude/rules/mobile/ios/swiftui-coding-standards.md`) — Project Structure section:
```
App/
├── App/, Features/, Core/, DesignSystem/, Resources/, Shared/KMP/
```

### React/Next.js (if selected)
Read `${CLAUDE_PLUGIN_ROOT}/rules/web/react-coding-standards.md` (fallback `.claude/rules/web/react-coding-standards.md`) — Project Structure section:
```
src/
├── app/, components/ui/, components/features/, hooks/, lib/, stores/, styles/, types/
```

### Node.js/Fastify (if selected)
Read `${CLAUDE_PLUGIN_ROOT}/rules/backend/nodejs/node-coding-standards.md` (fallback `.claude/rules/backend/nodejs/node-coding-standards.md`) — Project Structure section:
```
src/
├── config/, modules/, shared/, workers/, prisma/
```

### Python/FastAPI (if selected)
Read `${CLAUDE_PLUGIN_ROOT}/rules/backend/python/python-coding-standards.md` (fallback `.claude/rules/backend/python/python-coding-standards.md`) — Project Structure section:
```
src/
├── config/, modules/, shared/, workers/, alembic/
```

### JVM/Spring Boot (if selected)
Read `${CLAUDE_PLUGIN_ROOT}/rules/backend/jvm/jvm-coding-standards.md` (fallback `.claude/rules/backend/jvm/jvm-coding-standards.md`) — Project Structure section:
```
src/main/kotlin/com/example/{project}/
├── config/, modules/, shared/
src/main/resources/db/migration/
```

### Ktor Server (if selected)
Read `${CLAUDE_PLUGIN_ROOT}/rules/backend/kotlin/ktor-server-coding-standards.md` (fallback `.claude/rules/backend/kotlin/ktor-server-coding-standards.md`) — Project Structure section:
```
server/src/main/kotlin/com/example/{project}/
├── plugins/, features/, core/
```

Also create the standard docs and agency scaffolding. `docs/` has exactly five children — anything that does not fit one of them does not get a new top-level folder:

```
docs/
├── README.md             # Index: what lives where
├── artifacts/            # Agent-written, one folder per doc type (CLOSED list —
│   │                     #   see handoff-protocol.md). Folders are created on
│   │                     #   demand; filenames carry the Task ID.
│   ├── prd/  brd/  adr/  rfc/  spike/  design-spec/  api-contract/
│   ├── api-migration/  test-plan/  code-review/  security-review/
│   ├── static-analysis/  health-report/  incident-notes/  post-mortem/
│   └── release-record/  runbook/  tech-task/  retro/  replenishment/
│                        #   sprint-report/  onboarding/
├── board/                # Board archives (see board-adapter.md)
│   ├── README.md         # Index of quarter files
│   ├── backlog.md
│   ├── decisions-log.md
│   └── done-{YYYY}-Q{N}.md   # Created lazily on first completed task
├── guides/               # Hand-maintained and long-lived: setup, references,
│                         #   policies, and living registers (tech debt, SLOs,
│                         #   performance budgets, data retention)
├── assets/               # Images, GIFs, design handoff HTML/CSS
└── archive/{year}/       # Superseded documents — moved, never deleted
board-context.md          # `markdown` backend only. Live columns: Ready, In
                          #   Progress, Review, Blocked. On `github` the board is
                          #   GitHub Issues and this file does not exist.
```

The split is by **lifecycle**: `artifacts/` is written once per task by an agent and then read; `guides/` is maintained by hand over time; `board/` is appended to; `assets/` is binary; `archive/` is frozen.

## Step 6: Copy Agency Configuration (Gap-Filling)

Every copy below sources from `$PLUGIN_ROOT` / `$PAYLOAD_ROOT` as resolved in Step 0. Skip items that already exist — this step never overwrites.

### 6a. Shared Rules (the ones that live in the consumer)

These are the only rules copied into the project. Claude Code auto-loads them every session.

Copy **everything** the plugin ships under `rules/shared/`. Enumerate by glob rather than a hardcoded list — a hardcoded list silently omits any rule added to the plugin later, and because the audit above uses the same enumeration the omission would be invisible.

```bash
mkdir -p .claude/rules/shared

# Iterate with `find | while read`, NOT `for rule in $LIST`: unquoted parameter
# expansion does not word-split in zsh, so a space-separated list would run the
# body once with the entire list as $rule.
find "${PLUGIN_ROOT}/rules/shared" -maxdepth 1 -name '*.md' \
| sort | while read -r src; do
    rule="$(basename "$src")"
    dst=".claude/rules/shared/${rule}"
    if [ -f "$dst" ]; then
        echo "Skipped (exists): rules/shared/${rule}"
    else
        cp "$src" "$dst"
        echo "Copied: rules/shared/${rule}"
    fi
done

# Report the count so a truncated payload is visible rather than silent.
echo "Shared rules now in this project: $(find .claude/rules/shared -name '*.md' | grep -c .)"
```

Do not gate on a magic number — gate on the named core set, so that a rule added upstream does not read as a surplus and an optional one does not read as a gap. These ten must all be present:

```bash
MISSING=""
for rule in agent-preamble shared-standards operational-standards handoff-protocol \
            crash-investigation git-hooks board-adapter board-in-pr worktree-first \
            kotlin-agent-skills; do
    [ -f ".claude/rules/shared/${rule}.md" ] || MISSING="${MISSING} ${rule}.md"
done

if [ -n "$MISSING" ]; then
    echo "[✗] core shared rules missing:${MISSING}"
    echo "    The plugin payload is incomplete. Stop and reinstall rather than"
    echo "    proceeding with a partial rule set."
else
    echo "[✓] all 10 core shared rules present"
fi
```

The plugin may ship additional shared rules beyond these ten (`rules-delivery`, for instance). Those arrive through the glob above and need no change here — a count of 11 or more is healthy, not surplus.

The `shared/` subdirectory is part of the path, in the consumer exactly as in the plugin. Do not flatten it: every rule cross-reference in the agency is written `@.claude/rules/shared/<name>.md`, and a flat copy breaks all of them.

### 6b. Language Coding Standards — deliberately NOT copied

Do not copy `compose-coding-standards.md`, `swiftui-coding-standards.md`, `kmp-coding-standards.md`, `ktor-server-coding-standards.md`, `react-coding-standards.md`, `node-coding-standards.md`, `python-coding-standards.md`, or `jvm-coding-standards.md` into the project.

They stay in the plugin and are **read on demand** by the agent whose task is in that language:

| Stack | Read on demand from |
|---|---|
| Android / Compose | `${CLAUDE_PLUGIN_ROOT}/rules/mobile/android/compose-coding-standards.md` |
| iOS / SwiftUI | `${CLAUDE_PLUGIN_ROOT}/rules/mobile/ios/swiftui-coding-standards.md` |
| KMP shared | `${CLAUDE_PLUGIN_ROOT}/rules/mobile/shared/kmp-coding-standards.md` |
| Ktor server | `${CLAUDE_PLUGIN_ROOT}/rules/backend/kotlin/ktor-server-coding-standards.md` |
| React / Next.js | `${CLAUDE_PLUGIN_ROOT}/rules/web/react-coding-standards.md` |
| Node / Fastify | `${CLAUDE_PLUGIN_ROOT}/rules/backend/nodejs/node-coding-standards.md` |
| Python / FastAPI | `${CLAUDE_PLUGIN_ROOT}/rules/backend/python/python-coding-standards.md` |
| JVM / Spring Boot | `${CLAUDE_PLUGIN_ROOT}/rules/backend/jvm/jvm-coding-standards.md` |

Each falls back to `.claude/rules/<same path>.md` when `CLAUDE_PLUGIN_ROOT` is unset — the case when working inside the tech-agency repo itself.

If the audit found stale local copies (the `[!]` lines), tell the user to delete them: a local copy shadows the plugin's and silently goes stale.

### 6c. Skills — normally nothing to copy

An installed plugin already provides every skill as `/tech-agency:<name>`. Copying them into the project duplicates ~48 files that immediately begin drifting from the plugin, and the duplicates shadow plugin updates. **Default: copy nothing.**

Copy skills only when the user explicitly asks to vendor them (`--vendor-skills`), which is the non-plugin case: a project that wants the agency checked into its own repo with no plugin installed. Enumerate by glob so the set can never silently fall behind the plugin.

```bash
# ONLY when the user asked to vendor skills.
if [ "${VENDOR_SKILLS:-false}" = "true" ]; then
    mkdir -p .claude/skills
    find "${PLUGIN_ROOT}/skills" -mindepth 2 -maxdepth 2 -name SKILL.md -exec dirname {} \; \
    | while read -r skill_dir; do
        skill="$(basename "$skill_dir")"
        if [ -f ".claude/skills/${skill}/SKILL.md" ]; then
            echo "Skipped (exists): ${skill}"
        else
            cp -R "$skill_dir" ".claude/skills/${skill}"
            echo "Vendored: ${skill}"
        fi
    done
    # The plugin's licence notice travels with the vendored third-party skills.
    for f in LICENSE-APACHE-2.0.txt VENDORED-SKILLS.md; do
        [ -f "${PLUGIN_ROOT}/skills/${f}" ] && [ ! -f ".claude/skills/${f}" ] \
            && cp "${PLUGIN_ROOT}/skills/${f}" ".claude/skills/${f}"
    done
else
    echo "Skills served by the plugin as /tech-agency:<name> — nothing copied."
    echo "Pass --vendor-skills only if this project must work without the plugin installed."
fi
```

### 6d. CLAUDE.md (if missing)

`CLAUDE.md` is project-specific and is **not** part of the plugin payload — there is nothing to copy. Generate it.

```bash
if [ -f "CLAUDE.md" ]; then
    echo "Skipped (exists): CLAUDE.md"
else
    echo "Generating CLAUDE.md"
fi
```

Write a `CLAUDE.md` that states:
- The project name, one-line description, and the stacks detected in Step 2.
- The agent roster relevant to those stacks (drop agents whose stack this project does not use).
- Where the shared rules live (`.claude/rules/shared/`) and that they auto-load.
- Where the coding standards live (the plugin, read on demand) with the table from 6b trimmed to this project's stacks.
- The commit format: `[STORY-ID] @Agent: description`, where the agent tag is optional. The hook accepts `[T-015] @Claude: …`, `[TECH] @Claude: …`, `[tech] …`, and `[US-042] @Kai: …` — canonical regex `^\[[A-Za-z]+(-[0-9]+)?\][[:space:]]+(@[A-Za-z]+:[[:space:]]+)?.{3,}`.
- A pointer to the board — `gh issue list` on the `github` backend, `board-context.md` on `markdown` — and to `/tech-agency:daily-sync`. Name the configured `board_backend` explicitly so an agent never has to guess.

Present it to the user for review — it is the one file they will edit most.

### 6e. Board (if missing)

**First pick the backend** and write it to `.claude/settings.json`. This is the single most
consequential setup choice for the board, and leaving it unset makes every board-touching skill
guess (see `@.claude/rules/shared/board-adapter.md`):

| `GITHUB_REMOTE` from Step 1 | `board_backend` | What gets scaffolded |
|---|---|---|
| `true` | `"github"` **(default)** | Labels only. No `board-context.md`. |
| `false` | `"markdown"` | `board-context.md` + `docs/board/` as below |

```json
// .claude/settings.json
{ "board_backend": "github" }
```

**On `github`**, create the status labels and stop — there is no board file:

```bash
for l in "status:backlog:ededed" "status:ready:0e8a16" "status:in-progress:1d76db" \
         "status:review:fbca04" "status:blocked:d93f0b" \
         "priority:P0:b60205" "priority:P1:d93f0b" "priority:P2:fbca04" "priority:P3:c2e0c6" \
         "tech-debt:5319e7"; do
  gh label create "${l%:*}" --color "${l##*:}" --force
done
```

There is no `status:done` label by design — Done is the issue being closed, which is what lets
`Closes #N` in a PR body perform the transition. A Projects v2 board is optional and needs a
`project` token scope; `/migrate-board` Step 6 creates one when that scope is present.

`docs/board/decisions-log.md` is still created on **both** backends — it is a versioned document,
not tracked work.

**An existing repo that already has a markdown board** is not converted here. Say that
`/migrate-board` performs that migration — it repairs, dry-runs, never deletes, and is safe to
re-run — and leave `board_backend` as `"markdown"` until the user runs it.

**On `markdown`**, `board-context.md` is project state, not plugin payload. Generate an empty board
with the canonical column schema:

```bash
if [ -f "board-context.md" ]; then
    echo "Skipped (exists): board-context.md"
else
    echo "Generating board-context.md"
fi

mkdir -p docs/board
for f in backlog.md decisions-log.md README.md; do
    if [ ! -f "docs/board/$f" ]; then
        cp "{project-template}/docs/board/$f" "docs/board/$f"
        echo "Copied docs/board/$f"
    fi
done
# Quarter files (done-YYYY-QN.md) are created lazily by the first completed task.
```

```markdown
# Kanban Board Context

## Backlog

| Task ID | Priority | Description | Requested By |
|---------|----------|-------------|--------------|
| — | — | — | — |

## Ready

| Task ID | Priority | Description | Assigned To |
|---------|----------|-------------|-------------|
| — | — | — | — |

## In Progress (WIP limit: 2 per agent)

| Task ID | Agent | Description | Started | Cycle Day |
|---------|-------|-------------|---------|-----------|
| — | — | — | — | — |

## Review

| Task ID | Agent | Description | Reviewer | Waiting Since |
|---------|-------|-------------|----------|---------------|
| — | — | — | — | — |

## Blocked

| Task ID | Agent | Blocker | Waiting On | Blocked Since |
|---------|-------|---------|------------|---------------|
| — | — | — | — | — |

## Done (recent)

| Task ID | Agent | Description | Output | Completed |
|---------|-------|-------------|--------|-----------|
| — | — | — | — | — |

## Decisions Log

| Date | Decision | Decided By | ADR Ref |
|------|----------|------------|---------|
| — | — | — | — |
```

These column headers are the contract every board-touching skill writes against. Do not vary them.

### 6f. Reference Docs (if missing)

```bash
mkdir -p docs/guides/references

if [ "$PAYLOAD_HAS_DOCS" = "true" ]; then
    for doc in setup-guide migration-guide ci-enforcement-policy incident-response; do
        if [ -f "docs/${doc}.md" ]; then
            echo "Skipped (exists): docs/${doc}.md"
        elif [ -f "${PAYLOAD_ROOT}/docs/${doc}.md" ]; then
            cp "${PAYLOAD_ROOT}/docs/${doc}.md" "docs/${doc}.md"
            echo "Copied: docs/${doc}.md"
        fi
    done

    # Platform reference docs — copy only those matching the detected stacks:
    #   KMP     -> kmp-testing-reference.md, kmp-observability-reference.md
    #   Android -> compose-testing-reference.md, compose-observability-reference.md
    #   iOS     -> swiftui-testing-reference.md, swiftui-observability-reference.md
    #
    # SELECTED_REFERENCES is NEWLINE-separated and iterated via `printf | while
    # read`, not `for ref in $SELECTED_REFERENCES` — unquoted expansion does not
    # word-split in zsh, which would make the loop run once on the whole list.
    printf '%s\n' "$SELECTED_REFERENCES" | grep -v '^$' | while read -r ref; do
        if [ ! -f "docs/guides/references/${ref}" ] && [ -f "${PAYLOAD_ROOT}/docs/guides/references/${ref}" ]; then
            cp "${PAYLOAD_ROOT}/docs/guides/references/${ref}" "docs/guides/references/${ref}"
            echo "Copied: docs/guides/references/${ref}"
        fi
    done
else
    echo "Plugin install ships only the .claude/ subtree — reference docs unavailable."
    echo "Read them at https://github.com/Zeyad-37/tech-agency/tree/main/docs"
fi
```

Set `SELECTED_REFERENCES` from the platforms confirmed in Step 2 before running this block, one filename per line:

```bash
SELECTED_REFERENCES="kmp-testing-reference.md
kmp-observability-reference.md
compose-testing-reference.md
compose-observability-reference.md"
```

### 6g. Settings & Hooks Config

```bash
mkdir -p .claude

if [ ! -f ".claude/settings.json" ]; then
    cp "${PLUGIN_ROOT}/settings.json" .claude/settings.json
    echo "Copied settings.json from the plugin"
elif ! jq -e 'has("sandbox")' .claude/settings.json >/dev/null 2>&1; then
    # Existing project with its own settings — merge in ONLY the sandbox block.
    # Never overwrite the whole file; the project's own keys must survive.
    jq --slurpfile tpl "${PLUGIN_ROOT}/settings.json" '. + {sandbox: $tpl[0].sandbox}' \
        .claude/settings.json > .claude/settings.json.tmp \
        && mv .claude/settings.json.tmp .claude/settings.json
    echo "Merged sandbox block into the existing settings.json"
else
    echo "settings.json already has a sandbox block"
fi

if [ ! -f ".claude/hooks.json" ] && [ -f "${PLUGIN_ROOT}/hooks.json" ]; then
    cp "${PLUGIN_ROOT}/hooks.json" .claude/hooks.json
    echo "Copied hooks.json from the plugin"
fi
```

### 6h. Normalize the Sandbox for THIS Repo (runs unconditionally)

The plugin's `settings.json` hardcodes `"../tech-agency-worktrees"` as an allowed write path. Copied verbatim into a consumer, that path is wrong for every project except tech-agency itself — and `worktree-first.md` makes creating `../{repo}-worktrees/…` **Step 0 of every task**. A consumer that inherits the wrong path has its sandbox deny the first write of every task the agency performs.

So this normalization runs **after 6g on every path** — fresh copy, merged block, and re-run alike. It is idempotent.

```bash
REPO="$(basename "$(git rev-parse --show-toplevel)")"
WT="../${REPO}-worktrees"

jq --arg wt "$WT" '
  def dedupe: reduce .[] as $x ([]; if index($x) then . else . + [$x] end);

  # Point the worktree write path at THIS repo. Rewrites any existing
  # "*-worktrees" entry (including the template default) and appends if absent.
  .sandbox.filesystem.allowWrite =
      ((((.sandbox.filesystem.allowWrite // [])
         | map(if test("-worktrees$") then $wt else . end)) + [$wt]) | dedupe)

  # `git worktree add` writes into the main checkout .git dir and the sibling
  # worktrees tree. Exclude it so worktree creation is never sandbox-blocked.
| .sandbox.excludedCommands =
      ((((.sandbox.excludedCommands // []) + ["git worktree *"])) | dedupe)
' .claude/settings.json > .claude/settings.json.tmp \
  && mv .claude/settings.json.tmp .claude/settings.json

echo "Sandbox normalized: worktree write path = ${WT}, git worktree excluded"

# Verify — do not report success without checking.
jq -e --arg wt "$WT" '(.sandbox.filesystem.allowWrite | index($wt)) and
                      (.sandbox.excludedCommands | index("git worktree *"))' \
    .claude/settings.json >/dev/null \
    && echo "[✓] sandbox verified" \
    || echo "[✗] SANDBOX NORMALIZATION FAILED — worktree-first will be blocked"
```

If `jq` is not installed, stop and tell the user to install it (`brew install jq` / `apt install jq`) rather than hand-editing — a malformed `settings.json` disables the whole configuration silently.

Notes:
- The sandbox auto-allows sandboxed Bash (no extra prompts), so it does not slow agents down.
- `excludedCommands` keeps VCS network ops (`git push/fetch/pull`, `gh`) unsandboxed so SSH/auth work, plus `git worktree *` per above.
- Linux/WSL2 runners must have `bubblewrap` + `socat` installed, or `failIfUnavailable: true`
  will refuse to start. macOS uses built-in Seatbelt (nothing to install).
- If a project's builds need extra hosts or write paths, extend `sandbox.network.allowedDomains`
  / `sandbox.filesystem.allowWrite` rather than disabling the sandbox.

### 6i. Declare the Plugin for Cloud Sessions (runs unconditionally)

This is the step that makes the agency available in a **cloud** Claude Code session, not just on the developer's laptop.

Cloud sessions have **no `/plugin` command** — commands that only run in the terminal interface, such as `/plugin` or `/resume`, are not available there. The documented way to change what a cloud session loads is to *commit settings files to the repository* (or set environment variables). For plugins specifically, that means declaring the marketplace and the enabled plugin in the project's own `.claude/settings.json`, which is exactly what this step writes:

```json
{
  "extraKnownMarketplaces": {
    "tech-agency": { "source": { "source": "github", "repo": "Zeyad-37/tech-agency" } }
  },
  "enabledPlugins": { "tech-agency@tech-agency": true }
}
```

Once a team member trusts the repository folder, Claude Code adds the declared marketplace without a further prompt — this is the supported "team marketplace" path, and it works for any teammate who clones the repo, not only the person who ran this skill.

The merge below is **additive and idempotent**: it preserves every other top-level key, every other marketplace, and every other enabled plugin, and a second run makes no change at all. It refuses to write when the file is not valid JSON, or when either key holds something other than an object — silently rewriting a settings file the user hand-edited is worse than stopping.

```bash
SETTINGS=".claude/settings.json"
mkdir -p .claude

if [ ! -f "$SETTINGS" ]; then
    printf '{}\n' > "$SETTINGS"
    echo "Created $SETTINGS (did not exist)"
fi

# Never overwrite a file we cannot parse — a malformed settings.json is the
# user's edit in progress, not ours to discard.
if ! jq -e . "$SETTINGS" >/dev/null 2>&1; then
    echo "[✗] $SETTINGS is not valid JSON — refusing to touch it."
    echo "    Fix the syntax by hand, then re-run. Nothing was written."
    exit 1
fi

# Guard the two keys we merge into: a string or array there would make the
# assignment below fail mid-write.
BAD="$(jq -r '
  if type != "object" then "<root>"
  else
    [ (if has("extraKnownMarketplaces") and (.extraKnownMarketplaces != null)
          and (.extraKnownMarketplaces | type) != "object"
        then "extraKnownMarketplaces" else empty end),
      (if has("enabledPlugins") and (.enabledPlugins != null)
          and (.enabledPlugins | type) != "object"
        then "enabledPlugins" else empty end) ] | join(", ")
  end' "$SETTINGS")"

if [ -n "$BAD" ]; then
    echo "[✗] $SETTINGS has a non-object where an object is required: ${BAD}"
    echo "    Refusing to merge. Fix it by hand, then re-run. Nothing was written."
    exit 1
fi

# Additive merge: `(existing // {}) + {new}` keeps every sibling entry and
# overwrites only our own key, so re-running is a no-op.
jq '
  .extraKnownMarketplaces = ((.extraKnownMarketplaces // {}) + {
      "tech-agency": { "source": { "source": "github", "repo": "Zeyad-37/tech-agency" } }
  })
| .enabledPlugins = ((.enabledPlugins // {}) + {
      "tech-agency@tech-agency": true
  })
' "$SETTINGS" > "${SETTINGS}.tmp" || {
    rm -f "${SETTINGS}.tmp"
    echo "[✗] jq merge failed — $SETTINGS left untouched."
    exit 1
}

# Only move the temp file into place when something actually changed, so a
# re-run leaves the file byte-identical instead of churning its mtime.
if cmp -s "$SETTINGS" "${SETTINGS}.tmp"; then
    rm -f "${SETTINGS}.tmp"
    echo "[=] tech-agency already declared in $SETTINGS — no change"
else
    mv "${SETTINGS}.tmp" "$SETTINGS"
    echo "[+] Declared tech-agency marketplace + plugin in $SETTINGS"
fi

# Verify — do not report success without checking.
jq -e '
  (.extraKnownMarketplaces["tech-agency"].source.repo == "Zeyad-37/tech-agency")
  and (.enabledPlugins["tech-agency@tech-agency"] == true)
' "$SETTINGS" >/dev/null \
  && echo "[✓] cloud-session plugin declaration verified" \
  || echo "[✗] declaration missing after merge — inspect $SETTINGS by hand"
```

Note on formatting: the first run rewrites the file through `jq`, so a hand-formatted `settings.json` gets normalized to jq's two-space output once. Every run after that is byte-stable, which is what the `cmp` guard above checks.

#### Tell the user the honest caveat

Do **not** report this step as "the plugin now loads everywhere." Include this in the final report, verbatim in substance:

> Declaring the plugin in `.claude/settings.json` registers the marketplace and records the intent to enable the plugin. As of Claude Code v2.1.195, adding a marketplace this way does **not** by itself install a plugin that comes from an external source such as a GitHub repository. Until someone installs it, Claude Code reports the plugin as not installed and prints the install command to run:
>
> ```bash
> claude plugin install tech-agency@tech-agency
> ```

Two supported ways to close that first-install gap without a human typing that command in a cloud session — pick one and tell the user which applies to them:

1. **Cloud environment setup script** (claude.ai → cloud environments). Add the install to the environment's setup script so every cloud session starts with the plugin present:

   ```bash
   claude plugin install tech-agency@tech-agency --scope user
   ```

2. **Plugin seed directory.** Point `CLAUDE_CODE_PLUGIN_SEED_DIR` at a pre-populated, read-only copy of `~/.claude/plugins` — mirroring `known_marketplaces.json`, `marketplaces/<name>/`, and `cache/<marketplace>/<plugin>/<version>/`. It needs no network access, and it composes with the settings written above: when `extraKnownMarketplaces` or `enabledPlugins` declares a marketplace that already exists in the seed, Claude Code uses the seed copy instead of cloning.

Because `Zeyad-37/tech-agency` is a **public** repository, the marketplace clone needs no git credentials in the cloud environment. A private marketplace repo would additionally require a credential helper or a token URL rewrite configured in that environment.

The README's cloud-availability section is the fuller write-up — point the user at it rather than re-deriving the options here.

#### The zero-plugin fallback

If a project cannot use the plugin machinery at all (no install step available, no seed directory), Claude Code still auto-loads these straight out of the repo with no plugin involved:

- `.claude/skills/*/SKILL.md`
- `.claude/agents/*.md` — subagents defined in a repo's `.claude/agents/` are picked up automatically in cloud sessions
- `.claude/rules/**/*.md` (recursive)
- `CLAUDE.md`
- `.claude/settings.json`

That is the case `--vendor-skills` (Step 6c) exists for: vendoring the skills into the repo makes them load with zero auth and zero plugin machinery, at the cost of duplicating files that then drift from the plugin. Offer it only when the install paths above are genuinely unavailable.

Be precise about what that flag covers: `--vendor-skills` copies **skills only**, and this skill has no agent-vendoring step at all. A project that also needs the 19-agent roster resident with no plugin installed must copy `${PLUGIN_ROOT}/agents/*.md` into `.claude/agents/` itself, as a deliberate separate act, and then owns keeping those copies in sync with the plugin. Say that plainly rather than implying `--vendor-skills` already handled it.

Note that the plugin's **`rules/` directory is not one of the directories a plugin loads** — that is why the agency reads its coding standards on demand from `${CLAUDE_PLUGIN_ROOT}/rules/…` (Step 6b) rather than expecting them to auto-load. Vendoring copies rules into `.claude/rules/`, where the *project* rule loader picks them up; that is a different mechanism, not the plugin loader.

## Step 7: Install Git Hooks (Gap-Filling)

```bash
# Copy hook scripts if missing. They live at the payload root, not inside .claude/.
if [ -d "hooks" ]; then
    echo "Skipped (exists): hooks/"
elif [ "$PAYLOAD_HAS_HOOKS" = "true" ]; then
    cp -R "${PAYLOAD_ROOT}/hooks" ./hooks
    chmod +x hooks/pre-commit hooks/commit-msg hooks/pre-push hooks/install-hooks.sh 2>/dev/null
    echo "Copied hooks/ from the plugin payload"
else
    echo "Plugin install ships only the .claude/ subtree — hook scripts unavailable."
    echo "Fetch them from https://github.com/Zeyad-37/tech-agency/tree/main/hooks"
    echo "or skip hooks and rely on the CI quality gates from Step 8."
fi

# Install hooks if not already symlinked
if [ -d "hooks" ] && [ ! -L ".git/hooks/pre-commit" ]; then
    chmod +x hooks/install-hooks.sh
    ./hooks/install-hooks.sh
    echo "Git hooks installed"
else
    echo "Git hooks already installed (or hooks/ unavailable)"
fi
```

This installs three hooks:
- **pre-commit**: Secrets detection, force-unwrap checks, lint/format, large file detection
- **commit-msg**: Validates the commit message format
- **pre-push**: Branch naming, commit format, test suite, build verification

The accepted commit message format is `[STORY-ID] @Agent: description`, where the agent tag is **optional**. Canonical regex:

```
^\[[A-Za-z]+(-[0-9]+)?\][[:space:]]+(@[A-Za-z]+:[[:space:]]+)?.{3,}
```

It accepts `[T-015] @Claude: …`, `[TECH] @Claude: …`, `[tech] …`, and `[US-042] @Kai: …`.

See `@.claude/rules/shared/git-hooks.md` for full details on what each hook enforces.

## Step 7b: Android/Kotlin Agent Toolchain (Android / KMP projects only)

Skip this step unless the project targets Android or KMP. The agency ships a curated set of **Android & Kotlin Agent Skills** vendored under `.claude/skills/` (`android-*` and `kotlin-*` — see `.claude/skills/VENDORED-SKILLS.md`), and the mobile/kotlin rule files wire them into Kai, Link, Forge, and Sentinel. The skill *files* ship with the plugin and need no install. What does need installing is the underlying `android` CLI so agents can actually run `android docs`, `android run`, `android emulator`, etc.

```bash
# Is the android CLI already available?
command -v android && android --version && echo "ANDROID_CLI=present" || echo "ANDROID_CLI=missing"
```

If missing, tell the user how to install it (do not silently download binaries):

1. Download the `android` CLI from https://developer.android.com/tools/agents (a.k.a. `/tools/agents/android-cli`).
2. `android update` — pull the latest version.
3. (Optional) `android init` — installs Android's own `android-cli` skill for your default agent. The agency already vendors `android-cli`, so this is only needed if you want Android's canonical copy at the user level too.
4. (Optional) `android skills add --all --project=.` to drop the full upstream Android skill set into *this* project's `.claude/skills/` — only if you want skills beyond the curated vendored set.

For the **Kotlin agent skills**, the agency vendors a pinned subset. If the user wants the always-latest JetBrains set instead of the pin:

```bash
claude plugin marketplace add Kotlin/kotlin-agent-skills
claude plugin install kotlin-agent-skills@Kotlin
```

> Note: the `npx skills add Kotlin/kotlin-agent-skills` route requires Node.js. If Node isn't installed, use the `claude plugin marketplace` route or the vendored pin — no Node needed.

For **CI runners** (Sentinel): document `android sdk install <packages>` + `android emulator create/start` + `android run` in the relevant `.github/workflows/*.yml` so Android builds/tests are reproducible without a full Android Studio install. Add `Bash(android *)` to `.claude/settings.json` `permissions.allow` (via `/update-config`) to avoid per-call prompts.

## Step 8: GitHub Actions — CI/CD Pipelines (Gap-Filling)

Check which workflows are missing and create only those.

```bash
mkdir -p .github/workflows

for workflow in pr-checks verify-main release hotfix; do
    if [ ! -f ".github/workflows/${workflow}.yml" ]; then
        echo "Creating: .github/workflows/${workflow}.yml"
        # Create the workflow file (see below)
    else
        echo "Skipped (exists): .github/workflows/${workflow}.yml"
    fi
done
```

For **existing projects with existing CI**: do NOT overwrite their workflows. Instead, review the existing workflows and suggest additions:
- Missing lint step → suggest adding
- Missing security scan → suggest adding
- Missing coverage gate → suggest adding
- Missing release workflow → suggest adding

For **new projects or projects with no CI**, create all four workflows:

### 8a. PR Quality Gates (`pr-checks.yml`)

Triggered on: pull request to `main`

```yaml
name: PR Quality Gates

on:
  pull_request:
    branches: [main]

concurrency:
  group: pr-${{ github.event.pull_request.number }}
  cancel-in-progress: true

jobs:
  lint:
    name: Lint & Format
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      # TODO: Add your lint/format steps
      # Examples:
      #   - run: ./gradlew detekt (Kotlin)
      #   - run: npm run lint (Node/React)
      #   - run: ruff check . (Python)
      #   - run: swiftlint (iOS)

  test:
    name: Unit & Integration Tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      # TODO: Add your test steps

  security:
    name: Security Scan
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      # TODO: Add your security scan steps

  build:
    name: Build
    runs-on: ubuntu-latest
    needs: [lint, test, security]
    steps:
      - uses: actions/checkout@v4
      # TODO: Add your build steps
```

### 8b. Verify Main (`verify-main.yml`)

Triggered on: push to `main`

```yaml
name: Verify Main

on:
  push:
    branches: [main]

jobs:
  verify:
    name: Full Test Suite
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      # TODO: Run full test suite

  build-artifacts:
    name: Build Release Artifacts
    runs-on: ubuntu-latest
    needs: [verify]
    steps:
      - uses: actions/checkout@v4
      # TODO: Build deployable artifacts

  notify:
    name: Notify Team
    runs-on: ubuntu-latest
    needs: [verify]
    if: failure()
    steps:
      - run: echo "Main branch verification failed — investigate immediately"
```

### 8c. Release Flow (`release.yml`)

Triggered on: tag push matching `v*.*.*`

```yaml
name: Release

on:
  push:
    tags:
      - 'v*.*.*'

permissions:
  contents: write

jobs:
  validate-tag:
    name: Validate Release Tag
    runs-on: ubuntu-latest
    outputs:
      version: ${{ steps.version.outputs.version }}
    steps:
      - uses: actions/checkout@v4
      - id: version
        run: echo "version=${GITHUB_REF_NAME#v}" >> "$GITHUB_OUTPUT"
      - name: Verify tag is on main
        run: |
          git fetch origin main
          if ! git merge-base --is-ancestor ${{ github.sha }} origin/main; then
            echo "ERROR: Release tag must be on the main branch"
            exit 1
          fi

  test:
    name: Full Test Suite
    runs-on: ubuntu-latest
    needs: [validate-tag]
    steps:
      - uses: actions/checkout@v4
      # TODO: Run full test suite

  security-audit:
    name: Security Audit
    runs-on: ubuntu-latest
    needs: [validate-tag]
    steps:
      - uses: actions/checkout@v4
      # TODO: Run comprehensive security scan

  build-and-publish:
    name: Build & Publish
    runs-on: ubuntu-latest
    needs: [test, security-audit]
    steps:
      - uses: actions/checkout@v4
      # TODO: Build and publish release artifacts

  create-github-release:
    name: Create GitHub Release
    runs-on: ubuntu-latest
    needs: [build-and-publish]
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - name: Generate changelog
        id: changelog
        run: |
          PREV_TAG=$(git describe --tags --abbrev=0 HEAD^ 2>/dev/null || echo "")
          if [ -z "$PREV_TAG" ]; then
            CHANGELOG=$(git log --oneline --pretty=format:"- %s" HEAD)
          else
            CHANGELOG=$(git log --oneline --pretty=format:"- %s" ${PREV_TAG}..HEAD)
          fi
          echo "changelog<<EOF" >> "$GITHUB_OUTPUT"
          echo "$CHANGELOG" >> "$GITHUB_OUTPUT"
          echo "EOF" >> "$GITHUB_OUTPUT"
      - uses: softprops/action-gh-release@v2
        with:
          tag_name: ${{ github.ref_name }}
          name: Release ${{ github.ref_name }}
          body: |
            ## What's Changed
            ${{ steps.changelog.outputs.changelog }}
          draft: false
          prerelease: false

  deploy:
    name: Deploy
    runs-on: ubuntu-latest
    needs: [create-github-release]
    steps:
      - run: echo "Deploy release ${{ github.ref_name }}"
```

### 8d. Hotfix Flow (`hotfix.yml`)

Triggered on: push to `hotfix/**` branches

```yaml
name: Hotfix

on:
  push:
    branches:
      - 'hotfix/**'
  pull_request:
    branches: [main]
    paths-ignore: []

jobs:
  validate-hotfix:
    name: Validate Hotfix Branch
    runs-on: ubuntu-latest
    if: startsWith(github.head_ref || github.ref_name, 'hotfix/')
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - name: Verify hotfix branch naming
        run: |
          BRANCH_NAME="${{ github.head_ref || github.ref_name }}"
          echo "Hotfix branch: $BRANCH_NAME"
          VERSION=$(echo "$BRANCH_NAME" | grep -oP 'v\d+\.\d+\.\d+' || true)
          if [ -z "$VERSION" ]; then
            echo "WARNING: Hotfix branch should follow naming: hotfix/vX.Y.Z/description"
          fi

  test-focused:
    name: Focused Regression Tests
    runs-on: ubuntu-latest
    needs: [validate-hotfix]
    steps:
      - uses: actions/checkout@v4
      # TODO: Run focused test suite

  security-quick:
    name: Quick Security Check
    runs-on: ubuntu-latest
    needs: [validate-hotfix]
    steps:
      - uses: actions/checkout@v4
      # TODO: Run quick security check

  build:
    name: Build Hotfix
    runs-on: ubuntu-latest
    needs: [test-focused, security-quick]
    steps:
      - uses: actions/checkout@v4
      # TODO: Build hotfix artifacts
```

## Step 9: Branch Protection (Optional)

If the user opted for branch protection and it's not already configured:

```bash
gh api repos/{owner}/{repo}/branches/main/protection \
  --method PUT \
  --field required_status_checks='{"strict":true,"contexts":["Lint & Format","Unit & Integration Tests","Security Scan","Build"]}' \
  --field enforce_admins=true \
  --field required_pull_request_reviews='{"required_approving_review_count":1,"dismiss_stale_reviews":true}' \
  --field restrictions=null
```

For existing projects with existing branch protection, do NOT overwrite. Instead, suggest additions to the existing rules.

## Step 10: Initial Commit (New Projects Only)

Skip for existing projects — they already have commit history.

```bash
cd {project-name}

git add -A
git commit -m "Initial project scaffold

- Project structure per coding standards
- GitHub Actions: PR checks, verify main, release, hotfix
- Agency configuration (.claude/ rules, skills, hooks)
- Branch protection on main

Co-Authored-By: Sentinel <sentinel@tech-agency>"

# Do NOT push yet — present the initial commit to @Zeyad for approval
# When @Zeyad says "push", then:
# git push -u origin main
```

> **No Auto-Push:** Do not push to remote until @Zeyad explicitly approves. Present the setup summary and wait for confirmation.

## Step 11: Create GitHub Repository (New Projects Only)

```bash
gh repo create {org-or-user}/{project-name} --{visibility} --source=. --push
```

## Step 12: Post-Setup Report

Present the final report to the user. The format differs based on mode.

### For New Projects:

```
Repository Setup Complete: {project-name}

Platforms: [list selected]
GitHub: https://github.com/{org}/{project-name}

Created:
- [x] Git repo initialized with main branch
- [x] Project structure per coding standards
- [x] .claude/rules/shared/ — {n} shared rules (auto-load every session)
- [x] .claude/settings.json — sandbox normalized to ../{project-name}-worktrees
- [x] .claude/settings.json — tech-agency marketplace + plugin declared (cloud sessions)
- [x] CLAUDE.md with roster and workflow
- [x] GitHub Actions: PR quality gates
- [x] GitHub Actions: Verify main
- [x] GitHub Actions: Release flow (tag-based)
- [x] GitHub Actions: Hotfix flow
- [x] Branch protection on main
- [x] Git hooks installed (pre-commit, commit-msg, pre-push)
- [x] .gitignore for all platforms

TODOs (manual — fill in your tooling):
- [ ] Fill in TODO placeholders in .github/workflows/ with your specific build/test/deploy commands
- [ ] Add secrets to GitHub repo settings (API keys, deploy tokens, etc.)
- [ ] Configure deployment targets in release.yml (staging, canary, production)
- [ ] Configure notification channels in verify-main.yml (Slack, email, etc.)
- [ ] Update performance budgets in docs/guides/performance-budgets.md
- [ ] Define SLOs per service in docs/guides/slo/
- [ ] Run /tech-agency:new-product to kick off the product planning chain

Where things live:
- Shared rules ({n}) — .claude/rules/shared/ in THIS repo. Auto-loaded every session.
- Coding standards (8) — stay in the plugin, read on demand by the agent working
  in that language. Your project has 10-11 rule files, not 18, and that is correct:
  auto-loading all eight standards would cost ~65k context tokens per session,
  most of it for stacks you do not use.
- Skills ({n from the audit}) — served by the plugin as /tech-agency:<name>. Nothing was copied.

Cloud sessions:
- .claude/settings.json now declares the tech-agency marketplace and enables
  tech-agency@tech-agency. Commit it — that declaration is the only lever a cloud
  session has, because /plugin does not exist there.
- First install may still be needed: as of Claude Code v2.1.195, declaring an
  external-source plugin registers the marketplace but does not install the plugin.
  Until it is installed, Claude Code reports it as not installed and prints:
      claude plugin install tech-agency@tech-agency
  Close that gap with a cloud environment setup script (running the command above
  with --scope user) or a CLAUDE_CODE_PLUGIN_SEED_DIR seed. See the README's
  cloud-availability section.
```

### For Existing Projects:

```
Agency Setup Report: {project-name}

Mode: Existing project — gap-filling

Items already in place (skipped):
- [✓] {list items that were already present}

Newly added:
- [+] {list items that were just set up}

Still needs attention:
- [ ] Customize CLAUDE.md for your project specifics
- [ ] Fill in TODO placeholders in any new workflow files
- [ ] Review git hook settings — adjust lint commands for your tooling
- [ ] Delete any stale local coding-standards copies flagged [!] in the audit
- [ ] See docs/guides/migration-guide.md for the full incremental adoption path

Where things live:
- Shared rules ({n}) — .claude/rules/shared/ in THIS repo. Auto-loaded every session.
- Coding standards (8) — stay in the plugin, read on demand by the agent working in
  that language. 10-11 rule files here rather than 18 is correct, not a broken install.
- Skills ({n from the audit}) — served by the plugin as /tech-agency:<name>. Nothing was copied.

Cloud sessions:
- .claude/settings.json now declares the tech-agency marketplace and enables
  tech-agency@tech-agency. Commit it — that declaration is the only lever a cloud
  session has, because /plugin does not exist there.
- First install may still be needed: as of Claude Code v2.1.195, declaring an
  external-source plugin registers the marketplace but does not install the plugin.
  Until it is installed, Claude Code reports it as not installed and prints:
      claude plugin install tech-agency@tech-agency
  Close that gap with a cloud environment setup script (running the command above
  with --scope user) or a CLAUDE_CODE_PLUGIN_SEED_DIR seed. See the README's
  cloud-availability section.

Recommended next steps:
1. Run /tech-agency:daily-sync to initialize the board status
2. Start using commit format: [STORY-ID] @Agent: description
   (agent tag optional — [TECH] Fix the thing is also valid)
3. Follow docs/guides/migration-guide.md phases for gradual adoption
```

## Customization Notes

- All GitHub Actions are **tool-agnostic** — they have TODO placeholders where the user fills in their specific tooling (Gradle, npm, pytest, Docker, etc.)
- The workflows follow the patterns defined in `@.claude/rules/shared/shared-standards.md` (branch strategy, commit policy) and `@.claude/rules/shared/operational-standards.md` (release process, hotfix process)
- CI thresholds align with the testing and observability standards already defined in each coding standards file
- The release flow matches the `/release` skill's gate sequence: test -> security -> build -> deploy
- The hotfix flow matches the `/hotfix` skill's expedited process: focused tests, quick security, fast deploy
- For existing projects with existing CI, the skill **never overwrites** — it only suggests additions
