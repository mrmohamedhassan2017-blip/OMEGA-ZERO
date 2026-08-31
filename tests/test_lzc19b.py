import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from omega.lzc19b import run_recovery


class LZC19BTests(unittest.TestCase):
    def test_start_is_called_exactly_once_on_failure(self):
        calls = []
        def fail(root): calls.append(root); raise PermissionError("blocked")
        with tempfile.TemporaryDirectory() as folder, patch("omega.lzc19b._snapshot", return_value={}):
            result = run_recovery(Path(folder), start_fn=fail, task_snapshot_fn=lambda: {"state": "READY"})
        self.assertEqual(len(calls), 1); self.assertEqual(result["start_request_count"], 1)
        self.assertEqual(result["final_result"], "SUPERVISOR_RUNTIME_RECOVERY_FAILED")

    def test_start_failure_never_invokes_stop_or_retry(self):
        stopped = []
        with tempfile.TemporaryDirectory() as folder, patch("omega.lzc19b._snapshot", return_value={}):
            run_recovery(Path(folder), start_fn=lambda root: (_ for _ in ()).throw(RuntimeError("no")),
                         stop_fn=lambda root: stopped.append(root), task_snapshot_fn=lambda: {"state": "READY"})
        self.assertEqual(stopped, [])

    def test_core_and_authority_firewalls_on_failure(self):
        with tempfile.TemporaryDirectory() as folder, patch("omega.lzc19b._snapshot", return_value={}):
            result = run_recovery(Path(folder), start_fn=lambda root: (_ for _ in ()).throw(OSError("fail")),
                                  task_snapshot_fn=lambda: {"state": "READY"})
        self.assertTrue(result["core_api_spec_hash_valid"]); self.assertEqual(result["authority_violations"], 0)
        self.assertEqual(result["unsafe_process_terminations"], 0)

    @unittest.skipUnless(os.name == "nt", "Windows-only PowerShell process query")
    def test_worker_process_query_excludes_query_shell(self):
        from omega.lzc19b import _worker_processes
        with patch("omega.lzc19b.subprocess.run") as run:
            run.return_value.returncode = 0; run.return_value.stdout = "[]"
            self.assertEqual(_worker_processes(), [])
        command = run.call_args.args[0][-1]
        self.assertIn("-notlike '*powershell*'", command)
        self.assertIn("-notlike '*pwsh*'", command)


if __name__ == "__main__": unittest.main()
