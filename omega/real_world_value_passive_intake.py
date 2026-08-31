"""ZRWVE V1.2H passive real-incident intake design.

This module is deliberately non-authoritative. It compares passive intake
surfaces, validates a two-stage incident submission, freezes one publication
packet, and records privacy-minimized read-only intake classifications. It
never publishes, sends, or promotes a submission into demand or economic value.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Iterable, Mapping, Sequence

from .real_world_value import _atomic_write, _latest_json, _now
from .real_world_value_deep import (
    b3_configuration_schema,
    blind_transform_spec,
    freeze_incident_packet,
    incident_data_schema,
    operator_trace_schema,
    validate_blind_transform,
    validate_incident_packet,
    verification_criterion_schema,
)
from .real_world_value_frontier import _hash
from .wake_provenance import append_chain, read_chain


PASSIVE_INTAKE_SCHEMA = "ZERO_PASSIVE_REAL_INCIDENT_INTAKE_V1_2H"
PASSIVE_INTAKE_PROTOCOL = "ZRWVE_V1.2H"
EXPERIMENT_ID = "ZRWVE-T2-BLIND-001"
PUBLICATION_ID = "ZRWVE-PASSIVE-INTAKE-PUBLICATION-001"
DESTINATION = "mrmohamedhassan2017-blip/agent-runtime-audit"
EXACT_SURFACE = ".github/ISSUE_TEMPLATE/real-incident-intake.yml"
PASSIVE_INTAKE_WORK_ID = "ZRWVE V1.2H Passive Incident Intake"
PASSIVE_INTAKE_JOURNAL = "zrwve_passive_incident_intake.jsonl"

STAGE1_REQUIRED_FIELDS = (
    "firsthand_t2_experience",
    "stack_or_orchestrator",
    "incident_class",
    "real_incident_exists",
    "incident_relevance_summary",
    "willing_to_provide_sanitized_reconstruction",
    "sanitization_declaration",
    "public_attribution_preference",
)

T2_INCIDENT_CLASSES = frozenset({
    "PARTIAL_WORKFLOW_EXECUTION",
    "RESUME_RETRY_REPLAY",
    "AMBIGUOUS_PERSISTED_STATE",
    "CHECKPOINT_RECOVERY",
    "DOWNSTREAM_SIDE_EFFECT",
    "OPERATOR_RECONCILIATION",
    "RECOVERY_VERIFICATION",
})

SECRET_KEY_MARKERS = frozenset({
    "password", "secret", "token", "access_token", "refresh_token",
    "private_key", "client_secret", "credential", "api_key", "customer_pii",
})
SECRET_VALUE_PATTERNS = (
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"AIza[0-9A-Za-z_-]{20,}"),
    re.compile(r"ya29\.[0-9A-Za-z_-]{10,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
)
PROMPT_INJECTION_MARKERS = (
    "ignore previous", "ignore all previous", "system prompt", "system message",
    "grant authority", "execute command", "run this command", "override threshold",
    "change the constitution", "reveal credentials", "bypass privacy",
)
SPAM_MARKERS = (
    "buy now", "casino", "crypto airdrop", "backlink", "seo service",
    "guaranteed traffic", "sponsored placement",
)
OPINION_MARKERS = (
    "sounds interesting", "this would help", "retries are painful",
    "this happens to us", "we use airflow", "great tool",
)


@dataclass(frozen=True)
class PassiveSourceObservation:
    """Host-observed source identity; participant text cannot construct trust."""

    channel: str
    actor_id: str
    source_event_id: str
    source_event_reference: str
    source_created_at: str
    source_verified: bool
    owner_origin: bool | None
    bot_origin: bool | None
    omega_origin: bool | None


def _text_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _all_text(value: Any) -> str:
    if isinstance(value, Mapping):
        return "\n".join(f"{key}\n{_all_text(item)}" for key, item in value.items())
    if isinstance(value, (list, tuple, set)):
        return "\n".join(_all_text(item) for item in value)
    return str(value)


def _secret_markers(value: Any) -> list[str]:
    markers: set[str] = set()
    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized = re.sub(r"[^a-z0-9]+", "_", str(key).lower()).strip("_")
            if normalized in SECRET_KEY_MARKERS:
                markers.add("forbidden_sensitive_field")
            markers.update(_secret_markers(item))
    elif isinstance(value, (list, tuple, set)):
        for item in value:
            markers.update(_secret_markers(item))
    elif isinstance(value, str):
        if any(pattern.search(value) for pattern in SECRET_VALUE_PATTERNS):
            markers.add("secret_pattern")
    return sorted(markers)


def _prompt_injection_markers(value: Any) -> list[str]:
    lowered = _all_text(value).lower()
    return sorted(marker for marker in PROMPT_INJECTION_MARKERS if marker in lowered)


def _spam_markers(value: Any) -> list[str]:
    lowered = _all_text(value).lower()
    markers = {marker for marker in SPAM_MARKERS if marker in lowered}
    if lowered.count("http://") + lowered.count("https://") > 2:
        markers.add("excessive_links")
    return sorted(markers)


def _truthy(value: Any) -> bool:
    normalized = str(value).strip().upper()
    return normalized in {"YES", "TRUE", "I_HAVE_FIRSTHAND_EXPERIENCE"} or "[X]" in normalized


def _stage1_result_hash(result: Mapping[str, Any]) -> str:
    return _hash({key: value for key, value in result.items() if key != "stage1_result_hash"})


def stage1_schema() -> dict[str, Any]:
    record = {
        "schema": "ZRWVE_PASSIVE_STAGE1_QUALIFICATION_V1_2H",
        "required_fields": list(STAGE1_REQUIRED_FIELDS),
        "allowed_incident_classes": sorted(T2_INCIDENT_CLASSES),
        "purpose": "voluntary qualification only; self-qualification is not provenance",
        "accepted_channels": ["github_issue"],
        "public_attribution_options": ["PUBLIC_GITHUB_IDENTITY", "PSEUDONYMOUS_IN_REPORT"],
        "internal_dedupe_identity": "SHA256(channel + immutable actor id)",
        "opinion_alone_counts": False,
        "participant_must_initiate": True,
        "stage2_not_required_at_initial_contact": True,
        "never_request": [
            "credentials", "API keys", "tokens", "customer PII", "private production logs",
            "restricted source code", "confidential business information",
        ],
    }
    record["schema_hash"] = _hash(record)
    return record


def stage2_schema() -> dict[str, Any]:
    record = {
        "schema": "ZRWVE_PASSIVE_STAGE2_PACKET_V1_2H",
        "requires_qualified_stage1": True,
        "E1_INCIDENT_DATA": incident_data_schema(),
        "E2_B3_CONFIGURATION": b3_configuration_schema(),
        "E3_OPERATOR_TRACE": operator_trace_schema(),
        "E4_VERIFICATION_CRITERION": verification_criterion_schema(),
        "decision_and_outcome_information_must_remain_separate": True,
        "blind_transform_hash": blind_transform_spec()["transform_hash"],
        "incomplete_state": "PARKED_INCOMPLETE",
        "complete_event": "ZRWVE_REAL_INCIDENT_PACKET_RECEIVED",
    }
    record["schema_hash"] = _hash(record)
    return record


def wake_event_schema() -> dict[str, Any]:
    record = {
        "schema": "ZRWVE_PASSIVE_WAKE_EVENTS_V1_2H",
        "registered_with_wake_plane": False,
        "stage1_event": "ZRWVE_PASSIVE_INCIDENT_SUBMISSION",
        "stage1_wake_conditions": [
            "SOURCE_PROVENANCE_VALID", "NON_DUPLICATE", "T2_RELEVANT",
            "PARTICIPANT_INDEPENDENT", "STAGE1_QUALIFIED",
        ],
        "stage2_event": "ZRWVE_REAL_INCIDENT_PACKET_RECEIVED",
        "stage2_gate": "E1_E2_E3_E4_COMPLETE_AND_BLIND_COMPATIBLE",
        "spam_or_generic_comment_wake": False,
        "host_verification_required": True,
        "external_action_authority_granted": False,
    }
    record["schema_hash"] = _hash(record)
    return record


ISSUE_FORM_DRAFT = """name: Sanitized workflow incident intake
description: Voluntary research intake for interrupted or ambiguous workflow recovery.
title: "[incident-intake] "
body:
  - type: markdown
    attributes:
      value: |
        We are studying how experienced operators recover interrupted or ambiguous workflow state. Cases where existing tooling handled the incident well are equally valuable.
        Do not submit credentials, API keys, tokens, customer PII, private production logs, restricted source code, or confidential business information. Use aliases, redacted identifiers, relative timestamps, sanitized topology, and minimal state excerpts.
        Stage 1 asks only whether a relevant real incident exists. Stage 2 is optional until Stage 1 is qualified. Publication or submission is not evidence of demand, value, or product interest.
  - type: dropdown
    id: firsthand_t2_experience
    attributes:
      label: Firsthand operational experience
      options:
        - I_HAVE_FIRSTHAND_EXPERIENCE
        - NO_FIRSTHAND_EXPERIENCE
    validations:
      required: true
  - type: input
    id: stack_or_orchestrator
    attributes:
      label: Stack / orchestrator
      description: Product or stack name only; do not include private environment identifiers.
    validations:
      required: true
  - type: dropdown
    id: incident_class
    attributes:
      label: Incident class
      options:
        - PARTIAL_WORKFLOW_EXECUTION
        - RESUME_RETRY_REPLAY
        - AMBIGUOUS_PERSISTED_STATE
        - CHECKPOINT_RECOVERY
        - DOWNSTREAM_SIDE_EFFECT
        - OPERATOR_RECONCILIATION
        - RECOVERY_VERIFICATION
        - OTHER_OR_NOT_SURE
    validations:
      required: true
  - type: dropdown
    id: real_incident_exists
    attributes:
      label: Real incident exists
      options:
        - "YES"
        - "NO"
    validations:
      required: true
  - type: textarea
    id: incident_relevance_summary
    attributes:
      label: Incident relevance summary
      description: Two or three sanitized sentences about the state ambiguity; no logs or identifiers.
    validations:
      required: true
  - type: dropdown
    id: willing_to_provide_sanitized_reconstruction
    attributes:
      label: Sanitized reconstruction
      options:
        - "YES"
        - "NO"
    validations:
      required: true
  - type: checkboxes
    id: sanitization_declaration
    attributes:
      label: Sanitization declaration
      options:
        - label: I_WILL_NOT_SHARE_RESTRICTED_DATA
          required: true
  - type: dropdown
    id: public_attribution_preference
    attributes:
      label: Public attribution preference
      options:
        - PUBLIC_GITHUB_IDENTITY
        - PSEUDONYMOUS_IN_REPORT
    validations:
      required: true
  - type: textarea
    id: stage2_packet
    attributes:
      label: Stage 2 incident packet (optional JSON)
      description: Leave blank for Stage 1. After qualification, a sanitized E1/E2/E3/E4 JSON packet may be added by editing this issue.
      render: json
    validations:
      required: false
