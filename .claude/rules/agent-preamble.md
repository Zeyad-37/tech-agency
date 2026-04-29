# Agent Session Preamble

Every agent must perform these steps at the start of any task:

1. **Read the board**: Check `board-context.md` for current state, your WIP items, and blockers
2. **Read feature context**: If working on a feature, search for existing docs across `docs/prd/`, `docs/brd/`, `docs/adr/`, `docs/rfc/`, `docs/design-spec/`, and `docs/incident-notes/` using the Task ID or feature name. Follow prior decisions — do not contradict them
3. **Check dependencies**: Identify upstream artifacts you depend on. If missing, request from the producing agent via @Atlas
4. **Confirm scope**: Verify your assigned task has clear acceptance criteria. If not, ask @Diana or @Morgan before starting
5. **Announce start**: Update `board-context.md` to move your task to "In Progress"

At the end of any task:

1. **Write tests**: Every code change must be covered by tests on the same branch. Tests must cover all acceptance criteria — unit tests for logic, integration tests for API/DB boundaries. No exceptions.
2. **Verify tests pass**: Run the full test suite for the affected module and confirm all tests pass before proceeding. Do not commit failing tests.
3. **Save artifacts**: Write all output documents to `docs/{doc-type}/{Task-Id}-{Doc Type}-Title.md`. Create the folder if it does not exist.
4. **Commit**: Commit with `[STORY-ID] @YourAgentName: description` format (e.g., `[US-042] @Kai: Add email validation`)
5. **Update the board**: Move your task to "Review" in `board-context.md` only after tests pass.
6. **Handoff**: Use the appropriate handoff template from @.claude/rules/handoff-protocol.md. Tag the receiving agent and @Atlas
