import json
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from omega.claude_backend import (
    ClaudeCodeBackend,
    TaskEnvelope,
    backend_status,
    read_backend_history,
)


class FixtureBackend(ClaudeCodeBackend):
    def __init__(self, root: Path, script: str, history_path: Path | None = None):
        super().__init__(root, executable=sys.executable, history_path=history_path)
        self.script = script

    def _command(self, envelope, run_id):
        return [sys.executable, "-c", self.script]


def envelope(**overrides):
    values = {
        "task_id": "claude-test-001",
        "task_class": "CODE_REPAIR",
        "objective": "Apply the bounded fixture change.",
        "allowed_paths": ("allowed/**",),
        "expected_change_class": "SOURCE_MODIFICATION",
        "max_duration": 5,
        "resource_budget": {"max_output_bytes": 4096, "max_backend_attempts": 1},
        "authority_class": "INTERNAL_ISOLATED_WRITE",
    }
    values.update(overrides)
    return TaskEnvelope(**values)


class ClaudeBackendTests(unittest.TestCase):
    def repository(self):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name).resolve()
        (root / "allowed").mkdir()
        (root / "allowed" / "existing.txt").write_text("before", encoding="utf-8")
        return temp, root

    def test_task_envelope_fails_closed_for_authority_and_paths(self):
        for item in (
            envelope(external_write_policy="ALLOWED"),
            envelope(financial_policy="ALLOWED"),
            envelope(allowed_paths=("../escape",)),
            envelope(allowed_paths=(), expected_change_class="SOURCE_MODIFICATION"),
        ):
            with self.assertRaises(ValueError):
                item.validate()

    def test_read_only_execution_accepts_unicode_without_self_verification(self):
        temp, root = self.repository()
        try:
            task = envelope(task_class="STATIC_REVIEW", allowed_paths=(), expected_change_class="NONE",
                            authority_class="INTERNAL_READ_ONLY")
            result = FixtureBackend(root, "print('تحليل آمن')").execute_envelope(task, root)
            self.assertTrue(result["ok"])
            self.assertIn("تحليل آمن", result["stdout_summary"])
            self.assertEqual([], result["files_changed"])
            self.assertFalse(result["verified_success"])
            self.assertTrue(result["host_verification_required"])
        finally:
            temp.cleanup()

    def test_allowed_change_is_detected_but_remains_host_unverified(self):
        temp, root = self.repository()
        try:
            script = "from pathlib import Path;Path('allowed/fix.py').write_text('fixed',encoding='utf-8');print('done')"
            result = FixtureBackend(root, script).execute_envelope(envelope(), root)
            self.assertTrue(result["ok"])
            self.assertEqual(["allowed/fix.py"], result["files_changed"])
            self.assertTrue(result["diff_hash"])
            self.assertEqual("COMPLETED_PENDING_HOST_VERIFICATION", result["result_state"])
            self.assertFalse(result["verified_success"])
        finally:
            temp.cleanup()

    def test_success_claim_without_expected_change_is_no_changes(self):
        temp, root = self.repository()
        try:
            result = FixtureBackend(root, "print('implemented')").execute_envelope(envelope(), root)
            self.assertFalse(result["ok"])
            self.assertEqual("NO_CHANGES", result["failure_class"])
            self.assertFalse(result["claimed_success"])
        finally:
            temp.cleanup()

    def test_unexpected_change_fails_scope(self):
        temp, root = self.repository()
        try:
            script = "from pathlib import Path;Path('outside.txt').write_text('bad',encoding='utf-8')"
            result = FixtureBackend(root, script).execute_envelope(envelope(), root)
            self.assertFalse(result["ok"])
            self.assertEqual("TASK_SCOPE_VIOLATION", result["failure_class"])
            self.assertIn("outside-allowlist:outside.txt", result["scope_violations"])
        finally:
            temp.cleanup()

    def test_deletion_and_binary_changes_fail_closed(self):
        temp, root = self.repository()
        try:
            script = ("from pathlib import Path;Path('allowed/existing.txt').unlink();"
                      "Path('allowed/blob.bin').write_bytes(b'\\x00unsafe')")
            result = FixtureBackend(root, script).execute_envelope(envelope(), root)
            self.assertEqual("TASK_SCOPE_VIOLATION", result["failure_class"])
            self.assertIn("deleted:allowed/existing.txt", result["scope_violations"])
            self.assertIn("binary:allowed/blob.bin", result["scope_violations"])
        finally:
            temp.cleanup()

    def test_timeout_terminates_only_owned_process(self):
        temp, root = self.repository()
        try:
            task = envelope(max_duration=1)
            started = time.monotonic()
            result = FixtureBackend(root, "import time;time.sleep(20)").execute_envelope(task, root)
            self.assertEqual("TIMEOUT", result["failure_class"])
            self.assertEqual("PASS", result["cleanup_state"])
            self.assertLess(time.monotonic() - started, 5)
        finally:
            temp.cleanup()

    def test_explicit_cancel_targets_owned_run(self):
        temp, root = self.repository()
        try:
            backend = FixtureBackend(root, "import time;time.sleep(20)")
            output = {}
            thread = threading.Thread(target=lambda: output.update(backend.execute_envelope(envelope(max_duration=10), root)))
            thread.start()
            deadline = time.monotonic() + 3
            run_id = None
            while time.monotonic() < deadline:
                with backend._lock:
                    run_id = next(iter(backend._runs), None)
                if run_id:
                    break
                time.sleep(0.02)
            self.assertIsNotNone(run_id)
            self.assertTrue(backend.cancel(run_id))
            thread.join(timeout=5)
            self.assertFalse(thread.is_alive())
            self.assertEqual("CANCELLED", output["failure_class"])
            self.assertEqual("COMPLETED", output["cancellation_state"])
        finally:
            temp.cleanup()

    def test_wrong_workdir_is_rejected_before_process_start(self):
        first, root = self.repository()
        second = tempfile.TemporaryDirectory()
        try:
            backend = FixtureBackend(root, "raise SystemExit('must not run')")
            with patch("omega.claude_backend.subprocess.Popen") as popen:
                result = backend.execute_envelope(envelope(), Path(second.name))
            popen.assert_not_called()
            self.assertEqual("INVALID_TASK_ENVELOPE", result["failure_class"])
        finally:
            first.cleanup(); second.cleanup()

    def test_provider_failures_are_classified_without_retry(self):
        temp, root = self.repository()
        try:
            script = "import sys;sys.stderr.write('usage quota reached');sys.exit(1)"
            result = FixtureBackend(root, script).execute_envelope(
                envelope(task_class="STATIC_REVIEW", allowed_paths=(), expected_change_class="NONE"), root
            )
            self.assertEqual("USAGE_QUOTA_LIMIT", result["failure_class"])
            self.assertEqual("WAITING_RESOURCE", result["resource_state"])
        finally:
            temp.cleanup()

    def test_output_is_bounded_and_secrets_are_redacted(self):
        temp, root = self.repository()
        try:
            script = "print('A'*9000);print('api_key=top-secret-value')"
            task = envelope(task_class="STATIC_REVIEW", allowed_paths=(), expected_change_class="NONE")
            result = FixtureBackend(root, script).execute_envelope(task, root)
            self.assertLessEqual(len(result["stdout_summary"].encode("utf-8")), 4096)
            self.assertNotIn("top-secret-value", result["stdout_summary"])
            self.assertIn("[REDACTED]", result["stdout_summary"])
        finally:
            temp.cleanup()

    def test_history_contains_evidence_not_provider_output(self):
        temp, root = self.repository()
        try:
            history = root / ".runtime" / "history.jsonl"
            task = envelope(task_class="STATIC_REVIEW", allowed_paths=(), expected_change_class="NONE")
            FixtureBackend(root, "print('private provider output')", history).execute_envelope(task, root)
            rows = read_backend_history(history)
            self.assertEqual(1, len(rows))
            raw = history.read_text(encoding="utf-8")
            self.assertNotIn("private provider output", raw)
            self.assertNotIn("stdout_summary", rows[0])
            self.assertFalse(rows[0]["verified_success"])
        finally:
            temp.cleanup()

    def test_discovery_allowlists_auth_fields_and_detects_noninteractive_mode(self):
        temp, root = self.repository()
        try:
            version = type("Completed", (), {"returncode": 0, "stdout": "2.1.239 (Claude Code)", "stderr": ""})()
            help_result = type("Completed", (), {"returncode": 0, "stdout": "--print --permission-mode", "stderr": ""})()
            auth = type("Completed", (), {"returncode": 0, "stdout": json.dumps({
                "loggedIn": True, "authMethod": "claude.ai", "apiProvider": "firstParty",
                "email": "private@example.test", "accessToken": "do-not-copy",
            }), "stderr": ""})()
            backend = ClaudeCodeBackend(root, executable="claude.exe")
            with patch.object(backend, "_probe", side_effect=[version, help_result, auth]):
                result = backend.discover()
            self.assertEqual("2.1.239", result["version"])
            self.assertEqual("AUTHENTICATED", result["authentication_state"])
            self.assertEqual("SUPPORTED", result["noninteractive_mode"])
            self.assertNotIn("email", result)
            self.assertNotIn("accessToken", result)
            self.assertNotIn("do-not-copy", json.dumps(result))
        finally:
            temp.cleanup()

    def test_backend_status_preserves_shadow_and_codex_default(self):
        temp, root = self.repository()
        try:
            status = {"cli_found": True, "authentication_state": "AUTHENTICATED",
                      "noninteractive_mode": "SUPPORTED", "available": True, "resource_state": "ACTIVE"}
            with patch.object(ClaudeCodeBackend, "availability", return_value=status):
                result = backend_status(root)
            self.assertEqual("SHADOW", result["router_mode"])
            self.assertEqual("CODEX_BACKEND", result["production_default"])
            self.assertEqual("SHADOW_ONLY", result["backends"]["CLAUDE_CODE_BACKEND"]["routing"])
            self.assertEqual("NONE", result["backends"]["CLAUDE_CODE_BACKEND"]["financial_authority"])
        finally:
            temp.cleanup()


if __name__ == "__main__":
    unittest.main()
