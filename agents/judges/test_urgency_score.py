"""The urgency score helper returns the work management standard's test table."""

import importlib.util
from pathlib import Path

import pytest


_PATH = Path(__file__).resolve().parents[2] / "agents" / "dify-src" / "helpers" / "urgency_score.py"
_SPEC = importlib.util.spec_from_file_location("urgency_score", _PATH)
_HELPER = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_HELPER)


@pytest.mark.parametrize(
    ("value", "risk", "size", "days_left", "wont", "score", "band"),
    [
        (5, 5, 3, None, False, 3.67, 2),
        (8, 6, 1, 2, False, 23, 5),
        (10, 10, 1, -1, False, 30, 5),
        (5, 5, 5, 7, False, 3.4, 2),
        (9, 8, 2, 14, False, 11, 4),
        (4, 4, 8, 30, False, 1.38, 1),
        (7, 7, 2, 60, False, 7.5, 4),
        (6, 3, 3, None, True, 0, 1),
        (5, None, 3, None, False, None, 0),
        (5, 5, 0, None, False, None, 0),
    ],
)
def test_standard_test_table(value, risk, size, days_left, wont, score, band):
    got = _HELPER.urgency_score(value, risk, size, days_left, wont)
    assert got == score
    assert _HELPER.priority_band(got) == band


@pytest.mark.parametrize(
    ("days_left", "expected"),
    [(None, 1), (-5, 10), (0, 10), (1, 9), (2, 9), (3, 7), (7, 7), (8, 5), (14, 5), (15, 3), (30, 3), (31, 1)],
)
def test_time_criticality_steps(days_left, expected):
    assert _HELPER.time_criticality(days_left) == expected


@pytest.mark.parametrize("score,band", [(12, 5), (11.99, 4), (7, 4), (6.99, 3), (4, 3), (3.99, 2), (2, 2), (1.99, 1)])
def test_band_edges(score, band):
    assert _HELPER.priority_band(score) == band


def test_a_half_rounds_up_like_the_tracker_workflow():
    assert _HELPER.urgency_score(1, 0, 16) == 0.13


def test_wont_with_a_missing_input_stays_unscored():
    assert _HELPER.urgency_score(None, 5, 3, None, True) is None


def test_a_boolean_is_not_a_number():
    assert _HELPER.urgency_score(True, 5, 3) is None


@pytest.mark.parametrize(
    ("labels", "prefix", "expected"),
    [
        (["Must", "value:8", "risk:3"], "value", 8),
        (["Must", "value:8", "risk:3"], "risk", 3),
        (["size:x", "size:5"], "size", 5),
        (["values:8", "value:"], "value", None),
        (["value:8.5", "value:-1"], "value", None),
        ([], "value", None),
        (None, "value", None),
    ],
)
def test_label_number(labels, prefix, expected):
    assert _HELPER.label_number(labels, prefix) == expected
