import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from omega.continuity import REQUIRED_FILES, ROOT, execution_context, inspect_project, parse_front_matter


class ContinuityTests(unittest.TestCase):
    def make_repository(self, *, state_version="0.21.0", baseline="0.21.0", canonical=None):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        canonical = canonical or str(root.resolve())
        contents = {
            "PROJECT_STATE.md": (f"---\nproject_name: OMEGA\ncanonical_path: {canonical}\nversion: {state_version}\n"
                                 "status: verified\nlast_verified: 2026-08-27T06:52:42+03:00\n"
                                 "test_result: 60 passed\ncurrent_milestone: V0.21\nnext_milestone: V0.22\n---\n# State\n"),
            "NEXT_TASK.md": f"---\nbaseline_version: {baseline}\nmilestone: V0.22\nstatus: planned\n---\n# Next\n",
            "pyproject.toml": '[project]\nname="omega"\nversion="0.21.0"\n',
        }
        for name in REQUIRED_FILES:
            contents.setdefault(name, f"# {name}\n")
        for name, content in contents.items():
            path = root / name; path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        return temp, root

    def test_repository_continuity_is_consistent(self):
        status = inspect_project(ROOT)
        self.assertEqual("OK", status["continuity"])
        self.assertEqual("0.21.0", status["version"])
        self.assertEqual("V0.30 External Evaluator Evidence Collection", status["next_milestone"])

    def test_missing_and_corrupt_state_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            status = inspect_project(root)
            self.assertFalse(status["ready_to_continue"])
            self.assertTrue(status["missing"])
        temp, root = self.make_repository()
        try:
            (root / "PROJECT_STATE.md").write_text("not front matter", encoding="utf-8")
            with self.assertRaises(ValueError):
                parse_front_matter(root / "PROJECT_STATE.md")
            self.assertFalse(inspect_project(root)["ready_to_continue"])
        finally:
            temp.cleanup()

    def test_version_stale_task_and_path_mismatches_are_rejected(self):
        for kwargs, expected in (
            ({"state_version": "0.20.0"}, "version mismatch"),
            ({"baseline": "0.20.0"}, "stale"),
            ({"canonical": "C:\\wrong\\OMEGA" if sys.platform == "win32" else "/wrong/OMEGA"}, "canonical path mismatch"),
        ):
            temp, root = self.make_repository(**kwargs)
            try:
                status = inspect_project(root)
                self.assertFalse(status["ready_to_continue"])
                self.assertTrue(any(expected in error for error in status["errors"]))
            finally:
                temp.cleanup()

    def test_continue_context_contains_no_environment_or_credentials(self):
        context = execution_context(ROOT)
        self.assertIn("OMEGA PROJECT STATUS", context)
        self.assertIn("NEXT TASK", context)
        self.assertIn("V0.30 External Evaluator Evidence Collection", context)
        self.assertNotIn("API_KEY", context)
        self.assertNotIn("PASSWORD=", context)

    def test_status_cli_and_tool_execute(self):
        for command in (
            [sys.executable, "-m", "omega.cli", "project-status"],
            [sys.executable, "tools/project_status.py"],
        ):
            completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=180)
            self.assertEqual(0, completed.returncode, completed.stderr)
            self.assertIn("CONTINUITY: OK", completed.stdout)
            self.assertIn("READY TO CONTINUE: YES", completed.stdout)

    def test_continue_cli_prints_context_on_windows_console_encoding(self):
        completed = subprocess.run([sys.executable, "-m", "omega.cli", "continue"], cwd=ROOT,
                                   capture_output=True, timeout=30)
        self.assertEqual(0, completed.returncode, completed.stderr.decode(errors="replace"))
        output = completed.stdout.decode("utf-8")
        self.assertIn("OMEGA PROJECT STATUS", output)
        self.assertIn("NEXT TASK", output)


if __name__ == "__main__":
    unittest.main()
