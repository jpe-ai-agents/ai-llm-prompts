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

## Turns and context

Measure a fleet by turns times context per turn, read from the session transcripts. One overnight run of four
sessions took 13,000 turns at about 250k tokens each; most turns relayed or acknowledged a line of text.

- No relay. A fact goes from the session that learned it straight to the file or tracker that keeps it. No
  session forwards another session's status, and no clerk session exists only to post what others write.
- No acknowledgement. A message that needs no decision gets no reply.
- One report per chain. A worker reports when a chain ends or when it needs a ruling, not per step.
- Small sessions. A session restarts from its handoff file before each new chain, and at 150k tokens of context
  at the latest. Tracker and other single-tool writes go to a subagent, which starts with an empty context.
- The lead reads report files on its own monitor events. It does not copy them into a record of its own.
