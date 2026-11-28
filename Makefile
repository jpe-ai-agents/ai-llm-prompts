DIFY_OUTPUT ?= agents/dify
HERMES_OUTPUT ?= agents/hermes
AGENTS_ROOT ?= .
ROTATION_DRIVER_NAME ?= tier2-rotation
export ROTATION_DRIVER_NAME
INDEX_OUTPUT ?= $(AGENTS_ROOT)/agents/index.md
PROMPT_INDEX_OUTPUT ?= $(AGENTS_ROOT)/agents/prompts/index.md
PYTEST ?= python3 -m pytest
AUTOMATION_ROOT ?= automation
POLICY_PROMPT_OUTPUT ?= $(AUTOMATION_ROOT)
POLICY_RUBRICS := policy-gate security-review semantic-review leak-review code-review
GITHUB_AGENT_PROMPT_OUTPUT ?= $(AUTOMATION_ROOT)
GITHUB_AGENT_PROMPT_FILES := ai-workflows-docs-drift.prompt.yml ai-workflows-dep-review.md
.DEFAULT_GOAL := resolve-agents

.PHONY: render-policy-prompts check-policy-prompts $(addprefix render-policy-prompt-,$(POLICY_RUBRICS))
render-policy-prompts: $(addprefix render-policy-prompt-,$(POLICY_RUBRICS))

$(addprefix render-policy-prompt-,$(POLICY_RUBRICS)): render-policy-prompt-%:
	@mkdir -p "$(POLICY_PROMPT_OUTPUT)"
	@gomplate -c .="$(AUTOMATION_ROOT)/policy-gate-src/$*.yaml" \
		-t rubric="$(AUTOMATION_ROOT)/policy-gate-src/rubric.tmpl" \
		-i '{{ tmpl.Exec "rubric" (dict "name" "$*" "rubric" .) }}' \
		-o "$(POLICY_PROMPT_OUTPUT)/ai-workflows-$*.prompt.yml"

check-policy-prompts:
	@set -eu; output=$$(mktemp -d "$${TMPDIR:-/tmp}/policy-prompts.XXXXXX"); trap 'rm -rf "$$output"' EXIT; \
		mkdir "$$output/committed"; \
		cp $(foreach name,$(POLICY_RUBRICS),"$(AUTOMATION_ROOT)/ai-workflows-$(name).prompt.yml") "$$output/committed/"; \
		$(MAKE) --no-print-directory render-policy-prompts POLICY_PROMPT_OUTPUT="$$output/rendered"; \
		diff -ru "$$output/committed" "$$output/rendered"

.PHONY: render-github-agent-prompts check-github-agent-prompts render-github-agent-prompt-docs-drift render-github-agent-prompt-dep-review
render-github-agent-prompts: render-github-agent-prompt-docs-drift render-github-agent-prompt-dep-review

render-github-agent-prompt-docs-drift:
	@mkdir -p "$(GITHUB_AGENT_PROMPT_OUTPUT)"
	@gomplate -f "$(AUTOMATION_ROOT)/ai-workflows-docs-drift.prompt.yml.tmpl" \
		-o "$(GITHUB_AGENT_PROMPT_OUTPUT)/ai-workflows-docs-drift.prompt.yml"

render-github-agent-prompt-dep-review:
	@mkdir -p "$(GITHUB_AGENT_PROMPT_OUTPUT)"
	@gomplate -f "$(AUTOMATION_ROOT)/ai-workflows-dep-review.md.tmpl" \
		-o "$(GITHUB_AGENT_PROMPT_OUTPUT)/ai-workflows-dep-review.md"

check-github-agent-prompts:
	@set -eu; output=$$(mktemp -d "$${TMPDIR:-/tmp}/github-agent-prompts.XXXXXX"); trap 'rm -rf "$$output"' EXIT; \
		mkdir "$$output/committed"; \
		cp $(foreach file,$(GITHUB_AGENT_PROMPT_FILES),"$(AUTOMATION_ROOT)/$(file)") "$$output/committed/"; \
		$(MAKE) --no-print-directory render-github-agent-prompts GITHUB_AGENT_PROMPT_OUTPUT="$$output/rendered"; \
		diff -ru "$$output/committed" "$$output/rendered"

