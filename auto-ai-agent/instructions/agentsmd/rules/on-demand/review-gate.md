---
name: review-gate
description: The AI Merge Gate check on the PR head is the only review verdict; first rubric line flags custom code and reuse; lanes and the queue read the verdict
type: LLM Prompt
title: "Review gate"
resource: "prompt://dryvist/auto-ai-agent/instructions/agentsmd/rules/on-demand/review-gate"
tags:
  - shared-instructions
  - agent-instructions
timestamp: "2026-11-15T07:15:00Z"
status: active
consumers:
  - dryvist/nix-ai
  - dryvist/nix-claude-code
render: { engine: literal, variables: [], frontmatter: strip }
source_history: []
---

# Review gate

Before any other review check, ask whether the change adds or edits custom code: a script, a hand-written
service unit, timer or scheduled job, or glue code. The last paragraph lists what is not custom code.

If it does, apply the tool-choice order in `AGENTS.md`. If a rung before writing code does the same,
the verdict is CHANGES and the finding names it.

If none does, the change must show what that rule requires and cite the repository owner's recorded approval.
Otherwise the verdict is CHANGES.

Then apply the DRY principle of the code review instructions to mechanisms as well as code. A second copy
of a mechanism that already exists, or a value hard-coded for one consumer that should be a parameter,
is CHANGES.

These are not custom code: configuration of existing software, including a unit or schedule that a maintained
package ships, a maintained tool's own plugin or module, and a test case that runs under the test framework
the repository already uses. A new test runner, harness, or helper script is custom code.

## The verdict

- The verdict is a check named `AI Merge Gate` on the PR head, posted by the reviewer App.
  The ruleset pins that App's id, so no other workflow or token can satisfy it.
- The check summary carries `model:`, `author_family:`, `head:`, and a last line
  `VERDICT: MERGE`, `VERDICT: CHANGES`, or `VERDICT: DEFERRED`.
- The reviewer model comes from a different family than the author. The author family comes from the bot
  identity or the `Assisted-by` trailer, which PR policy requires.
- A launch is one read-only review call with the standard brief, starting with the rubric above.

## Lanes and the queue

Lanes are defined in `git-flow.md`.

- Tiny and land-first: the check posts `VERDICT: DEFERRED` with a neutral conclusion before merge. The real
  review runs after merge, on the merged PR labeled `checks:deferred`, and posts MERGE or CHANGES.
- Normal and guarded: the verdict is MERGE or CHANGES before merge.
- Bot lane: the check posts `VERDICT: DEFERRED` with no model call, and no review follows.
- In the queue (`merge_group`), the verdict job makes no model call. It checks that the entry's head already
  has its verdict.

## Holds and writers

- `human:review` is the only hold. Agents and executors never add it.
- One writer at a time per PR: the CI-fix agent, the review responder and the conflict worker share one
  concurrency group and skip a PR that is in the queue. A push removes a PR from the queue.
