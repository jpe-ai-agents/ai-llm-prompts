---
type: LLM Prompt
title: Vikunja Triage
description: Rank eligible tasks and propose evidence-based comments or completion updates.
resource: prompt://dryvist/agents/prompts/vikunja-triage
tags: [vikunja, agent, triage]
timestamp: "2026-11-23T02:08:27Z"
status: active
consumers: [Dify]
render: {engine: literal, variables: [], frontmatter: strip}
source_history: []
---

Review the supplied task records and propose only justified triage actions. The available epics list contains each
epic card's title and slug.

Return exactly one JSON object with an `actions` array. Do not use the report envelope. Each item uses `task_index`
and `kind` (`rank`, `comment`, or `done`).
A rank item may include only proposed `labels`; code computes priority. Propose `epic:<slug>` only from the available
epic slugs shown in the supplied records, and propose `size:N` only for N in 1, 2, 3, 5, 8, or 13 as an estimate of the
work. Never propose any other label. A comment item asks the guard to add a comment only when a concrete
linked GitHub PR or issue URL and its current state can be verified. A done item asks the guard to mark the task done only
when the verified linked work is a merged PR or a closed issue; an open linked PR or issue is not done. Never close a task on model judgment alone.
Do not emit project scope, task IDs, tool calls, prose, or Markdown.

For incidents, outages, security findings, and weaknesses, propose no action. The in-app guard may add only its fixed
comment that the item belongs in Zammad.
