---
type: LLM Prompt
title: "AI Agents Configuration"
description: "Shared global agent instructions for AI Agents Configuration."
resource: "prompt://dryvist/auto-ai-agent/instructions/AGENTS"
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
  - repository: dryvist/ai-assistant-instructions
    path: "AGENTS.md"
    note: Migrated from the instruction repository.
---
# AI Agents Configuration

## Coding behavior

Identity and posture: `soul.md`. Use evidence, make reasonable assumptions, proceed, and surface only
assumptions/tradeoffs that affect action. Ship the simplest surgical fix matching existing style; define
verifiable success criteria, use the narrowest proof, and report exactly what passed/failed. Fix every
warning, error and lint finding for real; never silence, skip or bypass the check that raised it.

Tool choice — **no new custom scripts**. Stop at the first rung that works:
(1) existing flags, config, or an installed skill, command, plugin or MCP server; (2) a native platform or tool
feature; (3) a maintained third-party tool; (4) community content (collections, modules, presets,
hooks, Actions); (5) prior art: `/github-code-search` (thousands of hits is idiomatic, three is a
mistake), context7, registries; (6) a standardized public repo. Only then write code, naming why each rung failed;
delete or replace an existing script before editing it.

Git workflow: never edit on the default branch — start a worktree with `git town hack`. `develop` default branch →
[git-flow](agentsmd/rules/on-demand/git-flow.md): PRs target `develop` (squash-merge), `develop` → `main` by
merge commit only. Otherwise trunk flow. Always **atomic commits**, one fix/feature/section per commit. Load
the on-demand rule for the activity — `rule-tiers.md` is the index. Instruction-behavior changes are `feat:`/`fix:`,
never `docs:`.

Documentation/backup vault exemption: when a repository's root `AGENTS.md` explicitly declares it is a
documentation/backup vault (direct-to-default-branch commits, custom commit prefix, dedicated task tracker), those
repo-local overrides take precedence over global git-flow, worktree, and task-tracker defaults.

Writing voice: prose a person will read follows `~/.agents/voice.md` when that file exists.

Knowledge base: documentation follows [Open Knowledge Format](agentsmd/rules/on-demand/okf.md) — search before
editing, capture new knowledge after a change.

## Where things get written (routing law, no exceptions)

Execute end to end in one shot, routed per this table.
GitHub is public, **pull requests only**; a PR body fills the template — objective, approach, changes,
verification, related PRs as full URLs, trace line — never what was broken, an incident, or what's still weak.

| Content | Destination |
| --- | --- |
| Incidents, outages, security findings, weaknesses | the incident tracker |
| Private documentation, especially secret management | the private docs site |
| Everything else, including side quests and follow-ups | the task tracker — **never a GitHub issue** |

The operator's role map names each product ([example](agentsmd/docs/tool-role-map.example.md)).

Never put an incident narrative, security finding, credential/secret detail, unprovisioned identity, internal
topology, host name, or outage timeline in a GitHub issue, PR, comment, or commit message — "side quest" is
not an exemption.

Repo boundaries: `jpe-ai-agents/ai-llm-prompts` `auto-ai-agent/instructions` (rules, `AGENTS.md`, workflows),
`dryvist/nix-claude-code` `data/permissions` (tool permissions), `dryvist/claude-code-plugins` (commands,
skills, agents, hooks).

**Delegation routing (binding, the only routing statement).** The lead never does delegable work itself: it plans,
judges results, and merges, fanning every independent task out to subagents in parallel and keeping long-lived workers busy
([fleet-utilization.md](agentsmd/rules/on-demand/fleet-utilization.md)). Every other skill, rule, agent definition
and brief points here and never restates an executor order.

1. **A Claude session orchestrates; it never runs Claude subagents.** It plans, decides, gates, integrates, and
   reviews. No Claude subagent of any model (Haiku, Sonnet, Opus or Fable), no fork, and no teammate on the
   session's model. A spawn that no non-Claude executor takes is refused and logged; nothing runs.
2. **The delegation hook places every spawn.** No session, skill, rule, agent pin or brief picks an executor by
   name. Tags beat the hook's classifier: `[class: text]` sends self-contained text work, with every input in the
   prompt, to a local model; `[task: code] [repo: owner/repository]` marks coding work in that repository.
3. **The hook ranks dynamically.** Among the executors a task is eligible for, it picks the one with the most
   headroom against its pace, from live quota, price and peak data. No executor is a favourite in code or text;
   when the best subscription changes, nothing is edited and no person acts. Local models come first for small,
   checkable work. A failed local call is never just abandoned: a subagent finds what went wrong and what to improve.
4. **Executor kinds.**
   - **Router models through the harness.** Tool-using work runs in the headless Claude Code CLI (no Anthropic
     account) driving a router model: a local model, or a non-Claude subscription the router exposes through a CLI
     proxy where that provider's own terms allow it. Spawns from an interactive session run at the interactive
     priority tier, ahead of batch and scheduled work.
   - **Own-CLI executors.** ZCode always runs in its own CLI (the `zcode-job` sandbox), as does any subscription
     whose discount or peak benefit is tied to its CLI. Claude is never proxied.
   - **Codex runs Luna at `xhigh`.** Luna is the only Codex model and `xhigh` the only Codex
     effort. Every hook, wrapper, profile, script and brief passes both explicitly.
   - **Trust.** Private or sensitive work goes only to executors trusted with it (local models;
     Codex Luna). Public-sandbox executors take only definitely non-sensitive coding in public
     repositories; their output is a ready PR that is leak-scanned before merge and never auto-merged.
     Open-internet research runs only in a separate untrusted, internet-open container.
5. **Briefs are complete.** Follow `brief-delegates.md`, and give the full text of any file to create or test,
   plus the command that runs it. A refused or failed executor falls to the next eligible one and leaves a task.

Never send secrets, credentials, inventory, or incident content to any executor. Antigravity (`agy`) is a
second-opinion reviewer, not an executor. The `jpe-ai-delegation` plugin's hook and `delegation-ladder` skill
implement this statement; [model-delegation.md](agentsmd/rules/on-demand/model-delegation.md) holds the CLI procedure.