.PHONY: resolve-agents render-dify check-dify render-sim check-sim render-langflow check-langflow render-index check-index render-hermes check-hermes test
resolve-agents:
	@set -eu; cd "$(AGENTS_ROOT)"; for definition in agents/*.yaml; do \
		name=$$(basename "$$definition" .yaml); \
		test "$$(yq -r '.name' "$$definition")" = "$$name"; \
		gomplate -c .="$$definition" -t source="$(CURDIR)/agents/dify-src/agent.tmpl" \
			-i '{{ tmpl.Exec "resolve" . }}{{ "\n" }}'; \
	done

render-dify:
	@mkdir -p "$(DIFY_OUTPUT)"
	@set -eu; name="$$ROTATION_DRIVER_NAME"; \
		case "$$name" in \
			*[!a-z0-9-]*) printf 'ROTATION_DRIVER_NAME must use only lowercase letters, digits, and hyphens, got "%s"\n' "$$name" >&2; exit 1 ;; \
		esac; \
		if [ "$${#name}" -lt 3 ] || [ "$${#name}" -gt 63 ]; then \
			printf 'ROTATION_DRIVER_NAME must be 3 to 63 characters long, got "%s"\n' "$$name" >&2; exit 1; \
		fi
	@set -eu; output=$$(mktemp -d "$${TMPDIR:-/tmp}/agents.XXXXXX"); trap 'rm -rf "$$output"' EXIT; \
		$(MAKE) --no-print-directory resolve-agents > "$$output/definitions.jsonl"; \
		cd "$(AGENTS_ROOT)"; while IFS= read -r definition; do \
			printf '%s\n' "$$definition" | yq '.agent' > "$$output/agent.yaml"; \
			platform=$$(yq -er '.home_platform' "$$output/agent.yaml"); \
			[ "$$platform" = dify ] || continue; \
			name=$$(yq -r '.name' "$$output/agent.yaml"); \
			gomplate -c .="$$output/agent.yaml" -f "$(CURDIR)/agents/dify-src/agent.tmpl" -o "$(abspath $(DIFY_OUTPUT))/$$name.dsl.yml"; \
		done < "$$output/definitions.jsonl"; \
		jq -s 'map(.agent)' "$$output/definitions.jsonl" > "$$output/agents.json"; \
		gomplate -t driver="$(CURDIR)/agents/dify-src/rotation.tmpl" \
			-i '{{ tmpl.Exec "driver-metadata" . }}' > "$$output/driver.json"; \
		driver=$$(jq -r '.name' "$$output/driver.json"); \
		gomplate -c agents="$$output/agents.json" -f "$(CURDIR)/agents/dify-src/rotation.tmpl" \
			-o "$(abspath $(DIFY_OUTPUT))/$$driver.dsl.yml"; \
		jq -c '.[] | select(.home_platform == "dify") | {name, mode, tier, kind: "agent"}' \
			"$$output/agents.json" > "$$output/manifest.jsonl"; \
		jq -c . "$$output/driver.json" >> "$$output/manifest.jsonl"; \
		while IFS= read -r entry; do \
			name=$$(printf '%s\n' "$$entry" | jq -r '.name'); \
			hash=$$(sha256sum "$(abspath $(DIFY_OUTPUT))/$$name.dsl.yml"); \
			printf '%s\n' "$$entry" | jq --arg path "agents/dify/$$name.dsl.yml" \
				--arg sha256 "$${hash%% *}" '. + {path: $$path, sha256: $$sha256}'; \
		done < "$$output/manifest.jsonl" > "$$output/entries.jsonl"; \
		jq -s 'sort_by(.name)' "$$output/entries.jsonl" > "$(abspath $(DIFY_OUTPUT))/manifest.json"

check-dify: check-policy-prompts check-github-agent-prompts
	@set -eu; output=$$(mktemp -d "$${TMPDIR:-/tmp}/dify.XXXXXX"); trap 'rm -rf "$$output"' EXIT; \
		mkdir "$$output/committed"; \
		cp "$(AGENTS_ROOT)"/agents/dify/*.dsl.yml "$$output/committed/"; \
		cp "$(AGENTS_ROOT)/agents/dify/manifest.json" "$$output/committed/"; \
		$(MAKE) --no-print-directory render-dify DIFY_OUTPUT="$$output/rendered"; \
		diff -ru "$$output/committed" "$$output/rendered"

render-sim render-langflow: render-%:
	@mkdir -p "$(or $(SHADOW_OUTPUT),agents/$*)"
	@set -eu; output=$$(mktemp -d "$${TMPDIR:-/tmp}/agents.XXXXXX"); trap 'rm -rf "$$output"' EXIT; \
		$(MAKE) --no-print-directory resolve-agents > "$$output/definitions.jsonl"; \
		cd "$(AGENTS_ROOT)"; while IFS= read -r definition; do \
			printf '%s\n' "$$definition" | yq '.agent' > "$$output/agent.yaml"; \
			home=$$(yq -er '.home_platform' "$$output/agent.yaml"); \
			[ "$$home" = dify ] || continue; \
			shadows=$$(yq -r '(.shadows // []) | join(",")' "$$output/agent.yaml"); \
			case ",$$shadows," in *,$*,*) ;; *) continue ;; esac; \
			name=$$(yq -r '.name' "$$output/agent.yaml"); \
			reason=$$(gomplate -c .="$$output/agent.yaml" -t shadow="$(CURDIR)/agents/sim-src/shared.tmpl" \
				-i '{{ tmpl.Exec "shadow-eligibility" (dict "definition" . "runtime" "$*") }}'); \
			if [ -n "$$reason" ]; then printf 'SKIP | %s | %s | %s\n' '$*' "$$name" "$$reason"; continue; fi; \
			gomplate -c .="$$output/agent.yaml" -t dify="$(CURDIR)/agents/dify-src/agent.tmpl" \
				-t shadow="$(CURDIR)/agents/sim-src/shared.tmpl" \
				-f "$(CURDIR)/agents/$*-src/agent.tmpl" \
				-o "$(abspath $(or $(SHADOW_OUTPUT),agents/$*))/$$name.json"; \
		done < "$$output/definitions.jsonl"

check-sim check-langflow: check-%:
	@set -eu; output=$$(mktemp -d "$${TMPDIR:-/tmp}/$*.XXXXXX"); trap 'rm -rf "$$output"' EXIT; \
		$(MAKE) --no-print-directory render-$* SHADOW_OUTPUT="$$output/rendered"; \
		diff -ru "$(AGENTS_ROOT)/agents/$*" "$$output/rendered"

render-index:
	@set -eu; output=$$(mktemp -d "$${TMPDIR:-/tmp}/catalog.XXXXXX"); trap 'rm -rf "$$output"' EXIT; \
		$(MAKE) --no-print-directory resolve-agents > "$$output/definitions.jsonl"; \
		jq -s 'map(.agent) | sort_by(.name)' "$$output/definitions.jsonl" > "$$output/agents.json"; \
		gomplate -c agents="$$output/agents.json" -f "$(CURDIR)/agents/catalog-src/index.tmpl" -o "$(abspath $(INDEX_OUTPUT))"; \
		gomplate -c agents="$$output/agents.json" -f "$(CURDIR)/agents/catalog-src/prompts.tmpl" -o "$(abspath $(PROMPT_INDEX_OUTPUT))"

check-index:
	@set -eu; output=$$(mktemp -d "$${TMPDIR:-/tmp}/catalog.XXXXXX"); trap 'rm -rf "$$output"' EXIT; \
		$(MAKE) --no-print-directory render-index INDEX_OUTPUT="$$output/index.md" PROMPT_INDEX_OUTPUT="$$output/prompts.md"; \
		diff -u "$(AGENTS_ROOT)/agents/index.md" "$$output/index.md"; \
		diff -u "$(AGENTS_ROOT)/agents/prompts/index.md" "$$output/prompts.md"

# Hermes profile souls: every definition with agents/prompts/hermes/<name>.md, plus the shared base text
# (agents/hermes/base.md) and the envelope schema, each listed with its sha256 so a deployment pins a commit and
# verifies every file it downloads.
render-hermes:
	@mkdir -p "$(HERMES_OUTPUT)"
	@set -eu; output=$$(mktemp -d "$${TMPDIR:-/tmp}/hermes.XXXXXX"); trap 'rm -rf "$$output"' EXIT; \
		$(MAKE) --no-print-directory resolve-agents > "$$output/definitions.jsonl"; \
		cd "$(AGENTS_ROOT)"; : > "$$output/entries.jsonl"; \
		while IFS= read -r definition; do \
			printf '%s\n' "$$definition" | yq '.agent' > "$$output/agent.yaml"; \
			name=$$(yq -r '.name' "$$output/agent.yaml"); \
			[ -f "agents/prompts/hermes/$$name.md" ] || continue; \
			gomplate -c .="$$output/agent.yaml" -t dify="$(CURDIR)/agents/dify-src/agent.tmpl" \
				-f "$(CURDIR)/agents/hermes-src/soul.tmpl" -o "$(abspath $(HERMES_OUTPUT))/$$name.soul.md"; \
			hash=$$(sha256sum "$(abspath $(HERMES_OUTPUT))/$$name.soul.md"); \
			if [ "$$(yq -r 'has("hermes")' "$$output/agent.yaml")" = true ]; then \
				hermes=$$(yq -c '.hermes' "$$output/agent.yaml"); \
				jq -cn --arg name "$$name" --arg path "agents/hermes/$$name.soul.md" --arg sha256 "$${hash%% *}" \
					--argjson hermes "$$hermes" \
					'{name: $$name, path: $$path, sha256: $$sha256, tools: $$hermes.tools, write_tools: $$hermes.write_tools, caps: $$hermes.caps}' \
					>> "$$output/entries.jsonl"; \
			else \
				jq -cn --arg name "$$name" --arg path "agents/hermes/$$name.soul.md" --arg sha256 "$${hash%% *}" \
					'{name: $$name, path: $$path, sha256: $$sha256}' >> "$$output/entries.jsonl"; \
			fi; \
		done < "$$output/definitions.jsonl"; \
		gomplate -t dify="$(CURDIR)/agents/dify-src/agent.tmpl" \
			-i '{{ tmpl.Exec "prompt" "agents/prompts/shared/base.md" }}{{ "\n" }}' \
			-o "$(abspath $(HERMES_OUTPUT))/base.md"; \
		hash=$$(sha256sum "$(abspath $(HERMES_OUTPUT))/base.md"); \
		jq -cn --arg name "base" --arg path "agents/hermes/base.md" --arg sha256 "$${hash%% *}" \
			'{name: $$name, path: $$path, sha256: $$sha256}' >> "$$output/entries.jsonl"; \
		hash=$$(sha256sum agents/schemas/clerk-envelope.schema.json); \
		jq -cn --arg sha256 "$${hash%% *}" \
			'{name: "clerk-envelope-schema", path: "agents/schemas/clerk-envelope.schema.json", sha256: $$sha256}' \
			>> "$$output/entries.jsonl"; \
		jq -s 'sort_by(.name)' "$$output/entries.jsonl" > "$(abspath $(HERMES_OUTPUT))/manifest.json"

check-hermes:
	@set -eu; output=$$(mktemp -d "$${TMPDIR:-/tmp}/hermes.XXXXXX"); trap 'rm -rf "$$output"' EXIT; \
		$(MAKE) --no-print-directory render-hermes HERMES_OUTPUT="$$output/rendered"; \
		diff -ru "$(AGENTS_ROOT)/agents/hermes" "$$output/rendered"

.PHONY: acceptance-sets
ACCEPTANCE_RUNS := 10
ACCEPTANCE_SETS = vikunja-clerk.yaml youtrack-clerk.yaml zammad-clerk.yaml vikunja-triage.yaml vikunja-nightly.yaml vikunja-windows.yaml
ACCEPTANCE_SUFFIX = $(if $(ACCEPTANCE_PUBLIC),,-candidate-$(CANDIDATE_MODEL))
ACCEPTANCE_UNTRUSTED_CLERK = $(if $(ACCEPTANCE_PUBLIC),vikunja-clerk,vikunja-clerk-untrusted-candidate-$(CANDIDATE_MODEL))
ACCEPTANCE_UNTRUSTED_ENV = $(if $(ACCEPTANCE_PUBLIC),ASK_AGENT_TOKEN="$$ACCEPTANCE_UNTRUSTED_TOKEN",)
acceptance-sets:
	@# shortcut: Promptfoo help is unavailable offline; --filter-pattern is assumed to match TestCase descriptions for the untrusted one-case shard.
	@# shortcut: --output JSON-path support is unconfirmed; suite is the set loop and result fields are assumed to be TestCase.id/description and results[].success.
	@set -eu; \
		$(if $(ACCEPTANCE_PUBLIC),: "$${ACCEPTANCE_UNTRUSTED_TOKEN:?ACCEPTANCE_UNTRUSTED_TOKEN is required with ACCEPTANCE_PUBLIC}",: "$${CANDIDATE_MODEL:?CANDIDATE_MODEL is required}"); \
		: "$${ASK_AGENT_CALLER:?ASK_AGENT_CALLER is required}"; \
		output=$$(mktemp -d "$${TMPDIR:-/tmp}/acceptance-sets.XXXXXX"); \
		trap 'rm -rf "$$output"' EXIT; \
		outcomes="$$output/outcomes.jsonl"; : > "$$outcomes"; \
		for test_file in $(ACCEPTANCE_SETS); do \
			suite=$${test_file%.yaml}; \
			clerk="$$suite$(ACCEPTANCE_SUFFIX)"; \
			for run in $$(seq 1 $(ACCEPTANCE_RUNS)); do \
				run_id="$$(date -u +%Y%m%dT%H%M%SZ)-$$-$$suite-$$run"; \
				if [ "$$suite" = vikunja-clerk ]; then \
					CLERK="$$clerk" CLERK_RUN="$$run_id" nix develop -c npx promptfoo eval \
						--config agents/evals/acceptance/promptfooconfig-clerk.yaml \
						--tests "agents/evals/acceptance/$$test_file" \
						--filter-pattern '^(?!untrusted-caller-cannot-read$$)' \
						--output "$$output/$$suite-$$run.json"; \
					jq -c --arg suite "$$suite" '(.results | if type == "array" then . elif type == "object" then (.results // []) else [] end)[] | {suite: $$suite, case: ((.testCase.id // .testCase.metadata.id // .testCase.description // .testCase.vars.case_id // .vars.case_id // .vars.description // "") | tostring), success: (.success == true)}' \
						"$$output/$$suite-$$run.json" >> "$$outcomes"; \
					$(ACCEPTANCE_UNTRUSTED_ENV) CLERK=$(ACCEPTANCE_UNTRUSTED_CLERK) CLERK_RUN="$$run_id" nix develop -c npx promptfoo eval \
						--config agents/evals/acceptance/promptfooconfig-clerk.yaml \
						--tests "agents/evals/acceptance/$$test_file" \
						--filter-pattern '^untrusted-caller-cannot-read$$' \
						--output "$$output/$$suite-untrusted-$$run.json"; \
					jq -c --arg suite "$$suite" '(.results | if type == "array" then . elif type == "object" then (.results // []) else [] end)[] | {suite: $$suite, case: ((.testCase.id // .testCase.metadata.id // .testCase.description // .testCase.vars.case_id // .vars.case_id // .vars.description // "") | tostring), success: (.success == true)}' \
						"$$output/$$suite-untrusted-$$run.json" >> "$$outcomes"; \
				else \
					CLERK="$$clerk" CLERK_RUN="$$run_id" nix develop -c npx promptfoo eval \
						--config agents/evals/acceptance/promptfooconfig-clerk.yaml \
						--tests "agents/evals/acceptance/$$test_file" \
						--output "$$output/$$suite-$$run.json"; \
					jq -c --arg suite "$$suite" '(.results | if type == "array" then . elif type == "object" then (.results // []) else [] end)[] | {suite: $$suite, case: ((.testCase.id // .testCase.metadata.id // .testCase.description // .testCase.vars.case_id // .vars.case_id // .vars.description // "") | tostring), success: (.success == true)}' \
						"$$output/$$suite-$$run.json" >> "$$outcomes"; \
				fi; \
			done; \
		done; \
		nix develop -c python3 -c 'import json, sys; from pathlib import Path; import yaml; sys.path.insert(0, "agents/judges"); from acceptance_bar import passes_bar; suites = ("vikunja-clerk", "youtrack-clerk", "zammad-clerk", "vikunja-triage", "vikunja-nightly", "vikunja-windows"); events = [json.loads(line) for line in Path(sys.argv[1]).read_text(encoding="utf-8").splitlines() if line]; overall = True; root = Path("agents/evals/acceptance"); exec("for suite in suites:\n cases = yaml.safe_load((root / (suite + \\\".yaml\\\")).read_text(encoding=\\\"utf-8\\\"))\n safety = {case[\\\"id\\\"]: [] for case in cases if case[\\\"metadata\\\"][\\\"kind\\\"] == \\\"safety\\\"}\n quality = {case[\\\"id\\\"]: [] for case in cases if case[\\\"metadata\\\"][\\\"kind\\\"] == \\\"quality\\\"}\n all_cases = safety | quality\n for event in events:\n  if event[\\\"suite\\\"] == suite and event[\\\"case\\\"] in all_cases:\n   all_cases[event[\\\"case\\\"]].append(event[\\\"success\\\"] is True)\n for case_id, results in all_cases.items():\n  print(\\\"{} {}: {}/10\\\".format(suite, case_id, sum(results)))\n quality_pass = sum(sum(results) for results in quality.values())\n quality_total = len(quality) * 10\n print(\\\"{} quality: {}/{}\\\".format(suite, quality_pass, quality_total))\n passed = passes_bar(safety, quality)\n print(\\\"{}: {}\\\".format(suite, \\\"PASS\\\" if passed else \\\"FAIL\\\"))\n overall = overall and passed"); print("overall: {}".format("PASS" if overall else "FAIL")); sys.exit(0 if overall else 1)' "$$outcomes"

test: check-dify check-sim check-langflow check-index check-hermes
	$(PYTEST) -q agents/judges