"""


ISSUE_FORM_LABELS = {
    "Firsthand operational experience": "firsthand_t2_experience",
    "Stack / orchestrator": "stack_or_orchestrator",
    "Incident class": "incident_class",
    "Real incident exists": "real_incident_exists",
    "Incident relevance summary": "incident_relevance_summary",
    "Sanitized reconstruction": "willing_to_provide_sanitized_reconstruction",
    "Sanitization declaration": "sanitization_declaration",
    "Public attribution preference": "public_attribution_preference",
    "Stage 2 incident packet (optional JSON)": "stage2_packet",
}


def validate_issue_form_draft(content: str = ISSUE_FORM_DRAFT) -> dict[str, Any]:
    sections = re.split(r"(?m)^  - type: ", content)
    ids: list[str] = []
    required: dict[str, bool] = {}
    for section in sections[1:]:
        match = re.search(r"(?m)^    id: ([a-z0-9_]+)$", section)
        if not match:
            continue
        field_id = match.group(1)
        ids.append(field_id)
        required[field_id] = bool(re.search(r"(?m)^\s+required: true$", section))
    stage1_ids = set(STAGE1_REQUIRED_FIELDS)
    unique = len(ids) == len(set(ids))
    stage1_complete = stage1_ids.issubset(ids) and all(required.get(field) for field in stage1_ids)
    stage2_optional = "stage2_packet" in ids and required.get("stage2_packet") is False
    privacy = all(marker in content for marker in (
        "credentials", "customer PII", "private production logs", "restricted source code",
    ))
    neutral = all(marker not in content.lower() for marker in (
        "zero solves", "we need users", "would you buy", "prove our system is better",
    ))
    structure = content.startswith("name:") and "\nbody:\n" in content
    return {
        "valid": bool(structure and unique and stage1_complete and stage2_optional and privacy and neutral),
        "field_ids": ids,
        "unique_ids": unique,
        "stage1_complete": stage1_complete,
        "stage2_optional": stage2_optional,
        "privacy_notice_present": privacy,
        "neutral_language": neutral,
    }


def parse_issue_form_body(body: str) -> dict[str, Any]:
    """Parse recognized Issue Form headings only; submitted text remains data."""
    if not isinstance(body, str) or len(body) > 100_000:
        return {"parse_valid": False, "fields": {}, "stage2_packet": None}
    fields: dict[str, str] = {}
    current: str | None = None
    collected: list[str] = []

    def commit() -> None:
        nonlocal collected
        if current:
            fields[current] = "\n".join(collected).strip()
        collected = []

    for line in body.splitlines():
        if line.startswith("### "):
            commit()
            current = ISSUE_FORM_LABELS.get(line[4:].strip())
        elif current:
            collected.append(line)
    commit()
    stage2_raw = fields.pop("stage2_packet", "").strip()
    stage2_packet: dict[str, Any] | None = None
    if stage2_raw:
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", stage2_raw, flags=re.IGNORECASE | re.DOTALL)
        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict):
                stage2_packet = parsed
        except json.JSONDecodeError:
            stage2_packet = None
    return {
        "parse_valid": set(STAGE1_REQUIRED_FIELDS).issubset(fields),
        "fields": fields,
        "stage2_packet": stage2_packet,
        "stage2_present": bool(stage2_raw),
        "stage2_parse_valid": bool(not stage2_raw or stage2_packet is not None),
        "recognized_field_count": len(fields) + (1 if stage2_raw else 0),
        "unrecognized_content_executed": False,
    }


def validate_stage1(
    submission: Mapping[str, Any],
    observation: PassiveSourceObservation,
    *,
    existing_dedupe_keys: Iterable[str] = (),
) -> dict[str, Any]:
    if not isinstance(observation, PassiveSourceObservation):
        raise TypeError("trusted passive source observation required")
    normalized = {str(key): value for key, value in submission.items()}
    missing = sorted(set(STAGE1_REQUIRED_FIELDS) - set(normalized))
    secret_markers = _secret_markers(normalized)
    prompt_markers = _prompt_injection_markers(normalized)
    spam_markers = _spam_markers(normalized)
    incident_class = str(normalized.get("incident_class", "")).strip().upper()
    t2_relevant = incident_class in T2_INCIDENT_CLASSES
    provenance_valid = bool(
        observation.source_verified
        and observation.channel == "github_issue"
        and observation.actor_id
        and observation.source_event_id
        and observation.source_event_reference
    )
    independent = bool(
        provenance_valid
        and observation.owner_origin is False
        and observation.bot_origin is False
        and observation.omega_origin is False
    )
    dedupe_key = _text_hash(f"{observation.channel}|{observation.source_event_id}")
    duplicate = dedupe_key in set(existing_dedupe_keys)
    firsthand = _truthy(normalized.get("firsthand_t2_experience"))
    incident_exists = _truthy(normalized.get("real_incident_exists"))
    willing = _truthy(normalized.get("willing_to_provide_sanitized_reconstruction"))
    declaration = "I_WILL_NOT_SHARE_RESTRICTED_DATA" in str(normalized.get("sanitization_declaration", "")).upper()
    attribution = str(normalized.get("public_attribution_preference", "")).strip().upper()
    attribution_valid = attribution in {"PUBLIC_GITHUB_IDENTITY", "PSEUDONYMOUS_IN_REPORT"}
    stack_present = bool(str(normalized.get("stack_or_orchestrator", "")).strip())
    relevance_present = bool(str(normalized.get("incident_relevance_summary", "")).strip())
    opinion_only = any(marker in _all_text(normalized).lower() for marker in OPINION_MARKERS) and not (
        firsthand and incident_exists and t2_relevant and relevance_present
    )
    qualified = bool(
        not missing and not secret_markers and not prompt_markers and not spam_markers
        and provenance_valid and independent and not duplicate and firsthand and incident_exists
        and willing and declaration and attribution_valid and stack_present and relevance_present
        and t2_relevant and not opinion_only
    )
    if secret_markers:
        classification = "REJECTED_SECRET_OR_PRIVATE_CONTENT"
    elif prompt_markers:
        classification = "REJECTED_PROMPT_INJECTION_DATA"
    elif spam_markers:
        classification = "REJECTED_SPAM"
    elif provenance_valid and not independent:
        classification = "REJECTED_NON_INDEPENDENT"
    elif not provenance_valid:
        classification = "REJECTED_UNVERIFIED_PROVENANCE"
    elif duplicate:
        classification = "REJECTED_DUPLICATE"
    elif opinion_only:
        classification = "UNQUALIFIED_CONTEXT"
    elif qualified:
        classification = "STAGE1_QUALIFIED"
    else:
        classification = "STAGE1_UNQUALIFIED"
    source_actor_hash = _text_hash(f"{observation.channel}|{observation.actor_id}")
    event = {
        "event_type": "ZRWVE_PASSIVE_INCIDENT_SUBMISSION",
        "source_provenance_valid": provenance_valid,
        "non_duplicate": not duplicate,
        "t2_relevant": t2_relevant,
        "participant_independent": independent,
        "stage1_qualified": qualified,
        "source_actor_hash": source_actor_hash,
        "source_event_id": observation.source_event_id,
        "source_event_reference": observation.source_event_reference,
        "source_created_at": observation.source_created_at,
        "dedupe_key": dedupe_key,
        "wake_eligible": bool(provenance_valid and not duplicate and t2_relevant and independent and qualified),
        "wake_plane_registered": False,
        "external_action": False,
        "evidence_class": "STAGE1_QUALIFICATION_ONLY" if qualified else "UNQUALIFIED_CONTEXT",
    }
    result = {
        "schema": "ZRWVE_PASSIVE_STAGE1_RESULT_V1_2H",
        "classification": classification,
        "qualified": qualified,
        "missing": missing,
        "source_provenance_valid": provenance_valid,
        "participant_independent": independent,
        "t2_relevant": t2_relevant,
        "duplicate": duplicate,
        "privacy_result": "PASS" if not secret_markers else "FAIL_CLOSED",
        "secret_markers": secret_markers,
        "prompt_injection_classification": "DATA_REJECTED" if prompt_markers else "NONE",
        "spam_markers": spam_markers,
        "opinion_only": opinion_only,
        "source_actor_hash": source_actor_hash,
        "dedupe_key": dedupe_key,
        "event": event,
        "raw_content_stored": False,
        "authority_granted": False,
        "economic_evidence_created": False,
    }
    result["stage1_result_hash"] = _stage1_result_hash(result)
    return result


def validate_stage1_result(result: Mapping[str, Any]) -> bool:
    return bool(
        result.get("schema") == "ZRWVE_PASSIVE_STAGE1_RESULT_V1_2H"
        and result.get("stage1_result_hash") == _stage1_result_hash(result)
    )


def validate_stage2(
    packet: Mapping[str, Any],
    stage1_result: Mapping[str, Any],
    *,
    existing_packet_hashes: Sequence[str] = (),
) -> dict[str, Any]:
    stage1_integrity = validate_stage1_result(stage1_result)
    if not stage1_integrity or stage1_result.get("qualified") is not True:
        return {
            "schema": "ZRWVE_PASSIVE_STAGE2_RESULT_V1_2H",
            "state": "PARKED_STAGE1_NOT_QUALIFIED",
            "complete": False,
            "wake_eligible": False,
            "raw_content_stored": False,
        }
    bound_packet = json.loads(json.dumps(packet, ensure_ascii=False)) if isinstance(packet, Mapping) else {}
    provenance = dict(bound_packet.get("provenance", {})) if isinstance(bound_packet.get("provenance"), Mapping) else {}
    provenance.update({
        "independence": True,
        "non_owner": True,
        "non_omega": True,
        "non_test_actor": True,
        "attributable": True,
        "source_actor_hash": stage1_result["source_actor_hash"],
        "stage1_dedupe_key": stage1_result["dedupe_key"],
        "submission_origin": "github_issue",
    })
    bound_packet["provenance"] = provenance
    prompt_markers = _prompt_injection_markers(bound_packet)
    secret_markers = _secret_markers(bound_packet)
    spam_markers = _spam_markers(bound_packet)
    if prompt_markers or secret_markers or spam_markers:
        return {
            "schema": "ZRWVE_PASSIVE_STAGE2_RESULT_V1_2H",
            "state": "PARKED_REJECTED_UNSAFE_CONTENT",
            "complete": False,
            "wake_eligible": False,
            "prompt_injection_classification": "DATA_REJECTED" if prompt_markers else "NONE",
            "privacy_result": "FAIL_CLOSED" if secret_markers else "PASS",
            "spam_result": "FAIL_CLOSED" if spam_markers else "PASS",
            "raw_content_stored": False,
            "authority_granted": False,
            "claims_promoted": [],
        }
    validation = validate_incident_packet(bound_packet)
    if not validation["valid"]:
        return {
            "schema": "ZRWVE_PASSIVE_STAGE2_RESULT_V1_2H",
            "state": "PARKED_INCOMPLETE",
            "complete": False,
            "wake_eligible": False,
            "validation": validation,
            "raw_content_stored": False,
            "claims_promoted": [],
        }
    frozen = freeze_incident_packet(bound_packet)
    packet_hash = frozen["packet_hash"]
    duplicate = packet_hash in set(existing_packet_hashes)
    blind_compatible = bool(
        validate_blind_transform(blind_transform_spec())
        and frozen.get("decision_information_set_hash")
        and frozen.get("outcome_verification_set_hash")
        and frozen["decision_information_set_hash"] != frozen["outcome_verification_set_hash"]
    )
    complete = bool(not duplicate and blind_compatible)
    event = {
        "event_type": "ZRWVE_REAL_INCIDENT_PACKET_RECEIVED",
        "packet_hash": packet_hash,
        "source_actor_hash": stage1_result["source_actor_hash"],
        "stage1_dedupe_key": stage1_result["dedupe_key"],
        "incident_uniqueness_key": _hash(bound_packet.get("incident_data", {})),
        "E1_complete": validation["incident_data"]["valid"],
        "E2_complete": validation["b3_configuration"]["valid"],
        "E3_complete": validation["operator_trace"]["valid"],
        "E4_complete": validation["verification_criterion"]["valid"],
        "blind_compatible": blind_compatible,
        "wake_eligible": complete,
        "wake_plane_registered": False,
        "host_verification_required": True,
        "evidence_class": "INDEPENDENT_EXTERNAL_INCIDENT_EVIDENCE" if complete else "DUPLICATE_OR_INCOMPLETE",
    }
    return {
        "schema": "ZRWVE_PASSIVE_STAGE2_RESULT_V1_2H",
        "state": "READY_FOR_HOST_VERIFICATION" if complete else "REJECTED_DUPLICATE",
        "complete": complete,
        "duplicate": duplicate,
        "blind_compatible": blind_compatible,
        "packet_hash": packet_hash,
        "decision_information_set_hash": frozen["decision_information_set_hash"],
        "outcome_verification_set_hash": frozen["outcome_verification_set_hash"],
        "event": event,
        "wake_eligible": complete,
        "raw_content_stored": False,
        "claims_promoted": [],
        "not_equivalent_to": ["DEMAND", "CUSTOMER", "USAGE", "WTP", "VALUE", "REVENUE"],
    }


def ingest_passive_issue(
    root: Path,
    parsed: Mapping[str, Any],
    observation: PassiveSourceObservation,
) -> dict[str, Any]:
    """Classify one trusted GitHub issue revision and store no raw body.

    The trusted adapter supplies ``observation``. Participant text is parsed as
    data only. Replaying the same issue revision is idempotent.
    """
    if not isinstance(observation, PassiveSourceObservation):
        raise TypeError("trusted passive source observation required")
    journal = Path(root) / ".omega" / "wake-provenance" / PASSIVE_INTAKE_JOURNAL
    records, errors = read_chain(journal)
    if errors:
        raise ValueError("passive intake journal integrity failure: " + errors[0])
    stage1_dedupe = [
        str(row.get("dedupe_key", "")) for row in records if row.get("stage") == "STAGE1"
    ]
    stage1 = validate_stage1(
        parsed.get("fields", {}) if isinstance(parsed, Mapping) else {},
        observation,
        existing_dedupe_keys=stage1_dedupe,
    )
    stage1_id = "ZRWVE-S1-" + _text_hash(observation.source_event_id)[:24]
    stage1_record = {
        "journal_event_id": stage1_id,
        "stage": "STAGE1",
        "recorded_at": _now(),
        "source_event_id": observation.source_event_id,
        "source_event_reference": observation.source_event_reference,
        "source_created_at": observation.source_created_at,
        "source_actor_hash": stage1["source_actor_hash"],
        "dedupe_key": stage1["dedupe_key"],
        "classification": stage1["classification"],
        "qualified": stage1["qualified"],
        "t2_relevant": stage1["t2_relevant"],
        "participant_independent": stage1["participant_independent"],
        "privacy_result": stage1["privacy_result"],
        "prompt_injection_classification": stage1["prompt_injection_classification"],
        "spam_detected": bool(stage1["spam_markers"]),
        "opinion_only": stage1["opinion_only"],
        "wake_eligible": stage1["event"]["wake_eligible"],
        "wake_plane_registered": True,
        "raw_content_stored": False,
        "claims_promoted": [],
        "economic_evidence_created": False,
    }
    stored_stage1, stage1_created = append_chain(
        journal, stage1_record, "journal_event_id"
    )
    stage2_result: dict[str, Any] | None = None
    stored_stage2: dict[str, Any] | None = None
    stage2_created = False
    stage2_present = bool(parsed.get("stage2_present")) if isinstance(parsed, Mapping) else False
    if stage1.get("qualified") is True and stage2_present:
        packet = parsed.get("stage2_packet")
        packet_value = packet if isinstance(packet, Mapping) else {}
        packet_hashes = [
            str(row.get("packet_hash", "")) for row in records
            if row.get("stage") == "STAGE2" and row.get("packet_hash")
        ]
        stage2_result = validate_stage2(
            packet_value, stage1, existing_packet_hashes=packet_hashes
        )
        stage2_id = "ZRWVE-S2-" + _text_hash(observation.source_event_id)[:24]
        stage2_record = {
            "journal_event_id": stage2_id,
            "stage": "STAGE2",
            "recorded_at": _now(),
            "source_event_id": observation.source_event_id,
            "source_event_reference": observation.source_event_reference,
            "source_actor_hash": stage1["source_actor_hash"],
            "stage1_journal_event_id": stage1_id,
            "state": stage2_result["state"],
            "complete": stage2_result["complete"],
            "packet_hash": stage2_result.get("packet_hash"),
            "blind_compatible": stage2_result.get("blind_compatible", False),
            "wake_eligible": stage2_result.get("wake_eligible", False),
            "wake_plane_registered": True,
            "host_verification_required": True,
            "raw_content_stored": False,
            "claims_promoted": [],
            "economic_evidence_created": False,
        }
        stored_stage2, stage2_created = append_chain(
            journal, stage2_record, "journal_event_id"
        )
    return {
        "stage1_result": stage1,
        "stage1_record": stored_stage1,
        "stage1_created": stage1_created,
        "stage2_result": stage2_result,
        "stage2_record": stored_stage2,
        "stage2_created": stage2_created,
        "raw_content_stored": False,
    }


def passive_intake_summary(root: Path) -> dict[str, Any]:
    journal = Path(root) / ".omega" / "wake-provenance" / PASSIVE_INTAKE_JOURNAL
    records, errors = read_chain(journal)
    stage1 = [row for row in records if row.get("stage") == "STAGE1"]
    stage2 = [row for row in records if row.get("stage") == "STAGE2"]
    return {
        "journal_ready": not errors,
        "record_count": len(records),
        "stage1_count": len(stage1),
        "stage1_qualified_count": sum(row.get("qualified") is True for row in stage1),
        "stage2_count": len(stage2),
        "stage2_complete_count": sum(row.get("complete") is True for row in stage2),
        "integrity_errors": errors,
        "raw_content_records": sum(row.get("raw_content_stored") is not False for row in records),
    }


SURFACE_WEIGHTS = {
    "voluntary_participation": 0.11,
    "provenance_strength": 0.12,
    "e1_e2_e3_e4_capability": 0.14,
    "privacy": 0.09,
    "sanitization_support": 0.08,
    "spam_resistance": 0.06,
    "deduplication": 0.07,
    "auditability": 0.07,
    "wake_plane_compatibility": 0.08,
    "owner_attention_cost": -0.05,
    "implementation_complexity": -0.04,
    "external_write_cost": -0.04,
    "long_term_maintenance": -0.05,
}


def _surface(
    surface_id: str,
    exact_write: str,
    factors: Sequence[float],
    *,
    eligible: bool,
    reason: str,
) -> dict[str, Any]:
    names = list(SURFACE_WEIGHTS)
    scores = {name: float(value) for name, value in zip(names, factors)}
    composite = round(100 * sum(scores[name] * weight for name, weight in SURFACE_WEIGHTS.items()), 2)
    return {
        "surface_id": surface_id,
        "design_eligible": eligible,
        "eligibility_reason": reason,
        "scores": scores,
        "composite_score": composite,
        "exact_external_write_required": exact_write,
    }


def evaluate_passive_surfaces(public_truth: Mapping[str, Any]) -> list[dict[str, Any]]:
    issues_available = public_truth.get("has_issues") is True
    discussions_available = public_truth.get("has_discussions") is True
    candidates = [
        _surface(
            "EXISTING_REPOSITORY_DOCUMENTATION",
            "one README addition, but no structured attributable submission route",
            (0.85, 0.40, 0.25, 0.80, 0.55, 0.90, 0.20, 0.60, 0.20, 0.25, 0.20, 0.20, 0.20),
            eligible=False,
            reason="documentation alone cannot receive a provenance-valid packet",
        ),
        _surface(
            "GITHUB_ISSUE_FORM",
            f"add exactly {EXACT_SURFACE} in one commit",
            (0.95, 0.95, 0.95, 0.70, 0.95, 0.75, 0.95, 0.95, 0.95, 0.35, 0.25, 0.20, 0.25),
            eligible=issues_available,
            reason="issues are verified available and already match the read-only provenance adapter" if issues_available else "issue availability not verified",
        ),
        _surface(
            "GITHUB_DISCUSSION_TEMPLATE",
            "enable Discussions and add one discussion template",
            (0.90, 0.90, 0.85, 0.70, 0.90, 0.65, 0.85, 0.90, 0.65, 0.45, 0.35, 0.45, 0.40),
            eligible=discussions_available,
            reason="Discussions verified available" if discussions_available else "Discussions are not enabled",
        ),
        _surface(
            "DEDICATED_RESEARCH_EMAIL",
            "publish one mailbox address and configure a new isolated intake namespace",
            (0.95, 0.65, 0.90, 0.90, 0.90, 0.45, 0.85, 0.75, 0.45, 0.75, 0.65, 0.60, 0.70),
            eligible=True,
            reason="technically possible but cannot reuse the isolated E2-01 binding and has higher moderation cost",
        ),
        _surface(
            "STATIC_INCIDENT_SUBMISSION_GUIDE",
            "publish one static guide with no submission endpoint",
            (0.90, 0.30, 0.60, 0.85, 0.90, 0.90, 0.30, 0.55, 0.15, 0.25, 0.15, 0.20, 0.20),
            eligible=False,
            reason="a guide without an intake endpoint cannot establish participant provenance",
        ),
        _surface(
            "EXISTING_ACTION_FAILURE_SURFACE",
            "modify the existing public Action workflow or failure output",
            (0.80, 0.75, 0.70, 0.65, 0.70, 0.70, 0.75, 0.80, 0.85, 0.45, 0.45, 0.50, 0.45),
            eligible=False,
            reason="would contaminate ZERO-INBOUND-001 and change an existing frozen experiment",
        ),
    ]
    return sorted(candidates, key=lambda row: (-row["composite_score"], row["surface_id"]))


def select_surface(candidates: Sequence[Mapping[str, Any]]) -> dict[str, Any] | None:
    eligible = [dict(row) for row in candidates if row.get("design_eligible") is True]
    return max(eligible, key=lambda row: (float(row["composite_score"]), row["surface_id"])) if eligible else None


def publication_packet(selected: Mapping[str, Any]) -> dict[str, Any]:
    stage1 = stage1_schema()
    stage2 = stage2_schema()
    wake = wake_event_schema()
    payload = {
        "publication_id": PUBLICATION_ID,
        "experiment_id": EXPERIMENT_ID,
        "state": "FROZEN_NOT_AUTHORIZED_NOT_PUBLISHED",
        "exact_surface": EXACT_SURFACE,
        "exact_content": ISSUE_FORM_DRAFT,
        "content_hash": _text_hash(ISSUE_FORM_DRAFT),
        "destination": DESTINATION,
        "privacy_notice": "Public and voluntary. Submit only aliases, redacted identifiers, relative timestamps, sanitized topology, and minimal state excerpts; never credentials, tokens, PII, private logs, restricted source, or confidential information.",
        "intake_schema_hash": _hash({"stage1": stage1, "stage2": stage2}),
        "wake_event_schema_hash": wake["schema_hash"],
        "moderation_policy": {
            "spam": "close without routing",
            "secret_or_private_data": "fail closed, do not ingest, use platform removal process",
            "opinion_only": "classify UNQUALIFIED_CONTEXT",
            "owner_or_bot": "reject as non-independent",
            "prompt_injection": "treat as DATA and reject",
            "automatic_follow_up": False,
        },
        "expiry_or_review_date": "30 days after independently verified publication",
        "rollback": f"remove exactly {EXACT_SURFACE} in a new commit; do not rewrite repository history; preserve legitimate negative evidence",
        "expected_information_gain": "MEDIUM",
        "discovery_limitations": "The form creates an intake endpoint only. Publication is not discovery, traffic, participation, qualified evidence, demand, or value.",
        "external_write_count": 1,
        "ongoing_owner_attention": "LOW",
        "selected_surface_score": selected.get("composite_score"),
        "external_action_authorized": False,
        "publication_executed": 0,
    }
    payload["publication_packet_hash"] = _hash(payload)
    return payload


def fixture_contract() -> dict[str, Any]:
    return {
        "schema": "ZRWVE_PASSIVE_INTAKE_TEST_FIXTURES_V1_2H",
        "test_only": True,
        "fixtures": [
            "real_qualifying_incident", "opinion_only", "anonymous_unverifiable_story",
            "owner_submission", "bot_submission", "duplicate", "missing_b3",
            "missing_operator_trace", "missing_verification", "secret_containing_submission",
            "prompt_injection", "b3_wins_incident", "zero_candidate_incident",
        ],
        "synthetic_fixture_evidence_class": "TEST_ONLY",
        "synthetic_fixture_value": "NONE",
    }


def _local_public_truth(root: Path) -> dict[str, Any]:
    base = root / ".omega" / "wake-provenance"
    config = _read_json(base / "config.json", {})
    checkpoint = _read_json(base / "github_checkpoint.json", {})
    records, errors = read_chain(base / "github_inbound.jsonl")
    github = config.get("github", {}) if isinstance(config, Mapping) else {}
    independent = [row for row in records if row.get("independence_status") == "PROVEN_INDEPENDENT"]
    return {
        "repository": github.get("repository", checkpoint.get("repository", DESTINATION)),
        "read_only_adapter_configured": github.get("enabled") is True and github.get("read_only") is True,
        "repository_identity_verified": checkpoint.get("repository_identity", {}).get("full_name") == DESTINATION,
        "last_successful_poll": checkpoint.get("last_successful_poll"),
        "independent_inbound_records": len(independent),
        "journal_integrity_errors": errors,
        "has_issues": None,
        "has_discussions": None,
        "issue_template_present": None,
        "metadata_source": "LOCAL_READ_ONLY_CHECKPOINT",
    }


def run_passive_intake_design(
    root: Path,
    *,
    public_surface_truth: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    root = Path(root).resolve()
    output = root / ".omega" / "zero"
    local_truth = _local_public_truth(root)
    truth = dict(local_truth)
    if public_surface_truth:
        truth.update(dict(public_surface_truth))
    discovery = _latest_json(output, "zrwve_participant_discovery") or {}
    entry_truth_valid = bool(
        discovery.get("final_result") == "QUALIFIED_BUT_NO_LEGITIMATE_CONTACT_ROUTE"
        and discovery.get("external_write_executed") == 0
        and discovery.get("messages_sent") == 0
        and discovery.get("current_evidence_level") == "L0"
    )
    candidates = evaluate_passive_surfaces(truth)
    selected = select_surface(candidates)
    form_validation = validate_issue_form_draft()
    structural_ready = bool(
        entry_truth_valid and selected and selected["surface_id"] == "GITHUB_ISSUE_FORM"
        and form_validation["valid"]
    )
    packet = publication_packet(selected or {}) if selected else None
    fingerprint = _hash({
        "protocol": PASSIVE_INTAKE_PROTOCOL,
        "entry_discovery_hash": _hash(discovery) if discovery else None,
        "public_surface_truth": truth,
        "surface_scores": candidates,
        "issue_form_hash": _text_hash(ISSUE_FORM_DRAFT),
        "issue_form_validation": form_validation,
    })
    numbered = sorted(output.glob("zrwve_passive_intake_design_[0-9][0-9][0-9][0-9].json"))
    for path in numbered:
        previous = _read_json(path, {})
        if previous.get("input_fingerprint") == fingerprint:
            replay = dict(previous)
            replay["idempotent_replay"] = True
            return replay
    sequence = len(numbered) + 1
    cycle_id = f"zrwve-passive-intake-design-{sequence:04d}"
    result = {
        "schema": PASSIVE_INTAKE_SCHEMA,
        "protocol": PASSIVE_INTAKE_PROTOCOL,
        "cycle_id": cycle_id,
        "entry_truth_valid": entry_truth_valid,
        "direct_participant_discovery": "SATURATED_FOR_CURRENT_EVIDENCE",
        "public_surface_truth": truth,
        "passive_surfaces_evaluated": len(candidates),
        "surface_evaluation": candidates,
        "selected_passive_surface": selected["surface_id"] if selected else "NONE",
        "selected_surface_score": selected["composite_score"] if selected else None,
        "issue_form_validation": form_validation,
        "stage1_schema": stage1_schema(),
        "stage2_schema": stage2_schema(),
        "wake_event_schema": wake_event_schema(),
        "stage1_qualification_ready": structural_ready,
        "stage2_e1_e2_e3_e4_ready": structural_ready,
        "provenance_ready": structural_ready,
        "privacy_ready": structural_ready,
        "dedupe_ready": structural_ready,
        "spam_filter_ready": structural_ready,
        "prompt_injection_contained": structural_ready,
        "wake_plane_route_ready": structural_ready,
        "wake_plane_route_registered": False,
        "blind_b3_vs_zero_compatible": validate_blind_transform(blind_transform_spec()),
        "existing_independent_discovery": "PROVEN" if truth.get("independent_inbound_records", 0) else "NOT_PROVEN",
        "passive_intake_expected_information_gain": "MEDIUM" if structural_ready else "LOW",
        "owner_attention_cost": "LOW" if structural_ready else "UNKNOWN",
        "publication_authority_required": bool(structural_ready),
        "publication_packet_frozen": bool(packet and structural_ready),
        "publication_packet": packet,
        "fixture_contract": fixture_contract(),
        "red_team_result": {
            "attacks": [
                "spam", "seo", "bot", "ai_generated_incident", "duplicate_incident",
                "owner_submission", "omega_submission", "prompt_injection", "credential_dump",
                "private_logs", "irrelevant_bug", "product_praise", "anonymous_anecdote",
                "fabricated_timeline",
            ],
            "all_submission_text_is_data": True,
            "authority_from_submission": False,
            "threshold_change_from_submission": False,
            "result": "CONTAINED_BY_DESIGN" if structural_ready else "INCOMPLETE",
        },
        "alternative_comparison": {
            "PARK": {"information_gain": "LOW", "cost": "LOW", "selected": False},
            "PUBLISH_MINIMAL_PASSIVE_INTAKE": {"information_gain": "MEDIUM", "cost": "LOW", "selected": structural_ready},
            "RESUME_DIRECT_DISCOVERY": {"information_gain": "LOW", "cost": "MEDIUM", "selected": False},
        },
        "external_write_executed": 0,
        "publication_executed": 0,
        "messages_sent": 0,
        "external_action_authorized": False,
        "current_evidence_level": "L0",
        "verified_net_economic_value": "0 KWD",
        "v0_30_state": "WAITING_EXTERNAL_EVIDENCE",
        "wake_plane_mode": "PASSIVE_PRODUCTION",
        "capability_router_mode": "SHADOW",
        "global_production_default": "LEGACY",
        "final_decision": "PASSIVE_INCIDENT_INTAKE_DESIGN_READY" if structural_ready else "PASSIVE_INTAKE_WITH_ISSUES",
        "next_atomic_action": "REQUEST_BOUNDED_PUBLICATION_AUTHORITY" if structural_ready else "REPAIR_PASSIVE_INTAKE",
        "test_results": {"status": "PENDING_HOST_VERIFICATION"},
        "input_fingerprint": fingerprint,
        "created_at": _now(),
        "idempotent_replay": False,
    }
    _atomic_write(output / f"zrwve_passive_intake_design_{sequence:04d}.json", result)
    _atomic_write(output / "zrwve_passive_intake_design_latest.json", result)
    _atomic_write(output / "zrwve_passive_intake_surface_evaluation.json", {"schema": "ZRWVE_PASSIVE_SURFACE_EVALUATION_V1_2H", "rows": candidates})
    _atomic_write(output / "zrwve_passive_intake_stage1_schema.json", result["stage1_schema"])
    _atomic_write(output / "zrwve_passive_intake_stage2_schema.json", result["stage2_schema"])
    _atomic_write(output / "zrwve_passive_intake_wake_event_schema.json", result["wake_event_schema"])
    _atomic_write(output / "zrwve_passive_intake_fixture_contract.json", result["fixture_contract"])
    if packet:
        _atomic_write(output / "zrwve_passive_intake_publication_packet.json", packet)
    _atomic_write(output / "zrwve_passive_intake_memory.json", {
        "schema": "ZRWVE_PASSIVE_INTAKE_MEMORY_V1_2H",
        "last_cycle_id": cycle_id,
        "input_fingerprint": fingerprint,
        "source_cycle_hash": _hash(result),
        "final_decision": result["final_decision"],
    })
    return result


def record_passive_intake_host_verification(root: Path, verification: Mapping[str, Any]) -> dict[str, Any]:
    root = Path(root).resolve()
    output = root / ".omega" / "zero"
    latest = _latest_json(output, "zrwve_passive_intake_design")
    if not latest:
        raise FileNotFoundError("no passive intake design cycle to verify")
    if verification.get("status") != "PASS":
        raise ValueError("only a passing host verification may be recorded")
    updated = dict(latest)
    updated["test_results"] = dict(verification)
    match = re.search(r"(\d+)$", str(updated.get("cycle_id", "")))
    if not match:
        raise ValueError("invalid passive intake cycle id")
    sequence = int(match.group(1))
    _atomic_write(output / f"zrwve_passive_intake_design_{sequence:04d}.json", updated)
    _atomic_write(output / "zrwve_passive_intake_design_latest.json", updated)
    memory_path = output / "zrwve_passive_intake_memory.json"
    memory = _read_json(memory_path, {"schema": "ZRWVE_PASSIVE_INTAKE_MEMORY_V1_2H"})
    memory["source_cycle_hash"] = _hash(updated)
    _atomic_write(memory_path, memory)
    record = {
        "schema": "ZRWVE_PASSIVE_INTAKE_HOST_VERIFICATION_V1_2H",
        "cycle_id": updated["cycle_id"],
        "recorded_at": _now(),
        "verification": dict(verification),
        "cycle_hash": _hash(updated),
    }
    _atomic_write(output / "zrwve_passive_intake_host_verification_0001.json", record)
    return updated


__all__ = [
    "EXACT_SURFACE", "EXPERIMENT_ID", "ISSUE_FORM_DRAFT", "PASSIVE_INTAKE_PROTOCOL",
    "PassiveSourceObservation", "evaluate_passive_surfaces", "fixture_contract",
    "parse_issue_form_body", "publication_packet", "record_passive_intake_host_verification",
    "run_passive_intake_design", "select_surface", "stage1_schema", "stage2_schema",
    "validate_issue_form_draft", "validate_stage1", "validate_stage1_result", "validate_stage2",
    "ingest_passive_issue", "passive_intake_summary",
    "wake_event_schema",
]
