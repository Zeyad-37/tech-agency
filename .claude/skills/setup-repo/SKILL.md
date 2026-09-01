---
name: setup-repo
description: "Set up a repository with the Tech Agency configuration — works for both new and existing projects. Detects what's already in place and only sets up the missing parts. Use when the user says 'setup repo', 'new repo', 'scaffold project', 'create a new project', 'initialize repo', 'bootstrap repo', 'add agency to project', 'integrate agency', or describes wanting to configure a codebase with the Tech Agency system."
---

# Setup Repository

You are Sentinel (DevOps/SRE) coordinating with Sage (Solutions Architect). This skill sets up a repository with the full Tech Agency system — project structure, coding standards, CI/CD pipelines, and git hooks.

**It works for both new and existing projects.** It detects what's already in place and only sets up what's missing.

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
test -f board-context.md && echo "[✓] board-context.md exists" || echo "[✗] board-context.md missing"

# 4. Rules
echo "--- Rules ---"
for rule in agent-preamble shared-standards operational-standards handoff-protocol crash-investigation git-hooks board-adapter board-in-pr worktree-first; do
    test -f ".claude/rules/${rule}.md" && echo "[✓] ${rule}.md" || echo "[✗] ${rule}.md missing"
done

# Platform-specific rules (check only for detected platforms)
echo "--- Platform Coding Standards ---"
for std in compose-coding-standards swiftui-coding-standards kmp-coding-standards ktor-server-coding-standards react-coding-standards node-coding-standards python-coding-standards jvm-coding-standards; do
    test -f ".claude/rules/${std}.md" && echo "[✓] ${std}.md" || echo "[○] ${std}.md (not present — may not be needed)"
done

# 5. Skills
echo "--- Skills ---"
for skill in daily-sync replenish retro new-product new-feature release hotfix investigate-crash investigate-bug pick-up-task kick-off code-review health-check onboard-agent dependency-upgrade rfc sprint-report tech-task dispatch update-board create-pr capture-screenshots postmortem setup-repo; do
    test -f ".claude/skills/${skill}/SKILL.md" && echo "[✓] ${skill}" || echo "[✗] ${skill} missing"
done

# 6. Hooks
echo "--- Git Hooks ---"
test -f hooks/pre-commit && echo "[✓] hooks/pre-commit" || echo "[✗] hooks/pre-commit missing"
test -f hooks/commit-msg && echo "[✓] hooks/commit-msg" || echo "[✗] hooks/commit-msg missing"
test -f hooks/pre-push && echo "[✓] hooks/pre-push" || echo "[✗] hooks/pre-push missing"
test -f hooks/install-hooks.sh && echo "[✓] hooks/install-hooks.sh" || echo "[✗] hooks/install-hooks.sh missing"
test -L .git/hooks/pre-commit && echo "[✓] hooks installed (symlinked)" || echo "[✗] hooks not installed"

# 7. CI/CD
echo "--- CI/CD Workflows ---"
test -f .github/workflows/pr-checks.yml && echo "[✓] PR quality gates" || echo "[✗] PR quality gates missing"
test -f .github/workflows/verify-main.yml && echo "[✓] Verify main" || echo "[✗] Verify main missing"
test -f .github/workflows/release.yml && echo "[✓] Release flow" || echo "[✗] Release flow missing"
test -f .github/workflows/hotfix.yml && echo "[✓] Hotfix flow" || echo "[✗] Hotfix flow missing"

# 8. Docs
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
Follow `@.claude/rules/kmp-coding-standards.md` — Project Structure section:
```
project/
├── build-logic/plugins/
├── core/architecture/, core/database/, core/network/, core/test-base/, core/time/
├── features/{feature}/domain/, data/, sharedPresentation/
├── gradle/libs.versions.toml
```

### Android (if selected)
Follow `@.claude/rules/compose-coding-standards.md` — Project Structure section:
```
androidApp/src/main/kotlin/com/example/{project}/
├── navigation/, features/, core/, designsystem/, shared/
```

### iOS (if selected)
Follow `@.claude/rules/swiftui-coding-standards.md` — Project Structure section:
```
App/
├── App/, Features/, Core/, DesignSystem/, Resources/, Shared/KMP/
```

### React/Next.js (if selected)
Follow `@.claude/rules/react-coding-standards.md` — Project Structure section:
```
src/
├── app/, components/ui/, components/features/, hooks/, lib/, stores/, styles/, types/
```

### Node.js/Fastify (if selected)
Follow `@.claude/rules/node-coding-standards.md` — Project Structure section:
```
src/
├── config/, modules/, shared/, workers/, prisma/
```

