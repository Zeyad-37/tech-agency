# Board Archives

`board-context.md` at the repo root holds only the **live** columns — Ready, In Progress, Review, Blocked. It is read at the start of every agent task, so it is kept small on purpose.

Everything here is history: consulted deliberately, never on the hot path. See `@.claude/rules/shared/board-adapter.md` for the operation-to-file mapping.

| File | Holds | Read by |
|---|---|---|
| [backlog.md](./backlog.md) | Work identified but not yet Ready | `/replenish`, triage |
| [decisions-log.md](./decisions-log.md) | Decisions with the date, decider, and ADR reference | Any agent checking a prior decision |
| `done-{YYYY}-Q{N}.md` | Completed tasks, one file per quarter | `/sprint-report`, `/retro`, release gates |

## Quarter files

| Quarter | File |
|---|---|
| 2026 Q3 | [done-2026-Q3.md](./done-2026-Q3.md) |

A quarter file is created by the first `→ Done` transition in that quarter. Closed quarters are never rewritten — an archive that changes after the fact is not a record. Add a row here when a new quarter file appears.
