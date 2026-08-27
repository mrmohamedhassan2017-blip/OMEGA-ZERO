import json
import tempfile
import unittest
from pathlib import Path

from omega.report import analyze_spec, render_markdown
from omega.spec import spec_to_bundle, validate_spec
from omega.store import Store


def example_spec():
    return json.loads((Path(__file__).parents[1] / "examples" / "launch.problem.json").read_text(encoding="utf-8"))


class SpecTests(unittest.TestCase):
    def test_spec_checks_without_mutating_a_database(self):
        spec = example_spec()
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(Path(tmp) / "spec.db")
            result = validate_spec(spec)
            self.assertTrue(result["valid"])
            self.assertEqual([], store.list_problems())

    def test_run_spec_generates_complete_report_and_audit(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = analyze_spec(Store(Path(tmp) / "spec.db"), example_spec())
        self.assertTrue(report["validation"]["valid"])
        self.assertEqual("launch", report["analysis_target"]["key"])
        self.assertIn("test_plan", report["prove_it"])
        self.assertEqual(1, report["audit_events"])
        markdown = render_markdown(report)
        self.assertIn("## WHY", markdown); self.assertIn("## BREAK IT", markdown)
        self.assertIn("## PROVE IT", markdown); self.assertIn("## WHAT IF", markdown)

    def test_spec_rejects_missing_analysis_target_before_import(self):
        spec = example_spec(); spec["analysis_target"] = "missing"
        with self.assertRaisesRegex(ValueError, "analysis_target"):
            spec_to_bundle(spec)

    def test_spec_rejects_duplicate_keys(self):
        spec = example_spec(); spec["nodes"].append(dict(spec["nodes"][0]))
        with self.assertRaisesRegex(ValueError, "unique"):
            spec_to_bundle(spec)


if __name__ == "__main__":
    unittest.main()
