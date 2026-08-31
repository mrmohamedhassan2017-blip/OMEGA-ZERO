import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from omega.real_world_value_participant_discovery import (
    DISCOVERY_PROTOCOL,
    discover_participant_dossiers,
    run_participant_discovery,
)


class ParticipantDiscoveryTests(unittest.TestCase):
    def test_resolves_only_firsthand_t2_identities_without_private_contacts(self):
        dossiers = discover_participant_dossiers()
        self.assertEqual(6, len(dossiers))
        self.assertTrue(all(item["qualification_status"] == "QUALIFIED_BUT_NOT_CONTACTABLE" for item in dossiers))
        self.assertTrue(all(item["public_contact_route"] is False for item in dossiers))
        self.assertTrue(all(item["non_owner"] and item["non_bot"] and item["non_omega"] for item in dossiers))
        self.assertTrue(all(item["firsthand_t2_evidence"] for item in dossiers))

    def test_separates_qualification_from_contactability(self):
        with tempfile.TemporaryDirectory() as directory:
            result = run_participant_discovery(Path(directory))
        self.assertEqual(6, result["qualified_but_not_contactable"])
        self.assertEqual(0, result["qualified_and_contactable"])
        self.assertEqual(0, result["contactable_but_not_qualified"])
        self.assertTrue(all(item["contact_route_type"] == "PUBLIC_GITHUB_PROFILE_ONLY" for item in result["candidate_dossiers"]))

    def test_scores_are_transparent_and_ranking_is_deterministic(self):
        dossiers = discover_participant_dossiers()
        factors = {
            "firsthand_incident_strength",
            "t2_relevance",
            "identity_confidence",
            "contact_route_confidence",
            "independence",
            "likelihood_of_e1_e2_e3_e4",
            "stack_diversity",
            "privacy_risk",
        }
        self.assertTrue(all(set(item["scores"]) == factors for item in dossiers))
        self.assertEqual(dossiers, discover_participant_dossiers())
        self.assertEqual({"Prefect", "Prefect on Kubernetes", "Airflow on Kubernetes"}, {item["stack"] for item in dossiers})

    def test_preserves_frozen_binding_hashes_without_binding_participants(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / ".omega" / "zero"
            output.mkdir(parents=True)
            (output / "zrwve_channel_participant_binding_0001.json").write_text(
                json.dumps({
                    "packet_hash": "packet-hash",
                    "initial_message_hash": "message-hash",
                    "participant_set_hash": "old-set-hash",
                    "input_fingerprint": "old-fingerprint",
                }),
                encoding="utf-8",
            )
            result = run_participant_discovery(Path(directory))
        self.assertEqual("packet-hash", result["packet_hash"])
        self.assertEqual("message-hash", result["initial_message_hash"])
        self.assertFalse(result["channel_binding_ready"])
        self.assertEqual([], result["bound_participants"])

    def test_cycle_is_idempotent_and_read_only_with_no_network(self):
        with tempfile.TemporaryDirectory() as directory, patch("urllib.request.urlopen", side_effect=AssertionError("network is forbidden")):
            first = run_participant_discovery(Path(directory))
            second = run_participant_discovery(Path(directory))
            numbered = list((Path(directory) / ".omega" / "zero").glob("zrwve_participant_discovery_[0-9][0-9][0-9][0-9].json"))
        self.assertFalse(first["idempotent_replay"])
        self.assertTrue(second["idempotent_replay"])
        self.assertEqual(1, len(numbered))
        self.assertEqual(0, first["external_write_executed"])
        self.assertEqual(0, first["messages_sent"])

    def test_saturation_and_red_team_close_the_cycle(self):
        with tempfile.TemporaryDirectory() as directory:
            result = run_participant_discovery(Path(directory))
        self.assertEqual(DISCOVERY_PROTOCOL, result["protocol"])
        self.assertEqual("EVIDENCE_SATURATED_CURRENT_T2_CORPUS", result["search_saturation"]["status"])
        self.assertEqual("QUALIFIED_BUT_NO_LEGITIMATE_CONTACT_ROUTE", result["final_result"])
        self.assertEqual(0, result["red_team_result"]["false_qualifications"])
        self.assertEqual("L0", result["current_evidence_level"])
        self.assertEqual("0 KWD", result["verified_net_economic_value"])


if __name__ == "__main__":
    unittest.main()
