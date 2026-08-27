from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

NODE_TYPES = {"fact", "assumption", "constraint", "unknown"}
EDGE_TYPES = {"depends_on", "supports", "contradicts", "relates_to"}


class Store:
    def __init__(self, path: str | Path = "data/omega.db") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        try:
            yield db
            db.commit()
        finally:
            db.close()

    def _init_schema(self) -> None:
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS schema_meta (
                    key TEXT PRIMARY KEY, value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS problems (
                    id TEXT PRIMARY KEY, title TEXT NOT NULL, description TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS nodes (
                    id TEXT PRIMARY KEY, problem_id TEXT NOT NULL REFERENCES problems(id) ON DELETE CASCADE,
                    type TEXT NOT NULL CHECK(type IN ('fact','assumption','constraint','unknown')),
                    statement TEXT NOT NULL, confidence REAL NOT NULL DEFAULT 0.5,
                    evidence TEXT NOT NULL DEFAULT '[]', status TEXT NOT NULL DEFAULT 'open',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS edges (
                    id TEXT PRIMARY KEY, problem_id TEXT NOT NULL REFERENCES problems(id) ON DELETE CASCADE,
                    source_id TEXT NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
                    target_id TEXT NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
                    type TEXT NOT NULL CHECK(type IN ('depends_on','supports','contradicts','relates_to')),
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(source_id, target_id, type)
                );
                INSERT OR REPLACE INTO schema_meta(key,value) VALUES('schema_version','1');
            """)

    @staticmethod
    def _id(prefix: str) -> str:
        return f"{prefix}_{uuid.uuid4().hex[:12]}"

    def create_problem(self, title: str, description: str) -> dict[str, Any]:
        pid = self._id("prb")
        with self.connect() as db:
            db.execute("INSERT INTO problems(id,title,description) VALUES(?,?,?)", (pid, title, description))
        return self.get_problem(pid)

    def get_problem(self, problem_id: str) -> dict[str, Any]:
        with self.connect() as db:
            row = db.execute("SELECT * FROM problems WHERE id=?", (problem_id,)).fetchone()
        if not row:
            raise KeyError(f"problem not found: {problem_id}")
        return dict(row)

    def list_problems(self) -> list[dict[str, Any]]:
        with self.connect() as db:
            return [dict(row) for row in db.execute("SELECT * FROM problems ORDER BY created_at,id")]

    def find_problem(self, title: str) -> dict[str, Any] | None:
        with self.connect() as db:
            row = db.execute("SELECT * FROM problems WHERE title=? ORDER BY created_at LIMIT 1", (title,)).fetchone()
        return dict(row) if row else None

    def add_node(self, problem_id: str, kind: str, statement: str, confidence: float = 0.5,
                 evidence: list[str] | None = None) -> dict[str, Any]:
        self.get_problem(problem_id)
        if kind not in NODE_TYPES:
            raise ValueError(f"type must be one of {sorted(NODE_TYPES)}")
        if not 0 <= confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")
        nid = self._id("node")
        with self.connect() as db:
            db.execute("INSERT INTO nodes(id,problem_id,type,statement,confidence,evidence) VALUES(?,?,?,?,?,?)",
                       (nid, problem_id, kind, statement, confidence, json.dumps(evidence or [])))
        return self.get_node(nid)

    def get_node(self, node_id: str) -> dict[str, Any]:
        with self.connect() as db:
            row = db.execute("SELECT * FROM nodes WHERE id=?", (node_id,)).fetchone()
        if not row:
            raise KeyError(f"node not found: {node_id}")
        result = dict(row)
        result["evidence"] = json.loads(result["evidence"])
        return result

    def add_edge(self, problem_id: str, source_id: str, target_id: str, kind: str) -> dict[str, Any]:
        if kind not in EDGE_TYPES:
            raise ValueError(f"type must be one of {sorted(EDGE_TYPES)}")
        source, target = self.get_node(source_id), self.get_node(target_id)
        if source_id == target_id:
            raise ValueError("self-referential edges are not allowed")
        if source["problem_id"] != problem_id or target["problem_id"] != problem_id:
            raise ValueError("both nodes must belong to the problem")
        eid = self._id("edge")
        if kind == "depends_on" and self._would_create_dependency_cycle(problem_id, source_id, target_id):
            raise ValueError("depends_on edge would create a dependency cycle")
        try:
            with self.connect() as db:
                db.execute("INSERT INTO edges(id,problem_id,source_id,target_id,type) VALUES(?,?,?,?,?)",
                           (eid, problem_id, source_id, target_id, kind))
        except sqlite3.IntegrityError as exc:
            raise ValueError("edge already exists or violates graph integrity") from exc
        return {"id": eid, "problem_id": problem_id, "source_id": source_id, "target_id": target_id, "type": kind}

    def _would_create_dependency_cycle(self, problem_id: str, source_id: str, target_id: str) -> bool:
        """A -> B is invalid when B already reaches A through depends_on edges."""
        with self.connect() as db:
            edges = db.execute("SELECT source_id,target_id FROM edges WHERE problem_id=? AND type='depends_on'",
                               (problem_id,)).fetchall()
        adjacency: dict[str, list[str]] = {}
        for edge in edges:
            adjacency.setdefault(edge["source_id"], []).append(edge["target_id"])
        stack, seen = [target_id], set()
        while stack:
            current = stack.pop()
            if current == source_id:
                return True
            if current not in seen:
                seen.add(current)
                stack.extend(adjacency.get(current, []))
        return False

    def update_node(self, node_id: str, *, statement: str | None = None, confidence: float | None = None,
                    evidence: list[Any] | None = None, status: str | None = None) -> dict[str, Any]:
        current = self.get_node(node_id)
        if confidence is not None and not 0 <= confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")
        if status is not None and status not in {"open", "testing", "supported", "falsified", "resolved"}:
            raise ValueError("invalid status")
        values = (statement if statement is not None else current["statement"],
                  confidence if confidence is not None else current["confidence"],
                  json.dumps(evidence if evidence is not None else current["evidence"]),
                  status if status is not None else current["status"], node_id)
        with self.connect() as db:
            db.execute("UPDATE nodes SET statement=?,confidence=?,evidence=?,status=? WHERE id=?", values)
        return self.get_node(node_id)

    def graph(self, problem_id: str) -> dict[str, Any]:
        problem = self.get_problem(problem_id)
        with self.connect() as db:
            nodes = [dict(r) for r in db.execute("SELECT * FROM nodes WHERE problem_id=? ORDER BY created_at,id", (problem_id,))]
            edges = [dict(r) for r in db.execute("SELECT * FROM edges WHERE problem_id=? ORDER BY created_at,id", (problem_id,))]
        for node in nodes:
            node["evidence"] = json.loads(node["evidence"])
        return {"problem": problem, "nodes": nodes, "edges": edges}
