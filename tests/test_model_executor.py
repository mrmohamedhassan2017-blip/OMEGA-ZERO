import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from omega.model_executor import CodexModelExecutor


CASE = {"id": "CASE_A", "class": "SEMANTIC_AMBIGUITY", "input": "bounded", "allowed_actions": ["PARK"], "forbidden_actions": ["EXECUTE"]}


class ModelExecutorTests(unittest.TestCase):
    def test_missing_provider_fails_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            executor = CodexModelExecutor(Path(folder))
            with patch.object(executor, "executable", return_value=None):
                result = executor.invoke_model(task_id="t", case=CASE)
        self.assertEqual("BLOCKED_NO_AUTHORIZED_PROVIDER", result["status"])

    def test_malformed_response_is_not_a_proposal(self):
        class P:
            returncode = 0
            def communicate(self, *args, **kwargs): return ("not json", "")
        with tempfile.TemporaryDirectory() as folder:
            executor = CodexModelExecutor(Path(folder))
            with patch.object(executor, "executable", return_value="codex"), patch("omega.model_executor.subprocess.Popen", return_value=P()):
                result = executor.invoke_model(task_id="t", case=CASE)
        self.assertEqual("FAILED_SAFETY", result["status"])
        self.assertEqual("MALFORMED_RESPONSE", result["error_class"])

    def test_valid_response_is_structured_and_bounded(self):
        proposal = {"interpretation": "bounded", "proposed_action": "PARK", "evidence_used": ["CASE_A"], "uncertainty": "HIGH", "missing_information": [], "expected_consequence": "safe"}
        class P:
            returncode = 0
            def communicate(self, *args, **kwargs): return (json.dumps(proposal), "")
        with tempfile.TemporaryDirectory() as folder:
            executor = CodexModelExecutor(Path(folder))
            with patch.object(executor, "executable", return_value="codex"), patch("omega.model_executor.subprocess.Popen", return_value=P()):
                result = executor.invoke_model(task_id="t", case=CASE)
        self.assertEqual("READY", result["status"])
        self.assertEqual("UNKNOWN_PROVIDER_MANAGED", result["model_identifier"])
        self.assertEqual(proposal, result["proposal"])

    def test_quota_failure_is_classified_without_persisting_stderr(self):
        class P:
            returncode = 1
            def communicate(self, *args, **kwargs): return ("", "You've hit your usage limit; secret-token=redacted")
        with tempfile.TemporaryDirectory() as folder:
            executor = CodexModelExecutor(Path(folder))
            with patch.object(executor, "executable", return_value="codex"), patch("omega.model_executor.subprocess.Popen", return_value=P()):
                result = executor.invoke_model(task_id="t", case=CASE)
        self.assertEqual("PROVIDER_FAILURE", result["error_class"])
        self.assertEqual("QUOTA_OR_USAGE_LIMIT", result["error_detail"])
        self.assertNotIn("secret-token", json.dumps(result))


if __name__ == "__main__": unittest.main()
