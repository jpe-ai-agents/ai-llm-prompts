---
name: fleet-utilization
description: Event-based monitoring and bounded restart for idle or blocked sessions.
type: LLM Prompt
title: "Fleet utilization"
resource: "prompt://dryvist/auto-ai-agent/instructions/agentsmd/rules/on-demand/fleet-utilization"
tags:
  - shared-instructions
  - agent-instructions
timestamp: "2026-11-22T03:07:43Z"
status: active
consumers:
  - dryvist/nix-ai
  - dryvist/nix-claude-code
render: { engine: literal, variables: [], frontmatter: strip }
source_history:
  - repository: jpe-ai-agents/ai-llm-prompts
    path: "auto-ai-agent/instructions/agentsmd/rules/on-demand/fleet-utilization.md"
    note: New rule.
---

# Fleet utilization

A session waits on an event with a background monitor, never on a timer. The delegate holds one monitor on each
domain owner's state, and one domain owner holds a monitor on the delegate. A session idle or blocked for 15
minutes gets one nudge; with no reply in 5 minutes it is restarted from its brief and report file.

Each worker keeps a `QUEUE` block at the top of its report file: ranked items, each with a check that answers
yes or no.
