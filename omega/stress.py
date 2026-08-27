from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from .store import Store


def write_batch(db_path: str, worker: int, count: int) -> None:
    store = Store(db_path)
    for index in range(count):
        problem = store.create_problem(f"worker-{worker}-problem-{index}", "concurrency stress")
        store.add_node(problem["id"], "unknown", f"worker-{worker}-unknown-{index}", role="question")


def run_concurrency_stress(workers: int = 4, writes_per_worker: int = 8) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmp:
        db_path = str(Path(tmp) / "stress.db"); Store(db_path)
        processes = [subprocess.Popen(
            [sys.executable, "-m", "omega.stress", "worker", "--db", db_path,
             "--worker", str(worker), "--count", str(writes_per_worker)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for worker in range(workers)]
        details = []
        for worker, process in enumerate(processes):
            try:
                stdout, stderr = process.communicate(timeout=30)
                details.append({"worker": worker, "returncode": process.returncode,
                                "stderr": stderr.strip()[-500:], "stdout": stdout.strip()[-500:]})
            except subprocess.TimeoutExpired:
                process.kill(); stdout, stderr = process.communicate()
                details.append({"worker": worker, "returncode": None, "stderr": "timeout", "stdout": stdout[-500:]})
        store = Store(db_path); health = store.database_health(); expected = workers * writes_per_worker
        unique_titles = len({problem["title"] for problem in store.list_problems()})
        passed = (all(item["returncode"] == 0 for item in details) and health["healthy"]
                  and health["counts"]["problems"] == expected and health["counts"]["nodes"] == expected
                  and unique_titles == expected)
        return {"passed": passed, "workers": workers, "writes_per_worker": writes_per_worker,
                "expected_writes": expected, "database": health, "processes": details}


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    worker = sub.add_parser("worker"); worker.add_argument("--db", required=True)
    worker.add_argument("--worker", type=int, required=True); worker.add_argument("--count", type=int, required=True)
    args = parser.parse_args()
    if args.command == "worker":
        write_batch(args.db, args.worker, args.count)


if __name__ == "__main__":
    main()
