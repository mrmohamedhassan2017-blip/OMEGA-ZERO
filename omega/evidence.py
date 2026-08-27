from __future__ import annotations

from datetime import datetime
from typing import Any

VERIFICATION_STATES = {"unverified", "corroborated", "reproduced", "disputed", "retracted", "legacy"}


def normalize_evidence(records: list[Any] | None) -> list[dict[str, Any]]:
    normalized = []
    for item in records or []:
        if isinstance(item, str):
            if not item.strip():
                raise ValueError("evidence source cannot be empty")
            normalized.append({"source": item.strip(), "observed_at": None, "method": "unspecified",
                               "reliability": 0.5, "verification_status": "legacy", "note": None})
            continue
        if not isinstance(item, dict):
            raise ValueError("each evidence record must be a string or object")
        source = str(item.get("source", "")).strip()
        if not source:
            raise ValueError("evidence.source is required")
        observed_at = item.get("observed_at")
        if observed_at is not None:
            try:
                datetime.fromisoformat(str(observed_at).replace("Z", "+00:00"))
            except ValueError as exc:
                raise ValueError("evidence.observed_at must be ISO-8601") from exc
        reliability = float(item.get("reliability", 0.5))
        if not 0 <= reliability <= 1:
            raise ValueError("evidence.reliability must be between 0 and 1")
        verification = item.get("verification_status", "unverified")
        if verification not in VERIFICATION_STATES:
            raise ValueError(f"evidence.verification_status must be one of {sorted(VERIFICATION_STATES)}")
        normalized.append({"source": source, "observed_at": observed_at,
                           "method": str(item.get("method", "unspecified")), "reliability": reliability,
                           "verification_status": verification, "note": item.get("note")})
    return normalized


def evidence_strength(records: list[dict[str, Any]]) -> float:
    if not records:
        return 0.0
    state_weight = {"reproduced": 1.0, "corroborated": 0.8, "unverified": 0.45,
                    "legacy": 0.3, "disputed": 0.15, "retracted": 0.0}
    scores = [record["reliability"] * state_weight[record["verification_status"]] for record in records]
    # More independent evidence helps, but cannot exceed the strongest record by more than 0.2.
    return round(min(1.0, max(scores) + min(0.2, 0.05 * (len(scores) - 1))), 3)

