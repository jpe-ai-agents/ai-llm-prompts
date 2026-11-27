# Promptfoo agent evaluation matrix

The test generator loads every resolved agent definition's `eval_set` into the matrix. New definitions participate
automatically, and missing suites fail generation.

## Installation

Nothing needs a global install. Enter the development shell from the repository root; it provides Python and the test
libraries:

```sh
nix develop
```

The Promptfoo commands in this file fetch Node.js and a pinned Promptfoo themselves through `nix shell`. The clerk
acceptance runs also need `ask-agent` on the path.

## Usage

Run the generator from the repository root to check its case and assertion counts:

```sh
python3 agents/evals/promptfoo/generate.py
```

Suite `cases` lists may include `file://` references to shared YAML case lists, relative to the suite file.
The generator and authoring judges expand these references through the same loader. Text-agent boundary cases live
in `agents/evals/shared/text-boundaries.yaml`.

Each suite's static prefix contains its declared shared prefix when that file exists, its canonical prompt, the declared
tool list, canonical JSON output instructions and the names (never the values) of the outcome fields that suite scores. The prefix
is byte-identical across the suite's cases; case data comes last, in the user message. The generator includes
`shared/homelab.md` because the agent definitions declare that existing file.

Every eval suite case with an unskipped `expected_parse` also yields a `<agent>-parse` test. That test sends the raw caller input
to the Dify "Parse request" node prompt of that agent's own rendered DSL (`agents/dify/<agent>.dsl.yml`), composed
from the suite's shared prefix and canonical `agents/prompts/<agent>.md` prompt. It scores `expected-fields-match`
and `parse-json-schema-valid` (the checker in `agents/judges/parse-json-schema.py`).

A suite's top-level `expected_output_scoring` sets how `expected-output` scores: `field-credit` (the default) is the
share of expected keys that match, and `strict` is 1 only when every key matches. `vikunja-clerk` is `strict`.

`agents/evals/live/*.yaml` holds live regression questions. The generator does not read them. To run one, send each
`question` to the published app, fill `<TASK_ID>` and `<INBOX_ID>` from the run's inputs, and pass the case only when
`pass_pattern` matches and no `fail_patterns` entry matches. No runner ships with the set.

## Decision-model evaluations

The fixed labelled sets under `agents/evals/decision-models/` cover delegated-brief sensitivity and leak-scanner candidates.
Each suite uses the local OpenAI-compatible provider: set `EVAL_LOCAL_MODEL` to the alias under evaluation and `OPENAI_BASE_URL`
to the endpoint. Set `OPENAI_API_KEY` only if that endpoint requires it. When the model behind an alias changes, rerun both
suites against the same checked-in cases and keep the alias and resolved model revision with each report.

Each case carries its label as test metadata, and its assertion states what that label must never do. The safety gate
is the run filtered to the label that must never be let through; it passes only when Promptfoo exits 0.

Brief sensitivity uses the delegation hook's own prompt and reply contract. A `private` case fails when the reply holds
a `public` verdict. A `public` case passes only on a reply the hook would accept as `public`: one JSON object with
exactly `verdict` and `reason`. Run the gate, then the whole set, from the repository root:

```sh
nix --extra-experimental-features 'nix-command flakes' shell nixpkgs#nodejs_22 -c \
  npx -y promptfoo@0.118.14 eval -c agents/evals/decision-models/promptfooconfig-brief-sensitivity.yaml \
  --no-cache --no-progress-bar --filter-metadata label=private
nix --extra-experimental-features 'nix-command flakes' shell nixpkgs#nodejs_22 -c \
  npx -y promptfoo@0.118.14 eval -c agents/evals/decision-models/promptfooconfig-brief-sensitivity.yaml \
  --no-cache --no-progress-bar
```

In the whole-set run, a failed `public` case is a harmless brief kept off the public executors; the pass rate of the
`public-answered-public` metric is the share that got through.

Leak candidates: a `real` or `uncertain` case fails when the reply is `false_positive`, and a `false_positive` case
passes only on that exact reply. The gate is the `real` label:

```sh
nix --extra-experimental-features 'nix-command flakes' shell nixpkgs#nodejs_22 -c \
  npx -y promptfoo@0.118.14 eval -c agents/evals/decision-models/promptfooconfig-leak-candidates.yaml \
  --no-cache --no-progress-bar --filter-metadata label=real
```

## Clerk acceptance

The sets under `agents/evals/acceptance/` ask a deployed tracker clerk plain requests through `ask-agent`, the same
command every caller uses. `ask-agent` checks each reply against the clerk envelope schema; the cases assert allowed
operations, readback after writes, duplicate prevention where creation is allowed, and that refusals change nothing.
Cases run in order and one at a time. `vikunja-clerk.yaml` uses a writable project (`CLERK_PROJECT`) to create one
probe task. `youtrack-clerk.yaml` uses open issues set aside for acceptance runs (`CLERK_ISSUE`,
`CLERK_RELATED_ISSUE`) and the title of an existing knowledge article (`CLERK_ARTICLE`). `zammad-clerk.yaml` uses a
group set aside for acceptance runs (`CLERK_GROUP`) to create one probe ticket.

