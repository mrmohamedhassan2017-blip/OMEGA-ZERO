import argparse
import json
from pathlib import Path

from .api import run
from .engine import Engine
from .store import Store
from .self_model import self_audit
from .benchmark import run_all_benchmarks
from .release import run_release_gates
from .stability import run_stability_audit
from .evaluation import aggregate_records, prepare_blind_case, run_blind_case, score_reveal
from .spec import validate_spec
from .report import analyze_spec, render_markdown


def _write_new_json(path: str, payload: object) -> Path:
    destination = Path(path)
    if destination.exists():
        raise FileExistsError(f"refusing to overwrite existing evaluation file: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return destination.resolve()


def demo(db_path: str) -> None:
    store = Store(db_path)
    problem = store.create_problem("Can this idea work?", "A minimal OMEGA demonstration")
    assumption = store.add_node(problem["id"], "assumption", "Users will change behavior", 0.35)
    fact = store.add_node(problem["id"], "fact", "Three users requested the feature", 0.8, ["interview-notes"])
    unknown = store.add_node(problem["id"], "unknown", "Will users pay?", 0.2)
    store.add_edge(problem["id"], fact["id"], assumption["id"], "supports")
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
    sub.add_parser("benchmark"); sub.add_parser("release-check"); sub.add_parser("stability-audit")
    export = sub.add_parser("export"); export.add_argument("problem_id"); export.add_argument("--out", required=True)
    import_cmd = sub.add_parser("import"); import_cmd.add_argument("path")
    backup = sub.add_parser("backup"); backup.add_argument("path")
    restore = sub.add_parser("restore"); restore.add_argument("path")
    prepare = sub.add_parser("eval-prepare"); prepare.add_argument("bundle"); prepare.add_argument("labels")
    prepare.add_argument("--public-out", required=True); prepare.add_argument("--reveal-out", required=True)
    eval_run = sub.add_parser("eval-run"); eval_run.add_argument("public_case"); eval_run.add_argument("--out", required=True)
    score = sub.add_parser("eval-score"); score.add_argument("public_case"); score.add_argument("prediction"); score.add_argument("reveal")
    score.add_argument("--out", required=True)
    aggregate = sub.add_parser("eval-aggregate"); aggregate.add_argument("records", nargs="+")
    spec_check = sub.add_parser("spec-check"); spec_check.add_argument("path")
    run_spec_cmd = sub.add_parser("run-spec"); run_spec_cmd.add_argument("path"); run_spec_cmd.add_argument("--json-out", required=True)
    run_spec_cmd.add_argument("--markdown-out")
    args = parser.parse_args()
    if args.command == "serve":
        run(args.host, args.port, args.db)
    elif args.command == "self-audit":
        print(json.dumps(self_audit(Store(args.db)), ensure_ascii=False, indent=2))
    elif args.command == "benchmark":
        print(json.dumps(run_all_benchmarks(), ensure_ascii=False, indent=2))
    elif args.command == "release-check":
        print(json.dumps(run_release_gates(), ensure_ascii=False, indent=2))
    elif args.command == "stability-audit":
        print(json.dumps(run_stability_audit(Store(args.db)), ensure_ascii=False, indent=2))
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
    elif args.command == "eval-prepare":
        if Path(args.public_out).resolve() == Path(args.reveal_out).resolve():
            raise ValueError("public and private reveal paths must be different")
        if Path(args.public_out).exists() or Path(args.reveal_out).exists():
            raise FileExistsError("refusing to overwrite an existing public or private evaluation file")
        prepared = prepare_blind_case(json.loads(Path(args.bundle).read_text(encoding="utf-8")),
                                      json.loads(Path(args.labels).read_text(encoding="utf-8")))
        public_path = _write_new_json(args.public_out, prepared["public_case"])
        reveal_path = _write_new_json(args.reveal_out, prepared["private_reveal"])
        print(json.dumps({"public_case": str(public_path),
                          "private_reveal": str(reveal_path),
                          "case_sha256": prepared["public_case"]["case_sha256"]}, indent=2))
    elif args.command == "eval-run":
        prediction = run_blind_case(json.loads(Path(args.public_case).read_text(encoding="utf-8")))
        output_path = _write_new_json(args.out, prediction)
        print(json.dumps({"prediction": str(output_path),
                          "prediction_sha256": prediction["prediction_sha256"]}, indent=2))
    elif args.command == "eval-score":
        record = score_reveal(*[json.loads(Path(path).read_text(encoding="utf-8"))
                                for path in (args.public_case, args.prediction, args.reveal)])
        output_path = _write_new_json(args.out, record)
        stored = Store(args.db).record_evaluation(record)
        print(json.dumps({"result": str(output_path), "metrics": record["metrics"], "stored": stored}, indent=2))
    elif args.command == "eval-aggregate":
        records = [json.loads(Path(path).read_text(encoding="utf-8")) for path in args.records]
        print(json.dumps(aggregate_records(records), ensure_ascii=False, indent=2))
    elif args.command == "spec-check":
        print(json.dumps(validate_spec(json.loads(Path(args.path).read_text(encoding="utf-8"))), ensure_ascii=False, indent=2))
    elif args.command == "run-spec":
        report = analyze_spec(Store(args.db), json.loads(Path(args.path).read_text(encoding="utf-8")))
        output = _write_new_json(args.json_out, report)
        markdown_path = None
        if args.markdown_out:
            markdown_path = Path(args.markdown_out)
            if markdown_path.exists():
                raise FileExistsError(f"refusing to overwrite report: {markdown_path}")
            markdown_path.parent.mkdir(parents=True, exist_ok=True); markdown_path.write_text(render_markdown(report), encoding="utf-8")
        print(json.dumps({"json_report": str(output), "markdown_report": str(markdown_path.resolve()) if markdown_path else None,
                          "problem_id": report["problem_id"]}, indent=2))
    else:
        demo(args.db)


if __name__ == "__main__":
    main()
