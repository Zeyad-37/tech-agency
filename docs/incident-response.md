# Incident Response Procedures

This document defines escalation procedures, on-call rotation templates, and runbook references. For incident severity definitions and SLAs, see `@.claude/rules/operational-standards.md` (lines 92–100).

## Escalation Flow

```
Issue detected (monitoring alert / user report / crash spike)
  │
  ├── Automated detection (Sentinel monitoring)
  │   └── Alert routes to on-call engineer via configured channel
  │
  └── Manual detection (user report via Echo, developer observation)
      └── Reporter tags @Atlas in board-context.md with initial severity estimate
          │
          ▼
On-call / first responder assesses severity
  │
  ├── P0 (Critical): Immediate action
  │   ├── Acknowledge within 15 minutes
  │   ├── @Zeyad notified immediately
  │   ├── All available engineers pulled in
  │   ├── Communication: status updates every 30 minutes
  │   ├── Resolution target: ASAP (no SLA upper bound — work until resolved)
  │   └── Post-mortem within 48 hours
  │
  ├── P1 (High): Urgent action
  │   ├── Acknowledge within 30 minutes
  │   ├── Dedicated engineer assigned
  │   ├── Communication: status updates every 2 hours
  │   ├── Resolution target: within 4 hours
  │   └── Post-mortem within 48 hours
  │
  ├── P2 (Medium): Next priority
  │   ├── Acknowledge within 2 hours
  │   ├── Pull into queue as next priority item
  │   ├── Communication: status update at end of business day
  │   ├── Resolution target: within 1 business day
  │   └── Brief incident note (no full post-mortem unless recurring)
  │
  └── P3 (Low): Backlog
      ├── Acknowledge within 1 business day
      ├── Add to backlog
      └── Pull when capacity allows
```

## On-Call Rotation Template

Adapt this template to your team size and working hours.

### Rotation Schedule

```markdown
# On-Call Rotation — [Month Year]

| Week | Primary On-Call | Secondary On-Call | Notes |
|------|----------------|-------------------|-------|
| Week 1 (Mon–Sun) | @[Agent/Person] | @[Agent/Person] | |
| Week 2 (Mon–Sun) | @[Agent/Person] | @[Agent/Person] | |
| Week 3 (Mon–Sun) | @[Agent/Person] | @[Agent/Person] | |
| Week 4 (Mon–Sun) | @[Agent/Person] | @[Agent/Person] | |

**Handoff:** Fridays at 10:00 AM. Outgoing on-call briefs incoming on-call on open issues.
**Escalation:** If primary doesn't acknowledge within 15 min (P0) or 30 min (P1), page secondary.
**Override:** If on-call is unavailable, they arrange a swap at least 24h in advance and notify @Atlas.
```

### On-Call Responsibilities

- **Monitor alert channels** during on-call hours.
- **Triage incoming alerts**: assess severity, acknowledge, begin investigation or escalate.
- **Document actions taken** in the incident channel or board-context.md.
- **Hand off cleanly**: at rotation end, brief the next on-call on any open or recently resolved issues.

### For AI Agent Teams

When using the Tech Agency with AI agents (no human on-call):

- @Sentinel acts as the always-on monitoring agent. It detects issues via health checks, error rate spikes, and crash reports.
- @Atlas acts as the triage coordinator. It assesses severity and routes to the appropriate engineer agent.
- Escalation to @Zeyad (human) occurs for all P0 incidents and for any P1 that isn't resolved within 2 hours.
- The `/investigate-crash` skill automates crash spike investigation and post-mortem generation.
- The `/investigate-bug` skill automates functional bug investigation (non-crashing issues) and produces bug reports with fix plans.

## Runbook References

Each service should have a runbook stored in `docs/runbooks/{service-name}.md`. Runbooks are maintained by @Sentinel and @Scroll.

### Runbook Template

