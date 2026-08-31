from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .capability_fabric import discover_capabilities, profile_task, route_task
from .experiment_override import evaluate_experiment_authority


MISSION_STATES = (
    "DRAFT", "PROPOSED", "UNDER_ZERO_REVIEW", "CONDITIONAL", "APPROVED", "READY",
    "RUNNING", "PAUSED", "BLOCKED", "AWAITING_EVIDENCE", "UNDER_VERIFICATION",
    "VERIFIED", "FAILED", "REJECTED", "CANCELLED",
)
VERDICT_TYPES = ("VERIFIED", "UNVERIFIED", "CONTRADICTED", "CONDITIONAL", "REJECTED",
                 "BLOCKED", "UNKNOWN", "AUTHORIZED", "UNAUTHORIZED")
CLAIM_STATES = ("UNVERIFIED", "SUPPORTED", "CONTRADICTED", "UNKNOWN", "SUPERSEDED")
VALID_TRANSITIONS = {
    "DRAFT": {"PROPOSED", "CANCELLED"},
    "PROPOSED": {"UNDER_ZERO_REVIEW", "CANCELLED"},
    "UNDER_ZERO_REVIEW": {"APPROVED", "CONDITIONAL", "REJECTED", "CANCELLED"},
    "CONDITIONAL": {"APPROVED", "REJECTED", "CANCELLED"},
    "APPROVED": {"READY", "CANCELLED"},
    "READY": {"RUNNING", "PAUSED", "CANCELLED"},
    "RUNNING": {"PAUSED", "BLOCKED", "AWAITING_EVIDENCE", "UNDER_VERIFICATION", "FAILED", "CANCELLED"},
    "PAUSED": {"READY", "CANCELLED"},
    "BLOCKED": {"READY", "FAILED", "CANCELLED"},
    "AWAITING_EVIDENCE": {"UNDER_VERIFICATION", "BLOCKED", "CANCELLED"},
    "UNDER_VERIFICATION": {"VERIFIED", "FAILED", "CONDITIONAL"},
    "VERIFIED": set(),
    "FAILED": set(),
    "REJECTED": set(),
    "CANCELLED": set(),
}


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _hash(value: Any) -> str:
    data = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def _base(root: Path) -> Path:
    return Path(root).resolve() / ".omega" / "missions"


def _atomic_write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".{os.getpid()}.{uuid.uuid4().hex}.tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


@dataclass
class CommandRecord:
    command_id: str
    timestamp: str
    operator_input: str
    normalized_intent: str
    target_role: str
    mission_id_if_any: str | None
    requested_action: str
    authorization_requirement: str
    execution_requested: bool
    context_refs: list[str]
    status: str = "ROUTED"


@dataclass
class Claim:
    claim_id: str
    mission_id: str
    speaker: str
    statement: str
    created_at: str
    claim_type: str
    evidence_refs: list[str] = field(default_factory=list)
    verification_state: str = "UNVERIFIED"
    contradictions: list[str] = field(default_factory=list)
    supersedes: str | None = None
    status: str = "UNVERIFIED"


@dataclass
class ZeroVerdict:
    verdict_id: str
    mission_id: str
    claim_id_if_any: str | None
    verdict_type: str
    issued_at: str
    subject: str
    reason: str
    evidence_refs: list[str] = field(default_factory=list)
    missing_evidence: list[str] = field(default_factory=list)
    contradictions: list[str] = field(default_factory=list)
    conditions: list[str] = field(default_factory=list)
    risk_notes: list[str] = field(default_factory=list)
    authorization_notes: list[str] = field(default_factory=list)
    recommended_next_action: str = "UNKNOWN"


@dataclass
class Mission:
    mission_id: str
    title: str
    objective: str
    origin: str
    created_at: str
    updated_at: str
    status: str = "DRAFT"
    priority: str = "NORMAL"
    parent_mission: str | None = None
    child_missions: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    required_capabilities: list[str] = field(default_factory=list)
    authorization_scope: str = "UNKNOWN_UNTIL_ZERO_REVIEW"
    resource_budget: dict[str, Any] = field(default_factory=dict)
    risk_class: str = "UNKNOWN"
    success_criteria: list[str] = field(default_factory=list)
    failure_criteria: list[str] = field(default_factory=list)
    evidence_requirements: list[str] = field(default_factory=list)
    current_plan: list[str] = field(default_factory=list)
    current_step: str = "DRAFT"
    blocked_reason: str | None = None
    claims: list[Claim] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    zero_verdict: ZeroVerdict | None = None
    continuity_state: dict[str, Any] = field(default_factory=dict)


def _mission_path(root: Path, mission_id: str) -> Path:
    return _base(root) / "missions" / f"{mission_id}.json"


