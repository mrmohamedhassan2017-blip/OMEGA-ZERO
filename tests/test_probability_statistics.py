from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from omega.probability_statistics import (
    TASK_ID, UNIT_IDS, diagnostic_evidence, park_eligibility,
    probability_campaign_status, probability_units, run_probability_campaign,
    run_statistical_application,
)
from omega.task_continuity import TaskContinuityStore


class ProbabilityStatisticsCampaignTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        (self.root / ".omega" / "wake-plane").mkdir(parents=True)
        heartbeat = {
            "status": "RUNNING", "mode": "PASSIVE_PRODUCTION",
            "pending_candidates": 0, "validated_pending": 0,
        }
        sources = {
            "v0_30_evaluator": {
                "milestone_state": "WAITING_EXTERNAL_EVIDENCE",
                "independent_evaluator_count": 0, "validated_count": 0,
            },
            "provider_recovery": {
                "last_error_class": "NO_ACTIVE_MATCHING_FROZEN_WORK",
                "validated_count": 0,
            },
            "github_inbound": {"validated_count": 0, "real_trigger_present": False},
        }
        (self.root / ".omega" / "wake-plane" / "heartbeat.json").write_text(
            json.dumps(heartbeat), encoding="utf-8"
        )
        (self.root / ".omega" / "wake-plane" / "sources.json").write_text(
            json.dumps(sources), encoding="utf-8"
        )
        runtime = self.root / ".omega" / "runtime"
        runtime.mkdir(parents=True)
        benchmark = {
            "format": "omega.claude-shadow-benchmark", "shadow_result": "PASS",
            "tasks": [
                {"task_id": f"task-{index}", "host_verified_success": True,
                 "duration_seconds": duration}
                for index, duration in enumerate((10.898, 19.046, 13.098), 1)
            ],
            "regression_rate": 0.0,
        }
        raw = json.dumps(benchmark, sort_keys=True).encode("utf-8")
        (runtime / "claude_shadow_benchmark.json").write_bytes(raw)

    def tearDown(self):
        self.temp.cleanup()

    def test_frozen_order_sources_and_diagnostics(self):
        units = probability_units()
        self.assertEqual(UNIT_IDS, [unit.knowledge_id for unit in units])
        self.assertEqual(14, len(units))
        seen = set()
        for unit in units:
            self.assertTrue(set(unit.prerequisites).issubset(seen))
            seen.add(unit.knowledge_id)
            source = unit.source_evidence[0]
            self.assertTrue(source.url.startswith("https://"))
            self.assertTrue(source.content_claim_hash)
            self.assertEqual("VERIFIED_2026-08-30", source.freshness)
            self.assertEqual([], source.conflicts)
            evidence = diagnostic_evidence(unit.knowledge_id)
            self.assertTrue(evidence["active_recall"])
            self.assertTrue(evidence["novel_problem"])
            self.assertTrue(evidence["passed"])

    def test_park_gate_fails_closed_on_material_trigger(self):
        self.assertTrue(park_eligibility(self.root)["eligible"])
        path = self.root / ".omega" / "wake-plane" / "sources.json"
        sources = json.loads(path.read_text(encoding="utf-8"))
        sources["github_inbound"]["real_trigger_present"] = True
        path.write_text(json.dumps(sources), encoding="utf-8")
        result = park_eligibility(self.root)
        self.assertFalse(result["eligible"])
        self.assertEqual([{"source": "github_inbound", "count": 1}], result["material_triggers"])

    def test_three_successes_are_insufficient_not_promoted(self):
        result = run_statistical_application(self.root)
        self.assertTrue(result["passed"])
        self.assertEqual("PASS", result["baseline_classification"])
        self.assertEqual("INSUFFICIENT_EVIDENCE", result["classification"])
        self.assertFalse(result["sample_sufficient"])
        self.assertLess(result["observations"]["wilson_95"][0], 0.8)
        self.assertEqual("IMPROVED", result["uncertainty_visibility"])
        self.assertEqual("SHADOW_CANDIDATE", result["capability_state"])
        self.assertFalse(result["replicated"])
        self.assertEqual("UNCHANGED", result["production_routing"])

    def test_campaign_completes_once_and_preserves_bootstrap(self):
        first = run_probability_campaign(self.root, trigger_check=lambda _: False)
        second = run_probability_campaign(self.root, trigger_check=lambda _: False)
        self.assertEqual("COMPLETED", first["campaign"]["status"])
        self.assertEqual(first["integrity_hash"], second["integrity_hash"])
        self.assertEqual({"passed": 14, "failed": 0, "total": 14}, first["assessment_summary"])
        self.assertEqual("TASK_COMPLETED", first["task_continuity"]["task_state"])
        self.assertEqual("PASS", first["task_continuity"]["host_verification"])
        self.assertEqual("PASS", first["active_recall"])
        self.assertEqual("PASS", first["novel_problem_transfer"])
        self.assertEqual(0, first["trusted_on_first_cycle"])
        self.assertEqual("UNCHANGED", first["production_routing"])
        self.assertFalse((self.root / ".omega" / "task_continuity" / "tasks" /
                          "learning-bootstrap-001.json").exists())
        self.assertEqual(TASK_ID, probability_campaign_status(self.root)["campaign"]["durable_task_id"])

    def test_real_work_preempts_and_exact_resume_preserves_progress(self):
        preempted = run_probability_campaign(self.root, trigger_check=lambda _: True)
        self.assertEqual("PREEMPTED", preempted["campaign"]["status"])
        self.assertEqual("PARKED", preempted["task_continuity"]["task_state"])
        self.assertEqual("REAL_WORK_PREEMPTION", preempted["task_continuity"]["blocker"])
        resumed = run_probability_campaign(self.root, trigger_check=lambda _: False)
        self.assertEqual("COMPLETED", resumed["campaign"]["status"])
        self.assertEqual(14, len(resumed["campaign"]["completed_units"]))
        task = TaskContinuityStore(self.root / ".omega" / "task_continuity").load_task(TASK_ID)
        self.assertEqual("TASK_COMPLETED", task.state)
        self.assertEqual(2, len(task.session_lineage))


if __name__ == "__main__":
    unittest.main()
