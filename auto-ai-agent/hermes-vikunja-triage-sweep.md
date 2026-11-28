---
type: LLM Prompt
title: Hermes Vikunja triage sweep
description: Fixed prompt for the scheduled inbox sweep.
resource: prompt://dryvist/auto-ai-agent/hermes-vikunja-triage-sweep
tags:
- hermes
- autonomous-agent
- cron
timestamp: '2026-11-28T06:30:00Z'
status: active
consumers:
- dryvist/ansible-proxmox-ai
render:
  engine: literal
  variables: []
  frontmatter: strip
source_history: []
---
Sweep the inbox project now. Follow your instructions for every item. Return your reply envelope.
