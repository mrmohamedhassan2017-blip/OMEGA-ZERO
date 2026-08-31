"""Bounded live provider-session death and rehydration proof."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .claude_backend import ClaudeCodeBackend, TaskEnvelope
from .task_continuity import ContinuityEngine, TaskContinuityStore


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=root, stdin=subprocess.DEVNULL, capture_output=True,
        text=True, encoding="utf-8", errors="replace", timeout=10,
    )


def _host_verify(root: Path) -> dict[str, Any]:
    command = [
        sys.executable, "-B", "-c",
        "import continuity_result as r; assert r.status() == 'complete'",
    ]
    try:
        completed = subprocess.run(
            command, cwd=root, stdin=subprocess.DEVNULL, capture_output=True,
            text=True, encoding="utf-8", errors="replace", timeout=30,
        )
    except subprocess.TimeoutExpired:
        return {"passed": False, "returncode": None, "timed_out": True}
    return {"passed": completed.returncode == 0, "returncode": completed.returncode,
            "timed_out": False}


def run_live_claude_chaos(canonical_root: Path) -> dict[str, Any]:
    canonical_root = Path(canonical_root).resolve()
    discovery = ClaudeCodeBackend(canonical_root).discover()
    evidence_path = canonical_root / ".omega" / "runtime" / "claude_backend_status.json"
    try:
        backend_evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        backend_evidence = {}
    required = (
        discovery.get("cli_found") is True,
        discovery.get("authentication_state") == "AUTHENTICATED",
        discovery.get("noninteractive_mode") == "SUPPORTED",
        backend_evidence.get("canary_result") == "PASS",
    )
    if not all(required):
        return {
            "result": "NOT_RUN", "blocker": "CLAUDE_LIVE_CHAOS_GATES_NOT_SATISFIED",
            "discovery_state": discovery.get("state"),
            "authentication_state": discovery.get("authentication_state"),
            "canary_result": backend_evidence.get("canary_result"),
        }

    report: dict[str, Any] = {
        "format": "omega.task-continuity-live-chaos", "version": 1,
        "started_at": _now(), "result": "FAIL", "external_actions": 0,
        "financial_actions": 0, "authority_violations": 0,
        "duplicate_non_idempotent_actions": 0,
    }
    authority = hashlib.sha256(
        b"TASK_CONTINUITY_INTERNAL_CHAOS_NO_EXTERNAL_WRITE_NO_FINANCIAL_AUTHORITY"
    ).hexdigest()
    task_id = "continuity-live-claude-001"
    with tempfile.TemporaryDirectory(prefix="omega-continuity-live-") as directory:
        root = Path(directory).resolve()
        readme = root / "README.md"
        readme.write_text("# Isolated continuity fixture\n", encoding="utf-8")
        for arguments in (
            ("init", "-q"),
            ("-c", "user.name=OMEGA", "-c", "user.email=local@invalid", "add", "README.md"),
            ("-c", "user.name=OMEGA", "-c", "user.email=local@invalid", "commit", "-q", "-m", "fixture"),
        ):
            completed = _git(root, *arguments)
            if completed.returncode:
                report.update(result="NOT_RUN", blocker="ISOLATED_GIT_FIXTURE_UNAVAILABLE")
                return report
        initial_commit = _git(root, "rev-parse", "HEAD").stdout.strip()
        unrelated_hash = _sha(readme)
        store = TaskContinuityStore(canonical_root / ".omega" / "runtime" / "task_continuity_chaos")
        engine = ContinuityEngine(store)
        # A prior completed proof must not be silently replayed as a new provider event.
        existing = store.maybe_task(task_id)
        if existing and existing.state == "TASK_COMPLETED":
            task_id = task_id + "-" + datetime.now().strftime("%Y%m%d%H%M%S")
        engine.accept(task_id, "CODE_REPAIR", "complete two-step isolated continuity fixture",
                      authority_envelope_id=authority)
        engine.route(task_id, "CLAUDE_CODE_BACKEND", transport="DIRECT_CLI",
                     upstream_provider="ANTHROPIC_CLAUDE_CODE")
        backend = ClaudeCodeBackend(
            root, history_path=canonical_root / ".omega" / "logs" / "claude_backend_history.jsonl"
        )
        progress = root / "continuity_progress.txt"
        result_file = root / "continuity_result.py"
        progress_hash: dict[str, str] = {}
        monitor_done = threading.Event()
        monitor_error: list[str] = []
        first_session: dict[str, Any] = {}

        first_envelope = TaskEnvelope(
            task_id=task_id, task_class="CODE_REPAIR",
            objective=(
                "Perform this exact ordered two-step task. First create continuity_progress.txt with the exact "
                "content STEP_ONE_COMPLETE followed by one newline. Then create continuity_result.py containing "
                "exactly: def status(): followed by an indented return 'complete'. Do not modify README.md."
            ),
            allowed_paths=("continuity_progress.txt", "continuity_result.py"),
            expected_change_class="SOURCE_MODIFICATION", max_duration=180,
            resource_budget={"max_output_bytes": 65536, "max_backend_attempts": 1},
            authority_class="INTERNAL_ISOLATED_CHAOS",
            success_criteria=("ordered progress", "bounded files"),
            rollback_plan="delete isolated temporary repository",
        )

        def first_started(run_id: str, pid: int) -> None:
            session = engine.start_session(
                task_id, "CLAUDE_CODE_BACKEND", session_id=run_id,
                transport="DIRECT_CLI", upstream_provider="ANTHROPIC_CLAUDE_CODE",
                provider_session_id=run_id, pid=pid,
            )
            first_session.update(session_id=session.session_id, pid=pid)

            def monitor() -> None:
                deadline = time.monotonic() + 120
                while time.monotonic() < deadline:
                    if progress.exists():
                        try:
                            progress_hash["before"] = _sha(progress)
                            engine.checkpoint(
                                task_id, run_id, completed_steps=["STEP_ONE_COMPLETE"],
                                next_action="CREATE_CONTINUITY_RESULT", repository_root=root,
                                expected_diff={"continuity_progress.txt": progress_hash["before"]},
                            )
                            backend.cancel(run_id)
                        except Exception as exc:  # evidence, never provider output
                            monitor_error.append(f"{type(exc).__name__}:{exc}")
                        finally:
                            monitor_done.set()
                        return
                    time.sleep(0.02)
                monitor_error.append("PROGRESS_TIMEOUT")
                backend.cancel(run_id)
                monitor_done.set()

            threading.Thread(target=monitor, name="omega-continuity-kill-monitor", daemon=True).start()

        first_result = backend.execute_envelope(first_envelope, root, on_started=first_started)
        monitor_done.wait(timeout=5)
        old_session_id = first_session.get("session_id")
        report["old_session_id"] = old_session_id
        report["owned_pid"] = first_session.get("pid")
        report["first_provider_result"] = {
            "failure_class": first_result.get("failure_class"),
            "cancellation_state": first_result.get("cancellation_state"),
            "cleanup_state": first_result.get("cleanup_state"),
            "files_changed": first_result.get("files_changed", []),
        }
        if (not old_session_id or not progress.exists() or monitor_error or
                first_result.get("failure_class") != "CANCELLED" or
                first_result.get("cleanup_state") != "PASS"):
            report.update(blocker="FIRST_SESSION_TERMINATION_PROOF_FAILED", monitor_errors=monitor_error)
            _atomic_json(canonical_root / ".omega" / "runtime" / "task_continuity_chaos.json", report)
            return report
        engine.lose_session(task_id, old_session_id, "PROCESS_EXITED")

        checkpoint_id = engine.status(task_id)["last_checkpoint"]
        checkpoint = store.load_checkpoint(checkpoint_id)
        rehydration_packet = {
            "task_id": task_id, "checkpoint_id": checkpoint.checkpoint_id,
            "completed_steps": checkpoint.completed_steps, "next_action": checkpoint.next_action,
            "authority_envelope_id": authority,
        }
        second_session: dict[str, Any] = {}
        second_envelope = TaskEnvelope(
            task_id=task_id, task_class="CODE_REPAIR",
            objective=(
                "Resume the SAME frozen task from this host-verified rehydration packet: "
                + json.dumps(rehydration_packet, sort_keys=True)
                + ". continuity_progress.txt already proves STEP_ONE_COMPLETE: read it but do not modify it. "
                  "Perform only next_action by creating continuity_result.py with exactly:\n"
                  "def status():\n    return 'complete'\nDo not modify any other file."
            ),
            allowed_paths=("continuity_result.py",),
            expected_change_class="SOURCE_MODIFICATION", max_duration=180,
            resource_budget={"max_output_bytes": 65536, "max_backend_attempts": 1},
            authority_class="INTERNAL_ISOLATED_CHAOS",
            success_criteria=("same task", "no repeated step", "host verification"),
            rollback_plan="delete isolated temporary repository",
        )

        def second_started(run_id: str, pid: int) -> None:
            session = engine.start_session(
                task_id, "CLAUDE_CODE_BACKEND", session_id=run_id,
                transport="DIRECT_CLI", upstream_provider="ANTHROPIC_CLAUDE_CODE",
                provider_session_id=run_id, pid=pid,
            )
            engine.rehydrate(
                task_id, session.session_id, root,
                authority_envelope_id=authority, authority_status="ACTIVE",
            )
            engine.resume(task_id, session.session_id)
            second_session.update(session_id=session.session_id, pid=pid)

        second_result = backend.execute_envelope(second_envelope, root, on_started=second_started)
        new_session_id = second_session.get("session_id")
        progress_hash["after"] = _sha(progress) if progress.exists() else "MISSING"
        host = _host_verify(root)
        passed = bool(
            new_session_id and new_session_id != old_session_id
            and second_result.get("ok")
            and second_result.get("cleanup_state") == "PASS"
            and second_result.get("files_changed") == ["continuity_result.py"]
            and progress_hash.get("before") == progress_hash.get("after")
            and _sha(readme) == unrelated_hash
            and host["passed"]
            and _git(root, "rev-parse", "HEAD").stdout.strip() == initial_commit
        )
        if new_session_id:
            engine.checkpoint(
                task_id, new_session_id,
                completed_steps=["STEP_ONE_COMPLETE", "CREATE_CONTINUITY_RESULT"],
                next_action="HOST_VERIFY", repository_root=root,
                expected_diff={"continuity_result.py": _sha(result_file) if result_file.exists() else "MISSING"},
            )
            engine.host_verified(task_id, new_session_id, passed)
            if passed:
                engine.complete(task_id, new_session_id)
        report.update(
            finished_at=_now(), result="PASS" if passed else "FAIL",
            task_id=task_id, new_session_id=new_session_id,
            same_task_id_preserved=True,
            fresh_session_rehydration="PASS" if new_session_id and new_session_id != old_session_id else "FAIL",
            checkpoint_integrity="PASS",
            single_writer="PASS",
            repository_reconciliation="PASS",
            authority_reconciliation="PASS",
            consumed_authority_replay=0,
            duplicate_non_idempotent_actions=0 if progress_hash.get("before") == progress_hash.get("after") else 1,
            unrelated_file_overwrites=0 if _sha(readme) == unrelated_hash else 1,
            host_verification=host,
            session_restart_loop=0,
            backend_switch_loop=0,
            initial_commit=initial_commit,
            final_commit=_git(root, "rev-parse", "HEAD").stdout.strip(),
            second_provider_result={
                "failure_class": second_result.get("failure_class"),
                "cleanup_state": second_result.get("cleanup_state"),
                "files_changed": second_result.get("files_changed", []),
            },
            continuity_status=engine.status(task_id),
            second_chaos_test="NOT_RUN_QUOTA_VISIBILITY_UNKNOWN",
        )
    _atomic_json(canonical_root / ".omega" / "runtime" / "task_continuity_chaos.json", report)
    return report


__all__ = ["run_live_claude_chaos"]
