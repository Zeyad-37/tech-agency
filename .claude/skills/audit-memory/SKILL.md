---
name: audit-memory
description: "Audit Claude Code's auto-memory store for stale, duplicate, or wrong entries. Run periodically (default: every 30 days). Use when the user says 'audit memory', 'check memory', 'review memories', 'clean up memory', or sees the audit-overdue reminder at session start."
---

# Audit Memory

Goal: catch stale, duplicate, or wrong memories before they propagate as false facts into future sessions. Auto-memory entries can drift — a feedback rule may have been superseded, a project memory may reference shipped/deleted work, two memories may overlap.

## Memory store location

Memories live outside the project, in user-personal storage:

```
$HOME/.claude-personal/projects/<encoded-project-path>/memory/
```

Where `<encoded-project-path>` is the project's absolute path with `/` and `.` replaced by `-`. Example: `/Users/alice/projects/foo` → `-Users-alice-projects-foo`.

The `MEMORY.md` index in that directory lists all active memory files.

## Steps

1. **Locate the memory store for this project:**
   ```bash
   ENCODED=$(pwd | sed 's|[./]|-|g')
   MEM_DIR="$HOME/.claude-personal/projects/${ENCODED}/memory"
   ls "$MEM_DIR"
   cat "$MEM_DIR/MEMORY.md"
   ```

2. **Read each memory file referenced in MEMORY.md.** For each one, evaluate:

   | Question | If "no" → action |
   |----------|------------------|
   | **Still true?** Verify file paths exist, function names resolve, decisions still hold. | Fix the memory or delete it. |
   | **Still useful?** Has the situation it described been resolved by other means (e.g., a one-time prevention is now part of a coding standard)? | Delete or demote to historical. |
   | **Still specific?** Vague descriptions don't surface at the right moments — Claude reads descriptions to decide relevance. | Sharpen the `description:` line. |
   | **Unique?** Two memories saying overlapping things means neither gets fully applied. | Merge into one. |

3. **Propose changes — do NOT make them yet.** Output a per-memory verdict table:

   | File | Verdict | Reason | Proposed action |
   |------|---------|--------|-----------------|
   | feedback_X.md | KEEP | Still applies, recent reinforcement | None |
   | project_Y.md | DELETE | References shipped feature US-042, no longer relevant | Delete + remove from MEMORY.md |
   | feedback_Z.md | MERGE | Overlaps with feedback_W.md | Consolidate into feedback_W.md, update description |
   | feedback_A.md | EDIT | Description too vague to surface reliably | Sharpen description to "..." |

4. **Wait for user approval per change** before editing.

5. **Apply approved changes.** For each:
   - Edit/delete the memory file
   - Update `MEMORY.md` index accordingly

6. **Stamp the audit:**
   ```bash
   date +%Y-%m-%d > .claude/.last-memory-audit
   ```
   The SessionStart audit-reminder hook reads this file and stays quiet for 30 days.

## Frequency

- **Default:** every 30 days. SessionStart hook surfaces a reminder when overdue.
- **Trigger early:** after a major refactor that invalidates project memories, or when a feedback memory is being consistently overridden (suggests it's wrongly framed).
- **Safe to skip:** if no new memories were added since the last audit AND the project hasn't changed materially.

## Output to user

End by showing:
- Count of memories before vs after the audit
- Summary of changes made
- Updated `MEMORY.md` contents
- Next-audit due date (audit date + 30 days)
