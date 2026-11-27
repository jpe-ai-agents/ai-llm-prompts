"""Rendered Hermes clerk souls carry the shared prefix, their own prompt and the envelope, and match the manifest."""

import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = json.loads((ROOT / "agents/hermes/manifest.json").read_text(encoding="utf-8"))
CLERKS = ["vikunja-clerk", "youtrack-clerk", "zammad-clerk"]


def _body(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8").split("\n---\n", 1)[1].strip()


@pytest.mark.parametrize("name", CLERKS)
def test_soul_is_prefix_then_prompt_then_envelope(name):
    soul = (ROOT / f"agents/hermes/{name}.soul.md").read_text(encoding="utf-8")
    homelab = _body("agents/prompts/shared/homelab.md")
    prompt = _body(f"agents/prompts/hermes/{name}.md")
    envelope = _body("agents/prompts/shared/clerk-envelope.md")
    assert soul.startswith(homelab)
    assert soul.index(prompt) < soul.index(envelope)
    assert soul.endswith(envelope + "\n")
    assert "{{" not in soul


def test_manifest_lists_every_soul_and_the_schema_with_matching_hashes():
    assert [entry["name"] for entry in MANIFEST] == sorted(["clerk-envelope-schema", *CLERKS])
    for entry in MANIFEST:
        digest = hashlib.sha256((ROOT / entry["path"]).read_bytes()).hexdigest()
        assert entry["sha256"] == digest, entry["path"]
