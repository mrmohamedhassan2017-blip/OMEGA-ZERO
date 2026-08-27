import tempfile
import unittest
from pathlib import Path

from omega.stability import run_stability_audit
from omega.store import Store
from omega.stress import run_concurrency_stress


class StabilityTests(unittest.TestCase):
    def test_core_candidate_passes_but_v1_remains_evidence_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_stability_audit(Store(Path(tmp) / "audit.db"))
        self.assertTrue(result["core_candidate_passed"])
        self.assertEqual({"passed": 10, "total": 10}, result["summary"])
        self.assertFalse(result["ready_for_v1"])
        self.assertGreaterEqual(len(result["v1_blockers"]), 1)

    def test_multi_process_concurrency_stress(self):
        result = run_concurrency_stress(workers=3, writes_per_worker=4)
        self.assertTrue(result["passed"], result["processes"])
        self.assertEqual(12, result["database"]["counts"]["problems"])


if __name__ == "__main__":
    unittest.main()
