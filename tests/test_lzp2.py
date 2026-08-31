import json
import tempfile
import unittest
from pathlib import Path

from omega.lzp2 import run_lzp2


class LZP2Tests(unittest.TestCase):
    def _run(self, folder):
        path = Path(folder) / ".omega" / "zero" / "lzp_001_result.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"final_result": "LEAN_PATH_PARITY_WITH_MEANINGFUL_SIMPLIFICATION", "authority_results": {"violations": 0}}), encoding="utf-8")
        return run_lzp2(Path(folder))

    def test_frozen_spec_and_all_concurrency_fixtures_pass(self):
        with tempfile.TemporaryDirectory() as folder:
            result = self._run(folder)
        self.assertEqual(64, len(result["spec_hash"]))
        self.assertEqual(8, len(result["concurrency_fixture_results"]))
        self.assertTrue(all(row["result"] == "PASS" for row in result["concurrency_fixture_results"]))

    def test_crash_matrix_surfaces_ambiguity_and_preserves_invariants(self):
        with tempfile.TemporaryDirectory() as folder:
            result = self._run(folder)
        self.assertEqual(12, len(result["crash_point_matrix"]))
        self.assertIn("AMBIGUOUS", [row["recovery_classification"] for row in result["crash_point_matrix"]])
        self.assertTrue(all(result["invariant_results"].values()))

    def test_owner_epoch_resource_and_verification_races_are_safe(self):
        with tempfile.TemporaryDirectory() as folder:
            result = self._run(folder)
        self.assertEqual(0, result["stale_owner_results"]["stale_owner_commits"])
        self.assertEqual(0, result["duplicate_wake_results"]["duplicate_accepted"])
        self.assertEqual(0, result["authority_race_results"]["violations"])
        self.assertEqual(0, result["verification_race_results"]["false_verified_successes"])

    def test_long_duration_and_failure_injection_are_deterministic(self):
        with tempfile.TemporaryDirectory() as folder:
            result = self._run(folder)
        self.assertEqual("PASS", result["long_duration_scheduling_results"]["result"])
        self.assertEqual(8 * 5, result["failure_injection_results"]["runs"])
        self.assertFalse(result["failure_injection_results"]["unfavorable_schedules_cherry_picked"])

    def test_opens_zlca_only_after_parity_and_keeps_migration_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            result = self._run(folder)
        self.assertEqual("LEAN_CONCURRENCY_AND_ATOMICITY_PARITY_SUPPORTED", result["final_result"])
        self.assertEqual("OPEN", result["zlca_entry_gate"])
        self.assertEqual("NO", result["shadow_runtime_gate"])
        self.assertEqual("NOT_AUTHORIZED", result["production_migration_status"])


if __name__ == "__main__": unittest.main()
