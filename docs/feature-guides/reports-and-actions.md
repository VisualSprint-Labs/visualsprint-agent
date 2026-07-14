# Final Reports And Action Recommendations

This guide explains how VisualSprint turns meeting state into a final report and approval-based downstream action recommendations.

## Feature Purpose

The final report is the main deliverable.

It should answer:

- what did the team decide?
- who owns follow-up?
- what is blocked?
- what questions remain open?
- what prior memory matters?
- what should be sent to Jira or Slack after human approval?

The action system exists because not every meeting record should automatically become a Jira issue or Slack message.

## Main Files

Reports:

- `services/api/src/visualsprint_api/routes/meetings.py`
- `services/api/src/visualsprint_api/summary_pipeline.py`
- `services/api/src/visualsprint_api/service_clients.py`
- `services/agents/src/visualsprint_agents/summary.py`
- `services/agents/src/visualsprint_agents/adk/summary_agent.py`
- `apps/web/src/features/report/meeting-report-page.tsx`
- `apps/web/src/features/report/components/final-report-view.tsx`
- `apps/web/src/features/report/components/report-toolbar.tsx`

Actions:

- `services/api/src/visualsprint_api/routes/actions.py`
- `services/api/src/visualsprint_api/action_executors/jira_client.py`
- `services/api/src/visualsprint_api/action_executors/slack_client.py`
- `services/agents/src/visualsprint_agents/action.py`
- `services/agents/src/visualsprint_agents/adk/action_agent.py`
- `apps/web/src/features/actions/actions-page.tsx`

Contracts:

- `FinalReport`
- `MeetingSummaryPacket`
- `ActionRecommendation`
- `ActionRecommendationInput`
- `JiraRecommendation`
- `SlackRecommendation`

## Final Report Flow

High-level flow:

1. Meeting is ended.
2. API builds `MeetingSummaryPacket`.
3. API calls summary agent when configured.
4. API stores `FinalReport`.
5. Frontend displays final report.

API routes:

- `GET /api/meetings/{meeting_id}/summary-packet`
- `GET /api/meetings/{meeting_id}/final-report`
- `POST /api/meetings/{meeting_id}/final-report`

## Summary Packet

File:

- `services/api/src/visualsprint_api/summary_pipeline.py`

Purpose:

- turns meeting state into a structured packet for summary generation

The summary packet includes:

- meeting ID
- title
- participant count
- duration
- draft executive summary
- highlights
- decisions
- commitments
- blockers
- open questions
- memory highlights

Why this matters:

- the summary agent should not inspect raw browser capture
- the agent receives already-curated meeting state
- final report generation stays schema-oriented

## Summary Agent Boundary

API method:

- `run_summary_agent(packet)` in `services/api/src/visualsprint_api/service_clients.py`

Agents service method:

- `run_summary_agent(payload)` in `services/agents/src/visualsprint_agents/summary.py`

The summary agent returns:

- `FinalReportDraft`

The API then constructs:

- `FinalReport`

Important behavior:

- structured records are preserved from the packet
- the agent mainly improves `executiveSummary`
- unresolved blockers and open questions should remain visible

## Final Report UI

Main component:

- `apps/web/src/features/report/components/final-report-view.tsx`

Page:

- `apps/web/src/features/report/meeting-report-page.tsx`

The report UI displays:

- executive summary
- decisions
- commitments
- blockers
- open questions
- memory highlights
- evidence-backed details

## Action Recommendation Flow

High-level flow:

1. User opens actions page after report exists.
2. User clicks/generates recommendations.
3. API builds action-agent input from final report.
4. Agents service returns recommendations.
5. API stores recommendations with `pending` status.
6. User approves or rejects.
7. Only approved recommendations can execute.
8. Execution calls Jira or Slack integration.

API routes:

- `POST /api/meetings/{meeting_id}/actions/recommendations`
- `GET /api/meetings/{meeting_id}/actions/recommendations`
- `POST /api/meetings/{meeting_id}/actions/recommendations/{recommendation_id}/approve`
- `POST /api/meetings/{meeting_id}/actions/recommendations/{recommendation_id}/reject`
- `POST /api/meetings/{meeting_id}/actions/recommendations/{recommendation_id}/execute`

Frontend methods:

- `generateActionRecommendations(meetingId)`
- `getActionRecommendations(meetingId)`
- `approveActionRecommendation(...)`
- `rejectActionRecommendation(...)`
- `executeActionRecommendation(...)`

## Action Agent

Files:

- `services/agents/src/visualsprint_agents/action.py`
- `services/agents/src/visualsprint_agents/adk/action_agent.py`

Input:

- `ActionAgentRequest`

Output:

- `ActionAgentResponse`

Recommendation types:

- `suggest_for_jira`
- `suggest_for_slack`
- `suggest_for_escalation`
- `suggest_for_manual_review`

Important behavior:

- deduplicate recommendations
- prefer high-value actions
- do not send anything externally
- keep human approval required

## Approval State

Action recommendation status values:

- `pending`
- `approved`
- `rejected`
- `completed`
- `failed`

Why approval matters:

- agents can suggest, but users decide
- external side effects are controlled
- the product remains safer for Jira and Slack

## Jira Execution

File:

- `services/api/src/visualsprint_api/action_executors/jira_client.py`

Important methods:

- `execute_jira_action(recommendation)`
- `_jira_auth_header()`
- `_resolve_project_issue_meta(...)`
- `_create_jira_issue(...)`
- `_update_jira_issue(...)`
- `_resolve_jira_issue(...)`
- `_execute_jira_stub(...)`

Behavior:

- if Jira config is complete, call Jira API
- otherwise use a stub result

Configuration usually includes:

- Jira base URL
- Jira email
- Jira API token
- Jira project key

## Slack Execution

File:

- `services/api/src/visualsprint_api/action_executors/slack_client.py`

Important methods:

- `execute_slack_action(recommendation)`
- `_resolve_channel(slack_channel)`
- `_post_slack_message(slack_details)`
- `_execute_slack_stub(slack_details)`

Behavior:

- if Slack token and channel config are complete, post a Slack message
- otherwise return a stub result

Configuration usually includes:

- Slack bot token
- default channel ID or channel name

## Actions UI

File:

- `apps/web/src/features/actions/actions-page.tsx`

The UI supports:

- pending/approved/completed/all filters
- recommendation cards
- approve/reject controls
- execute controls
- Jira and Slack details
- confidence and urgency display

## Common Bugs To Watch For

### Recommendations are empty

Likely causes:

- final report does not exist
- action agent returned no recommendations
- configured runtime failed and fallback rules found no high-value items

### Execute returns not found

Likely causes:

- recommendation ID is wrong
- recommendation was not approved
- meeting ID is wrong

### Slack/Jira action says stub

Likely cause:

- integration secrets or runtime env vars are not configured

This is safer than failing the whole product during local development.

### Agent recommends too many actions

Likely cause:

- action prompt is too broad

Fix:

- require high precision
- keep low-confidence items in manual review
- do not mirror every meeting record into an external action

## Learning Exercise

Trace one blocker into a Jira recommendation:

1. Reasoning agent creates a blocker.
2. API persists blocker.
3. Meeting ends.
4. API builds final report.
5. User generates action recommendations.
6. API calls action agent with report data.
7. Action agent recommends `suggest_for_jira`.
8. API stores recommendation as pending.
9. User approves.
10. User executes.
11. Jira executor creates or stubs the issue.