Set `CLERK` to the matching agent name, `CLERK_RUN` to a value unique to the run, and `ASK_AGENT_CALLER` to the
caller's label. Supply `CLERK_PROJECT` for Vikunja; `CLERK_ISSUE`, `CLERK_RELATED_ISSUE`, and `CLERK_ARTICLE` for
YouTrack; or `CLERK_GROUP` for Zammad as required by the selected set. One run passes when Promptfoo exits 0. Ten
runs of each set, each with a fresh probe value, from the repository root:

```sh
for clerk in vikunja-clerk youtrack-clerk zammad-clerk; do
  for run in $(seq 1 10); do
    CLERK="$clerk" CLERK_RUN="$(date +%s)-$clerk-$run" \
      nix --extra-experimental-features 'nix-command flakes' shell nixpkgs#nodejs_22 -c \
      npx -y promptfoo@0.118.14 eval -c agents/evals/acceptance/promptfooconfig-clerk.yaml \
      -t "agents/evals/acceptance/$clerk.yaml" -j 1 --no-cache --no-progress-bar || break 2
  done
done
```

## Providers

| Label | Candidate | Configuration |
| --- | --- | --- |
| `local` | an OpenAI-compatible endpoint | `EVAL_LOCAL_MODEL`, `OPENAI_BASE_URL`, `OPENAI_API_BASE_URL`, `OPENAI_API_KEY` |
| `luna` | Codex, through `scripts/promptfoo/luna.sh` | an operator-signed-in `codex` CLI |
| `go-kimi` | OpenCode Go, through `scripts/promptfoo/go-kimi.sh` | an operator-signed-in `opencode` CLI |
| `dify-live` | deployed Dify Workflow apps | `DIFY_BASE_URL` and each included app's `DIFY_APP_<NAME>` bearer value |

Cases scored only through `expected_behavior` use two graders: `behavior-rubric-judge-a` reads
`EVAL_JUDGE_A_BASE_URL` and `EVAL_JUDGE_A_MODEL`, and `behavior-rubric-judge-b` reads
`EVAL_JUDGE_B_BASE_URL` and `EVAL_JUDGE_B_MODEL`. A judge that needs a key sets `EVAL_JUDGE_A_API_KEY` or
`EVAL_JUDGE_B_API_KEY`; the grader sends it as a bearer header and never puts it on a command line. Keys come from the
runtime secret store, never from this repository. Both judges must be models outside the candidate set. Rubric scores
count only for cases where `not-truncated` passes.

The `dify-live` provider sends each case's input as the app's `text` start value and scores the returned JSON with the same
suite assertions. The generator reads each rendered app in `agents/dify/` and leaves out an app that is not a workflow app,
an app that starts from a trigger entry (the Service API cannot start it), and an app whose start form is not one `text`
input. It prints every excluded agent and its reason, and creates no `<agent>-parse` tests for this provider.

For deployed apps, set `DIFY_BASE_URL` and the `DIFY_APP_<NAME>` variables for included agents in the environment before
running Promptfoo. `<NAME>` is the agent name upper-cased with hyphens replaced by underscores. The app values are bearer
credentials and are read through Promptfoo's environment templating; do not put them in config files or command arguments.
Run the live provider from this directory with:

```sh
PROMPTFOO_PYTHON=python3 nix --extra-experimental-features 'nix-command flakes' \
  shell nixpkgs#nodejs_22 nixpkgs#yq-go nixpkgs#gomplate nixpkgs#python3 -c \
  npx -y promptfoo@0.118.14 eval -c promptfooconfig-dify-live.yaml --filter-providers dify-live \
  --no-cache --no-progress-bar -o /tmp/agent-evals-dify-live.json
```

Promptfoo records per-assertion metric scores in each result's `namedScores`. Print suite/provider/metric counts and mean
scores with (rubric scores are included only when `not-truncated` scored 1):

```sh
jq -r '
  .results.results
  | map(. as $result | (($result.namedScores // {}) | to_entries[]) | {
      suite: $result.vars.suite,
      provider: ($result.provider.label // $result.provider.id),
      metric: .key,
      score: .value
    } | select((.metric | startswith("behavior-rubric-") | not) or $result.namedScores["not-truncated"] == 1))
  | group_by([.suite, .provider, .metric])[]
  | [.[0].suite, .[0].provider, .[0].metric, (length | tostring), (map(.score) | add / length | tostring)]
  | @tsv
' /tmp/agent-evals-local.json
```

Print the share of result cases where both judges' pass values agree:

```sh
jq -r '
  [.results.results[]
   | [(.gradingResult.componentResults // [])[] | select(.assertion.metric == "behavior-rubric-judge-a") | .pass] as $judge_a
   | [(.gradingResult.componentResults // [])[] | select(.assertion.metric == "behavior-rubric-judge-b") | .pass] as $judge_b
   | select(($judge_a | length) > 0 and ($judge_b | length) > 0)
   | ($judge_a[0] == $judge_b[0])]
  | if length == 0 then "no paired judge results"
    else "agreement=\((map(select(.)) | length) / length)"
    end
' /tmp/agent-evals-local.json
```
