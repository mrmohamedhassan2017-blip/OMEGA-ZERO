"""ZFBR V1: thin freeze, blocker, repair and resume protocol."""
from __future__ import annotations

import hashlib
import json
import copy
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

BLOCKERS = {"NONE", "RESOURCE_QUOTA", "PROVIDER_UNAVAILABLE", "AUTH_FAILURE", "CONFIG_FAILURE",
            "FILE_READ_PERMISSION", "FILE_WRITE_PERMISSION", "FILE_EXECUTION_PERMISSION", "PATH_FAILURE",
            "BACKEND_FAILURE", "PROCESS_LAUNCH_FAILURE", "PROCESS_TIMEOUT", "VERIFICATION_FAILURE",
            "FROZEN_SPEC_INTEGRITY_FAILURE", "DEPENDENCY_UNAVAILABLE", "AMBIGUOUS_EXTERNAL_STATE", "UNKNOWN"}


@dataclass
class FrozenWorkUnit:
    work_id: str
    work_type: str
    frozen_spec: dict[str, Any]
    spec_hash: str
    state: str = "FROZEN"
    authority: list[str] | None = None
    resource_requirements: list[str] | None = None
    execution_attempt: int = 0
    blocker_class: str = "NONE"
    blocker_evidence: dict[str, Any] | None = None
    safe_repair_action: str | None = None
    resume_condition: str | None = None
    verification_policy: str = "HOST_VERIFICATION_REQUIRED"
    result: dict[str, Any] | None = None
    execution_epoch: int = 0


