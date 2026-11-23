from datetime import date

import pytest

from test_triage_guard_runner import _POLICY, _guard


_TODAY = date(2026, 1, 1)


def _label(label_id, title):
    return {"id": label_id, "title": title}


def _task(task_id, labels=None, priority=0, due_date=""):
    return {
        "id": str(task_id),
        "project_id": "10",
        "title": f"Task {task_id}",
        "priority": priority,
        "due_date": due_date,
        "labels": labels or [],
    }


def _epic_card(labels=None):
    base = [
        _label(1, "epic"),
        _label(2, "epic:x"),
        _label(3, "value:9"),
        _label(4, "risk:7"),
    ]
    return {
        "id": "90",
        "project_id": "10",
        "title": "EPIC: Example",
        "labels": labels if labels is not None else base,
        "is_epic": True,
    }


def _run(tasks, proposed, today=_TODAY):
    result = _guard(tasks, proposed, _POLICY, today=today)
    assert all(
        "labels" not in action
        for action in result["actions"]
        if action["operation"] == "update"
    )
    return result


def test_model_priority_is_ignored_and_missing_due_date_uses_the_shared_score():
    task = _task(7, [_label(2, "epic:x"), _label(5, "size:3")])

    result = _run(
        [task, _epic_card()],
        [{"task_index": 0, "kind": "rank", "priority": 5}],
    )

    assert result["actions"] == [
        {"operation": "update", "id": "7", "projectId": "10", "priority": 3}
    ]


def test_due_date_uses_utc_calendar_days_and_trailing_z():
    task = _task(
        7,
        [_label(2, "epic:x"), _label(5, "size:3")],
        due_date="2026-01-03T00:00:00Z",
    )

    result = _run([task, _epic_card()], [{"task_index": 0, "kind": "rank"}])

    assert result["actions"] == [
        {"operation": "update", "id": "7", "projectId": "10", "priority": 4}
    ]


@pytest.mark.parametrize("due_date", ["", "0001-01-01T00:00:00Z"])
def test_empty_and_zero_due_dates_are_unset(due_date):
    task = _task(
        7,
        [_label(2, "epic:x"), _label(5, "size:3")],
        due_date=due_date,
    )

    result = _run([task, _epic_card()], [{"task_index": 0, "kind": "rank"}])

    assert result["actions"][0]["priority"] == 3


@pytest.mark.parametrize(
    "current_priority, expected_actions",
    [
        (0, []),
        (4, [{"operation": "update", "id": "7", "projectId": "10", "priority": 0}]),
    ],
)
def test_missing_epic_and_no_proposal_scores_zero(current_priority, expected_actions):
    task = _task(7, priority=current_priority)

    result = _run([task], [{"task_index": 0, "kind": "rank"}])

    assert result["actions"] == expected_actions


def test_only_known_epic_and_valid_size_labels_are_added_with_apply_label():
    task = _task(7)
    size_holder = _task(91, [_label(5, "size:5")])

    result = _run(
        [task, _epic_card(), size_holder],
        [
            {
                "task_index": 0,
                "kind": "rank",
                "priority": 5,
                "labels": ["epic:x", "size:5", "urgent", "value:10", "Must"],
            }
        ],
    )

    assert result["actions"] == [
        {"operation": "update", "id": "7", "projectId": "10", "priority": 2},
        {
            "operation": "apply-label",
            "id": "7",
            "projectId": "10",
            "labels": [2, 5],
        },
    ]


def test_existing_size_is_never_replaced_and_is_used_for_scoring():
    task = _task(
        7,
        [_label(2, "epic:x"), _label(8, "size:8")],
    )

    result = _run(
        [task, _epic_card()],
        [{"task_index": 0, "kind": "rank", "labels": ["size:1"]}],
    )

    assert result["actions"] == [
        {"operation": "update", "id": "7", "projectId": "10", "priority": 2}
    ]


@pytest.mark.parametrize(
    "wont_label, on_card",
    [("Won't", False), ("Won’t", True)],
    ids=["task-straight-apostrophe", "card-curly-apostrophe"],
)
def test_wont_on_task_or_epic_scores_zero(wont_label, on_card):
    task = _task(
        7,
        [_label(2, "epic:x"), _label(5, "size:3")]
        + ([] if on_card else [_label(6, wont_label)]),
    )
    card_labels = [
        _label(1, "epic"),
        _label(2, "epic:x"),
        _label(3, "value:9"),
        _label(4, "risk:7"),
    ]
    if on_card:
        card_labels.append(_label(6, wont_label))

    result = _run([task, _epic_card(card_labels)], [{"task_index": 0, "kind": "rank"}])

    assert result["actions"] == [
        {"operation": "update", "id": "7", "projectId": "10", "priority": 1}
    ]


def test_accepted_label_without_an_id_is_reported_and_not_emitted():
    task = _task(7, [_label(2, "epic:x")])

    result = _run(
        [task, _epic_card()],
        [{"task_index": 0, "kind": "rank", "labels": ["size:3"]}],
    )

    assert result["actions"] == []
    assert result["unknown_label_count"] == 1
    assert result["unknown_label_titles"] == ["size:3"]


def test_epic_proposal_without_a_matching_card_is_dropped():
    task = _task(7)

    result = _run(
        [task, _epic_card()],
        [{"task_index": 0, "kind": "rank", "labels": ["epic:nope"]}],
    )

    assert result["actions"] == []
    assert result["unknown_label_count"] == 0


def test_invalid_size_and_card_value_are_ignored():
    task = _task(7, [_label(2, "epic:x"), _label(5, "size:3")])
    card = _epic_card(
        [
            _label(1, "epic"),
            _label(2, "epic:x"),
            _label(3, "value:11"),
            _label(4, "risk:7"),
        ]
    )

    result = _run(
        [task, card],
        [{"task_index": 0, "kind": "rank", "labels": ["size:4"]}],
    )

    assert result["actions"] == []
