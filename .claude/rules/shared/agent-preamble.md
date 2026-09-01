# Agent Session Preamble

Every agent must perform these steps at the start of any task:

0. **Create your worktree (mandatory, before any file writes)**: Follow `@.claude/rules/shared/worktree-first.md`. All Claude Code work happens in a git worktree — never in the main checkout. Derive the branch name from the task type (`{STORY-ID}/{slug}`, `tech/{slug}`, `deps/{slug}`, `hotfix/{ver}/{slug}`, `{BUG-ID}/{slug}`, or `triage/{slug}` if no ID yet), create the worktree under `../{repo}-worktrees/{branch-slug}`, `cd` into it, and verify with `pwd` + `git branch --show-current` before doing anything else. If you are already inside a worktree (spawned by `/dispatch` or `/dispatch-task`), verify it matches the task and continue.
1. **Read the board**: Check `board-context.md` for current state, your WIP items, and blockers
2. **Read feature context**: `grep -rl "{Task-Id}" docs/artifacts/` returns every artifact for this work — PRD, BRD, ADR, RFC, design spec, prior incident notes — because the Task ID is in every filename. Read them and follow prior decisions; do not contradict them. If the task has no ID yet, grep the feature name instead
3. **Check dependencies**: Identify upstream artifacts you depend on. If missing, request from the producing agent via @Atlas
4. **Confirm scope**: Verify your assigned task has clear acceptance criteria. If not, ask @Diana or @Morgan before starting
5. **Announce start**: Update `board-context.md` to move your task to "In Progress"

At the end of any task:

1. **Write tests**: Every code change must be covered by tests on the same branch. Tests must cover all acceptance criteria — unit tests for logic, integration tests for API/DB boundaries. No exceptions.
2. **Walk through acceptance criteria**: For every acceptance criterion of the form "when X then Y", enumerate every code path that produces Y and confirm each one satisfies the criterion. Document the walkthrough in the PR description as a short list (example: "Mark done routes back to agenda — confirmed in (a) no-celebration path, (b) confetti-only path, (c) milestone-dialog path"). If any path doesn't satisfy the criterion, either fix it on this branch or explicitly mark it out of scope in the PR description. Implementing the happy path only and assuming alternatives work the same way is the single most common cause of round-2 review findings.
3. **Verify tests pass**: Run the full test suite for the affected module and confirm all tests pass before proceeding. Do not commit failing tests.
4. **Save artifacts**: Write all output documents to `docs/artifacts/{doc-type}/{Task-Id}-{Doc-Type}-{Title}.md`. `{doc-type}` must come from the closed list in `@.claude/rules/shared/handoff-protocol.md` — if none fits, that is a rule change, not a new folder. Create the folder if it does not exist.
5. **Commit**: Commit with `[STORY-ID] @YourAgentName: description` format (e.g., `[US-042] @Kai: Add email validation`). Commits happen inside the worktree on the task branch — never on `main`.
6. **Update the board**: Move your task to "Review" in `board-context.md` only after tests pass. The board edit is committed on the task branch and merges back to `main` via the PR, just like the code change — never as a board-only PR and never as a commit on `main` (see `@.claude/rules/shared/board-in-pr.md`).
7. **Handoff**: Use the appropriate handoff template from @.claude/rules/shared/handoff-protocol.md. Tag the receiving agent and @Atlas. Open the PR with `/create-pr` — its post-PR sweep auto-removes any worktree whose PR has already merged, so cleanup is automatic for the happy path.