### Python/FastAPI (if selected)
Follow `@.claude/rules/python-coding-standards.md` — Project Structure section:
```
src/
├── config/, modules/, shared/, workers/, alembic/
```

### JVM/Spring Boot (if selected)
Follow `@.claude/rules/jvm-coding-standards.md` — Project Structure section:
```
src/main/kotlin/com/example/{project}/
├── config/, modules/, shared/
src/main/resources/db/migration/
```

### Ktor Server (if selected)
Follow `@.claude/rules/ktor-server-coding-standards.md` — Project Structure section:
```
server/src/main/kotlin/com/example/{project}/
├── plugins/, features/, core/
```

Also create the standard docs and agency scaffolding:
```
docs/
├── performance-budgets.md
├── data-retention-policy.md
├── slo/
└── releases/
├── board/                # Board archives (see board-adapter.md)
│   ├── README.md         # Index of quarter files
│   ├── backlog.md
│   ├── decisions-log.md
│   └── done-{YYYY}-Q{N}.md   # Created lazily on first completed task
board-context.md          # Live columns only: Ready, In Progress, Review, Blocked
```

## Step 6: Copy Agency Configuration (Gap-Filling)

For each missing item from the audit, copy it from the project template. Skip items that already exist.

### 6a. Core Rules (if missing)

```bash
mkdir -p .claude/rules

# Copy only missing rule files
for rule in agent-preamble shared-standards operational-standards handoff-protocol crash-investigation git-hooks board-adapter board-in-pr worktree-first; do
    if [ ! -f ".claude/rules/${rule}.md" ]; then
        cp {project-template}/.claude/rules/${rule}.md .claude/rules/
        echo "Copied: ${rule}.md"
    else
        echo "Skipped (exists): ${rule}.md"
    fi
done
```

### 6b. Platform Coding Standards (only for detected/selected platforms)

```bash
# Map detected platforms to coding standards files
# Only copy standards for platforms the project actually uses
for std in {selected-standards}; do
    if [ ! -f ".claude/rules/${std}" ]; then
        cp {project-template}/.claude/rules/${std} .claude/rules/
        echo "Copied: ${std}"
    else
        echo "Skipped (exists): ${std}"
    fi
done
```

**Only include coding standards files for the selected/detected platforms.** Remove any that don't apply.

### 6c. Skills (if missing)

```bash
# Copy only missing skills
for skill in daily-sync replenish retro new-product new-feature release hotfix investigate-crash investigate-bug pick-up-task kick-off code-review health-check onboard-agent dependency-upgrade rfc sprint-report tech-task dispatch update-board create-pr capture-screenshots postmortem setup-repo; do
    if [ ! -f ".claude/skills/${skill}/SKILL.md" ]; then
        mkdir -p ".claude/skills/${skill}"
        cp {project-template}/.claude/skills/${skill}/SKILL.md .claude/skills/${skill}/
        echo "Copied: ${skill}"
    else
        echo "Skipped (exists): ${skill}"
    fi
done
```

### 6d. CLAUDE.md (if missing)

```bash
if [ ! -f "CLAUDE.md" ]; then
    cp {project-template}/CLAUDE.md ./CLAUDE.md
    echo "Copied CLAUDE.md — CUSTOMIZE THIS for your project"
fi
```

If CLAUDE.md was copied, update it to reflect the actual project:
- Update the project name and description
- Remove agents irrelevant to this project's stack
- Remove references to coding standards that weren't copied
- Add any project-specific notes

### 6e. Board (if missing)

The board is a live file plus three archives — see `@.claude/rules/shared/board-adapter.md`. `board-context.md` holds only the four live columns so that the file every agent reads at task start stays small.

```bash
if [ ! -f "board-context.md" ]; then
    cp {project-template}/board-context.md ./board-context.md
    echo "Copied board-context.md"
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

### 6f. Reference Docs (if missing)

```bash
mkdir -p docs docs/references

for doc in setup-guide migration-guide ci-enforcement-policy incident-response; do
    if [ ! -f "docs/${doc}.md" ]; then
        cp {project-template}/docs/${doc}.md docs/
        echo "Copied: docs/${doc}.md"
    fi
done

# Copy reference files for selected platforms
# KMP platforms get kmp-testing-reference.md, kmp-observability-reference.md
# Android gets compose-testing-reference.md, compose-observability-reference.md
# iOS gets swiftui-testing-reference.md, swiftui-observability-reference.md
for ref in {selected-references}; do
    if [ ! -f "docs/references/${ref}" ]; then
        cp {project-template}/docs/references/${ref} docs/references/
        echo "Copied: docs/references/${ref}"
    fi
