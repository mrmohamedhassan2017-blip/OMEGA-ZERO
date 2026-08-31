import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from omega.claude_backend import ClaudeCodeBackend
from omega.claude_omniroute_canary import run_nonce_canary


class FakeCanaryBackend(ClaudeCodeBackend):
    def __init__(self, root: Path, response: str, *, backend_id: str = "CLAUDE_CODE_BACKEND"):
        super().__init__(root, executable="fake-claude")
        self.response = response
        self.backend_id_override = backend_id

    def execute_envelope(self, envelope, root, *, on_started=None):
        if on_started:
            on_started("run-fixture", 12345)
        expected = envelope.objective.split("Return exactly:", 1)[1].split("and no additional text.", 1)[0].strip()
        stdout = self.response.replace("<EXPECTED>", expected)
        return {
            "ok": True,
            "backend_id": self.backend_id_override,
            "provider": "ANTHROPIC_CLAUDE_CODE",
            "run_id": "run-fixture",
            "pid": 12345,
            "returncode": 0,
            "result_state": "COMPLETED_PENDING_HOST_VERIFICATION",
            "failure_class": None,
            "files_changed": [],
            "cleanup_state": "PASS",
            "stdout_summary": stdout,
        }


def available_registry(_root):
    return {
        "capabilities": [
            {
                "capability_id": "claude-code-backend",
                "capability_class": "CODE_GENERATION",
                "provider": "ANTHROPIC_CLAUDE_CODE",
                "availability": "AVAILABLE",
                "confidence": 0.9,
                "adoption_state": "CONTROLLED",
                "latency_class": "interactive",
                "resource_cost": "provider-dependent",
                "authority_required": "provider account and bounded task envelope",
                "external_side_effect": False,
            }
        ]
    }


class ClaudeOmniRouteCanaryTests(unittest.TestCase):
    def test_nonce_bound_canary_requires_route_and_exact_nonce(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            with patch("omega.claude_omniroute_canary.discover_capabilities", side_effect=available_registry):
                result = run_nonce_canary(root, backend_factory=lambda path: FakeCanaryBackend(path, "<EXPECTED>"))
            self.assertEqual("PASS", result["canary_result"], json.dumps(result, indent=2))
            self.assertEqual("VERIFIED", result["zero_to_claude_route_state"])
            self.assertTrue(result["omniroute_actually_invoked"])
            self.assertTrue(result["claude_actually_invoked"])
            self.assertEqual([], result["backend_result"]["files_changed"])

    def test_correct_text_from_wrong_backend_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            with patch("omega.claude_omniroute_canary.discover_capabilities", side_effect=available_registry):
                result = run_nonce_canary(root, backend_factory=lambda path: FakeCanaryBackend(path, "<EXPECTED>", backend_id="CODEX_BACKEND"))
            self.assertEqual("FAIL", result["canary_result"])
            self.assertIn("CLAUDE_ACTUALLY_INVOKED", result["host_verification"]["failures"])

    def test_stale_or_wrong_nonce_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            with patch("omega.claude_omniroute_canary.discover_capabilities", side_effect=available_registry):
                result = run_nonce_canary(root, backend_factory=lambda path: FakeCanaryBackend(path, "ZERO_CLAUDE_OMNIROUTE_CANARY_OK::deadbeef"))
            self.assertEqual("FAIL", result["canary_result"])
            self.assertIn("EXPECTED_EQUALS_ACTUAL", result["host_verification"]["failures"])
            self.assertIn("ACTUAL_NONCE_EQUALS_GENERATED_NONCE", result["host_verification"]["failures"])


if __name__ == "__main__":
    unittest.main()
