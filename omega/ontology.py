from __future__ import annotations

from typing import Any

NODE_ROLES = {
    "fact": {"observation", "measurement", "event", "verified_claim"},
    "assumption": {"hypothesis", "prediction", "unverified_claim", "risk"},
    "constraint": {"requirement", "limit", "policy", "invariant"},
    "unknown": {"question", "uncertainty", "missing_data"},
}

DEFAULT_ROLES = {"fact": "observation", "assumption": "hypothesis",
                 "constraint": "limit", "unknown": "question"}


def normalize_role(kind: str, role: str | None) -> str:
    selected = role or DEFAULT_ROLES[kind]
    if selected not in NODE_ROLES[kind]:
        raise ValueError(f"role '{selected}' is not valid for node type '{kind}'; expected one of {sorted(NODE_ROLES[kind])}")
    return selected


def taxonomy_reference_cases() -> list[dict[str, Any]]:
    """Human-labelled cases define the intended two-axis ontology boundary."""
    return [
        {"domain": "product", "statement": "12 of 20 interviewed users completed the task", "type": "fact", "role": "measurement"},
        {"domain": "product", "statement": "At least 30% of trial users will pay", "type": "assumption", "role": "prediction"},
        {"domain": "product", "statement": "Launch must satisfy the privacy policy", "type": "constraint", "role": "policy"},
        {"domain": "product", "statement": "The acceptable acquisition cost is not known", "type": "unknown", "role": "missing_data"},
        {"domain": "incident", "statement": "Latency crossed 900 ms at 10:32 UTC", "type": "fact", "role": "event"},
        {"domain": "incident", "statement": "The cache eviction caused the latency spike", "type": "assumption", "role": "hypothesis"},
        {"domain": "incident", "statement": "No customer data may be deleted during recovery", "type": "constraint", "role": "invariant"},
        {"domain": "incident", "statement": "Which deployment introduced the regression?", "type": "unknown", "role": "question"},
        {"domain": "science", "statement": "The sensor recorded 21.4 C", "type": "fact", "role": "observation"},
        {"domain": "science", "statement": "Higher temperature increases reaction rate", "type": "assumption", "role": "unverified_claim"},
        {"domain": "science", "statement": "The apparatus cannot exceed 80 C", "type": "constraint", "role": "limit"},
        {"domain": "science", "statement": "Measurement uncertainty has not been quantified", "type": "unknown", "role": "uncertainty"},
    ]


def run_taxonomy_benchmark() -> dict[str, Any]:
    results = []
    for case in taxonomy_reference_cases():
        try:
            normalized = normalize_role(case["type"], case["role"])
            results.append({**case, "normalized_role": normalized, "passed": True})
        except (KeyError, ValueError) as exc:
            results.append({**case, "passed": False, "error": str(exc)})
    domains = sorted({case["domain"] for case in results})
    type_coverage = sorted({case["type"] for case in results})
    return {"cases": results, "metrics": {"cases": len(results), "domains": domains,
                                             "type_coverage": type_coverage,
                                             "coverage_rate": sum(c["passed"] for c in results) / len(results)},
            "gate_passed": all(case["passed"] for case in results)}