done
```

### 6g. Settings & Hooks Config (if missing)

```bash
if [ ! -f ".claude/settings.json" ]; then
    cp {project-template}/.claude/settings.json .claude/
fi

if [ ! -f ".claude/hooks.json" ]; then
    cp {project-template}/.claude/hooks.json .claude/
fi
```

### 6h. Sandbox Enforcement (Gap-Filling)

All agency work runs inside the OS sandbox. The template `settings.json` ships a
`sandbox` block (enabled, `failIfUnavailable: true`, `autoAllowBashIfSandboxed: true`,
plus a build-tool/registry allowlist). New projects get it for free via 6g. For an
**existing** project that already had its own `.claude/settings.json` (so 6g was
skipped), add the block if missing — and adapt the worktree write path to this repo's
name, since the worktree-first protocol creates worktrees at `../{repo}-worktrees`.

```bash
if [ -f ".claude/settings.json" ] && ! grep -q '"sandbox"' .claude/settings.json; then
    REPO="$(basename "$(git rev-parse --show-toplevel)")"
    echo "Adding sandbox block to existing .claude/settings.json (worktree path: ../${REPO}-worktrees)"
    # Merge the template's `sandbox` block into the existing settings.json,
    # replacing the template's "../tech-agency-worktrees" allowWrite entry with
    # "../${REPO}-worktrees". Use jq (or hand-edit) to insert the key — do NOT
    # overwrite the whole file; preserve the project's existing keys.
    #   jq --arg wt "../${REPO}-worktrees" \
    #     '.sandbox = (input.sandbox | .filesystem.allowWrite |=
    #        map(if . == "../tech-agency-worktrees" then $wt else . end))' \
    #     .claude/settings.json {project-template}/.claude/settings.json > .tmp \
    #     && mv .tmp .claude/settings.json
fi
```

Notes:
- The sandbox auto-allows sandboxed Bash (no extra prompts), so it does not slow agents down.
- `excludedCommands` keeps VCS network ops (`git push/fetch/pull`, `gh`) unsandboxed so SSH/auth work.
- Linux/WSL2 runners must have `bubblewrap` + `socat` installed, or `failIfUnavailable: true`
  will refuse to start. macOS uses built-in Seatbelt (nothing to install).
- If a project's builds need extra hosts or write paths, extend `sandbox.network.allowedDomains`
  / `sandbox.filesystem.allowWrite` rather than disabling the sandbox.

## Step 7: Install Git Hooks (Gap-Filling)

```bash
# Copy hook scripts if missing
if [ ! -d "hooks" ]; then
    cp -r {project-template}/hooks/ ./hooks/
    echo "Copied hooks directory"
fi

# Install hooks if not already symlinked
if [ ! -L ".git/hooks/pre-commit" ]; then
    chmod +x hooks/install-hooks.sh
    ./hooks/install-hooks.sh
    echo "Git hooks installed"
else
    echo "Git hooks already installed"
fi
```

This installs three hooks:
- **pre-commit**: Secrets detection, force-unwrap checks, lint/format, large file detection
- **commit-msg**: Validates `[STORY-ID] @Agent: description` format
- **pre-push**: Branch naming, commit format, test suite, build verification

See `.claude/rules/git-hooks.md` for full details on what each hook enforce.

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
- [x] .claude/ agency configuration (rules, skills, hooks)
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
- [ ] Update performance budgets in docs/performance-budgets.md
- [ ] Define SLOs per service in docs/slo/
- [ ] Run /new-product to kick off the product planning chain
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
- [ ] See docs/migration-guide.md for the full incremental adoption path

Recommended next steps:
1. Run /daily-sync to initialize the board status
2. Start using commit format: [STORY-ID] @Agent: description
3. Follow docs/migration-guide.md phases for gradual adoption
```

## Customization Notes

- All GitHub Actions are **tool-agnostic** — they have TODO placeholders where the user fills in their specific tooling (Gradle, npm, pytest, Docker, etc.)
- The workflows follow the patterns defined in `@.claude/rules/shared-standards.md` (branch strategy, commit policy) and `@.claude/rules/operational-standards.md` (release process, hotfix process)
- CI thresholds align with the testing and observability standards already defined in each coding standards file
- The release flow matches the `/release` skill's gate sequence: test -> security -> build -> deploy
- The hotfix flow matches the `/hotfix` skill's expedited process: focused tests, quick security, fast deploy
- For existing projects with existing CI, the skill **never overwrites** — it only suggests additions
