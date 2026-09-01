# Tool Integrations (MCP Connections)

## Setup

1. Enable the MCP connection in the agent's project/configuration
2. Add the usage guidance to the agent's system prompt (already included in agent definitions)

## Integration Matrix

| Tool | Agents | Purpose |
|------|--------|---------|
| Jira/Linear | Atlas | Kanban board / task tracking |
| Slack | Atlas | Team notifications, blocker alerts |
| PagerDuty | Atlas, Sentinel | Incident escalation, on-call |
| Google Analytics | Morgan, Echo | Product metrics, user behavior |
| Mixpanel/Amplitude | Morgan | Feature adoption, funnels |
| Figma | Pixel | Design file access, inspect mode |
| Crashlytics | Swift, Kai, Apex, Echo | Crash reports, stack traces |
| Datadog | Sentinel, Echo | Infrastructure metrics, APM |
| Sentry | Sentinel, Apex, Echo | Application errors, breadcrumbs |
| Snyk | Shield | Dependency vulnerability scanning |
| SonarQube | Shield, Apex | Static analysis, code quality |

## Per-Agent Guidance

### Atlas — Jira/Linear, Slack, PagerDuty
- Query Jira for board status before daily sync
- Post board summaries and cycle time alerts to Slack
- Create PagerDuty incidents for P0 blockers

### Morgan — Google Analytics, Mixpanel/Amplitude
- Pull usage metrics before writing PRDs
- Reference funnel data in feature prioritization
- Include adoption metrics in release notes

### Pixel — Figma
- Access design files for component specs
- Export design tokens from Figma variables
- Reference Figma frames in design handoffs

### Sentinel — Datadog, Sentry, PagerDuty
- Query Datadog baseline metrics before deployments
- Monitor Sentry error rates post-deployment; alert @Atlas if >1% increase
- Route incidents through PagerDuty on-call rotation

### Shield — Snyk, SonarQube
- Run Snyk scan on dependencies before security review
- Check SonarQube for SAST findings
- Include scan results in security review reports

### Apex — Sentry, Crashlytics, SonarQube
- Check Sentry for existing errors before test planning
- Review Crashlytics for crash patterns in mobile testing
- Reference SonarQube code coverage in release sign-off

### Echo — Sentry, Crashlytics, Google Analytics, Datadog
- Check Sentry/Crashlytics for known issues before responding to tickets
- Reference Google Analytics for feature usage context
- Check Datadog for service health when triaging performance issues

## Access Control

- Each agent only gets connections listed in the matrix — no cross-access
- Read-only access by default; write access (Jira ticket creation, Slack posting) only for Atlas and Sentinel
- Credentials managed via MCP server configuration, never in agent prompts
