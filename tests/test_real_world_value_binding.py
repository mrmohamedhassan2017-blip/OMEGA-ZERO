import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from omega.real_world_value_binding import (
    BINDING_PROTOCOL,
    discover_channels,
    discover_participant_candidates,
    freeze_binding,
    record_binding_host_verification,
)


class RealWorldValueBindingTests(unittest.TestCase):
    def gmail_capability(self):
        return {
            "channel": "gmail",
            "account": "omega.agent.runtime@gmail.com",
            "oauth_client_configured": True,
            "encrypted_token_present": True,
            "scopes": ["https://www.googleapis.com/auth/gmail.send", "https://www.googleapis.com/auth/gmail.readonly"],
        }

    def test_channel_capability_is_separate_from_experiment_authority(self):
        with patch("omega.real_world_value_binding.channel_status", return_value=self.gmail_capability()):
            result = discover_channels(Path.cwd())
        gmail = result["channels"][0]
        self.assertEqual("gmail", result["selected_channel_id"])
        self.assertTrue(gmail["programmatic_write_available"])
        self.assertEqual(["E2-01"], gmail["current_experiment_bindings"])
        self.assertTrue(result["channel_capability_is_not_authority"])
        self.assertFalse(result["e2_authority_reused"])

    def test_channel_without_verified_scopes_is_not_safe_for_binding(self):
        capability = self.gmail_capability()
        capability["scopes"] = ["https://www.googleapis.com/auth/gmail.readonly"]
        with patch("omega.real_world_value_binding.channel_status", return_value=capability):
            result = discover_channels(Path.cwd())
        self.assertFalse(result["channels"][0]["programmatic_write_available"])
        self.assertFalse(result["channels"][0]["suitable_for_zrwve"])
        self.assertEqual("NOT_CONFIGURED_OR_SCOPE_MISMATCH", result["channels"][0]["security_state"])

    def test_candidate_qualification_requires_attributable_public_route(self):
        candidates = discover_participant_candidates()
        self.assertGreaterEqual(len(candidates), 1)
        self.assertTrue(all(row["qualification_status"] != "QUALIFIED" for row in candidates))
        self.assertTrue(all(row["public_contact_route"] is False for row in candidates))
        self.assertTrue(all(row["contact_route_provenance"] == "PUBLIC_PRIMARY_SOURCE_REFERENCE_ONLY" for row in candidates))

    def test_candidates_rank_transparently_and_preserve_stack_context(self):
        candidates = discover_participant_candidates()
        self.assertEqual(sorted(candidates, key=lambda row: (-row["composite_score"], row["participant_candidate_id"])), candidates)
        self.assertTrue(all("firsthand_incident_relevance" in row["scores"] for row in candidates))
        self.assertTrue(any(row["stack"].startswith("Airflow") for row in candidates))

    def test_binding_fails_closed_without_participant_and_never_sends(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch("omega.real_world_value_binding.channel_status", return_value=self.gmail_capability()), \
                 patch("urllib.request.urlopen", side_effect=AssertionError("network called")):
                result = freeze_binding(root)
            self.assertEqual(BINDING_PROTOCOL, result["protocol"])
            self.assertEqual("READY_TO_BIND_BUT_NO_QUALIFIED_PARTICIPANT", result["final_result"])
            self.assertFalse(result["channel_bound"])
            self.assertFalse(result["authority_envelope"]["external_action_authorized"])
            self.assertEqual(0, result["send_state"]["messages_sent"])
            self.assertEqual([], result["selected_participants"])
            self.assertEqual(0, result["qualified_participant_candidates"])
            self.assertEqual(0, result["bound_participant_count"])
            self.assertFalse(result["external_action_authorized"])
            self.assertEqual("0 KWD", result["verified_net_economic_value"])

    def test_binding_reports_no_safe_channel_when_gmail_is_unavailable(self):
        capability = self.gmail_capability()
        capability["encrypted_token_present"] = False
        with tempfile.TemporaryDirectory() as directory:
            with patch("omega.real_world_value_binding.channel_status", return_value=capability):
                result = freeze_binding(Path(directory))
        self.assertEqual("READY_TO_BIND_BUT_NO_SAFE_CHANNEL", result["final_result"])
        self.assertFalse(result["channel_security_result"] == "PASS")
        self.assertFalse(result["authority_envelope"]["external_action_authorized"])

    def test_binding_is_idempotent_and_does_not_touch_e2_state(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch("omega.real_world_value_binding.channel_status", return_value=self.gmail_capability()):
                first = freeze_binding(root)
                replay = freeze_binding(root)
            self.assertTrue(replay["idempotent_replay"])
            self.assertEqual(first["participant_set_hash"], replay["participant_set_hash"])
            self.assertFalse(replay["authority_envelope"]["e2_authority_reused"])
            self.assertEqual(0, replay["send_state"]["external_write_executed"])
            binding_files = list((root / ".omega" / "zero").glob("zrwve_channel_participant_binding_*.json"))
            self.assertEqual(1, len(binding_files))
            persisted = json.loads(binding_files[0].read_text(encoding="utf-8"))
            self.assertEqual(first["input_fingerprint"], persisted["input_fingerprint"])

    def test_binding_freezes_hashes_expiry_dedupe_and_isolated_thread_policy(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch("omega.real_world_value_binding.channel_status", return_value=self.gmail_capability()):
                result = freeze_binding(Path(directory))
        binding = result["channel_binding"]
        self.assertTrue(result["packet_hash_valid"])
        self.assertTrue(result["initial_message_hash"])
        self.assertTrue(result["participant_set_hash"])
        self.assertIn("ZRWVE-T2-BLIND-001", binding["thread_policy"])
        self.assertNotIn("E2-01", binding["thread_policy"])
        self.assertTrue(binding["e2_thread_reuse_forbidden"])
        self.assertEqual("READY", result["dedupe_result"])
        self.assertTrue(result["expiry"])
        self.assertEqual("PRIMARY_PARTICIPANT_ONLY", result["next_send_policy"])
        self.assertEqual("FIND_QUALIFIED_PARTICIPANT", result["next_atomic_action"])

    def test_host_verification_is_persisted_without_opening_authority(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch("omega.real_world_value_binding.channel_status", return_value=self.gmail_capability()):
                result = freeze_binding(root)
            record = record_binding_host_verification(root, {"status": "PASS", "tests": "binding:6/6"})
            self.assertEqual(BINDING_PROTOCOL, record["protocol"])
            self.assertEqual(result["input_fingerprint"], record["binding_cycle_input_fingerprint"])
            self.assertFalse(record["authority_granted"])
            persisted = json.loads((root / ".omega" / "zero" / "zrwve_channel_binding_host_verification_0001.json").read_text(encoding="utf-8"))
            self.assertEqual("PASS", persisted["verification"]["status"])


if __name__ == "__main__":
    unittest.main()