```markdown
# Runbook — [Service Name]

## Service Overview
- **Repository:** [link]
- **Owner agent:** @[Agent]
- **Deployment:** [K8s namespace / ECS service / etc.]
- **Health check:** [URL]
- **Dashboard:** [link to monitoring dashboard]

## Common Issues & Remediation

### Issue: High Error Rate (> 1% over 5 min)
**Symptoms:** Alert fires on error rate metric.
**Diagnosis:**
1. Check recent deployments: `git log --oneline -5` on the service repo.
2. Check dependency health: hit `/health/ready` and inspect which check failed.
3. Check logs: search for ERROR level logs in the last 30 minutes.
**Remediation:**
- If caused by a recent deploy: revert the last commit and redeploy.
- If caused by a dependency (DB, external API): check dependency status, open incident for dependency team.
- If cause is unclear: collect logs and traces, escalate to the owning agent.

### Issue: Service Unresponsive (Health Check Failing)
**Symptoms:** Liveness probe failing, service returning 5xx or timing out.
**Diagnosis:**
1. Check if the process is running.
2. Check resource usage (CPU, memory, disk).
3. Check database connection pool (connection exhaustion).
**Remediation:**
- Restart the service.
- If resource-bound: scale up or investigate memory leak.
- If DB connection pool exhausted: restart, then investigate query patterns.

### Issue: Database Migration Failed
**Symptoms:** Deployment fails during migration step.
**Diagnosis:**
1. Check migration logs for the specific error.
2. Check if the migration was partially applied.
**Remediation:**
- If migration was not applied: fix the migration SQL, rerun.
- If partially applied: manually roll back the partial changes, fix the migration, rerun.
- Never manually modify a migration that has been applied to production. Create a new corrective migration.

### Issue: Crash Spike (Mobile)
**Symptoms:** Crash-free rate drops below 99.5%.
**Diagnosis:**
1. Run `/investigate-crash` skill.
2. Check `.claude/crashlytics-context.md` for crash data.
**Remediation:**
- Follow the crash investigation protocol.
- If the fix is ready: `/hotfix` workflow.
- If the fix needs design: route to @Sage, communicate timeline to @Echo for user support.
```

### Required Runbook Coverage

Every service deployed to production MUST have a runbook covering at minimum:

- Service overview (repo, owner, deployment, health check, dashboard links)
- Top 3 most common failure modes with diagnosis and remediation steps
- Restart procedure
- Rollback procedure (with specific commands)
- Scaling procedure (if applicable)
- Contact information for the owning agent/team

## Communication During Incidents

### Status Update Template

```markdown
**Incident:** [Brief title]
**Severity:** P[0-3]
**Status:** Investigating / Identified / Mitigating / Resolved
**Impact:** [What is broken? Who is affected?]
**Current action:** [What is being done right now]
**Next update:** [Time of next status update]
```

### Communication Channels

| Severity | Channel | Frequency |
|----------|---------|-----------|
| P0 | Dedicated incident channel + @Zeyad direct | Every 30 minutes |
| P1 | Team channel | Every 2 hours |
| P2 | Team channel | End of business day |
| P3 | Board task | On resolution |

### Post-Incident

1. **Post-mortem**: P0 and P1 incidents get a post-mortem within 48 hours. Use the template in `.claude/rules/crash-investigation.md`.
2. **Action items**: All prevention action items from the post-mortem are added to `board-context.md` with assigned owners and due dates. See "Feedback Loop Closure" below.
3. **Retro**: @Atlas schedules a retro to discuss systemic issues if the same incident category occurs more than twice.

## Feedback Loop Closure

Post-incident action items MUST be tracked to completion:

1. Each action item from a post-mortem or retro is added to `board-context.md` backlog with:
   - Assigned owner (@AgentName)
   - Priority (P0–P3)
   - Due date (P0: 48h, P1: 1 week, P2: 2 weeks, P3: next sprint)
   - Source reference (link to the post-mortem or retro doc)
2. @Atlas includes these items in the weekly replenishment review.
3. Overdue action items are escalated: @Atlas flags them in the daily sync.
4. Action items are only marked complete when the fix is deployed and verified (not just when the code is written).

This ensures that lessons learned from incidents actually result in systemic improvements, not just documentation.
