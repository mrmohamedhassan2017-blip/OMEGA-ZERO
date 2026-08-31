import argparse
import json
import sys
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
from .impossibility import build_impossibility_map
from .continuity import execution_context, format_status, inspect_project
from .supervisor import (Supervisor, format_supervisor_status, install_task, request_stop,
                         start_scheduled_task, uninstall_task)
from .capability_discovery import run_discovery
from .venture_foundry import advance_e2, audit_agent_events, founder_os, market_barrier, render_agent_audit_html, run_foundry
from .provider_resilience import run_preb_simulation
from .quota_lifeline import (
    manually_rearm_after_usage_refresh,
    quota_lifeline_status,
    record_codex_usage_snapshot,
)
from .zdoa import run_zdoa
from .zava import run_zava
from .lean_control import run_lzp
from .zlca import run_zlca
from .lzp2 import run_lzp2
from .zlca_v11 import run_zlca_v11, run_zlca_v11_real
from .zfbr import operate_zfbr
from .zfa import run_zfa
from .zero_truth import operate_truth_cycle, operate_zmi_cycle, operate_zmc_cycle, operate_zdd_cycle, operate_urvk_cycle, operate_zagl_cycle, operate_zabbe_cycle, operate_zavae_cycle, operate_zabbe_hypothesis_cycle, operate_zmim_cycle, operate_ccs_cycle, operate_zopd_cycle, operate_zmc_convergence_cycle, operate_veh_qualification_cycle, operate_veh_subscription_phase1, operate_veh_subscription_comparison, operate_zad_cycle
from .gmail_adapter import (DPAPITokenStore, GmailAdapter, OAuthClient, channel_status,
                            execute_e2_batch, monitor_e2_replies, oauth_client_path, verify_and_transition)
from .zero_kernel import (execute_first_cycle, execute_zeu_stress_baseline, operate_discovery_cycle,
                          operate_economic_bridge_cycle, operate_option_creation_cycle,
                          operate_value_bridge_experiment, operate_counterparty_cycle,
                          record_value_bridge_publication, record_counterparty_comment)
from .development_governor import run_governor_cycle
from .capability_fabric import run_capability_fabric_cycle
from .real_world_value import (run_value_cycle, value_evidence, value_experiments,
                               value_opportunities, value_status)
from .real_world_value_frontier import frontier_status, run_frontier_cycle
from .real_world_value_deep import deep_status, run_deep_cycle, run_packet_hardening
from .real_world_value_binding import freeze_binding
from .real_world_value_participant_discovery import run_participant_discovery


