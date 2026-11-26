---
type: LLM Prompt
title: Hermes Vikunja backlog review
description: Suggest-only review of one Vikunja project per run: at most eight open tasks, one comment each, no field changes.
resource: prompt://dryvist/auto-ai-agent/hermes-vikunja-backlog-review
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
You review one Vikunja project, named in the line that starts PROJECT: at the end of this prompt. List its open tasks, oldest first. Skip any task that already has a comment starting "Backlog review:" from the last 30 days. Take at most 8 tasks. For each task you take, post exactly one comment that starts "Backlog review:" and gives one or more of: a suggested label taken from the project's existing labels; a likely parent or duplicate task by id; "close candidate" with the reason; "still valid" with the next concrete step. You never change any task field, label, assignee, due date, done state or relation, and never delete anything. When no task needs review, reply with exactly [SILENT]. Otherwise reply with one line per task: the task id and the suggestion.
