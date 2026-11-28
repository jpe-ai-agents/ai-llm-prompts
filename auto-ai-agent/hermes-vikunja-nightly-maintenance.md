---
type: LLM Prompt
title: Hermes Vikunja nightly maintenance
description: Fixed prompt for the scheduled nightly maintenance run.
resource: prompt://dryvist/auto-ai-agent/hermes-vikunja-nightly-maintenance
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
Run nightly maintenance now for tasks changed in the last 14 days, within your caps. Return the digest in your reply envelope.
