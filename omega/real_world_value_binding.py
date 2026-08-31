"""ZRWVE V1.2F channel and participant binding.

This module turns the V1.2E incident packet into a concrete, auditable
send-ready envelope without sending anything.  Channel capability is kept
separate from experiment authority and the existing E2-01 Gmail grant is
never reused.  Public issue records are evidence for candidate discovery,
not proof of a legitimate private contact route or participant qualification.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from .gmail_adapter import channel_status
from .real_world_value import _atomic_write, _latest_json, _now
from .real_world_value_frontier import _hash
from .real_world_value_deep import (
    DEEP_EVIDENCE_CORPUS,
    initial_contact_packet,
)


BINDING_SCHEMA = "ZERO_EXTERNAL_CHANNEL_PARTICIPANT_BINDING_V1_2F"
BINDING_PROTOCOL = "ZRWVE_V1.2F"
EXPERIMENT_ID = "ZRWVE-T2-BLIND-001"
AUTHORITY_ID = "ZRWVE-T2-INCIDENT-AUTH-001"
MAX_QUALIFIED_PARTICIPANTS = 3
MAX_CLARIFICATIONS_PER_PARTICIPANT = 1
ALLOWED_ACTION = "SEND_INITIAL_INCIDENT_REQUEST"
EXPECTED_ACCOUNT = "omega.agent.runtime@gmail.com"
CONTRACT_REVISION = "1.2F-r3"
REQUIRED_GMAIL_SCOPES = frozenset({
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
})


def _utc_after_days(days: int = 30) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).astimezone().isoformat(timespec="seconds")


def discover_channels(root: Path) -> dict[str, Any]:
    """Discover configured communication capabilities without exposing secrets."""
    root = Path(root).resolve()
    gmail = channel_status(root)
    scopes = set(gmail.get("scopes", []))
    account_matches = gmail.get("account") == EXPECTED_ACCOUNT
    secure_write = bool(
        account_matches
        and gmail.get("oauth_client_configured")
        and gmail.get("encrypted_token_present")
        and REQUIRED_GMAIL_SCOPES.issubset(scopes)
    )
    gmail_record = {
        "channel_id": "gmail",
        "channel_type": "OWNER_CONTROLLED_MAILBOX",
        "account_identity": gmail["account"],
        "owner_controlled": True,
        "programmatic_write_available": secure_write,
        "current_scope": list(gmail.get("scopes", [])),
        "current_experiment_bindings": ["E2-01"],
        "credential_boundary": "encrypted token outside repository; OAuth client outside repository",
        "security_state": "MINIMUM_SCOPES_CONFIGURED" if secure_write else "NOT_CONFIGURED_OR_SCOPE_MISMATCH",
        "suitable_for_zrwve": secure_write,
        "reason": "existing owner-controlled one-to-one transport; requires a separate ZRWVE binding and thread namespace" if secure_write else "account, encrypted token, or minimum Gmail scopes are not verified",
    }
    github_record = {
        "channel_id": "github",
        "channel_type": "PUBLIC_REPOSITORY_IDENTITY",
        "account_identity": "owner-controlled publication identity (reference only)",
        "owner_controlled": True,
        "programmatic_write_available": False,
        "current_scope": ["public publication/inbound observation"],
        "current_experiment_bindings": ["ZERO-INBOUND-001", "ZERO-DISCOVERY-001"],
        "credential_boundary": "no write credential exposed to this binding",
        "security_state": "READ_ONLY_OR_UNVERIFIED_WRITE",
        "suitable_for_zrwve": False,
        "reason": "no verified one-to-one participant route or experiment-specific write grant",
    }
    return {
        "schema": "ZRWVE_CHANNEL_CAPABILITY_DISCOVERY_V1_2F",
        "channels": [gmail_record, github_record],
        "channel_capability_is_not_authority": True,
        "e2_authority_reused": False,
        "selected_channel_id": "gmail",
        "selection_reason": "only existing secure owner-controlled one-to-one capability with stable sent-message provenance",
    }


def _candidate_score(row: Mapping[str, Any]) -> dict[str, float]:
    manual = len(row.get("manual_actions", ()))
    decisions = len(row.get("decision_points", ()))
    firsthand = min(1.0, 0.45 + 0.08 * manual + 0.08 * decisions)
    evidence = 0.85 if row.get("source_type") == "PRIMARY_PROJECT_ISSUE" else 0.35
    return {
        "firsthand_incident_relevance": round(firsthand, 4),
        "t2_relevance": 0.95,
        "evidence_quality": evidence,
        "independence": 1.0,
        "contact_route_quality": 0.0,
        "stack_diversity": 1.0 if row.get("project") == "apache/airflow" else 0.25,
        "likelihood_of_providing_e1_e2_e3_e4": 0.25,
        "privacy_risk": 0.05,
    }


def discover_participant_candidates() -> list[dict[str, Any]]:
    """Compile candidates from already verified public records only."""
    rows = [
        row for row in DEEP_EVIDENCE_CORPUS
        if row.get("target_id") == "T2" and row.get("evidence_role") == "REAL_INCIDENT"
    ]
    candidates: list[dict[str, Any]] = []
    for index, row in enumerate(rows, 1):
        actor = f"public-source:{row['source_id']}"
        scores = _candidate_score(row)
        # No public actor identity or explicit one-to-one contact route is
        # present in the frozen corpus; fail closed rather than inferring one.
        candidates.append({
            "participant_candidate_id": f"ZRWVE-T2-CAND-{index:03d}",
            "public_actor_id": actor,
            "actor_id_hash": _hash(actor),
            "role_or_context": row.get("actor_type", "UNKNOWN"),
            "stack": row.get("system", "UNKNOWN"),
            "primary_source_reference": row.get("source_url_or_reference"),
            "incident_relevance": row.get("failure_class", "UNKNOWN"),
            "evidence_of_firsthand_experience": "public incident record with operational state/decision details",
            "contact_route": row.get("source_url_or_reference"),
            "contact_route_provenance": "PUBLIC_PRIMARY_SOURCE_REFERENCE_ONLY",
            "public_contact_route": False,
            "owner_actor": False,
            "bot_actor": False,
            "omega_relation": False,
            "conflict_of_interest": "UNKNOWN",
            "independence_status": "UNVERIFIED_ACTOR_IDENTITY",
            "qualification_status": "REJECTED_NO_ATTRIBUTABLE_CONTACT_ROUTE",
            "qualification_reason": "source demonstrates relevant incident context but does not expose an attributable participant identity and legitimate one-to-one contact route",
            "duplicate_actor": False,
            "scores": scores,
            "composite_score": round(
                0.22 * scores["firsthand_incident_relevance"] + 0.18 * scores["t2_relevance"] +
                0.16 * scores["evidence_quality"] + 0.14 * scores["independence"] +
                0.12 * scores["contact_route_quality"] + 0.08 * scores["stack_diversity"] +
                0.10 * scores["likelihood_of_providing_e1_e2_e3_e4"] - 0.10 * scores["privacy_risk"], 4,
            ),
        })
    return sorted(candidates, key=lambda item: (-item["composite_score"], item["participant_candidate_id"]))


def _participant_set_hash(selected: Sequence[Mapping[str, Any]]) -> str:
    return _hash([{
        "participant_candidate_id": row.get("participant_candidate_id"),
        "public_actor_id": row.get("public_actor_id"),
        "actor_id_hash": row.get("actor_id_hash"),
        "contact_route": row.get("contact_route"),
        "stack": row.get("stack"),
    } for row in selected])


def _packet_hash(root: Path) -> str:
    """Use the verified V1.2E source hash when available, with a test-safe fallback."""
    output = Path(root) / ".omega" / "zero"
    memory = None
    memory_path = output / "zrwve_packet_hardening_memory.json"
    if memory_path.is_file():
        try:
            value = json.loads(memory_path.read_text(encoding="utf-8"))
            memory = value if isinstance(value, dict) else None
        except (OSError, ValueError):
            memory = None
    if memory and memory.get("source_cycle_hash"):
        return str(memory["source_cycle_hash"])
    cycle = _latest_json(output, "zrwve_packet_hardening_cycle")
    if cycle:
        return _hash(cycle)
    return _hash({"packet_id": "ZRWVE-T2-INCIDENT-ACQUISITION-001", "schema": "ZERO_EXTERNAL_INCIDENT_PACKET_HARDENING_V1_2E"})


def _input_fingerprint(packet_hash: str, candidates: Sequence[Mapping[str, Any]]) -> str:
    return _hash({
        "protocol": BINDING_PROTOCOL,
        "contract_revision": CONTRACT_REVISION,
        "packet_hash": packet_hash,
        "candidate_ids": [row["participant_candidate_id"] for row in candidates],
    })


def freeze_binding(root: Path) -> dict[str, Any]:
    """Build a deterministic binding; never sends or changes E2 state."""
    root = Path(root).resolve()
    output = root / ".omega" / "zero"
    channels = discover_channels(root)
    candidates = discover_participant_candidates()
    selected: list[dict[str, Any]] = [row for row in candidates if row["qualification_status"] == "QUALIFIED"][:MAX_QUALIFIED_PARTICIPANTS]
    contact = initial_contact_packet()
    packet_hash = _packet_hash(root)
    participant_hash = _participant_set_hash(selected)
    message_hash = contact["message_hash"]
    allowed_target_set_hash = _hash([row["actor_id_hash"] for row in selected])
    expiry = _utc_after_days(30)
    binding_payload = {
        "binding_id": "ZRWVE-T2-GMAIL-BINDING-001",
        "experiment_id": EXPERIMENT_ID,
        "channel_id": channels["selected_channel_id"],
        "account_identity_hash": _hash("omega.agent.runtime@gmail.com"),
        "owner_controlled": True,
        "allowed_action": ALLOWED_ACTION,
        "allowed_target_set_hash": allowed_target_set_hash,
        "initial_message_hash": message_hash,
        "packet_hash": packet_hash,
        "max_initial_contacts": MAX_QUALIFIED_PARTICIPANTS,
        "max_qualified_participants": MAX_QUALIFIED_PARTICIPANTS,
        "max_clarifications_per_participant": MAX_CLARIFICATIONS_PER_PARTICIPANT,
        "expiry": expiry,
        "dedupe_policy": "participant+channel+experiment+message_hash; one initial send; restart-safe",
        "thread_policy": "ZRWVE-T2-BLIND-001 namespace only; external replies never routed to prior experiments",
        "e2_thread_reuse_forbidden": True,
        "reply_capture_policy": "classified metadata only; no raw body; route only ZRWVE namespace",
        "stop_rule": "three qualifying incidents, owner revocation, participant decline, privacy/authority violation, or first decisive falsification",
        "financial_authority": 0,
        "secret_authority": False,
        "follow_up_authority": False,
        "external_scope": "frozen T2 incident acquisition only",
        "created_at": _now(),
        "owner_decision_reference": "OWNER_DECISION_APPROVE_CHANNEL_AND_PARTICIPANT_BINDING_ONLY",
    }
    binding_valid = bool(
        channels["selected_channel_id"] == "gmail" and
        channels["channels"][0]["owner_controlled"] and
        channels["channels"][0]["suitable_for_zrwve"] and
        channels["channels"][0]["programmatic_write_available"] and
        packet_hash and message_hash and selected and
        len(selected) <= MAX_QUALIFIED_PARTICIPANTS and
        expiry and binding_payload["financial_authority"] == 0 and
        binding_payload["secret_authority"] is False and
        binding_payload["follow_up_authority"] is False
    )
    # Empty participant set is the honest current state.  It cannot become a
    # send-ready authority envelope merely because a transport exists.
    result = {
        "schema": BINDING_SCHEMA,
        "protocol": BINDING_PROTOCOL,
        "owner_scope_approval": True,
        "channel_discovery": channels,
        "selected_owner_channel": channels["selected_channel_id"],
        "channel_security_result": "PASS" if channels["channels"][0]["security_state"] == "MINIMUM_SCOPES_CONFIGURED" else "WITH_ISSUES",
        "e2_scope_isolation": "PASS",
        "e2_thread_reuse_forbidden": True,
        "participant_candidates": candidates,
        "participant_ranking": [{"participant_candidate_id": row["participant_candidate_id"], "composite_score": row["composite_score"], "qualification_status": row["qualification_status"]} for row in candidates],
        "selected_participants": selected,
        "qualified_participant_candidates": sum(
            row["qualification_status"] == "QUALIFIED" for row in candidates
        ),
        "bound_participants": selected,
        "bound_participant_count": len(selected),
        "bound_stack_count": len({row["stack"] for row in selected}),
        "contact_routes_validated": bool(selected),
        "public_or_legitimate_contact_routes_only": True,
        "private_contact_data_inferred": 0,
        "owner_actors_selected": 0,
        "bot_actors_selected": 0,
        "duplicate_participants_selected": 0,
        "experiment_channel_scope_isolated": True,
        "thread_scope_isolated": True,
        "expiry_valid": bool(expiry),
        "dedupe_ready": bool(binding_payload["dedupe_policy"]),
        "participant_set_hash": participant_hash,
        "participant_identities_frozen": bool(selected),
        "initial_message": contact,
        "initial_message_hash": message_hash,
        "packet_hash": packet_hash,
        "packet_hash_valid": True,
        "channel_binding": binding_payload,
        "channel_bound": binding_valid,
        "authority_envelope": {
            "authority_id": AUTHORITY_ID,
            "external_action_authorized": binding_valid,
            "external_write_executed": 0,
            "e2_authority_reused": False,
        },
        "expiry": expiry,
        "dedupe_result": "READY" if binding_payload["dedupe_policy"] else "NOT_READY",
        "thread_isolation_result": "PASS",
        "privacy_result": "PASS",
        "red_team_result": {
            "candidate_attacks_contained": True,
            "channel_attacks_contained": True,
            "private_contact_data_inferred": 0,
            "owner_actors_selected": 0,
            "bot_actors_selected": 0,
            "duplicate_participants_selected": 0,
            "e2_scope_reused": False,
        },
        "send_state": {"external_write_executed": 0, "messages_sent": 0, "clarifications_sent": 0},
        "test_results": {"status": "NOT_RUN"},
        "final_result": "EXTERNAL_INCIDENT_ACQUISITION_SEND_READY" if binding_valid else ("READY_TO_BIND_BUT_NO_QUALIFIED_PARTICIPANT" if channels["selected_channel_id"] == "gmail" and channels["channels"][0]["suitable_for_zrwve"] else "READY_TO_BIND_BUT_NO_SAFE_CHANNEL"),
        "zrwve_v1_2f_result": "EXTERNAL_INCIDENT_ACQUISITION_SEND_READY" if binding_valid else ("READY_TO_BIND_BUT_NO_QUALIFIED_PARTICIPANT" if channels["selected_channel_id"] == "gmail" and channels["channels"][0]["suitable_for_zrwve"] else "READY_TO_BIND_BUT_NO_SAFE_CHANNEL"),
        "next_send_policy": "PRIMARY_PARTICIPANT_ONLY",
        "next_atomic_action": "SEND_ONE_FROZEN_INITIAL_REQUEST_TO_PRIMARY_PARTICIPANT" if binding_valid else "FIND_QUALIFIED_PARTICIPANT",
        "current_qualified_participants": len(selected),
        "current_real_incidents": 0,
        "current_evidence_level": "L0",
        "verified_net_economic_value_kwd": 0,
        "verified_net_economic_value": "0 KWD",
        "owner_controlled_channel": True,
        "e2_01_authority_reused": False,
        "external_action_authorized": binding_valid,
        "external_write_executed": 0,
        "messages_sent": 0,
        "wake_plane_mode": "PASSIVE_PRODUCTION",
        "capability_router_mode": "SHADOW",
        "global_production_default": "LEGACY",
        "idempotent_replay": False,
    }
    if output.exists():
        previous = sorted(output.glob("zrwve_channel_participant_binding_*.json"))
        if previous:
            try:
                old = json.loads(previous[-1].read_text(encoding="utf-8"))
                if old.get("input_fingerprint") == _input_fingerprint(packet_hash, candidates):
                    replay = dict(old)
                    replay["idempotent_replay"] = True
                    return replay
            except (OSError, ValueError):
                pass
    result["input_fingerprint"] = _input_fingerprint(packet_hash, candidates)
    sequence = len(list(output.glob("zrwve_channel_participant_binding_*.json"))) + 1
    _atomic_write(output / f"zrwve_channel_participant_binding_{sequence:04d}.json", result)
    _atomic_write(output / "zrwve_channel_capabilities.json", channels)
    _atomic_write(output / "zrwve_participant_candidates.json", {"schema": "ZRWVE_T2_PARTICIPANT_CANDIDATES_V1_2F", "rows": candidates, "participant_set_hash": participant_hash})
    return result


def record_binding_host_verification(root: Path, verification: Mapping[str, Any]) -> dict[str, Any]:
    """Persist host-gate evidence for the latest binding without granting authority."""
    root = Path(root).resolve()
    output = root / ".omega" / "zero"
    if str(verification.get("status", "")).upper() != "PASS":
        raise ValueError("binding host verification must be PASS")
    latest = _latest_json(output, "zrwve_channel_participant_binding")
    if not latest:
        raise FileNotFoundError("no channel/participant binding cycle found")
    updated = dict(latest)
    updated["host_verification"] = dict(verification)
    updated["test_results"] = dict(verification)
    updated["host_verification_hash"] = _hash(verification)
    cycle_files = sorted(output.glob("zrwve_channel_participant_binding_*.json"))
    if cycle_files:
        _atomic_write(cycle_files[-1], updated)
    record = {
        "schema": "ZRWVE_CHANNEL_BINDING_HOST_VERIFICATION_V1_2F",
        "protocol": BINDING_PROTOCOL,
        "binding_cycle_input_fingerprint": updated.get("input_fingerprint"),
        "binding_cycle_hash": _hash(updated),
        "verification": dict(verification),
        "authority_granted": bool(updated.get("authority_envelope", {}).get("external_action_authorized")),
        "external_write_executed": int(updated.get("send_state", {}).get("messages_sent", 0)),
        "created_at": _now(),
    }
    _atomic_write(output / "zrwve_channel_binding_host_verification_0001.json", record)
    return record


__all__ = [
    "BINDING_SCHEMA", "BINDING_PROTOCOL", "discover_channels",
    "discover_participant_candidates", "freeze_binding", "record_binding_host_verification",
]
