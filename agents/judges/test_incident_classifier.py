"""Both rendered Vikunja guards embed and execute the same incident classifier."""

from pathlib import Path

import pytest
import yaml

from dify_nodes import node_main


_ROOT = Path(__file__).resolve().parents[2]
_WORKFLOWS = ("vikunja-clerk", "vikunja-triage")
_HELPER = (
    _ROOT / "agents" / "dify-src" / "helpers" / "incident_classifier.py"
).read_text().strip()


@pytest.mark.parametrize("workflow", _WORKFLOWS)
def test_rendered_guard_embeds_the_shared_classifier(workflow):
    source = yaml.safe_load((_ROOT / "agents" / f"{workflow}.yaml").read_text())
    rendered = yaml.safe_load((_ROOT / "agents" / "dify" / f"{workflow}.dsl.yml").read_text())
    source_guard = next(
        node["data"]["code"]
        for node in source["dify"]["workflow"]["graph"]["nodes"]
        if node["id"] == "guard"
    )
    rendered_guard = next(
        node["data"]["code"]
        for node in rendered["workflow"]["graph"]["nodes"]
        if node["id"] == "guard"
    )
    assert "__DIFY_HELPER_INCIDENT_CLASSIFIER__" in source_guard
    assert _HELPER in rendered_guard


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        (("Investigate an incident",), True),
        (("Review incidents",), True),
        (("Service OUTAGES",), True),
        (("Service is down",), True),
        (("Investigate breaches",), True),
        (("Review vulnerabilities",), True),
        (("Assess a vulnerability",), True),
        (("CVE report",), True),
        (("Review exploits",), True),
        (("Investigate a leak",), True),
        (("Rotate credentials",), True),
        (("Rotate a secret",), True),
        (("Security review",), True),
        (("Review weaknesses",), True),
        (("Account compromised",), True),
        (("Assess compromise",), True),
        (("Compromising behavior",), True),
        (("Schedule a planning meeting",), False),
        (("Download the incidentally named file",), False),
        (("Secretariat report",), False),
        (("Investigate a breach",), False),
        (("", None, 0), False),
        (("Ordinary task", {"category": "security"}), True),
        (({"security": "ordinary task"},), False),
        ((["maintenance", "outage"],), True),
        ((("maintenance", "leaks"),), True),
        ((["maintenance", "planning"],), False),
    ],
)
def test_rendered_guards_classify_the_same_samples(values, expected):
    for workflow in _WORKFLOWS:
        classifier = node_main(workflow, "guard").__globals__["has_incident_marker"]
        assert classifier(*values) is expected, workflow