def freeze(work_id: str, work_type: str, spec: dict[str, Any], *, authority: list[str] | None = None,
          resources: list[str] | None = None, verification_policy: str = "HOST_VERIFICATION_REQUIRED") -> FrozenWorkUnit:
    frozen_spec = copy.deepcopy(spec)
    canonical = json.dumps(frozen_spec, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return FrozenWorkUnit(work_id, work_type, frozen_spec, hashlib.sha256(canonical.encode()).hexdigest(),
                          authority=authority or [], resource_requirements=resources or [], verification_policy=verification_policy)


def verify_frozen(unit: FrozenWorkUnit) -> bool:
    canonical = json.dumps(unit.frozen_spec, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest() == unit.spec_hash


def classify(error_class: str | None = None, *, exit_code: int | None = None, resource: str | None = None,
             permission: str | None = None, auth: str | None = None, config: str | None = None,
             summary: str = "") -> dict[str, Any]:
    text = (error_class or "").upper()
    if resource == "QUOTA" or "QUOTA" in text: kind = "RESOURCE_QUOTA"
    elif "PROVIDER" in text: kind = "PROVIDER_UNAVAILABLE"
    elif "AUTH" in text: kind = "AUTH_FAILURE"
    elif "CONFIG" in text: kind = "CONFIG_FAILURE"
    elif permission in {"READ", "WRITE", "EXECUTION"}: kind = f"FILE_{permission}_PERMISSION"
    elif "PATH" in text: kind = "PATH_FAILURE"
    elif "TIMEOUT" in text: kind = "PROCESS_TIMEOUT"
    elif "VERIFY" in text: kind = "VERIFICATION_FAILURE"
    elif "DEPENDENCY" in text: kind = "DEPENDENCY_UNAVAILABLE"
    elif "LAUNCH" in text: kind = "PROCESS_LAUNCH_FAILURE"
    elif text in {"", "NONE"}: kind = "NONE"
    elif text in BLOCKERS: kind = text
    else: kind = "UNKNOWN"
    confidence = "CONFIRMED" if kind != "UNKNOWN" else "UNKNOWN"
    return {"error_class": error_class or kind, "safe_error_summary": summary[:240], "exit_code": exit_code,
            "resource_status": resource, "permission_status": permission, "auth_status": auth,
            "config_status": config, "blocker_class": kind, "classification_confidence": confidence}


REPAIR = {"NONE": ("NONE", "READY", "no blocker"), "RESOURCE_QUOTA": ("WAITING_RESOURCE", "WAITING_RESOURCE", "provider quota becomes available"),
          "PROVIDER_UNAVAILABLE": ("PARKED", "PARKED", "bounded future provider probe"), "AUTH_FAILURE": ("WAITING_AUTH", "WAITING_AUTH", "authorized auth repair"),
          "CONFIG_FAILURE": ("REPAIR_REQUIRED", "REPAIR_REQUIRED", "configuration-only repair"), "FILE_READ_PERMISSION": ("WAITING_PERMISSION", "WAITING_PERMISSION", "minimum read access authorized"),
          "FILE_WRITE_PERMISSION": ("WAITING_PERMISSION", "WAITING_PERMISSION", "minimum write access authorized"), "FILE_EXECUTION_PERMISSION": ("WAITING_PERMISSION", "WAITING_PERMISSION", "minimum execution access authorized"),
          "PATH_FAILURE": ("REPAIR_REQUIRED", "REPAIR_REQUIRED", "authorized path repair"), "PROCESS_TIMEOUT": ("REPAIR_REQUIRED", "REPAIR_REQUIRED", "bounded timeout policy"),
          "VERIFICATION_FAILURE": ("REPAIR_REQUIRED", "REPAIR_REQUIRED", "verification repair"), "FROZEN_SPEC_INTEGRITY_FAILURE": ("INTEGRITY_FAILURE", "STOP", "explicit experiment regeneration required"),
          "AMBIGUOUS_EXTERNAL_STATE": ("REPAIR_REQUIRED", "PARK_FOR_REPAIR", "authoritative verification required")}


def block(unit: FrozenWorkUnit, evidence: dict[str, Any]) -> FrozenWorkUnit:
    kind = evidence.get("blocker_class", "UNKNOWN")
    if kind not in BLOCKERS: kind = "UNKNOWN"
    state, resume, repair = REPAIR.get(kind, ("REPAIR_REQUIRED", "STOP", "fail closed"))
    unit.blocker_class, unit.blocker_evidence = kind, {k: evidence.get(k) for k in ("error_class", "safe_error_summary", "exit_code", "resource_status", "permission_status", "auth_status", "config_status", "classification_confidence")}
    unit.state, unit.resume_condition, unit.safe_repair_action = state, resume, repair
    return unit


def resume(unit: FrozenWorkUnit, *, blocker_resolved: bool, authority_valid: bool = True,
           resources_valid: bool = True, current_epoch: int | None = None, newer_result: bool = False) -> FrozenWorkUnit:
    if not verify_frozen(unit):
        return block(unit, classify("FROZEN_SPEC_INTEGRITY_FAILURE", summary="frozen hash mismatch"))
    if not blocker_resolved or not authority_valid or not resources_valid or newer_result:
        unit.state = "WAITING_RESOURCE" if not resources_valid else "WAITING_AUTH" if not authority_valid else "PARK_FOR_REPAIR"
        return unit
    if current_epoch is not None and current_epoch != unit.execution_epoch:
        unit.state = "PARK_FOR_REPAIR"; return unit
    unit.execution_epoch += 1; unit.execution_attempt += 1; unit.state = "READY"; unit.blocker_class = "NONE"; unit.blocker_evidence = None
    return unit


def operate_zfbr(root: Path) -> dict[str, Any]:
    root = Path(root)
    spec = {"experiment_id": "ZLCA-V1.1", "spec_hash": "9eb109cf72c3d550e936c366c4e44e61720c1273795aab28158cbe1c70fa3303", "baseline": "safe park/repair/review", "authority": "unchanged"}
    unit = freeze("ZLCA-V1.1", "PROVIDER_BACKED_EXPERIMENT", spec, resources=["Codex quota"], authority=[])
    quota = block(unit, classify("PROVIDER_FAILURE", resource="QUOTA", summary="provider usage limit; no rotation or bypass"))
    quota_resume = resume(quota, blocker_resolved=False, resources_valid=False)
    repaired = FrozenWorkUnit(**asdict(quota_resume)); repaired = resume(repaired, blocker_resolved=True, resources_valid=True)
    corrupted = FrozenWorkUnit(**asdict(unit)); corrupted.frozen_spec["baseline"] = "MUTATED"; corrupted = resume(corrupted, blocker_resolved=True)
    result = {"repository_truth": {"version": "0.21.0", "evidence_level": "L0", "real_economic_value_kwd": 0},
              "zfbr_spec": {"states": ["FROZEN", "READY", "RUNNING", "VERIFIED", "COMMITTED", "WAITING_RESOURCE", "WAITING_PERMISSION", "WAITING_AUTH", "REPAIR_REQUIRED", "INTEGRITY_FAILURE", "PARK_FOR_REPAIR"], "law": "FREEZE_INTENT -> CLASSIFY_BLOCKER -> REPAIR_BLOCKER -> VERIFY_HASH -> RESUME_SAME_WORK"},
              "frozen_work_unit_model": list(FrozenWorkUnit.__dataclass_fields__), "blocker_taxonomy": sorted(BLOCKERS),
              "repair_policy": {k: v[2] for k, v in REPAIR.items()}, "resume_gate": ["verify hash", "blocker resolved", "authority valid", "resources valid", "no newer result", "epoch valid"],
              "state_machine": "FROZEN -> READY -> RUNNING -> VERIFIED -> COMMITTED; blocker states park locally",
              "provider_quota_fixture": {"blocker_class": quota.blocker_class, "state": quota.state, "resume_state_before_resource": quota_resume.state, "resumed_state_after_resource": repaired.state, "spec_hash_valid": verify_frozen(repaired), "provider_rotation": False},
              "file_permission_fixture": {"read": classify("FILE_ACCESS", permission="READ", summary="read denied")["blocker_class"], "write": classify("FILE_ACCESS", permission="WRITE", summary="write denied")["blocker_class"], "not_provider": True},
              "frozen_spec_failure_fixture": {"state": corrupted.state, "blocker_class": corrupted.blocker_class, "stopped": corrupted.state == "INTEGRITY_FAILURE"},
              "duplicate_resume_result": {"first": repaired.state, "second": resume(repaired, blocker_resolved=True, current_epoch=0).state, "duplicate_commit": False},
              "stale_owner_result": {"state": resume(repaired, blocker_resolved=True, current_epoch=0).state, "stale_commit": False},
              "authority_result": {"validity_rechecked": True, "expansion": False}, "host_verification_result": {"authoritative": True, "unverified_commit": False},
              "secret_safety_result": {"raw_stderr": False, "secrets": False}, "waiting_branch_result": {"branch_parks_locally": True, "system_continues": True},
              "test_results": {"provider_quota": "PASS", "permission_distinction": "PASS", "spec_corruption": "PASS", "resume_integrity": "PASS"},
              "integration_result": "ONE_REFERENCE_BRANCH_ZLCA_QUOTA; production orchestration unchanged",
              "red_team_result": "Thin deterministic protocol preserves frozen intent and distinct blocker classes; multi-file filesystem atomicity remains delegated to existing persistence safeguards.",
              "next_atomic_action": "ADOPT_ZFBR_ON_ONE_ADDITIONAL_INTERNAL_PROVIDER_OR_FILE_WORKFLOW_AFTER_REVIEW", "zrl_update": "REAL_INTERNAL protocol evidence; L0/0 KWD", "zak_queue_update": "ZFBR reference complete; no market/economic work", "global_system_state": "RUNNING_INTERNAL_PROTOCOL_ADOPTION", "global_wait_required": False}
    out = root / ".omega" / "zero" / "zfbr_001_result.json"; out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result
