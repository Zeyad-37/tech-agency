# Agent Session Preamble

Every agent must perform these steps at the start of any task:

0. **Create your worktree (mandatory, before any file writes)**: Follow `@.claude/rules/shared/worktree-first.md`. All Claude Code work happens in a git worktree — never in the main checkout. Derive the branch name from the task type (`{STORY-ID}/{slug}`, `tech/{slug}`, `deps/{slug}`, `hotfix/{ver}/{slug}`, `{BUG-ID}/{slug}`, or `triage/{slug}` if no ID yet), create the worktree under `../{repo}-worktrees/{branch-slug}`, `cd` into it, and verify with `pwd` + `git branch --show-current` before doing anything else. If you are already inside a worktree (spawned by `/dispatch` or `/dispatch-task`), verify it matches the task and continue.
1. **Read the board**: Check `board-context.md` for current state, your WIP items, and blockers
2. **Read feature context**: If working on a feature, search for existing docs across `docs/prd/`, `docs/brd/`, `docs/adr/`, `docs/rfc/`, `docs/design-spec/`, and `docs/incident-notes/` using the Task ID or feature name. Follow prior decisions — do not contradict them
3. **Read your coding standard (required, before any code)**: Identify the stack(s) your task writes code in, then read each one's coding standard. They are **not** preloaded — they live in the plugin and are read on demand. Resolve the path as `${CLAUDE_PLUGIN_ROOT}/rules/<path>.md`, falling back to `.claude/rules/<path>.md` when `CLAUDE_PLUGIN_ROOT` is unset. The full table of standards, owners, and the resolution snippet is in `@.claude/rules/shared/rules-delivery.md`. A task spanning two stacks requires reading both standards. If a standard cannot be resolved, that is a blocker to report — not a step to skip. (Documentation-only and planning-only tasks may skip this step.)
4. **Check dependencies**: Identify upstream artifacts you depend on. If missing, request from the producing agent via @Atlas
5. **Confirm scope**: Verify your assigned task has clear acceptance criteria. If not, ask @Diana or @Morgan before starting
6. **Announce start**: Update `board-context.md` to move your task to "In Progress"

At the end of any task:

1. **Write tests**: Every code change must be covered by tests on the same branch. Tests must cover all acceptance criteria — unit tests for logic, integration tests for API/DB boundaries. No exceptions.
2. **Walk through acceptance criteria**: For every acceptance criterion of the form "when X then Y", enumerate every code path that produces Y and confirm each one satisfies the criterion. Document the walkthrough in the PR description as a short list (example: "Mark done routes back to agenda — confirmed in (a) no-celebration path, (b) confetti-only path, (c) milestone-dialog path"). If any path doesn't satisfy the criterion, either fix it on this branch or explicitly mark it out of scope in the PR description. Implementing the happy path only and assuming alternatives work the same way is the single most common cause of round-2 review findings.
3. **Verify tests pass**: Run the full test suite for the affected module and confirm all tests pass before proceeding. Do not commit failing tests.
4. **Save artifacts**: Write all output documents to `docs/{doc-type}/{Task-Id}-{Doc Type}-Title.md`. Create the folder if it does not exist.
5. **Commit**: Commit with `[ID] @YourAgentName: description` format (e.g., `[US-042] @Kai: Add email validation`). `[ID]` is the task's board ID; the `@Agent:` tag is optional but expected for agent-authored commits. See the Git Commit Policy in `@.claude/rules/shared/shared-standards.md`. Commits happen inside the worktree on the task branch — never on `main`.
6. **Update the board**: Move your task to "Review" in `board-context.md` only after tests pass. The board edit is committed on the task branch and merges back to `main` via the PR, just like the code change — never as a board-only PR and never as a commit on `main` (see `@.claude/rules/shared/board-in-pr.md`).
7. **Handoff and open the PR**: Use the appropriate handoff template from `@.claude/rules/shared/handoff-protocol.md`. Tag the receiving agent and @Atlas. Then open the PR with `/create-pr`.

   **Invoking `/create-pr` is itself the authorization to push this branch** — it commits, runs the pre-push verification gate, pushes, and opens the PR without asking for a further confirmation. That is the settled push policy (see "Push Policy" in `@.claude/rules/shared/shared-standards.md`); it does not contradict any "commit locally, don't push" rule, because that rule applies only to a bare `git push` outside these skills. Never push to `main`. If a parent skill needs the PR prepared but not pushed, it passes `/create-pr --no-push`.

   `/create-pr`'s post-PR sweep auto-removes any worktree whose PR has already merged, so cleanup is automatic for the happy path.
