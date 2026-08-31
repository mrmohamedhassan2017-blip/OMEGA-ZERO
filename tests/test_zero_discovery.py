import json
import tempfile
import unittest
from pathlib import Path

from omega.zero_kernel import generate_discovery_options, operate_discovery_cycle, score_discovery_option


class ZeroDiscoveryTests(unittest.TestCase):
    def test_candidates_cover_distinct_surfaces_and_required_metrics(self):
        options = generate_discovery_options()
        self.assertGreaterEqual(len(options), 6)
        self.assertEqual(len(options), len({item["surface"] for item in options}))
        required = {"external_audience_fit", "signal_quality", "expected_reach", "time_to_signal",
                    "authority_required", "authority_friction", "cost", "spam_policy_risk", "measurement_quality",
                    "automation_potential", "reusability", "contamination_risk", "eva", "evsi"}
        self.assertTrue(all(required <= set(item) for item in options))

    def test_winner_is_scored_not_identifier_hardcoded(self):
        first = generate_discovery_options()[0]
        changed = dict(first); changed["id"] = "renamed"; changed["external_audience_fit"] = 0
        self.assertNotEqual(first["score"], score_discovery_option(changed)["score"])

    def test_forbidden_or_unmeasurable_candidate_is_rejected(self):
        option = dict(generate_discovery_options()[0]); option["forbidden_dependency"] = "fake engagement"
        self.assertEqual("OPTION_REJECTED", score_discovery_option(option)["state"])
        option = dict(generate_discovery_options()[0]); option["measurement"] = ""
        self.assertEqual("OPTION_REJECTED", score_discovery_option(option)["state"])

    def test_cycle_preserves_inbound_and_creates_one_authority_case(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); zero = root / ".omega" / "zero"; zero.mkdir(parents=True)
            state = {"global_state": "PARKED_NO_EXECUTABLE_ACTION", "branches": [
                {"id": "e2-01", "state": "PARKED_WAITING_EXTERNAL"},
                {"id": "v0.30", "state": "PARKED_WAITING_EXTERNAL"},
                {"id": "inbound-evidence", "state": "PUBLISHED_WAITING_EXTERNAL_EVIDENCE"},
            ]}
            (zero / "state.json").write_text(json.dumps(state), encoding="utf-8")
            result = operate_discovery_cycle(root)
            self.assertFalse(result["execution"]["external_action_performed"])
            self.assertEqual("AUTHORITY_REQUIRED", result["authority_case"]["status"])
            self.assertEqual(result["winner"]["surface"], result["authority_case"]["surface"])
            self.assertEqual(result["winner"]["action"], result["authority_case"]["exact_action"])
            self.assertEqual("PUBLISHED_WAITING_EXTERNAL_EVIDENCE", next(
                item["state"] for item in json.loads((zero / "state.json").read_text()) ["branches"]
                if item["id"] == "inbound-evidence"))
            self.assertEqual(10, len(result["measurement_contract"]["funnel"]))
            self.assertEqual([], result["external_evidence"])


if __name__ == "__main__":
    unittest.main()
