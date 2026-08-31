from __future__ import annotations

import hashlib
import json
import secrets
import uuid
from typing import Any

from .contracts import CONTRACT_VERSION
from .engine import Engine
from .ontology import DEFAULT_ROLES
from .scoring import DEFAULT_SCORING_PROFILE


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _verify_bundle(bundle: dict[str, Any]) -> None:
    payload = bundle.get("payload")
    if not isinstance(payload, dict) or bundle.get("sha256") != _digest(payload):
        raise ValueError("problem bundle fingerprint mismatch")
    if payload.get("format") != "omega.problem-bundle" or payload.get("format_version") != 1:
        raise ValueError("unsupported problem bundle")


def prepare_blind_case(problem_bundle: dict[str, Any], labels: dict[str, Any],
                       salt: str | None = None) -> dict[str, Any]:
    _verify_bundle(problem_bundle)
    expected_order = labels.get("expected_order")
    evaluator_ref = str(labels.get("evaluator_ref", "")).strip()
    if not isinstance(expected_order, list) or not expected_order or len(set(expected_order)) != len(expected_order):
        raise ValueError("labels.expected_order must be a non-empty unique list of node keys")
    attackable = {node["key"] for node in problem_bundle["payload"]["nodes"]
                  if node["type"] in {"assumption", "constraint", "unknown"}}
    if not set(expected_order).issubset(attackable):
        raise ValueError("expected_order contains a missing or non-attackable node key")
    if not evaluator_ref:
        raise ValueError("labels.evaluator_ref is required")
    evaluation_id = f"eval_{uuid.uuid4().hex}"
    secret = salt or secrets.token_hex(32)
    commitment_payload = {"evaluation_id": evaluation_id, "problem_sha256": problem_bundle["sha256"],
                          "expected_order": expected_order, "evaluator_ref": evaluator_ref, "salt": secret}
    public_case = {"format": "omega.blind-evaluation-case", "format_version": 1,
                   "evaluation_id": evaluation_id, "problem_bundle": problem_bundle,
                   "scoring_profile": DEFAULT_SCORING_PROFILE.to_dict(),
                   "label_commitment": _digest(commitment_payload)}
    public_case["case_sha256"] = _digest(public_case)
    private_reveal = {"format": "omega.blind-evaluation-reveal", "format_version": 1, **commitment_payload,
                      "label_commitment": public_case["label_commitment"]}
    return {"public_case": public_case, "private_reveal": private_reveal}


def _engine_graph(public_case: dict[str, Any]) -> dict[str, Any]:
    bundle = public_case["problem_bundle"]; payload = bundle["payload"]
    nodes = [{**node, "id": node["key"], "problem_id": public_case["evaluation_id"],
              "role": node.get("role") or DEFAULT_ROLES[node["type"]], "created_at": "evaluation"}
             for node in payload["nodes"]]
    edges = [{"id": f"edge-{index}", "problem_id": public_case["evaluation_id"],
              "source_id": edge["source"], "target_id": edge["target"], "type": edge["type"]}
             for index, edge in enumerate(payload["edges"])]
    return {"problem": {"id": public_case["evaluation_id"], **payload["problem"]}, "nodes": nodes, "edges": edges}


def run_blind_case(public_case: dict[str, Any]) -> dict[str, Any]:
    supplied_hash = public_case.get("case_sha256"); unsigned = {k: v for k, v in public_case.items() if k != "case_sha256"}
    if supplied_hash != _digest(unsigned):
        raise ValueError("public evaluation case fingerprint mismatch")
    if public_case.get("format") != "omega.blind-evaluation-case" or public_case.get("format_version") != 1:
        raise ValueError("unsupported public evaluation case")
    _verify_bundle(public_case["problem_bundle"])
    if public_case.get("scoring_profile") != DEFAULT_SCORING_PROFILE.to_dict():
        raise ValueError("evaluation scoring profile does not match the locked default")
    result = Engine(_engine_graph(public_case)).break_it()
    prediction = {"format": "omega.blind-evaluation-prediction", "format_version": 1,
                  "evaluation_id": public_case["evaluation_id"], "case_sha256": supplied_hash,
                  "contract_version": result["contract_version"], "scoring_profile": result["scoring_profile"],
                  "predicted_order": [item["node"]["id"] for item in result["attack_order"]],
                  "scores": {item["node"]["id"]: item["fragility"] for item in result["attack_order"]}}
    prediction["prediction_sha256"] = _digest(prediction)
    return prediction


