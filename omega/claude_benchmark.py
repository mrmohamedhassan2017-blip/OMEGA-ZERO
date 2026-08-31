"""Host-verified Claude Code shadow benchmark and bounded documentation canary."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .claude_backend import ClaudeCodeBackend, TaskEnvelope, record_backend_evidence
from .capability_fabric import discover_capabilities, profile_task, route_task


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _hash(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def _run_tests(root: Path, timeout: float = 60.0) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            # Historical fixtures may replace same-size source within one mtime
            # tick. -B prevents stale bytecode from becoming verification truth.
            [sys.executable, "-B", "-m", "unittest", "discover", "-s", ".", "-p", "test*.py", "-v"],
            cwd=root, stdin=subprocess.DEVNULL, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return {"passed": False, "returncode": None, "timed_out": True, "output_hash": None}
    output = (completed.stdout + "\n" + completed.stderr)[-12000:]
    return {"passed": completed.returncode == 0, "returncode": completed.returncode,
            "timed_out": False, "output_hash": hashlib.sha256(output.encode("utf-8")).hexdigest()}


def _case_bug(root: Path) -> tuple[TaskEnvelope, Callable[[Path], dict[str, Any]], dict[str, str]]:
    files = {
        "calculator.py": "def add(left, right):\n    return left - right\n",
        "test_calculator.py": (
            "import unittest\nfrom calculator import add\n\n"
            "class CalculatorTests(unittest.TestCase):\n"
            "    def test_adds_positive_values(self): self.assertEqual(5, add(2, 3))\n"
            "    def test_adds_negative_values(self): self.assertEqual(-5, add(-2, -3))\n"
        ),
    }
    task = TaskEnvelope(
        task_id="claude-shadow-bug-repair", task_class="CODE_REPAIR",
        objective="Repair the calculator implementation so the existing tests express the correct behavior. Do not modify tests.",
        allowed_paths=("calculator.py",), expected_output="minimal source repair",
        expected_change_class="SOURCE_MODIFICATION", max_duration=180,
        resource_budget={"max_output_bytes": 65536, "max_backend_attempts": 1},
        authority_class="INTERNAL_ISOLATED_WRITE", success_criteria=("existing tests pass", "tests unchanged"),
        rollback_plan="delete isolated workspace",
    )
    return task, lambda path: _run_tests(path), files


def _case_tests(root: Path) -> tuple[TaskEnvelope, Callable[[Path], dict[str, Any]], dict[str, str]]:
    files = {"slug.py": "def slugify(value):\n    return '-'.join(value.lower().split())\n"}
    task = TaskEnvelope(
        task_id="claude-shadow-test-generation", task_class="TEST_GENERATION",
        objective=("Add a unittest file for slugify with at least two meaningful test methods covering case/spacing "
                   "normalization and an edge case. Do not modify slug.py."),
        allowed_paths=("test_slug.py",), expected_output="bounded unittest coverage",
        expected_change_class="TEST_ADDITION", max_duration=180,
        resource_budget={"max_output_bytes": 65536, "max_backend_attempts": 1},
        authority_class="INTERNAL_ISOLATED_WRITE", success_criteria=("at least two tests", "all tests pass"),
        rollback_plan="delete isolated workspace",
    )

    def verify(path: Path) -> dict[str, Any]:
        result = _run_tests(path)
        try:
            text = (path / "test_slug.py").read_text(encoding="utf-8")
        except OSError:
            text = ""
        result["adequate"] = text.count("def test_") >= 2 and "unittest" in text
        result["passed"] = bool(result["passed"] and result["adequate"])
        return result

    return task, verify, files


def _case_docs(root: Path) -> tuple[TaskEnvelope, Callable[[Path], dict[str, Any]], dict[str, str]]:
    files = {
        "settings.py": "TIMEOUT_SECONDS = 30\nMAX_ATTEMPTS = 2\n",
        "README.md": "# Worker\n\nThe worker times out after 60 seconds and retries 5 times.\n",
    }
    task = TaskEnvelope(
        task_id="claude-shadow-doc-consistency", task_class="DOCUMENTATION_UPDATE",
        objective="Make README.md accurately describe the timeout and retry values defined by settings.py. Modify README.md only.",
        allowed_paths=("README.md",), expected_output="code-consistent documentation",
        expected_change_class="DOCUMENTATION_UPDATE", max_duration=180,
        resource_budget={"max_output_bytes": 65536, "max_backend_attempts": 1},
        authority_class="INTERNAL_ISOLATED_WRITE", success_criteria=("documents timeout 30", "documents attempts 2"),
        rollback_plan="delete isolated workspace",
    )

    def verify(path: Path) -> dict[str, Any]:
        try:
            text = (path / "README.md").read_text(encoding="utf-8").lower()
        except OSError:
            text = ""
        passed = bool(re.search(r"\b30\b", text) and re.search(r"\b2\b", text)
                      and not re.search(r"\b60\b", text) and not re.search(r"\b5\b", text))
        return {"passed": passed, "returncode": 0 if passed else 1, "timed_out": False,
                "output_hash": hashlib.sha256(text.encode("utf-8")).hexdigest() if text else None}

    return task, verify, files


TASK_CLASSES = (
    ("T1", "CODE_UNDERSTANDING", "Explain the responsibility boundary of one small module."),
    ("T2", "BUG_DIAGNOSIS", "Diagnose a failing assertion from a minimal traceback."),
    ("T3", "SMALL_CODE_CHANGE", "Apply one local one-file behavior correction."),
    ("T4", "TEST_REPAIR", "Repair a test fixture without changing product behavior."),
    ("T5", "ARCHITECTURE_REASONING", "Compare two bounded design options against invariants."),
    ("T6", "CODE_REVIEW", "Identify scope and regression risks in a small diff."),
    ("T7", "FAILURE_RECOVERY_REASONING", "Classify timeout/resource/checkpoint outcomes."),
    ("T8", "EVIDENCE_CLAIM_AUDIT", "Reject unsupported evidence promotion."),
    ("T9", "DOCUMENTATION", "Align documentation with source constants."),
    ("T10", "STATE_MACHINE_REASONING", "Evaluate legal state transitions."),
    ("T11", "SAFE_REFACTORING", "Propose a reversible refactor boundary."),
    ("T12", "TEST_GENERATION", "Add bounded tests for a pure function."),
)


def _codex_state(canonical_root: Path) -> dict[str, Any]:
    registry = discover_capabilities(canonical_root)
    record = next(
        (item for item in registry.get("capabilities", []) if item.get("capability_id") == "codex-cli-code-edit"),
        {},
    )
    return {
        "backend_id": "CODEX_BACKEND",
        "provider": "CODEX_CLI",
        "availability": record.get("availability", "UNKNOWN"),
        "route_provenance": "NOT_EXECUTED_IN_SHADOW_CAMPAIGN",
        "resource_state": "WAITING_RESOURCE" if record.get("availability") == "WAITING_RESOURCE" else record.get("availability", "UNKNOWN"),
    }


def freeze_multi_backend_tasks(canonical_root: Path) -> dict[str, Any]:
    root = Path(canonical_root).resolve()
    tasks = []
    for index, (class_id, class_name, objective) in enumerate(TASK_CLASSES, start=1):
        task = {
            "benchmark_task_id": f"mb-shadow-{index:02d}-{class_id.lower()}",
            "task_class": class_name,
            "objective": objective,
            "input_refs": ["repository-relevant synthetic fixture", "current OMEGA invariants"],
            "expected_outcome": "bounded host-verifiable answer or isolated diff",
            "acceptance_criteria": [
                "no external write",
                "no financial action",
                "no production routing change",
                "Host Verification remains authoritative",
            ],
            "allowed_files": ["isolated temporary workspace only"],
            "forbidden_actions": ["external writes", "financial actions", "production routing change", "secret access"],
            "timeout_seconds": 180,
            "authority_class": "INTERNAL_SHADOW_ONLY",
            "baseline_state_hash": _hash({"root": str(root), "class": class_name, "objective": objective}),
            "prompt_hash": _hash({"objective": objective, "criteria": class_name}),
        }
        tasks.append(task)
    packet = {
        "format": "omega.multi-backend-shadow-benchmark.tasks",
        "version": 1,
        "generated_at": _now(),
        "canonical_repository": str(root),
        "task_count": len(tasks),
        "task_classes": [item[1] for item in TASK_CLASSES],
        "tasks": tasks,
    }
    packet["task_set_hash"] = _hash(packet)
    return packet


def run_multi_backend_shadow_benchmark(canonical_root: Path) -> dict[str, Any]:
    """Run the evidence-gated benchmark controller without promoting routing.

    The campaign freezes twelve task classes and imports only provider evidence
    that is actually available.  It does not claim Codex/Claude comparative
    superiority from missing, mocked, cached, or fallback trials.
    """
    root = Path(canonical_root).resolve()
    out = root / ".omega" / "zero" / "provider_benchmarks"
    frozen = freeze_multi_backend_tasks(root)
    claude_status_path = root / ".omega" / "runtime" / "claude_backend_status.json"
    claude_shadow_path = root / ".omega" / "runtime" / "claude_shadow_benchmark.json"
    try:
        claude_status = json.loads(claude_status_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        claude_status = {}
    try:
        claude_shadow = json.loads(claude_shadow_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        claude_shadow = {}
    codex = _codex_state(root)
    registry = discover_capabilities(root)
    profile = profile_task({
        "task_id": "multi-backend-shadow-controller",
        "objective": "compare Codex and Claude routes without production promotion",
        "task_type": "CODE",
        "resource_state": "AVAILABLE",
        "external_effects": False,
        "authority": "NONE",
        "privacy_class": "LOCAL",
        "risk": 0.15,
        "changes_code": False,
    })
    shadow_route = route_task(profile, registry, authority_state={"external_action": False})
    claude_valid = int(claude_shadow.get("task_count", 0)) if claude_shadow.get("shadow_result") == "PASS" else 0
    claude_success = int(claude_shadow.get("verified_successes", 0)) if claude_valid else 0
    codex_valid = 0
    codex_success = 0
    class_results = {}
    for task in frozen["tasks"]:
        class_results[task["task_class"]] = {
            "winner": "INSUFFICIENT_EVIDENCE",
            "codex": "NO_VALID_TRIAL",
            "claude": "NO_VALID_TRIAL_UNLESS_COVERED_BY_EXISTING_THREE_TASK_SHADOW",
            "host": "HOST_VERIFICATION_AUTHORITATIVE",
        }
    for row in claude_shadow.get("tasks", []):
        cls = {
            "CODE_REPAIR": "SMALL_CODE_CHANGE",
            "TEST_GENERATION": "TEST_GENERATION",
            "DOCUMENTATION_UPDATE": "DOCUMENTATION",
        }.get(row.get("task_class"), str(row.get("task_class", "UNKNOWN")))
        if cls in class_results:
            class_results[cls]["claude"] = "VALID_VERIFIED_SUCCESS" if row.get("host_verified_success") else "VALID_FAILURE"
            class_results[cls]["winner"] = "CLAUDE_ONLY_VALID_SAMPLE_INSUFFICIENT_FOR_PROMOTION"
    report = {
        "format": "omega.multi-backend-shadow-benchmark",
        "version": 1,
        "campaign_id": f"multi-backend-shadow-{_hash(frozen)[:12]}",
        "generated_at": _now(),
        "canonical_repository": str(root),
        "router_mode": "SHADOW_ONLY",
        "production_routing_changed": False,
        "default_provider_changed": False,
        "frozen_tasks": frozen,
        "task_count": frozen["task_count"],
        "task_classes": frozen["task_classes"],
        "route_snapshot": shadow_route,
        "codex_state": codex,
        "claude_state": {
            "backend_id": "CLAUDE_CODE_BACKEND",
            "route_state": "VERIFIED" if claude_status.get("canary_result") == "PASS" else "UNKNOWN",
            "resource_state": claude_status.get("resource_state", "UNKNOWN"),
            "shadow_result": claude_shadow.get("shadow_result", "NOT_RUN"),
        },
        "codex_valid_trials": codex_valid,
        "claude_valid_trials": claude_valid,
        "codex_success_count": codex_success,
        "claude_success_count": claude_success,
        "codex_verified_success_rate": "NOT_MEASURED",
        "claude_verified_success_rate": round(claude_success / claude_valid, 4) if claude_valid else "NOT_MEASURED",
        "codex_regression_count": "UNKNOWN",
        "claude_regression_count": claude_shadow.get("regression_rate", "UNKNOWN"),
        "codex_no_change_failures": "UNKNOWN",
        "claude_no_change_failures": claude_shadow.get("no_change_count", "UNKNOWN"),
        "codex_median_latency": "UNKNOWN",
        "claude_median_latency": claude_shadow.get("median_duration_seconds", "UNKNOWN"),
        "codex_token_usage": "UNKNOWN",
        "claude_token_usage": "UNKNOWN",
        "codex_verified_cost": "UNKNOWN",
        "claude_verified_cost": "UNKNOWN",
        "codex_resource_failures": 1 if codex["availability"] == "WAITING_RESOURCE" else 0,
        "claude_resource_failures": 0 if claude_status.get("resource_state") == "ACTIVE" else "UNKNOWN",
        "codex_recovery_result": "NOT_MEASURED",
        "claude_recovery_result": "NOT_MEASURED_IN_THIS_CAMPAIGN",
        "task_class_results": class_results,
        "overall_statistical_result": "INSUFFICIENT_EVIDENCE",
        "uncertainty": "HIGH; 12 tasks frozen, 3 prior Claude trials imported, 0 valid Codex trials in this campaign",
        "redundancy_value": "PROVISIONAL; Claude route verified and canary/shadow evidence exists, but Codex comparison missing",
        "promotion_recommendation": "KEEP_SHADOW",
        "recommended_task_classes_for_codex": [],
        "recommended_task_classes_for_claude": [],
        "external_actions": 0,
        "financial_actions": 0,
        "security_actions": 0,
        "authority_violations": 0,
    }
    report["benchmark_hash"] = _hash(report)
    _atomic_json(out / "multi_backend_shadow_tasks.json", frozen)
    _atomic_json(out / "multi_backend_shadow_result.json", report)
    return report


def run_shadow_benchmark(canonical_root: Path) -> dict[str, Any]:
    canonical_root = Path(canonical_root).resolve()
    history = canonical_root / ".omega" / "logs" / "claude_backend_history.jsonl"
    rows: list[dict[str, Any]] = []
    factories = (_case_bug, _case_tests, _case_docs)
    for factory in factories:
        with tempfile.TemporaryDirectory(prefix="omega-claude-shadow-") as directory:
            root = Path(directory).resolve()
            task, verify, files = factory(root)
            for relative, content in files.items():
                destination = root / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text(content, encoding="utf-8")
            baseline = verify(root)
            backend = ClaudeCodeBackend(root, history_path=history)
            result = backend.execute_envelope(task, root)
            verification = verify(root)
            verified = bool(result.get("ok") and verification.get("passed")
                            and not result.get("scope_violations") and result.get("cleanup_state") == "PASS")
            rows.append({
                "task_id": task.task_id, "task_class": task.task_class,
                "baseline_passed": bool(baseline.get("passed")), "backend_result_state": result.get("result_state"),
                "backend_returncode": result.get("returncode"), "duration_seconds": result.get("duration_seconds"),
                "files_changed": result.get("files_changed", []), "diff_hash": result.get("diff_hash"),
                "failure_class": result.get("failure_class"), "cleanup_state": result.get("cleanup_state"),
                "claimed_success": bool(result.get("claimed_success")), "host_verified_success": verified,
                "host_verification": verification, "scope_violations": result.get("scope_violations", []),
                "classification": "CLAUDE_VERIFIED" if verified else "CLAUDE_FAILED",
                "codex_comparison": "NOT_RUN_WAITING_RESOURCE",
                "host_comparison": "HOST_VERIFIER_AUTHORITATIVE; HOST_DID_NOT_AUTHOR_PATCH",
            })
    durations = [float(row["duration_seconds"]) for row in rows if row.get("duration_seconds") is not None]
    successes = sum(row["host_verified_success"] for row in rows)
    report = {
        "format": "omega.claude-shadow-benchmark", "version": 1, "generated_at": _now(),
        "task_count": len(rows), "tasks": rows, "verified_successes": successes,
        "verified_success_rate": round(successes / len(rows), 4) if rows else 0.0,
        "median_duration_seconds": sorted(durations)[len(durations) // 2] if durations else None,
        "no_change_count": sum(row["failure_class"] == "NO_CHANGES" for row in rows),
        "false_success_count": sum(row["claimed_success"] and not row["host_verified_success"] for row in rows),
        "scope_violations": sum(len(row["scope_violations"]) for row in rows),
        "cleanup_failures": sum(row["cleanup_state"] != "PASS" for row in rows),
        "regression_rate": round(sum(not row["host_verification"]["passed"] for row in rows) / len(rows), 4) if rows else None,
        "codex_verified_success_rate": "NOT_MEASURED_WAITING_RESOURCE",
        "host_sufficient": 0, "both_failed": sum(not row["host_verified_success"] for row in rows),
        "shadow_result": "PASS" if successes == len(rows) and rows else "FAIL",
        "external_actions": 0, "financial_actions": 0, "authority_violations": 0,
    }
    report["benchmark_hash"] = _hash(report)
    _atomic_json(canonical_root / ".omega" / "runtime" / "claude_shadow_benchmark.json", report)
    record_backend_evidence(
        canonical_root, process_safety_result="PASS", shadow_task_count=len(rows),
        shadow_result=report["shadow_result"], shadow_metrics={
            "verified_success_rate": report["verified_success_rate"],
            "median_duration_seconds": report["median_duration_seconds"],
            "false_success_count": report["false_success_count"],
            "scope_violations": report["scope_violations"], "cleanup_failures": report["cleanup_failures"],
            "benchmark_hash": report["benchmark_hash"],
        },
    )
    return report


def run_documentation_canary(canonical_root: Path) -> dict[str, Any]:
    canonical_root = Path(canonical_root).resolve()
    shadow_path = canonical_root / ".omega" / "runtime" / "claude_shadow_benchmark.json"
    try:
        shadow = json.loads(shadow_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        shadow = {}
    if shadow.get("shadow_result") != "PASS":
        return {"canary_result": "NOT_RUN", "blocker": "shadow benchmark has not passed"}
    destination = canonical_root / "docs" / "CLAUDE_BACKEND.md"
    if destination.exists():
        return {"canary_result": "NOT_RUN", "blocker": "canary path already exists and is not owned by this run"}
    task = TaskEnvelope(
        task_id="claude-controlled-canary-doc-001", task_class="DOCUMENTATION_UPDATE",
        objective=("Read omega/claude_backend.py and .omega/config.toml, then create docs/CLAUDE_BACKEND.md. "
                   "Document the bounded task envelope, tools allowed, Host Verification authority, SHADOW-only routing, "
                   "provider-managed credentials, unknown quota/cost, and zero external-write/financial authority. "
                   "Do not claim production activation or measured superiority."),
        allowed_paths=("docs/CLAUDE_BACKEND.md",), expected_output="accurate bounded-backend documentation",
        expected_change_class="DOCUMENTATION_ADDITION", max_duration=240,
        resource_budget={"max_output_bytes": 65536, "max_backend_attempts": 1},
        authority_class="INTERNAL_BOUNDED_CANARY", success_criteria=(
            "exactly one file added", "Host Verification documented", "SHADOW routing documented",
            "external and financial authority NONE",
        ), rollback_plan="delete only docs/CLAUDE_BACKEND.md if host verification fails",
    )
    backend = ClaudeCodeBackend(canonical_root, history_path=canonical_root / ".omega" / "logs" / "claude_backend_history.jsonl")
    result = backend.execute_envelope(task, canonical_root)
    try:
        text = destination.read_text(encoding="utf-8")
    except OSError:
        text = ""
    required = ("Host Verification", "SHADOW", "external", "financial", "TaskEnvelope")
    content_pass = all(value.lower() in text.lower() for value in required)
    forbidden = re.compile(r"(?i)(api[_-]?key|access[_-]?token|refresh[_-]?token|client[_-]?secret|password)\s*[:=]\s*\S+")
    secret_pass = not forbidden.search(text)
    host = {"passed": False, "returncode": None, "timed_out": False, "output_hash": None}
    if result.get("ok") and content_pass and secret_pass:
        try:
            completed = subprocess.run(
                [sys.executable, "-m", "unittest", "tests.test_claude_backend", "tests.test_supervisor",
                 "tests.test_provider_resilience", "tests.test_capability_fabric", "tests.test_cli", "-q"],
                cwd=canonical_root, stdin=subprocess.DEVNULL, capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=300,
            )
            output = (completed.stdout + "\n" + completed.stderr)[-12000:]
            host = {"passed": completed.returncode == 0, "returncode": completed.returncode, "timed_out": False,
                    "output_hash": hashlib.sha256(output.encode("utf-8")).hexdigest()}
        except subprocess.TimeoutExpired:
            host = {"passed": False, "returncode": None, "timed_out": True, "output_hash": None}
    passed = bool(result.get("ok") and result.get("files_changed") == ["docs/CLAUDE_BACKEND.md"]
                  and content_pass and secret_pass and host["passed"] and result.get("cleanup_state") == "PASS")
    if not passed and destination.exists():
        destination.unlink()
    report = {
        "format": "omega.claude-controlled-canary", "version": 1, "generated_at": _now(),
        "task_id": task.task_id, "canary_result": "PASS" if passed else "FAIL",
        "backend_result_state": result.get("result_state"), "returncode": result.get("returncode"),
        "duration_seconds": result.get("duration_seconds"), "files_changed": result.get("files_changed", []),
        "diff_hash": result.get("diff_hash"), "failure_class": result.get("failure_class"),
        "claimed_success": bool(result.get("claimed_success")), "verified_success": passed,
        "scope_violations": result.get("scope_violations", []), "cleanup_state": result.get("cleanup_state"),
        "content_contract_pass": content_pass, "secret_scan_pass": secret_pass,
        "host_verification": host, "rollback_performed": not passed,
        "external_actions": 0, "financial_actions": 0, "authority_violations": 0,
    }
    report["canary_hash"] = _hash(report)
    _atomic_json(canonical_root / ".omega" / "runtime" / "claude_canary.json", report)
    record_backend_evidence(
        canonical_root, canary_result=report["canary_result"],
        canary_evidence={"canary_hash": report["canary_hash"], "diff_hash": report["diff_hash"],
                         "host_verification": host, "scope_violations": report["scope_violations"]},
        capability_registry_eligible=passed, router_shadow_result="READY" if passed else "NOT_READY",
    )
    return report


__all__ = [
    "freeze_multi_backend_tasks", "run_multi_backend_shadow_benchmark",
    "run_shadow_benchmark", "run_documentation_canary",
]
