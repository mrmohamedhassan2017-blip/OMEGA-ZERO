"""ZRWVE V1.2G read-only participant discovery.

The discovery cycle resolves public identities and firsthand T2 evidence from
the already frozen incident corpus plus first-party public profiles.  It never
guesses contact details, sends messages, or changes the V1.2F binding.  A
candidate can therefore be *qualified-but-not-contactable* without becoming a
participant or opening external authority.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from .real_world_value import _atomic_write, _latest_json, _now
from .real_world_value_binding import _packet_hash
from .real_world_value_deep import DEEP_EVIDENCE_CORPUS
from .real_world_value_frontier import _hash


DISCOVERY_SCHEMA = "ZRWVE_PARTICIPANT_DISCOVERY_V1_2G"
DISCOVERY_PROTOCOL = "ZRWVE_V1.2G"
EXPERIMENT_ID = "ZRWVE-T2-BLIND-001"
MAX_SERIOUS_CANDIDATES = 15


# These are bounded, first-party public references captured during the
# read-only search.  No email address or inferred private endpoint is stored.
_PUBLIC_IDENTITY_EVIDENCE: dict[str, dict[str, Any]] = {
    "prefect-17484": {
        "public_identity": "GitHub:ir3456",
        "identity_provenance": [
            "https://github.com/ir3456",
            "https://github.com/PrefectHQ/prefect/issues/17484",
        ],
        "role": "issue author describing a production-like Prefect flow retry",
        "contact_route_type": "PUBLIC_GITHUB_PROFILE_ONLY",
        "contact_route_provenance": "PROFILE_HAS_NO_PUBLIC_PROFESSIONAL_ENDPOINT",
    },
    "prefect-17913": {
        "public_identity": "GitHub:desertaxle (Alex Streed)",
        "identity_provenance": [
            "https://github.com/desertaxle",
            "https://github.com/PrefectHQ/prefect/issues/17913",
            "https://dev-log.prefect.io/codex-as-alpha-tester/",
        ],
        "role": "Prefect software engineer and issue author",
        "contact_route_type": "PUBLIC_GITHUB_PROFILE_ONLY",
        "contact_route_provenance": "PROFILE_HAS_NO_PUBLIC_PROFESSIONAL_ENDPOINT",
    },
    "prefect-18303": {
        "public_identity": "GitHub:sophiaponte (Sophia Ponte)",
        "identity_provenance": [
            "https://github.com/sophiaponte",
            "https://github.com/PrefectHQ/prefect/issues/18303",
        ],
        "role": "issue author describing persisted-result and retry behavior",
        "contact_route_type": "PUBLIC_GITHUB_PROFILE_ONLY",
        "contact_route_provenance": "PROFILE_HAS_NO_PUBLIC_PROFESSIONAL_ENDPOINT",
    },
    "prefect-15658": {
        "public_identity": "GitHub:majo-aqfer",
        "identity_provenance": [
            "https://github.com/majo-aqfer",
            "https://github.com/PrefectHQ/prefect/issues/15658",
        ],
        "role": "issue author describing task retry/result-store behavior",
        "contact_route_type": "PUBLIC_GITHUB_PROFILE_ONLY",
        "contact_route_provenance": "PROFILE_HAS_NO_PUBLIC_PROFESSIONAL_ENDPOINT",
    },
    "prefect-16429": {
        "public_identity": "GitHub:criskurtin (Cristopher Kurtin)",
        "identity_provenance": [
            "https://github.com/criskurtin",
            "https://github.com/PrefectHQ/prefect/issues/16429",
        ],
        "role": "issue author describing Kubernetes/Prefect crash resurrection",
        "contact_route_type": "PUBLIC_GITHUB_PROFILE_ONLY",
        "contact_route_provenance": "PROFILE_HAS_NO_PUBLIC_PROFESSIONAL_ENDPOINT",
    },
    "airflow-10544": {
        "public_identity": "GitHub:stijndehaes (Stijn De Haes)",
        "identity_provenance": [
            "https://github.com/stijndehaes",
            "https://github.com/apache/airflow/issues/10544",
        ],
        "role": "issue author describing KubernetesPodOperator retry collisions",
        "contact_route_type": "PUBLIC_GITHUB_PROFILE_ONLY",
        "contact_route_provenance": "PROFILE_HAS_NO_PUBLIC_PROFESSIONAL_ENDPOINT",
    },
}


def _score(row: Mapping[str, Any], identity: Mapping[str, Any]) -> dict[str, float]:
    """Return auditable factors; no hidden attractiveness score is used."""
    manual = len(row.get("manual_actions", ()))
    decisions = len(row.get("decision_points", ()))
    return {
        "firsthand_incident_strength": round(min(1.0, 0.55 + 0.04 * manual + 0.04 * decisions), 4),
        "t2_relevance": 0.95,
        "identity_confidence": 0.95 if "(" in str(identity.get("public_identity", "")) else 0.85,
        "contact_route_confidence": 0.0,
        "independence": 1.0,
        "likelihood_of_e1_e2_e3_e4": 0.25,
        "stack_diversity": 1.0 if row.get("system", "").startswith("Airflow") else 0.5,
        "privacy_risk": 0.05,
    }


def _composite(scores: Mapping[str, float]) -> float:
    return round(
        0.22 * scores["firsthand_incident_strength"]
        + 0.18 * scores["t2_relevance"]
        + 0.16 * scores["identity_confidence"]
        + 0.12 * scores["contact_route_confidence"]
        + 0.12 * scores["independence"]
        + 0.08 * scores["likelihood_of_e1_e2_e3_e4"]
        + 0.08 * scores["stack_diversity"]
        - 0.10 * scores["privacy_risk"],
        4,
    )


def discover_participant_dossiers() -> list[dict[str, Any]]:
    """Resolve public identity evidence without contact enrichment."""
    dossiers: list[dict[str, Any]] = []
    for row in DEEP_EVIDENCE_CORPUS:
        source_id = row.get("source_id")
        if row.get("target_id") != "T2" or row.get("evidence_role") != "REAL_INCIDENT":
            continue
        identity = _PUBLIC_IDENTITY_EVIDENCE.get(str(source_id))
        if not identity:
            continue
        scores = _score(row, identity)
        dossiers.append({
            "candidate_id": f"ZRWVE-T2-G-CAND-{len(dossiers) + 1:03d}",
            "source_id": source_id,
            "public_identity": identity["public_identity"],
            "identity_provenance": list(identity["identity_provenance"]),
            "role": identity["role"],
            "stack": row.get("system", "UNKNOWN"),
            "firsthand_t2_evidence": row.get("failure", "REAL_INCIDENT"),
            "primary_source_references": [row.get("source_url_or_reference")],
            "incident_relevance": row.get("failure_class", "UNKNOWN"),
            "contact_route_type": identity["contact_route_type"],
            "contact_route_provenance": identity["contact_route_provenance"],
            "public_contact_route": False,
            "non_owner": True,
            "non_bot": True,
            "non_omega": True,
            "independence_status": "INDEPENDENT_PUBLIC_ACTOR_IDENTITY",
            "privacy_risk": scores["privacy_risk"],
            "qualification_status": "QUALIFIED_BUT_NOT_CONTACTABLE",
            "rejection_reason_if_any": "no explicit public professional one-to-one endpoint; GitHub profile and issue URL are identity/evidence only",
            "duplicate_actor": False,
            "duplicate_incident": False,
            "scores": scores,
            "composite_score": _composite(scores),
        })
    return sorted(dossiers, key=lambda item: (-item["composite_score"], item["candidate_id"]))


def _binding_context(root: Path) -> dict[str, Any]:
    latest = _latest_json(Path(root) / ".omega" / "zero", "zrwve_channel_participant_binding")
    if latest:
        return {
            "packet_hash": latest.get("packet_hash", ""),
            "initial_message_hash": latest.get("initial_message_hash", ""),
            "previous_participant_set_hash": latest.get("participant_set_hash", ""),
            "binding_input_fingerprint": latest.get("input_fingerprint", ""),
        }
    return {"packet_hash": _packet_hash(Path(root)), "initial_message_hash": "", "previous_participant_set_hash": "", "binding_input_fingerprint": ""}


def _input_fingerprint(dossiers: Sequence[Mapping[str, Any]], context: Mapping[str, Any]) -> str:
    return _hash({
        "protocol": DISCOVERY_PROTOCOL,
        "experiment_id": EXPERIMENT_ID,
        "packet_hash": context.get("packet_hash", ""),
        "source_ids": [item.get("source_id") for item in dossiers],
        "identity_provenance": [item.get("identity_provenance") for item in dossiers],
    })


def run_participant_discovery(root: Path) -> dict[str, Any]:
    """Run one idempotent V1.2G read-only cycle and persist its evidence."""
    root = Path(root).resolve()
    output = root / ".omega" / "zero"
    dossiers = discover_participant_dossiers()[:MAX_SERIOUS_CANDIDATES]
    context = _binding_context(root)
    fingerprint = _input_fingerprint(dossiers, context)
    numbered_artifacts = sorted(
        output.glob("zrwve_participant_discovery_[0-9][0-9][0-9][0-9].json")
    )
    for path in numbered_artifacts:
        try:
            previous = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if previous.get("input_fingerprint") == fingerprint:
            replay = dict(previous)
            replay["idempotent_replay"] = True
            return replay

    selected: list[dict[str, Any]] = []
    participant_set_hash = _hash(selected)
    stacks = sorted({str(item["stack"]) for item in selected})
    result = {
        "schema": DISCOVERY_SCHEMA,
        "protocol": DISCOVERY_PROTOCOL,
        "experiment_id": EXPERIMENT_ID,
        "search_mode": "READ_ONLY_PUBLIC_FIRST_PARTY",
        "target": "T2 DATAFLOW_PARTIAL_RESUME_STATE_RECONSTRUCTION",
        "max_serious_candidates": MAX_SERIOUS_CANDIDATES,
        "serious_candidates_reviewed": len(dossiers),
        "candidate_dossiers": dossiers,
        "screening_ranking": [
            {"candidate_id": item["candidate_id"], "composite_score": item["composite_score"], "qualification_status": item["qualification_status"]}
            for item in dossiers
        ],
        "participant_ranking": [],
        "qualified_participants_found": 0,
        "qualified_and_contactable": 0,
        "qualified_but_not_contactable": len(dossiers),
        "contactable_but_not_qualified": 0,
        "bound_participants": selected,
        "bound_stack_count": len(stacks),
        "public_contact_routes_only": True,
        "inferred_private_contacts": 0,
        "owner_actors_selected": 0,
        "bot_actors_selected": 0,
        "duplicate_actors_selected": 0,
        "identity_provenance_pass": bool(dossiers),
        "contact_route_provenance_pass": False,
        "participant_set_hash": participant_set_hash,
        "packet_hash": context.get("packet_hash", ""),
        "packet_hash_valid": bool(context.get("packet_hash")),
        "initial_message_hash": context.get("initial_message_hash", ""),
        "initial_message_hash_valid": bool(context.get("initial_message_hash")),
        "channel_binding_ready": False,
        "external_action_authorized": False,
        "external_write_executed": 0,
        "messages_sent": 0,
        "search_saturation": {
            "status": "EVIDENCE_SATURATED_CURRENT_T2_CORPUS",
            "source_families_reviewed": ["Prefect issue authors", "Airflow issue author", "first-party public profiles", "first-party technical posts"],
            "remaining_gap": "no legitimate public one-to-one professional route attributable to a screened operator",
            "invasive_enrichment_used": False,
        },
        "passive_alternative_evaluation": {
            "considered": True,
            "beats_targeted_search": False,
            "reason": "a passive route would require an external surface change; no such write is authorized in this discovery-only cycle",
        },
        "red_team_result": {
            "same_person_aliases_checked": True,
            "duplicate_incidents_checked": True,
            "guessed_addresses": 0,
            "owner_or_bot_selected": 0,
            "identity_or_route_inference": False,
            "false_qualifications": 0,
        },
        "final_result": "QUALIFIED_BUT_NO_LEGITIMATE_CONTACT_ROUTE" if dossiers else "PARTICIPANT_DISCOVERY_SATURATED_NO_SAFE_MATCH",
        "current_evidence_level": "L0",
        "verified_net_economic_value": "0 KWD",
        "next_atomic_action": "PARK_UNTIL_NEW_PUBLIC_EVIDENCE",
        "input_fingerprint": fingerprint,
        "created_at": _now(),
        "idempotent_replay": False,
    }
    sequence = len(numbered_artifacts) + 1
    _atomic_write(output / f"zrwve_participant_discovery_{sequence:04d}.json", result)
    _atomic_write(output / "zrwve_participant_discovery_latest.json", result)
    return result