def _commands_path(root: Path) -> Path:
    return _base(root) / "commands.jsonl"


def _events_path(root: Path) -> Path:
    return _base(root) / "events.jsonl"


def _event(root: Path, kind: str, **data: Any) -> dict[str, Any]:
    record = {"timestamp": _now(), "event": kind, **data}
    path = _events_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    return record


def _record_command(root: Path, record: CommandRecord) -> None:
    path = _commands_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(asdict(record), ensure_ascii=False, sort_keys=True) + "\n")


def _mission_from_dict(value: dict[str, Any]) -> Mission:
    claims = [Claim(**item) for item in value.get("claims", [])]
    verdict = value.get("zero_verdict")
    value = dict(value)
    value["claims"] = claims
    value["zero_verdict"] = ZeroVerdict(**verdict) if isinstance(verdict, dict) else None
    return Mission(**value)


def _mission_to_dict(mission: Mission) -> dict[str, Any]:
    return asdict(mission)


def save_mission(root: Path, mission: Mission) -> Mission:
    mission.updated_at = _now()
    value = _mission_to_dict(mission)
    value["record_hash"] = _hash({k: v for k, v in value.items() if k != "record_hash"})
    _atomic_write(_mission_path(root, mission.mission_id), value)
    return load_mission(root, mission.mission_id)


def load_mission(root: Path, mission_id: str) -> Mission:
    value = json.loads(_mission_path(root, mission_id).read_text(encoding="utf-8"))
    value.pop("record_hash", None)
    return _mission_from_dict(value)


def list_missions(root: Path) -> list[dict[str, Any]]:
    base = _base(root) / "missions"
    if not base.exists():
        return []
    result = []
    for path in sorted(base.glob("mission-*.json")):
        try:
            mission = load_mission(root, path.stem)
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            continue
        result.append({
            "mission_id": mission.mission_id,
            "title": mission.title,
            "status": mission.status,
            "current_step": mission.current_step,
            "blocked_reason": mission.blocked_reason,
            "zero_verdict": mission.zero_verdict.verdict_type if mission.zero_verdict else None,
        })
    return result


def parse_command(text: str) -> CommandRecord:
    raw = text.strip()
    lower = raw.lower()
    arabic = raw
    target = "SYSTEM"
    intent = "UNKNOWN"
    execution = False
    mission_id = None
    requested = raw
    mission_match = re.search(r"\bmission-[a-f0-9]{8}\b", lower)
    if mission_match:
        mission_id = mission_match.group(0)
    if lower.startswith("zero") or arabic.startswith("زيرو"):
        target = "ZERO"
        intent = "STATUS" if "status" in lower or "حالة" in arabic or "true" in lower else "ASK_ZERO"
        if "challenge" in lower or "تحدى" in arabic or "راجع" in arabic:
            intent = "CHALLENGE"
    elif lower.startswith("omega") or arabic.startswith("اوميجا") or arabic.startswith("أوميجا"):
        target = "OMEGA"
        intent = "ASK_OMEGA"
        if "execute" in lower or "نفذ" in arabic:
            intent = "EXECUTE"; execution = True
    if "create mission" in lower or "انشئ مهمة" in arabic or "أنشئ مهمة" in arabic:
        target = "OMEGA"; intent = "CREATE_MISSION"
    elif "show missions" in lower or "المهام" in arabic:
        intent = "STATUS"; target = "SYSTEM"
    elif "show evidence" in lower:
        intent = "SHOW_EVIDENCE"; target = "ZERO"
    elif "show claims" in lower:
        intent = "SHOW_CLAIMS"; target = "ZERO"
    elif "verify" in lower or "تحقق" in arabic:
        intent = "VERIFY"; target = "ZERO"
    elif "pause" in lower or "وقف" in arabic:
        intent = "PAUSE"
    elif "resume" in lower or "استأنف" in arabic:
        intent = "RESUME"
    elif "cancel" in lower or "الغ" in arabic:
        intent = "CANCEL"
    if intent == "UNKNOWN" and ("status" in lower or "الحالة" in arabic):
        intent = "STATUS"
    return CommandRecord(
        command_id="cmd-" + uuid.uuid4().hex[:12],
        timestamp=_now(),
        operator_input=raw,
        normalized_intent=intent,
        target_role=target,
        mission_id_if_any=mission_id,
        requested_action=requested,
        authorization_requirement="NONE" if not execution else "MISSION_APPROVAL_REQUIRED",
        execution_requested=execution,
        context_refs=[],
        status="PARSED" if intent != "UNKNOWN" else "REJECTED",
    )


