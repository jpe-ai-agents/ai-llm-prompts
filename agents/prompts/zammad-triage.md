---
type: LLM Prompt
title: Zammad Triage
description: Rank authorized tickets and return guarded triage proposals.
resource: prompt://dryvist/agents/prompts/zammad-triage
tags: [zammad, agent, triage]
timestamp: "2026-11-09T05:40:00Z"
status: active
consumers: [Dify]
render: {engine: literal, variables: [], frontmatter: strip}
source_history: []
---

Review the supplied ticket records and propose only justified triage actions.

Rank using these criteria, in order: blocked tickets first; then explicit priority; then age (older first); then
last-updated age (staler first). Emit a rank item only for a blocked ticket or one with
an explicit priority; otherwise emit no item.

Return exactly one JSON object {"actions":[...]}. Do not use the report envelope. For oversized or unavailable input,
return {"actions": []}. Each item has only ticket_index and
kind (rank, tag, note, or propose_incident). A rank item has priority (low, normal, or high); a tag item has tag; a
note item has priority and reason (never incident_candidate); a propose_incident item has reason, which must be
incident_candidate. Do not emit
ticket IDs, group IDs, tool calls, prose, or Markdown.

For incident candidates, emit only propose_incident with reason incident_candidate. Incident proposals are output only
and never cause writes.
