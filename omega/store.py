from __future__ import annotations

import json
import hashlib
import sqlite3
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from .evidence import normalize_evidence
from .ontology import normalize_role

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
        db.execute("PRAGMA busy_timeout = 10000")
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def _init_schema(self) -> None:
        with self.connect() as db:
            db.execute("PRAGMA journal_mode = WAL")
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
                    role TEXT,
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
            """)
            version_row = db.execute("SELECT value FROM schema_meta WHERE key='schema_version'").fetchone()
            previous_version = int(version_row[0]) if version_row else None
            columns = {row[1] for row in db.execute("PRAGMA table_info(nodes)")}
            if "role" not in columns:
                db.execute("ALTER TABLE nodes ADD COLUMN role TEXT")
            if previous_version is not None and previous_version < 4:
                db.execute("""DELETE FROM edges AS old WHERE old.type='supports' AND EXISTS (
                    SELECT 1 FROM edges AS other WHERE other.type='supports'
                    AND other.source_id=old.target_id AND other.target_id=old.source_id AND other.id < old.id)""")
                db.execute("UPDATE edges SET source_id=target_id, target_id=source_id WHERE type='supports'")
            db.execute("INSERT OR REPLACE INTO schema_meta(key,value) VALUES('schema_version','4')")

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

    def delete_problem(self, problem_id: str) -> dict[str, Any]:
        graph = self.graph(problem_id)
        with self.connect() as db:
            db.execute("DELETE FROM problems WHERE id=?", (problem_id,))
        return {"deleted": True, "problem_id": problem_id, "nodes_deleted": len(graph["nodes"]),
                "edges_deleted": len(graph["edges"])}

    def add_node(self, problem_id: str, kind: str, statement: str, confidence: float = 0.5,
                 evidence: list[Any] | None = None, role: str | None = None) -> dict[str, Any]:
        self.get_problem(problem_id)
        if kind not in NODE_TYPES:
            raise ValueError(f"type must be one of {sorted(NODE_TYPES)}")
        if not 0 <= confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")
        role = normalize_role(kind, role)
        nid = self._id("node")
        with self.connect() as db:
            db.execute("INSERT INTO nodes(id,problem_id,type,role,statement,confidence,evidence) VALUES(?,?,?,?,?,?,?)",
                       (nid, problem_id, kind, role, statement, confidence, json.dumps(normalize_evidence(evidence))))
        return self.get_node(nid)

    def get_node(self, node_id: str) -> dict[str, Any]:
        with self.connect() as db:
            row = db.execute("SELECT * FROM nodes WHERE id=?", (node_id,)).fetchone()
        if not row:
            raise KeyError(f"node not found: {node_id}")
        result = dict(row)
        result["role"] = normalize_role(result["type"], result.get("role"))
        result["evidence"] = normalize_evidence(json.loads(result["evidence"]))
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
                    evidence: list[Any] | None = None, status: str | None = None,
                    role: str | None = None) -> dict[str, Any]:
        current = self.get_node(node_id)
        if confidence is not None and not 0 <= confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")
        if status is not None and status not in {"open", "testing", "supported", "falsified", "resolved"}:
            raise ValueError("invalid status")
        selected_role = normalize_role(current["type"], role if role is not None else current["role"])
        values = (selected_role, statement if statement is not None else current["statement"],
                  confidence if confidence is not None else current["confidence"],
                  json.dumps(normalize_evidence(evidence) if evidence is not None else current["evidence"]),
                  status if status is not None else current["status"], node_id)
        with self.connect() as db:
            db.execute("UPDATE nodes SET role=?,statement=?,confidence=?,evidence=?,status=? WHERE id=?", values)
        return self.get_node(node_id)

    def graph(self, problem_id: str) -> dict[str, Any]:
        problem = self.get_problem(problem_id)
        with self.connect() as db:
            nodes = [dict(r) for r in db.execute("SELECT * FROM nodes WHERE problem_id=? ORDER BY created_at,id", (problem_id,))]
            edges = [dict(r) for r in db.execute("SELECT * FROM edges WHERE problem_id=? ORDER BY created_at,id", (problem_id,))]
        for node in nodes:
            node["role"] = normalize_role(node["type"], node.get("role"))
            node["evidence"] = normalize_evidence(json.loads(node["evidence"]))
        return {"problem": problem, "nodes": nodes, "edges": edges}

    @staticmethod
    def _canonical_json(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    def export_problem(self, problem_id: str) -> dict[str, Any]:
        graph = self.graph(problem_id)
        ordered_nodes = sorted(graph["nodes"], key=lambda node: (
            node["type"], node["role"], node["statement"], node["confidence"], node["status"],
            self._canonical_json(node["evidence"]), node["id"]))
        keys = {node["id"]: f"n{index}" for index, node in enumerate(ordered_nodes)}
        payload = {
            "format": "omega.problem-bundle", "format_version": 1,
            "problem": {"title": graph["problem"]["title"], "description": graph["problem"]["description"]},
            "nodes": [{"key": keys[node["id"]], "type": node["type"], "role": node["role"],
                       "statement": node["statement"], "confidence": node["confidence"],
                       "evidence": node["evidence"], "status": node["status"]} for node in ordered_nodes],
            "edges": sorted([{"source": keys[edge["source_id"]], "target": keys[edge["target_id"]],
                              "type": edge["type"]} for edge in graph["edges"]],
                            key=lambda edge: (edge["source"], edge["target"], edge["type"])),
        }
        return {"payload": payload,
                "sha256": hashlib.sha256(self._canonical_json(payload).encode("utf-8")).hexdigest()}

    def import_problem(self, bundle: dict[str, Any]) -> dict[str, Any]:
        payload = bundle.get("payload")
        if not isinstance(payload, dict) or bundle.get("sha256") != hashlib.sha256(
                self._canonical_json(payload).encode("utf-8")).hexdigest():
            raise ValueError("bundle fingerprint mismatch")
        if payload.get("format") != "omega.problem-bundle" or payload.get("format_version") != 1:
            raise ValueError("unsupported bundle format or version")
        problem = payload.get("problem")
        if not isinstance(problem, dict) or not str(problem.get("title", "")).strip():
            raise ValueError("bundle problem title is required")
        raw_nodes, raw_edges = payload.get("nodes"), payload.get("edges")
        if not isinstance(raw_nodes, list) or not isinstance(raw_edges, list):
            raise ValueError("bundle nodes and edges must be lists")
        prepared, keys = [], set()
        valid_statuses = {"open", "testing", "supported", "falsified", "resolved"}
        for node in raw_nodes:
            if not isinstance(node, dict) or not str(node.get("key", "")).strip() or node["key"] in keys:
                raise ValueError("bundle node keys must be present and unique")
            kind = node.get("type")
            if kind not in NODE_TYPES:
                raise ValueError(f"invalid imported node type: {kind}")
            role = normalize_role(kind, node.get("role"))
            confidence = float(node.get("confidence", 0.5))
            if not 0 <= confidence <= 1:
                raise ValueError("imported confidence must be between 0 and 1")
            status = node.get("status", "open")
            if status not in valid_statuses:
                raise ValueError("invalid imported node status")
            keys.add(node["key"])
            prepared.append({**node, "role": role, "confidence": confidence, "status": status,
                             "statement": str(node.get("statement", "")).strip(),
                             "evidence": normalize_evidence(node.get("evidence"))})
            if not prepared[-1]["statement"]:
                raise ValueError("imported node statement is required")
        dependency_adjacency: dict[str, list[str]] = {}
        seen_edges = set()
        for edge in raw_edges:
            if not isinstance(edge, dict) or edge.get("source") not in keys or edge.get("target") not in keys:
                raise ValueError("imported edge references an unknown node")
            signature = (edge["source"], edge["target"], edge.get("type"))
            if edge["source"] == edge["target"] or edge.get("type") not in EDGE_TYPES or signature in seen_edges:
                raise ValueError("invalid, duplicate, or self-referential imported edge")
            seen_edges.add(signature)
            if edge["type"] == "depends_on":
                dependency_adjacency.setdefault(edge["source"], []).append(edge["target"])
        self._assert_acyclic(dependency_adjacency)

        problem_id = self._id("prb")
        node_ids = {node["key"]: self._id("node") for node in prepared}
        with self.connect() as db:
            db.execute("INSERT INTO problems(id,title,description) VALUES(?,?,?)",
                       (problem_id, str(problem["title"]).strip(), str(problem.get("description", ""))))
            for node in prepared:
                db.execute("INSERT INTO nodes(id,problem_id,type,role,statement,confidence,evidence,status) VALUES(?,?,?,?,?,?,?,?)",
                           (node_ids[node["key"]], problem_id, node["type"], node["role"], node["statement"],
                            node["confidence"], json.dumps(node["evidence"]), node["status"]))
            for edge in raw_edges:
                db.execute("INSERT INTO edges(id,problem_id,source_id,target_id,type) VALUES(?,?,?,?,?)",
                           (self._id("edge"), problem_id, node_ids[edge["source"]], node_ids[edge["target"]], edge["type"]))
        return {"problem_id": problem_id, "nodes_imported": len(prepared), "edges_imported": len(raw_edges),
                "sha256": bundle["sha256"]}

    @staticmethod
    def _assert_acyclic(adjacency: dict[str, list[str]]) -> None:
        visiting, visited = set(), set()
        def visit(node: str) -> None:
            if node in visiting:
                raise ValueError("imported depends_on graph contains a cycle")
            if node in visited:
                return
            visiting.add(node)
            for target in adjacency.get(node, []):
                visit(target)
            visiting.remove(node); visited.add(node)
        for node in list(adjacency):
            visit(node)

    def backup_to(self, destination: str | Path) -> dict[str, Any]:
        target_path = Path(destination)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        source = sqlite3.connect(self.path)
        target = sqlite3.connect(target_path)
        try:
            source.backup(target)
        finally:
            target.close(); source.close()
        digest = hashlib.sha256(target_path.read_bytes()).hexdigest()
        return {"path": str(target_path.resolve()), "sha256": digest, "bytes": target_path.stat().st_size}

    def restore_from(self, source: str | Path) -> dict[str, Any]:
        source_path = Path(source)
        if not source_path.is_file():
            raise ValueError("backup file not found")
        check = sqlite3.connect(f"file:{source_path.as_posix()}?mode=ro", uri=True)
        try:
            if check.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise ValueError("backup failed SQLite integrity check")
            tables = {row[0] for row in check.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if not {"problems", "nodes", "edges"}.issubset(tables):
                raise ValueError("backup is not an OMEGA database")
        finally:
            check.close()
        source_db, target_db = sqlite3.connect(source_path), sqlite3.connect(self.path)
        try:
            source_db.backup(target_db)
        finally:
            target_db.close(); source_db.close()
        self._init_schema()
        return {"restored": True, "source": str(source_path.resolve()), "problems": len(self.list_problems())}

    def database_health(self) -> dict[str, Any]:
        with self.connect() as db:
            quick_check = db.execute("PRAGMA quick_check").fetchone()[0]
            version_row = db.execute("SELECT value FROM schema_meta WHERE key='schema_version'").fetchone()
            counts = {table: db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                      for table in ("problems", "nodes", "edges")}
        return {"healthy": quick_check == "ok" and version_row is not None,
                "quick_check": quick_check, "schema_version": int(version_row[0]) if version_row else None,
                "counts": counts}
