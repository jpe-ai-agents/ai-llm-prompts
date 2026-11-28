"""Tests for the acceptance seed fixture loader."""
from pathlib import Path

import pytest
import yaml

import acceptance_seed
from acceptance_seed import seed


ROOT = Path(__file__).resolve().parents[2]


def _write_seed(directory, steps, suite="suite"):
    path = directory / f"{suite}.yaml"
    path.write_text(yaml.safe_dump(steps, sort_keys=False), encoding="utf-8")
    return path


def _fake(responses):
    calls = []

    def opener(method, url, body):
        calls.append((method, url, body))
        return responses.pop(0)

    return calls, opener


def test_steps_substitute_run_env_and_saved_ids(tmp_path, capsys):
    _write_seed(tmp_path, [
        {"key": "task", "method": "POST", "path": "/tasks",
         "json": {"title": "seed ${RUN} ${env:X}"}},
        {"method": "PUT", "path": "/tasks/${id:task}",
         "json": {"nested": [{"related": "${id:task}"}], "title": "${RUN}/${env:X}"}},
    ])
    calls, opener = _fake([(201, {"id": 42}), (200, {})])
    assert seed("suite", "run-a", "", "marker", tmp_path, opener,
                {"X": "value"}) == 2
    assert calls[0][2] == {"title": "seed run-a value"}
    assert calls[1][1].endswith("/tasks/42")
    assert calls[1][2] == {"nested": [{"related": 42}], "title": "run-a/value"}
    assert "seed suite run-a: 2 steps" in capsys.readouterr().out


def test_project_placeholder_selects_exact_title_and_rejects_no_match(tmp_path):
    _write_seed(tmp_path, [{"method": "GET", "path": "/projects/${project:INBOX}"}])
    env = {"INBOX": "Exact"}
    hits = [{"id": 1, "title": "Exact copy"}, {"id": 2, "title": "Exact"}]
    calls, opener = _fake([(200, hits), (200, {})])
    seed("suite", "r", "", "marker", tmp_path, opener, env)
    assert calls[1][1].endswith("/projects/2")
    calls, opener = _fake([(200, [{"id": 1, "title": "Other"}])])
    with pytest.raises(ValueError, match="project INBOX must match exactly one"):
        seed("suite", "r", "", "marker", tmp_path, opener, env)


def test_bucket_resolves_kanban_view_and_caches_project(tmp_path):
    _write_seed(tmp_path, [{"method": "POST", "path": "/tasks", "json": {
        "bucket_a": "${bucket:INBOX:Ready}", "bucket_b": "${bucket:INBOX:Ready}"}}])
    responses = [
        (200, [{"id": 5, "title": "Inbox"}]),
        (200, [{"id": 8, "view_kind": "list"}, {"id": 9, "view_kind": "kanban"}]),
        (200, [{"id": 12, "title": "Ready"}]),
        (200, {}),
    ]
    calls, opener = _fake(responses)
    seed("suite", "r", "", "marker", tmp_path, opener, {"INBOX": "Inbox"})
    assert [call[0] for call in calls] == ["GET", "GET", "GET", "POST"]
    assert calls[0][1].endswith("/projects?s=Inbox&per_page=50")
    assert calls[-1][2] == {"bucket_a": 12, "bucket_b": 12}


def test_label_substitutes_run_creates_and_reuses_label(tmp_path):
    _write_seed(tmp_path, [{"method": "POST", "path": "/tasks", "json": {
        "labels": ["${label:triage ${RUN}}", "${label:triage ${RUN}}"]}}])
    calls, opener = _fake([(200, []), (201, {"id": 17}), (200, {})])
    seed("suite", "r-7", "", "marker", tmp_path, opener)
    assert [call[0] for call in calls] == ["GET", "PUT", "POST"]
    assert calls[1][2] == {"title": "triage r-7"}
    assert calls[-1][2] == {"labels": [17, 17]}


