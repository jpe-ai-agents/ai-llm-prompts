"""Load declarative fixtures for one prompt-pack acceptance suite."""
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import yaml

# Beside the loader, not under agents/evals: seed steps are not eval cases.
DEFAULT_SEEDS_DIR = Path(__file__).resolve().parent / "acceptance_seeds"
_PLACEHOLDER = re.compile(r"\$\{([^{}]*)\}")


def _urllib_opener(token):
    def send(method, url, body):
        payload = None if body is None else json.dumps(body).encode("utf-8")
        request = Request(url, data=payload, method=method,
                          headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
        try:
            response = urlopen(request, timeout=30)
        except HTTPError as error:
            return error.code, None
        with response:
            raw = response.read()
        return response.status, json.loads(raw) if raw else None
    return send


def _exact(rows, field, value, description):
    matches = [row for row in rows or [] if isinstance(row, dict) and row.get(field) == value]
    if len(matches) != 1:
        raise ValueError(f"{description} must match exactly one result")
    return int(matches[0]["id"])


def seed(suite, run_id, base_url, token, seeds_dir=DEFAULT_SEEDS_DIR,
         opener=None, environ=None, now=None):
    """Create a suite's seed steps in order and print its step count."""
    seed_file = Path(seeds_dir) / f"{suite}.yaml"
    if not seed_file.exists(): print(f"seed {suite}: no seed file"); return 0
    env = os.environ if environ is None else environ
    api_root, send = base_url.rstrip("/") + "/api/v1", opener or _urllib_opener(token)
    cache, ids, context = {}, {}, {"number": 0, "key": "<none>"}

    def request(method, path, body=None):
        try: status, data = send(method, api_root + path, body)
        except Exception: raise ValueError(f"step {context['number']} key {context['key']} {method} {path} request failed") from None
        if not 200 <= status < 300: raise ValueError(f"step {context['number']} key {context['key']} {method} {path} status {status}")
        return data
    def cached(key, load):
        if key not in cache: cache[key] = load()
        return cache[key]
    def env_value(name):
        value = env.get(name)
        if not value: raise ValueError(f"missing environment variable {name}")
        return value
    def project(name):
        title = env_value(name)
        path = "/projects?" + urlencode({"s": title, "per_page": 50})
        return cached(("project", title), lambda: _exact(request("GET", path), "title", title, f"project {name}"))
    def view(name):
        project_id = project(name)
        def load():
            rows = request("GET", f"/projects/{project_id}/views") or []
            matches = [row for row in rows if isinstance(row, dict) and row.get("view_kind") == "kanban"]
            if len(matches) != 1: raise ValueError(f"kanban view for {name} must match exactly one result")
            return int(matches[0]["id"])
        return cached(("view", project_id), load)
    def resolve(expression):
        if expression == "RUN": return run_id
        kind, separator, argument = expression.partition(":")
        if not separator: raise ValueError(f"unknown placeholder kind {kind}")
        if kind == "env": return env_value(argument)
        if kind == "project": return project(argument)
        if kind == "view": return view(argument)
        if kind == "bucket":
            name, separator, title = argument.partition(":")
            if not separator: raise ValueError("bucket placeholder needs a project name and title")
            project_id, view_id = project(name), view(name)
            path = f"/projects/{project_id}/views/{view_id}/buckets"
            return cached(("bucket", project_id, view_id, title),
                          lambda: _exact(request("GET", path), "title", title, f"bucket {title}"))
        if kind == "label":
            title = argument
            def load():
                path = "/labels?" + urlencode({"s": title, "per_page": 50})
                matches = [row for row in request("GET", path) or []
                           if isinstance(row, dict) and row.get("title") == title]
                if len(matches) > 1: raise ValueError(f"label {title} must match at most one result")
                if matches: return int(matches[0]["id"])
                created = request("PUT", "/labels", {"title": title})
                if not isinstance(created, dict) or "id" not in created:
                    raise ValueError("created label response has no id")
                return int(created["id"])
            return cached(("label", title), load)
        if kind == "user":
            username = env_value(argument)
            path = "/users?" + urlencode({"s": username})
            return cached(("user", username), lambda: _exact(
                request("GET", path), "username", username, f"user {argument}"))
        if kind == "id":
            if argument not in ids: raise ValueError(f"unknown id key {argument}")
            return ids[argument]
        if kind == "date":
            match = re.fullmatch(r"([+-])(\d+)([dh])", argument)
            if not match: raise ValueError(f"invalid date placeholder {argument}")
            moment = now if now is not None else datetime.now(timezone.utc)
            if moment.tzinfo is None: moment = moment.replace(tzinfo=timezone.utc)
            amount = int(match.group(2)) * (1 if match.group(1) == "+" else -1)
            delta = timedelta(days=amount) if match.group(3) == "d" else timedelta(hours=amount)
            return (moment + delta).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        raise ValueError(f"unknown placeholder kind {kind}")
    def substitute(value):
        if isinstance(value, list): return [substitute(item) for item in value]
        if isinstance(value, dict): return {str(substitute(key)): substitute(item) for key, item in value.items()}
        if not isinstance(value, str): return value
        while True:
            match = _PLACEHOLDER.search(value)
            if match is None: return value
            replacement = resolve(match.group(1))
            if match.start() == 0 and match.end() == len(value): return replacement
            value = value[:match.start()] + str(replacement) + value[match.end():]

    steps = yaml.safe_load(seed_file.read_text(encoding="utf-8"))
    if not isinstance(steps, list): raise ValueError("seed file must contain a YAML list")
    for number, step in enumerate(steps, 1):
        if not isinstance(step, dict): raise ValueError(f"step {number} must be a mapping")
        key, method = step.get("key"), step.get("method")
        context.update(number=number, key=key if key is not None else "<none>")
        if "reset" in step:  # empty an acceptance project so every run starts from the same state
            name = step["reset"]
            if not env_value(name).startswith("Acceptance"): raise ValueError(f"step {number} refuses to reset {name}")
            project_id = project(name)
            for _ in range(40):
                rows = request("GET", f"/projects/{project_id}/tasks?per_page=50") or []
                if not rows: break
                for row in rows: request("DELETE", f"/tasks/{row['id']}")
            else: raise ValueError(f"step {number} could not empty {name}")
            continue
        if method not in {"PUT", "POST", "GET", "DELETE"}: raise ValueError(f"step {number} has an unsupported method")
        path = substitute(step.get("path"))
        if not isinstance(path, str): raise ValueError(f"step {number} path must be a string")
        body = substitute(step["json"]) if "json" in step else None
        data = request(method, path, body)
        # Label, relation, assignee and bucket writes answer without an id: their key only names the step.
        if key is not None and isinstance(data, dict) and "id" in data: ids[key] = int(data["id"])
    print(f"seed {suite} {run_id}: {len(steps)} steps")
    return len(steps)


def main():
    if len(sys.argv) != 3: print("usage: acceptance_seed.py <suite> <run_id>", file=sys.stderr); return 2
    suite, run_id = sys.argv[1:]
    if not (DEFAULT_SEEDS_DIR / f"{suite}.yaml").exists(): print(f"seed {suite}: no seed file"); return 0
    missing = [name for name in ("ACCEPTANCE_SEED_URL", "ACCEPTANCE_SEED_TOKEN") if not os.environ.get(name)]
    if missing:
        print("missing environment variable " + ", ".join(missing), file=sys.stderr)
        return 2
    try:
        seed(suite, run_id, os.environ["ACCEPTANCE_SEED_URL"], os.environ["ACCEPTANCE_SEED_TOKEN"])
    except Exception as error: print(str(error), file=sys.stderr); return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
