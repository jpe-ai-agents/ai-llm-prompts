"""The clerk's guards keep a non-text filter out of the list call, scope a comment by its task, and never let a
denied project shadow another project with the same name. Each test runs the rendered DSL code node by title."""

import json
from pathlib import Path

import pytest
import yaml


_ROOT = Path(__file__).resolve().parents[2]
_DSL = _ROOT / "agents" / "dify" / "vikunja-clerk.dsl.yml"
_NODES = yaml.safe_load(_DSL.read_text())["workflow"]["graph"]["nodes"]


def _main(title):
    code = next(node["data"]["code"] for node in _NODES if node["data"].get("title") == title)
    namespace = {}
    exec(compile(code, title, "exec"), namespace)  # defines the node's functions only
    return namespace["main"]


def _list(**fields):
    intent = {"route": "vikunja", "operation": "list", "project_named": False, "category": None, **fields}
    return _main("Code guard")(json.dumps(intent), "", "", json.dumps(["200"]), json.dumps([]), "200", "shadow")


@pytest.mark.parametrize(
    ("fields", "expected"),
    [
        ({"filter": {"done": False}}, {"filter": "", "done": False, "search": ""}),
        ({"filter": {"search": "clerk"}}, {"filter": "", "done": None, "search": "clerk"}),
        ({"filter": {"assignee": "me"}}, {"filter": "", "done": None, "search": ""}),
        ({"filter": ["x"]}, {"filter": "", "done": None, "search": ""}),
        ({"filter": " priority >= 3 "}, {"filter": "priority >= 3", "done": None, "search": ""}),
        ({"filter": {"done": False, "search": "b"}, "done": True, "search": "a"}, {"filter": "", "done": True, "search": "a"}),
        ({"filter": {"done": "no"}}, {"filter": "", "done": None, "search": ""}),
    ],
    ids=["done-object", "search-object", "unknown-object", "list", "text", "top-level-wins", "non-boolean-done"],
)
def test_only_a_text_filter_reaches_the_list_call(fields, expected):
    result = _list(**fields)
    assert result["allowed"] is True, result["reason"]
    assert {key: result[key] for key in expected} == expected


@pytest.mark.parametrize("operation,extra", [("comment", {"comment": "A note"}), ("relate", {"other_task_id": 102})])
def test_a_task_write_needs_no_project_flag_in_the_first_guard(operation, extra):
    intent = {"route": "vikunja", "operation": operation, "task_id": 101, "category": None, **extra}
    result = _main("Code guard")(json.dumps(intent), "", "", json.dumps(["200"]), json.dumps([]), "200", "shadow")
    assert result["allowed"] is True, result["reason"]
    assert result["needs_write_check"] is True


def test_a_comment_is_scoped_by_its_task_in_the_write_guard():
    main = _main("Update project guard")
    intent = {"route": "vikunja", "operation": "comment", "task_id": 101, "comment": "A note", "category": None}
    plan = json.dumps({"operation": "comment", "task_id": "101", "comment": "A note"})
    task = [{"id": 101, "projectId": 200, "title": "A task"}]
    allowed = main(json.dumps(intent), "", "", "101", json.dumps(["200"]), json.dumps([]), "shadow", "", plan, task, None)
    assert allowed["allowed"] is True, allowed["reason"]
    denied = main(json.dumps(intent), "", "", "101", json.dumps(["200"]), json.dumps(["200"]), "shadow", "", plan, task, None)
    assert denied["allowed"] is False
    assert "denied" in denied["reason"]


@pytest.mark.parametrize("operation", ["create", "update"])
def test_a_create_or_update_still_needs_the_project_flag(operation):
    intent = {"route": "vikunja", "operation": operation, "title": "Probe", "task_id": 101, "category": None}
    result = _main("Code guard")(json.dumps(intent), "", "", json.dumps(["200"]), json.dumps([]), "200", "shadow")
    assert result["allowed"] is False
    assert result["reason"] == "Project scope is missing or ambiguous."


def _create_in_inbox(rows, denied):
    intent = {"route": "vikunja", "operation": "create", "title": "Probe", "project": "Inbox", "project_named": True, "category": None}
    return _main("Code guard")(json.dumps(intent), "", "", json.dumps(["201"]), json.dumps(denied), "201", "shadow", "", rows)


@pytest.mark.parametrize("ids", [(200, 201), (201, 200)], ids=["denied-first", "denied-last"])
def test_a_denied_project_does_not_shadow_one_with_the_same_name(ids):
    result = _create_in_inbox([{"id": pid, "title": "Inbox"} for pid in ids], ["200"])
    assert result["allowed"] is True, result["reason"]
    assert result["project_id"] == "201"


def test_a_name_that_only_a_denied_project_has_is_still_refused():
    result = _create_in_inbox([{"id": 200, "title": "Inbox"}], ["200"])
    assert result["allowed"] is False
    assert result["reason"] == "The target project is denied; deny wins over allow."