def test_date_placeholders_use_injected_utc_time(tmp_path):
    _write_seed(tmp_path, [{"method": "POST", "path": "/tasks", "json": {
        "future": "${date:+7d}", "past": "${date:-2d}"}}])
    calls, opener = _fake([(200, {})])
    seed("suite", "r", "", "marker", tmp_path, opener,
         now=acceptance_seed.datetime(2026, 1, 10, 12, 30, tzinfo=acceptance_seed.timezone.utc))
    assert calls[0][2] == {
        "future": "2026-01-17T12:30:00Z", "past": "2026-01-08T12:30:00Z",
    }


def test_http_error_names_step_details_without_token(tmp_path):
    _write_seed(tmp_path, [{"key": "blocked", "method": "DELETE", "path": "/tasks/42"}])
    calls, opener = _fake([(403, {"message": "body must not be shown"})])
    with pytest.raises(ValueError) as error:
        seed("suite", "r", "", "marker", tmp_path, opener)
    message = str(error.value)
    assert all(part in message for part in ("step 1", "blocked", "DELETE", "/tasks/42", "403"))
    assert "marker" not in message and "body must not be shown" not in message
    assert calls[0][2] is None


def test_a_keyed_step_whose_answer_has_no_id_saves_nothing(tmp_path):
    _write_seed(tmp_path, [{"key": "link", "method": "PUT", "path": "/tasks/1/labels", "json": {"label_id": 2}},
                           {"method": "GET", "path": "/tasks/${id:link}"}])
    calls, opener = _fake([(201, {"label_id": 2})])
    with pytest.raises(ValueError, match="unknown id key link"):
        seed("suite", "r", "", "marker", tmp_path, opener, {})
    assert len(calls) == 1


def test_reset_empties_an_acceptance_project_and_refuses_any_other(tmp_path):
    _write_seed(tmp_path, [{"reset": "AREA"}])
    calls, opener = _fake([(200, [{"id": 7, "title": "Acceptance area"}]), (200, [{"id": 1}, {"id": 2}]),
                           (200, {}), (200, {}), (200, [])])
    assert seed("suite", "r", "", "marker", tmp_path, opener, {"AREA": "Acceptance area"}) == 1
    assert [(method, url.split("?")[0]) for method, url, _ in calls[1:]] == [
        ("GET", "/api/v1/projects/7/tasks"), ("DELETE", "/api/v1/tasks/1"),
        ("DELETE", "/api/v1/tasks/2"), ("GET", "/api/v1/projects/7/tasks")]
    calls, opener = _fake([])
    with pytest.raises(ValueError, match="refuses to reset AREA"):
        seed("suite", "r", "", "marker", tmp_path, opener, {"AREA": "Homelab"})
    assert calls == []


def test_main_handles_missing_seed_and_token(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(acceptance_seed, "DEFAULT_SEEDS_DIR", tmp_path)
    monkeypatch.setattr(acceptance_seed.sys, "argv", ["acceptance_seed.py", "suite", "r"])
    monkeypatch.setenv("ACCEPTANCE_SEED_URL", "base")
    monkeypatch.delenv("ACCEPTANCE_SEED_TOKEN", raising=False)
    assert acceptance_seed.main() == 0
    assert "seed suite: no seed file" in capsys.readouterr().out
    _write_seed(tmp_path, [])
    assert acceptance_seed.main() == 2
    assert "ACCEPTANCE_SEED_TOKEN" in capsys.readouterr().err


def test_makefile_seeds_after_run_id_before_first_eval():
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    target = makefile.split("acceptance-sets:", 1)[1].split("\ntest:", 1)[0]
    run_id = target.index('run_id="$$(date')
    seed_call = target.index('nix develop -c python3 agents/judges/acceptance_seed.py')
    first_eval = target.index("promptfoo eval")
    assert run_id < seed_call < first_eval
