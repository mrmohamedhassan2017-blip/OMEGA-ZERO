import json
import tempfile
import unittest
from pathlib import Path

from omega.zlca import run_zlca


class ZLCATests(unittest.TestCase):
    def _root(self):
        folder = tempfile.TemporaryDirectory(); self.addCleanup(folder.cleanup)
        root = Path(folder.name); path = root / ".omega" / "zero" / "lzp_001_result.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({"final_result": "LEAN_PATH_PARITY_WITH_MEANINGFUL_SIMPLIFICATION", "authority_results": {"violations": 0}}), encoding="utf-8")
        return root

    def test_requires_successful_lzp_gate(self):
        with self.assertRaises(RuntimeError): run_zlca(Path(tempfile.gettempdir()) / "zlca-no-lzp")

    def test_constitution_cannot_be_overridden_and_failures_are_safe(self):
        result = run_zlca(self._root())
        self.assertIn("AUTHORITY_BOUNDARIES", result["constitutional_core"])
        self.assertFalse(result["intelligence_escalation_spec"]["constitutional_override"])
        self.assertTrue(all(row["authority_preserved"] and row["verification_preserved"] for row in result["failure_injection_results"]))

    def test_known_rule_never_escalates_and_model_value_is_not_fabricated(self):
        result = run_zlca(self._root())
        known = next(row for row in result["model_escalation_results"] if row["state"] == "RULE_MATCH_EXISTS")
        self.assertFalse(known["model_invoked"])
        self.assertEqual(0, result["model_escalation_yield"]["model_call_count"])
        self.assertEqual("NOT_MEASURED", result["model_escalation_yield"]["value"])

    def test_capability_and_council_value_remain_unknown_without_outcomes(self):
        result = run_zlca(self._root())
        self.assertEqual("NOT_TESTED", result["capability_acquisition_results"]["status"])
        self.assertEqual("UNKNOWN", result["capability_reuse_results"]["advantage"])
        self.assertEqual("UNKNOWN", result["council_value_results"]["value"])

    def test_minimal_architecture_wins_and_migration_remains_blocked(self):
        result = run_zlca(self._root())
        self.assertEqual("MINIMAL_DETERMINISTIC_ZERO_PREFERRED", result["final_architecture_decision"])
        self.assertEqual("CORE_MINIMAL", result["zak_role"])
        self.assertEqual("SIMPLIFIED_CORE", result["zrl_role"])
        self.assertIn("no production migration", result["rollback_status"])


if __name__ == "__main__": unittest.main()
