"""Vikunja clerk tool replies reach each consumer whether Dify fills the tool node's text or its json output.

Dify 1.19.0 sends a JSON-shaped MCP reply to `json` and leaves `text` empty; a markdown reply goes to `text`.
The json output is [{"data": []}] when a reply held no JSON. Each test runs the rendered DSL code node by title.
"""

import json
import re
from pathlib import Path

import pytest
import yaml


_ROOT = Path(__file__).resolve().parents[2]
_DSL = _ROOT / "agents" / "dify" / "vikunja-clerk.dsl.yml"
_NODES = yaml.safe_load(_DSL.read_text())["workflow"]["graph"]["nodes"]
_TOOL_IDS = {"projects-tool", "preflight-tool", "other-read-tool", "update-tool", "readback-tool"}


def _node(title):
    return next(node["data"] for node in _NODES if node["data"].get("title") == title)


def _namespace(title):
    namespace = {}
    exec(compile(_node(title)["code"], title, "exec"), namespace)  # defines the node's functions only
    return namespace


_NO_DATA = [{"data": []}]


def test_tool_text_takes_whichever_output_holds_data():
    tool_text = _namespace("Read result")["tool_text"]
    assert tool_text("## ✅ Success\n\n1. **Inbox** (ID: 200)", _NO_DATA) == "## ✅ Success\n\n1. **Inbox** (ID: 200)"
    assert tool_text("", _NO_DATA) == ""
    assert tool_text(None, None) == ""
    assert json.loads(tool_text("", [{"id": 7, "title": "Clerk notes"}])) == [{"id": 7, "title": "Clerk notes"}]


def test_read_result_answers_a_json_reply_with_one_line_per_item():
    main = _namespace("Read result")["main"]
    result = main(text="", items=[{"id": 7, "title": "Clerk notes", "done": False}, {"id": 8, "title": "Done one", "done": True}])
    assert result == {"answer": "- ID 7: Clerk notes - open\n- ID 8: Done one - done"}


def test_read_result_unwraps_a_wrapped_task_list():
    main = _namespace("Read result")["main"]
    result = main(text="", items=[{"tasks": [{"id": 9, "title": "Inside"}]}])
    assert result == {"answer": "- ID 9: Inside"}


def test_read_result_reports_an_empty_reply_without_a_selector():
    main = _namespace("Read result")["main"]
    assert main(text="", items=_NO_DATA) == {"answer": "The read returned no data."}


def test_read_result_passes_a_markdown_reply_through():
    main = _namespace("Read result")["main"]
    assert main(text="## ✅ Success\n\nFound 1 task", items=_NO_DATA) == {"answer": "## ✅ Success\n\nFound 1 task"}


def test_code_guard_resolves_a_named_project_from_json_items():
    main = _namespace("Code guard")["main"]
    intent = {"route": "vikunja", "operation": "create", "title": "Probe", "project": "Inbox", "project_named": True, "category": None}
    result = main(json.dumps(intent), "", "", json.dumps(["200"]), json.dumps([]), "200", "shadow", "", [{"id": 200, "title": "Inbox"}])
    assert result["allowed"] is True, result["reason"]
    assert json.loads(result["preview"])["args"]["projectId"] == "200"


def test_an_unresolved_project_name_files_to_the_inbox():
    main = _namespace("Code guard")["main"]
    intent = {"route": "vikunja", "operation": "create", "title": "Probe", "project": "Unknown", "project_named": True, "category": None}
    result = main(json.dumps(intent), "", "", json.dumps(["200"]), json.dumps([]), "200", "shadow", "", [])
    assert result["allowed"] is True, result["reason"]
    assert json.loads(result["preview"])["args"]["projectId"] == "200"


def test_update_guard_reads_the_task_from_json_items():
    main = _namespace("Update project guard")["main"]
    intent = {"route": "vikunja", "operation": "update", "title": "New title", "project_named": False, "category": None}
    result = main(
        json.dumps(intent),
        "",
        "",
        "101",
        json.dumps(["200"]),
        json.dumps([]),
        "shadow",
        "",
        "",
        [{"id": 101, "projectId": 200, "title": "Old title"}],
        None,
    )
    assert result["allowed"] is True, result["reason"]
    assert json.loads(result["preview"])["args"]["id"] == "101"
    assert json.loads(result["preview"])["args"]["projectId"] == "200"


def test_update_guard_refuses_a_task_reply_with_no_data():
    main = _namespace("Update project guard")["main"]
    intent = {"route": "vikunja", "operation": "update", "title": "New title", "project_named": False, "category": None}
    result = main(json.dumps(intent), "", "", "101", json.dumps(["200"]), json.dumps([]), "shadow", "", "", _NO_DATA, None)
    assert result["allowed"] is False
    assert "could not be verified" in result["reason"]


def test_readback_target_takes_the_new_id_from_a_json_or_markdown_reply():
    main = _namespace("Readback target")["main"]
    assert main(write_text="", write_items=[{"id": 55, "title": "Probe"}], operation="create", task_id="") == {"readback_id": "55"}
    assert main(write_text="## ✅ Success\n\nCreated (ID: 56)", write_items=_NO_DATA, operation="create", task_id="") == {"readback_id": "56"}
    assert main(write_text="", write_items=_NO_DATA, operation="update", task_id="57") == {"readback_id": "57"}


def test_write_receipt_joins_the_summary_the_write_and_the_readback():
    main = _namespace("Write receipt")["main"]
    result = main(
        summary="Update task 5.",
        write_text="",
        write_items=[{"id": 5, "title": "Probe"}],
        readback_text="",
        readback_items=[{"id": 5, "title": "Probe", "done": False}],
    )
    assert result == {"answer": "Update task 5.\n\n- ID 5: Probe\n\nReadback:\n- ID 5: Probe - open"}


def test_every_consumer_of_a_tool_output_reads_both_text_and_json():
    for node in _NODES:
        data = node["data"]
        selectors = {}
        for variable in data.get("variables") or []:
            selector = variable.get("value_selector") or []
            if len(selector) == 2 and selector[0] in _TOOL_IDS:
                selectors.setdefault(selector[0], set()).add(selector[1])
        for tool_id, fields in selectors.items():
            assert fields == {"text", "json"}, f"{data.get('title')} reads {tool_id} via {sorted(fields)} only"


def test_no_answer_renders_a_tool_selector():
    for node in _NODES:
        data = node["data"]
        if data.get("type") != "answer":
            continue
        answer = str(data.get("answer", ""))
        assert not re.search(r"\{\{#[a-z0-9-]+\.(text|json)#\}\}", answer), f"{data.get('title')} renders a raw selector"
        for tool_id in _TOOL_IDS:
            assert f"{{{{#{tool_id}." not in answer, f"{data.get('title')} renders {tool_id} directly"


@pytest.mark.parametrize("title", ["Code guard", "Update project guard", "Readback target", "Read result", "Write receipt"])
def test_each_tool_consumer_carries_the_shared_helper(title):
    assert "def tool_text" in _node(title)["code"] or "def tool_answer" in _node(title)["code"]
