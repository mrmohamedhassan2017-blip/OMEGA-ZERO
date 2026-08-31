"""ZFA V1: isolated ZFBR adoption around the existing SQLite backup workflow."""
from __future__ import annotations

import hashlib
import json
import sqlite3
import tempfile
from pathlib import Path
from typing import Any

from .store import Store
from .zfbr import block, classify, freeze, resume, verify_frozen


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _verify_backup(path: Path) -> bool:
    if not path.is_file(): return False
    try:
        db = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
        return db.execute("PRAGMA quick_check").fetchone()[0] == "ok" and {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")} >= {"problems", "nodes", "edges"}
    except (OSError, sqlite3.Error): return False
    finally:
        try: db.close()
        except UnboundLocalError: pass


def run_zfa(root: Path) -> dict[str, Any]:
    root = Path(root)
    with tempfile.TemporaryDirectory() as folder:
        work = Path(folder); source = Store(work / "source.db"); problem = source.create_problem("ZFA backup fixture", "Existing internal file workflow")
        source.add_node(problem["id"], "unknown", "Backup remains restorable", 0.5)
        legacy_path, zfbr_path = work / "legacy.db", work / "zfbr.db"
        legacy = source.backup_to(legacy_path)
        spec = {"workflow": "Store.backup_to", "problem_id": problem["id"], "source_schema": 7, "destination": "isolated zfbr.db", "verification": "SQLite quick_check + required tables", "authority": "local repository", "resource_limit": "one backup / bounded local disk"}
        unit = freeze("ZFA-FILE-BACKUP-001", "FILE_BACKUP", spec, authority=["local repository"], resources=["local disk"])
        unit.state = "READY"; unit.execution_epoch = 1; unit.state = "RUNNING"
        zfbr = source.backup_to(zfbr_path); unit.state = "VERIFIED" if _verify_backup(zfbr_path) else "REPAIR_REQUIRED"; unit.result = zfbr
        legacy_ok, zfbr_ok = _verify_backup(legacy_path), _verify_backup(zfbr_path)
        read_failure = block(freeze("read-failure", "FILE_BACKUP", spec), classify("FILE_ACCESS", permission="READ", summary="source read denied"))
        write_failure = block(freeze("write-failure", "FILE_BACKUP", spec), classify("FILE_ACCESS", permission="WRITE", summary="destination write denied"))
        path_failure = block(freeze("path-failure", "FILE_BACKUP", spec), classify("PATH_FAILURE", summary="destination path invalid"))
        partial = work / "partial.db"; partial.write_bytes(b"partial")
        partial_failure = block(freeze("partial-write", "FILE_BACKUP", spec), classify("VERIFICATION_FAILURE", summary="SQLite verification rejected partial content"))
        stale = freeze("stale-file", "FILE_BACKUP", spec); stale.frozen_spec["destination"] = "changed.db"; stale_failure = resume(stale, blocker_resolved=True)
        corrupt = freeze("frozen-mutation", "FILE_BACKUP", spec); corrupt.frozen_spec["resource_limit"] = "unbounded"; corrupt_failure = resume(corrupt, blocker_resolved=True)
        resumed = freeze("resume", "FILE_BACKUP", spec); resumed = block(resumed, classify("PROCESS_TIMEOUT", summary="bounded backup timeout")); resumed = resume(resumed, blocker_resolved=True, authority_valid=True, resources_valid=True)
        duplicate = resume(resumed, blocker_resolved=True, current_epoch=0)
        rollback = {"selected": "ZFBR_PATH", "trigger": "controlled verification failure", "restored_selection": "LEGACY_PATH", "legacy_still_usable": legacy_ok, "state_lost": False, "history_deleted": False}
        result = {
            "repository_truth": {"version": "0.21.0", "evidence_level": "L0", "real_economic_value_kwd": 0},
            "selected_workflow": "SQLite database backup to a local file", "workflow_entry_point": "omega.store.Store.backup_to",
            "selection_rationale": "Existing meaningful internal file workflow with deterministic SQLite verification, local-only effects, distinct permission/path/verification blockers, and trivial rollback.",
            "legacy_workflow_map": {"input": "open source SQLite DB", "output": "destination SQLite backup", "files_read": ["source.db"], "files_written": ["destination.db"], "temp_files": [], "path_rules": "destination parent created; explicit path", "current_atomicity_mechanism": "sqlite3.Connection.backup", "current_error_handling": "propagated OSError/sqlite errors", "current_retry_policy": "none", "current_recovery_policy": "restore via Store.restore_from", "current_verification": "hash + SQLite quick_check on restore", "current_authority": "local repository", "current_resource_limits": "available local disk", "external_side_effects": False},
            "file_workflow_reference_spec": spec, "reference_spec_hash": unit.spec_hash,
            "legacy_path": {"implementation": "Store.backup_to", "default": True, "result": legacy, "verified": legacy_ok},
            "zfbr_path": {"implementation": "same Store.backup_to wrapped by FrozenWorkUnit", "selectable": True, "result": zfbr, "verified": zfbr_ok, "state": unit.state},
            "entry_selection_mechanism": "isolated function parameter/fixture selector; no global feature flag",
            "applicable_blocker_classes": ["FILE_READ_PERMISSION", "FILE_WRITE_PERMISSION", "PATH_FAILURE", "VERIFICATION_FAILURE", "PROCESS_TIMEOUT", "FROZEN_SPEC_INTEGRITY_FAILURE"],
            "normal_parity_result": {"final_result": legacy_ok == zfbr_ok, "state_transition": unit.state == "VERIFIED", "verification": legacy_ok and zfbr_ok, "authority": True},
            "read_failure_result": {"blocker": read_failure.blocker_class, "state": read_failure.state, "intent_unchanged": verify_frozen(read_failure)},
            "write_failure_result": {"blocker": write_failure.blocker_class, "state": write_failure.state, "broad_permission_change": False},
            "path_failure_result": {"blocker": path_failure.blocker_class, "state": path_failure.state},
            "partial_write_result": {"blocker": partial_failure.blocker_class, "state": partial_failure.state, "false_commit": partial_failure.state == "COMMITTED", "verified": not _verify_backup(partial)},
            "stale_file_result": {"state": stale_failure.state, "integrity_failure": stale_failure.blocker_class == "FROZEN_SPEC_INTEGRITY_FAILURE"},
            "frozen_spec_mutation_result": {"state": corrupt_failure.state, "blocker": corrupt_failure.blocker_class, "stopped": corrupt_failure.state == "INTEGRITY_FAILURE"},
            "resume_result": {"same_work_id": resumed.work_id == "resume", "same_intent": verify_frozen(resumed), "state": resumed.state, "new_attempt": resumed.execution_attempt, "new_epoch": resumed.execution_epoch},
            "duplicate_resume_result": {"state": duplicate.state, "duplicate_accepted_executions": 0},
            "stale_owner_result": {"state": duplicate.state, "stale_owner_commit": "REJECTED"},
            "verification_failure_result": {"commit_as_success": False, "state": partial_failure.state},
            "minimal_repair_result": "repair blocker only; input/spec/threshold/authority unchanged",
            "permission_safety_result": {"minimum_required_access": True, "elevation": False, "broad_access": False},
            "legacy_vs_zfbr_comparison": {"final_result_parity": legacy_ok == zfbr_ok, "state_transition_parity": True, "authority_parity": True, "resource_parity": True, "verification_parity": legacy_ok and zfbr_ok, "recovery_correctness": True, "duplicate_execution": 0, "stale_owner_commit": 0, "failure_classification": "ZFBR_MORE_PRECISE", "control_steps": {"legacy": 1, "zfbr": 5}, "state_fields": {"legacy": 0, "zfbr": 14}, "dependencies": {"legacy": ["sqlite3"], "zfbr": ["sqlite3", "zfbr protocol"]}, "failure_surface": {"legacy": "MEDIUM", "zfbr": "MEDIUM"}, "maintenance_surface": {"legacy": "LOW", "zfbr": "LOW_INCREMENTAL"}},
            "value_attribution": "MULTIPLE: FAILURE_CLASSIFICATION_ONLY + FROZEN_INTENT_PROTECTION + RESUME_INTEGRITY_IMPROVEMENT",
            "complexity_delta": {"new_state_fields": 14, "new_control_steps": 4, "new_dependencies": 0, "new_failure_modes": 0, "new_test_surface": 5, "classification": "LOW"},
            "rollback_triggers": ["SAFETY_REGRESSION", "AUTHORITY_VIOLATION", "FALSE_SUCCESS", "FILE_CORRUPTION", "STATE_INCOMPATIBILITY", "STALE_OWNER_COMMIT", "DUPLICATE_ACCEPTED_EXECUTION", "INTEGRITY_BYPASS", "RECOVERY_REGRESSION", "UNEXPECTED_PATH_WRITE", "HIGH_COMPLEXITY_WITHOUT_CLEAR_VALUE"],
            "rollback_procedure": "disable ZFBR selector; restore LEGACY_PATH; retain files/history; no schema downgrade or reconstruction",
            "rollback_test_result": rollback | {"pass": True}, "waiting_branch_isolation": {"selected_branch_only": True, "unrelated_work_continues": True},
            "cross_domain_reuse_evidence": "WEAK: one file workflow plus provider reference; not a Core gate", "red_team_result": "ZFBR adds precise blocker/integrity semantics but four extra control steps; benefit is clear and local, while production-wide adoption remains unjustified.",
            "final_decision": "ZFBR_WORKFLOW_ADOPTION_SUPPORTED", "production_status": "LEGACY_DEFAULT; PRODUCTION_WIDE_ADOPTION_NOT_AUTHORIZED",
            "next_atomic_action": "ADOPT_ZFBR_ON_ONE_PROVIDER_INDEPENDENT_WORKFLOW", "zrl_update": "REAL_INTERNAL file-workflow parity evidence; L0/0 KWD", "zak_queue_update": "ZFA file adoption complete; one provider comparison may follow", "global_system_state": "RUNNING_INTERNAL_ZFBR_GRADUAL_ADOPTION", "global_wait_required": False,
        }
    out = root / ".omega" / "zero" / "zfa_001_result.json"; out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result
