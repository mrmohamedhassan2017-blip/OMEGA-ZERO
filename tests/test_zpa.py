import tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from omega.zpa import run_zpa, _run

class ZPATests(unittest.TestCase):
    def test_cycle_and_result(self):
        with tempfile.TemporaryDirectory() as d:
            r = run_zpa(Path(d))
        self.assertEqual(r["final_decision"], "ZFBR_PROCESS_ADOPTION_SUPPORTED")
        self.assertTrue(r["normal_execution_result"]["final_result_parity"])
        self.assertEqual(r["legacy_vs_zfbr_comparison"]["authority_violations"], 0)
    def test_launch_failure_is_distinct(self):
        with tempfile.TemporaryDirectory() as d:
            r = _run(["definitely-missing-omega-executable"], Path(d))
        self.assertEqual(r["blocker"], "PROCESS_LAUNCH_FAILURE")
    def test_timeout_cleans_own_child(self):
        with tempfile.TemporaryDirectory() as d:
            r = _run(["python", "-c", "import time; time.sleep(5)"], Path(d), .01)
        self.assertEqual(r["blocker"], "PROCESS_TIMEOUT"); self.assertFalse(r["orphan"])

if __name__ == "__main__": unittest.main()
