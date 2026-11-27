"""The shared clerk reply envelope: the schema validators pin and the fragment the clerks read agree."""

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((ROOT / "agents/schemas/clerk-envelope.schema.json").read_text(encoding="utf-8"))
VALIDATOR = Draft202012Validator(SCHEMA)

READ = {"status": "ok", "outcome": "Found one task.", "ids": ["9771"],
        "items": [{"id": "9771", "title": "Slow tests"}], "readback": None, "error": None}
WRITE = {"status": "ok", "outcome": "Added the comment.", "ids": ["9771"], "items": [],
         "readback": {"comment": "Measured again today."}, "error": None}
REFUSED = {"status": "refused", "outcome": "Deleting is not allowed; nothing changed.", "ids": [], "items": [],
           "readback": None, "error": {"code": "no-delete", "message": "I never delete tasks."}}


def test_schema_is_valid_draft_2020_12():
    Draft202012Validator.check_schema(SCHEMA)


@pytest.mark.parametrize("envelope", [READ, WRITE, REFUSED], ids=["read", "write", "refused"])
def test_valid_envelopes_pass(envelope):
    assert not list(VALIDATOR.iter_errors(envelope))


def _changed(base, change):
    envelope = copy.deepcopy(base)
    change(envelope)
    return envelope


@pytest.mark.parametrize(
    "envelope",
    [
        _changed(READ, lambda e: e.pop("readback")),
        _changed(READ, lambda e: e.update(extra=1)),
        _changed(READ, lambda e: e.update(status="stop")),
        _changed(READ, lambda e: e.update(error={"code": "x", "message": "y"})),
        _changed(REFUSED, lambda e: e.update(error=None)),
        _changed(READ, lambda e: e.update(ids=[9771])),
        _changed(READ, lambda e: e.update(items=[{"id": "9771"}])),
    ],
    ids=["missing-key", "extra-key", "bad-status", "ok-with-error", "refused-without-error", "integer-id",
         "item-without-title"],
)
def test_invalid_envelopes_fail(envelope):
    assert list(VALIDATOR.iter_errors(envelope))


def test_fragment_names_every_key_and_status():
    text = (ROOT / "agents/prompts/shared/clerk-envelope.md").read_text(encoding="utf-8")
    body = text.split("\n---\n", 1)[1]
    for word in [*SCHEMA["required"], *SCHEMA["properties"]["status"]["enum"]]:
        assert word in body, word
