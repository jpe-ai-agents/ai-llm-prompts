# The urgency score of the work management standard. The standard owns the formula, the scales, the bands and the
# test table; agents/judges/test_urgency_score.py pins that table. Change a number here only when the standard changes.
_DUE_STEPS = ((0, 10), (2, 9), (7, 7), (14, 5), (30, 3))
_PRIORITY_BANDS = ((12, 5), (7, 4), (4, 3), (2, 2))


def time_criticality(days_left):
    # days_left is whole days until the due date, counted in UTC. None means no due date.
    if days_left is None:
        return 1
    for limit, value in _DUE_STEPS:
        if days_left <= limit:
            return value
    return 1


def urgency_score(value, risk, size, days_left=None, wont=False):
    # Returns None for an unscored item: a missing Value or Risk Reduction, or a Job Size of zero or less. That check
    # comes before the Won't rule, so a Won't item with a missing input stays unscored.
    for number in (value, risk, size):
        if isinstance(number, bool) or not isinstance(number, (int, float)):
            return None
    if size <= 0:
        return None
    if wont:
        return 0
    raw = (value + time_criticality(days_left) + risk) / size
    # Round a half up to two places, as JavaScript Math.round(x * 100) / 100 does; Python's round() rounds a half to
    # even. shortcut: correct for raw >= 0 only, upgrade if a negative Value or Risk Reduction is ever allowed.
    return int(raw * 100 + 0.5) / 100


def priority_band(score):
    # The tracker's own priority, 0 to 5. None (unscored) is 0. A score of 0 (Won't) is 1.
    if score is None:
        return 0
    for limit, band in _PRIORITY_BANDS:
        if score >= limit:
            return band
    return 1


def label_number(labels, prefix):
    # The N of the first label "prefix:N" where N is a whole number in ASCII digits, else None.
    for label in labels or []:
        text = str(label)
        number = text[len(prefix) + 1:]
        if text.startswith(prefix + ":") and number.isascii() and number.isdigit():
            return int(number)
    return None
