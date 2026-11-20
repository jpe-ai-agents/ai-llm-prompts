---
type: LLM Prompt
title: "CI Failure Auto-Fix"
description: "Prompt for diagnosing and minimally fixing CI failures."
resource: "prompt://dryvist/automation/ai-workflows/ci-fix"
tags:
  - "automation"
  - "ai-workflows"
timestamp: "2026-11-20T09:00:00Z"
status: active
consumers:
  - "JacobPEvans/.github-ai"
render:
  engine: envsubst
  variables:
    - "CI_STRUCTURE"
    - "FAILURE_LOGS"
    - "REPO_CONTEXT"
  frontmatter: strip
source_history:
  - repository: "JacobPEvans/.github-ai"
    path: ".github/prompts/ci-fix.md"
    commit: "fad075ea44873c3a38f6c7060a5212880a10207c"
---
# CI Failure Auto-Fix

You are fixing a CI failure. The repository, its CI structure and the failure logs are at the end of this prompt.

## Instructions

1. Analyze the failure logs to identify the root cause.
2. Run first only the tests that the failing job's log names, to reproduce the failure. A test the log does not name
   is out of scope, even when it fails here.
3. Fix the issue in the source files with your file-editing tools.
4. Run the repository's formatter on the files you changed (for example `tofu fmt`, `ruff format`, `prettier --write`)
   and keep its output.
5. Read the repository's own CI definition (`.github/workflows/` and the CI structure below) and run every check it
   runs for the files you changed, with the same commands. Run a repository-wide lint only when lint is the failing
   job. Finish only when each one exits 0. If a check cannot run here, name it and say why in your final message. A
   check you did not run is never assumed to pass.
6. Never run `apt-get install` or install any system package. If a check needs a tool that is missing, name the check
   and the tool in your final message instead.
7. A file size or token limit failure is fixed by moving, not by removing. The total content after the change equals
   the content before; only its place changes:
   - move whole blocks, resources, variables or document sections into a new file next to the old one;
   - never delete a declaration, a test, a test case or a document section to get under the limit;
   - after the move, every reference must still resolve, and no declaration may be left unused.
8. Never delete or weaken a test to make a check pass.
9. Do not run git or attempt to commit. Your file edits are committed to the PR branch automatically after you finish.

Only fix what the CI is complaining about. Do not refactor or improve unrelated code.

## Repository

${REPO_CONTEXT}

## CI Structure

${CI_STRUCTURE}

## Failure Logs

```text
${FAILURE_LOGS}
```
