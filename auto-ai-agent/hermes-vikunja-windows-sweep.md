---
type: LLM Prompt
title: Hermes Vikunja windows sweep
description: Fixed prompt for the scheduled maintenance-window sweep.
resource: prompt://dryvist/auto-ai-agent/hermes-vikunja-windows-sweep
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
Sweep the maintenance windows now. Close each lapsed window. Return what you closed in your reply envelope.
