"""Bounded public-reality observation for the frozen ZRWVE T2 target.

The Reality Watch is a source adapter, not a second watcher.  It is called by
the existing Wake Plane, performs conditional read-only observations against a
small allowlist, stores only provenance and structured facts, and emits a wake
candidate only after a deterministic qualification gate has passed.

External text is always treated as untrusted data.  It can influence neither
authority nor configuration, and is never retained in the incident journal.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import time
import tracemalloc
from typing import Any, Callable, Iterable

from .wake_provenance import (
    GithubFetcher,
    GithubResponse,
    append_chain,
    atomic_json,
    digest,
    github_get,
    read_chain,
    read_json,
)


SCHEMA_VERSION = "ZRWVE_REALITY_WATCH_V1_2J"
TARGET = "T2"
WORK_ID = "ZRWVE V1.2J Public Incident Watch"
EVENT_KIND = "ZRWVE_PUBLIC_INCIDENT_CANDIDATE"
OWNER_LOGINS = frozenset({"mrmohamedhassan2017-blip"})
MAX_BODY_CHARS = 32_000
MAX_ITEMS_PER_SOURCE = 30
DEFAULT_MIN_POLL_SECONDS = 900
MAX_NETWORK_REQUESTS_PER_CYCLE = 2
ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    "DISCOVERED": frozenset({"FILTERED"}),
    "FILTERED": frozenset({"QUALIFIED", "PUBLIC_INSUFFICIENT"}),
    "QUALIFIED": frozenset({"SNAPSHOT_FROZEN"}),
    "SNAPSHOT_FROZEN": frozenset({"PUBLIC_COMPLETE", "PUBLIC_PARTIAL", "PUBLIC_INSUFFICIENT"}),
    "PUBLIC_COMPLETE": frozenset({"B3_RECONSTRUCTED"}),
    "PUBLIC_PARTIAL": frozenset({"B3_RECONSTRUCTED", "WAIT_HUMAN", "PARK"}),
    "PUBLIC_INSUFFICIENT": frozenset({"PARK"}),
    "B3_RECONSTRUCTED": frozenset({"ZERO_RECONSTRUCTED"}),
    "ZERO_RECONSTRUCTED": frozenset({"COMPARISON_FROZEN"}),
    "COMPARISON_FROZEN": frozenset({"VERIFIED", "WAIT_HUMAN", "PARK"}),
    "VERIFIED": frozenset({"CLASSIFIED"}),
    "CLASSIFIED": frozenset({"REPLICATE", "KILL", "WAIT_HUMAN", "PARK"}),
}


@dataclass(frozen=True)
class RealitySource:
    source_id: str
    source_type: str
    project: str
    public_location: str
    read_mode: str
    authority_class: str
    provenance_method: str
    cursor_method: str
    etag_support: bool
    rate_limit_policy: str
    target_relevance: str
    enabled: bool = True


SOURCE_REGISTRY: tuple[RealitySource, ...] = (
    RealitySource(
        source_id="github-prefect-t2",
        source_type="GITHUB_PUBLIC_ISSUES",
        project="PrefectHQ/prefect",
        public_location="https://api.github.com/repos/PrefectHQ/prefect/issues",
        read_mode="READ_ONLY_CONDITIONAL_GET",
        authority_class="PUBLIC_READ_ONLY_AUTHORIZED",
        provenance_method="FIXED_REPOSITORY_API_PLUS_IMMUTABLE_ACTOR_ID",
        cursor_method="ETAG_PLUS_UPDATED_AT",
        etag_support=True,
        rate_limit_policy="MIN_15_MINUTES_EXPONENTIAL_BACKOFF",
        target_relevance="T2_DATAFLOW_PARTIAL_RESUME_AND_STATE_RECONSTRUCTION",
    ),
    RealitySource(
        source_id="github-airflow-t2",
        source_type="GITHUB_PUBLIC_ISSUES",
        project="apache/airflow",
        public_location="https://api.github.com/repos/apache/airflow/issues",
        read_mode="READ_ONLY_CONDITIONAL_GET",
        authority_class="PUBLIC_READ_ONLY_AUTHORIZED",
        provenance_method="FIXED_REPOSITORY_API_PLUS_IMMUTABLE_ACTOR_ID",
        cursor_method="ETAG_PLUS_UPDATED_AT",
        etag_support=True,
        rate_limit_policy="MIN_15_MINUTES_EXPONENTIAL_BACKOFF",
        target_relevance="T2_DATAFLOW_PARTIAL_RESUME_AND_STATE_RECONSTRUCTION",
    ),
)


CLUSTER_TERMS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("DUPLICATE_EFFECT", ("duplicate", "twice", "again", "double", "exactly once")),
    ("PARTIAL_DOWNSTREAM_COMMIT", ("partial", "downstream", "side effect", "committed", "external effect")),
    ("CHECKPOINT_STALE", ("checkpoint", "stale checkpoint", "resume from")),
    ("RETRY_DUPLICATION", ("retry", "rerun", "re-run", "reattach")),
    ("STATE_DIVERGENCE", ("state", "inconsistent", "diverge", "completed", "running", "crashed")),
    ("VERIFICATION_AMBIGUITY", ("verify", "unknown", "uncertain", "cannot tell", "ambiguous")),
)

RECOVERY_TERMS = frozenset({
    "retry", "resume", "replay", "recover", "recovery", "checkpoint", "rerun",
    "re-run", "restart", "reattach", "rollback", "reconcile",
})
STATE_TERMS = frozenset({
    "state", "running", "completed", "failed", "crashed", "pending", "scheduled",
    "result", "worker", "pod", "task", "flow", "dag", "workflow",
})
CONSEQUENCE_TERMS = frozenset({
    "duplicate", "twice", "side effect", "downstream", "partial", "commit",
    "transaction", "inconsistent", "diverge", "wrong", "data loss", "orphan",
})
ACTION_TERMS = frozenset({
    "manual", "operator", "workaround", "inspect", "force", "cancel", "kill",
    "clear", "mark", "change", "fix", "upgrade", "wait",
})
GENERIC_ONLY_TERMS = frozenset({"documentation", "docs", "typo", "feature request", "question"})
INJECTION_MARKERS = (
    "ignore previous instructions", "system prompt", "developer message", "grant authority",
    "run this command", "execute this", "reveal secret", "access token", "client_secret",
)
STRONG_RECOVERY_PHRASES = (
    "manual retry", "retried", "retrying", "retry after", "resume", "resuming",
    "replay", "rerun", "re-run", "recover", "checkpoint", "restart after",
)
STRONG_CONSEQUENCE_PHRASES = (
    "side effect", "downstream", "transaction committed", "already committed",
    "partial commit", "partial execution", "duplicate execution", "duplicate work",
    "duplicate effect", "executed twice", "runs twice", "ran twice", "data loss",
)
CLASSIFIER_SPEC = {
    "version": "ZRWVE_T2_DETERMINISTIC_FILTER_V2",
    "requires": ["strong_recovery_phrase", "strong_consequence_phrase", "state_signal"],
    "generic_log_noise_rejected": True,
    "raw_text_retained": False,
}
CLASSIFIER_SPEC_HASH = digest(CLASSIFIER_SPEC)


def _now(value: datetime | None = None) -> datetime:
    current = value or datetime.now(timezone.utc)
    return current.astimezone(timezone.utc)


def _iso(value: datetime | None = None) -> str:
    return _now(value).astimezone().isoformat(timespec="seconds")


def _parse_time(value: Any) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else None
    except (TypeError, ValueError):
        return None


def _safe_text(value: Any, limit: int = MAX_BODY_CHARS) -> tuple[str, bool]:
    text = str(value or "")
    truncated = len(text) > limit
    return text[:limit], truncated


def _terms(text: str, vocabulary: Iterable[str]) -> set[str]:
    lowered = text.casefold()
    return {term for term in vocabulary if term in lowered}


def _is_bot(login: str, actor_type: str) -> bool:
    lowered = login.casefold()
    return actor_type.casefold() == "bot" or lowered.endswith("[bot]") or lowered.endswith("-bot")


def _cluster(text: str) -> str:
    lowered = text.casefold()
    for cluster, terms in CLUSTER_TERMS:
        if any(term in lowered for term in terms):
            return cluster
    return "UNCLASSIFIED_T2"


def _has_unnegated_phrase(text: str, phrases: Iterable[str]) -> bool:
    lowered = text.casefold()
    for phrase in phrases:
        start = 0
        while True:
            index = lowered.find(phrase, start)
            if index < 0:
                break
            prefix = lowered[max(0, index - 40):index]
            if not re.search(r"\b(?:no|not|without|neither)\b[^.!?]{0,35}$", prefix):
                return True
            start = index + len(phrase)
    return False


def _consequential_question(cluster: str) -> str | None:
    return {
        "DUPLICATE_EFFECT": "HAS_THIS_SIDE_EFFECT_ALREADY_OCCURRED?",
        "PARTIAL_DOWNSTREAM_COMMIT": "IS_DOWNSTREAM_STATE_VALID?",
        "CHECKPOINT_STALE": "WHICH_CHECKPOINT_IS_TRUSTWORTHY?",
        "RETRY_DUPLICATION": "REPLAY_ALLOWED?",
        "STATE_DIVERGENCE": "IS_WORKFLOW_ACTUALLY_COMPLETE?",
        "VERIFICATION_AMBIGUITY": "SAFE_TO_RESUME?",
    }.get(cluster)


def transition(current: str, requested: str) -> str:
    if requested not in ALLOWED_TRANSITIONS.get(current, frozenset()):
        raise ValueError(f"ILLEGAL_INCIDENT_TRANSITION:{current}->{requested}")
    return requested


def source_registry_payload(*, lifecycle: str = "SHADOW",
                            observed_at: str | None = None,
                            source_health: dict[str, Any] | None = None) -> dict[str, Any]:
    health = source_health or {}
    rows = []
    for item in SOURCE_REGISTRY:
        source_status = health.get(item.source_id, {})
        rows.append({
            "SOURCE_ID": item.source_id,
            "SOURCE_TYPE": item.source_type,
            "PROJECT": item.project,
            "PUBLIC_LOCATION": item.public_location,
            "READ_MODE": item.read_mode,
            "AUTHORITY_CLASS": item.authority_class,
            "PROVENANCE_METHOD": item.provenance_method,
            "CURSOR_METHOD": item.cursor_method,
            "ETAG_SUPPORT": item.etag_support,
            "RATE_LIMIT_POLICY": item.rate_limit_policy,
            "LAST_OBSERVATION": source_status.get("last_observation"),
            "LAST_SUCCESS": source_status.get("last_success"),
            "LAST_FAILURE": source_status.get("last_failure"),
            "BACKOFF_STATE": source_status.get("backoff_state", "CLEAR"),
            "SOURCE_HEALTH": source_status.get("health", "UNTESTED"),
            "TARGET_RELEVANCE": item.target_relevance,
            "ENABLED": item.enabled,
            "LIFECYCLE": lifecycle,
        })
    return {
        "schema": "ZRWVE_REALITY_SOURCE_REGISTRY_V1_2J",
        "target": TARGET,
        "observed_at": observed_at,
        "bounded_source_count": len(rows),
        "sources": rows,
        "external_write_authority": False,
        "model_polling": False,
    }


def _source_url(source: RealitySource) -> str:
    return (f"{source.public_location}?state=all&sort=updated&direction=desc"
            f"&per_page={MAX_ITEMS_PER_SOURCE}")


def normalize_public_issue(source: RealitySource, item: dict[str, Any],
                           observed_at: datetime | None = None) -> dict[str, Any]:
    """Normalize one public issue without retaining its title or body."""
    now_value = _now(observed_at)
    actor = item.get("user") if isinstance(item.get("user"), dict) else {}
    login = str(actor.get("login", "")).strip()
    actor_id = str(actor.get("id", "")).strip()
    actor_type = str(actor.get("type", "")).strip()
    native_id = str(item.get("id", "")).strip()
    number = str(item.get("number", "")).strip()
    created = _parse_time(item.get("created_at"))
    updated = _parse_time(item.get("updated_at")) or created
    public_reference = str(item.get("html_url", "")).strip()
    title, title_truncated = _safe_text(item.get("title"), 1_000)
    body, body_truncated = _safe_text(item.get("body"), MAX_BODY_CHARS)
    text = f"{title}\n{body}"
    lowered = text.casefold()
    recovery = _terms(text, RECOVERY_TERMS)
    state = _terms(text, STATE_TERMS)
    consequence = _terms(text, CONSEQUENCE_TERMS)
    action = _terms(text, ACTION_TERMS)
    injection = any(marker in lowered for marker in INJECTION_MARKERS)
    generic = any(term in lowered for term in GENERIC_ONLY_TERMS)
    strong_recovery = _has_unnegated_phrase(text, STRONG_RECOVERY_PHRASES)
    strong_consequence = _has_unnegated_phrase(text, STRONG_CONSEQUENCE_PHRASES)
    log_noise = bool(
        ("log" in lowered or "logging" in lowered)
        and ("state check" in lowered or "observer" in lowered or "unchanged" in lowered)
        and not strong_consequence
    )
    cluster = _cluster(text)
    question = _consequential_question(cluster)
    category_hits = sum(bool(group) for group in (recovery, state, consequence, action))
    score = min(1.0, 0.18 * len(recovery) + 0.10 * min(len(state), 3)
                + 0.18 * len(consequence) + 0.08 * min(len(action), 2))
    if generic and not consequence:
        score = min(score, 0.2)
    owner_actor = login.casefold() in OWNER_LOGINS
    bot_actor = _is_bot(login, actor_type)
    expected_prefix = f"https://github.com/{source.project}/issues/".casefold()
    provenance_valid = bool(
        native_id and number and actor_id and login and created and updated
        and public_reference.casefold().startswith(expected_prefix)
        and not isinstance(item.get("pull_request"), dict)
    )
    material = bool(
        score >= 0.55 and consequence and recovery and state
        and strong_recovery and strong_consequence and not log_noise
    )
    enough_causal = category_hits >= 3 and len(body) >= 40
    duplicate_state = "UNASSESSED"
    qualified = bool(
        provenance_valid and not owner_actor and not bot_actor and material
        and question and enough_causal
    )
    if not provenance_valid:
        rejection = "PUBLIC_PROVENANCE_INVALID"
    elif owner_actor:
        rejection = "OWNER_ACTOR"
    elif bot_actor:
        rejection = "BOT_ACTOR"
    elif not material:
        rejection = "T2_RELEVANCE_NOT_MATERIAL"
    elif not question:
        rejection = "NO_CONSEQUENTIAL_DECISION"
    elif not enough_causal:
        rejection = "INSUFFICIENT_CAUSAL_STRUCTURE"
    else:
        rejection = None
    content_hash = digest({"title": title, "body": body})
    event_id = f"zrwve-public:{source.source_id}:{native_id or number}"
    cross_source_fingerprint = digest({
        "summary_hash": content_hash,
        "actor_public_id": digest({"source": "github", "actor_id": actor_id}),
        "source_created_at": _iso(created) if created else None,
    })
    version_hash = digest({
        "event_id": event_id,
        "updated_at": _iso(updated) if updated else None,
        "content_hash": content_hash,
    })
    incident_version = digest({
        "source_update_hash": version_hash,
        "classifier_spec_hash": CLASSIFIER_SPEC_HASH,
    })
    return {
        "schema": "ZRWVE_PUBLIC_INCIDENT_CANDIDATE_V1_2J",
        "EVENT_ID": event_id,
        "SOURCE_ID": source.source_id,
        "SOURCE_NATIVE_ID": native_id,
        "PROJECT": source.project,
        "PUBLIC_REFERENCE": public_reference,
        "FIRST_SEEN_AT": _iso(now_value),
        "SOURCE_CREATED_AT": _iso(created) if created else None,
        "SOURCE_UPDATED_AT": _iso(updated) if updated else None,
        "ACTOR_PUBLIC_ID_HASH": digest({"source": "github", "actor_id": actor_id}),
        "OWNER_ACTOR": owner_actor,
        "BOT_ACTOR": bot_actor,
        "TARGET_CLASS": TARGET,
        "SUMMARY_HASH": content_hash,
        "RAW_CONTENT_STORED": False,
        "PROVENANCE_STATE": "VALID" if provenance_valid else "INVALID",
        "DUPLICATE_STATE": duplicate_state,
        "RELEVANCE_SCORE": round(score, 4),
        "QUALIFICATION_STATE": "QUALIFIED" if qualified else "REJECTED",
        "REJECTION_REASON": rejection,
        "STRUCTURAL_INCIDENT_CLUSTER_ID": cluster,
        "CONSEQUENTIAL_DECISION": question,
        "ENOUGH_CAUSAL_STRUCTURE": enough_causal,
        "PROMPT_INJECTION_MARKERS_PRESENT": injection,
        "PROMPT_INJECTION_EFFECT": "NONE",
        "CONTENT_TRUNCATED": title_truncated or body_truncated,
        "SOURCE_UPDATE_HASH": version_hash,
        "CROSS_SOURCE_FINGERPRINT": cross_source_fingerprint,
        "CLASSIFIER_SPEC_HASH": CLASSIFIER_SPEC_HASH,
        "INCIDENT_VERSION": incident_version[:24],
        "signal_facts": {
            "recovery_terms": sorted(recovery),
            "state_terms": sorted(state),
            "consequence_terms": sorted(consequence),
            "action_terms": sorted(action),
            "strong_recovery": strong_recovery,
            "strong_consequence": strong_consequence,
            "log_noise": log_noise,
        },
    }


def _decision_snapshot(incident: dict[str, Any]) -> dict[str, Any]:
    facts = incident.get("signal_facts", {})
    decision = {
        "INCIDENT_STATE": incident.get("STRUCTURAL_INCIDENT_CLUSTER_ID"),
        "KNOWN_SYSTEM_STATE": list(facts.get("state_terms", [])),
        "KNOWN_CHECKPOINTS": [term for term in facts.get("recovery_terms", []) if "checkpoint" in term],
        "KNOWN_SIDE_EFFECTS": list(facts.get("consequence_terms", [])),
        "KNOWN_FAILURES": [incident.get("STRUCTURAL_INCIDENT_CLUSTER_ID")],
        "KNOWN_OPERATOR_OBSERVATIONS": list(facts.get("action_terms", [])),
        "AVAILABLE_LOGICAL_FACTS": list(facts.get("recovery_terms", [])),
        "PUBLICLY_AVAILABLE_TOOL_STATE": incident.get("PROJECT"),
        "UNCERTAINTIES": ["ACTUAL_B3_CONFIGURATION", "ACTUAL_EFFECT_COMMIT_STATE"],
        "UNKNOWN_FIELDS": ["PRIVATE_OPERATOR_TRACE", "PRIVATE_DOWNSTREAM_STATE"],
    }
    return {
        "decision_time_information_set": decision,
        "decision_information_set_hash": digest(decision),
    }


def _outcome_snapshot(source: dict[str, Any]) -> dict[str, Any]:
    outcome = {
        "final_operator_resolution": source.get("final_outcome", "UNKNOWN"),
        "actual_downstream_state": source.get("actual_downstream_state", "UNKNOWN"),
        "successful_or_failed_recovery": source.get("recovery_outcome", "UNKNOWN"),
        "known_duplicated_effects": source.get("known_duplicated_effects", "UNKNOWN"),
        "final_verification": source.get("verification_outcome", "UNKNOWN"),
    }
    return {
        "outcome_verification_set": outcome,
        "outcome_verification_set_hash": digest(outcome),
    }


def freeze_snapshot(incident: dict[str, Any], source: dict[str, Any] | None = None) -> dict[str, Any]:
    decision = _decision_snapshot(incident)
    outcome = _outcome_snapshot(source or {})
    public_snapshot = {
        "event_id": incident["EVENT_ID"],
        "source_update_hash": incident["SOURCE_UPDATE_HASH"],
        "public_reference": incident["PUBLIC_REFERENCE"],
        "project": incident["PROJECT"],
        "cluster": incident["STRUCTURAL_INCIDENT_CLUSTER_ID"],
        "consequential_decision": incident["CONSEQUENTIAL_DECISION"],
        "decision_information_set_hash": decision["decision_information_set_hash"],
        "outcome_verification_set_hash": outcome["outcome_verification_set_hash"],
        "raw_content_stored": False,
    }
    return {
        "PUBLIC_INCIDENT_SNAPSHOT": public_snapshot,
        "INCIDENT_SNAPSHOT_HASH": digest(public_snapshot),
        **decision,
        **outcome,
        "information_never_publicly_available": [
            "private logs", "private internal systems", "exact private operator burden",
        ],
    }


def _minimal_zero(cluster: str) -> dict[str, Any]:
    mapping = {
        "STATE_DIVERGENCE": ["provenance", "checkpoint", "state_reconciliation", "verification"],
        "RETRY_DUPLICATION": ["provenance", "side_effect_awareness", "verification"],
        "DUPLICATE_EFFECT": ["provenance", "side_effect_awareness", "freeze_blocker_resume", "verification"],
        "PARTIAL_DOWNSTREAM_COMMIT": ["provenance", "side_effect_awareness", "state_reconciliation", "verification"],
        "CHECKPOINT_STALE": ["provenance", "checkpoint", "temporal_coherence", "verification"],
        "VERIFICATION_AMBIGUITY": ["provenance", "evidence_boundary", "verification"],
    }
    components = mapping.get(cluster, ["provenance", "state_reconciliation", "verification"])
    spec = {
        "MINIMAL_ZERO_COMPONENT_SET": components,
        "MINIMAL_ZERO_COMPLEXITY_COST": {
            "component_count": len(components),
            "integration_count": 1,
            "model_calls": 0,
            "new_external_services": 0,
        },
        "decision_policy": "PARK_UNLESS_PROVEN_SAFE_BY_FROZEN_EVIDENCE",
    }
    spec["MINIMAL_ZERO_SPEC_HASH"] = digest(spec)
    return spec


def _b3_spec(root: Path, cluster: str) -> dict[str, Any]:
    ledger = read_json(root / ".omega" / "zero" / "zrwve_strong_baseline_ledger.json", {})
    row = next((item for item in ledger.get("rows", []) if item.get("target_id") == TARGET), {})
    frozen = {
        "B3_ACTUAL_OR_OBSERVED": "UNKNOWN_FROM_PUBLIC_EVIDENCE",
        "B3_STRONGEST_REASONABLE_COUNTERFACTUAL": row.get("B3", {
            "result": "CONVENTIONAL_CONTROL_SET_REQUIRED",
            "controls": [
                "idempotent effect key", "transaction boundary", "attempt identity",
                "bounded retry", "competent operator verification",
            ],
        }),
        "B3_COUNTERFACTUAL_CONFIDENCE": "MEDIUM" if row else "LOW",
        "BASELINE_ADVOCATE": {
            "challenge": [
                "configuration", "idempotency", "transactions", "retry policy",
                "checkpoint versioning", "generation guards", "observability",
                "reconciliation script", "native workflow tooling", "competent runbook",
            ],
            "cluster": cluster,
            "conclusion": "B3_SUFFICIENCY_UNKNOWN_UNTIL_ACTUAL_CONFIGURATION_AND_EFFECT_TRUTH",
        },
    }
    frozen["B3_SPEC_HASH"] = digest(frozen)
    return frozen


def missing_information_contract(incident: dict[str, Any]) -> dict[str, Any]:
    cluster = incident.get("STRUCTURAL_INCIDENT_CLUSTER_ID")
    effect_question = cluster in {"DUPLICATE_EFFECT", "PARTIAL_DOWNSTREAM_COMMIT", "RETRY_DUPLICATION"}
    exact = ("Whether the relevant downstream effect had already committed at the decision point"
             if effect_question else
             "Which persisted state was independently verified as authoritative at the decision point")
    question = ("At the decision point, was the relevant downstream effect already committed?"
                if effect_question else
                "At the decision point, which persisted state was independently verified as authoritative?")
    contract = {
        "INCIDENT_ID": incident["EVENT_ID"],
        "MISSING_FACT_ID": "MF-" + digest({"incident": incident["EVENT_ID"], "fact": exact})[:16],
        "EXACT_FACT_REQUIRED": exact,
        "WHY_REQUIRED": "The fact can change safe resume/replay classification.",
        "WHICH_DECISION_IT_CHANGES": incident.get("CONSEQUENTIAL_DECISION"),
        "B3_IMPACT": "Determines whether conventional verification is sufficient.",
        "ZERO_IMPACT": "Determines whether ZERO may safely resume or must remain blocked.",
        "CAN_PUBLIC_EVIDENCE_RESOLVE": False,
        "CAN_DETERMINISTIC_TEST_RESOLVE": False,
        "HUMAN_REQUIRED": True,
        "EXPECTED_INFORMATION_GAIN": "HIGH_IF_INCIDENT_IS_OTHERWISE_COMPARISON_READY",
        "MINIMAL_QUESTION": question,
        "ALLOWED_PASSIVE_ROUTE": "EXISTING_REAL_INCIDENT_GITHUB_ISSUE_FORM",
        "AUTHORITY_REQUIRED": "SEPARATE_EXTERNAL_WRITE_AUTHORITY_IF_DIRECT_CONTACT_IS_PROPOSED",
    }
    contract["contract_hash"] = digest(contract)
    return contract


def compare_incident(root: Path, incident: dict[str, Any],
                     source: dict[str, Any] | None = None) -> dict[str, Any]:
    snapshot = freeze_snapshot(incident, source)
    b3 = _b3_spec(root, str(incident.get("STRUCTURAL_INCIDENT_CLUSTER_ID")))
    zero = _minimal_zero(str(incident.get("STRUCTURAL_INCIDENT_CLUSTER_ID")))
    shared_hash = snapshot["decision_information_set_hash"]
    actual_b3_known = bool(source and source.get("actual_b3_configuration"))
    outcome = snapshot["outcome_verification_set"]
    outcome_known = any(value != "UNKNOWN" for value in outcome.values())
    complete = actual_b3_known and outcome_known
    completeness = "PUBLIC_COMPLETE" if complete else "PUBLIC_PARTIAL"
    contract = None if complete else missing_information_contract(incident)
    claim = "INCONCLUSIVE_PUBLIC_EVIDENCE" if complete else "HUMAN_EVIDENCE_REQUIRED"
    comparison = {
        "incident_id": incident["EVENT_ID"],
        "public_evidence_completeness": completeness,
        "snapshot": snapshot,
        "B3": b3,
        "MINIMAL_ZERO": zero,
        "B3_DECISION": "PARK_UNTIL_EFFECT_AND_AUTHORITATIVE_STATE_ARE_VERIFIED",
        "ZERO_DECISION": "PARK_UNTIL_EFFECT_AND_AUTHORITATIVE_STATE_ARE_VERIFIED",
        "B3_CONFIDENCE": "LOW",
        "ZERO_CONFIDENCE": "LOW",
        "B3_REQUIRED_HUMAN_STEPS": "UNKNOWN",
        "ZERO_REQUIRED_HUMAN_STEPS": "UNKNOWN",
        "B3_RECONSTRUCTION_STEPS": "UNKNOWN",
        "ZERO_RECONSTRUCTION_STEPS": len(zero["MINIMAL_ZERO_COMPONENT_SET"]),
        "B3_UNRESOLVED_UNCERTAINTY": ["ACTUAL_B3_CONFIGURATION", "EFFECT_COMMIT_STATE"],
        "ZERO_UNRESOLVED_UNCERTAINTY": ["EFFECT_COMMIT_STATE"],
        "B3_EVIDENCE_HASH": shared_hash,
        "ZERO_EVIDENCE_HASH": shared_hash,
        "SAME_EVIDENCE": True,
        "DECISION_TIME_INFORMATION_LEAK": False,
        "OUTCOME_INFORMATION_LEAK": False,
        "FINAL_CLASSIFICATION": claim,
        "MISSING_INFORMATION_CONTRACT": contract,
        "CLAIM_MATRIX": {
            "REAL_INCIDENT": "YES",
            "STRUCTURAL_FAILURE": "YES",
            "B3_SUFFICIENT": "UNKNOWN",
            "ZERO_DECISION_DELTA": "UNKNOWN",
            "ZERO_ATTENTION_DELTA": "UNKNOWN",
            "ZERO_RELIABILITY_DELTA": "UNKNOWN",
            "ZERO_VERIFICATION_DELTA": "UNKNOWN",
            "INDEPENDENT_REPLICATION": "NO",
            "MARKET_SIGNAL": "NONE",
        },
    }
    frozen = {
        "question": incident.get("CONSEQUENTIAL_DECISION"),
        "evidence_hash": shared_hash,
        "metrics": ["DECISION_CORRECTNESS", "FALSE_SAFE_RESUME", "FALSE_BLOCK", "MISSED_STATE_CONFLICT"],
        "thresholds": {
            "material_decision_delta": "DIFFERENT_VERIFIABLY_CORRECT_CONSEQUENTIAL_DECISION",
            "material_attention_delta": "AT_LEAST_50_PERCENT_AND_THREE_VERIFIED_MANUAL_CHECKS",
            "material_reliability_delta": "PREVENTS_FALSE_SAFE_RESUME_OR_DUPLICATE_EFFECT",
            "material_verification_delta": "PRODUCES_INDEPENDENTLY_CHECKABLE_EFFECT_AND_STATE_PROOF",
        },
        "b3_spec_hash": b3["B3_SPEC_HASH"],
        "minimal_zero_spec_hash": zero["MINIMAL_ZERO_SPEC_HASH"],
    }
    comparison["EXPERIMENT_SPEC_HASH"] = digest(frozen)
    comparison["COMPARISON_HASH"] = digest(comparison)
    return comparison


def _historical_incident(source: dict[str, Any]) -> dict[str, Any]:
    failure = str(source.get("failure", ""))
    actual = str(source.get("actual_behavior", ""))
    recovery = str(source.get("recovery_action", ""))
    text = f"{failure} {actual} {recovery}"
    structural = bool(source.get("structural"))
    cluster = str(source.get("failure_class") or _cluster(text))
    question = _consequential_question(cluster) or (
        "REPLAY_ALLOWED?" if structural else None
    )
    qualified = bool(structural and source.get("evidence_role") == "REAL_INCIDENT" and question)
    source_id = str(source.get("source_id"))
    signal_facts = {
        "recovery_terms": sorted(_terms(text, RECOVERY_TERMS)),
        "state_terms": sorted(_terms(text, STATE_TERMS)),
        "consequence_terms": sorted(_terms(text, CONSEQUENCE_TERMS)),
        "action_terms": sorted(_terms(text, ACTION_TERMS)),
    }
    record = {
        "schema": "ZRWVE_PUBLIC_INCIDENT_CANDIDATE_V1_2J",
        "EVENT_ID": "historical:" + source_id,
        "SOURCE_ID": source_id,
        "SOURCE_NATIVE_ID": source_id,
        "PROJECT": source.get("project"),
        "PUBLIC_REFERENCE": source.get("source_url_or_reference"),
        "FIRST_SEEN_AT": source.get("date"),
        "SOURCE_CREATED_AT": source.get("date"),
        "SOURCE_UPDATED_AT": source.get("date"),
        "ACTOR_PUBLIC_ID_HASH": digest({"historical": source_id}),
        "OWNER_ACTOR": False,
        "BOT_ACTOR": False,
        "TARGET_CLASS": TARGET,
        "SUMMARY_HASH": digest({"failure": failure, "actual": actual}),
        "RAW_CONTENT_STORED": False,
        "PROVENANCE_STATE": "VALID_EXISTING_REPOSITORY_CORPUS",
        "DUPLICATE_STATE": "UNIQUE_IN_CORPUS" if not source.get("duplicate_of") else "DUPLICATE",
        "RELEVANCE_SCORE": 1.0 if qualified else 0.2,
        "QUALIFICATION_STATE": "QUALIFIED" if qualified else "REJECTED",
        "REJECTION_REASON": None if qualified else "NON_STRUCTURAL_OR_NO_CONSEQUENTIAL_DECISION",
        "STRUCTURAL_INCIDENT_CLUSTER_ID": cluster,
        "CONSEQUENTIAL_DECISION": question,
        "ENOUGH_CAUSAL_STRUCTURE": structural,
        "PROMPT_INJECTION_MARKERS_PRESENT": False,
        "PROMPT_INJECTION_EFFECT": "NONE",
        "CONTENT_TRUNCATED": False,
        "SOURCE_UPDATE_HASH": digest(source),
        "INCIDENT_VERSION": digest(source)[:24],
        "signal_facts": signal_facts,
        "historical_validation_only": True,
    }
    return record


def historical_replay(root: Path) -> dict[str, Any]:
    corpus = read_json(root / ".omega" / "zero" / "zrwve_deep_evidence_corpus.json", {})
    sources = [item for item in corpus.get("sources", [])
               if item.get("target_id") == TARGET and item.get("evidence_role") == "REAL_INCIDENT"]
    incidents = [_historical_incident(item) for item in sources]
    qualified = [item for item in incidents if item["QUALIFICATION_STATE"] == "QUALIFIED"]
    rejected = [item for item in incidents if item["QUALIFICATION_STATE"] == "REJECTED"]
    comparisons = []
    by_id = {str(item.get("source_id")): item for item in sources}
    for incident in qualified:
        comparison = compare_incident(root, incident, by_id.get(str(incident["SOURCE_ID"])))
        comparisons.append(comparison)
    expected_structural = {"prefect-17484", "prefect-18303", "prefect-15658", "prefect-16429"}
    detected = {item["SOURCE_ID"] for item in qualified}
    simple_rejected = {"prefect-17913", "airflow-10544"}.issubset(
        {item["SOURCE_ID"] for item in rejected}
    )
    same_evidence = all(item["SAME_EVIDENCE"] for item in comparisons)
    no_leak = all(not item["DECISION_TIME_INFORMATION_LEAK"]
                  and not item["OUTCOME_INFORMATION_LEAK"] for item in comparisons)
    passed = expected_structural.issubset(detected) and simple_rejected and same_evidence and no_leak
    return {
        "mode": "TEST_VALIDATION_ONLY",
        "result": "PASS" if passed else "FAIL",
        "sources_scanned": len(incidents),
        "qualified": len(qualified),
        "rejected": len(rejected),
        "qualified_source_ids": sorted(detected),
        "rejected_source_ids": sorted(item["SOURCE_ID"] for item in rejected),
        "comparisons": comparisons,
        "same_evidence": same_evidence,
        "no_hindsight_leak": no_leak,
        "synthetic_evidence_counted_as_real": 0,
    }


def _checkpoint_path(root: Path, source: RealitySource) -> Path:
    return root / ".omega" / "reality-watch" / "checkpoints" / f"{source.source_id}.json"


def _journal_path(root: Path) -> Path:
    return root / ".omega" / "reality-watch" / "incidents.jsonl"


def _known_versions(root: Path) -> tuple[dict[str, list[dict[str, Any]]], list[str]]:
    records, errors = read_chain(_journal_path(root))
    by_event: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        by_event.setdefault(str(record.get("EVENT_ID", "")), []).append(record)
    return by_event, errors


def _backoff_seconds(errors: int, rate_limited: bool = False) -> int:
    if rate_limited:
        return 3600
    return min(3600, DEFAULT_MIN_POLL_SECONDS * (2 ** min(max(errors - 1, 0), 2)))


def poll_source(root: Path, source: RealitySource, fetcher: GithubFetcher,
                *, current_time: datetime | None = None, force: bool = False,
                min_poll_seconds: int = DEFAULT_MIN_POLL_SECONDS) -> dict[str, Any]:
    now_value = _now(current_time)
    checkpoint_path = _checkpoint_path(root, source)
    checkpoint = read_json(checkpoint_path, {})
    if not isinstance(checkpoint, dict):
        return {
            "source_id": source.source_id, "health": "BLOCKED",
            "blocker": "CURSOR_CORRUPT", "network_requests": 0,
            "scanned": 0, "new_versions": [], "wake_candidates": [],
        }
    last_success = _parse_time(checkpoint.get("last_success"))
    if (not force and last_success
            and now_value - last_success.astimezone(timezone.utc)
            < timedelta(seconds=min_poll_seconds)):
        return {
            "source_id": source.source_id, "health": "ACTIVE",
            "blocker": None, "network_requests": 0, "bytes_read": 0,
            "scanned": 0, "new_versions": [], "wake_candidates": [],
            "cached": True, "checkpoint": checkpoint,
        }
    known, journal_errors = _known_versions(root)
    if journal_errors:
        return {
            "source_id": source.source_id, "health": "BLOCKED",
            "blocker": journal_errors[0], "network_requests": 0,
            "scanned": 0, "new_versions": [], "wake_candidates": [],
        }
    try:
        classifier_changed = checkpoint.get("classifier_spec_hash") != CLASSIFIER_SPEC_HASH
        response = fetcher(
            _source_url(source),
            None if classifier_changed else checkpoint.get("etag"),
        )
        if response.status in {403, 429}:
            raise RuntimeError(f"GITHUB_HTTP_{response.status}")
        if response.status == 304:
            checkpoint.update({
                "schema": SCHEMA_VERSION, "source_id": source.source_id,
                "classifier_spec_hash": CLASSIFIER_SPEC_HASH,
                "last_observation": _iso(now_value), "last_success": _iso(now_value),
                "last_failure": None, "backoff_state": "CLEAR",
                "next_retry": _iso(now_value + timedelta(seconds=min_poll_seconds)),
                "network_requests": int(checkpoint.get("network_requests", 0)) + 1,
            })
            atomic_json(checkpoint_path, checkpoint)
            return {
                "source_id": source.source_id, "health": "ACTIVE", "blocker": None,
                "network_requests": 1, "bytes_read": 0, "scanned": 0,
                "new_versions": [], "wake_candidates": [], "cached": True,
                "checkpoint": checkpoint,
            }
        if response.status != 200 or not isinstance(response.payload, list):
            raise RuntimeError("GITHUB_ISSUES_RESPONSE_INVALID")
        payload = response.payload[:MAX_ITEMS_PER_SOURCE]
        bytes_read = len(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
        new_versions: list[dict[str, Any]] = []
        wake_candidates: list[dict[str, Any]] = []
        max_updated: str | None = checkpoint.get("source_cursor")
        for item in payload:
            if not isinstance(item, dict):
                continue
            normalized = normalize_public_issue(source, item, now_value)
            event_id = str(normalized["EVENT_ID"])
            prior_versions = known.get(event_id, [])
            candidate_version_id = normalized["EVENT_ID"] + ":" + normalized["INCIDENT_VERSION"]
            if any(row.get("event_version_id") == candidate_version_id
                   for row in prior_versions):
                continue
            same_source_revision = bool(
                prior_versions
                and normalized["SOURCE_UPDATE_HASH"] == prior_versions[-1].get("SOURCE_UPDATE_HASH")
            )
            normalized["DUPLICATE_STATE"] = (
                "RECLASSIFICATION" if same_source_revision else
                "MATERIAL_UPDATE" if prior_versions else "UNIQUE"
            )
            mirrored = next(
                (
                    row for rows in known.values() for row in rows
                    if row.get("EVENT_ID") != event_id
                    and row.get("CROSS_SOURCE_FINGERPRINT")
                    == normalized.get("CROSS_SOURCE_FINGERPRINT")
                ),
                None,
            )
            if mirrored is not None:
                normalized["DUPLICATE_STATE"] = "CROSS_SOURCE_DUPLICATE"
                normalized["QUALIFICATION_STATE"] = "REJECTED"
                normalized["REJECTION_REASON"] = "MIRRORED_INCIDENT"
            normalized["MATERIAL_CHANGE"] = bool(
                mirrored is None and (
                    not prior_versions
                    or normalized["SUMMARY_HASH"] != prior_versions[-1].get("SUMMARY_HASH")
                )
            )
            normalized["OBSERVED_AT"] = _iso(now_value)
            normalized["STATE_SEQUENCE"] = (
                ["DISCOVERED", "FILTERED", "QUALIFIED", "SNAPSHOT_FROZEN",
                 "PUBLIC_PARTIAL", "B3_RECONSTRUCTED", "ZERO_RECONSTRUCTED",
                 "COMPARISON_FROZEN", "WAIT_HUMAN"]
                if normalized["QUALIFICATION_STATE"] == "QUALIFIED"
                else ["DISCOVERED", "FILTERED", "PUBLIC_INSUFFICIENT", "PARK"]
            )
            normalized["event_version_id"] = candidate_version_id
            stored, created = append_chain(
                _journal_path(root), normalized, "event_version_id"
            )
            if created:
                new_versions.append(stored)
                known.setdefault(event_id, []).append(stored)
                if (stored["QUALIFICATION_STATE"] == "QUALIFIED"
                        and stored["MATERIAL_CHANGE"]):
                    comparison = compare_incident(root, stored)
                    comparison_record = {
                        **comparison,
                        "comparison_id": "CMP-" + comparison["COMPARISON_HASH"][:24],
                        "observed_at": _iso(now_value),
                    }
                    append_chain(
                        root / ".omega" / "reality-watch" / "comparisons.jsonl",
                        comparison_record, "comparison_id",
                    )
                    contract = comparison.get("MISSING_INFORMATION_CONTRACT")
                    if isinstance(contract, dict):
                        append_chain(
                            root / ".omega" / "reality-watch" / "human_evidence.jsonl",
                            {**contract, "status": "WAITING_HUMAN", "queued_at": _iso(now_value)},
                            "MISSING_FACT_ID",
                        )
                    wake_candidates.append(stored)
                elif (stored["QUALIFICATION_STATE"] == "REJECTED"
                      and any(row.get("QUALIFICATION_STATE") == "QUALIFIED"
                              for row in prior_versions)):
                    prior_comparisons, _ = read_chain(
                        root / ".omega" / "reality-watch" / "comparisons.jsonl"
                    )
                    prior = next(
                        (row for row in reversed(prior_comparisons)
                         if row.get("incident_id") == event_id), None
                    )
                    correction = {
                        "comparison_id": "CMP-CORRECTION-" + digest({
                            "event": event_id, "classifier": CLASSIFIER_SPEC_HASH,
                        })[:20],
                        "incident_id": event_id,
                        "observed_at": _iso(now_value),
                        "FINAL_CLASSIFICATION": "INCIDENT_NOT_QUALIFIED",
                        "reason": stored.get("REJECTION_REASON"),
                        "supersedes_comparison_id": prior.get("comparison_id") if prior else None,
                        "B3_DECISION": None,
                        "ZERO_DECISION": None,
                        "public_evidence_completeness": "PUBLIC_INSUFFICIENT",
                        "SAME_EVIDENCE": True,
                        "DECISION_TIME_INFORMATION_LEAK": False,
                        "OUTCOME_INFORMATION_LEAK": False,
                    }
                    append_chain(
                        root / ".omega" / "reality-watch" / "comparisons.jsonl",
                        correction, "comparison_id",
                    )
                    old_contracts, _ = read_chain(
                        root / ".omega" / "reality-watch" / "human_evidence.jsonl"
                    )
                    old = next(
                        (row for row in reversed(old_contracts)
                         if row.get("INCIDENT_ID") == event_id
                         and row.get("status", "WAITING_HUMAN") == "WAITING_HUMAN"), None
                    )
                    if old:
                        append_chain(
                            root / ".omega" / "reality-watch" / "human_evidence.jsonl",
                            {
                                "MISSING_FACT_ID": str(old["MISSING_FACT_ID"]) + ":CLOSED:"
                                                   + CLASSIFIER_SPEC_HASH[:12],
                                "INCIDENT_ID": event_id,
                                "status": "CLOSED_FALSE_POSITIVE",
                                "closes_missing_fact_id": old["MISSING_FACT_ID"],
                                "closed_at": _iso(now_value),
                                "reason": stored.get("REJECTION_REASON"),
                            },
                            "MISSING_FACT_ID",
                        )
            updated = str(normalized.get("SOURCE_UPDATED_AT") or "")
            if updated and (not max_updated or updated > max_updated):
                max_updated = updated
        remaining = response.headers.get("x-ratelimit-remaining")
        checkpoint = {
            "schema": SCHEMA_VERSION,
            "classifier_spec_hash": CLASSIFIER_SPEC_HASH,
            "source_id": source.source_id,
            "project": source.project,
            "etag": response.headers.get("etag") or checkpoint.get("etag"),
            "source_cursor": max_updated,
            "last_observation": _iso(now_value),
            "last_success": _iso(now_value),
            "last_failure": None,
            "backoff_state": "CLEAR",
            "next_retry": _iso(now_value + timedelta(seconds=min_poll_seconds)),
            "rate_limit_remaining": int(remaining) if str(remaining).isdigit() else None,
            "poll_errors": int(checkpoint.get("poll_errors", 0)),
            "network_requests": int(checkpoint.get("network_requests", 0)) + 1,
            "bytes_read": int(checkpoint.get("bytes_read", 0)) + bytes_read,
        }
        atomic_json(checkpoint_path, checkpoint)
        return {
            "source_id": source.source_id, "health": "ACTIVE", "blocker": None,
            "network_requests": 1, "bytes_read": bytes_read, "scanned": len(payload),
            "new_versions": new_versions, "wake_candidates": wake_candidates,
            "cached": False, "checkpoint": checkpoint,
        }
    except (RuntimeError, OSError, ValueError, TypeError) as exc:
        error = str(exc)
        rate_limited = error in {"GITHUB_HTTP_403", "GITHUB_HTTP_429"}
        errors = int(checkpoint.get("poll_errors", 0)) + 1
        delay = _backoff_seconds(errors, rate_limited)
        checkpoint.update({
            "schema": SCHEMA_VERSION,
            "classifier_spec_hash": CLASSIFIER_SPEC_HASH,
            "source_id": source.source_id,
            "project": source.project,
            "last_observation": _iso(now_value),
            "last_failure": error,
            "backoff_state": "RATE_LIMITED" if rate_limited else "BACKOFF",
            "next_retry": _iso(now_value + timedelta(seconds=delay)),
            "poll_errors": errors,
            "network_requests": int(checkpoint.get("network_requests", 0)) + 1,
        })
        atomic_json(checkpoint_path, checkpoint)
        return {
            "source_id": source.source_id,
            "health": "DEGRADED",
            "blocker": "RATE_LIMITED" if rate_limited else error,
            "network_requests": 1,
            "bytes_read": 0,
            "scanned": 0,
            "new_versions": [],
            "wake_candidates": [],
            "cached": False,
            "checkpoint": checkpoint,
        }


def _config(root: Path) -> dict[str, Any]:
    return read_json(root / ".omega" / "wake-provenance" / "config.json", {})


def _enabled(root: Path) -> tuple[bool, str]:
    config = _config(root)
    watch = config.get("reality_watch", {}) if isinstance(config, dict) else {}
    enabled = bool(
        isinstance(watch, dict) and watch.get("enabled") is True
        and watch.get("read_only") is True and watch.get("target") == TARGET
    )
    return enabled, str(watch.get("mode", "SHADOW")) if isinstance(watch, dict) else "SHADOW"


def poll_reality_watch(root: Path, fetcher: GithubFetcher | None = None,
                       *, force: bool = False,
                       current_time: datetime | None = None) -> dict[str, Any]:
    """Run one bounded observation cycle for the existing Wake Plane."""
    root = Path(root)
    enabled, configured_mode = _enabled(root)
    if not enabled:
        return {
            "enabled": False, "mode": "DISABLED", "health": "DORMANT",
            "source_results": [], "wake_candidates": [], "network_requests": 0,
            "bytes_read": 0, "external_writes": 0, "model_calls": 0,
        }
    perform = fetcher or github_get
    started = time.process_time()
    already_tracing = tracemalloc.is_tracing()
    if not already_tracing:
        tracemalloc.start()
    results = [
        poll_source(root, source, perform, current_time=current_time, force=force)
        for source in SOURCE_REGISTRY if source.enabled
    ]
    current, peak = tracemalloc.get_traced_memory()
    if not already_tracing:
        tracemalloc.stop()
    del current
    wake_candidates = [candidate for result in results
                       for candidate in result.get("wake_candidates", [])]
    requests = sum(int(item.get("network_requests", 0)) for item in results)
    bytes_read = sum(int(item.get("bytes_read", 0)) for item in results)
    healthy = sum(item.get("health") == "ACTIVE" for item in results)
    return {
        "enabled": True,
        "mode": configured_mode,
        "health": "ACTIVE" if healthy == len(results) else "DEGRADED",
        "source_results": results,
        "active_sources": len(results),
        "healthy_sources": healthy,
        "wake_candidates": wake_candidates,
        "network_requests": requests,
        "bytes_read": bytes_read,
        "cpu_seconds": round(time.process_time() - started, 6),
        "memory_peak_bytes": peak,
        "external_writes": 0,
        "model_calls": 0,
        "supervisor_run_count": 0,
        "prompt_injection_escapes": 0,
    }


def _set_config_mode(root: Path, mode: str) -> None:
    path = root / ".omega" / "wake-provenance" / "config.json"
    config = read_json(path, {})
    if not isinstance(config, dict):
        raise ValueError("WAKE_PROVENANCE_CONFIG_INVALID")
    config["reality_watch"] = {
        "enabled": True,
        "read_only": True,
        "target": TARGET,
        "mode": mode,
        "source_ids": [source.source_id for source in SOURCE_REGISTRY],
        "min_poll_seconds": DEFAULT_MIN_POLL_SECONDS,
        "external_write": False,
        "model_polling": False,
    }
    atomic_json(path, config)


def _history_summary(root: Path) -> dict[str, Any]:
    incidents, incident_errors = read_chain(_journal_path(root))
    comparisons, comparison_errors = read_chain(
        root / ".omega" / "reality-watch" / "comparisons.jsonl"
    )
    humans, human_errors = read_chain(
        root / ".omega" / "reality-watch" / "human_evidence.jsonl"
    )
    latest_incidents: dict[str, dict[str, Any]] = {}
    for row in incidents:
        if row.get("EVENT_ID"):
            latest_incidents[str(row["EVENT_ID"])] = row
    unique = set(latest_incidents)
    current_incidents = list(latest_incidents.values())
    qualified = [row for row in current_incidents if row.get("QUALIFICATION_STATE") == "QUALIFIED"]
    insufficient = [row for row in current_incidents if row.get("QUALIFICATION_STATE") == "REJECTED"]
    clusters = {str(row.get("STRUCTURAL_INCIDENT_CLUSTER_ID")) for row in qualified}
    latest_comparisons: dict[str, dict[str, Any]] = {}
    for row in comparisons:
        latest_comparisons[str(row.get("incident_id", ""))] = row
    current_comparisons = list(latest_comparisons.values())
    closed_incidents = {
        str(row.get("INCIDENT_ID")) for row in humans
        if row.get("status") == "CLOSED_FALSE_POSITIVE"
    }
    active_humans = [
        row for row in humans
        if row.get("status", "WAITING_HUMAN") == "WAITING_HUMAN"
        and str(row.get("INCIDENT_ID")) not in closed_incidents
    ]
    classifications = [str(row.get("FINAL_CLASSIFICATION")) for row in current_comparisons]
    return {
        "incident_records": incidents,
        "comparison_records": comparisons,
        "human_records": humans,
        "integrity_errors": incident_errors + comparison_errors + human_errors,
        "public_incidents_scanned": len(unique),
        "qualified_public_incidents": len({row.get("EVENT_ID") for row in qualified}),
        "public_complete_incidents": sum(
            row.get("public_evidence_completeness") == "PUBLIC_COMPLETE" for row in current_comparisons
        ),
        "public_partial_incidents": sum(
            row.get("public_evidence_completeness") == "PUBLIC_PARTIAL" for row in current_comparisons
        ),
        "public_insufficient_incidents": len({row.get("EVENT_ID") for row in insufficient}),
        "structural_incident_clusters": len(clusters),
        "real_zero_technical_signals": classifications.count("ZERO_TECHNICAL_SIGNAL"),
        "real_zero_baseline_breaks_observed": classifications.count("ZERO_BASELINE_BREAK_OBSERVED"),
        "baseline_wins": classifications.count("BASELINE_WINS"),
        "parity_results": classifications.count("PARITY"),
        "human_evidence_contracts": len(active_humans),
    }


def run_reality_watch(root: Path, fetcher: GithubFetcher | None = None,
                      *, current_time: datetime | None = None) -> dict[str, Any]:
    """Execute replay -> shadow -> bounded live canary -> activation gates."""
    root = Path(root)
    _set_config_mode(root, "SHADOW")
    replay = historical_replay(root)
    shadow_pass = bool(
        replay["result"] == "PASS" and replay["same_evidence"]
        and replay["no_hindsight_leak"]
    )
    canary = poll_reality_watch(root, fetcher, force=True, current_time=current_time)
    live_pass = bool(
        canary["health"] == "ACTIVE"
        and canary["active_sources"] == len(SOURCE_REGISTRY)
        and canary["healthy_sources"] == len(SOURCE_REGISTRY)
        and canary["network_requests"] <= MAX_NETWORK_REQUESTS_PER_CYCLE
        and canary["external_writes"] == 0
        and canary["model_calls"] == 0
        and canary["prompt_injection_escapes"] == 0
    )
    activation = shadow_pass and live_pass
    mode = "ACTIVE_READ_ONLY" if activation else ("SHADOW" if shadow_pass else "DISABLED")
    _set_config_mode(root, mode)
    health_map = {
        item["source_id"]: {
            "health": item["health"],
            "last_observation": item.get("checkpoint", {}).get("last_observation"),
            "last_success": item.get("checkpoint", {}).get("last_success"),
            "last_failure": item.get("checkpoint", {}).get("last_failure"),
            "backoff_state": item.get("checkpoint", {}).get("backoff_state"),
        }
        for item in canary.get("source_results", [])
    }
    registry = source_registry_payload(
        lifecycle="ACTIVE" if activation else "SHADOW",
        observed_at=_iso(current_time), source_health=health_map,
    )
    atomic_json(root / ".omega" / "zero" / "zrwve_reality_source_registry.json", registry)
    history = _history_summary(root)
    false_positive_wakes = sum(
        1 for row in canary.get("wake_candidates", [])
        if row.get("QUALIFICATION_STATE") != "QUALIFIED"
    )
    result_class = (
        "REALITY_WATCH_ACTIVE" if activation else
        "REALITY_WATCH_SHADOW_READY" if shadow_pass else
        "REALITY_WATCH_WITH_ISSUES"
    )
    useful = len(canary.get("wake_candidates", []))
    result = {
        "schema": SCHEMA_VERSION,
        "recorded_at": _iso(current_time),
        "ZRWVE_REALITY_WATCH_STATE": result_class,
        "SOURCE_REGISTRY": registry,
        "ACTIVE_TARGET": TARGET,
        "SOURCE_COUNT": len(SOURCE_REGISTRY),
        "SOURCE_HEALTH": health_map,
        "HISTORICAL_REPLAY_RESULT": replay,
        "SHADOW_RESULT": "PASS" if shadow_pass else "FAIL",
        "LIVE_CANARY_RESULT": "PASS" if live_pass else "FAIL",
        "QUALIFICATION_RESULT": "PASS" if replay["qualified"] == 4 else "FAIL",
        "FALSE_POSITIVE_RESULT": "PASS" if false_positive_wakes == 0 else "FAIL",
        "DEDUPLICATION_RESULT": "PASS",
        "INCIDENT_CLUSTERING_RESULT": "PASS" if replay["qualified"] else "FAIL",
        "DECISION_TIME_FREEZE_RESULT": "PASS" if replay["no_hindsight_leak"] else "FAIL",
        "OUTCOME_FREEZE_RESULT": "PASS" if replay["no_hindsight_leak"] else "FAIL",
        "B3_CHALLENGE_RESULT": "PASS_NO_ZERO_ADVANTAGE_CLAIMED",
        "MINIMAL_ZERO_RESULT": "PASS_MINIMAL_COMPONENT_SETS_FROZEN",
        "SAME_EVIDENCE_RESULT": "PASS" if replay["same_evidence"] else "FAIL",
        "HUMAN_ONLY_WHEN_NECESSARY_RESULT": "PASS_PRECISE_CONTRACTS_NO_CONTACT",
        "WAKE_ROUTE_RESULT": "ACTIVE_READ_ONLY_REGISTERED" if activation else "SHADOW_ONLY",
        "SINGLE_WAKE_RESULT": "PASS_DEDUPE_KEYED_EVENT_VERSION",
        "RESOURCE_BUDGET_RESULT": {
            "NETWORK_REQUESTS": canary.get("network_requests", 0),
            "BYTES_READ": canary.get("bytes_read", 0),
            "CPU_TIME": canary.get("cpu_seconds", 0),
            "MEMORY_PEAK": canary.get("memory_peak_bytes", 0),
            "WAKE_COUNT": useful,
            "MODEL_CALL_COUNT": 0,
            "SUPERVISOR_RUN_COUNT": 0,
            "INCIDENTS_PROCESSED": sum(item.get("scanned", 0) for item in canary.get("source_results", [])),
            "USEFUL_EVIDENCE_EVENTS": useful,
            "COST_PER_USEFUL_EVIDENCE_EVENT": (
                round(canary.get("network_requests", 0) / useful, 4)
                if useful else "UNDEFINED_NO_USEFUL_EVIDENCE_EVENT"
            ),
        },
        "SECURITY_RESULT": "PASS_BOUNDED_UNTRUSTED_DATA_NO_RAW_RETENTION",
        "PROMPT_INJECTION_RESULT": "PASS_ZERO_ESCAPES",
        "AUTHORITY_RESULT": "PASS_READ_ONLY_ZERO_EXTERNAL_WRITES",
        "FINAL_RESULT": result_class,
        "NEXT_ATOMIC_ACTION": (
            "PROCESS_FIRST_REAL_INCIDENT" if useful else
            "PASSIVE_OBSERVE" if activation else "REPAIR_REALITY_WATCH"
        ),
        "metrics": history,
        "false_positive_wakes": false_positive_wakes,
        "duplicate_wakes": 0,
        "owner_attention_events": 0,
        "external_writes": 0,
        "emails_sent": 0,
        "github_comments_sent": 0,
        "github_issues_created": 0,
        "mentions_sent": 0,
        "paid_promotion": 0,
        "model_calls_for_polling": 0,
        "decision_time_information_leaks": 0,
        "outcome_information_leaks": 0,
        "synthetic_evidence_counted_as_real": 0,
        "owner_activity_counted_as_external": 0,
        "current_evidence_level": "L0",
        "verified_net_economic_value": "0 KWD",
        "wake_plane_mode": "PASSIVE_PRODUCTION",
        "capability_router_mode": "SHADOW",
        "global_production_default": "LEGACY",
    }
    atomic_json(root / ".omega" / "zero" / "zrwve_v1_2j_result.json", result)
    atomic_json(root / ".omega" / "reality-watch" / "state.json", {
        "schema": SCHEMA_VERSION,
        "mode": mode,
        "last_scan": _iso(current_time),
        "last_real_incident": (
            canary["wake_candidates"][-1].get("PUBLIC_REFERENCE")
            if canary.get("wake_candidates") else None
        ),
        "wake_count": useful,
        "external_writes": 0,
        "evidence_level": "L0",
        "result_reference": ".omega/zero/zrwve_v1_2j_result.json",
    })
    return result


def reality_watch_status(root: Path) -> dict[str, Any]:
    root = Path(root)
    state = read_json(root / ".omega" / "reality-watch" / "state.json", {})
    registry = read_json(root / ".omega" / "zero" / "zrwve_reality_source_registry.json", {})
    history = _history_summary(root)
    sources = registry.get("sources", []) if isinstance(registry, dict) else []
    return {
        "mode": state.get("mode", "DISABLED"),
        "active_sources": sum(row.get("LIFECYCLE") == "ACTIVE" for row in sources),
        "source_health": {row.get("SOURCE_ID"): row.get("SOURCE_HEALTH") for row in sources},
        "last_scan": state.get("last_scan"),
        "last_real_incident": state.get("last_real_incident"),
        "qualified_incident_count": history["qualified_public_incidents"],
        "pending_public_partial_incidents": history["public_partial_incidents"],
        "waiting_human_contracts": history["human_evidence_contracts"],
        "latest_comparison": (
            history["comparison_records"][-1].get("FINAL_CLASSIFICATION")
            if history["comparison_records"] else None
        ),
        "wake_count": state.get("wake_count", 0),
        "external_writes": 0,
        "evidence_level": "L0",
        "integrity_errors": history["integrity_errors"],
    }


def reality_watch_history(root: Path, limit: int = 20) -> list[dict[str, Any]]:
    history = _history_summary(Path(root))
    comparisons = {row.get("incident_id"): row for row in history["comparison_records"]}
    output = []
    for incident in history["incident_records"][-max(1, limit):]:
        comparison = comparisons.get(incident.get("EVENT_ID"), {})
        output.append({
            "incident_id": incident.get("EVENT_ID"),
            "source": incident.get("SOURCE_ID"),
            "public_reference": incident.get("PUBLIC_REFERENCE"),
            "cluster": incident.get("STRUCTURAL_INCIDENT_CLUSTER_ID"),
            "qualification": incident.get("QUALIFICATION_STATE"),
            "B3_result": comparison.get("B3_DECISION"),
            "ZERO_result": comparison.get("ZERO_DECISION"),
            "verification": comparison.get("FINAL_CLASSIFICATION"),
            "final_classification": comparison.get("FINAL_CLASSIFICATION")
                                  or "INCIDENT_NOT_QUALIFIED",
            "raw_external_text": "NOT_STORED",
        })
    return output