def create_mission(root: Path, objective: str, *, origin: str = "operator") -> Mission:
    title = objective.strip().splitlines()[0][:90] or "Untitled mission"
    mission_id = "mission-" + hashlib.sha256((objective + _now()).encode("utf-8")).hexdigest()[:8]
    mission = Mission(
        mission_id=mission_id,
        title=title,
        objective=objective.strip(),
        origin=origin,
        created_at=_now(),
        updated_at=_now(),
        status="DRAFT",
        assumptions=["The requested outcome can be verified with repository-local evidence."],
        constraints=["No external write, financial action, security testing, or production routing change without separate authority."],
        required_capabilities=["host-verification", "capability-discovery"],
        authorization_scope="A0_READ_A1_INTERNAL_EXECUTION_A2_INTERNAL_PREPARATION_UNTIL_ZERO_REVIEW",
        resource_budget={"financial": "0 KWD", "external_writes": 0},
        risk_class="LOW_INTERNAL" if not re.search(r"\b(send|publish|pay|attack|scan)\b", objective, re.I) else "REQUIRES_AUTHORITY_REVIEW",
        success_criteria=["A ZERO verdict cites concrete evidence before VERIFIED."],
        failure_criteria=["Required evidence is missing, contradicted, or authority is insufficient."],
        evidence_requirements=["Host Verification output or equivalent repository-local evidence."],
        current_plan=["ZERO review", "capability route selection", "bounded execution only after authority", "Host Verification", "ZERO verdict"],
        current_step="DRAFT_CREATED",
        continuity_state={"source": "mission_control", "task_continuity_integration": "MISSION_LINK_ONLY"},
    )
    mission = save_mission(root, mission)
    _event(root, "MISSION_CREATED", mission_id=mission.mission_id, status=mission.status)
    return mission


def transition_mission(root: Path, mission_id: str, target_state: str, *, reason: str = "") -> Mission:
    mission = load_mission(root, mission_id)
    if target_state not in MISSION_STATES:
        raise ValueError(f"unknown mission state: {target_state}")
    allowed = VALID_TRANSITIONS.get(mission.status, set())
    if target_state not in allowed:
        _event(root, "MISSION_TRANSITION_REJECTED", mission_id=mission_id, source=mission.status,
               target=target_state, reason="illegal transition")
        raise ValueError(f"illegal mission transition: {mission.status} -> {target_state}")
    mission.status = target_state
    mission.current_step = target_state
    if target_state in {"BLOCKED", "FAILED", "REJECTED"}:
        mission.blocked_reason = reason or target_state
    mission = save_mission(root, mission)
    _event(root, "MISSION_TRANSITIONED", mission_id=mission_id, target=target_state, reason=reason)
    return mission


def zero_challenge(root: Path, mission_id: str) -> ZeroVerdict:
    mission = load_mission(root, mission_id)
    missing: list[str] = []
    risks: list[str] = []
    conditions: list[str] = []
    if not mission.success_criteria:
        missing.append("success criteria")
    if not mission.evidence_requirements:
        missing.append("evidence requirements")
    if mission.risk_class == "REQUIRES_AUTHORITY_REVIEW":
        risks.append("objective may require external/financial/security authority")
    if not mission.evidence_refs:
        missing.append("completion evidence")
    conditions.append("OMEGA may not self-verify; ZERO requires linked evidence.")
    verdict_type = "CONDITIONAL" if not risks else "BLOCKED"
    verdict = ZeroVerdict(
        verdict_id="verdict-" + uuid.uuid4().hex[:12],
        mission_id=mission_id,
        claim_id_if_any=None,
        verdict_type=verdict_type,
        issued_at=_now(),
        subject="mission readiness",
        reason="mission is structurally reviewable but cannot be VERIFIED before evidence exists",
        evidence_refs=mission.evidence_refs,
        missing_evidence=missing,
        contradictions=[],
        conditions=conditions,
        risk_notes=risks,
        authorization_notes=[mission.authorization_scope],
        recommended_next_action="revise mission into bounded internal evidence step" if risks else "propose bounded execution plan",
    )
    mission.zero_verdict = verdict
    mission.status = "UNDER_ZERO_REVIEW" if mission.status in {"DRAFT", "PROPOSED"} else mission.status
    save_mission(root, mission)
    _event(root, "ZERO_VERDICT_ISSUED", mission_id=mission_id, verdict=verdict.verdict_type)
    return verdict


