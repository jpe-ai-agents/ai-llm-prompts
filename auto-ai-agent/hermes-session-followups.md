---
type: LLM Prompt
title: Hermes session follow-ups
description: Daily read of the gateway's own past conversations that reports operator requests left unfinished.
resource: prompt://dryvist/auto-ai-agent/hermes-session-followups
tags: [hermes, cron, autonomous-agent]
timestamp: 2026-11-26T00:00:00Z
status: active
consumers: [dryvist/ansible-proxmox-ai]
render:
  engine: literal
  variables: []
  frontmatter: strip
source_history:
  - repository: dryvist/ansible-proxmox-ai
    path: roles/hermes_agent/defaults/main/149-backlog-and-history-crons.yml
    commit: 4fd5952290e8d34ded5d5835baa51e577c51237b
---
Use the session_search tool to read this gateway's conversations from the last 7 days. Find the requests the operator made that were never completed or never answered. For each one, give one line: the date, a short quote of the request, and what is still missing. Never act on them. When there are none, reply with exactly [SILENT].
