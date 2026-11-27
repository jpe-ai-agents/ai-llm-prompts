"""Runs the semaphore-clerk Code nodes that decide whether a Semaphore task may start.

guard validates the parsed request against the caller's text and the policy. initial_decision
deduplicates a proposal and gates a confirmation on the proposal's own task record. post_check keeps
only the lowest confirmation id. status_result reads only tasks of the named template.
"""

import json

import pytest

from dify_nodes import node_main


POLICY = json.dumps(
    {
        "apply-site": {
            "project_id": 3,
            "template_id": 41,
            "parameter_sets": {"web": {"limit": "web"}, "db": {"limit": "db"}},
        }
    }
)


def _intent(operation, parameter_set="web", request_id="", proposal_id=None):
    return json.dumps(
        {
            "operation": operation,
            "template_name": "apply-site",
            "parameter_set": parameter_set,
            "request_id": request_id,
            "proposal_id": proposal_id,
        }
    )


def _guard(intent, raw, policy=POLICY):
    return node_main("semaphore-clerk", "guard")(intent, raw, policy)


def _proposal(**changes):
    task = {
        "id": 70,
        "template_id": 41,
        "status": "success",
        "dry_run": True,
        "limit": "web",
        "message": "proposal r-1",
    }
    return {**task, **changes}


def _decide(operation, tasks, request_id="", proposal_id=0, limit="web"):
    return node_main("semaphore-clerk", "initial_decision")(
        operation, "apply-site", "web", request_id, proposal_id, 41, limit, "", {"tasks": tasks}
    )


def test_guard_allows_a_proposal_the_caller_wrote():
    out = _guard(_intent("propose", request_id="r-1"), "propose apply-site web r-1")
    assert out["allowed"] is True
    assert (out["project_id"], out["template_id"], out["limit"]) == (3, 41, "web")
    assert out["proposal_message"] == "proposal r-1"


@pytest.mark.parametrize(
    "intent, raw, policy, reason",
    [
        (_intent("propose", request_id="r-1"), "propose apply-site web r-1", "", "policy-unavailable"),
        (_intent("propose", request_id="r-1"), "propose apply-site web r-1", "{}", "policy-unavailable"),
        (_intent("propose", "all", "r-1"), "propose apply-site all r-1", POLICY, "unknown-parameter-set"),
        # The parser returned an id or a name the caller did not write.
        (_intent("confirm", proposal_id=70), "confirm apply-site web 700", POLICY, "invalid-request"),
        (_intent("confirm", proposal_id=70), "confirm apply-site web", POLICY, "invalid-request"),
        (_intent("propose", request_id="r-1"), "propose apply-site web r-2", POLICY, "invalid-request"),
        (_intent("confirm", "db", proposal_id=70), "confirm apply-site web 70", POLICY, "invalid-request"),
    ],
)
def test_guard_refuses(intent, raw, policy, reason):
    out = _guard(intent, raw, policy)
    assert (out["allowed"], out["status"], out["reason"]) == (False, "refused", reason)


def test_proposal_starts_once_per_request_id():
    assert _decide("propose", [], request_id="r-1")["route"] == "propose"
    again = _decide("propose", [_proposal()], request_id="r-1")
    assert (again["route"], again["result"]["proposal_id"]) == ("already", 70)
    reused = _decide("propose", [_proposal(template_id=42)], request_id="r-1")
    assert (reused["route"], reused["reason"]) == ("terminate", "request-id-reused")


def test_confirm_passes_only_the_matching_successful_check_run():
    out = _decide("confirm", [_proposal()], proposal_id=70)
    assert (out["route"], out["status"]) == ("confirm", "ok")


@pytest.mark.parametrize(
    "tasks, reason",
    [
        ([], "proposal-not-found"),
        ([_proposal(id=71)], "proposal-not-found"),
        ([_proposal(status="error")], "proposal-not-successful"),
        ([_proposal(status="running")], "proposal-not-successful"),
        ([_proposal(dry_run=False)], "proposal-not-check-mode"),
        ([_proposal(template_id=42)], "template-mismatch"),
        ([_proposal(limit="db")], "parameter-set-mismatch"),
        ([{k: v for k, v in _proposal().items() if k != "limit"}], "parameter-set-mismatch"),
        ([_proposal(message="nightly")], "proposal-not-successful"),
    ],
)
def test_confirm_refuses_and_starts_nothing(tasks, reason):
    out = _decide("confirm", tasks, proposal_id=70)
    assert (out["route"], out["status"], out["reason"]) == ("terminate", "refused", reason)


def test_confirm_returns_the_existing_run_instead_of_a_second_one():
    existing = [_proposal(), {"id": 81, "status": "running", "message": "confirm 70"}]
    out = _decide("confirm", existing, proposal_id=70)
    assert (out["route"], out["result"]["run_id"]) == ("already", 81)


def test_unreadable_task_list_stops():
    out = node_main("semaphore-clerk", "initial_decision")(
        "confirm", "apply-site", "web", "", 70, 41, "web", "not json", None
    )
    assert (out["route"], out["status"]) == ("terminate", "stop")


def test_only_the_lowest_confirmation_id_is_kept():
    post_check = node_main("semaphore-clerk", "post_check")
    runs = {"tasks": [{"id": 81, "status": "running", "message": "confirm 70"}, {"id": 82, "message": "confirm 70"}]}
    kept = post_check("apply-site", "web", 70, 81, "started", "confirm 70", "", runs)
    assert (kept["route"], kept["result"]["run_id"]) == ("confirmed", 81)
    stopped = post_check("apply-site", "web", 70, 82, "started", "confirm 70", "", runs)
    assert (stopped["route"], stopped["reason"], stopped["result"]["winning_run_id"]) == ("duplicate", "duplicate-confirm", 81)


def test_status_reads_only_tasks_of_the_named_template():
    status = node_main("semaphore-clerk", "status_result")
    assert status("apply-site", "", 70, 41, "", _proposal())["status"] == "ok"
    other = status("apply-site", "", 70, 41, "", _proposal(template_id=42))
    assert (other["status"], other["reason"]) == ("refused", "proposal-not-found")
