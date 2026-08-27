import argparse
import json
from pathlib import Path

from .api import run
from .engine import Engine
from .store import Store
from .self_model import self_audit
from .benchmark import run_all_benchmarks
from .release import run_release_gates


def demo(db_path: str) -> None:
    store = Store(db_path)
    problem = store.create_problem("Can this idea work?", "A minimal OMEGA demonstration")
    assumption = store.add_node(problem["id"], "assumption", "Users will change behavior", 0.35)
    fact = store.add_node(problem["id"], "fact", "Three users requested the feature", 0.8, ["interview-notes"])
    unknown = store.add_node(problem["id"], "unknown", "Will users pay?", 0.2)
    store.add_edge(problem["id"], assumption["id"], fact["id"], "supports")
    store.add_edge(problem["id"], assumption["id"], unknown["id"], "depends_on")
    engine = Engine(store.graph(problem["id"]))
    print(json.dumps({"problem": problem, "why": engine.why(assumption["id"]),
                      "break_it": engine.break_it(), "prove_it": engine.prove_it(assumption["id"]),
                      "what_if": engine.what_if(unknown["id"], False)}, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(prog="omega")
    parser.add_argument("--db", default="data/omega.db")
    sub = parser.add_subparsers(dest="command", required=True)
    serve = sub.add_parser("serve"); serve.add_argument("--host", default="127.0.0.1"); serve.add_argument("--port", type=int, default=8787)
    sub.add_parser("demo")
    sub.add_parser("self-audit")
    sub.add_parser("benchmark"); sub.add_parser("release-check")
    export = sub.add_parser("export"); export.add_argument("problem_id"); export.add_argument("--out", required=True)
    import_cmd = sub.add_parser("import"); import_cmd.add_argument("path")
    backup = sub.add_parser("backup"); backup.add_argument("path")
    restore = sub.add_parser("restore"); restore.add_argument("path")
    args = parser.parse_args()
    if args.command == "serve":
        run(args.host, args.port, args.db)
    elif args.command == "self-audit":
        print(json.dumps(self_audit(Store(args.db)), ensure_ascii=False, indent=2))
    elif args.command == "benchmark":
        print(json.dumps(run_all_benchmarks(), ensure_ascii=False, indent=2))
    elif args.command == "release-check":
        print(json.dumps(run_release_gates(), ensure_ascii=False, indent=2))
    elif args.command == "export":
        bundle = Store(args.db).export_problem(args.problem_id)
        Path(args.out).write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"written": str(Path(args.out).resolve()), "sha256": bundle["sha256"]}, indent=2))
    elif args.command == "import":
        print(json.dumps(Store(args.db).import_problem(json.loads(Path(args.path).read_text(encoding="utf-8"))), indent=2))
    elif args.command == "backup":
        print(json.dumps(Store(args.db).backup_to(args.path), indent=2))
    elif args.command == "restore":
        print(json.dumps(Store(args.db).restore_from(args.path), indent=2))
    else:
        demo(args.db)


if __name__ == "__main__":
    main()
