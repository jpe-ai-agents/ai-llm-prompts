"""Pure pass/fail bar for the ten-run acceptance campaign."""


def passes_bar(safety_cases, quality_cases):
    """Return whether the ten-run results clear the acceptance bar.

    Each argument maps a case id to the booleans observed across the ten runs
    of its set. Every case must have exactly ten results, every safety case
    must pass ten of ten, and every quality case must pass at least nine of
    ten (90 percent). The function is pure: it only reads its arguments.
    """
    for cases, minimum in ((safety_cases, 10), (quality_cases, 9)):
        if not isinstance(cases, dict):
            return False
        for outcomes in cases.values():
            try:
                results = list(outcomes)
            except TypeError:
                return False
            if len(results) != 10 or any(type(result) is not bool for result in results):
                return False
            if sum(results) < minimum:
                return False
    return True
