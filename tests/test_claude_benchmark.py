import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from omega.claude_benchmark import (
    freeze_multi_backend_tasks,
    run_documentation_canary,
    run_multi_backend_shadow_benchmark,
    run_shadow_benchmark,
)


class ClaudeBenchmarkTests(unittest.TestCase):
    def repository(self):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name).resolve()
        (root / ".omega" / "runtime").mkdir(parents=True)
        (root / "docs").mkdir()
        return temp, root

    @staticmethod
    def successful_shadow(self_backend, task, root):
        if task.task_id.endswith("bug-repair"):
            (root / "calculator.py").write_text("def add(left, right):\n    return left + right\n", encoding="utf-8")
            changed = ["calculator.py"]
        elif task.task_id.endswith("test-generation"):
            (root / "test_slug.py").write_text(
                "import unittest\nfrom slug import slugify\nclass T(unittest.TestCase):\n"
                " def test_spacing(self): self.assertEqual('a-b',slugify(' A  B '))\n"
                " def test_empty(self): self.assertEqual('',slugify(''))\n", encoding="utf-8")
            changed = ["test_slug.py"]
        else:
            (root / "README.md").write_text("Timeout is 30 seconds with 2 attempts.\n", encoding="utf-8")
            changed = ["README.md"]
        return {"ok": True, "result_state": "COMPLETED_PENDING_HOST_VERIFICATION", "returncode": 0,
                "duration_seconds": 1.0, "files_changed": changed, "diff_hash": "h", "failure_class": None,
                "cleanup_state": "PASS", "claimed_success": True, "scope_violations": []}

    def test_shadow_requires_host_verified_results(self):
        temp, root = self.repository()
        try:
            with patch("omega.claude_benchmark.ClaudeCodeBackend.execute_envelope", autospec=True,
                       side_effect=self.successful_shadow):
                result = run_shadow_benchmark(root)
            self.assertEqual("PASS", result["shadow_result"], json.dumps(result, ensure_ascii=False, indent=2))
            self.assertEqual(3, result["verified_successes"])
            self.assertEqual(0, result["false_success_count"])
            self.assertEqual(0, result["scope_violations"])
        finally:
            temp.cleanup()

    def test_canary_never_runs_before_shadow_passes(self):
        temp, root = self.repository()
        try:
            with patch("omega.claude_benchmark.ClaudeCodeBackend.execute_envelope") as execute:
                result = run_documentation_canary(root)
            execute.assert_not_called()
            self.assertEqual("NOT_RUN", result["canary_result"])
        finally:
            temp.cleanup()

    def test_canary_is_one_file_host_verified_and_registry_eligible(self):
        temp, root = self.repository()
        try:
            shadow = root / ".omega" / "runtime" / "claude_shadow_benchmark.json"
            shadow.write_text(json.dumps({"shadow_result": "PASS"}), encoding="utf-8")

            def execute(_backend, _task, repository):
                path = repository / "docs" / "CLAUDE_BACKEND.md"
                path.write_text("TaskEnvelope; Host Verification; SHADOW; external NONE; financial NONE\n", encoding="utf-8")
                return {"ok": True, "result_state": "COMPLETED_PENDING_HOST_VERIFICATION", "returncode": 0,
                        "duration_seconds": 1.0, "files_changed": ["docs/CLAUDE_BACKEND.md"], "diff_hash": "h",
                        "failure_class": None, "claimed_success": True, "scope_violations": [], "cleanup_state": "PASS"}

            completed = type("Completed", (), {"returncode": 0, "stdout": "", "stderr": ""})()
            with patch("omega.claude_benchmark.ClaudeCodeBackend.execute_envelope", autospec=True, side_effect=execute), \
                 patch("omega.claude_benchmark.subprocess.run", return_value=completed):
                result = run_documentation_canary(root)
            self.assertEqual("PASS", result["canary_result"])
            status = json.loads((root / ".omega" / "runtime" / "claude_backend_status.json").read_text(encoding="utf-8"))
            self.assertTrue(status["capability_registry_eligible"])
            self.assertEqual("READY", status["router_shadow_result"])
        finally:
            temp.cleanup()

    def test_multi_backend_shadow_freezes_twelve_tasks_and_does_not_promote(self):
        temp, root = self.repository()
        try:
            packet = freeze_multi_backend_tasks(root)
            self.assertEqual(12, packet["task_count"])
            self.assertEqual(12, len(set(task["prompt_hash"] for task in packet["tasks"])))
            self.assertTrue(all(task["authority_class"] == "INTERNAL_SHADOW_ONLY" for task in packet["tasks"]))
            result = run_multi_backend_shadow_benchmark(root)
            self.assertEqual("KEEP_SHADOW", result["promotion_recommendation"])
            self.assertFalse(result["production_routing_changed"])
            self.assertFalse(result["default_provider_changed"])
            self.assertEqual(0, result["external_actions"])
            self.assertEqual(0, result["financial_actions"])
            self.assertEqual(0, result["authority_violations"])
            self.assertEqual("INSUFFICIENT_EVIDENCE", result["overall_statistical_result"])
        finally:
            temp.cleanup()

    def test_multi_backend_shadow_imports_only_real_existing_claude_evidence(self):
        temp, root = self.repository()
        try:
            runtime = root / ".omega" / "runtime"
            runtime.mkdir(parents=True, exist_ok=True)
            (runtime / "claude_backend_status.json").write_text(
                json.dumps({"canary_result": "PASS", "resource_state": "ACTIVE"}),
                encoding="utf-8",
            )
            (runtime / "claude_shadow_benchmark.json").write_text(
                json.dumps({
                    "shadow_result": "PASS",
                    "task_count": 3,
                    "verified_successes": 3,
                    "median_duration_seconds": 10,
                    "no_change_count": 0,
                    "tasks": [
                        {"task_class": "CODE_REPAIR", "host_verified_success": True},
                        {"task_class": "TEST_GENERATION", "host_verified_success": True},
                        {"task_class": "DOCUMENTATION_UPDATE", "host_verified_success": True},
                    ],
                }),
                encoding="utf-8",
            )
            result = run_multi_backend_shadow_benchmark(root)
            self.assertEqual(3, result["claude_valid_trials"])
            self.assertEqual(3, result["claude_success_count"])
            self.assertEqual(0, result["codex_valid_trials"])
            self.assertEqual("NOT_MEASURED", result["codex_verified_success_rate"])
            self.assertEqual("KEEP_SHADOW", result["promotion_recommendation"])
        finally:
            temp.cleanup()


if __name__ == "__main__":
    unittest.main()
