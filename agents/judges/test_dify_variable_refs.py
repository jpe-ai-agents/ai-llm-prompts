"""Every {{#node.var#}} reference in a rendered Dify DSL resolves at run time.

Dify's runtime matches references with graphon.runtime.variable_pool.VARIABLE_PATTERN; a node id outside
[a-zA-Z0-9_] never matches, so the reference reaches the caller as literal text.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

DSL_DIR = Path(__file__).resolve().parents[1] / "dify"
LENIENT = re.compile(r"\{\{#([^#.{}]+)\.([^#{}]+)#\}\}")
RUNTIME = re.compile(r"\{\{#([a-zA-Z0-9_]{1,50}(?:\.[a-zA-Z_][a-zA-Z0-9_]{0,29}){1,10})#\}\}")
GLOBAL_SCOPES = {"sys", "env", "conversation"}


def _strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)


@pytest.mark.parametrize("path", sorted(DSL_DIR.glob("*.dsl.yml")), ids=lambda p: p.name)
def test_variable_references_match_the_runtime_pattern_and_name_a_node(path):
    graph = (yaml.safe_load(path.read_text(encoding="utf-8")).get("workflow") or {}).get("graph") or {}
    node_ids = {node["id"] for node in graph.get("nodes", [])}
    bad = []
    for text in _strings(graph.get("nodes", [])):
        for match in LENIENT.finditer(text):
            ref = match.group(0)
            if not RUNTIME.fullmatch(ref):
                bad.append(f"{ref}: does not match the runtime pattern")
            elif match.group(1) not in node_ids | GLOBAL_SCOPES:
                bad.append(f"{ref}: names no node")
    assert not bad, sorted(set(bad))


def test_the_check_catches_a_hyphenated_node_id():
    assert LENIENT.search("{{#read-result.answer#}}") and not RUNTIME.fullmatch("{{#read-result.answer#}}")
    assert RUNTIME.fullmatch("{{#read_result.answer#}}")
