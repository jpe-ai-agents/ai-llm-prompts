---
type: LLM Prompt
title: "CI Failure Auto-Fix"
description: "Prompt for diagnosing and minimally fixing CI failures."
resource: "prompt://dryvist/automation/ai-workflows/ci-fix"
tags:
  - "automation"
  - "ai-workflows"
timestamp: "2026-11-20T13:20:00Z"
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
2. Rerun first only what failed in the failing job, to reproduce the failure: the tests its log names, or, for a job
   with no tests, the job's own failing command (lint, format, validate) exactly as the workflow runs it. A test or
   check the log does not name is out of scope, even when it fails here.
3. If that rerun passes, or cannot run with the repository's declared setup, stop. Change no file, and say in your
   final message what you ran and why the failure did not reproduce.
4. Fix the issue in the source files with your file-editing tools.
5. Run the repository's formatter on the files you changed (for example `tofu fmt`, `ruff format`, `prettier --write`)
   and keep its output.
6. Read the failing job in the repository's own CI definition (`.github/workflows/` and the CI structure below) and
   rerun the checks it ran, with the same commands. Run no lint that the failing job did not run. Finish only when
   each one exits 0. If a check cannot run here, name it and say why in your final message. A check you did not run
   is never assumed to pass.
7. Use only the repository's declared setup. Never install a system package (`apt-get install` or any other), and
   never fetch, build or install a dependency by hand: no `git clone` of a dependency, no copy into a collections or
   packages path. If a check needs a tool or dependency that is missing, stop and name the check and what is missing
   in your final message.
8. A file size or token limit failure is fixed by moving, not by removing. The total content after the change equals
   the content before; only its place changes:
   - move whole blocks, resources, variables or document sections into a new file next to the old one;
   - never delete a declaration, a test, a test case or a document section to get under the limit;
   - after the move, every reference must still resolve, and no declaration may be left unused;
   - when moved Ansible tasks carry their own tags, pull the new file in with `import_tasks`, never `include_tasks`,
     so the tags stay selectable with `--tags`;
   - read the comments around the moved block and keep every rule they state.
9. Never delete or weaken a test to make a check pass. Updating a golden value is allowed in one case: the pull request
   only bumps a pinned input (a dependency, action or prompt pin), and a golden or snapshot test fails because its stored
   value came from the old input. Then regenerate the stored value from the new input with the repository's own update
   command, or compute it the way the test does, and change nothing else in the test.
10. Do not run git or attempt to commit. Your file edits are committed to the PR branch automatically after you finish.

Only fix what the CI is complaining about. Do not refactor or improve unrelated code.

## Repository

${REPO_CONTEXT}

## CI Structure

${CI_STRUCTURE}

## Failure Logs

```text
${FAILURE_LOGS}
```
