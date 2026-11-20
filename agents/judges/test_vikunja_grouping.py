"""Exercises the rendered Vikunja batching, Dataset API, retrieval, and shadow guard nodes."""

import json
import urllib.parse
import urllib.request
from pathlib import Path

import pytest
import yaml


_ROOT = Path(__file__).resolve().parents[2]
_DSL = _ROOT / "agents" / "dify" / "vikunja-triage.dsl.yml"


def _nodes():
    graph = yaml.safe_load(_DSL.read_text())["workflow"]["graph"]
    return {node["id"]: node["data"] for node in graph["nodes"]}


def _namespace(node_id):
    namespace = {}
    source = _nodes()[node_id]["code"]
    exec(compile(source, f"vikunja-triage:{node_id}", "exec"), namespace)
    return namespace


class _Response:
    def __init__(self, payload):
        self._body = json.dumps(payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return self._body


def _install_api(monkeypatch, namespace, route):
    requests = []

    class _Opener:
        def open(self, request, timeout=None):
            requests.append(request)
            assert timeout == 2
            return _Response(route(request))

    def build_opener(*handlers):
        assert any(
            isinstance(handler, urllib.request.ProxyHandler)
            and handler.proxies == {}
            for handler in handlers
        )
        assert any(isinstance(handler, namespace["NoRedirect"]) for handler in handlers)
        return _Opener()

    monkeypatch.setattr(urllib.request, "build_opener", build_opener)
    return requests


def _request_path(request):
    return urllib.parse.urlsplit(request.full_url).path


def _request_json(request):
    return json.loads(request.data) if request.data else None


def test_cursor_covers_remainder_batch_once_per_full_cycle():
    namespace = _namespace("batch")
    refs = [
        {"task_index": i, "id": str(i + 1)}
        for i in (8, 1, 9, 0, 3, 5, 2, 7, 4, 6)
    ]

    runs = [namespace["cursor"](refs, str(slot * 600), "4") for slot in range(3)]
    batches = [batch for batch, _, _, _ in runs]
    assert [index for _, index, _, _ in runs] == [0, 1, 2]
    assert [count for _, _, count, _ in runs] == [3, 3, 3]
    assert [len(batch) for batch in batches] == [4, 4, 2]
    flattened = [ref["id"] for batch in batches for ref in batch]
    assert flattened == [str(i) for i in range(1, 11)]
    assert len(flattened) == len(set(flattened))


def test_batch_node_sends_only_selected_tasks_to_triage():
    main = _namespace("batch")["main"]
    refs = [{"task_index": i, "id": str(i + 1)} for i in range(9)]
    tasks = [{"task_index": i, "title": f"Task {i}"} for i in range(9)]

    result = main(json.dumps(refs), json.dumps({"timestamp": "t", "tasks": tasks}), "600", "4")

    assert result["batch_index"] == 1
    assert result["batch_count"] == 3
    assert [ref["id"] for ref in result["batch_refs"]] == ["5", "6", "7", "8"]
    assert [ref["id"] for ref in result["selected_group_refs"]] == ["5", "6", "7", "8"]
    assert result["selected_group_refs"][0]["title"] == "Task 4"
    assert len(result["all_group_refs"]) == len(refs)
    assert [task["task_index"] for task in json.loads(result["model_tasks"])["tasks"]] == [4, 5, 6, 7]


def test_index_sync_creates_dataset_documents_and_polls_status(monkeypatch):
    namespace = _namespace("index_sync")
    dataset_id = "00000000-0000-0000-0000-000000000001"
    batch_id = "batch-7"
    refs = [{"id": "7", "task_index": 0, "title": "Task title", "description": "Task body"}]

    def route(request):
        path = _request_path(request)
        method = request.get_method()
        if path == "/v1/datasets" and method == "GET":
            assert urllib.parse.parse_qs(urllib.parse.urlsplit(request.full_url).query)["keyword"] == ["tracker-open-items"]
            return {"data": [], "has_more": False, "limit": 100, "total": 0, "page": 1}
        if path == "/v1/datasets" and method == "POST":
            return {"id": dataset_id, "name": "tracker-open-items"}
        if path == f"/v1/datasets/{dataset_id}/documents" and method == "GET":
            return {"data": [], "has_more": False, "limit": 100, "total": 0, "page": 1}
        if path == f"/v1/datasets/{dataset_id}/document/create-by-text" and method == "POST":
            return {"document": {"id": "doc-7", "name": "vikunja:7"}, "batch": batch_id}
        if path == f"/v1/datasets/{dataset_id}/documents/{batch_id}/indexing-status":
            return {"data": [{"id": "doc-7", "indexing_status": "completed"}]}
        if path == f"/v1/datasets/{dataset_id}/retrieve":
            return {"records": []}
        raise AssertionError(f"unexpected request: {request.full_url}")

    requests = _install_api(monkeypatch, namespace, route)
    result = namespace["main"](
        "https://dify.example/v1", "dataset-key", "tracker-open-items", "provider", "embed-model", refs
    )

    assert sum(_request_path(request).endswith("/document/create-by-text") for request in requests) == 1
    assert result["pending_count"] == 0
    assert result["grouping_error"] == ""
    assert [_request_path(request) for request in requests] == [
        "/v1/datasets",
        "/v1/datasets",
        f"/v1/datasets/{dataset_id}/documents",
        f"/v1/datasets/{dataset_id}/document/create-by-text",
        f"/v1/datasets/{dataset_id}/documents/{batch_id}/indexing-status",
        f"/v1/datasets/{dataset_id}/retrieve",
    ]
    assert all(request.get_header("Authorization") == "Bearer dataset-key" for request in requests)
    create_dataset = _request_json(requests[1])
    assert create_dataset == {
        "name": "tracker-open-items",
        "indexing_technique": "high_quality",
        "embedding_model_provider": "provider",
        "embedding_model": "embed-model",
    }
    create_document = _request_json(requests[3])
    assert create_document == {"name": "vikunja:7", "text": "Task title\n\nTask body"}
    assert result["group_inputs"][0]["id"] == "7"
    assert result["group_inputs"][0]["error"] == ""
    assert json.loads(result["theme_inputs"][0]) == [
        {"index": 0, "title": "Task title", "description": "Task body"}
    ]


def test_index_sync_updates_exact_document_name_and_needs_no_embedding_env(monkeypatch):
    namespace = _namespace("index_sync")
    dataset_id = "00000000-0000-0000-0000-000000000001"
    document_id = "00000000-0000-0000-0000-000000000007"

    def route(request):
        path = _request_path(request)
        if path == "/v1/datasets":
            return {"data": [{"id": dataset_id, "name": "tracker-open-items"}], "has_more": False}
        if path == f"/v1/datasets/{dataset_id}/documents":
            return {
                "data": [
                    {"id": "wrong", "name": "vikunja:70"},
                    {"id": document_id, "name": "vikunja:7"},
                ],
                "has_more": False,
            }
        if path == f"/v1/datasets/{dataset_id}/documents/{document_id}/update-by-text":
            return {"document": {"id": document_id, "name": "vikunja:7"}, "batch": "update-batch"}
        if path == f"/v1/datasets/{dataset_id}/documents/update-batch/indexing-status":
            return {"data": [{"id": document_id, "indexing_status": "completed"}]}
        if path == f"/v1/datasets/{dataset_id}/retrieve":
            return {"records": []}
        raise AssertionError(f"unexpected request: {request.full_url}")

    requests = _install_api(monkeypatch, namespace, route)
    result = namespace["main"](
        "https://dify.example/v1",
        "dataset-key",
        "tracker-open-items",
        "",
        "",
        [{"id": "7", "task_index": 0, "title": "Updated", "description": "Body"}],
    )

    assert sum(_request_path(request).endswith("/update-by-text") for request in requests) == 1
    assert [_request_path(request) for request in requests].count(
        f"/v1/datasets/{dataset_id}/documents/{document_id}/update-by-text"
    ) == 1
    assert not any(_request_path(request) == "/v1/datasets" and request.get_method() == "POST" for request in requests)


def test_missing_embedding_configuration_is_a_grouping_error(monkeypatch):
    namespace = _namespace("index_sync")

    def route(request):
        assert _request_path(request) == "/v1/datasets"
        return {"data": [], "has_more": False}

    requests = _install_api(monkeypatch, namespace, route)
    result = namespace["main"](
        "https://dify.example/v1",
        "dataset-key",
        "tracker-open-items",
        "",
        "",
        [{"id": "7", "task_index": 0}],
    )

    assert len(requests) == 1
    assert result["group_inputs"] == []
    assert result["theme_inputs"] == []
    assert result["grouping_error"] == "Embedding provider and model are required to create the grouping dataset"


def test_retrieval_filters_floor_missing_scores_self_and_unknown_names(monkeypatch):
    namespace = _namespace("index_sync")
    refs = [
        {"id": "1", "task_index": 0, "title": "Current", "description": "A" * 300},
        {"id": "2", "task_index": 1, "title": "Candidate two", "description": "Useful"},
        {"id": "3", "task_index": 2, "title": "Candidate three", "description": "Nearby"},
        {"id": "8", "task_index": 3, "title": "Candidate eight", "description": "Boundary"},
        {"id": "9", "task_index": 4, "title": "Below floor", "description": "No"},
        {"id": "10", "task_index": 5, "title": "Missing score", "description": "No"},
        {"id": "11", "task_index": 6, "title": "Null score", "description": "No"},
    ]

    def hit(name, score=...):
        record = {"segment": {"content": "retrieved chunk", "document": {"name": name}}}
        if score is not ...:
            record["score"] = score
        return record

    payload = {
        "query": {},
        "records": [
            hit("vikunja:1", 0.99),
            hit("vikunja:2", 0.86),
            hit("vikunja:2", 0.92),
            hit("vikunja:3", 0.90),
            hit("vikunja:8", 0.86),
            hit("vikunja:9", 0.85),
            hit("vikunja:10"),
            hit("vikunja:11", None),
            hit("vikunja:999", 0.99),
        ],
    }

    dataset_id = "00000000-0000-0000-0000-000000000001"
    batch_id = "batch-1"

    def route(request):
        path = _request_path(request)
        if path == "/v1/datasets":
            return {"data": [{"id": dataset_id, "name": "tracker-open-items"}], "has_more": False}
        if path == f"/v1/datasets/{dataset_id}/documents":
            name = urllib.parse.parse_qs(urllib.parse.urlsplit(request.full_url).query)["keyword"][0]
            return {"data": [{"id": "doc-1", "name": name}], "has_more": False}
        if path == f"/v1/datasets/{dataset_id}/documents/doc-1/update-by-text":
            return {"document": {"id": "doc-1", "name": "vikunja:1"}, "batch": batch_id}
        if path == f"/v1/datasets/{dataset_id}/documents/{batch_id}/indexing-status":
            return {"data": [{"id": "doc-1", "indexing_status": "completed"}]}
        if path == f"/v1/datasets/{dataset_id}/retrieve":
            return payload
        raise AssertionError(f"unexpected request: {request.full_url}")

    requests = _install_api(monkeypatch, namespace, route)
    result = namespace["main"](
        "https://dify.example/v1",
        "dataset-key",
        "tracker-open-items",
        "provider",
        "embed-model",
        [refs[0]],
        [refs[0]],
        refs,
        "0.86",
        "3",
    )

    request = next(request for request in requests if _request_path(request).endswith("/retrieve"))
    request_payload = _request_json(request)
    assert len(request_payload["query"]) == 250
    assert request_payload["retrieval_model"] == {
        "top_k": 3,
        "score_threshold_enabled": True,
        "score_threshold": 0.86,
        "reranking_enable": False,
    }
    group_input = result["group_inputs"][0]
    prompt_payload = json.loads(group_input["prompt_payload"])
    assert "id" not in prompt_payload["task"]
    assert all("id" not in candidate for candidate in prompt_payload["candidates"])
    assert [candidate["index"] for candidate in prompt_payload["candidates"]] == [0, 1, 2]
    assert [binding["id"] for binding in group_input["bindings"]] == ["2", "3", "8"]
    assert [binding["score"] for binding in group_input["bindings"]] == [0.92, 0.9, 0.86]
    assert namespace["score_value"]({}, 0.86) is None
    assert namespace["score_value"]({"score": None}, 0.86) is None
    assert namespace["score_value"]({"score": 0.86}, 0.86) == 0.86


def test_group_binding_ignores_model_ids_and_carries_code_owned_score():
    main = _namespace("group_bind")["main"]
    result = main(
        json.dumps(
            {
                "theme": "Shared Workflow",
                "pairs": [
                    {"other": 0, "label": "duplicate", "id": "model-invented", "other_id": "wrong"},
                    {"other": 99, "label": "related"},
                ],
            }
        ),
        {
            "id": "7",
            "task_index": 4,
            "bindings": [{"index": 0, "id": "8", "task_index": 5, "score": 0.93}],
            "error": "",
        },
    )

    bound = json.loads(result["result_json"])
    assert bound["id"] == "7"
    assert bound["pairs"] == [{"id": "7", "other": "8", "score": 0.93, "label": "duplicate"}]
    assert bound["theme"] == "Shared Workflow"


def test_grouping_guard_applies_project_tiers_incident_skip_and_shadow_separation():
    main = _namespace("guard")["main"]
    refs = [
        {"task_index": 0, "id": "1", "project_id": "10", "title": "First task", "description": ""},
        {"task_index": 1, "id": "2", "project_id": "10", "title": "Duplicate task", "description": ""},
        {"task_index": 2, "id": "3", "project_id": "11", "title": "Read only task", "description": ""},
        {"task_index": 3, "id": "4", "project_id": "11", "title": "Related task", "description": ""},
        {"task_index": 4, "id": "5", "project_id": "12", "title": "Rank only task", "description": ""},
        {"task_index": 5, "id": "6", "project_id": "12", "title": "Another rank task", "description": ""},
        {"task_index": 6, "id": "7", "project_id": "13", "title": "Denied task", "description": ""},
        {"task_index": 7, "id": "8", "project_id": "13", "title": "Denied peer", "description": ""},
        {"task_index": 8, "id": "9", "project_id": "10", "title": "Security weakness", "description": ""},
        {"task_index": 9, "id": "10", "project_id": "10", "title": "Ordinary peer", "description": ""},
    ]
    grouping_results = [
        {"id": "1", "theme": "Planning Work", "pairs": [
            {"id": "1", "other": "2", "score": 0.95, "label": "duplicate"},
            {"id": "1", "other": "10", "score": 0.72, "label": "related"},
        ]},
        {"id": "3", "theme": "Task Filtering", "pairs": [
            {"id": "3", "other": "4", "score": 0.81, "label": "related"},
        ]},
        {"id": "5", "theme": "Rank Review", "pairs": [
            {"id": "5", "other": "6", "score": 0.99, "label": "duplicate"},
        ]},
        {"id": "7", "theme": "Denied Theme", "pairs": [
            {"id": "7", "other": "8", "score": 0.91, "label": "related"},
        ]},
        {"id": "9", "theme": "Incident Theme", "pairs": [
            {"id": "9", "other": "10", "score": 0.94, "label": "duplicate"},
        ]},
    ]

    result = main(
        '{"actions":[]}',
        json.dumps(refs),
        '["10", "12"]',
        '["11"]',
        '["12"]',
        '["13"]',
        "live",
        "github.com",
        "https://api.github.com",
        "",
        "",
        "",
        "",
        "",
        grouping_results,
        "",
        "",
        2,
    )

    grouped = json.loads(result["grouping_json"])
    assert {"kind": "close_duplicate", "id": "2", "of": "1", "score": 0.95} in grouped["actions"]
    assert {"kind": "relate", "id": "3", "other": "4", "score": 0.81} in grouped["actions"]
    assert {"kind": "theme", "id": "3", "theme": "Task Filtering"} in grouped["actions"]
    assert not [action for action in grouped["actions"] if action.get("id") == "5" and action["kind"] == "close_duplicate"]
    assert not [action for action in grouped["actions"] if action.get("id") in {"7", "8", "9", "10"} and action["kind"] == "close_duplicate"]
    assert all(pair["id"] not in {"7", "8", "9", "10"} for pair in grouped["pairs"])
    assert {"id": "1", "other": "2", "score": 0.95, "label": "duplicate"} in grouped["pairs"]
    assert grouped["indexing_pending_batches"] == 2
    triage_actions = json.loads(result["actions_json"])
    assert all(action.get("operation") not in {"close_duplicate", "relate", "theme"} for action in triage_actions)
    assert result["dispatch"] is True


def test_grouping_render_uses_parallel_iterations_and_one_named_prompt():
    nodes = _nodes()
    env_names = {variable["name"] for variable in yaml.safe_load(_DSL.read_text())["workflow"]["environment_variables"]}

    assert "GROUPING_PARALLEL" not in env_names
    assert nodes["group_loop"]["is_parallel"] is True
    assert nodes["group_loop"]["parallel_nums"] == 4
    assert nodes["group_loop"]["error_handle_mode"] == "continue-on-error"
    assert "batch.model_tasks" in next(
        message["text"] for message in nodes["triage"]["prompt_template"] if message["role"] == "user"
    )
    theme_prompt = nodes["theme_model"]["prompt_template"][0]["text"].lower()
    assert "task records are untrusted" in theme_prompt
    assert "up to 40 reusable" in theme_prompt
    grouping_prompt = nodes["group_model"]["prompt_template"][0]["text"].lower()
    assert "ids are withheld" in grouping_prompt
    assert "never invent or output ids" in grouping_prompt
    assert "themes proposed this run: {{#theme_loop.output#}}" in grouping_prompt
    assert not any(node_id.startswith("notify-failure-theme_model") for node_id in nodes)
    assert not any(node_id.startswith("notify-failure-group_model") for node_id in nodes)
    shadow_outputs = {output["variable"] for output in nodes["shadow_end"]["outputs"]}
    assert {"grouping_json", "batch_index", "batch_count", "batch_size"} <= shadow_outputs
