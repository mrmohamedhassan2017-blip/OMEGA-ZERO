from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from omega.scientific_learning import (
    CYBER_MODE, LearningStore, STATES, first_campaign_units, learning_status,
    normalize_windows_status, run_first_campaign, run_test_only_application,
    freeze_learning_rehydration,
)


class ScientificLearningTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()

    def tearDown(self):
        self.temp.cleanup()

    def test_frozen_curriculum_has_required_evidence_and_no_trust(self):
        units = first_campaign_units()
        self.assertEqual(11, len(units))
        self.assertEqual(list("ABCDEFGHIJK"), [unit.knowledge_id for unit in units])
        self.assertIn("TRUSTED", STATES)
        for unit in units:
            self.assertTrue(unit.source_evidence)
            self.assertTrue(unit.source_evidence[0].url.startswith("https://"))
            self.assertTrue(unit.source_evidence[0].content_claim_hash)
            self.assertTrue(unit.plain_explanation)
            self.assertTrue(unit.formal_explanation)
            self.assertTrue(unit.active_recall)
            self.assertTrue(unit.novel_problem)
            self.assertTrue(unit.counterexample_or_failure_mode)
            self.assertNotEqual("TRUSTED", unit.state)

    def test_signed_unsigned_application_beats_baseline(self):
        self.assertEqual("0xC000013A", normalize_windows_status(-1073741510))
        self.assertEqual("0xC000013A", normalize_windows_status(3221225786))
        result = run_test_only_application()
        self.assertTrue(result["passed"])
        self.assertEqual("TEST_ONLY", result["mode"])
        self.assertEqual("CAPABILITY_CANDIDATE", result["capability_state"])
        self.assertEqual(0, result["external_writes"])

    def test_application_uses_existing_capability_fabric_in_shadow(self):
        result = run_test_only_application(self.root)
        self.assertEqual("SHADOW_CANDIDATE_RECORDED", result["capability_fabric"]["state"])
        self.assertEqual("CAPABILITY_GAP", result["capability_fabric"]["route_status"])
        self.assertFalse(result["capability_fabric"]["execution_performed"])
        self.assertFalse(result["capability_fabric"]["promotion_authorized"])

    def test_campaign_persists_and_is_idempotent(self):
        first = run_first_campaign(self.root)
        second = run_first_campaign(self.root)
        self.assertEqual("COMPLETED", first["campaign"]["status"])
        self.assertEqual(first["integrity_hash"], second["integrity_hash"])
        self.assertEqual({"passed": 11, "failed": 0, "total": 11}, first["assessment_summary"])
        self.assertEqual("TASK_COMPLETED", first["task_continuity"]["task_state"])
        self.assertEqual("PASS", first["task_continuity"]["host_verification"])
        self.assertIsNone(learning_status(self.root)["task_continuity"]["next_action"])
        self.assertEqual(CYBER_MODE, first["cybersecurity_mode"])
        self.assertEqual(0, first["trusted_on_first_cycle"])
        self.assertFalse(any(state == "TRUSTED" for state in first["knowledge_states"].values()))
        self.assertEqual(first["campaign"]["campaign_id"], learning_status(self.root)["campaign"]["campaign_id"])

    def test_integrity_and_contradiction_fail_closed(self):
        run_first_campaign(self.root)
        store = LearningStore(self.root / ".omega" / "zero" / "scientific_learning")
        path = store.knowledge / "B.json"
        value = json.loads(path.read_text(encoding="utf-8"))
        value["formal_explanation"] = "tampered"
        path.write_text(json.dumps(value), encoding="utf-8")
        with self.assertRaises(ValueError):
            store.read(path)

    def test_prerequisite_graph_is_ordered_and_cyber_is_defensive(self):
        seen = set()
        for unit in first_campaign_units():
            self.assertTrue(set(unit.prerequisites).issubset(seen))
            seen.add(unit.knowledge_id)
        cyber = next(unit for unit in first_campaign_units() if unit.knowledge_id == "G")
        self.assertIn("authorization", cyber.formal_explanation.lower())
        self.assertEqual("DEFENSIVE_AUTHORIZED_ONLY", CYBER_MODE)

    def test_completed_campaign_freezes_full_rehydration_packet(self):
        run_first_campaign(self.root)
        packet = freeze_learning_rehydration(self.root)["ZERO_REHYDRATION_PACKET"]
        self.assertEqual("learning-bootstrap-001", packet["TASK_ID"])
        self.assertEqual("COMPLETED", packet["CURRENT_PHASE"])
        self.assertEqual("NONE_FOR_THIS_TASK; RETURN_TO_REAL_WORK", packet["NEXT_ATOMIC_ACTION"])
        self.assertIn("DO_NOT_REBUILD_ENGINE", packet["DO_NOT_REPEAT"])
        self.assertTrue(packet["INTEGRITY_HASH"])


if __name__ == "__main__":
    unittest.main()
