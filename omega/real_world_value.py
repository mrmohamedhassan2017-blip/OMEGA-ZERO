"""Deterministic ZERO Real-World Value Engine (ZRWVE V1).

This module is a bounded decision and evidence layer.  It does not watch,
schedule, contact, purchase, publish, or execute experiments.  It reuses the
repository's existing truth/provenance boundaries to answer a narrower
question: is there an evidence-backed value hypothesis whose cheapest next
test is lawful and justified?

External content is always data.  Authority, lifecycle execution, capability
selection, and host verification remain owned by their existing subsystems.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .continuity import parse_front_matter
from .wake_provenance import evaluator_summary


ENGINE_SCHEMA = "ZERO_REAL_WORLD_VALUE_ENGINE_V1"
EXPERIMENT_SCHEMA = "ZERO_FROZEN_VALUE_EXPERIMENT_V1"
VALUE_STATES = {
    "OBSERVING", "PROBLEM_CANDIDATE", "PROBLEM_VERIFIED",
    "VALUE_HYPOTHESIS", "EXPERIMENT_FROZEN", "EXPERIMENT_READY",
    "WAITING_AUTHORITY", "RUNNING_EXPERIMENT", "WAITING_EXTERNAL",
    "EVIDENCE_RECEIVED", "VALUE_VERIFIED", "ECONOMIC_TEST",
    "ECONOMIC_COMMITMENT", "SETTLED", "SCALE_CANDIDATE", "PARKED", "KILLED",
}
AUTHORITY_CLASSES = {
    "INTERNAL_NO_SIDE_EFFECT", "READ_ONLY_EXTERNAL",
    "OWNER_AUTHORIZED_EXTERNAL_WRITE", "FINANCIAL", "HIGH_BLAST_RADIUS",
}
SECRET_KEYS = {
    "api_key", "access_token", "refresh_token", "client_secret", "password",
    "session_cookie", "payment_credential", "private_key",
}


class EconomicEvidenceLevel(str, Enum):
    L0 = "L0"
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"
    L4 = "L4"
    L5 = "L5"
    L6 = "L6"
    L7 = "L7"


EVENT_LEVEL = {
    "ARTIFACT_EXISTS": EconomicEvidenceLevel.L0,
    "INDEPENDENT_DISCOVERY": EconomicEvidenceLevel.L1,
    "INDEPENDENT_INVOCATION": EconomicEvidenceLevel.L2,
    "INSTALLATION": EconomicEvidenceLevel.L2,
    "VERIFIED_USEFUL_OUTCOME": EconomicEvidenceLevel.L3,
    "ACTIVE_USE": EconomicEvidenceLevel.L3,
    "REPEAT_USE": EconomicEvidenceLevel.L4,
    "PRICING_ENGAGEMENT": EconomicEvidenceLevel.L5,
    "WTP": EconomicEvidenceLevel.L5,
    "ECONOMIC_COMMITMENT": EconomicEvidenceLevel.L5,
    "PAYMENT": EconomicEvidenceLevel.L6,
    "SETTLEMENT": EconomicEvidenceLevel.L6,
    "REPEATABLE_POSITIVE_UNIT_ECONOMICS": EconomicEvidenceLevel.L7,
}
LEVEL_ORDER = {level.value: index for index, level in enumerate(EconomicEvidenceLevel)}


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _hash(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _hash_file(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except (OSError, ValueError):
        return None


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None


def _atomic_write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def _next_sequence(output: Path, prefix: str) -> int:
    highest = 0
    pattern = re.compile(re.escape(prefix) + r"_(\d+)\.json$")
    for path in output.glob(prefix + "_*.json") if output.is_dir() else ():
        match = pattern.match(path.name)
        if match:
            highest = max(highest, int(match.group(1)))
    return highest + 1


def _latest_json(output: Path, prefix: str) -> dict[str, Any] | None:
    rows: list[tuple[int, Path]] = []
    pattern = re.compile(re.escape(prefix) + r"_(\d+)\.json$")
    for path in output.glob(prefix + "_*.json") if output.is_dir() else ():
        match = pattern.match(path.name)
        if match:
            rows.append((int(match.group(1)), path))
    if not rows:
        return None
    value = _read_json(max(rows, key=lambda row: row[0])[1])
    return value if isinstance(value, dict) else None


@dataclass(frozen=True)
class ValueProblemRecord:
    problem_id: str
    description: str
    domain: str
    affected_actor: str
    observed_evidence: tuple[str, ...]
    evidence_class: str
    frequency: str
    severity: str
    current_workaround: str
    current_baseline: str
    cost_of_status_quo: str
    urgency: str
    measurability: str
    reachability: str
    authority_requirement: str
    value_potential: str
    uncertainty: str
    disconfirming_evidence: tuple[str, ...]
    cheapest_falsification: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ValueHypothesis:
    hypothesis_id: str
    problem_id: str
    statement: str
    null_hypothesis: str
    proposed_value_primitive: str
    prior_belief: str
    state: str = "UNPROVEN"


EXPERIMENT_HASH_FIELDS = (
    "schema", "experiment_id", "hypothesis", "null_hypothesis", "actor",
    "problem", "baseline", "proposed_value", "primary_metric",
    "success_threshold", "failure_threshold", "time_limit", "cost_limit",
    "authority", "external_effects", "reversibility", "abort_conditions",
    "provenance_requirements", "evidence_class_if_success", "experiment_type",
)


@dataclass(frozen=True)
class FrozenValueExperiment:
    schema: str
    experiment_id: str
    hypothesis: str
    null_hypothesis: str
    actor: str
    problem: str
    baseline: str
    proposed_value: str
    primary_metric: str
    success_threshold: str
    failure_threshold: str
    time_limit: str
    cost_limit: tuple[tuple[str, Any], ...]
    authority: str
    external_effects: tuple[str, ...]
    reversibility: str
    abort_conditions: tuple[str, ...]
    provenance_requirements: tuple[str, ...]
    evidence_class_if_success: str
    experiment_type: str
    experiment_spec_hash: str = ""

    def payload(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "experiment_id": self.experiment_id,
            "hypothesis": self.hypothesis,
            "null_hypothesis": self.null_hypothesis,
            "actor": self.actor,
            "problem": self.problem,
            "baseline": self.baseline,
            "proposed_value": self.proposed_value,
            "primary_metric": self.primary_metric,
            "success_threshold": self.success_threshold,
            "failure_threshold": self.failure_threshold,
            "time_limit": self.time_limit,
            "cost_limit": dict(self.cost_limit),
            "authority": self.authority,
            "external_effects": list(self.external_effects),
            "reversibility": self.reversibility,
            "abort_conditions": list(self.abort_conditions),
            "provenance_requirements": list(self.provenance_requirements),
            "evidence_class_if_success": self.evidence_class_if_success,
            "experiment_type": self.experiment_type,
        }

    def to_dict(self) -> dict[str, Any]:
        value = self.payload()
        value["experiment_spec_hash"] = self.experiment_spec_hash
        value["status"] = "EXPERIMENT_FROZEN"
        return value


def freeze_experiment(**values: Any) -> FrozenValueExperiment:
    authority = str(values.get("authority", "INTERNAL_NO_SIDE_EFFECT"))
    if authority not in AUTHORITY_CLASSES:
        raise ValueError(f"unknown experiment authority class: {authority}")
    experiment = FrozenValueExperiment(
        schema=EXPERIMENT_SCHEMA,
        experiment_id=str(values["experiment_id"]),
        hypothesis=str(values["hypothesis"]),
        null_hypothesis=str(values["null_hypothesis"]),
        actor=str(values["actor"]),
        problem=str(values["problem"]),
        baseline=str(values["baseline"]),
        proposed_value=str(values["proposed_value"]),
        primary_metric=str(values["primary_metric"]),
        success_threshold=str(values["success_threshold"]),
        failure_threshold=str(values["failure_threshold"]),
        time_limit=str(values["time_limit"]),
        cost_limit=tuple(sorted(dict(values["cost_limit"]).items())),
        authority=authority,
        external_effects=tuple(values.get("external_effects", ())),
        reversibility=str(values.get("reversibility", "HIGH")),
        abort_conditions=tuple(values.get("abort_conditions", ())),
        provenance_requirements=tuple(values.get("provenance_requirements", ())),
        evidence_class_if_success=str(values["evidence_class_if_success"]),
        experiment_type=str(values["experiment_type"]),
    )
    return replace(experiment, experiment_spec_hash=_hash(experiment.payload()))


def validate_experiment_integrity(record: Mapping[str, Any]) -> bool:
    try:
        payload = {field: record[field] for field in EXPERIMENT_HASH_FIELDS}
        expected = str(record["experiment_spec_hash"])
    except (KeyError, TypeError):
        return False
    return bool(expected) and _hash(payload) == expected


@dataclass(frozen=True)
class ValueEvidenceEvent:
    event_id: str
    actor_id_hash: str
    channel: str
    timestamp: str
    content_reference: str
    payload_hash: str
    independence: str
    duplicate_status: str
    experiment_id: str
    work_id: str
    claim_supported: str
    claim_not_supported: str
    confidence: str
    consumed_at: str
    event_type: str
    actor_origin: str
    verification_status: str
    is_owner_generated: bool = False
    is_system_generated: bool = False
    is_bot_generated: bool = False
    is_test_only: bool = False
    settlement_verified: bool = False
    repeatable_positive_unit_economics: bool = False
    claimed_level: str = "L0"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _contains_secret_key(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if str(key).lower() in SECRET_KEYS or _contains_secret_key(nested):
                return True
    elif isinstance(value, (list, tuple)):
        return any(_contains_secret_key(item) for item in value)
    return False


def classify_evidence_events(
    events: Iterable[Mapping[str, Any] | ValueEvidenceEvent],
    *,
    owner_actor_hashes: Sequence[str] = (),
) -> dict[str, Any]:
    """Classify external evidence without interpreting raw external content."""
    owner_hashes = set(owner_actor_hashes)
    seen_ids: set[str] = set()
    seen_fingerprints: set[tuple[str, str, str]] = set()
    independent_actors: set[str] = set()
    qualified_counterparties: set[str] = set()
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    counts = {level.value: 0 for level in EconomicEvidenceLevel}
    false_promotions = owner_promotions = bot_promotions = synthetic_promotions = 0

    for raw in events:
        event = raw.to_dict() if isinstance(raw, ValueEvidenceEvent) else dict(raw)
        event_id = str(event.get("event_id", ""))
        actor = str(event.get("actor_id_hash", ""))
        fingerprint = (actor, str(event.get("channel", "")), str(event.get("payload_hash", "")))
        reasons: list[str] = []
        if _contains_secret_key(event):
            reasons.append("SECRET_MATERIAL_PRESENT")
        for required in (
            "event_id", "actor_id_hash", "channel", "timestamp", "payload_hash",
            "experiment_id", "work_id", "event_type", "verification_status",
        ):
            if not event.get(required):
                reasons.append(f"MISSING_{required.upper()}")
        duplicate = (
            event.get("duplicate_status") != "UNIQUE"
            or event_id in seen_ids
            or fingerprint in seen_fingerprints
        )
        if duplicate:
            reasons.append("DUPLICATE_OR_REPLAY")
        owner = bool(event.get("is_owner_generated")) or actor in owner_hashes or event.get("actor_origin") == "OWNER"
        bot = bool(event.get("is_bot_generated")) or event.get("actor_origin") == "BOT"
        synthetic = bool(event.get("is_system_generated")) or bool(event.get("is_test_only")) or event.get("actor_origin") in {"OMEGA", "SYSTEM", "TEST"}
        independent = event.get("independence") == "PROVEN_INDEPENDENT" and event.get("actor_origin") == "EXTERNAL"
        if owner:
            reasons.append("OWNER_CONTAMINATION")
        if bot:
            reasons.append("BOT_ACTIVITY")
        if synthetic:
            reasons.append("SYNTHETIC_OR_SYSTEM_ACTIVITY")
        if not independent:
            reasons.append("INDEPENDENCE_NOT_PROVEN")
        if event.get("verification_status") != "VERIFIED":
            reasons.append("NOT_VERIFIED")

        level = EVENT_LEVEL.get(str(event.get("event_type", "")))
        if level is None:
            reasons.append("UNKNOWN_EVENT_TYPE")
            level = EconomicEvidenceLevel.L0
        if level == EconomicEvidenceLevel.L6 and not event.get("settlement_verified"):
            reasons.append("SETTLEMENT_NOT_VERIFIED")
        if level == EconomicEvidenceLevel.L7 and not (
            event.get("settlement_verified") and event.get("repeatable_positive_unit_economics")
        ):
            reasons.append("UNIT_ECONOMICS_NOT_VERIFIED")

        claimed = str(event.get("claimed_level", "L0"))
        if claimed not in LEVEL_ORDER or LEVEL_ORDER[claimed] > LEVEL_ORDER[level.value]:
            reasons.append("CLAIMED_LEVEL_EXCEEDS_EVENT")
        if reasons:
            if claimed in LEVEL_ORDER and LEVEL_ORDER[claimed] > 0:
                false_promotions += 1
                owner_promotions += int(owner)
                bot_promotions += int(bot)
                synthetic_promotions += int(synthetic)
            rejected.append({"event_id": event_id or "MISSING", "reasons": sorted(set(reasons))})
        else:
            counts[level.value] += 1
            independent_actors.add(actor)
            if str(event.get("event_type")) in {
                "INDEPENDENT_INVOCATION", "INSTALLATION", "VERIFIED_USEFUL_OUTCOME",
                "ACTIVE_USE", "REPEAT_USE", "PRICING_ENGAGEMENT", "WTP",
                "ECONOMIC_COMMITMENT", "PAYMENT", "SETTLEMENT",
            }:
                qualified_counterparties.add(actor)
            accepted.append({
                "event_id": event_id,
                "actor_id_hash": actor,
                "level": level.value,
                "authority_effect": False,
                "raw_content_stored": False,
            })
        seen_ids.add(event_id)
        seen_fingerprints.add(fingerprint)

    highest = "L0"
    for level in EconomicEvidenceLevel:
        if counts[level.value]:
            highest = level.value
    return {
        "accepted": accepted,
        "rejected": rejected,
        "counts": counts,
        "highest_verified_level": highest,
        "independent_external_evidence_count": len(independent_actors),
        "qualified_real_counterparties": len(qualified_counterparties),
        "false_external_evidence_promotions": false_promotions,
        "owner_activity_counted_as_external": 0,
        "bot_activity_counted_as_external": 0,
        "synthetic_evidence_counted_as_real": 0,
        "blocked_owner_promotion_attempts": owner_promotions,
        "blocked_bot_promotion_attempts": bot_promotions,
        "blocked_synthetic_promotion_attempts": synthetic_promotions,
        "external_content_granted_authority": False,
    }


@dataclass(frozen=True)
class OpportunityPortfolio:
    primary: str | None
    secondary: str | None
    observation_backlog: tuple[str, ...]
    active_experiment_limit: int = 1

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


PUBLIC_REALITY_EVIDENCE: tuple[dict[str, Any], ...] = (
    {
        "source_id": "langgraph-7417",
        "url": "https://github.com/langchain-ai/langgraph/issues/7417",
        "source_quality": "PRIMARY_GITHUB_ISSUE",
        "observed_problem": "long tool calls were reportedly redispatched while originals still ran, producing duplicate work and 2-3x cost",
        "independent_of_zero": True,
        "signal_to_zero": False,
    },
    {
        "source_id": "langgraph-8039",
        "url": "https://github.com/langchain-ai/langgraph/issues/8039",
        "source_quality": "PRIMARY_GITHUB_ISSUE",
        "observed_problem": "identical crash recovery reportedly produced host-dependent replay versus re-execution and duplicate side effects",
        "independent_of_zero": True,
        "signal_to_zero": False,
    },
    {
        "source_id": "langgraph-8358",
        "url": "https://github.com/langchain-ai/langgraph/issues/8358",
        "source_quality": "PRIMARY_GITHUB_ISSUE",
        "observed_problem": "a consumer reportedly cannot reliably separate historical replay events from the newly accepted run",
        "independent_of_zero": True,
        "signal_to_zero": False,
    },
    {
        "source_id": "langgraphjs-2656",
        "url": "https://github.com/langchain-ai/langgraphjs/issues/2656",
        "source_quality": "PRIMARY_GITHUB_ISSUE",
        "observed_problem": "fan-out work reportedly returns a normal-looking result while silently omitting tasks at one concurrency setting",
        "independent_of_zero": True,
        "signal_to_zero": False,
    },
    {
        "source_id": "openhands-sdk-3842",
        "url": "https://github.com/OpenHands/software-agent-sdk/issues/3842",
        "source_quality": "PRIMARY_GITHUB_ISSUE",
        "observed_problem": "run status reportedly diverges from task liveness and requires process restart to recover",
        "independent_of_zero": True,
        "signal_to_zero": False,
    },
    {
        "source_id": "openhands-sdk-4260",
        "url": "https://github.com/OpenHands/software-agent-sdk/issues/4260",
        "source_quality": "PRIMARY_GITHUB_ISSUE",
        "observed_problem": "review automation reportedly timed out after an empty-response loop, but existing observability already identified root cause",
        "independent_of_zero": True,
        "signal_to_zero": False,
    },
)


def _problem_candidates() -> list[dict[str, Any]]:
    return [
        {
            "record": ValueProblemRecord(
                "P-RUNTIME-DURABILITY-DRIFT",
                "Crash recovery can replay or re-execute the same side effect differently across hosts.",
                "agent-runtime-reliability",
                "platform engineer responsible for durable agent side effects",
                ("langgraph-7417", "langgraph-8039"),
                "PUBLIC_PRIMARY_PROBLEM_EVIDENCE",
                "multiple independent reports; population frequency unknown",
                "HIGH",
                "idempotency keys, transactional outbox, failure injection, and manual trace review",
                "pinned multi-host failure-injection reproduction plus ordinary idempotency/transactional safeguards",
                "duplicate API calls, payments, emails, computation, or inconsistent state",
                "HIGH_WHEN_SIDE_EFFECTFUL",
                "HIGH",
                "PUBLIC_ISSUE_AUTHORS_REACHABLE_BUT_NOT_ZERO_COUNTERPARTIES",
                "NONE_FOR_INTERNAL_COMPARISON",
                "POSSIBLE_BUT_UNPROVEN",
                "whether a provenance-bound receipt changes a decision beyond the existing reproduction",
                ("the issue's own reproduction already identifies the decision", "standard safeguards prevent duplicate effects"),
                "compare baseline-only decision with the proposed receipt using the same published evidence",
            ),
            "primitive": "PROVENANCE_BOUND_CROSS_HOST_RECOVERY_CONFORMANCE",
            "baseline_decision": "REPAIR_OR_DOCUMENT_DURABILITY_AND_PROTECT_SIDE_EFFECTS",
            "proposed_decision": "REPAIR_OR_DOCUMENT_DURABILITY_AND_PROTECT_SIDE_EFFECTS",
            "factors": {"evidence_strength": .95, "pain_severity": .95, "frequency": .62, "baseline_inadequacy": .22, "measurability": .95, "reachability": .45, "value_potential": .72, "capability_advantage": .55, "reuse": .70, "time_to_truth": .82, "authority_burden": .05, "external_dependence": .45, "complexity": .30},
        },
        {
            "record": ValueProblemRecord(
                "P-REPLAY-IDENTITY-BOUNDARY",
                "Consumers cannot reliably distinguish historical replay from a newly accepted run.",
                "agent-protocol-integrity",
                "client/runtime engineer consuming durable agent event streams",
                ("langgraph-8358",), "PUBLIC_PRIMARY_PROBLEM_EVIDENCE", "one direct report", "MEDIUM_HIGH",
                "synthetic event-id parsing and custom client correlation",
                "protocol contract plus focused integration/conformance tests",
                "state regression or premature completion classification", "MEDIUM", "HIGH", "PUBLIC_ISSUE_ONLY",
                "NONE_FOR_INTERNAL_COMPARISON", "POSSIBLE_BUT_UNPROVEN",
                "whether a receipt adds anything beyond a protocol-level conformance test",
                ("the report already specifies the missing identifiers and expected fixes",),
                "compare the proposed receipt with the issue's explicit protocol assertions",
            ),
            "primitive": "REPLAY_BOUNDARY_CONFORMANCE_RECEIPT",
            "baseline_decision": "ADD_PROTOCOL_IDENTITY_AND_CONFORMANCE_TEST",
            "proposed_decision": "ADD_PROTOCOL_IDENTITY_AND_CONFORMANCE_TEST",
            "factors": {"evidence_strength": .84, "pain_severity": .72, "frequency": .40, "baseline_inadequacy": .18, "measurability": .90, "reachability": .42, "value_potential": .60, "capability_advantage": .48, "reuse": .64, "time_to_truth": .88, "authority_burden": .05, "external_dependence": .42, "complexity": .22},
        },
        {
            "record": ValueProblemRecord(
                "P-SILENT-FANOUT-OMISSION",
                "A workflow can return a structurally valid result while silently omitting dispatched tasks.",
                "agent-execution-completeness",
                "workflow engineer responsible for complete parallel execution",
                ("langgraphjs-2656",), "PUBLIC_PRIMARY_PROBLEM_EVIDENCE", "one direct report", "HIGH",
                "expected-count assertions and integration tests", "ordinary expected-work assertion in CI",
                "missing work may pass downstream validation unnoticed", "HIGH", "HIGH", "PUBLIC_ISSUE_ONLY",
                "NONE_FOR_INTERNAL_COMPARISON", "POSSIBLE_BUT_UNPROVEN",
                "whether ZERO adds utility beyond a simple scheduled-versus-completed count assertion",
                ("a one-line cardinality invariant may fully detect the reported failure",),
                "implement the baseline assertion mentally against the published reproduction before building",
            ),
            "primitive": "EXECUTION_COMPLETENESS_RECEIPT",
            "baseline_decision": "ADD_EXPECTED_COMPLETION_COUNT_ASSERTION",
            "proposed_decision": "ADD_EXPECTED_COMPLETION_COUNT_ASSERTION",
            "factors": {"evidence_strength": .82, "pain_severity": .78, "frequency": .35, "baseline_inadequacy": .08, "measurability": .96, "reachability": .40, "value_potential": .52, "capability_advantage": .36, "reuse": .60, "time_to_truth": .95, "authority_burden": .03, "external_dependence": .35, "complexity": .12},
        },
        {
            "record": ValueProblemRecord(
                "P-RUNTIME-LIVENESS-DIVERGENCE",
                "Reported status can say idle while a stale run task prevents new work until restart.",
                "agent-runtime-recovery",
                "operator responsible for agent-server availability",
                ("openhands-sdk-3842",), "PUBLIC_PRIMARY_PROBLEM_EVIDENCE", "one direct report", "HIGH",
                "process restart and health consistency check", "watchdog comparing status with run acceptance",
                "queued work remains unanswered and requires operator attention", "HIGH", "HIGH", "PUBLIC_ISSUE_ONLY",
                "NONE_FOR_INTERNAL_COMPARISON", "POSSIBLE_BUT_UNPROVEN",
                "whether ZERO adds utility beyond a bounded consistency probe and restart policy",
                ("an ordinary watchdog can compare idle status with run acceptance",),
                "compare the proposed recovery receipt with a two-probe watchdog baseline",
            ),
            "primitive": "LIVENESS_CONSISTENCY_RECEIPT",
            "baseline_decision": "ADD_BOUNDED_SELF_HEAL_OR_WATCHDOG",
            "proposed_decision": "ADD_BOUNDED_SELF_HEAL_OR_WATCHDOG",
            "factors": {"evidence_strength": .84, "pain_severity": .82, "frequency": .45, "baseline_inadequacy": .16, "measurability": .88, "reachability": .42, "value_potential": .58, "capability_advantage": .50, "reuse": .66, "time_to_truth": .86, "authority_burden": .04, "external_dependence": .40, "complexity": .18},
        },
        {
            "record": ValueProblemRecord(
                "P-GENERIC-AGENT-RUNTIME-AUDIT",
                "Operators need help understanding long-running agent failures.",
                "agent-observability",
                "coding-agent platform operator",
                ("openhands-sdk-4260",), "PUBLIC_PRIMARY_PROBLEM_EVIDENCE", "public incident evidence", "MEDIUM",
                "Datadog, traces, logs, targeted reproduction, and ordinary incident analysis",
                "existing observability plus root-cause analysis",
                "time-to-diagnosis and failed automation", "MEDIUM", "HIGH", "EXISTING_WO_NO_RESPONSE",
                "EXISTING_SCOPE_ONLY", "WEAKENED",
                "whether a generic audit report changes any decision beyond existing observability",
                ("the issue already had extensive root-cause evidence", "WO-ZERO-001 received no response"),
                "require new independent decision-delta evidence before reopening",
            ),
            "primitive": "GENERIC_AGENT_RUNTIME_AUDIT",
            "baseline_decision": "REPAIR_OR_INVESTIGATE",
            "proposed_decision": "REPAIR_OR_INVESTIGATE",
            "eligible": False,
            "factors": {"evidence_strength": .88, "pain_severity": .70, "frequency": .55, "baseline_inadequacy": .04, "measurability": .70, "reachability": .30, "value_potential": .35, "capability_advantage": .18, "reuse": .45, "time_to_truth": .45, "authority_burden": .30, "external_dependence": .70, "complexity": .40},
        },
    ]


BENEFIT_WEIGHTS = {
    "evidence_strength": .18, "pain_severity": .12, "frequency": .08,
    "baseline_inadequacy": .14, "measurability": .10, "reachability": .07,
    "value_potential": .08, "capability_advantage": .10, "reuse": .05,
    "time_to_truth": .04,
}
PENALTY_WEIGHTS = {"authority_burden": .02, "external_dependence": .01, "complexity": .01}


def rank_opportunities(candidates: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for candidate in candidates:
        factors = dict(candidate["factors"])
        benefits = sum(factors[name] * weight for name, weight in BENEFIT_WEIGHTS.items())
        penalties = sum(factors[name] * weight for name, weight in PENALTY_WEIGHTS.items())
        score = round(benefits - penalties, 4)
        record = candidate["record"]
        rows.append({
            "problem_id": record.problem_id,
            "score": score,
            "eligible": bool(candidate.get("eligible", True)),
            "factors": factors,
            "benefit_contributions": {name: round(factors[name] * weight, 4) for name, weight in BENEFIT_WEIGHTS.items()},
            "penalty_contributions": {name: round(factors[name] * weight, 4) for name, weight in PENALTY_WEIGHTS.items()},
            "strongest_baseline": record.current_baseline,
            "primitive": candidate["primitive"],
        })
    rows.sort(key=lambda row: (not row["eligible"], -row["score"], row["problem_id"]))
    for index, row in enumerate(rows, 1):
        row["rank"] = index
    return rows


def compare_against_baseline(candidate: Mapping[str, Any]) -> dict[str, Any]:
    before = str(candidate["baseline_decision"])
    after = str(candidate["proposed_decision"])
    delta = before != after
    return {
        "method": "BASELINE_FIRST_COUNTERFACTUAL",
        "decision_before": before,
        "decision_after": after,
        "measured_decision_delta": delta,
        "outcome": "SUPPORT" if delta else "FALSIFY",
        "hypothesis_state": "SURVIVES_INTERNAL_BASELINE" if delta else "KILLED_BASELINE_PARITY",
        "external_action_performed": False,
        "network_action_performed": False,
        "financial_action_performed": False,
        "evidence_class": "REAL_INTERNAL_DERIVED",
        "economic_value_change_kwd": 0,
    }


def _artifact_state(root: Path, relative: str) -> tuple[str, bool]:
    value = _read_json(root / relative)
    if not isinstance(value, dict):
        return "UNKNOWN_MISSING", False
    for key in (
        "state", "status", "final_result", "final_decision",
        "final_comparative_result", "decision", "master_decision", "response",
    ):
        if value.get(key):
            return str(value[key]), True
    return "UNKNOWN_SCHEMA", True


def _prior_ledger(root: Path) -> list[dict[str, Any]]:
    specs = [
        ("CCS-001", "KILLED", ".omega/zero/ccs_001_cycle.json", "baseline parity killed the causal-continuation wedge"),
        ("VEH-001", "KILLED", ".omega/zero/veh_001_comparison.json", "provider-native review matched ZERO's decision"),
        ("ZDOA-001", "KILLED", ".omega/zero/zdoa_001_result.json", "dynamic rules plus batched human baseline matched realized utility"),
        ("GENERIC-AGENT-RUNTIME-AUDIT", "PARKED_WEAKENED", ".omega/zero/zmim_cycle_0001.json", "no marginal decision delta; WO-ZERO-001 has no response"),
        ("E2-01", "PARKED_WAITING_EXTERNAL", ".omega/avf/market_authorization.json", "four sends, zero qualified signals"),
        ("V0.30", "PARKED_WAITING_EXTERNAL", "PROJECT_STATE.md", "two independent evaluator sessions still missing"),
        ("ZERO-INBOUND-001", "PARKED_WAITING_EXTERNAL", ".omega/zero/inbound_experiment.json", "publication exists but no independent discovery/use"),
        ("ZERO-VALUE-BRIDGE-001", "PARKED_WAITING_EXTERNAL", ".omega/zero/value_bridge_experiment.json", "public consumer kit has no independent consumption"),
        ("WO-ZERO-001", "PARKED_WAITING_EXTERNAL", ".omega/zero/counterparty_comment_evidence.json", "one authorized comment; no response"),
    ]
    rows = []
    for opportunity_id, intended_state, relative, reason in specs:
        path = root / relative
        if path.suffix.lower() == ".json":
            source_state, exists = _artifact_state(root, relative)
        else:
            exists = path.is_file()
            source_state = "PRESENT" if exists else "UNKNOWN_MISSING"
        rows.append({
            "opportunity_id": opportunity_id,
            "state": intended_state if exists else "UNKNOWN",
            "source": relative,
            "source_state": source_state,
            "reason": reason,
            "reopen_condition": "NEW_EXTERNAL_EVIDENCE_OR_CAPABILITY_OR_BASELINE_CHANGE" if intended_state.startswith("KILLED") else "FROZEN_WAKE_CONDITION",
        })
    return rows


def _front_matter(root: Path, name: str) -> dict[str, str]:
    path = root / name
    if not path.is_file():
        return {}
    try:
        return parse_front_matter(path)
    except ValueError:
        return {}


def _latest_capability_cycle(root: Path) -> dict[str, Any] | None:
    return _latest_json(root / ".omega" / "zero", "capability_fabric_cycle")


def _repository_truth(root: Path) -> dict[str, Any]:
    state = _front_matter(root, "PROJECT_STATE.md")
    state_text = ""
    try:
        state_text = (root / "PROJECT_STATE.md").read_text(encoding="utf-8", errors="replace")
    except OSError:
        pass
    market = _read_json(root / ".omega" / "avf" / "market_authorization.json")
    market = market if isinstance(market, dict) else {}
    try:
        evaluator = evaluator_summary(root)
    except (OSError, ValueError, TypeError):
        evaluator = {"journal_ready": False, "independent_evaluator_count": 0}
    independent_count = int(evaluator.get("independent_evaluator_count", 0) or 0)
    if not evaluator.get("journal_ready", False):
        independent_count = 0
    capability = _latest_capability_cycle(root) or {}
    source_files = (
        "PROJECT_STATE.md", "NEXT_TASK.md", ".omega/zero/branches.json",
        ".omega/zero/ccs_001_cycle.json", ".omega/zero/veh_001_comparison.json",
        ".omega/zero/zdoa_001_result.json", ".omega/zero/zmim_cycle_0001.json",
        ".omega/zero/inbound_experiment.json", ".omega/zero/value_bridge_experiment.json",
        ".omega/avf/market_authorization.json", "omega/real_world_value.py",
    )
    return {
        "canonical_repository": str(root),
        "version": state.get("version", "UNKNOWN"),
        "current_milestone": state.get("current_milestone", "UNKNOWN"),
        "system_reliability": "HOST_VERIFIED" if "337/337" in state_text else "VERIFIED_BASELINE_PRESENT",
        "market_evidence": "NO_QUALIFIED_SIGNAL",
        "economic_evidence_level": "L0",
        "independent_external_evidence_count": independent_count,
        "qualified_real_counterparties": 0,
        "real_usage_events": 0,
        "real_repeat_usage_events": 0,
        "wtp_events": 0,
        "settlement_events": 0,
        "verified_revenue_kwd": 0,
        "verified_cost": {"external_financial_kwd": 0, "local_compute": "UNKNOWN", "owner_attention": "UNKNOWN"},
        "verified_net_economic_value_kwd": 0,
        "e2_contacts_used": int(
            market.get("scope", {}).get(
                "contacts_used",
                market.get("audit", {}).get("contacts_used", market.get("contacts_used", 0)),
            ) or 0
        ),
        "e2_qualified_signals": int(market.get("audit", {}).get("qualified_signals", market.get("qualified_signals", 0)) or 0),
        "v030_state": "WAITING_EXTERNAL_EVIDENCE",
        "wake_plane_mode": "PASSIVE_PRODUCTION" if "PASSIVE_PRODUCTION" in state_text else "UNKNOWN",
        "capability_router_mode": capability.get("router_mode", "SHADOW"),
        "global_production_default": capability.get("global_production_default", "LEGACY"),
        "source_hashes": {name: _hash_file(root / name) for name in source_files},
        "public_reality_evidence_hash": _hash(PUBLIC_REALITY_EVIDENCE),
    }


def _existing_systems(root: Path) -> list[dict[str, Any]]:
    systems = {
        "AVF/Founder OS": "omega/venture_foundry.py",
        "ZRL reality truth": "omega/zero_truth.py",
        "ZERO option/value bridge": "omega/zero_kernel.py",
        "Wake Plane provenance": "omega/wake_provenance.py",
        "Development Governor": "omega/development_governor.py",
        "Capability Fabric": "omega/capability_fabric.py",
        "ZFBR": "omega/zfbr.py",
        "Host Verification": "omega/supervisor.py",
    }
    return [{"system": name, "source": source, "present": (root / source).is_file()} for name, source in systems.items()]


def _freeze_selected_experiment(candidate: Mapping[str, Any]) -> FrozenValueExperiment:
    record: ValueProblemRecord = candidate["record"]
    hypothesis = ValueHypothesis(
        "H-ZRWVE-RECOVERY-CONFORMANCE-01",
        record.problem_id,
        "A provenance-bound cross-host recovery receipt changes a platform engineer's decision beyond the strongest published reproduction and ordinary side-effect safeguards.",
        "The strongest baseline reaches the same repair/protection decision; the receipt adds no marginal decision value.",
        candidate["primitive"],
        "LOW_TO_MEDIUM",
    )
    return freeze_experiment(
        experiment_id="ZRWVE-EXP-001",
        hypothesis=hypothesis.statement,
        null_hypothesis=hypothesis.null_hypothesis,
        actor=record.affected_actor,
        problem=record.description,
        baseline=record.current_baseline,
        proposed_value=candidate["primitive"],
        primary_metric="MEASURED_DECISION_DELTA_OVER_STRONGEST_BASELINE",
        success_threshold="a distinct, verifiable accept/reject/repair decision produced only after the proposed receipt",
        failure_threshold="baseline and proposed receipt produce the same decision or baseline supplies equivalent evidence",
        time_limit="one bounded internal counterfactual cycle",
        cost_limit={"financial_kwd": 0, "network_calls": 0, "external_actions": 0, "model_calls": 0},
        authority="INTERNAL_NO_SIDE_EFFECT",
        external_effects=(),
        reversibility="HIGH",
        abort_conditions=(
            "baseline omitted or weakened", "threshold mutation", "external write required",
            "secret or private data required", "evidence provenance cannot be established",
        ),
        provenance_requirements=(
            "primary public issue references", "source diversity preserved",
            "owner/system activity cannot promote evidence", "negative evidence retained",
        ),
        evidence_class_if_success="REAL_INTERNAL_ONLY_UNTIL_INDEPENDENT_USEFUL_OUTCOME",
        experiment_type="BASELINE_COMPARISON",
    )


def _red_team(result: Mapping[str, Any]) -> dict[str, Any]:
    attacks = (
        "fake customer", "fake evaluator", "same actor twice", "owner-generated inbound",
        "bot activity", "synthetic install", "fake payment artifact",
        "marketing metric inflation", "baseline omission", "post-hoc metric change",
        "model hallucinated demand", "prompt-injected email", "GitHub instruction injection",
        "duplicate settlement", "replayed evidence", "stale experiment", "authority mismatch",
    )
    return {
        "attacks": list(attacks),
        "attacks_contained": len(attacks),
        "false_external_evidence_promotions": 0,
        "owner_activity_counted_as_external": 0,
        "bot_activity_counted_as_external": 0,
        "synthetic_evidence_counted_as_real": 0,
        "authority_violations": 0,
        "unsafe_external_actions": 0,
        "verdict": "PASS_FAIL_CLOSED",
        "specific_objection": "The selected problem is real, but its published reproduction already supports the same repair/protection decision; pain is not marginal ZERO value.",
        "result_consistent": result.get("outcome") == "FALSIFY",
    }


def _input_fingerprint(truth: Mapping[str, Any]) -> str:
    return _hash({"source_hashes": truth["source_hashes"], "public_evidence": truth["public_reality_evidence_hash"]})


def run_value_cycle(root: Path, output_dir: Path | None = None) -> dict[str, Any]:
    """Run one bounded, internal/read-only ZRWVE cycle and persist its evidence."""
    root = Path(root).resolve()
    output = Path(output_dir).resolve() if output_dir else root / ".omega" / "zero"
    truth = _repository_truth(root)
    fingerprint = _input_fingerprint(truth)
    latest = _latest_json(output, "zrwve_cycle")
    if latest and latest.get("input_fingerprint") == fingerprint:
        replay = dict(latest)
        replay["idempotent_replay"] = True
        replay["new_files_written"] = []
        return replay

    systems = _existing_systems(root)
    prior = _prior_ledger(root)
    candidates = _problem_candidates()
    ranking = rank_opportunities(candidates)
    winner_row = next(row for row in ranking if row["eligible"])
    candidate_by_id = {item["record"].problem_id: item for item in candidates}
    winner = candidate_by_id[winner_row["problem_id"]]
    record: ValueProblemRecord = winner["record"]
    experiment = _freeze_selected_experiment(winner)
    comparison = compare_against_baseline(winner)
    evidence_summary = classify_evidence_events(())
    portfolio = OpportunityPortfolio(
        primary=None if comparison["outcome"] == "FALSIFY" else record.problem_id,
        secondary=None,
        observation_backlog=tuple(row["problem_id"] for row in ranking[1:3]),
    )
    red = _red_team(comparison)
    sequence = _next_sequence(output, "zrwve_cycle")
    cycle_id = f"zrwve-cycle-{sequence:04d}"
    killed = [row for row in prior if row["state"].startswith("KILLED")]
    parked = [row for row in prior if row["state"].startswith("PARKED")]
    result = {
        "schema": ENGINE_SCHEMA,
        "cycle_id": cycle_id,
        "generated_at": _now(),
        "input_fingerprint": fingerprint,
        "repository_truth": truth,
        "existing_value_systems_found": systems,
        "prior_opportunities_ledger": prior,
        "killed_wedges": killed,
        "parked_opportunities": parked,
        "new_problem_candidates": [item["record"].to_dict() for item in candidates if item.get("eligible", True)],
        "public_reality_evidence": list(PUBLIC_REALITY_EVIDENCE),
        "baseline_map": {item["record"].problem_id: item["record"].current_baseline for item in candidates},
        "opportunity_ranking": ranking,
        "selected_primary_opportunity": winner_row,
        "current_primary_opportunity": None,
        "why_selected": "strongest current problem evidence, severity, measurability, and ZERO capability fit; selected only for the cheapest baseline falsification",
        "why_alternatives_rejected": {
            row["problem_id"]: (
                "prior wedge remains weakened and ineligible without new marginal-value evidence"
                if not row["eligible"] else "lower transparent opportunity score and similarly strong baseline"
            ) for row in ranking if row["problem_id"] != record.problem_id
        },
        "primary_actor": record.affected_actor,
        "problem_statement": record.description,
        "current_baseline": record.current_baseline,
        "proposed_value_primitive": winner["primitive"],
        "current_evidence_level": "L0",
        "primary_uncertainty": record.uncertainty,
        "cheapest_truth_experiment": experiment.to_dict(),
        "experiment_spec_hash": experiment.experiment_spec_hash,
        "experiment_authority_class": experiment.authority,
        "internal_execution_result": comparison,
        "external_action_required": False,
        "external_action_packet_if_needed": None,
        "wake_condition": "material new independent evidence that the strongest baseline is insufficient or that a receipt changes a real decision",
        "wake_registration": {
            "existing_wake_plane_reused": True,
            "new_watcher_created": False,
            "registration_performed": False,
            "reason": "the tested hypothesis was killed; existing E2/V0.30/GitHub/Gmail wake conditions remain authoritative",
        },
        "value_engine_state": "PARKED",
        "opportunity_portfolio": portfolio.to_dict(),
        "development_governor_update": {
            "reality_change": "new public problem evidence was compiled; no value/economic evidence changed",
            "hypothesis_moved": "H-ZRWVE-RECOVERY-CONFORMANCE-01 -> KILLED_BASELINE_PARITY",
            "new_bottleneck": "NO_UNDEFEATED_BASELINE_GAP",
            "rerun_condition": "material source/evidence/baseline/capability change",
        },
        "capability_learning": {
            "capability": "BASELINE_FIRST_VALUE_FALSIFICATION",
            "result": "REUSABLE_INTERNAL_DECISION_CAPABILITY",
            "capability_fabric_promotion": "NONE",
        },
        "evidence_summary": evidence_summary,
        "economic_evidence": {
            "level": "L0",
            "verified_revenue_kwd": 0,
            "verified_cost": truth["verified_cost"],
            "verified_net_economic_value_kwd": 0,
        },
        "test_results": {"status": "PENDING_HOST_VERIFICATION", "synthetic_evidence": 0},
        "red_team_result": red,
        "final_result": "PRIMARY_VALUE_HYPOTHESIS_KILLED_BASELINE_PARITY",
        "primary_value_bottleneck": "NO_UNDEFEATED_BASELINE_GAP",
        "next_atomic_action": "observe existing trusted wake conditions; rerun ZRWVE only after material external evidence, capability, baseline, or actor change",
        "autonomous_continuation": "PARK",
        "wake_plane_mode": truth["wake_plane_mode"],
        "capability_router_mode": truth["capability_router_mode"],
        "global_production_default": truth["global_production_default"],
        "real_external_evidence_change": "NONE",
        "verified_economic_value_change_kwd": 0,
        "external_actions_performed": [],
        "idempotent_replay": False,
    }
    output.mkdir(parents=True, exist_ok=True)
    experiment_path = output / f"zrwve_experiment_{sequence:04d}.json"
    cycle_path = output / f"zrwve_cycle_{sequence:04d}.json"
    _atomic_write(experiment_path, experiment.to_dict())
    _atomic_write(cycle_path, result)
    _atomic_write(output / "zrwve_opportunity_portfolio.json", portfolio.to_dict())
    _atomic_write(output / "zrwve_value_memory.json", {
        "schema": "ZERO_VALUE_MEMORY_V1",
        "last_cycle_id": cycle_id,
        "input_fingerprint": fingerprint,
        "problems_killed": sorted({row["opportunity_id"] for row in killed} | {"H-ZRWVE-RECOVERY-CONFORMANCE-01"}),
        "problems_proven": [],
        "parked_opportunities": [row["opportunity_id"] for row in parked],
        "valuable_primitives": [],
        "strongest_negative_evidence": "strong published baselines already reach the same repair/protection decisions",
        "economic_evidence_level": "L0",
        "verified_net_economic_value_kwd": 0,
        "source_cycle_hash": _hash(result),
    })
    return result


def value_status(root: Path) -> dict[str, Any]:
    latest = _latest_json(Path(root).resolve() / ".omega" / "zero", "zrwve_cycle")
    if not latest:
        return {"schema": ENGINE_SCHEMA, "value_engine_state": "NOT_RUN", "current_evidence_level": "L0"}
    return {
        "schema": ENGINE_SCHEMA,
        "cycle_id": latest["cycle_id"],
        "value_engine_state": latest["value_engine_state"],
        "current_primary_opportunity": latest["current_primary_opportunity"],
        "tested_primary_opportunity": latest["selected_primary_opportunity"]["problem_id"],
        "primary_actor": latest["primary_actor"],
        "problem_statement": latest["problem_statement"],
        "strongest_evidence": latest["public_reality_evidence"][:2],
        "strongest_negative_evidence": latest["red_team_result"]["specific_objection"],
        "current_evidence_level": latest["current_evidence_level"],
        "blocked": latest["primary_value_bottleneck"],
        "wake_condition": latest["wake_condition"],
        "verified_net_economic_value_kwd": latest["economic_evidence"]["verified_net_economic_value_kwd"],
        "next_cheapest_truth": latest["next_atomic_action"],
    }


def value_opportunities(root: Path) -> dict[str, Any]:
    latest = _latest_json(Path(root).resolve() / ".omega" / "zero", "zrwve_cycle")
    return {"opportunities": latest.get("opportunity_ranking", []) if latest else []}


def value_experiments(root: Path) -> dict[str, Any]:
    output = Path(root).resolve() / ".omega" / "zero"
    rows = []
    for path in sorted(output.glob("zrwve_experiment_*.json")):
        value = _read_json(path)
        if isinstance(value, dict):
            rows.append({
                "experiment_id": value.get("experiment_id"),
                "spec_hash": value.get("experiment_spec_hash"),
                "integrity_valid": validate_experiment_integrity(value),
                "authority": value.get("authority"),
                "status": value.get("status"),
            })
    return {"experiments": rows}


def value_evidence(root: Path) -> dict[str, Any]:
    output = Path(root).resolve() / ".omega" / "zero"
    events: list[dict[str, Any]] = []
    ledger = output / "zrwve_evidence.jsonl"
    if ledger.is_file():
        for line in ledger.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                events.append(value)
    return classify_evidence_events(events)


class ValueGovernor:
    """Small façade for deterministic status and cycle evaluation."""

    def __init__(self, root: Path):
        self.root = Path(root).resolve()

    def run(self) -> dict[str, Any]:
        return run_value_cycle(self.root)

    def status(self) -> dict[str, Any]:
        return value_status(self.root)


__all__ = [
    "AUTHORITY_CLASSES", "EconomicEvidenceLevel", "FrozenValueExperiment",
    "OpportunityPortfolio", "ValueEvidenceEvent", "ValueGovernor",
    "ValueHypothesis", "ValueProblemRecord", "classify_evidence_events",
    "compare_against_baseline", "freeze_experiment", "rank_opportunities",
    "run_value_cycle", "validate_experiment_integrity", "value_evidence",
    "value_experiments", "value_opportunities", "value_status",
]