def _write_new_json(path: str, payload: object) -> Path:
    destination = Path(path)
    if destination.exists():
        raise FileExistsError(f"refusing to overwrite existing evaluation file: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return destination.resolve()


def _print_text(value: str) -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(value)


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
    sub.add_parser("eval-list")
    spec_check = sub.add_parser("spec-check"); spec_check.add_argument("path")
    run_spec_cmd = sub.add_parser("run-spec"); run_spec_cmd.add_argument("path"); run_spec_cmd.add_argument("--json-out", required=True)
    run_spec_cmd.add_argument("--markdown-out")
    imap = sub.add_parser("impossibility-map"); imap.add_argument("problem_id"); imap.add_argument("--target")
    status_cmd = sub.add_parser("project-status"); status_cmd.add_argument("--verify-tests", action="store_true")
    sub.add_parser("continue")
    console = sub.add_parser("console"); console.add_argument("operator_input", nargs="*")
    mission = sub.add_parser("mission")
    mission_sub = mission.add_subparsers(dest="mission_action", required=True)
    mission_create = mission_sub.add_parser("create"); mission_create.add_argument("objective", nargs="+")
    mission_sub.add_parser("list")
    mission_show = mission_sub.add_parser("show"); mission_show.add_argument("mission_id")
    mission_challenge = mission_sub.add_parser("challenge"); mission_challenge.add_argument("mission_id")
    mission_execute = mission_sub.add_parser("execute"); mission_execute.add_argument("mission_id")
    mission_verify = mission_sub.add_parser("verify"); mission_verify.add_argument("mission_id"); mission_verify.add_argument("--evidence-ref")
    mission_transition = mission_sub.add_parser("transition"); mission_transition.add_argument("mission_id"); mission_transition.add_argument("state"); mission_transition.add_argument("--reason", default="")
    experiment = sub.add_parser("experiment-override")
    experiment_sub = experiment.add_subparsers(dest="experiment_action", required=True)
    experiment_sub.add_parser("status")
    exp_enable = experiment_sub.add_parser("enable"); exp_enable.add_argument("--task-id"); exp_enable.add_argument("--minutes", type=int, default=120)
    exp_disable = experiment_sub.add_parser("disable"); exp_disable.add_argument("--reason", default="manual restore")
    discovery = sub.add_parser("capability-discover"); discovery.add_argument("--out-dir")
    foundry = sub.add_parser("venture-foundry"); foundry.add_argument("--out-dir")
    e2 = sub.add_parser("venture-e2"); e2.add_argument("--out-dir")
    founder = sub.add_parser("founder-os"); founder.add_argument("--out-dir")
    barrier = sub.add_parser("market-barrier"); barrier.add_argument("--out-dir")
    gmail = sub.add_parser("gmail-channel"); gmail.add_argument("gmail_action", choices=("status", "consent", "verify", "execute-e2", "monitor-e2"))
    sub.add_parser("zero-cycle")
    sub.add_parser("zero-stress")
    sub.add_parser("zero-options")
    sub.add_parser("zero-discovery")
    sub.add_parser("zero-economic-bridge")
    sub.add_parser("zero-value-bridge")
    sub.add_parser("zero-counterparty")
    sub.add_parser("preb-simulate")
    sub.add_parser("zero-truth-cycle")
    sub.add_parser("zmi-cycle")
    sub.add_parser("zmc-cycle")
    sub.add_parser("zdd-cycle")
    sub.add_parser("urvk-cycle")
    sub.add_parser("zagl-cycle")
    sub.add_parser("zabbe-cycle")
    sub.add_parser("zavae-cycle")
    sub.add_parser("zabbe-hypothesis-cycle")
    sub.add_parser("zmim-cycle")
    sub.add_parser("ccs-cycle")
    sub.add_parser("zopd-cycle")
    sub.add_parser("zmc-convergence-cycle")
    sub.add_parser("veh-qualification-cycle")
    sub.add_parser("veh-subscription-phase1")
    sub.add_parser("veh-subscription-compare")
    sub.add_parser("zad-cycle")
    sub.add_parser("zdoa-benchmark")
    sub.add_parser("zava-audit")
    sub.add_parser("lean-parity")
    sub.add_parser("zlca-audit")
    sub.add_parser("lzp2-parity")
    sub.add_parser("zlca-v11")
    sub.add_parser("zlca-v11-real")
    sub.add_parser("zfbr-cycle")
    sub.add_parser("zfa-cycle")
    sub.add_parser("zpa-cycle")
    sub.add_parser("zcce-cycle")
    sub.add_parser("lzc-cycle")
    sub.add_parser("lzc11-cycle")
    sub.add_parser("lzc12-cycle")
    sub.add_parser("lzc13-cycle")
    sub.add_parser("lzc14-cycle")
    sub.add_parser("lzc15-cycle")
    sub.add_parser("lzc16-cycle")
    sub.add_parser("lzc17-cycle")
    sub.add_parser("lzc18-cycle")
    lzc19 = sub.add_parser("lzc19-cycle")
    lzc19.add_argument("--duration", type=float, default=3600.0)
    lzc19.add_argument("--interval", type=float, default=30.0)
    lzc19a = sub.add_parser("lzc19a-cycle")
    lzc19a.add_argument("--duration", type=float, default=300.0)
    lzc19a.add_argument("--interval", type=float, default=30.0)
    lzc19b = sub.add_parser("lzc19b-recover")
    lzc19b.add_argument("--timeout", type=float, default=600.0)
    lzc19b.add_argument("--interval", type=float, default=5.0)
    sub.add_parser("lzc19c-freeze")
    sub.add_parser("lzc19d-record")
    sub.add_parser("lzc110-design")
    lzc111=sub.add_parser("lzc111-campaign"); lzc111.add_argument('--duration',type=float,default=3600); lzc111.add_argument('--interval',type=float,default=30)
    sub.add_parser("wake-plane-status")
    wake_history=sub.add_parser("wake-plane-history"); wake_history.add_argument('--limit',type=int,default=20)
    wake_shadow=sub.add_parser("wake-plane-shadow"); wake_shadow.add_argument('--once',action='store_true')
    wake_run=sub.add_parser("wake-plane-run"); wake_run.add_argument('--mode',choices=('SHADOW','PASSIVE_PRODUCTION_VALIDATE_ONLY','PASSIVE_PRODUCTION'),default='SHADOW');wake_run.add_argument('--interval',type=float,default=60)
    wake_install=sub.add_parser('wake-plane-install');wake_install.add_argument('--mode',choices=('SHADOW','PASSIVE_PRODUCTION_VALIDATE_ONLY','PASSIVE_PRODUCTION'),default='SHADOW');sub.add_parser('wake-plane-start');sub.add_parser('wake-plane-stop');sub.add_parser('wake-plane-uninstall')
    sub.add_parser("reality-watch-run")
    sub.add_parser("reality-watch-status")
    reality_history = sub.add_parser("reality-watch-history")
    reality_history.add_argument("--limit", type=int, default=20)
    sub.add_parser("zero-value-bridge-record-publication")
    sub.add_parser("zero-counterparty-record-comment")
    sub.add_parser("development-governor")
    sub.add_parser("capability-fabric")
    sub.add_parser("backend-status")
    backend_history = sub.add_parser("backend-history")
    backend_history.add_argument("--limit", type=int, default=20)
    sub.add_parser("claude-shadow-benchmark")
    sub.add_parser("multi-backend-shadow-benchmark")
    sub.add_parser("claude-controlled-canary")
    sub.add_parser("claude-omniroute-canary")
    sub.add_parser("task-continuity-status")
    sub.add_parser("task-continuity-live-chaos")
    sub.add_parser("scientific-learning-run")
    sub.add_parser("scientific-learning-status")
    sub.add_parser("scientific-learning-rehydration")
    sub.add_parser("probability-statistics-run")
    sub.add_parser("probability-statistics-status")
    cyber = sub.add_parser("cyber")
    cyber.add_argument("cyber_action", choices=("status", "train", "ask", "exam", "mastery", "promotion-status", "research-eval", "external-eval-freeze", "external-eval-status"))
    cyber.add_argument("cyber_request", nargs="*")
    cyber.add_argument("--environment", choices=("LOCAL", "SANDBOX", "CTF_LAB", "AUTHORIZED_TARGET", "READ_ONLY_ANALYSIS"), default="READ_ONLY_ANALYSIS")
    cyber.add_argument("--authorization")
    gateway = sub.add_parser("public-gateway")
    gateway.add_argument("gateway_action", choices=("status", "init", "scan", "readiness", "mission-run"))
    gateway.add_argument("target", nargs="*")
    sub.add_parser("value-cycle")
    sub.add_parser("value-status")
    sub.add_parser("value-opportunities")
    sub.add_parser("value-experiments")
    sub.add_parser("value-evidence")
    sub.add_parser("value-frontier-cycle")
    sub.add_parser("value-frontier-status")
    sub.add_parser("value-deep-cycle")
    sub.add_parser("value-deep-status")
    sub.add_parser("value-deep-packet-audit")
    sub.add_parser("value-deep-binding-audit")
    sub.add_parser("value-deep-participant-discovery")
    sub.add_parser("economic-status")
    sub.add_parser("economic-opportunities")
    sub.add_parser("economic-ledger")
    sub.add_parser("economic-claims")
    sub.add_parser("economic-evidence")
    sub.add_parser("economic-engines")
    sub.add_parser("economic-verify")
    sub.add_parser("economic-bootstrap-audit")
    sub.add_parser("economic-platform-registry")
    quota_status = sub.add_parser("quota-lifeline-status")
    quota_status.add_argument("task_id")
    quota_usage = sub.add_parser("quota-lifeline-record-usage")
    quota_usage.add_argument("task_id")
    quota_usage.add_argument("--source", choices=("CODEX_CLI_STATUS", "CODEX_USAGE_DASHBOARD"), required=True)
    quota_usage.add_argument("--observed-at", required=True)
    quota_usage.add_argument("--five-hour-state", choices=("AVAILABLE", "EXHAUSTED", "UNKNOWN"), required=True)
    quota_usage.add_argument("--weekly-state", choices=("AVAILABLE", "EXHAUSTED", "UNKNOWN"), required=True)
    quota_usage.add_argument("--five-hour-reset-at")
    quota_usage.add_argument("--weekly-reset-at")
    quota_rearm = sub.add_parser("quota-lifeline-manual-rearm")
    quota_rearm.add_argument("task_id")
    quota_rearm.add_argument("--source", choices=("CODEX_CLI_STATUS", "CODEX_USAGE_DASHBOARD"), required=True)
    quota_rearm.add_argument("--observed-at", required=True)
    audit = sub.add_parser("venture-audit-log"); audit.add_argument("events"); audit.add_argument("--json-out",required=True); audit.add_argument("--html-out",required=True)
    supervisor_cmd = sub.add_parser("supervisor")
    supervisor_cmd.add_argument("supervisor_action", choices=("run", "start", "stop", "status", "logs", "install", "uninstall"))
    supervisor_cmd.add_argument("--once", action="store_true")
    supervisor_cmd.add_argument("--background-runtime", action="store_true")
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
    elif args.command == "eval-list":
        records = Store(args.db).list_evaluations()
        print(json.dumps({"records": len(records), "evaluations": records}, ensure_ascii=False, indent=2))
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
    elif args.command == "impossibility-map":
        print(json.dumps(build_impossibility_map(Store(args.db).graph(args.problem_id), args.target),
                         ensure_ascii=False, indent=2))
    elif args.command == "project-status":
        result = inspect_project(verify_tests=args.verify_tests)
        _print_text(format_status(result))
        if not result["ready_to_continue"]:
            raise SystemExit(1)
    elif args.command == "continue":
        _print_text(execution_context())
    elif args.command == "capability-discover":
        result = run_discovery(Path.cwd(), Path(args.out_dir) if args.out_dir else None)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == "venture-foundry":
        result = run_foundry(Path.cwd(), Path(args.out_dir) if args.out_dir else None)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == "venture-e2":
        result=advance_e2(Path.cwd(),Path(args.out_dir) if args.out_dir else None)
        print(json.dumps(result,ensure_ascii=False,indent=2))
    elif args.command == "founder-os":
        result=founder_os(Path.cwd(),Path(args.out_dir) if args.out_dir else None)
        print(json.dumps(result,ensure_ascii=False,indent=2))
    elif args.command == "market-barrier":
        result=market_barrier(Path.cwd(),Path(args.out_dir) if args.out_dir else None)
        print(json.dumps(result,ensure_ascii=False,indent=2))
    elif args.command == "gmail-channel":
        if args.gmail_action == "status":
            print(json.dumps(channel_status(Path.cwd()), ensure_ascii=False, indent=2))
        else:
            adapter = GmailAdapter(OAuthClient.load(oauth_client_path()), DPAPITokenStore())
            if args.gmail_action == "consent":
                adapter.authorize_interactively()
            if args.gmail_action == "execute-e2":
                result = execute_e2_batch(Path.cwd(), adapter)
            elif args.gmail_action == "monitor-e2":
                result = monitor_e2_replies(Path.cwd(), adapter)
            else:
                result = verify_and_transition(Path.cwd(), adapter)
            print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == "zero-cycle":
        print(json.dumps(execute_first_cycle(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "zero-stress":
        print(json.dumps(execute_zeu_stress_baseline(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "zero-options":
        print(json.dumps(operate_option_creation_cycle(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "zero-discovery":
        print(json.dumps(operate_discovery_cycle(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "zero-economic-bridge":
        print(json.dumps(operate_economic_bridge_cycle(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "zero-value-bridge":
        print(json.dumps(operate_value_bridge_experiment(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "zero-counterparty":
        print(json.dumps(operate_counterparty_cycle(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "preb-simulate":
        print(json.dumps(run_preb_simulation(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "zero-truth-cycle":
        print(json.dumps(operate_truth_cycle(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "zmi-cycle":
        _print_text(json.dumps(operate_zmi_cycle(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "zmc-cycle":
        _print_text(json.dumps(operate_zmc_cycle(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "zdd-cycle":
        _print_text(json.dumps(operate_zdd_cycle(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "urvk-cycle":
        _print_text(json.dumps(operate_urvk_cycle(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "zagl-cycle":
        _print_text(json.dumps(operate_zagl_cycle(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "zabbe-cycle":
        _print_text(json.dumps(operate_zabbe_cycle(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "zavae-cycle":
        _print_text(json.dumps(operate_zavae_cycle(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "zabbe-hypothesis-cycle":
        _print_text(json.dumps(operate_zabbe_hypothesis_cycle(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "zmim-cycle":
        _print_text(json.dumps(operate_zmim_cycle(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "ccs-cycle":
        _print_text(json.dumps(operate_ccs_cycle(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "zopd-cycle":
        _print_text(json.dumps(operate_zopd_cycle(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "zmc-convergence-cycle":
        _print_text(json.dumps(operate_zmc_convergence_cycle(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "veh-qualification-cycle":
        _print_text(json.dumps(operate_veh_qualification_cycle(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "veh-subscription-phase1":
        _print_text(json.dumps(operate_veh_subscription_phase1(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "veh-subscription-compare":
        _print_text(json.dumps(operate_veh_subscription_comparison(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "zad-cycle":
        _print_text(json.dumps(operate_zad_cycle(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "zdoa-benchmark":
        _print_text(json.dumps(run_zdoa(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "zava-audit":
        _print_text(json.dumps(run_zava(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "lean-parity":
        _print_text(json.dumps(run_lzp(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "zlca-audit":
        _print_text(json.dumps(run_zlca(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "lzp2-parity":
        _print_text(json.dumps(run_lzp2(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "zlca-v11":
        _print_text(json.dumps(run_zlca_v11(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "zlca-v11-real":
        _print_text(json.dumps(run_zlca_v11_real(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "zfbr-cycle":
        _print_text(json.dumps(operate_zfbr(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "zfa-cycle":
        _print_text(json.dumps(run_zfa(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "zpa-cycle":
        from .zpa import run_zpa
        _print_text(json.dumps(run_zpa(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "zcce-cycle":
        from .zcce import evaluate_zcce
        _print_text(json.dumps(evaluate_zcce(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "lzc-cycle":
        from .lzc import run_lzc
        _print_text(json.dumps(run_lzc(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "lzc11-cycle":
        from .lzc11 import run_campaign
        _print_text(json.dumps(run_campaign(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "lzc12-cycle":
        from .lzc12 import run_controlled
        _print_text(json.dumps(run_controlled(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "lzc13-cycle":
        from .lzc13 import run_second_workflow
        _print_text(json.dumps(run_second_workflow(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "lzc14-cycle":
        from .lzc14 import run_default_migration
        _print_text(json.dumps(run_default_migration(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "lzc15-cycle":
        from .lzc15 import run_extended_stability
        _print_text(json.dumps(run_extended_stability(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "lzc16-cycle":
        from .lzc16 import run_multi_default
        _print_text(json.dumps(run_multi_default(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "lzc17-cycle":
        from .lzc17 import run_time_canary
        _print_text(json.dumps(run_time_canary(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "lzc18-cycle":
        from .lzc18 import run_supervisor_shadow
        _print_text(json.dumps(run_supervisor_shadow(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "lzc19-cycle":
        from .lzc19 import run_long_supervisor_shadow
        _print_text(json.dumps(run_long_supervisor_shadow(Path.cwd(), args.duration, args.interval), ensure_ascii=False, indent=2))
    elif args.command == "lzc19a-cycle":
        from .lzc19a import run_heartbeat_diagnosis
        _print_text(json.dumps(run_heartbeat_diagnosis(Path.cwd(), args.duration, args.interval), ensure_ascii=False, indent=2))
    elif args.command == "lzc19b-recover":
        from .lzc19b import run_recovery
        _print_text(json.dumps(run_recovery(Path.cwd(), timeout_seconds=args.timeout, sample_interval=args.interval), ensure_ascii=False, indent=2))
    elif args.command == "lzc19c-freeze":
        from .lzc19c import freeze_health_model
        _print_text(json.dumps(freeze_health_model(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "lzc19d-record":
        from .lzc19d import freeze_episode
        _print_text(json.dumps(freeze_episode(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "lzc110-design":
        from .lzc110 import freeze_design
        _print_text(json.dumps(freeze_design(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "lzc111-campaign":
        from .lzc111 import run_campaign
        _print_text(json.dumps(run_campaign(Path.cwd(),args.duration,args.interval),ensure_ascii=False,indent=2))
    elif args.command == "wake-plane-status":
        from .wake_plane import status
        _print_text(json.dumps(status(Path.cwd()),ensure_ascii=False,indent=2))
    elif args.command == "wake-plane-history":
        from .wake_plane import history
        _print_text(json.dumps(history(Path.cwd(),args.limit),ensure_ascii=False,indent=2))
    elif args.command == "wake-plane-shadow":
        from .wake_plane import WakePlane
        plane=WakePlane(Path.cwd(),'SHADOW')
        _print_text(json.dumps(plane.cycle(),ensure_ascii=False,indent=2))
    elif args.command == 'wake-plane-run':
        from .wake_plane import WakePlane
        wake_fn = None
        if args.mode == 'PASSIVE_PRODUCTION':
            from .supervisor import start_scheduled_task as supervisor_start_scheduled_task
            wake_fn = supervisor_start_scheduled_task
        WakePlane(Path.cwd(),args.mode,wake_fn).run(args.interval)
    elif args.command == 'wake-plane-install':
        from .wake_plane import install_shadow
        install_shadow(Path.cwd(),args.mode);print(f'WAKE_PLANE_INSTALLED_{args.mode}')
    elif args.command == 'wake-plane-start':
        from .wake_plane import start_task
        start_task();print('WAKE_PLANE_START_REQUESTED')
    elif args.command == 'wake-plane-stop':
        from .wake_plane import stop_task
        stop_task(Path.cwd());print('WAKE_PLANE_STOP_REQUESTED')
    elif args.command == 'wake-plane-uninstall':
        from .wake_plane import uninstall_task
        uninstall_task();print('WAKE_PLANE_UNINSTALLED')
    elif args.command == "reality-watch-run":
        from .real_world_value_reality_watch import run_reality_watch
        _print_text(json.dumps(run_reality_watch(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "reality-watch-status":
        from .real_world_value_reality_watch import reality_watch_status
        _print_text(json.dumps(reality_watch_status(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "reality-watch-history":
        from .real_world_value_reality_watch import reality_watch_history
        _print_text(json.dumps(reality_watch_history(Path.cwd(), args.limit), ensure_ascii=False, indent=2))
    elif args.command == "zero-value-bridge-record-publication":
        print(json.dumps(record_value_bridge_publication(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "zero-counterparty-record-comment":
        print(json.dumps(record_counterparty_comment(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "development-governor":
        _print_text(json.dumps(run_governor_cycle(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "capability-fabric":
        _print_text(json.dumps(run_capability_fabric_cycle(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "console":
        from .mission_control import route_operator_command
        text = " ".join(args.operator_input).strip()
        if not text:
            _print_text("ZERO / OMEGA Console. Pass a command, for example: ZERO, status")
        else:
            _print_text(json.dumps(route_operator_command(Path.cwd(), text), ensure_ascii=False, indent=2))
    elif args.command == "mission":
        from .mission_control import (create_mission, execute_mission, list_missions, load_mission,
                                      transition_mission, verify_mission, zero_challenge)
        if args.mission_action == "create":
            _print_text(json.dumps(create_mission(Path.cwd(), " ".join(args.objective)).__dict__, ensure_ascii=False, indent=2, default=lambda o: getattr(o, "__dict__", str(o))))
        elif args.mission_action == "list":
            _print_text(json.dumps(list_missions(Path.cwd()), ensure_ascii=False, indent=2))
        elif args.mission_action == "show":
            _print_text(json.dumps(load_mission(Path.cwd(), args.mission_id).__dict__, ensure_ascii=False, indent=2, default=lambda o: getattr(o, "__dict__", str(o))))
        elif args.mission_action == "challenge":
            _print_text(json.dumps(zero_challenge(Path.cwd(), args.mission_id).__dict__, ensure_ascii=False, indent=2))
        elif args.mission_action == "execute":
            _print_text(json.dumps(execute_mission(Path.cwd(), args.mission_id), ensure_ascii=False, indent=2))
        elif args.mission_action == "verify":
            _print_text(json.dumps(verify_mission(Path.cwd(), args.mission_id, evidence_ref=args.evidence_ref).__dict__, ensure_ascii=False, indent=2))
        elif args.mission_action == "transition":
            _print_text(json.dumps(transition_mission(Path.cwd(), args.mission_id, args.state, reason=args.reason).__dict__, ensure_ascii=False, indent=2, default=lambda o: getattr(o, "__dict__", str(o))))
    elif args.command == "experiment-override":
        from .experiment_override import disable_experiment_override, enable_experiment_override, read_experiment_state
        if args.experiment_action == "status":
            _print_text(json.dumps(read_experiment_state(Path.cwd()), ensure_ascii=False, indent=2))
        elif args.experiment_action == "enable":
            _print_text(json.dumps(enable_experiment_override(Path.cwd(), task_id=args.task_id, max_runtime_minutes=args.minutes), ensure_ascii=False, indent=2))
        elif args.experiment_action == "disable":
            _print_text(json.dumps(disable_experiment_override(Path.cwd(), reason=args.reason), ensure_ascii=False, indent=2))
    elif args.command == "backend-status":
        from .claude_backend import backend_status
        _print_text(json.dumps(backend_status(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "backend-history":
        from .claude_backend import read_backend_history
        history = Path.cwd() / ".omega" / "logs" / "claude_backend_history.jsonl"
        _print_text(json.dumps(read_backend_history(history, args.limit), ensure_ascii=False, indent=2))
    elif args.command == "claude-shadow-benchmark":
        from .claude_benchmark import run_shadow_benchmark
        _print_text(json.dumps(run_shadow_benchmark(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "multi-backend-shadow-benchmark":
        from .claude_benchmark import run_multi_backend_shadow_benchmark
        _print_text(json.dumps(run_multi_backend_shadow_benchmark(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "claude-controlled-canary":
        from .claude_benchmark import run_documentation_canary
        _print_text(json.dumps(run_documentation_canary(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "claude-omniroute-canary":
        from .claude_omniroute_canary import run_nonce_canary
        _print_text(json.dumps(run_nonce_canary(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "task-continuity-status":
        from .task_continuity import continuity_status
        _print_text(json.dumps(continuity_status(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "task-continuity-live-chaos":
        from .task_continuity_chaos import run_live_claude_chaos
        _print_text(json.dumps(run_live_claude_chaos(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "scientific-learning-run":
        from .scientific_learning import run_first_campaign
        _print_text(json.dumps(run_first_campaign(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "scientific-learning-status":
        from .scientific_learning import learning_status
        _print_text(json.dumps(learning_status(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "scientific-learning-rehydration":
        from .scientific_learning import freeze_learning_rehydration
        _print_text(json.dumps(freeze_learning_rehydration(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "probability-statistics-run":
        from .probability_statistics import run_probability_campaign
        _print_text(json.dumps(run_probability_campaign(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "probability-statistics-status":
        from .probability_statistics import probability_campaign_status
        _print_text(json.dumps(probability_campaign_status(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "cyber":
        from .cyber_expert import answer_request, cyber_status, freeze_final_exam, initialize_curriculum, run_bounded_assessment
        if args.cyber_action == "status":
            _print_text(json.dumps(cyber_status(Path.cwd()), ensure_ascii=False, indent=2))
        elif args.cyber_action in {"train", "exam"}:
            _print_text(json.dumps(run_bounded_assessment(Path.cwd()), ensure_ascii=False, indent=2))
        elif args.cyber_action == "mastery":
            _print_text(json.dumps(freeze_final_exam(Path.cwd()), ensure_ascii=False, indent=2))
        elif args.cyber_action == "promotion-status":
            from .cyber_promotion import promotion_status
            _print_text(json.dumps(promotion_status(Path.cwd()), ensure_ascii=False, indent=2))
        elif args.cyber_action == "research-eval":
            from .cyber_promotion import run_promotion_campaign
            _print_text(json.dumps(run_promotion_campaign(Path.cwd()), ensure_ascii=False, indent=2))
        elif args.cyber_action == "external-eval-freeze":
            from .cyber_external_evaluation import freeze_external_evaluation_packet
            _print_text(json.dumps(freeze_external_evaluation_packet(Path.cwd()), ensure_ascii=False, indent=2))
        elif args.cyber_action == "external-eval-status":
            from .cyber_external_evaluation import external_evaluation_status
            _print_text(json.dumps(external_evaluation_status(Path.cwd()), ensure_ascii=False, indent=2))
        elif args.cyber_action == "ask":
            _print_text(json.dumps(answer_request(Path.cwd(), " ".join(args.cyber_request),
                                                  environment=args.environment,
                                                  authorization=args.authorization), ensure_ascii=False, indent=2))
        else:
            _print_text(json.dumps(initialize_curriculum(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "public-gateway":
        from .public_gateway import gateway_scan, gateway_status, initialize_gateway, release_readiness, run_public_gateway_mission
        if args.gateway_action == "status":
            _print_text(json.dumps(gateway_status(Path.cwd()), ensure_ascii=False, indent=2))
        elif args.gateway_action == "init":
            _print_text(json.dumps(initialize_gateway(Path.cwd()), ensure_ascii=False, indent=2))
        elif args.gateway_action == "scan":
            _print_text(json.dumps(gateway_scan(Path.cwd(), " ".join(args.target)), ensure_ascii=False, indent=2))
        elif args.gateway_action == "readiness":
            _print_text(json.dumps(release_readiness(Path.cwd()), ensure_ascii=False, indent=2))
        elif args.gateway_action == "mission-run":
            _print_text(json.dumps(run_public_gateway_mission(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "value-cycle":
        _print_text(json.dumps(run_value_cycle(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "value-status":
        _print_text(json.dumps(value_status(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "value-opportunities":
        _print_text(json.dumps(value_opportunities(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "value-experiments":
        _print_text(json.dumps(value_experiments(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "value-evidence":
        _print_text(json.dumps(value_evidence(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "value-frontier-cycle":
        _print_text(json.dumps(run_frontier_cycle(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "value-frontier-status":
        _print_text(json.dumps(frontier_status(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "value-deep-cycle":
        _print_text(json.dumps(run_deep_cycle(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "value-deep-status":
        _print_text(json.dumps(deep_status(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "value-deep-packet-audit":
        _print_text(json.dumps(run_packet_hardening(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "value-deep-binding-audit":
        _print_text(json.dumps(freeze_binding(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "value-deep-participant-discovery":
        _print_text(json.dumps(run_participant_discovery(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "economic-status":
        from .economic_engine import status
        _print_text(json.dumps(status(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "economic-opportunities":
        from .economic_engine import load_state
        payload = load_state(Path.cwd())
        _print_text(json.dumps((payload or {"opportunities": [], "state": "NOT_BOOTSTRAPPED"})["opportunities"], ensure_ascii=False, indent=2))
    elif args.command == "economic-ledger":
        from .economic_engine import load_state
        payload = load_state(Path.cwd())
        _print_text(json.dumps((payload or {"ledger": [], "state": "NOT_BOOTSTRAPPED"})["ledger"], ensure_ascii=False, indent=2))
    elif args.command == "economic-claims":
        from .economic_engine import load_state
        payload = load_state(Path.cwd())
        _print_text(json.dumps((payload or {"claims": [], "state": "NOT_BOOTSTRAPPED"})["claims"], ensure_ascii=False, indent=2))
    elif args.command == "economic-evidence":
        from .economic_engine import load_state
        payload = load_state(Path.cwd())
        _print_text(json.dumps((payload or {"evidence": [], "state": "NOT_BOOTSTRAPPED"})["evidence"], ensure_ascii=False, indent=2))
    elif args.command == "economic-engines":
        from .economic_engine import load_state
        payload = load_state(Path.cwd())
        if payload is None:
            _print_text(json.dumps({"state": "NOT_BOOTSTRAPPED"}, ensure_ascii=False, indent=2))
        else:
            _print_text(json.dumps({"engine_state": payload["engine_state"], "causal_memory": payload["causal_memory"]}, ensure_ascii=False, indent=2))
    elif args.command == "economic-verify":
        from .economic_engine import verify_economic_engine
        _print_text(json.dumps(verify_economic_engine(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "economic-bootstrap-audit":
        from .economic_engine import run_bootstrap
        _print_text(json.dumps(run_bootstrap(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "economic-platform-registry":
        from .economic_engine import run_platform_registry
        _print_text(json.dumps(run_platform_registry(Path.cwd()), ensure_ascii=False, indent=2))
    elif args.command == "quota-lifeline-status":
        _print_text(json.dumps(quota_lifeline_status(Path.cwd(), args.task_id), ensure_ascii=False, indent=2))
    elif args.command == "quota-lifeline-record-usage":
        _print_text(json.dumps(record_codex_usage_snapshot(
            Path.cwd(), task_id=args.task_id, source=args.source, observed_at=args.observed_at,
            five_hour_state=args.five_hour_state, weekly_state=args.weekly_state,
            five_hour_reset_at=args.five_hour_reset_at, weekly_reset_at=args.weekly_reset_at,
        ), ensure_ascii=False, indent=2))
    elif args.command == "quota-lifeline-manual-rearm":
        _print_text(json.dumps(manually_rearm_after_usage_refresh(
            Path.cwd(), task_id=args.task_id, source=args.source, observed_at=args.observed_at,
        ), ensure_ascii=False, indent=2))
    elif args.command == "venture-audit-log":
        events=[]
        for line in Path(args.events).read_text(encoding="utf-8",errors="replace").splitlines():
            try: events.append(json.loads(line))
            except json.JSONDecodeError: pass
        report=audit_agent_events(events); _write_new_json(args.json_out,report)
        html=Path(args.html_out)
        if html.exists(): raise FileExistsError(f"refusing to overwrite report: {html}")
        html.write_text(render_agent_audit_html(report),encoding="utf-8")
        print(json.dumps({"assessment":report["assessment"],"json":str(Path(args.json_out).resolve()),"html":str(html.resolve())},indent=2))
    elif args.command == "supervisor":
        if args.supervisor_action == "run":
            Supervisor().run(once=args.once)
        elif args.supervisor_action == "start":
            print(json.dumps({"started": True, "mode": "windows-task-scheduler", "pid": start_scheduled_task()}, indent=2))
        elif args.supervisor_action == "stop":
            print(json.dumps(request_stop(), indent=2))
        elif args.supervisor_action == "status":
            _print_text(format_supervisor_status())
        elif args.supervisor_action == "logs":
            path = Path(".omega/logs/events.jsonl")
            _print_text("\n".join(path.read_text(encoding="utf-8").splitlines()[-50:]) if path.exists() else "No events recorded.")
        elif args.supervisor_action == "install":
            completed = install_task(); _print_text(completed.stdout or completed.stderr)
            if completed.returncode: raise SystemExit(completed.returncode)
        elif args.supervisor_action == "uninstall":
            completed = uninstall_task(); _print_text(completed.stdout or completed.stderr)
            if completed.returncode: raise SystemExit(completed.returncode)
    else:
        demo(args.db)


if __name__ == "__main__":
    main()
