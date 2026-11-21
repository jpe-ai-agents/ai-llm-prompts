"""The clerk's project-find operation answers from the project list the workflow fetched, and makes no task call."""

import json
from pathlib import Path

import pytest
import yaml


_ROOT = Path(__file__).resolve().parents[2]
_DSL = _ROOT / "agents" / "dify" / "vikunja-clerk.dsl.yml"
_MARKDOWN = "## ✅ Success\n\nFound 2 projects\n\n1. **Inbox** (ID: 200)\n2. **Example Area** (ID: 201)\n"
_ITEMS = [{"id": 200, "title": "Inbox"}, {"id": 201, "title": "Example Area"}]


def _guard():
    nodes = yaml.safe_load(_DSL.read_text())["workflow"]["graph"]["nodes"]
    code = next(node["data"]["code"] for node in nodes if node["data"].get("title") == "Code guard")
    namespace = {}
    exec(compile(code, "Code guard", "exec"), namespace)  # defines the node's functions only
    return namespace["main"]


def _find(project, projects_text="", projects_items=None):
    intent = {"route": "vikunja", "operation": "project-find", "project_named": project is not None, "project": project, "category": None}
    return _guard()(json.dumps(intent), "", "", json.dumps(["200"]), json.dumps([]), "200", "live", projects_text, projects_items)


@pytest.mark.parametrize(
    "projects_text,projects_items",
    [(_MARKDOWN, None), ("", _ITEMS)],
    ids=["markdown-reply", "json-reply"],
)
def test_a_named_project_is_answered_with_its_id(projects_text, projects_items):
    result = _find("Inbox", projects_text, projects_items)
    assert result["allowed"] is True, result["reason"]
    assert result["project_answer"] == 'Project "Inbox" has ID 200.'


def test_a_name_match_ignores_case():
    assert _find("inbox", _MARKDOWN)["project_answer"] == 'Project "Inbox" has ID 200.'


def test_visible_projects_are_listed_when_no_name_is_asked():
    answer = _find(None, _MARKDOWN)["project_answer"]
    assert answer == "Visible projects:\n- Inbox (ID: 200)\n- Example Area (ID: 201)"


def test_an_unknown_name_is_reported_not_guessed():
    result = _find("Nowhere", _MARKDOWN)
    assert result["project_answer"] == 'No project named "Nowhere" is in the project list.'
    assert "200" not in result["project_answer"]


def test_an_empty_project_list_says_no_project_was_checked():
    assert _find("Inbox", "")["project_answer"] == "No projects were returned, so no project was checked."


def test_a_full_page_of_projects_says_a_later_project_may_be_missing():
    rows = [{"id": index, "title": f"Project {index}"} for index in range(1, 51)]
    answer = _find("Late one", "", rows)["project_answer"]
    assert "at most 50 projects" in answer


@pytest.mark.parametrize("project", ["Inbox", None])
def test_project_find_makes_no_task_call(project):
    result = _find(project, _MARKDOWN)
    assert result["read_operation"] == ""
    assert result["dispatch"] is False
    assert result["preview"] == ""
    assert result["needs_write_check"] is False
