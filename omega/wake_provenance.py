"""Trusted, read-only provenance journals for Wake Plane source detectors.

This module intentionally separates source observation from wake decisions.  A
plain JSON document cannot assert that it came from an independent actor.  The
only production observations constructed here are derived from read-only
responses returned by the configured source adapter.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import time
from typing import Any, Callable, Iterable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


SCHEMA_VERSION = "omega.wake-provenance.v1"
GITHUB_REPOSITORY = "mrmohamedhassan2017-blip/agent-runtime-audit"
GITHUB_OWNER = "mrmohamedhassan2017-blip"
GITHUB_API = "https://api.github.com"
GITHUB_MIN_POLL_SECONDS = 300
V030_WORK_ID = "V0.30 External Evaluator Evidence Collection"
GITHUB_WORK_ID = "ZERO-INBOUND-001"
PASSIVE_INTAKE_KIND = "ZRWVE_PASSIVE_INCIDENT_INTAKE"
PASSIVE_INTAKE_TITLE_PREFIX = "[incident-intake]"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso(value: datetime | None = None) -> str:
    return (value or utc_now()).astimezone().isoformat(timespec="seconds")


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def digest(value: Any) -> str:
    raw = value if isinstance(value, bytes) else canonical(value)
    return hashlib.sha256(raw).hexdigest()


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _record_hash(record: dict[str, Any]) -> str:
    return digest({key: value for key, value in record.items()
                   if key != "record_hash"})


def read_chain(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    """Read the valid prefix of an integrity chained JSONL journal.

    A corrupt or partial tail is evidence, not something to silently repair.
    Valid records before the bad tail remain available and no later records are
    trusted until an operator explicitly repairs the journal.
    """
    if not path.exists():
        return [], []
    records: list[dict[str, Any]] = []
    errors: list[str] = []
    previous = "GENESIS"
    for number, line in enumerate(path.read_text(encoding="utf-8",
                                                 errors="replace").splitlines(), 1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            errors.append(f"CORRUPT_RECORD:{number}")
            break
        if not isinstance(record, dict):
            errors.append(f"INVALID_RECORD:{number}")
            break
        if record.get("previous_hash") != previous:
            errors.append(f"CHAIN_BREAK:{number}")
            break
        if record.get("record_hash") != _record_hash(record):
            errors.append(f"HASH_MISMATCH:{number}")
            break
        records.append(record)
        previous = record["record_hash"]
    return records, errors


def append_chain(path: Path, record: dict[str, Any], dedupe_field: str,
                 crash_before_append: bool = False) -> tuple[dict[str, Any], bool]:
    """Durably append once and return ``(record, created)``."""
    records, errors = read_chain(path)
    if errors:
        raise ValueError("journal integrity failure: " + errors[0])
    key = record.get(dedupe_field)
    for existing in records:
        if existing.get(dedupe_field) == key:
            return existing, False
    complete = dict(record)
    complete.setdefault("schema_version", SCHEMA_VERSION)
    complete["previous_hash"] = records[-1]["record_hash"] if records else "GENESIS"
    complete["record_hash"] = _record_hash(complete)
    if crash_before_append:
        raise RuntimeError("SIMULATED_CRASH_BEFORE_APPEND")
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(complete, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")) + "\n"
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(line)
        stream.flush()
        os.fsync(stream.fileno())
    return complete, True


@dataclass(frozen=True)
class TrustedSourceObservation:
    """A source observation made by a read-only adapter, not a user assertion."""

    channel: str
    actor_identifier: str
    actor_id: str
    actor_type: str
    source_event_reference: str
    source_event_id: str
    source_created_at: str
    owner_origin: bool | None
    system_origin: bool | None
    source_verified: bool
    verification_basis: str
    canonical_event_fingerprint: str


EVALUATOR_REQUIRED = {
    "submission_id", "evaluator_session_id", "evaluation_id",
    "payload_sha256", "format", "format_version",
}


def ingest_v030_submission(root: Path, payload: dict[str, Any],
                           observation: TrustedSourceObservation,
                           *, received_at: datetime | None = None) -> dict[str, Any]:
    """Record a V0.30 submission with fail-closed independence classification.

    The payload hash is recomputed.  The payload itself is deliberately not
    stored in this provenance journal.
    """
    if not isinstance(observation, TrustedSourceObservation):
        raise TypeError("trusted source observation required")
    raw_payload = dict(payload) if isinstance(payload, dict) else {}
    payload_hash = digest(raw_payload)
    supplied_hash = str(raw_payload.get("payload_sha256", ""))
    required_ok = (EVALUATOR_REQUIRED.issubset(raw_payload)
                   and raw_payload.get("format") == "omega.blind-evaluation-result"
                   and raw_payload.get("format_version") == 1)
    hash_ok = supplied_hash == payload_hash or supplied_hash == digest({
        key: value for key, value in raw_payload.items() if key != "payload_sha256"
    })
    validation = "VALID" if required_ok and hash_ok and observation.source_verified else "INVALID"
    owner = observation.owner_origin
    system = observation.system_origin
    if validation != "VALID":
        independence = "UNKNOWN"
        basis = "SOURCE_OR_PAYLOAD_NOT_VERIFIED"
    elif owner is True or system is True:
        independence = "PROVEN_NON_INDEPENDENT"
        basis = "OWNER_OR_SYSTEM_ORIGIN"
    elif owner is False and system is False and observation.actor_id:
        independence = "PROVEN_INDEPENDENT"
        basis = observation.verification_basis
    else:
        independence = "UNKNOWN"
        basis = "ACTOR_ORIGIN_NOT_ATTRIBUTABLE"
    actor_hash = digest({"channel": observation.channel,
                         "actor_id": observation.actor_id,
                         "actor_identifier": observation.actor_identifier})
    journal = Path(root) / ".omega" / "wake-provenance" / "v0_30_evaluator_provenance.jsonl"
    existing, errors = read_chain(journal)
    if errors:
        raise ValueError("evaluator journal integrity failure: " + errors[0])
    duplicate_of = None
    for prior in existing:
        if prior.get("submission_id") == raw_payload.get("submission_id"):
            duplicate_of = prior.get("evidence_event_id")
            break
        if (prior.get("source_actor_hash") == actor_hash and
                prior.get("evaluator_session_id") == raw_payload.get("evaluator_session_id")):
            duplicate_of = prior.get("evidence_event_id")
            break
    if duplicate_of:
        independence = "PROVEN_NON_INDEPENDENT"
        basis = "DUPLICATE_SUBMISSION_OR_SESSION"
    event_id = "V030-" + digest({"source": observation.source_event_id,
                                  "submission": raw_payload.get("submission_id", ""),
                                  "payload": payload_hash})[:24]
    record = {
        "evidence_event_id": event_id,
        "submission_id": str(raw_payload.get("submission_id", "")),
        "evaluator_session_id": str(raw_payload.get("evaluator_session_id", "")),
        "received_at": iso(received_at),
        "source_channel": observation.channel,
        "source_actor_identifier": observation.actor_identifier,
        "source_actor_hash": actor_hash,
        "source_event_reference": observation.source_event_reference,
        "source_event_id": observation.source_event_id,
        "canonical_event_fingerprint": observation.canonical_event_fingerprint,
        "payload_hash": payload_hash,
        "observation_hash": digest(asdict(observation)),
        "ingestion_method": "READ_ONLY_SOURCE_ADAPTER",
        "ingested_by": "OMEGA_WAKE_PLANE_HOST",
        "owner_origin": owner if owner is not None else "unknown",
        "system_origin": system if system is not None else "unknown",
        "independence_status": independence,
        "independence_basis": basis,
        "duplicate_of": duplicate_of,
        "validation_status": validation,
        "work_id": V030_WORK_ID,
        "consumed_at": None,
    }
    stored, _ = append_chain(journal, record, "evidence_event_id")
    return stored


def evaluator_summary(root: Path) -> dict[str, Any]:
    path = Path(root) / ".omega" / "wake-provenance" / "v0_30_evaluator_provenance.jsonl"
    records, errors = read_chain(path)
    identities: set[str] = set()
    qualifying: list[dict[str, Any]] = []
    for record in records:
        if (record.get("validation_status") == "VALID" and
                record.get("independence_status") == "PROVEN_INDEPENDENT" and
                not record.get("duplicate_of")):
            identity = str(record.get("source_actor_hash", ""))
            if identity and identity not in identities:
                identities.add(identity)
                qualifying.append(record)
    return {
        "journal_ready": not errors,
        "record_count": len(records),
        "independent_evaluator_count": len(identities),
        "qualifying_records": qualifying,
        "integrity_errors": errors,
    }


@dataclass(frozen=True)
class GithubResponse:
    status: int
    headers: dict[str, str]
    payload: Any


GithubFetcher = Callable[[str, str | None], GithubResponse]


def github_get(url: str, etag: str | None = None) -> GithubResponse:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "OMEGA-Wake-Plane/0.21.0",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if etag:
        headers["If-None-Match"] = etag
    request = Request(url, headers=headers, method="GET")
    try:
        with urlopen(request, timeout=12) as response:  # nosec B310: fixed HTTPS API
            body = response.read(2_000_000)
            payload = json.loads(body.decode("utf-8")) if body else None
            return GithubResponse(response.status,
                                  {key.lower(): value for key, value in response.headers.items()},
                                  payload)
    except HTTPError as exc:
        headers_out = {key.lower(): value for key, value in exc.headers.items()}
        if exc.code == 304:
            return GithubResponse(304, headers_out, None)
        if exc.code in {403, 429}:
            return GithubResponse(exc.code, headers_out, None)
        raise RuntimeError("GITHUB_HTTP_ERROR") from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise RuntimeError("GITHUB_NETWORK_ERROR") from exc


def _parse_time(value: str | None) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else None
    except (TypeError, ValueError):
        return None


def _bot(login: str, actor_type: str) -> bool:
    lowered = login.lower()
    return actor_type.upper() == "BOT" or lowered.endswith("[bot]") or lowered.endswith("-bot")


def _github_record(repository: str, owner_login: str, owner_id: str,
                   item: dict[str, Any], observed_at: datetime) -> tuple[dict[str, Any] | None,
                                                                         TrustedSourceObservation | None]:
    actor = item.get("user")
    if not isinstance(actor, dict):
        return None, None
    login = str(actor.get("login", "")).strip()
    actor_id = str(actor.get("id", "")).strip()
    actor_type = str(actor.get("type", "")).strip()
    event_id = str(item.get("id", "")).strip()
    number = str(item.get("number", "")).strip()
    created = _parse_time(item.get("created_at"))
    url = str(item.get("html_url", "")).strip()
    if not (login and actor_id and event_id and number and created and url.startswith("https://github.com/")):
        return None, None
    event_type = "pull_request" if isinstance(item.get("pull_request"), dict) else "issue"
    title = str(item.get("title", "")).strip()
    submission_kind = (
        PASSIVE_INTAKE_KIND
        if event_type == "issue" and title.casefold().startswith(PASSIVE_INTAKE_TITLE_PREFIX)
        else "GENERAL_GITHUB_INBOUND"
    )
    owner_actor = login.casefold() == owner_login.casefold() or actor_id == owner_id
    bot_actor = _bot(login, actor_type)
    independence = ("PROVEN_NON_INDEPENDENT" if owner_actor or bot_actor
                    else "PROVEN_INDEPENDENT")
    source_event_id = f"github:{repository}:{event_type}:{event_id}"
    fingerprint = digest({"provider": "github", "repository": repository,
                          "event_type": event_type, "event_id": event_id})
    actor_hash = digest({"provider": "github", "actor_id": actor_id, "login": login})
    content_hash = digest({"title": str(item.get("title", "")),
                           "body": str(item.get("body", ""))})
    record = {
        "github_event_id": event_id,
        "source_event_id": source_event_id,
        "canonical_event_fingerprint": fingerprint,
        "event_type": event_type,
        "submission_kind": submission_kind,
        "repository": repository,
        "actor_login": login,
        "actor_id": actor_id,
        "actor_hash": actor_hash,
        "actor_type": actor_type,
        "created_at": created.astimezone().isoformat(timespec="seconds"),
        "observed_at": iso(observed_at),
        "url_reference": url,
        "content_hash": content_hash,
        "owner_actor": owner_actor,
        "bot_actor": bot_actor,
        "independence_status": independence,
        "work_id": GITHUB_WORK_ID,
        "dedupe_key": fingerprint,
        "consumed_at": None,
    }
    observation = TrustedSourceObservation(
        channel="GITHUB_PUBLIC_API",
        actor_identifier=login,
        actor_id=actor_id,
        actor_type=actor_type,
        source_event_reference=url,
        source_event_id=source_event_id,
        source_created_at=record["created_at"],
        owner_origin=owner_actor,
        system_origin=bot_actor,
        source_verified=True,
        verification_basis="GITHUB_PUBLIC_API_IMMUTABLE_ACTOR_ID",
        canonical_event_fingerprint=fingerprint,
    )
    return record, observation


def poll_github(root: Path, fetcher: GithubFetcher | None = None,
                *, current_time: datetime | None = None,
                force: bool = False) -> dict[str, Any]:
    """Poll the designated public repository and durably journal inbound events."""
    root = Path(root)
    now_value = current_time or utc_now()
    base = root / ".omega" / "wake-provenance"
    config = read_json(base / "config.json", {})
    github_config = config.get("github", {}) if isinstance(config, dict) else {}
    if github_config.get("enabled") is not True:
        return {"enabled": False, "health": "DORMANT", "production_ready": False,
                "blocker": "GITHUB_READ_ONLY_DETECTOR_NOT_CONFIGURED", "records": [],
                "new_records": [], "network_requests": 0}
    repository = str(github_config.get("repository", ""))
    owner_login = str(github_config.get("owner_login", ""))
    if repository != GITHUB_REPOSITORY or owner_login.casefold() != GITHUB_OWNER.casefold():
        return {"enabled": True, "health": "BLOCKED", "production_ready": False,
                "blocker": "REPOSITORY_OR_OWNER_MISMATCH", "records": [],
                "new_records": [], "network_requests": 0}
    passive_config = github_config.get("passive_incident_intake", {})
    passive_enabled = bool(
        isinstance(passive_config, dict)
        and passive_config.get("enabled") is True
        and passive_config.get("read_only") is True
    )
    checkpoint_path = base / "github_checkpoint.json"
    journal_path = base / "github_inbound.jsonl"
    checkpoint = read_json(checkpoint_path, {})
    records, integrity_errors = read_chain(journal_path)
    if integrity_errors:
        return {"enabled": True, "health": "BLOCKED", "production_ready": False,
                "blocker": integrity_errors[0], "records": records, "new_records": [],
                "network_requests": 0, "checkpoint": checkpoint}
    last_poll = _parse_time(checkpoint.get("last_successful_poll"))
    if (not force and last_poll and
            now_value.astimezone(timezone.utc) - last_poll.astimezone(timezone.utc) <
            timedelta(seconds=GITHUB_MIN_POLL_SECONDS)):
        return {"enabled": True, "health": "ACTIVE", "production_ready": True,
                "blocker": None, "records": records, "new_records": [],
                "passive_intake_enabled": passive_enabled,
                "passive_candidates": [], "network_requests": 0,
                "checkpoint": checkpoint, "cached": True}
    perform = fetcher or github_get
    requests = 0
    try:
        repo_url = f"{GITHUB_API}/repos/{repository}"
        repo_response = perform(repo_url, checkpoint.get("repo_etag"))
        requests += 1
        if repo_response.status in {403, 429}:
            raise RuntimeError(f"GITHUB_HTTP_{repo_response.status}")
        repo_payload = (repo_response.payload if repo_response.status != 304
                        else checkpoint.get("repository_identity"))
        if not isinstance(repo_payload, dict):
            raise RuntimeError("GITHUB_REPOSITORY_RESPONSE_INVALID")
        remote_owner = repo_payload.get("owner", {})
        remote_owner_login = str(remote_owner.get("login", ""))
        remote_owner_id = str(remote_owner.get("id", ""))
        if (str(repo_payload.get("full_name", "")) != repository or
                remote_owner_login.casefold() != owner_login.casefold() or not remote_owner_id):
            raise RuntimeError("GITHUB_REPOSITORY_IDENTITY_MISMATCH")
        issues_url = f"{GITHUB_API}/repos/{repository}/issues?state=all&sort=created&direction=asc&per_page=100"
        issue_response = perform(issues_url, checkpoint.get("issues_etag"))
        requests += 1
        if issue_response.status in {403, 429}:
            raise RuntimeError(f"GITHUB_HTTP_{issue_response.status}")
        items = [] if issue_response.status == 304 else issue_response.payload
        if not isinstance(items, list):
            raise RuntimeError("GITHUB_ISSUES_RESPONSE_INVALID")
        new_records: list[dict[str, Any]] = []
        passive_candidates: list[dict[str, Any]] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            record, observation = _github_record(repository, owner_login, remote_owner_id,
                                                  item, now_value)
            if not record:
                continue
            stored, created = append_chain(journal_path, record, "source_event_id")
            if created:
                new_records.append(stored)
            if (passive_enabled and observation is not None
                    and record.get("submission_kind") == PASSIVE_INTAKE_KIND):
                # Body/title are transient adapter data. They are never written to
                # the provenance checkpoint or generic GitHub journal.
                updated_at = str(item.get("updated_at") or item.get("created_at") or "")
                revision = digest({
                    "source_event_id": observation.source_event_id,
                    "updated_at": updated_at,
                    "content_hash": record["content_hash"],
                })
                passive_candidates.append({
                    "observation": observation,
                    "source_record": stored,
                    "revision_source_event_id": f"{observation.source_event_id}:revision:{revision[:24]}",
                    "body": str(item.get("body", "")),
                    "updated_at": updated_at,
                })
        records, integrity_errors = read_chain(journal_path)
        rate_remaining = (issue_response.headers.get("x-ratelimit-remaining") or
                          repo_response.headers.get("x-ratelimit-remaining"))
        rate_reset = (issue_response.headers.get("x-ratelimit-reset") or
                      repo_response.headers.get("x-ratelimit-reset"))
        checkpoint = {
            "schema_version": SCHEMA_VERSION,
            "repository": repository,
            "repository_identity": repo_payload,
            "last_successful_poll": iso(now_value),
            "source_cursor": max((str(r.get("github_event_id", "")) for r in records),
                                 default=None),
            "repo_etag": repo_response.headers.get("etag") or checkpoint.get("repo_etag"),
            "issues_etag": issue_response.headers.get("etag") or checkpoint.get("issues_etag"),
            "rate_limit_remaining": int(rate_remaining) if str(rate_remaining).isdigit() else None,
            "rate_limit_reset": rate_reset,
            "next_retry": iso(now_value + timedelta(seconds=GITHUB_MIN_POLL_SECONDS)),
            "last_error_class": None,
            "poll_errors": int(checkpoint.get("poll_errors", 0)),
            "network_requests": int(checkpoint.get("network_requests", 0)) + requests,
        }
        # Do not persist repository body/content; keep only the identity needed
        # to verify owner filtering on 304 responses.
        checkpoint["repository_identity"] = {
            "full_name": repository,
            "owner": {"login": remote_owner_login, "id": remote_owner_id},
        }
        atomic_json(checkpoint_path, checkpoint)
        return {"enabled": True, "health": "ACTIVE", "production_ready": not integrity_errors,
                "blocker": integrity_errors[0] if integrity_errors else None,
                "records": records, "new_records": new_records,
                "passive_intake_enabled": passive_enabled,
                "passive_candidates": passive_candidates,
                "network_requests": requests, "checkpoint": checkpoint, "cached": False}
    except (RuntimeError, ValueError) as exc:
        error_class = str(exc)
        rate_limited = error_class in {"GITHUB_HTTP_403", "GITHUB_HTTP_429"}
        checkpoint.update({
            "schema_version": SCHEMA_VERSION,
            "repository": repository,
            "last_attempt": iso(now_value),
            "last_error_class": "RATE_LIMITED" if rate_limited else error_class,
            "poll_errors": int(checkpoint.get("poll_errors", 0)) + 1,
            "network_requests": int(checkpoint.get("network_requests", 0)) + requests,
            "next_retry": iso(now_value + timedelta(minutes=15 if rate_limited else 5)),
        })
        atomic_json(checkpoint_path, checkpoint)
        return {"enabled": True, "health": "DEGRADED", "production_ready": False,
                "blocker": checkpoint["last_error_class"], "records": records,
                "new_records": [], "passive_intake_enabled": passive_enabled,
                "passive_candidates": [], "network_requests": requests,
                "checkpoint": checkpoint, "cached": False}


def github_qualifying_records(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return [record for record in records
            if record.get("independence_status") == "PROVEN_INDEPENDENT"
            and record.get("owner_actor") is False
            and record.get("bot_actor") is False
            and record.get("submission_kind") != PASSIVE_INTAKE_KIND]
