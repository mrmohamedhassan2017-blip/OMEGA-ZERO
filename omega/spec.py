from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path
from typing import Any

from .store import Store


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def spec_to_bundle(spec: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(spec, dict) or spec.get("format") != "omega.problem-spec" or spec.get("format_version") != 1:
        raise ValueError("unsupported problem spec format or version")
    problem = spec.get("problem")
    if not isinstance(problem, dict) or not str(problem.get("title", "")).strip():
        raise ValueError("spec problem.title is required")
    nodes = spec.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        raise ValueError("spec.nodes must be a non-empty list")
    keys = [node.get("key") if isinstance(node, dict) else None for node in nodes]
    if any(not isinstance(key, str) or not key.strip() for key in keys) or len(set(keys)) != len(keys):
        raise ValueError("spec node keys must be non-empty and unique")
    target = spec.get("analysis_target")
    if not isinstance(target, str) or target not in set(keys):
        raise ValueError("spec.analysis_target must reference a node key")
    payload = {"format": "omega.problem-bundle", "format_version": 1,
               "problem": {"title": str(problem["title"]).strip(), "description": str(problem.get("description", ""))},
               "nodes": [{key: node[key] for key in ("key", "type", "role", "statement", "confidence", "evidence", "status")
                          if key in node} for node in nodes],
               "edges": []}
    raw_edges = spec.get("edges", [])
    if not isinstance(raw_edges, list):
        raise ValueError("spec.edges must be a list")
    for edge in raw_edges:
        if not isinstance(edge, dict):
            raise ValueError("each spec edge must be an object")
        payload["edges"].append({"source": edge.get("source"), "target": edge.get("target"), "type": edge.get("type")})
    return {"payload": payload, "sha256": hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()}


def validate_spec(spec: dict[str, Any]) -> dict[str, Any]:
    bundle = spec_to_bundle(spec)
    with tempfile.TemporaryDirectory() as tmp:
        imported = Store(Path(tmp) / "validation.db").import_problem(bundle)
    return {"valid": True, "nodes": imported["nodes_imported"], "edges": imported["edges_imported"],
            "analysis_target": spec["analysis_target"], "bundle_sha256": bundle["sha256"]}


def run_spec(store: Store, spec: dict[str, Any]) -> dict[str, Any]:
    bundle = spec_to_bundle(spec)
    imported = store.import_problem(bundle)
    return {"bundle": bundle, "imported": imported, "spec": spec}

