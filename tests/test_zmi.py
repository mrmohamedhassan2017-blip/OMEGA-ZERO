import tempfile, unittest
from pathlib import Path
from omega.zero_truth import operate_zmi_cycle

class ZMITests(unittest.TestCase):
    def test_cycle_decomposes_and_preserves_ladder(self):
        with tempfile.TemporaryDirectory() as tmp:
            r=operate_zmi_cycle(Path(tmp)); self.assertEqual(8,len(r["child_bottlenecks"])); self.assertEqual("L0",r["current_value_level"])
            self.assertEqual("COUNTERPARTY_MOTIVATION",r["dominant_child_bottleneck"]); self.assertTrue(r["red"]["existing_kit_sufficient"])
    def test_capability_contract_is_machine_readable_without_secrets(self):
        with tempfile.TemporaryDirectory() as tmp:
            c=operate_zmi_cycle(Path(tmp))["capability_contract"]; self.assertTrue({"capability_id","input_schema","output_schema","privacy_boundary","verification_method","provenance_method","source_commit","evidence_contract"}<=set(c)); self.assertNotIn("token",str(c).lower())
    def test_no_external_action_or_value_created(self):
        with tempfile.TemporaryDirectory() as tmp:
            r=operate_zmi_cycle(Path(tmp)); self.assertIsNone(r["authorization_required"]); self.assertEqual(0,r["real_economic_value_kwd"]); self.assertIn("no external",r["action_executed"])

if __name__=="__main__": unittest.main()
