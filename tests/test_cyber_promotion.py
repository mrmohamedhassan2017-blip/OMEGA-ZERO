import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from omega.cyber_promotion import (
    MISSION_ID,
    build_novel_cases,
    build_promotion_spec,
    freeze_promotion_contract,
    promotion_status,
    run_promotion_campaign,
)


ROOT = Path(__file__).resolve().parents[1]


class CyberPromotionTests(unittest.TestCase):
    def test_promotion_spec_is_frozen_before_results_and_covers_required_domains(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            frozen = freeze_promotion_contract(root)
            state = json.loads((root / ".omega" / "zero" / "cybersecurity" / "promotion" / "v1" / "state.json").read_text(encoding="utf-8"))
        self.assertEqual(MISSION_ID, frozen["mission"]["mission_id"])
        self.assertEqual(40, frozen["spec"]["case_count"])
        self.assertEqual(20, len(frozen["spec"]["evaluation_domains"]))
        self.assertEqual(frozen["spec"]["promotion_spec_hash"], state["promotion_spec_hash"])
        self.assertEqual(frozen["case_packet"]["case_set_hash"], state["case_set_hash"])
        self.assertFalse(state["external_actions_authorized"])
        self.assertFalse(state["financial_actions_authorized"])

    def test_novel_cases_are_not_practical_lab_repeats_and_include_adversarial_uncertainty(self):
        cases = build_novel_cases()
        self.assertEqual(40, len(cases))
        self.assertEqual(20, len({case["domain"] for case in cases}))
        self.assertGreaterEqual(sum(1 for case in cases if case["required_uncertainty"]), 10)
        self.assertGreaterEqual(sum(1 for case in cases if case["safety_critical"]), 3)
        practical_terms = {"ERROR auth", "Everyone:F", "MD5", "shell=True"}
        joined = json.dumps(cases)
        self.assertTrue(all(term not in joined for term in practical_terms))

    def test_campaign_collects_internal_research_evidence_but_refuses_without_independent_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            packet = run_promotion_campaign(root)
            status = promotion_status(root)
            decision_path = root / ".omega" / "zero" / "cybersecurity" / "promotion" / "v1" / "promotion_decision.json"
            self.assertTrue(decision_path.exists())
        self.assertEqual("RESEARCH_GRADE_INTERNAL_EVIDENCE_SUPPORTED", packet["PROMOTION_LEVEL"])
        self.assertEqual("INSUFFICIENT_INDEPENDENT_EVIDENCE", packet["ZERO_VERDICT"])
        self.assertEqual("REFUSE_PROMOTION_PENDING_INDEPENDENT_EVIDENCE", packet["PROMOTION_DECISION"])
        self.assertFalse(packet["PROMOTED"])
        self.assertEqual(40, packet["CASE_COUNT"])
        self.assertEqual(1.0, packet["SAFETY_SCORE"])
        self.assertEqual([], packet["CRITICAL_FAILURES"])
        self.assertEqual("INDEPENDENT_EVIDENCE_NOT_AVAILABLE", packet["INDEPENDENT_EVIDENCE_STATE"])
        self.assertFalse(status["promoted"])

    def test_benchmark_replication_stability_and_safety_fields_are_machine_readable(self):
        with tempfile.TemporaryDirectory() as directory:
            packet = run_promotion_campaign(Path(directory))
        self.assertTrue(packet["BENCHMARK_RESULT"]["passed"])
        self.assertGreater(packet["BENCHMARK_RESULT"]["expert_passed"], packet["BENCHMARK_RESULT"]["baseline_passed"])
        self.assertTrue(packet["STABILITY_RESULT"]["passed"])
        self.assertTrue(packet["REPLICATION_RESULT"]["passed"])
        self.assertEqual(0, packet["EXTERNAL_WRITES"])
        self.assertEqual(0, packet["FINANCIAL_ACTIONS"])
        self.assertFalse(packet["PRODUCTION_ROUTING_CHANGED"])

    def test_cli_research_eval_and_promotion_status(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            env = dict(os.environ)
            env["PYTHONPATH"] = str(ROOT) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
            completed = subprocess.run(
                [sys.executable, "-m", "omega.cli", "cyber", "research-eval"],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            packet = json.loads(completed.stdout)
            status = subprocess.run(
                [sys.executable, "-m", "omega.cli", "cyber", "promotion-status"],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
        self.assertEqual("INSUFFICIENT_INDEPENDENT_EVIDENCE", packet["ZERO_VERDICT"])
        self.assertFalse(json.loads(status.stdout)["promoted"])


if __name__ == "__main__":
    unittest.main()
