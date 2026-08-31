import tempfile, unittest
from pathlib import Path
from omega.zcce import evaluate_zcce

class ZCCETests(unittest.TestCase):
    def test_core_candidate_is_evidence_based_and_not_migration(self):
        with tempfile.TemporaryDirectory() as d: result = evaluate_zcce(Path(d))
        self.assertEqual(result["core_status_decision"], "ZFBR_LEAN_ZERO_CORE_SUPPORTED")
        self.assertEqual(result["production_status"], "LEGACY_DEFAULT; PRODUCTION_WIDE_ADOPTION_NOT_AUTHORIZED")
        self.assertEqual(result["core_thinness"], "PASS")
    def test_unknown_blocker_fails_closed(self):
        with tempfile.TemporaryDirectory() as d: result = evaluate_zcce(Path(d))
        unknown = result["unknown_blocker_result"]
        self.assertFalse(unknown["commit"]); self.assertTrue(unknown["intent_preserved"])
    def test_ownership_boundaries_are_unique(self):
        with tempfile.TemporaryDirectory() as d: result = evaluate_zcce(Path(d))
        self.assertEqual(result["responsibility_ownership_map"]["worker_lifecycle"], "supervisor")
        self.assertEqual(result["zfbr_zrl_boundary"], "CLEAN")

if __name__ == "__main__": unittest.main()
