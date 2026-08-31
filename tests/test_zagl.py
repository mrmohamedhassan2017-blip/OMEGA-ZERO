import tempfile, unittest
from pathlib import Path
from omega.zero_truth import operate_zagl_cycle

class ZAGLTests(unittest.TestCase):
    def test_baseline_parity_and_no_winner(self):
        with tempfile.TemporaryDirectory() as t:
            r=operate_zagl_cycle(Path(t)); self.assertEqual("BASELINE_PARITY",r["state"]); self.assertFalse(r["assurance_genome_candidate_found"]); self.assertEqual("NO_WINNER",r["tournament_winner"])
    def test_external_gate_preserved(self):
        with tempfile.TemporaryDirectory() as t:
            r=operate_zagl_cycle(Path(t)); self.assertEqual("L0",r["current_value_level"]); self.assertFalse(r["external_experiment_justified"]); self.assertEqual(0,r["real_economic_value_kwd"])

if __name__=="__main__": unittest.main()
