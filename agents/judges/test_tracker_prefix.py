"""Tracker agents share one system-prompt prefix and add only their own prompt file after it.

Report mode: mismatches are warnings until STRICT is set.
"""

import warnings
from pathlib import Path

import pytest
import yaml

from definitions import resolved_records

ROOT = Path(__file__).resolve().parents[2]
STRICT = False
TRACKER_PROFILE_PREFIX = "tracker-"


def prompt_body(path):
    """The text agent.tmpl's define "prompt" renders: frontmatter dropped, whitespace trimmed."""
    text = (ROOT / path).read_text()
    if text.startswith("---\n"):
        text = text.split("\n---\n", 1)[1]
    return text.strip()


def tracker_agents():
    for record in resolved_records():
        agent = record["agent"]
        profile = (ROOT / "agents" / "profiles" / f"{agent.get('extends', '')}.yaml")
        chain = [agent.get("extends") or ""]
        if profile.is_file():
            chain.append((yaml.safe_load(profile.read_text()) or {}).get("extends") or "")
        if any(name.startswith(TRACKER_PROFILE_PREFIX) for name in chain):
            yield agent


def system_prompts(name):
    dsl = yaml.safe_load((ROOT / "agents" / "dify" / f"{name}.dsl.yml").read_text())
    return [
        message["text"]
        for node in dsl["workflow"]["graph"]["nodes"]
        if node["data"].get("type") == "llm"
        for message in node["data"]["prompt_template"]
        if message.get("role") == "system"
    ]


def prefix_problems(cases):
    """cases: (name, shared_prefix_text, prompt_text, rendered_system_prompts). Returns readable problems."""
    problems = []
    prefixes = {shared for _, shared, _, _ in cases}
    if len(prefixes) > 1:
        problems.append(f"tracker agents declare {len(prefixes)} different shared prefixes")
    for name, shared, prompt, rendered in cases:
        if not rendered:
            problems.append(f"{name}: no system prompt rendered")
        for text in rendered:
            if not text.startswith(shared + "\n\n"):
                problems.append(f"{name}: system prompt does not start with the shared prefix")
            elif text != shared + "\n\n" + prompt:
                problems.append(f"{name}: system prompt holds text outside its shared prefix and prompt file")
    return problems


def report(problems, strict):
    if strict:
        assert not problems, "\n".join(problems)
    for problem in problems:
        warnings.warn(problem, stacklevel=2)


def test_tracker_agents_share_one_prefix_and_only_their_prompt():
    cases = [
        (agent["name"], prompt_body(agent["shared_prefix"]), prompt_body(agent["prompt"]), system_prompts(agent["name"]))
        for agent in tracker_agents()
    ]
    assert cases, "no agent extends a tracker profile"
    report(prefix_problems(cases), STRICT)


def test_strict_mode_fails_on_a_mismatch():
    cases = [
        ("a", "Shared.", "Duty A.", ["Shared.\n\nDuty A."]),
        ("b", "Shared.", "Duty B.", ["Shared.\n\nDuty B. Extra text."]),
    ]
    problems = prefix_problems(cases)
    assert problems == ["b: system prompt holds text outside its shared prefix and prompt file"]
    with pytest.raises(AssertionError):
        report(problems, strict=True)
    with pytest.warns(UserWarning):
        report(problems, strict=False)
