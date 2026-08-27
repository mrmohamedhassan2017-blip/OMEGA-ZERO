import argparse
import json

from .api import run
from .engine import Engine
from .store import Store
from .self_model import self_audit


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
    args = parser.parse_args()
    if args.command == "serve":
        run(args.host, args.port, args.db)
    elif args.command == "self-audit":
        print(json.dumps(self_audit(Store(args.db)), ensure_ascii=False, indent=2))
    else:
        demo(args.db)


if __name__ == "__main__":
    main()
