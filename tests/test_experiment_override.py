import tempfile
import unittest
from pathlib import Path

from omega.experiment_override import (disable_experiment_override, enable_experiment_override,
                                       evaluate_experiment_authority, read_experiment_state)


class ExperimentOverrideTests(unittest.TestCase):
    def test_internal_actions_are_temporarily_authorized_and_recorded(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = enable_experiment_override(root, task_id="task-1", max_runtime_minutes=120)
            self.assertTrue(state["enabled"])
            allowed = evaluate_experiment_authority(root, action="run internal tests", task_id="task-1")
            self.assertTrue(allowed["allowed"])
            self.assertEqual(allowed["authority_source"], "EXPERIMENT_OVERRIDE")
            self.assertEqual(allowed["action_class"], "A1_INTERNAL_EXECUTION")
            events = (root / ".omega/zero/experiment/events.jsonl").read_text(encoding="utf-8")
            self.assertIn("EXPERIMENT_OVERRIDE_ACTIVATED", events)
            self.assertIn("EXPERIMENT_AUTHORITY_EVALUATED", events)

    def test_external_financial_security_and_unknown_actions_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            enable_experiment_override(root)
            for action in ("send email to user", "purchase subscription", "scan target", ""):
                result = evaluate_experiment_authority(root, action=action)
                self.assertFalse(result["allowed"], action)
                self.assertEqual(result["authority_source"], "NORMAL_AUTHORITY_REQUIRED")

    def test_disable_restores_normal_rules_without_losing_state_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            enable_experiment_override(root, task_id="task-1")
            disabled = disable_experiment_override(root, reason="test restore")
            self.assertFalse(disabled["enabled"])
            self.assertFalse(read_experiment_state(root)["enabled"])
            result = evaluate_experiment_authority(root, action="run internal tests", task_id="task-1")
            self.assertFalse(result["allowed"])


if __name__ == "__main__":
    unittest.main()