def verify_mission(root: Path, mission_id: str, *, evidence_ref: str | None = None) -> ZeroVerdict:
    mission = load_mission(root, mission_id)
    evidence = list(mission.evidence_refs)
    if evidence_ref:
        evidence.append(evidence_ref)
    if not evidence:
        verdict_type = "UNVERIFIED"
        reason = "ZERO cannot verify without evidence."
        missing = list(mission.evidence_requirements or ["evidence"])
    else:
        verdict_type = "VERIFIED"
        reason = "Required evidence reference supplied; mission claim is supported at repository-evidence level."
        missing = []
        mission.evidence_refs = evidence
        mission.status = "VERIFIED"
        mission.current_step = "ZERO_VERIFIED"
    verdict = ZeroVerdict(
        verdict_id="verdict-" + uuid.uuid4().hex[:12],
        mission_id=mission_id,
        claim_id_if_any=None,
        verdict_type=verdict_type,
        issued_at=_now(),
        subject="mission outcome",
        reason=reason,
        evidence_refs=evidence,
        missing_evidence=missing,
        recommended_next_action="attach evidence" if missing else "archive or continue child mission",
    )
    mission.zero_verdict = verdict
    save_mission(root, mission)
    _event(root, "ZERO_VERDICT_ISSUED", mission_id=mission_id, verdict=verdict.verdict_type)
    return verdict


def execute_mission(root: Path, mission_id: str) -> dict[str, Any]:
    mission = load_mission(root, mission_id)
    auth = evaluate_experiment_authority(root, action="execute internal mission step", task_id=mission_id)
    if not auth["allowed"] and mission.status not in {"APPROVED", "READY"}:
        mission.status = "BLOCKED"
        mission.blocked_reason = "execution denied without mission approval or experiment override"
        save_mission(root, mission)
        return {"executed": False, "mission_id": mission_id, "state": "BLOCKED", "authorization": auth}
    capabilities = discover_capabilities(root)
    profile = profile_task({
        "task_id": mission_id,
        "objective": mission.objective,
        "task_type": "DETERMINISTIC",
        "external_effects": False,
        "requires_capability": "VERIFICATION",
    })
    route = route_task(profile, capabilities)
    evidence_ref = "mission-evidence-" + uuid.uuid4().hex[:12]
    mission.status = "UNDER_VERIFICATION"
    mission.current_step = "HOST_VERIFICATION_REQUIRED"
    mission.evidence_refs.append(evidence_ref)
    mission.claims.append(Claim(
        claim_id="claim-" + uuid.uuid4().hex[:12],
        mission_id=mission_id,
        speaker="OMEGA",
        statement="Bounded internal mission step executed and awaits ZERO verification.",
        created_at=_now(),
        claim_type="EXECUTION_RESULT",
        evidence_refs=[evidence_ref],
        verification_state="UNVERIFIED",
    ))
    save_mission(root, mission)
    _event(root, "MISSION_INTERNAL_ACTION_EXECUTED", mission_id=mission_id, evidence_ref=evidence_ref,
           authority_source=auth["authority_source"])
    return {"executed": True, "mission_id": mission_id, "state": "UNDER_VERIFICATION",
            "authorization": auth, "route": route, "evidence_ref": evidence_ref}


def command_status(root: Path) -> dict[str, Any]:
    return {
        "zero_status": "TRUTH_VERIFIER_READY",
        "omega_status": "MISSION_OPERATOR_READY",
        "mission_count": len(list_missions(root)),
        "missions": list_missions(root)[-10:],
        "roles": {"ZERO": "verdict/evidence/authority", "OMEGA": "plan/execute/propose"},
    }


def route_operator_command(root: Path, text: str) -> dict[str, Any]:
    command = parse_command(text)
    _record_command(root, command)
    if command.normalized_intent == "CREATE_MISSION":
        objective = re.sub(r"(?i)^create mission[: ]*", "", command.operator_input).strip()
        mission = create_mission(root, objective, origin=command.command_id)
        return {"command": asdict(command), "result": _mission_to_dict(mission)}
    if command.normalized_intent == "STATUS":
        return {"command": asdict(command), "result": command_status(root)}
    if command.normalized_intent == "CHALLENGE" and command.mission_id_if_any:
        return {"command": asdict(command), "result": asdict(zero_challenge(root, command.mission_id_if_any))}
    if command.normalized_intent == "VERIFY" and command.mission_id_if_any:
        return {"command": asdict(command), "result": asdict(verify_mission(root, command.mission_id_if_any))}
    if command.normalized_intent == "EXECUTE" and command.mission_id_if_any:
        return {"command": asdict(command), "result": execute_mission(root, command.mission_id_if_any)}
    return {
        "command": asdict(command),
        "result": {
            "verdict": "UNKNOWN" if command.normalized_intent == "UNKNOWN" else "ROUTED",
            "message": "Command parsed; use mission create/list/show/challenge/execute/verify for material work.",
        },
    }

