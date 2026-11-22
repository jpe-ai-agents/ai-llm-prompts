---
name: rule-tiers
description: Index of the on-demand rule tier.
type: LLM Prompt
title: "Rule tiers"
resource: "prompt://dryvist/auto-ai-agent/instructions/agentsmd/rules/rule-tiers"
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
    path: "agentsmd/rules/rule-tiers.md"
    note: Migrated from the instruction repository.
---

# Rule tiers

`AGENTS.md`, `soul.md`, `operating-core.md`, `public-disclosure.md`, `agent-notifications.md` and this index load
every session. Other rules load by `paths:` or this activity index. Roles: `soul.md` is identity and tone only;
behavior rules go in `operating-core.md`; routing goes in `AGENTS.md`. Read the relevant on-demand file when you
begin that activity.

| When you are… | Read |
| --- | --- |
| Branching, PR, releasing | `git-flow.md` |
| Reviewing a pull request or a diff | `review-gate.md` |
| Writing or fixing a CI workflow, or a CI run failed | `ci-resilience.md` |
| Claiming a shared resource | `session-coordination.md` |
| Spawning subagents | `subagent-resilience.md` |
| Configuring deterministic recurring work | `loop-cadence.md` |
| Delegating, or acting after a denial | `delegation-trust.md` |
| Invoking another model or CLI | `model-delegation.md` for invocation; routing is in `AGENTS.md` |
| Orchestrating worker sessions | `fleet-utilization.md` |
| Running multi-repo work as a Claude project, or working as a project thread | `claude-projects.md` |
| Running a `/skill` | `skill-execution-integrity.md` |
| Side quest, deferred work, maintenance window | `task-tracking.md` |
| Outage or security weakness | `incident-management.md` |
| Changing live infra | `infrastructure-conventions.md` |
| Unattended converge, credential creation/move, or "not authenticated" | `secrets-separation.md` |
| Cloning/setting up a repo, starting a change | `workspace-conventions.md` |
| Choosing tools/subagent types | `tool-use.md` |
| OKF bundle | `okf.md` |
| Observability or data-feed change | `data-pipeline.md` |
| Editing renovate config | `dependency-automation.md` |
| Reading logs | `log-platform.md` |
| Authoring a skill, rule, hook, agent, or harness setting | `cost-aware-authoring.md` |
| Building or evaluating agents, skills, tools, or platform integrations | `agent-standards.md`, `agent-standards-platform.md`, and their source files: `agent-standards-sources.md`, `agent-standards-anthropic-sources.md`, `agent-standards-openai-sources.md`, `agent-standards-ecosystem-sources.md`, `agent-standards-platform-sources.md` |
| Designing an agent, prompt, job or routing rule that calls a local model | `local-llm-cache.md` |
| Merging a change to behavior, config, a name, a version, or an endpoint in any repo | the private documentation source's `docs-sync` skill — find the pages that name the changed repo or file and bring them back in line in the same session |

Machine-specific instructions: the operator's own `*.local.md` files, outside version control.
