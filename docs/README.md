# Docs

`docs/` has five children, split by **lifecycle** — how a document comes into being and what happens to it after. That is the property that predicts where something belongs; subject matter is not, which is how a folder-per-feature tree grows.

| Folder | Lifecycle | Who writes it |
|---|---|---|
| [`artifacts/`](./artifacts/) | Written once per task, then read | An agent, at the end of a task |
| [`board/`](./board/README.md) | Appended to | `board.move_task()` via the adapter |
| [`guides/`](./guides/) | Maintained by hand over time | People |
| `assets/` | Binary, referenced from the above | Whoever adds the image |
| `archive/{year}/` | Frozen | Nobody — moved here, never edited |

## artifacts/

One folder per document type, from the **closed list** in `@.claude/rules/shared/handoff-protocol.md`. Filenames carry the Task ID: `{Task-Id}-{Doc-Type}-{Title}.md`.

The Task ID is the index. `grep -rl "US-042" docs/artifacts/` returns every artifact for that story across all types — which is why there are no per-feature folders and no cross-reference stubs.

A folder here that is not in the rule's table fails `scripts/check-doc-types.sh` in CI. Adding a type means adding the table row in the same PR.

## board/

Backlog, per-quarter Done archives, and the decisions log. `board-context.md` at the repo root keeps only the live columns, because it is read at the start of every agent task. See `@.claude/rules/shared/board-adapter.md`.

## guides/

Hand-maintained and long-lived: setup and migration guides, the command reference, CI and incident policy, plus living registers (`tech-debt/`, `slo/`, performance budgets, data retention). `guides/references/` holds the deep platform references that the coding-standards rules link out to — they live here specifically so that detail does not bloat rules that auto-load into every session.

## archive/

Superseded documents, by year. Moved, never deleted — a plan that was abandoned is still evidence of why.
