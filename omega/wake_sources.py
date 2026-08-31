"""Read-only source adapters for the Wake Plane.

Adapters return normalized candidates and a readiness matrix. They never
perform external writes and never infer independence from caller JSON.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .real_world_value_passive_intake import (
    PASSIVE_INTAKE_WORK_ID,
    PassiveSourceObservation,
    ingest_passive_issue,
    parse_issue_form_body,
    passive_intake_summary,
)
from .wake_provenance import (
    GITHUB_WORK_ID, PASSIVE_INTAKE_KIND, TrustedSourceObservation,
    digest, evaluator_summary, github_qualifying_records, poll_github,
)
from .real_world_value_reality_watch import (
    EVENT_KIND as REALITY_WATCH_EVENT_KIND,
    WORK_ID as REALITY_WATCH_WORK_ID,
    poll_reality_watch,
)


def _now() -> datetime:
    return datetime.now(timezone.utc).astimezone()


def _read(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _lines(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            value = json.loads(line)
            if isinstance(value, dict):
                out.append(value)
        except json.JSONDecodeError:
            continue
    return out


def _health(name: str, state: str, ready: bool, count: int = 0,
            error: str | None = None, **extra: Any) -> dict[str, Any]:
    return {
        "source": name, "health": state,
        "enabled": state not in {"DORMANT", "BLOCKED"},
        "last_success": _now().isoformat(timespec="seconds") if not error else None,
        "next_retry": None, "last_error_class": error,
        "candidate_count": count, "validated_count": 0,
        "production_ready": ready,
        "provenance_strength": extra.pop("provenance_strength", "LOCAL_JOURNAL"),
        "dedupe": extra.pop("dedupe", "DURABLE"),
        "routing": extra.pop("routing", "FAIL_CLOSED"), **extra,
    }


def _trigger(event_id: str, kind: str, source: str, identity: str,
             work: str, provenance: str, ref: str, dedupe: str,
             condition: str, *, source_event_id: str | None = None,
             fingerprint: str | None = None) -> dict[str, Any]:
    stamp = _now()
    source_event_id = source_event_id or event_id
    fingerprint = fingerprint or hashlib.sha256(
        f"{source}:{source_event_id}".encode("utf-8")).hexdigest()
    return {
        "trigger_id": event_id, "trigger_type": kind, "source": source,
        "source_identity": identity, "source_event_id": source_event_id,
        "canonical_event_fingerprint": fingerprint, "observed_at": stamp.isoformat(),
        "work_id": work, "wake_condition": condition,
        "provenance_class": provenance, "evidence_reference": ref,
        "authority_requirement": "NONE", "resource_requirement": "HOST_AVAILABLE",
        "external_effect": False, "dedupe_key": dedupe,
        "expiry": (stamp + timedelta(days=30)).isoformat(),
        "verification_requirement": "HOST_VERIFICATION_REQUIRED",
    }


def _v030_sources(root: Path, triggers: list[dict[str, Any]],
                  health: dict[str, dict[str, Any]]) -> None:
    summary = evaluator_summary(root)
    if summary["integrity_errors"]:
        health["v0_30_evaluator"] = _health(
            "v0_30_evaluator", "BLOCKED", False, summary["record_count"],
            "JOURNAL_INTEGRITY_FAILURE", provenance_strength="CHAIN_VERIFIED")
        return
    qualifying = summary["qualifying_records"]
    for record in qualifying:
        event_id = str(record["evidence_event_id"])
        fingerprint = str(record.get("canonical_event_fingerprint") or
                           hashlib.sha256(event_id.encode()).hexdigest())
        triggers.append(_trigger(
            event_id, "V0_30_EVIDENCE", "v0_30_provenance",
            str(record.get("source_actor_hash", "")),
            "V0.30 External Evaluator Evidence Collection", "INDEPENDENT_EXTERNAL",
            str(record.get("source_event_reference", "")),
            str(record.get("submission_id", event_id)),
            "verified independent evaluator submission",
            source_event_id=str(record.get("source_event_id", event_id)),
            fingerprint=fingerprint,
        ))
    independent_count = summary["independent_evaluator_count"]
    ready = independent_count >= 2
    health["v0_30_evaluator"] = _health(
        "v0_30_evaluator", "ACTIVE" if ready else "BLOCKED", ready, len(qualifying),
        None if ready else "NO_PROVEN_INDEPENDENT_EVIDENCE",
        provenance_strength="CHAIN_VERIFIED_EXTERNAL_ATTRIBUTION",
        journal_ready=True,
        independent_evaluator_count=independent_count,
        milestone_state=("READY" if ready else "WAITING_EXTERNAL_EVIDENCE"),
        integrity_errors=summary["integrity_errors"],
    )


def poll_sources(root: Path, *, github_fetcher: Any = None,
                 force_github: bool = False, reality_fetcher: Any = None,
                 force_reality: bool = False) -> tuple[list[dict[str, Any]],
                                                        dict[str, dict[str, Any]]]:
    root = Path(root)
    triggers: list[dict[str, Any]] = []
    health: dict[str, dict[str, Any]] = {}

    # Gmail bodies/tokens are never read here; only classified metadata.
    replies = _lines(root / ".omega" / "avf" / "e2_01_reply_events.jsonl")
    for event in replies:
        message_id = str(event.get("gmail_message_id", ""))
        classification = str(event.get("classification", "")).upper()
        if message_id and classification in {
            "POSITIVE", "NEGATIVE", "AMBIGUOUS", "BOUNCE", "UNSUBSCRIBE", "OTHER",
        }:
            source_id = f"gmail:E2-01:{message_id}"
            triggers.append(_trigger(
                "E2-" + hashlib.sha256(message_id.encode()).hexdigest()[:16],
                "E2_INBOUND", "gmail-e2-monitor", "E2-01-preregistered-threads",
                "E2-01", "INDEPENDENT_EXTERNAL",
                "e2_01_reply_events.jsonl#" + hashlib.sha256(message_id.encode()).hexdigest()[:12],
                message_id, "new classified E2 reply event", source_event_id=source_id,
            ))
    health["gmail_e2"] = _health(
        "gmail_e2", "ACTIVE", True, len(replies),
        provenance_strength="GMAIL_CLASSIFIED_METADATA")

    _v030_sources(root, triggers, health)

    # Network polling is opt-in via a repository config file. Unit tests and
    # unconfigured checkouts therefore never perform accidental network I/O.
    github = poll_github(root, github_fetcher, force=force_github)
    github_records = github.get("records", [])
    for record in github.get("new_records", []):
        if (record.get("independence_status") != "PROVEN_INDEPENDENT"
                or record.get("submission_kind") == PASSIVE_INTAKE_KIND):
            continue
        trigger_id = "GH-" + hashlib.sha256(
            str(record["source_event_id"]).encode("utf-8")).hexdigest()[:16]
        triggers.append(_trigger(
            trigger_id, "INBOUND_INSTALL", "github-inbound",
            str(record.get("actor_hash", "")), GITHUB_WORK_ID,
            "INDEPENDENT_EXTERNAL", str(record.get("url_reference", "")),
            str(record.get("dedupe_key", record["source_event_id"])),
            "new non-owner non-bot GitHub inbound event",
            source_event_id=str(record["source_event_id"]),
            fingerprint=str(record["canonical_event_fingerprint"]),
        ))
    health["github_inbound"] = {
        "source": "github_inbound", "health": github.get("health", "DORMANT"),
        "enabled": bool(github.get("enabled", False)),
        "last_success": github.get("checkpoint", {}).get("last_successful_poll"),
        "next_retry": github.get("checkpoint", {}).get("next_retry"),
        "last_error_class": github.get("blocker"),
        "candidate_count": len(github_records), "validated_count": 0,
        "production_ready": bool(github.get("production_ready", False)),
        "provenance_strength": "GITHUB_IMMUTABLE_ACTOR_ID" if github.get("enabled") else "NONE",
        "dedupe": "CHAIN_AND_SOURCE_EVENT_ID", "routing": "ZERO-INBOUND-001_FAIL_CLOSED",
        "real_trigger_present": bool(github_qualifying_records(github_records)),
        "network_requests": int(github.get("network_requests", 0)),
        "rate_limit_remaining": github.get("checkpoint", {}).get("rate_limit_remaining"),
        "checkpoint": github.get("checkpoint", {}),
    }

    passive_triggers = 0
    for candidate in github.get("passive_candidates", []):
        trusted = candidate.get("observation") if isinstance(candidate, dict) else None
        source_record = candidate.get("source_record", {}) if isinstance(candidate, dict) else {}
        if not isinstance(trusted, TrustedSourceObservation) or not isinstance(source_record, dict):
            continue
        revision_source_event_id = str(candidate.get("revision_source_event_id", ""))
        if not revision_source_event_id:
            continue
        observation = PassiveSourceObservation(
            channel="github_issue",
            actor_id=trusted.actor_id,
            source_event_id=revision_source_event_id,
            source_event_reference=trusted.source_event_reference,
            source_created_at=str(candidate.get("updated_at") or trusted.source_created_at),
            source_verified=trusted.source_verified,
            owner_origin=trusted.owner_origin,
            bot_origin=trusted.system_origin,
            omega_origin=trusted.owner_origin,
        )
        parsed = parse_issue_form_body(str(candidate.get("body", "")))
        ingestion = ingest_passive_issue(root, parsed, observation)
        stage1 = ingestion["stage1_result"]
        stage2 = ingestion.get("stage2_result")
        if (ingestion.get("stage2_created") and isinstance(stage2, dict)
                and stage2.get("wake_eligible") is True):
            packet_hash = str(stage2.get("packet_hash", ""))
            trigger_id = "ZRWVE-S2-" + digest({
                "source": revision_source_event_id, "packet": packet_hash,
            })[:16]
            triggers.append(_trigger(
                trigger_id, "ZRWVE_REAL_INCIDENT_PACKET_RECEIVED",
                "github-zrwve-passive-intake", str(stage1.get("source_actor_hash", "")),
                PASSIVE_INTAKE_WORK_ID, "INDEPENDENT_EXTERNAL",
                trusted.source_event_reference, packet_hash,
                "qualified complete E1/E2/E3/E4 incident packet",
                source_event_id=revision_source_event_id,
                fingerprint=digest({"event": "ZRWVE_REAL_INCIDENT_PACKET_RECEIVED",
                                    "packet_hash": packet_hash}),
            ))
            passive_triggers += 1
        elif (ingestion.get("stage1_created") and stage1.get("qualified") is True):
            trigger_id = "ZRWVE-S1-" + digest(revision_source_event_id.encode("utf-8"))[:16]
            triggers.append(_trigger(
                trigger_id, "ZRWVE_PASSIVE_INCIDENT_SUBMISSION",
                "github-zrwve-passive-intake", str(stage1.get("source_actor_hash", "")),
                PASSIVE_INTAKE_WORK_ID, "INDEPENDENT_EXTERNAL",
                trusted.source_event_reference, str(stage1.get("dedupe_key", "")),
                "qualified independent Stage 1 T2 incident submission",
                source_event_id=revision_source_event_id,
                fingerprint=digest({"event": "ZRWVE_PASSIVE_INCIDENT_SUBMISSION",
                                    "source": revision_source_event_id}),
            ))
            passive_triggers += 1
    passive = passive_intake_summary(root)
    passive_ready = bool(
        github.get("passive_intake_enabled") is True
        and github.get("production_ready") is True
        and passive["journal_ready"]
    )
    health["zrwve_passive_intake"] = _health(
        "zrwve_passive_intake",
        "ACTIVE" if passive_ready else ("BLOCKED" if github.get("passive_intake_enabled") else "DORMANT"),
        passive_ready,
        passive["stage1_count"],
        None if passive_ready else (
            passive["integrity_errors"][0] if passive["integrity_errors"]
            else "PASSIVE_INTAKE_NOT_ENABLED_OR_GITHUB_UNAVAILABLE"
        ),
        provenance_strength="GITHUB_IMMUTABLE_ACTOR_ID_AND_REVISION_HASH",
        dedupe="CHAIN_SOURCE_REVISION_AND_PACKET_HASH",
        routing="ZRWVE_V1_2H_FAIL_CLOSED",
        route_registered=bool(github.get("passive_intake_enabled")),
        stage1_qualified_count=passive["stage1_qualified_count"],
        stage2_complete_count=passive["stage2_complete_count"],
        current_cycle_triggers=passive_triggers,
        raw_content_records=passive["raw_content_records"],
        publication_is_not_discovery=True,
    )

    # ZRWVE V1.2J is another source adapter in this same polling cycle, not a
    # second watcher. Only material, independently attributable T2 incidents
    # become candidates; raw external text never enters the trigger.
    reality = poll_reality_watch(root, reality_fetcher, force=force_reality)
    reality_triggers = 0
    for incident in reality.get("wake_candidates", []):
        event_id = str(incident.get("EVENT_ID", ""))
        version = str(incident.get("SOURCE_UPDATE_HASH", ""))
        actor_hash = str(incident.get("ACTOR_PUBLIC_ID_HASH", ""))
        reference = str(incident.get("PUBLIC_REFERENCE", ""))
        if not (event_id and version and actor_hash and reference):
            continue
        trigger_id = "ZRWVE-PUBLIC-" + digest({"event": event_id, "version": version})[:16]
        triggers.append(_trigger(
            trigger_id, REALITY_WATCH_EVENT_KIND, "zrwve-public-reality-watch",
            actor_hash, REALITY_WATCH_WORK_ID, "INDEPENDENT_EXTERNAL",
            reference, event_id + "|" + version,
            "qualified new or materially updated public T2 incident",
            source_event_id=event_id,
            fingerprint=digest({"zrwve_public_incident": event_id, "version": version}),
        ))
        reality_triggers += 1
    health["zrwve_public_reality_watch"] = _health(
        "zrwve_public_reality_watch",
        reality.get("health", "DORMANT"),
        reality.get("mode") == "ACTIVE_READ_ONLY" and reality.get("health") == "ACTIVE",
        sum(int(item.get("scanned", 0)) for item in reality.get("source_results", [])),
        None if reality.get("health") == "ACTIVE" else (
            next((item.get("blocker") for item in reality.get("source_results", [])
                  if item.get("blocker")), None)
        ),
        provenance_strength="FIXED_GITHUB_REPOSITORY_AND_IMMUTABLE_ACTOR_ID",
        dedupe="CHAIN_EVENT_VERSION_AND_WAKE_PLANE_CANONICAL_FINGERPRINT",
        routing="ZRWVE_V1_2J_MATERIAL_THRESHOLD_ONLY",
        route_registered=True,
        mode=reality.get("mode", "DISABLED"),
        active_sources=int(reality.get("active_sources", 0)),
        healthy_sources=int(reality.get("healthy_sources", 0)),
        current_cycle_triggers=reality_triggers,
        network_requests=int(reality.get("network_requests", 0)),
        model_calls=int(reality.get("model_calls", 0)),
        external_writes=int(reality.get("external_writes", 0)),
    )

    checkpoint = _read(root / ".omega" / "runtime" / "provider_checkpoint.json", {})
    next_task = ((root / "NEXT_TASK.md").read_text(encoding="utf-8", errors="replace")
                 if (root / "NEXT_TASK.md").exists() else "")
    active_provider = bool(
        checkpoint.get("status") == "WAITING_RESOURCE" and checkpoint.get("task_id")
        and checkpoint.get("branch")
        and str(checkpoint.get("branch", "")).lower() in next_task.lower())
    health["provider_recovery"] = _health(
        "provider_recovery", "WAITING_RESOURCE" if active_provider else "DORMANT",
        True if active_provider else False, 0,
        None if active_provider else "NO_ACTIVE_MATCHING_FROZEN_WORK",
        provenance_strength="HOST_CHECKPOINT")

    decisions_dir = root / ".omega" / "runtime" / "approval_decisions"
    decisions = list(decisions_dir.glob("*.json")) if decisions_dir.exists() else []
    valid_decisions = 0
    for decision_path in decisions:
        decision = _read(decision_path, {})
        required = {"request_id", "work_id", "requesting_component", "decision",
                    "authority_scope", "expiry", "verification_requirements"}
        if required.issubset(decision) and decision.get("decision") in {"APPROVE", "REJECT"}:
            valid_decisions += 1
            request_id, decision_value = str(decision["request_id"]), str(decision["decision"])
            event_id = "APPROVAL-" + hashlib.sha256(
                (request_id + decision_value).encode()).hexdigest()[:16]
            triggers.append(_trigger(
                event_id, "OWNER_APPROVAL", "structured-approval-decision",
                str(decision["requesting_component"]), str(decision["work_id"]),
                "OWNER_SIGNED", str(decision_path.relative_to(root)),
                request_id + "|" + decision_value, "valid structured owner decision",
                source_event_id="approval:" + request_id,
            ))
    health["owner_approval"] = _health(
        "owner_approval", "ACTIVE", True, valid_decisions,
        provenance_strength="STRICT_STRUCTURED_OWNER_RECORD")

    queue = root / ".omega" / "runtime" / "work_queue.jsonl"
    items = _lines(queue)
    runnable = [item for item in items if item.get("state") == "READY"
                and item.get("work_id") and item.get("authority_valid") is True
                and item.get("resources_available") is True]
    for item in runnable:
        work_id = str(item["work_id"])
        triggers.append(_trigger(
            "QUEUE-" + hashlib.sha256(work_id.encode()).hexdigest()[:16],
            "INTERNAL_READY", "work-queue", "host-queue", work_id,
            "INTERNAL_DETERMINISTIC", str(queue.relative_to(root)), work_id,
            "persisted ready work", source_event_id="queue:" + work_id,
        ))
    health["internal_queue"] = _health(
        "internal_queue", "ACTIVE" if queue.exists() else "DORMANT",
        True if queue.exists() else False, len(runnable),
        None if queue.exists() else "NO_QUEUE_JOURNAL",
        provenance_strength="HOST_JOURNAL")
    return triggers, health
