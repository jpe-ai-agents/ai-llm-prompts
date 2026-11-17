---
type: LLM Prompt
title: "Claude Code only"
description: "Shared global agent instructions for Claude Code only."
resource: "prompt://dryvist/auto-ai-agent/instructions/agentsmd/claude-code"
tags:
  - shared-instructions
  - agent-instructions
timestamp: "2026-11-17T18:00:00Z"
status: active
consumers:
  - dryvist/nix-ai
  - dryvist/nix-claude-code
render: { engine: literal, variables: [], frontmatter: strip }
source_history:
  - repository: dryvist/ai-assistant-instructions
    path: "agentsmd/claude-code.md"
    note: Migrated from the instruction repository.
---
# Claude Code only

- **Lead rule.** Make small, known edits; review every diff. Delegate scoping >3 unread files, bulk reads, tracker triage, shipping, and implementation.
- **Routing.** Follow [model-delegation.md](rules/on-demand/model-delegation.md).
- Never fork: a fork is a Claude subagent on your own model. The delegation hook places every spawn.
- Prefer parallel tool calls to `&&` chains; they avoid extra permission prompts.
- After a PR needs manual verification CI cannot do (visual render, browser click, UI smoke), send a PushNotification
  immediately: PR URL plus the top check, 200 characters max. Put branch, worktree and repro steps
  in the reply. Skip when CI covers it.
