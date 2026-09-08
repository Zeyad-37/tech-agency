# Board Configuration

This file documents the board backend configuration for this project. The board backend is set in `.claude/settings.json` via the `board_backend` field.

## Current Backend

```
board_backend: markdown
```

When using the `markdown` backend, the board state lives in `board-context.md` at the project root. All agents read and write this file through the board adapter operations defined in `@.claude/rules/shared/board-adapter.md`.

Note that on the `markdown` backend the merged board is **not** a live view of in-flight work: a task's In Progress / Blocked / Review transitions are committed on its own branch and only reach `main` when that branch's PR merges (see `@.claude/rules/shared/board-in-pr.md`). Live state is derived from open PRs. External backends do not have this property — they write through their API immediately.

## Switching to an External Tool

To switch to Jira, Linear, Asana, or another tool:

1. **Connect the MCP tool** — see `docs/guides/tool-integrations.md` for how to configure MCP connections
2. **Update settings.json** — change `board_backend` from `"markdown"` to the tool name (e.g., `"jira"`, `"linear"`, `"asana"`)
3. **Document the status mapping** below
4. **Test** — run `/daily-sync` to verify reads work, then `/pick-up-task` to verify writes work

## Status Mapping

When using an external tool, map the agency's column names to the tool's statuses:

| Agency Column | External Tool Status | Notes |
|---------------|---------------------|-------|
| Backlog | | |
| Ready | | |
| In Progress | | |
| Review | | |
| Blocked | | |
| Done | | |

### Example: Jira

| Agency Column | Jira Status | Jira Transition ID |
|---------------|-------------|-------------------|
| Backlog | Backlog | — |
| Ready | Selected for Development | 21 |
| In Progress | In Progress | 31 |
| Review | In Review | 41 |
| Blocked | Blocked (custom) | 51 |
| Done | Done | 61 |

### Example: Linear

| Agency Column | Linear Status | Linear State ID |
|---------------|--------------|-----------------|
| Backlog | Backlog | backlog |
| Ready | Todo | todo |
| In Progress | In Progress | in_progress |
| Review | In Review | in_review |
| Blocked | Blocked (label) | — (use label) |
| Done | Done | done |

## Project Filter

When using an external tool, specify how to filter tasks to this project:

- **Jira**: Project key = `___` (e.g., `MYAPP`)
- **Linear**: Team = `___`, Project = `___`
- **Asana**: Project GID = `___`

## Agent ↔ User Mapping

Map agency agent names to external tool user accounts:

| Agent | External Tool User | Email |
|-------|--------------------|-------|
| @Kai | | |
| @Swift | | |
| @Link | | |
| @Nova | | |
| @Flux | | |
| @Pyra | | |
| @Forge | | |
| @Atlas | | |
| @Apex | | |
| @Shield | | |
| @Sentinel | | |

Fill in when configuring the external tool connection.

## Local Mirror

Even when using an external backend, `board-context.md` is maintained as a local mirror for quick offline reference. The board adapter automatically syncs writes to both the external tool and the local file.
