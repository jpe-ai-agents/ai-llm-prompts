---
name: local-llm-cache
description: Designing an agent, prompt, job or routing rule that calls a local model — prompt cache rate target and the prompt shapes that keep the cache reusable.
type: LLM Prompt
title: "Local model prompt cache"
resource: "prompt://dryvist/auto-ai-agent/instructions/agentsmd/rules/on-demand/local-llm-cache"
tags:
  - shared-instructions
  - agent-instructions
timestamp: "2026-11-16T03:01:44Z"
status: active
consumers:
  - dryvist/nix-ai
  - dryvist/nix-claude-code
render: { engine: literal, variables: [], frontmatter: strip }
source_history: []
---

# Local model prompt cache

Read this before designing or changing an agent, a prompt, a scheduled job or a routing rule that calls a
locally served model.

## Two figures, read together

- **Token utilization**: tokens the machine produces over the most it can produce.
- **Prompt cache rate**: cached prompt tokens over received prompt tokens. Target: at least 80% on every local
  lane. A caller below 80% has a defect in how it builds its prompt; it is not a capacity problem.

A local engine computes every prompt token it cannot find in its cache, and that time is taken from
generating. A high cache rate is how a busy lane stays fast.

## Build prompts so the cache can be reused

1. **Stable first, variable last.** System text and tool definitions come first, byte-identical across runs
   of the same kind, in a fixed order. Nothing run-specific goes in them: no date or time, run id, repository,
   path, branch, user name or random id. Everything that changes per run goes last, in one block.
2. **A family shares its opening.** Agents of one family start with the same block, then the role-specific
   part, then the run part. Two instances of one agent differ only in the tail.
3. **Append, never rewrite.** A multi-turn loop only appends. Do not edit, reorder or summarise earlier
   turns in the middle of a run, and do not add a system message after the first turn.
4. **Fixed tools.** The tool list and its order stay the same within a run and across runs of the same kind.
   Limit tools per caller with a static grant, not per request.
5. **Same prefix back to back.** Order batch work so jobs with the same opening follow each other, and warm
   the opening once before a batch.
6. **No needless variation.** Do not change template or sampling settings that alter the rendered prompt
   between runs of the same kind.
7. **Honest context size.** A large unique context pushes other callers' entries out of the cache. Send what
   the step needs.

## Where a request should go

- Callers with a warm, shared opening (standing agents, loops, families of jobs) go to the local lane first.
- A one-off request with a large unique prompt and no shared opening leans to a cloud route when the local
  cache is under pressure, if its content may leave the environment. It would evict entries that many other
  calls reuse.
- Private content always stays local, whatever its cache behaviour.

## Measure and prove

- The engine's cached-token and prompt-token counters give the rate per lane; the router's per-caller
  counters give it per caller. A caller under 80% gets a prompt audit: find the first run-specific token.
- A change that adds or edits a prompt states the expected length of its shared opening, and is checked with
  two identical runs: the second must read almost all of its prompt from the cache.
