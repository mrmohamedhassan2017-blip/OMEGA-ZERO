import tempfile
import unittest
from pathlib import Path

from omega.zava import run_zava


class ZAVATests(unittest.TestCase):
    def test_preserves_truth_and_safety_core(self):
        with tempfile.TemporaryDirectory() as folder:
            result = run_zava(Path(folder))
        self.assertEqual("L0", result["repository_truth"]["evidence_level"])
        self.assertEqual(0, result["repository_truth"]["real_economic_value_kwd"])
        self.assertIn("Supervisor + continuity", result["safety_core"])
        self.assertIn("AgentBackend + Host Verification + PREB", result["safety_core"])

    def test_ablation_is_isolated_and_reports_parity_without_deletion(self):
        with tempfile.TemporaryDirectory() as folder:
            result = run_zava(Path(folder))
        ablation = result["ablation_results"]
        self.assertTrue(ablation["task_success"])
        self.assertEqual(0, ablation["authority_violations"])
        self.assertIn("not production migration", ablation["fixture"])
        self.assertIn("NOT_ABLATED", result["current_vs_minimal_comparison"]["recovery_correctness"])

    def test_prefers_deterministic_core_and_on_demand_intelligence(self):
        with tempfile.TemporaryDirectory() as folder:
            result = run_zava(Path(folder))
        self.assertEqual("DETERMINISTIC_CORE_MODEL_ESCALATION", result["preferred_control_architecture"])
        self.assertEqual("ON_DEMAND_TOOL", result["capability_discovery_reassessment"])
        self.assertEqual("HIGH", result["research_overhead"])
        self.assertEqual("LEAN_ZERO_STRONGLY_PREFERRED", result["master_architecture_decision"])

    def test_writes_machine_readable_result(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            run_zava(root)
            self.assertTrue((root / ".omega" / "zero" / "zava_001_result.json").is_file())


if __name__ == "__main__":
    unittest.main()
