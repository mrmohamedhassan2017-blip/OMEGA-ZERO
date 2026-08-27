from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from .engine import Engine
from .store import Store


def run_release_gates() -> dict[str, Any]:
    results = []
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp); store = Store(root / "source.db")
        problem = store.create_problem("Release gate", "Portable reasoning graph")
        claim = store.add_node(problem["id"], "assumption", "The core round-trips", 0.6, role="unverified_claim")
        evidence = store.add_node(problem["id"], "fact", "Tests ran", 0.9, [{
            "source": "release-gate", "observed_at": "2026-08-27", "method": "automated",
            "reliability": 0.9, "verification_status": "reproduced"}], role="event")
        store.add_edge(problem["id"], evidence["id"], claim["id"], "supports")

        first, second = store.export_problem(problem["id"]), store.export_problem(problem["id"])
        results.append({"gate": "deterministic-export", "passed": first == second, "sha256": first["sha256"]})

        imported_store = Store(root / "imported.db")
        imported = imported_store.import_problem(first)
        reexported = imported_store.export_problem(imported["problem_id"])
        results.append({"gate": "semantic-round-trip", "passed": reexported == first})
        validation = Engine(imported_store.graph(imported["problem_id"])).validate()
        results.append({"gate": "imported-graph-valid", "passed": validation["valid"], "issues": validation["issues"]})

        before = len(imported_store.list_problems()); tampered = {**first, "sha256": "0" * 64}
        try:
            imported_store.import_problem(tampered); rejected = False
        except ValueError:
            rejected = True
        results.append({"gate": "tamper-rejected-atomically",
                        "passed": rejected and len(imported_store.list_problems()) == before})

        backup_path = root / "backup.db"; backup = imported_store.backup_to(backup_path)
        imported_store.delete_problem(imported["problem_id"])
        restored = imported_store.restore_from(backup_path)
        results.append({"gate": "backup-restore", "passed": restored["problems"] == before and backup["bytes"] > 0})
    return {"gates": results, "passed": all(item["passed"] for item in results),
            "summary": {"passed": sum(item["passed"] for item in results), "total": len(results)}}
