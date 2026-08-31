"""Provider-neutral durable task continuity for ZERO/OMEGA.

The module owns task/session/checkpoint truth.  Supervisors and providers emit
lifecycle facts through :class:`ContinuityEngine`; they do not implement retry,
ownership, rehydration, or authority-replay policy themselves.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import threading
import time
import uuid
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TERMINAL_AUTHORITY = {"CONSUMED_CLOSED", "EXPIRED", "REVOKED"}
REHYDRATABLE_BLOCKERS = {"SESSION_EXPIRED", "PROCESS_EXITED", "TRANSIENT_NETWORK"}
BLOCKER_STRATEGIES = {
    "SESSION_EXPIRED": "REHYDRATE_BOUNDED",
    "PROCESS_EXITED": "REHYDRATE_BOUNDED",
    "TRANSIENT_NETWORK": "REHYDRATE_BOUNDED",
    "AUTH_REQUIRED": "WAIT_AUTH",
    "USAGE_QUOTA_LIMIT": "WAITING_RESOURCE",
    "AUTHORITY_BLOCKED": "WAIT_AUTHORITY",
    "FINANCIAL_UNCERTAIN": "RECONCILIATION_REQUIRED",
    "REPOSITORY_CHANGED": "RECONCILIATION_REQUIRED",
    "CHECKPOINT_CORRUPT": "RECONCILIATION_REQUIRED",
    "REAL_WORK_PREEMPTION": "WAIT_REAL_WORK_COMPLETION",
}


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _sealed(value: dict[str, Any]) -> dict[str, Any]:
    value = dict(value)
    value.pop("integrity_hash", None)
    value["integrity_hash"] = _hash(value)
    return value


def _verify(value: dict[str, Any]) -> bool:
    expected = value.get("integrity_hash")
    check = dict(value)
    check.pop("integrity_hash", None)
    return isinstance(expected, str) and expected == _hash(check)


class ContinuityError(RuntimeError):
    """Base fail-closed continuity error."""


class IntegrityError(ContinuityError):
    """Stored continuity evidence is truncated, malformed, or hash-mismatched."""


class OwnershipError(ContinuityError):
    """A session attempted to mutate a task it does not own."""


class ReconciliationError(ContinuityError):
    """Durable intent no longer matches repository or authority truth."""


@dataclass
class DurableTask:
    task_id: str
    task_class: str
    objective_hash: str
    state: str = "TASK_ACCEPTED"
    backend: str | None = None
    transport: str | None = None
    upstream_provider: str | None = None
    active_session_id: str | None = None
    last_checkpoint_id: str | None = None
    session_lineage: list[str] = field(default_factory=list)
    session_restart_count: int = 0
    backend_switch_count: int = 0
    provider_retry_count: int = 0
    max_session_restarts: int = 2
    max_backend_switches: int = 1
    max_provider_retries: int = 1
    blocker_class: str | None = None
    recovery_state: str = "NOT_REQUIRED"
    next_trigger: str | None = None
    authority_envelope_id: str | None = None
    authority_status: str = "ACTIVE"
    host_verification: str = "NOT_RUN"
    completed_steps: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    revision: int = 0
    integrity_hash: str = ""


@dataclass
class Checkpoint:
    checkpoint_id: str
    task_id: str
    sequence: int
    session_id: str
    completed_steps: list[str]
    next_action: str
    repository_state: dict[str, Any]
    expected_diff: dict[str, str]
    authority_envelope_id: str | None
    authority_status: str
    created_at: str = field(default_factory=_now)
    integrity_hash: str = ""


@dataclass
class SessionRecord:
    session_id: str
    task_id: str
    backend: str
    transport: str | None = None
    upstream_provider: str | None = None
    provider_session_id: str | None = None
    pid: int | None = None
    state: str = "SESSION_STARTED"
    started_at: str = field(default_factory=_now)
    ended_at: str | None = None
    blocker_class: str | None = None
    integrity_hash: str = ""


@dataclass
class RehydrationPacket:
    packet_id: str
    task_id: str
    mission: str
    last_verified_state: str
    current_phase: str
    completed: list[str]
    current_step: str
    current_blocker: str | None
    next_atomic_action: str
    verified_results: dict[str, Any]
    failed_attempts: list[str]
    files_or_artifacts_used: list[str]
    important_hashes: dict[str, str]
    authority: dict[str, Any]
    resource_blockers: list[str]
    do_not_repeat: list[str]
    open_questions: list[str]
    success_criteria: list[str]
    evidence: dict[str, Any]
    expected_final_state: str
    created_at: str = field(default_factory=_now)
    integrity_hash: str = ""


def classify_blocker(value: str | None) -> str:
    text = (value or "").upper()
    for blocker in BLOCKER_STRATEGIES:
        if blocker in text:
            return blocker
    if any(token in text for token in ("AUTH", "LOGIN", "CREDENTIAL")):
        return "AUTH_REQUIRED"
    if any(token in text for token in ("QUOTA", "USAGE LIMIT", "CREDIT BALANCE")):
        return "USAGE_QUOTA_LIMIT"
    if any(token in text for token in ("NETWORK", "CONNECTION", "DNS")):
        return "TRANSIENT_NETWORK"
    if any(token in text for token in ("EXIT", "CRASH", "CANCEL")):
        return "PROCESS_EXITED"
    return "UNKNOWN_BLOCKER"


def recovery_strategy(blocker: str) -> str:
    return BLOCKER_STRATEGIES.get(blocker, "PARK")


def _git(root: Path, *args: str) -> str | None:
    try:
        completed = subprocess.run(
            ["git", *args], cwd=root, stdin=subprocess.DEVNULL,
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=3,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return completed.stdout.strip() if completed.returncode == 0 else None


def repository_state(root: Path) -> dict[str, Any]:
    root = Path(root).resolve()
    commit = _git(root, "rev-parse", "HEAD")
    status = _git(root, "status", "--porcelain=v1", "-z")
    excluded = {".git", ".omega", "__pycache__", ".pytest_cache", ".venv", "node_modules"}
    workspace: list[tuple[str, int, int]] = []
    try:
        for path in root.rglob("*"):
            relative = path.relative_to(root)
            if not path.is_file() or any(part in excluded for part in relative.parts):
                continue
            stat = path.stat()
            workspace.append((relative.as_posix(), stat.st_size, stat.st_mtime_ns))
    except OSError:
        workspace = []
    return {
        "root": str(root),
        "commit": commit,
        "dirty_hash": _hash(status) if status is not None else None,
        "workspace_hash": _hash(sorted(workspace)),
        "git_available": commit is not None or status is not None,
    }


def verify_rehydration(checkpoint: Checkpoint, root: Path, *,
                       authority_envelope_id: str | None,
                       authority_status: str) -> dict[str, Any]:
    if authority_status in TERMINAL_AUTHORITY:
        return {"ok": False, "reason": "AUTHORITY_TERMINAL_NO_REPLAY"}
    if checkpoint.authority_status in TERMINAL_AUTHORITY:
        return {"ok": False, "reason": "CHECKPOINT_AUTHORITY_ALREADY_TERMINAL"}
    if checkpoint.authority_envelope_id != authority_envelope_id:
        return {"ok": False, "reason": "AUTHORITY_ENVELOPE_MISMATCH"}
    current = repository_state(root)
    frozen = checkpoint.repository_state
    if current.get("root") != frozen.get("root"):
        return {"ok": False, "reason": "REPOSITORY_ROOT_MISMATCH", "current": current}
    if current.get("commit") != frozen.get("commit"):
        return {"ok": False, "reason": "REPOSITORY_COMMIT_MISMATCH", "current": current}
    if current.get("dirty_hash") != frozen.get("dirty_hash"):
        return {"ok": False, "reason": "REPOSITORY_DIRTY_STATE_MISMATCH", "current": current}
    if current.get("workspace_hash") != frozen.get("workspace_hash"):
        return {"ok": False, "reason": "REPOSITORY_WORKSPACE_MISMATCH", "current": current}
    return {"ok": True, "reason": "MATCH", "current": current}


class TaskContinuityStore:
    """Atomic, hash-sealed local store with bounded single-writer file locks."""

    def __init__(self, root: Path):
        self.root = Path(root).resolve()
        self.tasks = self.root / "tasks"
        self.sessions = self.root / "sessions"
        self.checkpoints = self.root / "checkpoints"
        self.rehydration = self.root / "rehydration"
        for path in (self.tasks, self.sessions, self.checkpoints, self.rehydration):
            path.mkdir(parents=True, exist_ok=True)
        self.events = self.root / "events.jsonl"
        self._lock = threading.RLock()

    @contextmanager
    def _process_lock(self, name: str, timeout: float = 5.0):
        """Crash-released OS lock; no stale lockfile ownership is trusted."""
        path = self.root / f".{name}.lock"
        path.parent.mkdir(parents=True, exist_ok=True)
        handle = path.open("a+b")
        if handle.tell() == 0:
            handle.write(b"0")
            handle.flush()
        deadline = time.monotonic() + timeout
        locked = False
        try:
            while not locked:
                try:
                    handle.seek(0)
                    if os.name == "nt":
                        import msvcrt
                        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                    else:
                        import fcntl
                        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    locked = True
                except (OSError, BlockingIOError):
                    if time.monotonic() >= deadline:
                        raise OwnershipError("bounded continuity store lock timeout")
                    time.sleep(0.01)
            yield
        finally:
            if locked:
                try:
                    handle.seek(0)
                    if os.name == "nt":
                        import msvcrt
                        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                    else:
                        import fcntl
                        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
                except OSError:
                    pass
            handle.close()

    def _atomic_write(self, path: Path, value: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_name(path.name + f".{os.getpid()}.{uuid.uuid4().hex}.tmp")
        data = json.dumps(_sealed(value), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        try:
            with temp.open("x", encoding="utf-8") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            temp.replace(path)
        finally:
            temp.unlink(missing_ok=True)

    @staticmethod
    def _read(path: Path) -> dict[str, Any]:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise IntegrityError(f"invalid continuity record: {path.name}") from exc
        if not isinstance(value, dict) or not _verify(value):
            raise IntegrityError(f"continuity hash mismatch: {path.name}")
        return value

    def save_task(self, task: DurableTask, *, expected_revision: int | None = None) -> DurableTask:
        with self._lock, self._process_lock("tasks"):
            path = self.tasks / f"{task.task_id}.json"
            if path.exists() and expected_revision is not None:
                current = self._read(path)
                if int(current.get("revision", -1)) != expected_revision:
                    raise OwnershipError("task compare-and-set revision mismatch")
            task.updated_at = _now()
            task.revision += 1
            value = asdict(task)
            value.pop("integrity_hash", None)
            self._atomic_write(path, value)
            return self.load_task(task.task_id)

    def load_task(self, task_id: str) -> DurableTask:
        value = self._read(self.tasks / f"{task_id}.json")
        return DurableTask(**value)

    def maybe_task(self, task_id: str) -> DurableTask | None:
        path = self.tasks / f"{task_id}.json"
        return self.load_task(task_id) if path.exists() else None

    def save_session(self, session: SessionRecord) -> SessionRecord:
        value = asdict(session)
        value.pop("integrity_hash", None)
        with self._lock, self._process_lock("sessions"):
            self._atomic_write(self.sessions / f"{session.session_id}.json", value)
        return self.load_session(session.session_id)

    def load_session(self, session_id: str) -> SessionRecord:
        return SessionRecord(**self._read(self.sessions / f"{session_id}.json"))

    def save_checkpoint(self, checkpoint: Checkpoint) -> Checkpoint:
        value = asdict(checkpoint)
        value.pop("integrity_hash", None)
        with self._lock, self._process_lock("checkpoints"):
            self._atomic_write(self.checkpoints / f"{checkpoint.checkpoint_id}.json", value)
        return self.load_checkpoint(checkpoint.checkpoint_id)

    def load_checkpoint(self, checkpoint_id: str) -> Checkpoint:
        return Checkpoint(**self._read(self.checkpoints / f"{checkpoint_id}.json"))

    def save_rehydration(self, packet: RehydrationPacket) -> RehydrationPacket:
        value = asdict(packet)
        value.pop("integrity_hash", None)
        with self._lock, self._process_lock("rehydration"):
            self._atomic_write(self.rehydration / f"{packet.task_id}.{packet.packet_id}.json", value)
        return self.load_rehydration(packet.task_id, packet.packet_id)

    def load_rehydration(self, task_id: str, packet_id: str) -> RehydrationPacket:
        return RehydrationPacket(**self._read(self.rehydration / f"{task_id}.{packet_id}.json"))

    def latest_rehydration(self, task_id: str) -> RehydrationPacket | None:
        candidates = sorted(self.rehydration.glob(f"{task_id}.*.json"),
                            key=lambda path: path.stat().st_mtime_ns, reverse=True)
        if not candidates:
            return None
        value = self._read(candidates[0])
        return RehydrationPacket(**value)

    def event(self, kind: str, **data: Any) -> None:
        record = {"timestamp": _now(), "event": kind, **data}
        with self._lock, self.events.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
            handle.flush()


class ContinuityEngine:
    def __init__(self, store: TaskContinuityStore):
        self.store = store

    def accept(self, task_id: str, task_class: str, objective: str, *,
               authority_envelope_id: str | None = None,
               authority_status: str = "ACTIVE") -> DurableTask:
        existing = self.store.maybe_task(task_id)
        objective_hash = _hash(objective)
        if existing:
            if existing.objective_hash != objective_hash:
                raise ReconciliationError("task objective changed under the same durable task id")
            return existing
        task = DurableTask(task_id=task_id, task_class=task_class, objective_hash=objective_hash,
                           authority_envelope_id=authority_envelope_id,
                           authority_status=authority_status)
        task = self.store.save_task(task)
        self.store.event("TASK_ACCEPTED", task_id=task_id)
        return task

    def route(self, task_id: str, backend: str, *, transport: str | None = None,
              upstream_provider: str | None = None) -> DurableTask:
        task = self.store.load_task(task_id)
        if task.state == "PARKED" and task.backend == backend:
            raise ContinuityError("same blocked route requires a material wake before retry")
        if task.backend and task.backend != backend:
            if task.backend_switch_count >= task.max_backend_switches:
                task.state = "PARKED"
                task.recovery_state = "BACKEND_SWITCH_LIMIT"
                return self.store.save_task(task, expected_revision=task.revision)
            task.backend_switch_count += 1
        task.backend, task.transport, task.upstream_provider = backend, transport, upstream_provider
        task.state = "BACKEND_ROUTED"
        task = self.store.save_task(task, expected_revision=task.revision)
        self.store.event("BACKEND_ROUTED", task_id=task_id, backend=backend,
                         transport=transport, upstream_provider=upstream_provider)
        return task

    def start_session(self, task_id: str, backend: str, *, session_id: str | None = None,
                      transport: str | None = None, upstream_provider: str | None = None,
                      provider_session_id: str | None = None, pid: int | None = None) -> SessionRecord:
        task = self.store.load_task(task_id)
        if task.state == "PARKED":
            raise ContinuityError("parked task requires a material wake or route change")
        if task.active_session_id:
            active = self.store.load_session(task.active_session_id)
            if active.state in {"SESSION_STARTED", "TASK_RESUMED", "SESSION_REHYDRATED"}:
                raise OwnershipError("one mutating session already owns this task")
        if task.session_lineage and task.session_restart_count >= task.max_session_restarts:
            task.state, task.recovery_state = "PARKED", "SESSION_RESTART_LIMIT"
            self.store.save_task(task, expected_revision=task.revision)
            raise ContinuityError("session restart limit reached")
        session_id = session_id or str(uuid.uuid4())
        session = SessionRecord(session_id=session_id, task_id=task_id, backend=backend,
                                transport=transport, upstream_provider=upstream_provider,
                                provider_session_id=provider_session_id, pid=pid)
        self.store.save_session(session)
        task.active_session_id = session_id
        task.backend, task.transport, task.upstream_provider = backend, transport, upstream_provider
        if task.session_lineage:
            task.session_restart_count += 1
        task.session_lineage.append(session_id)
        task.state, task.recovery_state = "SESSION_STARTED", "ACTIVE"
        self.store.save_task(task, expected_revision=task.revision)
        self.store.event("SESSION_STARTED", task_id=task_id, session_id=session_id,
                         backend=backend, transport=transport)
        return self.store.load_session(session_id)

    def bind_provider_session(self, task_id: str, session_id: str, *,
                              provider_session_id: str | None, pid: int | None) -> SessionRecord:
        task = self.store.load_task(task_id)
        if task.active_session_id != session_id:
            raise OwnershipError("stale session cannot bind provider identity")
        session = self.store.load_session(session_id)
        session.provider_session_id, session.pid = provider_session_id, pid
        return self.store.save_session(session)

    def checkpoint(self, task_id: str, session_id: str, *, completed_steps: list[str],
                   next_action: str, repository_root: Path,
                   expected_diff: dict[str, str] | None = None) -> Checkpoint:
        task = self.store.load_task(task_id)
        if task.active_session_id != session_id:
            raise OwnershipError("stale session cannot checkpoint")
        if task.authority_status in TERMINAL_AUTHORITY:
            raise ReconciliationError("terminal authority cannot be checkpointed for replay")
        checkpoint = Checkpoint(
            checkpoint_id=str(uuid.uuid4()), task_id=task_id,
            sequence=len(task.completed_steps) + 1, session_id=session_id,
            completed_steps=list(dict.fromkeys(completed_steps)), next_action=next_action,
            repository_state=repository_state(repository_root), expected_diff=expected_diff or {},
            authority_envelope_id=task.authority_envelope_id,
            authority_status=task.authority_status,
        )
        checkpoint = self.store.save_checkpoint(checkpoint)
        task.last_checkpoint_id = checkpoint.checkpoint_id
        task.completed_steps = checkpoint.completed_steps
        task.state = "CHECKPOINT_CREATED"
        self.store.save_task(task, expected_revision=task.revision)
        self.store.event("CHECKPOINT_CREATED", task_id=task_id, session_id=session_id,
                         checkpoint_id=checkpoint.checkpoint_id, next_action=next_action)
        return checkpoint

    def lose_session(self, task_id: str, session_id: str, blocker: str) -> DurableTask:
        task = self.store.load_task(task_id)
        if task.active_session_id != session_id:
            raise OwnershipError("stale session cannot alter current ownership")
        blocker = classify_blocker(blocker)
        session = self.store.load_session(session_id)
        session.state, session.ended_at, session.blocker_class = "SESSION_LOST", _now(), blocker
        self.store.save_session(session)
        task.active_session_id = None
        task.blocker_class = blocker
        task.recovery_state = recovery_strategy(blocker)
        task.next_trigger = task.recovery_state
        task.state = "SESSION_LOST" if blocker in REHYDRATABLE_BLOCKERS else "PARKED"
        task = self.store.save_task(task, expected_revision=task.revision)
        self.store.event("SESSION_LOST", task_id=task_id, session_id=session_id)
        self.store.event("BLOCKER_CLASSIFIED", task_id=task_id, blocker=blocker,
                         recovery_strategy=task.recovery_state)
        return task

    def preempt(self, task_id: str, session_id: str) -> DurableTask:
        """Park lower-priority work after its latest durable checkpoint.

        This is deliberately narrower than generic blocker handling: only the
        owning session may preempt, and a checkpoint must already exist.  A
        later resume requires an explicit material-wake token.
        """
        task = self.store.load_task(task_id)
        if task.active_session_id != session_id:
            raise OwnershipError("stale session cannot preempt current work")
        if not task.last_checkpoint_id:
            raise ReconciliationError("preemption requires a durable checkpoint")
        session = self.store.load_session(session_id)
        session.state, session.ended_at = "CHECKPOINTED_PREEMPTED", _now()
        session.blocker_class = "REAL_WORK_PREEMPTION"
        self.store.save_session(session)
        task.active_session_id = None
        task.blocker_class = "REAL_WORK_PREEMPTION"
        task.recovery_state = "WAIT_REAL_WORK_COMPLETION"
        task.next_trigger = "REAL_WORK_COMPLETED"
        task.state = "PARKED"
        task = self.store.save_task(task, expected_revision=task.revision)
        self.store.event("TASK_PREEMPTED", task_id=task_id, session_id=session_id,
                         checkpoint_id=task.last_checkpoint_id)
        return task

    def material_wake(self, task_id: str, trigger: str) -> DurableTask:
        """Release a preempted task only after the exact material wake."""
        task = self.store.load_task(task_id)
        if task.state != "PARKED" or task.blocker_class != "REAL_WORK_PREEMPTION":
            raise ContinuityError("task is not parked by real-work preemption")
        if trigger != task.next_trigger or trigger != "REAL_WORK_COMPLETED":
            raise ReconciliationError("material wake does not match parked task")
        task.state = "BACKEND_ROUTED" if task.backend else "TASK_ACCEPTED"
        task.blocker_class = None
        task.recovery_state = "RESUME_READY"
        task.next_trigger = None
        task = self.store.save_task(task, expected_revision=task.revision)
        self.store.event("MATERIAL_WAKE_ACCEPTED", task_id=task_id, trigger=trigger)
        return task

    def rehydrate(self, task_id: str, session_id: str, repository_root: Path, *,
                  authority_envelope_id: str | None, authority_status: str) -> Checkpoint:
        task = self.store.load_task(task_id)
        if task.active_session_id != session_id:
            raise OwnershipError("replacement session does not own task")
        if not task.last_checkpoint_id:
            raise ReconciliationError("no durable checkpoint exists")
        checkpoint = self.store.load_checkpoint(task.last_checkpoint_id)
        verdict = verify_rehydration(checkpoint, repository_root,
                                     authority_envelope_id=authority_envelope_id,
                                     authority_status=authority_status)
        if not verdict["ok"]:
            task.state, task.recovery_state = "RECONCILIATION_REQUIRED", verdict["reason"]
            task.active_session_id = None
            self.store.save_task(task, expected_revision=task.revision)
            raise ReconciliationError(verdict["reason"])
        session = self.store.load_session(session_id)
        session.state = "SESSION_REHYDRATED"
        self.store.save_session(session)
        task.state, task.recovery_state, task.blocker_class = "SESSION_REHYDRATED", "RESUMED", None
        self.store.save_task(task, expected_revision=task.revision)
        self.store.event("SESSION_REHYDRATED", task_id=task_id, session_id=session_id,
                         checkpoint_id=checkpoint.checkpoint_id)
        return checkpoint

    def resume(self, task_id: str, session_id: str) -> DurableTask:
        task = self.store.load_task(task_id)
        if task.active_session_id != session_id:
            raise OwnershipError("stale session cannot resume task")
        session = self.store.load_session(session_id)
        session.state = "TASK_RESUMED"
        self.store.save_session(session)
        task.state = "TASK_RESUMED"
        task = self.store.save_task(task, expected_revision=task.revision)
        self.store.event("TASK_RESUMED", task_id=task_id, session_id=session_id)
        return task

    def host_verified(self, task_id: str, session_id: str, passed: bool) -> DurableTask:
        task = self.store.load_task(task_id)
        if task.active_session_id != session_id:
            raise OwnershipError("stale session cannot attach Host Verification")
        task.host_verification = "PASS" if passed else "FAIL"
        task.state = "HOST_VERIFIED" if passed else "VERIFICATION_FAILED"
        task = self.store.save_task(task, expected_revision=task.revision)
        self.store.event("HOST_VERIFIED" if passed else "HOST_VERIFICATION_FAILED",
                         task_id=task_id, session_id=session_id)
        return task

    def complete(self, task_id: str, session_id: str) -> DurableTask:
        task = self.store.load_task(task_id)
        if task.active_session_id != session_id:
            raise OwnershipError("stale session cannot complete task")
        if task.host_verification != "PASS":
            raise ContinuityError("Host Verification must pass before task completion")
        session = self.store.load_session(session_id)
        session.state, session.ended_at = "TASK_COMPLETED", _now()
        self.store.save_session(session)
        task.active_session_id = None
        task.state, task.recovery_state, task.next_trigger = "TASK_COMPLETED", "COMPLETE", None
        task = self.store.save_task(task, expected_revision=task.revision)
        self.store.event("TASK_COMPLETED", task_id=task_id, session_id=session_id)
        return task

    def status(self, task_id: str) -> dict[str, Any]:
        task = self.store.load_task(task_id)
        checkpoint = self.store.load_checkpoint(task.last_checkpoint_id) if task.last_checkpoint_id else None
        next_action = None if task.state == "TASK_COMPLETED" else (checkpoint.next_action if checkpoint else None)
        return {
            "task_id": task.task_id, "task_state": task.state,
            "active_session": task.active_session_id, "backend": task.backend,
            "transport": task.transport, "upstream_provider": task.upstream_provider,
            "last_checkpoint": task.last_checkpoint_id,
            "session_lineage": task.session_lineage,
            "restart_count": task.session_restart_count,
            "blocker": task.blocker_class, "recovery_strategy": task.recovery_state,
            "next_trigger": task.next_trigger,
            "next_action": next_action,
            "host_verification": task.host_verification,
        }

    def freeze_rehydration(self, task_id: str, **fields: Any) -> RehydrationPacket:
        """Persist a bounded Work-session rollover packet for an existing task."""
        task = self.store.load_task(task_id)
        if fields.get("task_id") not in {None, task_id}:
            raise ReconciliationError("rehydration packet task mismatch")
        if task.state == "TASK_COMPLETED" and fields.get("current_phase") != "COMPLETED":
            raise ReconciliationError("completed task cannot be frozen as active")
        packet = RehydrationPacket(
            packet_id=str(uuid.uuid4()), task_id=task_id,
            mission=str(fields["mission"]), last_verified_state=str(fields["last_verified_state"]),
            current_phase=str(fields["current_phase"]), completed=list(fields["completed"]),
            current_step=str(fields["current_step"]), current_blocker=fields.get("current_blocker"),
            next_atomic_action=str(fields["next_atomic_action"]),
            verified_results=dict(fields["verified_results"]),
            failed_attempts=list(fields.get("failed_attempts", [])),
            files_or_artifacts_used=list(fields.get("files_or_artifacts_used", [])),
            important_hashes=dict(fields.get("important_hashes", {})),
            authority=dict(fields["authority"]), resource_blockers=list(fields.get("resource_blockers", [])),
            do_not_repeat=list(fields["do_not_repeat"]), open_questions=list(fields.get("open_questions", [])),
            success_criteria=list(fields["success_criteria"]), evidence=dict(fields["evidence"]),
            expected_final_state=str(fields["expected_final_state"]),
        )
        latest = self.store.latest_rehydration(task_id)
        if latest is not None:
            def semantic(value: RehydrationPacket) -> dict[str, Any]:
                record = asdict(value)
                for key in ("packet_id", "created_at", "integrity_hash"):
                    record.pop(key, None)
                return record
            if semantic(latest) == semantic(packet):
                return latest
        packet = self.store.save_rehydration(packet)
        self.store.event("REHYDRATION_PACKET_FROZEN", task_id=task_id, packet_id=packet.packet_id)
        return packet


def continuity_status(root: Path) -> dict[str, Any]:
    root = Path(root).resolve()
    store_root = root / ".omega" / "runtime" / "task_continuity"
    tasks_root = store_root / "tasks"
    if not tasks_root.exists():
        candidates: list[Path] = []
        store = None
    else:
        store = TaskContinuityStore(store_root)
        candidates = sorted(tasks_root.glob("*.json"), key=lambda path: path.stat().st_mtime_ns,
                            reverse=True)
    if not candidates:
        chaos_path = root / ".omega" / "runtime" / "task_continuity_chaos.json"
        try:
            chaos = json.loads(chaos_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            chaos = None
        return {
            "state": "RUNTIME_PROVEN_NO_ACTIVE_TASK" if isinstance(chaos, dict) and chaos.get("result") == "PASS"
            else "NO_DURABLE_TASK",
            "task": None,
            "live_chaos": {
                "result": chaos.get("result"), "task_id": chaos.get("task_id"),
                "old_session_id": chaos.get("old_session_id"),
                "new_session_id": chaos.get("new_session_id"),
                "host_verification": (chaos.get("host_verification") or {}).get("passed"),
            } if isinstance(chaos, dict) else None,
        }
    task_id = candidates[0].stem
    try:
        assert store is not None
        return {"state": "AVAILABLE", "task": ContinuityEngine(store).status(task_id)}
    except ContinuityError as exc:
        return {"state": "CORRUPT_FAIL_CLOSED", "task_id": task_id,
                "error": type(exc).__name__}


__all__ = [
    "DurableTask", "Checkpoint", "SessionRecord", "RehydrationPacket", "TaskContinuityStore",
    "ContinuityEngine", "ContinuityError", "IntegrityError", "OwnershipError",
    "ReconciliationError", "classify_blocker", "recovery_strategy",
    "repository_state", "verify_rehydration",
    "continuity_status",
]
