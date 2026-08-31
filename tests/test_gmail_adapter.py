import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from omega.gmail_adapter import (GMAIL_ACCOUNT, GMAIL_SCOPES, DPAPITokenStore,
                                 GmailAdapter, OAuthClient, channel_status, execute_e2_batch, monitor_e2_replies,
                                 verify_and_transition)


class GmailAdapterTests(unittest.TestCase):
    def test_minimum_scopes_exclude_mailbox_modification(self):
        self.assertEqual({"https://www.googleapis.com/auth/gmail.send",
                          "https://www.googleapis.com/auth/gmail.readonly"}, set(GMAIL_SCOPES))
        self.assertFalse(any(scope.endswith("gmail.modify") or scope.endswith("/mail.google.com/") for scope in GMAIL_SCOPES))

    def test_token_store_encrypts_and_never_writes_plaintext(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "token.dpapi"
            store = DPAPITokenStore(path, protect=lambda value: b"encrypted:" + value[::-1],
                                    unprotect=lambda value: value.removeprefix(b"encrypted:")[::-1])
            token = {"access_token": "highly-secret", "refresh_token": "also-secret"}
            store.save(token)
            self.assertNotIn(b"secret", path.read_bytes())
            self.assertEqual(token, store.load())

    def test_status_is_read_only_and_config_lives_outside_repository(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repository"; root.mkdir()
            local = Path(tmp) / "local"
            with patch.dict(os.environ, {"LOCALAPPDATA": str(local)}, clear=False):
                status = channel_status(root)
            self.assertFalse(status["outreach_sent"])
            self.assertEqual("INSTALL_OAUTH_CLIENT", status["next_action"])
            self.assertFalse(str(status["credential_directory"]).startswith(str(root)))

    def test_readiness_checks_profile_and_performs_no_send(self):
        calls = []
        token = {"access_token": "redacted", "expires_at": 99999999999, "scope": " ".join(GMAIL_SCOPES)}
        class Store:
            def load(self): return token
            def save(self, value): raise AssertionError("fresh token should not be rewritten")
        def request(url, **kwargs):
            calls.append((url, kwargs)); return {"emailAddress": GMAIL_ACCOUNT}
        ready = GmailAdapter(OAuthClient("id", "secret", "auth", "token"), Store(), request).verify_readiness()
        self.assertTrue(ready["ready"]); self.assertFalse(ready["send_performed"])
        self.assertEqual(1, len(calls)); self.assertTrue(calls[0][0].endswith("/profile"))

    def test_wrong_account_or_missing_scope_never_becomes_ready(self):
        class Store:
            def __init__(self, scope): self.scope = scope
            def load(self): return {"access_token": "x", "expires_at": 99999999999, "scope": self.scope}
        client = OAuthClient("id", "secret", "auth", "token")
        with self.assertRaisesRegex(RuntimeError, "MINIMUM_SCOPES"):
            GmailAdapter(client, Store(GMAIL_SCOPES[0]), lambda *a, **k: {}).verify_readiness()
        with self.assertRaisesRegex(RuntimeError, "ACCOUNT_MISMATCH"):
            GmailAdapter(client, Store(" ".join(GMAIL_SCOPES)), lambda *a, **k: {"emailAddress": "other@example.com"}).verify_readiness()

    def test_transition_requires_real_profile_and_preserves_e2_limits(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); avf = root / ".omega" / "avf"; avf.mkdir(parents=True)
            message = avf / "e2_01_frozen_message.txt"; message.write_text("frozen", encoding="utf-8")
            digest = hashlib.sha256(message.read_bytes()).hexdigest()
            authorization = {"experiment_id": "E2-01", "status": "AUTHORIZED_PENDING_CHANNEL",
                "identity": {"owner_authorized": True, "credential_configured": False}, "channel": {"authorized": False},
                "scope": {"maximum_qualified_contacts": 10, "contacts_used": 0, "financial_authority_kwd": 0},
                "frozen_message": {"path": ".omega/avf/e2_01_frozen_message.txt", "sha256": digest},
                "blocker": "AUTHORIZED_CHANNEL_NOT_TECHNICALLY_CONFIGURED"}
            auth_path = avf / "market_authorization.json"; auth_path.write_text(json.dumps(authorization), encoding="utf-8")
            class Adapter:
                def verify_readiness(self):
                    return {"ready": True, "account": GMAIL_ACCOUNT, "verified_at": "2026-08-27T00:00:00+00:00", "send_performed": False}
            with patch("omega.gmail_adapter.FROZEN_MESSAGE_SHA256", digest):
                result = verify_and_transition(root, Adapter())
            saved = json.loads(auth_path.read_text(encoding="utf-8"))
            self.assertEqual("E2_EXECUTABLE", result["state"]); self.assertEqual("E2_EXECUTABLE", saved["status"])
            self.assertEqual(0, saved["scope"]["contacts_used"]); self.assertEqual(0, saved["scope"]["financial_authority_kwd"])
            self.assertFalse(result["outreach_sent"])

    def test_send_rejects_missing_broker_grant_without_network(self):
        adapter = GmailAdapter(OAuthClient("id", "secret", "auth", "token"), object(),
                               lambda *args, **kwargs: self.fail("network must not be called"))
        with self.assertRaisesRegex(PermissionError, "BROKER_GRANT_REQUIRED"):
            adapter.send_authorized(b"message", {})

    def test_e2_batch_is_one_to_one_idempotent_and_monitor_is_read_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); avf=root/".omega"/"avf"; avf.mkdir(parents=True)
            frozen=avf/"frozen.txt"; frozen.write_text("Subject: Frozen subject\n\nFrozen body",encoding="utf-8")
            digest=hashlib.sha256(frozen.read_bytes()).hexdigest()
            auth={"experiment_id":"E2-01","status":"E2_EXECUTABLE","identity":{"owner_authorized":True},
              "channel":{"id":"gmail","account":GMAIL_ACCOUNT,"authorized":True,"policy_verified":True},
              "scope":{"contacts_used":0,"maximum_qualified_contacts":10,"financial_authority_kwd":0,"message_variants":1,"automated_follow_up":False},
              "frozen_message":{"path":".omega/avf/frozen.txt","sha256":digest},"kill_switch":{"revoked":False},
              "audit":{"actions_executed":0,"deliveries":0,"qualified_signals":0,"negative_responses":0}}
            (avf/"market_authorization.json").write_text(json.dumps(auth),encoding="utf-8")
            targets=[]
            for index in range(4):
                targets.append({"target_id":f"t{index}","recipient":f"t{index}@example.com","operates_coding_agents":True,
                  "runtime_responsibility":True,"pain_evidence":"public","authority":"CHAMPION","channel_permits_contact":True})
            report={"experiment_id":"E2-01","message_sha256":digest,"qualified_targets":targets,
                    "pre_send_invariants":{"individual_messages":4}}
            (avf/"e2_01_qualified_targets.json").write_text(json.dumps(report),encoding="utf-8")
            class Adapter:
                def __init__(self): self.sent=[]
                def send_authorized(self,raw,grant): self.sent.append(grant["target_id"]); return {"id":f"m{len(self.sent)}"}
                def _fresh_token(self): return {"access_token":"fake"}
                def _request_json(self,url,**kwargs):
                    if "/threads/" in url: return {"messages":[{"id":url.split("/")[-1].split("?")[0]}]}
                    identifier=url.split("/messages/")[-1].split("?")[0]
                    return {"id":identifier,"threadId":identifier,"labelIds":["SENT"]}
            adapter=Adapter()
            with patch("omega.gmail_adapter.FROZEN_MESSAGE_SHA256",digest):
                first=execute_e2_batch(root,adapter); second=execute_e2_batch(root,adapter)
            self.assertEqual(4,first["contacts_used"]); self.assertEqual(4,len(adapter.sent))
            self.assertTrue(all(item["send_status"]=="SKIPPED_ALREADY_SENT" for item in second["outcomes"]))
            monitored=monitor_e2_replies(root,adapter)
            self.assertEqual([],monitored["new_reply_events"]); self.assertEqual(0,monitored["positive_demand_signals"])


if __name__ == "__main__":
    unittest.main()