def score_reveal(public_case: dict[str, Any], prediction: dict[str, Any], reveal: dict[str, Any]) -> dict[str, Any]:
    rerun = run_blind_case(public_case)
    unsigned_prediction = {k: v for k, v in prediction.items() if k != "prediction_sha256"}
    if prediction.get("prediction_sha256") != _digest(unsigned_prediction) or prediction != rerun:
        raise ValueError("prediction fingerprint or deterministic replay mismatch")
    if reveal.get("format") != "omega.blind-evaluation-reveal" or reveal.get("format_version") != 1:
        raise ValueError("unsupported evaluation reveal")
    commitment_payload = {key: reveal.get(key) for key in
                          ("evaluation_id", "problem_sha256", "expected_order", "evaluator_ref", "salt")}
    if (_digest(commitment_payload) != public_case["label_commitment"]
            or reveal.get("label_commitment") != public_case["label_commitment"]
            or reveal.get("evaluation_id") != public_case["evaluation_id"]
            or reveal.get("problem_sha256") != public_case["problem_bundle"]["sha256"]):
        raise ValueError("label commitment verification failed")
    expected, actual = reveal["expected_order"], prediction["predicted_order"]
    first_rank = actual.index(expected[0]) + 1 if expected[0] in actual else None
    comparable, agreements = 0, 0
    for index, left in enumerate(expected):
        for right in expected[index + 1:]:
            comparable += 1
            if left in actual and right in actual and actual.index(left) < actual.index(right):
                agreements += 1
    metrics = {"top1": first_rank == 1, "expected_first_rank": first_rank,
               "reciprocal_rank": round(1 / first_rank, 4) if first_rank else 0.0,
               "pairwise_agreement": round(agreements / comparable, 4) if comparable else 1.0}
    record = {"format": "omega.blind-evaluation-result", "format_version": 1,
              "evaluation_id": public_case["evaluation_id"], "case_sha256": public_case["case_sha256"],
              "prediction_sha256": prediction["prediction_sha256"], "label_commitment": public_case["label_commitment"],
              "evaluator_ref": reveal["evaluator_ref"], "expected_order": expected,
              "predicted_order": actual, "metrics": metrics, "verified": True,
              "contract_version": CONTRACT_VERSION}
    record["record_sha256"] = _digest(record)
    return record


def aggregate_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    if not records:
        raise ValueError("at least one evaluation record is required")
    seen = set()
    for record in records:
        unsigned = {k: v for k, v in record.items() if k != "record_sha256"}
        if not record.get("verified") or record.get("record_sha256") != _digest(unsigned):
            raise ValueError("evaluation record fingerprint or verification flag is invalid")
        if record["evaluation_id"] in seen:
            raise ValueError("duplicate evaluation_id")
        seen.add(record["evaluation_id"])
    count = len(records)
    independent = len({r["evaluator_ref"] for r in records})
    return {"format": "omega.blind-evaluation-summary", "format_version": 1,
            "records": count, "independent_evaluator_refs": independent,
            "metrics": {"top1_accuracy": sum(r["metrics"]["top1"] for r in records) / count,
                        "mean_reciprocal_rank": round(sum(r["metrics"]["reciprocal_rank"] for r in records) / count, 4),
                        "mean_pairwise_agreement": round(sum(r["metrics"]["pairwise_agreement"] for r in records) / count, 4)},
            "evidence_gate": {"minimum_independent_evaluators": 2,
                              "satisfied": independent >= 2,
                              "remaining": max(0, 2 - independent)},
            "note": "Evaluator references are self-declared pseudonyms, not cryptographic identity proof; metrics describe ranking agreement, not proven usefulness."}


def run_protocol_gate() -> dict[str, Any]:
    payload = {"format": "omega.problem-bundle", "format_version": 1,
               "problem": {"title": "Protocol gate", "description": "Blinding integrity"},
               "nodes": [
                   {"key": "weak", "type": "unknown", "role": "question", "statement": "Weakest premise",
                    "confidence": 0.1, "evidence": [], "status": "open"},
                   {"key": "strong", "type": "assumption", "role": "hypothesis", "statement": "Stronger premise",
                    "confidence": 0.8, "evidence": [], "status": "open"}], "edges": []}
    bundle = {"payload": payload, "sha256": _digest(payload)}
    prepared = prepare_blind_case(bundle, {"expected_order": ["weak", "strong"], "evaluator_ref": "protocol-gate"},
                                  salt="fixed-gate-salt")
    public, reveal = prepared["public_case"], prepared["private_reveal"]
    prediction = run_blind_case(public); result = score_reveal(public, prediction, reveal)
    tampered = {**reveal, "expected_order": ["strong", "weak"]}
    try:
        score_reveal(public, prediction, tampered); tamper_rejected = False
    except ValueError:
        tamper_rejected = True
    public_is_blind = "expected_order" not in _canonical(public) and "evaluator_ref" not in _canonical(public)
    passed = result["verified"] and result["metrics"]["top1"] and tamper_rejected and public_is_blind
    return {"passed": passed, "public_is_blind": public_is_blind, "tamper_rejected": tamper_rejected,
            "verified_result": result["verified"], "top1": result["metrics"]["top1"]}
