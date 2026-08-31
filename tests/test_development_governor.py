import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from omega.development_governor import run_governor_cycle
from omega.wake_provenance import append_chain


class DevelopmentGovernorTests(unittest.TestCase):
    def make_repository(self, root: Path, *, evaluator_count: int = 0) -> None:
        canonical = str(root.resolve())
        (root / ".omega" / "wake-provenance").mkdir(parents=True)
        (root / "PROJECT_STATE.md").write_text(
            "---\n"
            "project_name: OMEGA\n"
            f"canonical_path: {canonical}\n"
            "version: 0.21.0\n"
            "status: verified-core\n"
            "last_verified: 2026-08-29T05:02:32+03:00\n"
            "current_milestone: V0.30 External Evaluator Evidence Collection\n"
            "test_result: 317 passed\n"
            "---\n"
            "REAL_ECONOMIC_VALUE = 0 KWD\n"
            "V0.30 remains WAITING_EXTERNAL_EVIDENCE.\n",
            encoding="utf-8",
        )
        (root / "NEXT_TASK.md").write_text(
            "---\n"
            "baseline_version: 0.21.0\n"
            "milestone: V0.30 External Evaluator Evidence Collection\n"
            "status: waiting_external_evidence\n"
            "---\n"
            "Collect two independently supplied evaluator sessions.\n",
            encoding="utf-8",
        )
        for name in ("ROADMAP.md", "PROGRESS.md", "CHANGELOG.md"):
            (root / name).write_text(f"# {name}\n", encoding="utf-8")
        journal = root / ".omega" / "wake-provenance" / "v0_30_evaluator_provenance.jsonl"
        for index in range(evaluator_count):
            append_chain(
                journal,
                {
                    "evidence_event_id": f"E-{index}",
                    "validation_status": "VALID",
                    "independence_status": "PROVEN_INDEPENDENT",
                    "source_actor_hash": f"actor-{index}",
                    "duplicate_of": None,
                },
                "evidence_event_id",
            )

    def test_cycle_identifies_external_blocker_and_executes_internal_checkpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repository(root)
            result = run_governor_cycle(root)
            self.assertEqual("OPERATED_INTERNAL_ONLY", result["state"])
            self.assertEqual("INDEPENDENT_EXTERNAL_EVIDENCE", result["primary_bottleneck"]["id"])
            self.assertEqual("EVOLUTION_MEMORY_COMPRESSION", result["selected_improvement"]["id"])
            self.assertEqual("WAIT_EXTERNAL", result["autonomous_continuation"])
            self.assertEqual(0, result["verified_economic_value_change"])
            self.assertFalse(result["selected_improvement"]["external_effect"])
            checkpoint = root / ".omega" / "zero" / "evolution_checkpoint_0001.json"
            cycle = root / ".omega" / "zero" / "development_governor_cycle_0001.json"
            self.assertTrue(checkpoint.is_file())
            self.assertTrue(cycle.is_file())
            saved = json.loads(checkpoint.read_text(encoding="utf-8"))
            self.assertEqual(result["implementation_result"]["checkpoint_hash"], saved["checkpoint_hash"])
            self.assertIn("governor never executes or grants authority", saved["new_invariants"])

    def test_checkpoint_sequence_is_append_only_and_source_hashed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repository(root)
            first = run_governor_cycle(root)
            (root / "PROJECT_STATE.md").write_text(
                (root / "PROJECT_STATE.md").read_text(encoding="utf-8") + "\nA material state change is recorded.\n",
                encoding="utf-8",
            )
            second = run_governor_cycle(root)
            self.assertEqual("governor-cycle-0001", first["cycle_id"])
            self.assertEqual("governor-cycle-0002", second["cycle_id"])
            self.assertNotEqual(
                first["implementation_result"]["checkpoint_hash"],
                second["implementation_result"]["checkpoint_hash"],
            )
            self.assertTrue((root / ".omega" / "zero" / "evolution_checkpoint_0001.json").is_file())
            self.assertTrue((root / ".omega" / "zero" / "evolution_checkpoint_0002.json").is_file())

    def test_governor_never_invokes_external_processes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repository(root)
            with patch.object(subprocess, "run", side_effect=AssertionError("external process called")):
                result = run_governor_cycle(root)
            self.assertEqual([], result["implementation_result"]["side_effects"])

    def test_two_evaluators_change_only_bottleneck_status_not_value_claim(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repository(root, evaluator_count=2)
            result = run_governor_cycle(root)
            self.assertEqual("OPEN", result["primary_bottleneck"]["status"])
            self.assertEqual("PRESENT_REQUIRES_GATE", result["repository_truth"]["external_evidence"])
            self.assertEqual(0, result["repository_truth"]["real_economic_value_kwd"])


if __name__ == "__main__":
    unittest.main()
