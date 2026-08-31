from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from omega.quota_lifeline import (
    bounded_probe,
    manually_rearm_after_usage_refresh,
    park_for_resource_wait,
    quota_lifeline_status,
    record_codex_usage_snapshot,
    record_material_wake,
    rehydrate_same_task,
)


class QuotaLifelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.repo = self.root / "repo"
        self.repo.mkdir()
        (self.root / "omega").mkdir()
        for name in (
            "engine.py", "store.py", "api.py", "supervisor.py", "wake_plane.py",
            "wake_provenance.py", "gmail_adapter.py", "capability_discovery.py",
            "development_governor.py", "zpa.py", "evaluation.py", "zero_truth.py",
            "claude_backend.py",
        ):
            (self.root / "omega" / name).write_text(name, encoding="utf-8")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_parks_in_read_only_mode_and_records_verified_retry(self) -> None:
        result = park_for_resource_wait(
            self.root,
            task_id="quota-task",
            task_class="CODE_REPAIR",
            objective="resume same task after quota wait",
            session_id="session-1",
            repository_root=self.repo,
            completed_steps=["STEP_ONE"],
            next_action="STEP_TWO",
            retry_at="2026-08-30T09:00:00+03:00",
            authority_envelope_id="authority-1",
        )
        self.assertEqual("WAITING_RESOURCE", result["state"])
        self.assertTrue(result["read_only_safe_mode"])
        self.assertTrue(result["verified_retry_timestamp"])
        self.assertFalse(result["provider_rotation"])
        self.assertFalse(result["production_routing_changed"])
        self.assertFalse(result["preb"]["wake"]["retry_storm"])
        self.assertEqual("WAITING_RESOURCE", result["task_continuity_status"]["recovery_strategy"])

    def test_requires_material_wake_and_only_one_bounded_probe(self) -> None:
        park_for_resource_wait(
            self.root,
            task_id="quota-task",
            task_class="CODE_REPAIR",
            objective="resume same task after quota wait",
            session_id="session-1",
            repository_root=self.repo,
            completed_steps=["STEP_ONE"],
            next_action="STEP_TWO",
            authority_envelope_id="authority-1",
        )
        with self.assertRaises(Exception):
            bounded_probe(self.root, task_id="quota-task", provider_available=True)
        record_material_wake(self.root, task_id="quota-task", trigger="PROVIDER_RECOVERY", source="wake-plane")
        bounded_probe(self.root, task_id="quota-task", provider_available=False, observed_at="2026-08-30T09:01:00+03:00")
        with self.assertRaises(Exception):
            bounded_probe(self.root, task_id="quota-task", provider_available=True, observed_at="2026-08-30T09:02:00+03:00")

    def test_rehydrates_same_task_after_wake_and_successful_probe(self) -> None:
        park_for_resource_wait(
            self.root,
            task_id="quota-task",
            task_class="CODE_REPAIR",
            objective="resume same task after quota wait",
            session_id="session-1",
            repository_root=self.repo,
            completed_steps=["STEP_ONE"],
            next_action="STEP_TWO",
            authority_envelope_id="authority-1",
        )
        record_material_wake(self.root, task_id="quota-task", trigger="PROVIDER_RECOVERY", source="wake-plane")
        bounded_probe(self.root, task_id="quota-task", provider_available=True, observed_at="2026-08-30T09:01:00+03:00")
        resumed = rehydrate_same_task(
            self.root,
            task_id="quota-task",
            session_id="session-2",
            repository_root=self.repo,
            authority_envelope_id="authority-1",
        )
        self.assertEqual("TASK_RESUMED", resumed["state"])
        self.assertEqual("session-2", resumed["session_id"])
        self.assertEqual("TASK_RESUMED", resumed["task_continuity_status"]["task_state"])
        self.assertEqual(["session-1", "session-2"], resumed["task_continuity_status"]["session_lineage"])

    def test_status_reads_saved_record(self) -> None:
        park_for_resource_wait(
            self.root,
            task_id="quota-task",
            task_class="CODE_REPAIR",
            objective="resume same task after quota wait",
            session_id="session-1",
            repository_root=self.repo,
            completed_steps=[],
            next_action="STEP_TWO",
        )
        self.assertEqual("quota-task", quota_lifeline_status(self.root, "quota-task")["task_id"])

    def test_records_independent_verified_five_hour_and_weekly_usage(self) -> None:
        park_for_resource_wait(
            self.root, task_id="quota-task", task_class="CODE_REPAIR", objective="resume",
            session_id="session-1", repository_root=self.repo, completed_steps=[], next_action="STEP_TWO",
        )
        record = record_codex_usage_snapshot(
            self.root, task_id="quota-task", source="CODEX_USAGE_DASHBOARD",
            observed_at="2026-08-30T09:00:00+03:00", five_hour_state="EXHAUSTED",
            five_hour_reset_at="2026-08-30T14:00:00+03:00", weekly_state="AVAILABLE",
        )
        usage = record["codex_usage"]
        self.assertFalse(usage["usable"])
        self.assertEqual("2026-08-30T14:00:00+03:00", usage["next_retry_at"])
        self.assertTrue(usage["five_hour"]["verified_reset_timestamp"])
        self.assertFalse(usage["estimated"])
        self.assertFalse(usage["reset_consumed"])

    def test_exhausted_usage_requires_verified_reset_timestamp(self) -> None:
        park_for_resource_wait(
            self.root, task_id="quota-task", task_class="CODE_REPAIR", objective="resume",
            session_id="session-1", repository_root=self.repo, completed_steps=[], next_action="STEP_TWO",
        )
        with self.assertRaises(ValueError):
            record_codex_usage_snapshot(
                self.root, task_id="quota-task", source="CODEX_CLI_STATUS",
                observed_at="2026-08-30T09:00:00+03:00", five_hour_state="EXHAUSTED", weekly_state="AVAILABLE",
            )

    def test_manual_rearm_requires_owner_observed_refresh_then_allows_one_probe(self) -> None:
        park_for_resource_wait(
            self.root, task_id="quota-task", task_class="CODE_REPAIR", objective="resume",
            session_id="session-1", repository_root=self.repo, completed_steps=[], next_action="STEP_TWO",
        )
        record = manually_rearm_after_usage_refresh(
            self.root, task_id="quota-task", source="CODEX_CLI_STATUS", observed_at="2026-08-30T14:00:00+03:00",
        )
        self.assertTrue(record["material_wake_seen"])
        self.assertTrue(quota_lifeline_status(self.root, "quota-task")["codex_usage"]["usable"])
        bounded_probe(self.root, task_id="quota-task", provider_available=True)
        with self.assertRaises(Exception):
            bounded_probe(self.root, task_id="quota-task", provider_available=True)


if __name__ == "__main__":
    unittest.main()
