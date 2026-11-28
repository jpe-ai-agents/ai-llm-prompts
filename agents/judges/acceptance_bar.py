"""Pass/fail bar for the ten-run acceptance campaign, and its report."""
import json
import sys
from pathlib import Path

import yaml

SETS_DIR = Path(__file__).resolve().parents[1] / "evals" / "acceptance"


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


def main(argv, sets_dir=SETS_DIR):
    """Print each case's count and each set's verdict; return 0 only when every set that ran clears the bar.

    `argv` is the outcomes file (one JSON object per line: suite, case, success) and then the set files that ran.
    """
    events = [json.loads(line) for line in Path(argv[0]).read_text(encoding="utf-8").splitlines() if line]
    overall = True
    for name in argv[1:]:
        suite = name.removesuffix(".yaml")
        cases = yaml.safe_load((Path(sets_dir) / f"{suite}.yaml").read_text(encoding="utf-8"))
        safety = {case["id"]: [] for case in cases if case["metadata"]["kind"] == "safety"}
        quality = {case["id"]: [] for case in cases if case["metadata"]["kind"] == "quality"}
        for event in events:
            for group in (safety, quality):
                if event["suite"] == suite and event["case"] in group:
                    group[event["case"]].append(event["success"] is True)
        for case_id, results in (safety | quality).items():
            print(f"{suite} {case_id}: {sum(results)}/10")
        print(f"{suite} quality: {sum(sum(results) for results in quality.values())}/{len(quality) * 10}")
        passed = passes_bar(safety, quality)
        print(f"{suite}: {'PASS' if passed else 'FAIL'}")
        overall = overall and passed
    print(f"overall: {'PASS' if overall else 'FAIL'}")
    return 0 if overall and len(argv) > 1 else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
