from __future__ import annotations

import base64
import ctypes
import hashlib
import http.server
import json
import os
import secrets
import socket
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from email.message import EmailMessage
from email.utils import format_datetime, make_msgid
from ctypes import wintypes
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


GMAIL_ACCOUNT = "omega.agent.runtime@gmail.com"
GMAIL_SCOPES = (
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
)
PROFILE_URL = "https://gmail.googleapis.com/gmail/v1/users/me/profile"
FROZEN_MESSAGE_SHA256 = "cf4dc2ae69945e079ac2c006b6eb5af12b86da09a4b84b4064cd5121dcbf2a4a"


def gmail_config_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    if not base:
        raise RuntimeError("LOCALAPPDATA is unavailable; refusing to place OAuth material in the repository")
    return Path(base) / "OMEGA" / "gmail"


def oauth_client_path() -> Path:
    override = os.environ.get("OMEGA_GMAIL_OAUTH_CLIENT_FILE")
    return Path(override).expanduser().resolve() if override else gmail_config_dir() / "oauth-client.json"


class _Blob(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]


def _blob(data: bytes) -> tuple[_Blob, Any]:
    buffer = ctypes.create_string_buffer(data)
    return _Blob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char))), buffer


def dpapi_protect(data: bytes) -> bytes:
    if os.name != "nt":
        raise RuntimeError("Gmail token encryption requires Windows DPAPI")
    incoming, keepalive = _blob(data)
    outgoing = _Blob()
    crypt32 = ctypes.windll.crypt32
    if not crypt32.CryptProtectData(ctypes.byref(incoming), "OMEGA Gmail OAuth", None, None, None, 1, ctypes.byref(outgoing)):
        raise ctypes.WinError()
    try:
        return ctypes.string_at(outgoing.pbData, outgoing.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(outgoing.pbData)


def dpapi_unprotect(data: bytes) -> bytes:
    if os.name != "nt":
        raise RuntimeError("Gmail token decryption requires Windows DPAPI")
    incoming, keepalive = _blob(data)
    outgoing = _Blob()
    if not ctypes.windll.crypt32.CryptUnprotectData(ctypes.byref(incoming), None, None, None, None, 1, ctypes.byref(outgoing)):
        raise ctypes.WinError()
    try:
        return ctypes.string_at(outgoing.pbData, outgoing.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(outgoing.pbData)


class DPAPITokenStore:
    def __init__(self, path: Path | None = None, protect: Callable[[bytes], bytes] = dpapi_protect,
                 unprotect: Callable[[bytes], bytes] = dpapi_unprotect) -> None:
        self.path = path or gmail_config_dir() / "token.dpapi"
        self._protect, self._unprotect = protect, unprotect

    def save(self, token: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        encrypted = self._protect(json.dumps(token, separators=(",", ":")).encode("utf-8"))
        temporary = self.path.with_suffix(".tmp")
        temporary.write_bytes(encrypted)
        os.replace(temporary, self.path)

    def load(self) -> dict[str, Any] | None:
        if not self.path.exists():
            return None
        return json.loads(self._unprotect(self.path.read_bytes()).decode("utf-8"))


@dataclass(frozen=True)
class OAuthClient:
    client_id: str
    client_secret: str
    auth_uri: str
    token_uri: str

    @classmethod
    def load(cls, path: Path | None = None) -> "OAuthClient":
        source = path or oauth_client_path()
        payload = json.loads(source.read_text(encoding="utf-8"))
        installed = payload.get("installed")
        if not isinstance(installed, dict) or not installed.get("client_id") or not installed.get("token_uri"):
            raise ValueError("OAuth client must be a Google Desktop app credential")
        return cls(installed["client_id"], installed.get("client_secret", ""),
                   installed.get("auth_uri", "https://accounts.google.com/o/oauth2/auth"), installed["token_uri"])


def _request_json(url: str, *, method: str = "GET", headers: dict[str, str] | None = None,
                  form: dict[str, str] | None = None, json_body: dict[str, Any] | None = None,
                  timeout: float = 15) -> dict[str, Any]:
    if form is not None and json_body is not None:
        raise ValueError("form and JSON body are mutually exclusive")
    body = (urllib.parse.urlencode(form).encode() if form is not None else
            json.dumps(json_body, separators=(",", ":")).encode() if json_body is not None else None)
    request = urllib.request.Request(url, data=body, method=method, headers=headers or {})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


class GmailAdapter:
    """OAuth Gmail adapter. Readiness never sends mail; sending requires a broker-issued action."""

    def __init__(self, client: OAuthClient, store: DPAPITokenStore, request_json: Callable[..., dict[str, Any]] = _request_json) -> None:
        self.client, self.store, self._request_json = client, store, request_json

    def _fresh_token(self) -> dict[str, Any]:
        token = self.store.load()
        if not token:
            raise RuntimeError("GMAIL_CONSENT_REQUIRED")
        if token.get("expires_at", 0) > time.time() + 60:
            return token
        refresh = token.get("refresh_token")
        if not refresh:
            raise RuntimeError("GMAIL_CONSENT_REQUIRED")
        refreshed = self._request_json(self.client.token_uri, method="POST", form={
            "client_id": self.client.client_id, "client_secret": self.client.client_secret,
            "refresh_token": refresh, "grant_type": "refresh_token",
        })
        token.update(refreshed)
        token["refresh_token"] = refresh
        token["expires_at"] = time.time() + int(refreshed.get("expires_in", 3600))
        self.store.save(token)
        return token

    def verify_readiness(self) -> dict[str, Any]:
        token = self._fresh_token()
        granted = set(str(token.get("scope", "")).split())
        if not set(GMAIL_SCOPES).issubset(granted):
            raise RuntimeError("GMAIL_MINIMUM_SCOPES_NOT_GRANTED")
        profile = self._request_json(PROFILE_URL, headers={"Authorization": f"Bearer {token['access_token']}"})
        if str(profile.get("emailAddress", "")).lower() != GMAIL_ACCOUNT:
            raise RuntimeError("GMAIL_ACCOUNT_MISMATCH")
        return {"ready": True, "account": GMAIL_ACCOUNT, "scopes": list(GMAIL_SCOPES),
                "verified_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "send_performed": False}

    def send_authorized(self, raw_message: bytes, grant: dict[str, Any]) -> dict[str, Any]:
        """Send only a message for which the External Action Broker issued an exact E2-01 grant."""
        required = {"authorized": True, "issued_by": "OMEGA_EXTERNAL_ACTION_BROKER", "experiment_id": "E2-01", "channel": "gmail",
                    "account": GMAIL_ACCOUNT, "message_sha256": FROZEN_MESSAGE_SHA256}
        if any(grant.get(key) != value for key, value in required.items()):
            raise PermissionError("BROKER_GRANT_REQUIRED")
        if grant.get("contacts_used", 0) >= grant.get("contacts_maximum", 0) or grant.get("revoked") is not False:
            raise PermissionError("E2_CONTACT_LIMIT_OR_KILL_SWITCH")
        token = self._fresh_token()
        encoded = base64.urlsafe_b64encode(raw_message).decode("ascii")
        return self._request_json("https://gmail.googleapis.com/gmail/v1/users/me/messages/send", method="POST",
                                  headers={"Authorization": f"Bearer {token['access_token']}", "Content-Type": "application/json"},
                                  json_body={"raw": encoded})

    def authorize_interactively(self, timeout: int = 180) -> dict[str, Any]:
        verifier = secrets.token_urlsafe(64)
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
        state = secrets.token_urlsafe(24)
        result: dict[str, str] = {}

        class Callback(http.server.BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                if query.get("state", [""])[0] == state:
                    result.update({key: values[0] for key, values in query.items() if values})
                self.send_response(200); self.send_header("Content-Type", "text/plain; charset=utf-8"); self.end_headers()
                self.wfile.write(b"OMEGA Gmail consent received. You may close this tab.")
            def log_message(self, format: str, *args: Any) -> None:
                return

        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0)); port = probe.getsockname()[1]
        redirect = f"http://127.0.0.1:{port}/"
        server = http.server.HTTPServer(("127.0.0.1", port), Callback)
        server.timeout = timeout
        thread = threading.Thread(target=server.handle_request, daemon=True); thread.start()
        params = {"client_id": self.client.client_id, "redirect_uri": redirect, "response_type": "code",
                  "scope": " ".join(GMAIL_SCOPES), "access_type": "offline", "prompt": "consent",
                  "state": state, "code_challenge": challenge, "code_challenge_method": "S256"}
        webbrowser.open(self.client.auth_uri + "?" + urllib.parse.urlencode(params))
        thread.join(timeout)
        server.server_close()
        if thread.is_alive() or "code" not in result:
            raise RuntimeError("GMAIL_CONSENT_NOT_COMPLETED")
        token = self._request_json(self.client.token_uri, method="POST", form={
            "client_id": self.client.client_id, "client_secret": self.client.client_secret,
            "code": result["code"], "code_verifier": verifier, "grant_type": "authorization_code", "redirect_uri": redirect,
        })
        token["expires_at"] = time.time() + int(token.get("expires_in", 3600))
        self.store.save(token)
        return self.verify_readiness()


def channel_status(root: Path) -> dict[str, Any]:
    config = oauth_client_path()
    token = gmail_config_dir() / "token.dpapi"
    return {"channel": "gmail", "account": GMAIL_ACCOUNT, "oauth_client_configured": config.is_file(),
            "encrypted_token_present": token.is_file(), "credential_directory": str(gmail_config_dir()),
            "scopes": list(GMAIL_SCOPES), "outreach_sent": False,
            "next_action": "VERIFY" if token.is_file() else ("CONSENT" if config.is_file() else "INSTALL_OAUTH_CLIENT")}


def verify_and_transition(root: Path, adapter: GmailAdapter) -> dict[str, Any]:
    authorization_path = root / ".omega" / "avf" / "market_authorization.json"
    authorization = json.loads(authorization_path.read_text(encoding="utf-8"))
    message_path = root / authorization["frozen_message"]["path"]
    actual_hash = hashlib.sha256(message_path.read_bytes()).hexdigest()
    if actual_hash != authorization["frozen_message"]["sha256"] or actual_hash != FROZEN_MESSAGE_SHA256:
        raise RuntimeError("FROZEN_E2_MESSAGE_INTEGRITY_FAILURE")
    scope = authorization["scope"]
    if scope["maximum_qualified_contacts"] != 10 or scope["contacts_used"] != 0 or scope["financial_authority_kwd"] != 0:
        raise RuntimeError("E2_AUTHORIZATION_LIMITS_CHANGED")
    verified = adapter.verify_readiness()
    authorization["status"] = "CHANNEL_READY"
    authorization["identity"]["credential_configured"] = True
    authorization["channel"] = {"id": "gmail", "account": GMAIL_ACCOUNT, "owner_controlled": True,
                                  "authorized": True, "policy_verified": True,
                                  "minimum_scopes": list(GMAIL_SCOPES), "verified_at": verified["verified_at"]}
    authorization["status"] = "E2_EXECUTABLE"
    authorization["blocker"] = None
    temporary = authorization_path.with_suffix(".tmp")
    temporary.write_text(json.dumps(authorization, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, authorization_path)
    return {"state": "E2_EXECUTABLE", "channel_ready": True, "account": GMAIL_ACCOUNT,
            "contacts_used": 0, "contacts_maximum": 10, "financial_authority_kwd": 0, "outreach_sent": False}


def execute_e2_batch(root: Path, adapter: GmailAdapter) -> dict[str, Any]:
    """Execute only the preregistered E2-01 one-to-one batch, idempotently."""
    from .venture_foundry import gmail_broker_grant

    avf = root / ".omega" / "avf"
    authorization_path = avf / "market_authorization.json"
    target_path = avf / "e2_01_qualified_targets.json"
    event_path = avf / "e2_01_send_events.jsonl"
    authorization = json.loads(authorization_path.read_text(encoding="utf-8"))
    report = json.loads(target_path.read_text(encoding="utf-8"))
    if authorization.get("status") != "E2_EXECUTABLE" or report.get("experiment_id") != "E2-01":
        raise RuntimeError("E2_BATCH_NOT_EXECUTABLE")
    targets = report.get("qualified_targets", [])
    if len(targets) != 4 or report.get("pre_send_invariants", {}).get("individual_messages") != 4:
        raise RuntimeError("PREREGISTERED_E2_BATCH_CHANGED")
    frozen_path = root / authorization["frozen_message"]["path"]
    frozen_bytes = frozen_path.read_bytes()
    digest = hashlib.sha256(frozen_bytes).hexdigest()
    if digest != FROZEN_MESSAGE_SHA256 or digest != report.get("message_sha256"):
        raise RuntimeError("FROZEN_E2_MESSAGE_INTEGRITY_FAILURE")
    # Hash the original bytes above; normalize only the transport parser's line separators.
    frozen = frozen_bytes.decode("utf-8").replace("\r\n", "\n")
    subject_line, separator, body = frozen.partition("\n\n")
    if not separator or not subject_line.startswith("Subject: "):
        raise RuntimeError("FROZEN_E2_MESSAGE_FORMAT_INVALID")
    subject = subject_line.removeprefix("Subject: ")
    existing = []
    if event_path.exists():
        for line in event_path.read_text(encoding="utf-8").splitlines():
            try: existing.append(json.loads(line))
            except json.JSONDecodeError: continue
    completed = {event["target_id"] for event in existing if event.get("send_status") == "SEND_ACCEPTED"}
    outcomes = []
    for target in targets:
        if target["target_id"] in completed:
            outcomes.append({"target_id": target["target_id"], "send_status": "SKIPPED_ALREADY_SENT"})
            continue
        grant = gmail_broker_grant(authorization, target)
        if not grant["authorized"]:
            outcomes.append({"target_id": target["target_id"], "send_status": "BROKER_REJECTED", "reason": grant["reason"]})
            continue
        message = EmailMessage()
        message["From"] = f"OMEGA / Agent Runtime Audit <{GMAIL_ACCOUNT}>"
        message["To"] = target["recipient"]
        message["Subject"] = subject
        message["Date"] = format_datetime(datetime.now(timezone.utc))
        message["Message-ID"] = make_msgid(domain="gmail.com")
        message.set_content(body)
        timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
        try:
            receipt = adapter.send_authorized(message.as_bytes(), grant)
            gmail_id = receipt.get("id")
            sent = adapter._request_json(
                f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{urllib.parse.quote(str(gmail_id))}?format=minimal",
                headers={"Authorization": f"Bearer {adapter._fresh_token()['access_token']}"})
            sent_verified = bool(gmail_id and "SENT" in sent.get("labelIds", []))
            event = {"event": "E2_CONTACT_ACTION", "experiment_id": "E2-01", "target_id": target["target_id"],
                     "recipient": target["recipient"], "timestamp": timestamp, "message_sha256": digest,
                     "send_status": "SEND_ACCEPTED", "gmail_message_id": gmail_id,
                     "sent_folder_verified": sent_verified, "delivery_status": "UNVERIFIED",
                     "demand_signal": False, "follow_up_scheduled": False}
            authorization["scope"]["contacts_used"] += 1
            authorization["audit"]["actions_executed"] += 1
        except Exception as exc:
            event = {"event": "E2_CONTACT_ACTION", "experiment_id": "E2-01", "target_id": target["target_id"],
                     "recipient": target["recipient"], "timestamp": timestamp, "message_sha256": digest,
                     "send_status": "SEND_FAILED", "delivery_status": "NOT_SENT", "demand_signal": False,
                     "follow_up_scheduled": False, "error_type": type(exc).__name__}
        with event_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")
        temporary = authorization_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(authorization, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temporary, authorization_path)
        outcomes.append(event)
    return {"experiment_id": "E2-01", "outcomes": outcomes,
            "contacts_used": authorization["scope"]["contacts_used"],
            "contacts_maximum": authorization["scope"]["maximum_qualified_contacts"],
            "actions_executed": authorization["audit"]["actions_executed"],
            "deliveries_verified": authorization["audit"]["deliveries"],
            "qualified_signals": authorization["audit"]["qualified_signals"],
            "financial_authority_kwd": authorization["scope"]["financial_authority_kwd"]}


def monitor_e2_replies(root: Path, adapter: GmailAdapter) -> dict[str, Any]:
    """Inspect only the four recorded Gmail threads and retain classifications, never raw reply bodies."""
    avf = root / ".omega" / "avf"
    send_path, reply_path = avf / "e2_01_send_events.jsonl", avf / "e2_01_reply_events.jsonl"
    authorization_path = avf / "market_authorization.json"
    authorization = json.loads(authorization_path.read_text(encoding="utf-8"))
    sends = [json.loads(line) for line in send_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    prior = []
    if reply_path.exists():
        for line in reply_path.read_text(encoding="utf-8").splitlines():
            try: prior.append(json.loads(line))
            except json.JSONDecodeError: continue
    seen = {event.get("gmail_message_id") for event in prior}
    token = adapter._fresh_token()
    headers = {"Authorization": f"Bearer {token['access_token']}"}
    observed = []
    positive_signals = 0
    for sent_event in sends:
        if sent_event.get("send_status") != "SEND_ACCEPTED":
            continue
        sent_id = sent_event.get("gmail_message_id")
        sent = adapter._request_json(f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{sent_id}?format=minimal", headers=headers)
        thread_id = sent.get("threadId")
        thread = adapter._request_json(f"https://gmail.googleapis.com/gmail/v1/users/me/threads/{thread_id}?format=full", headers=headers)
        related = [message for message in thread.get("messages", []) if message.get("id") != sent_id and message.get("id") not in seen]
        for message in related:
            header_items = message.get("payload", {}).get("headers", [])
            mail_headers = {str(item.get("name", "")).lower(): str(item.get("value", "")) for item in header_items}
            sender = mail_headers.get("from", "").lower()
            subject = mail_headers.get("subject", "").lower()
            if GMAIL_ACCOUNT in sender:
                continue
            text_parts = []
            stack = [message.get("payload", {})]
            while stack:
                part = stack.pop(); stack.extend(part.get("parts", []))
                if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
                    encoded = part["body"]["data"]; encoded += "=" * (-len(encoded) % 4)
                    text_parts.append(base64.urlsafe_b64decode(encoded).decode("utf-8", errors="replace"))
            normalized = " ".join(text_parts).lower()
            if any(value in sender or value in subject for value in ("mailer-daemon", "postmaster", "delivery status", "undeliverable")):
                classification = "BOUNCE"
            elif any(value in normalized for value in ("unsubscribe", "remove me", "do not contact")):
                classification = "UNSUBSCRIBE"
            elif any(value in normalized for value in ("not interested", "not relevant", "no thanks", "decline", "not a problem")):
                classification = "NEGATIVE"
            elif any(value in normalized for value in ("interested", "willing to", "happy to review", "send the sample", "try the audit", "book a demo")):
                classification = "POSITIVE"
                positive_signals += 1
            elif normalized.strip():
                classification = "AMBIGUOUS"
            else:
                classification = "OTHER"
            event = {"event": "E2_REPLY_OBSERVED", "experiment_id": "E2-01",
                     "target_id": sent_event["target_id"], "gmail_message_id": message.get("id"),
                     "gmail_thread_id": thread_id, "observed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                     "classification": classification, "raw_content_stored": False,
                     "demand_signal": classification == "POSITIVE", "automated_follow_up": False}
            with reply_path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")
            observed.append(event)
            if classification == "NEGATIVE": authorization["audit"]["negative_responses"] += 1
    if positive_signals:
        authorization["audit"]["qualified_signals"] += positive_signals
    if observed:
        temporary = authorization_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(authorization, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temporary, authorization_path)
    return {"experiment_id": "E2-01", "threads_checked": len(sends), "new_reply_events": observed,
            "positive_demand_signals": authorization["audit"]["qualified_signals"],
            "negative_responses": authorization["audit"]["negative_responses"],
            "deliveries_verified": authorization["audit"]["deliveries"], "raw_content_stored": False}
