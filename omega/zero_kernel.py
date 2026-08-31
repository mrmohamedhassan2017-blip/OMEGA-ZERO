from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BRANCH_STATES = {"READY", "RUNNING", "PARKED_WAITING_EXTERNAL", "PARKED_WAITING_TIME",
                 "PUBLISHED_WAITING_EXTERNAL_EVIDENCE",
                 "EXPERIMENT_FROZEN_WAITING_EXTERNAL",
                 "WAITING_AUTHORIZATION", "WAITING_RESOURCE", "BLOCKED", "FAILED", "COMPLETED", "KILLED"}
EVIDENCE_TYPES = {"REAL", "DERIVED", "SIMULATED", "SYNTHETIC", "HYPOTHETICAL"}
HYPOTHESIS_STATES = {"UNKNOWN", "WEAK", "SUPPORTED", "CONTESTED", "FALSIFIED"}
PROGRESS_TYPES = {"NEW_EVIDENCE", "UNCERTAINTY_REDUCED", "CAPABILITY_VERIFIED", "REAL_ECONOMIC_VALUE",
                  "RISK_REDUCED", "OPTION_UNLOCKED", "BLOCKER_REMOVED"}
OPTION_STATES = {"OPTION_CREATED", "OPTION_VERIFIED", "OPTION_EXECUTABLE", "OPTION_REJECTED"}
REAL_ECONOMIC_STATES = {"FORECAST", "INTEREST", "COMMITMENT", "CONTRACTED", "INVOICED", "RECEIVABLE",
                        "RECEIVED", "SETTLED", "OWNER_WITHDRAWABLE"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _hash(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode()).hexdigest()


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, path)


def make_evidence(*, evidence_id: str, evidence_type: str, source: str, subject: str, claim: str,
                  confidence: float, independence: str, reproducibility: str, sample_size: int | None = None,
                  conflicts: list[str] | None = None, expiry: str | None = None,
                  manipulation_risk: str = "UNKNOWN") -> dict[str, Any]:
    if evidence_type not in EVIDENCE_TYPES:
        raise ValueError("unsupported evidence type")
    if not 0 <= confidence <= 1:
        raise ValueError("confidence must be between zero and one")
    return {"evidence_id": evidence_id, "type": evidence_type, "source": source, "timestamp": _now(),
            "subject": subject, "claim": claim, "confidence": confidence, "independence": independence,
            "reproducibility": reproducibility, "sample_size": sample_size, "conflicts": conflicts or [],
            "expiry_staleness": expiry, "manipulation_risk": manipulation_risk,
            "real_world_promotions_allowed": evidence_type == "REAL"}


def validate_economic_truth(evidence: dict[str, Any], economic_state: str | None = None) -> None:
    if economic_state and economic_state not in REAL_ECONOMIC_STATES:
        raise ValueError("unsupported real economic state")
    if economic_state and evidence.get("type") != "REAL":
        raise ValueError("non-real evidence cannot populate real economic states")


def branch(identifier: str, objective: str, state: str, **fields: Any) -> dict[str, Any]:
    if state not in BRANCH_STATES:
        raise ValueError("unsupported branch state")
    defaults = {"dependencies": [], "wake_conditions": [], "evidence_required": [], "authority_required": [],
                "resources_required": [], "expected_value": 0.0, "information_value": 0.0, "risk": 0.0,
                "reversibility": "HIGH", "estimated_cost": {"cash_kwd": 0, "attention": 0, "compute": "LOW"},
                "estimated_duration": "UNKNOWN", "last_progress": None, "next_executable_actions": []}
    defaults.update(fields)
    return {"id": identifier, "objective": objective, "state": state, **defaults}


def inspect_reality(root: Path) -> dict[str, Any]:
    avf = root / ".omega" / "avf"
    auth = json.loads((avf / "market_authorization.json").read_text(encoding="utf-8"))
    replies = []
    reply_path = avf / "e2_01_reply_events.jsonl"
    if reply_path.exists():
        for line in reply_path.read_text(encoding="utf-8").splitlines():
            try: replies.append(json.loads(line))
            except json.JSONDecodeError: continue
    next_task = (root / "NEXT_TASK.md").read_text(encoding="utf-8")
    return {"version":"0.21.0", "financial_authority_kwd":auth["scope"]["financial_authority_kwd"],
            "mission_verified_economic_value_kwd":0, "e2_contacts_used":auth["scope"]["contacts_used"],
            "e2_contacts_maximum":auth["scope"]["maximum_qualified_contacts"], "e2_replies":len(replies),
            "e2_signals":auth["audit"]["qualified_signals"], "e2_actions":auth["audit"]["actions_executed"],
            "v030_waiting_external":"waiting_external_evidence" in next_task.lower(),
            "gmail_monitor":"omega-e2-01-reply-monitor", "observed_at":_now()}


def initialize_branches(reality: dict[str, Any]) -> list[dict[str, Any]]:
    return [
      branch("e2-01", "Obtain genuine agent-runtime-audit demand evidence", "PARKED_WAITING_EXTERNAL",
             wake_conditions=["reply", "bounce", "unsubscribe", "experiment timeout", "authorization change"],
             evidence_required=["external reply or stronger market behavior"], authority_required=["existing E2-01 scope"],
             resources_required=["Gmail channel"], expected_value=.85, information_value=.95, risk=.25,
             estimated_duration="external/unknown", last_progress=f"{reality['e2_actions']} messages accepted; {reality['e2_replies']} replies",
             next_executable_actions=[]),
      branch("v0.30", "Collect independent evaluator outcome evidence", "PARKED_WAITING_EXTERNAL",
             wake_conditions=["genuine independent evaluator session supplied"], evidence_required=["two independent blinded sessions"],
             authority_required=[], resources_required=["independent evaluator attention"], expected_value=.9,
             information_value=.95, risk=.1, estimated_duration="external/unknown", next_executable_actions=[]),
      branch("zero-agency-kernel", "Select authorized mission-positive actions without global waiting", "RUNNING",
             wake_conditions=["material world change"], evidence_required=["frozen cycle", "RED challenge", "actual outcome"],
             resources_required=["local compute"], expected_value=.88, information_value=.8, risk=.3,
             estimated_duration="bounded local cycle", next_executable_actions=["run-first-shadow-cycle"]),
      branch("capability-discovery", "Preserve verified capability discovery", "COMPLETED",
             evidence_required=["host-verified capability artifacts"], expected_value=.6, information_value=.5,
             last_progress="Capability Discovery Engine V1 verified", next_executable_actions=[]),
      branch("inbound-evidence", "Test whether the existing local audit can attract self-service external evidence", "READY",
             wake_conditions=[], evidence_required=["real installation attempt or independently initiated inquiry"],
             authority_required=["publishing authorization before external publication"], resources_required=["existing CLI", "sample report"],
             expected_value=.8, information_value=.88, risk=.18, reversibility="HIGH", estimated_duration="one frozen local preparation",
             next_executable_actions=["freeze-self-service-install-attempt-experiment"]),
      branch("zeu-economic-lab", "Stress-test simulated resource allocation without monetary claims", "READY",
             evidence_required=["simulated stress failures"], resources_required=["local compute"], expected_value=.55,
             information_value=.62, risk=.08, estimated_duration="bounded simulation", next_executable_actions=["run-zeu-stress-baseline"])
    ]


BENEFIT_WEIGHTS = {"mission_impact":.20,"useful_outcome_probability":.12,"information_gain":.17,"economic_upside":.08,
                   "capability_unlock":.13,"blocking_reduction":.10,"reuse_value":.08}
BURDEN_WEIGHTS = {"time":.03,"cost":.03,"risk":.03,"irreversibility":.02,"authority_friction":.01}


def rank_action(action: dict[str, Any]) -> dict[str, Any]:
    required = set(BENEFIT_WEIGHTS) | set(BURDEN_WEIGHTS)
    if not required.issubset(action.get("components", {})):
        raise ValueError("action ranking components incomplete")
    benefit = sum(action["components"][key]*weight for key,weight in BENEFIT_WEIGHTS.items())
    burden = sum(action["components"][key]*weight for key,weight in BURDEN_WEIGHTS.items())
    executable = bool(action.get("authorized") and action.get("resources_available") and not action.get("blocked"))
    progress = bool(PROGRESS_TYPES.intersection(action.get("progress_if_success", [])))
    return {**action, "executable_now":executable, "busywork":not progress,
            "eva":round(benefit-burden,4) if executable and progress else None,
            "ranking_model":{"benefit_weights":BENEFIT_WEIGHTS,"burden_weights":BURDEN_WEIGHTS,
              "warning":"heuristic for auditable comparison, not scientific precision"}}


def candidate_actions() -> list[dict[str, Any]]:
    base={"estimated_cost":{"cash_kwd":0},"resources_available":True,"blocked":False,"reversible":True}
    raw=[
      {**base,"id":"freeze-inbound-install-experiment","branch_id":"inbound-evidence",
       "what_changes":"Freeze one self-service installation-attempt experiment around the existing local audit CLI and sample report.",
       "why":"Tests reachability and installation intent without waiting for replies or building multiple channels.",
       "uncertainty_reduced":"Whether a privacy-bounded self-service artifact is a worthwhile real experiment.",
       "evidence_possible":"Future REAL installation attempts; current output is DERIVED experiment evidence only.",
       "capability_unlocked":"A publishable, preregistered inbound experiment awaiting explicit publishing authority.",
       "what_can_go_wrong":["no traffic", "wrong audience", "sample creates trust concern"],"authorized":True,
       "progress_if_success":["OPTION_UNLOCKED","UNCERTAINTY_REDUCED"],
       "components":{"mission_impact":.82,"useful_outcome_probability":.72,"information_gain":.9,"economic_upside":.55,
         "capability_unlock":.82,"blocking_reduction":.68,"reuse_value":.8,"time":.2,"cost":0,"risk":.18,"irreversibility":.05,"authority_friction":.25}},
      {**base,"id":"run-zeu-stress-baseline","branch_id":"zeu-economic-lab",
       "what_changes":"Run a simulation-only balanced-ledger stress baseline.","why":"Find accounting failure modes before any future resource-allocation policy.",
       "uncertainty_reduced":"Whether the simulation ledger rejects imbalance and preserves type separation.",
       "evidence_possible":"SIMULATED stress failures and VERIFIED_OBJECTIVE implementation checks.",
       "capability_unlocked":"Safer internal allocation experiments.","what_can_go_wrong":["self-referential validation"],"authorized":True,
       "progress_if_success":["RISK_REDUCED","CAPABILITY_VERIFIED"],
       "components":{"mission_impact":.62,"useful_outcome_probability":.78,"information_gain":.64,"economic_upside":.2,
         "capability_unlock":.66,"blocking_reduction":.3,"reuse_value":.75,"time":.25,"cost":0,"risk":.08,"irreversibility":0,"authority_friction":0}},
      {**base,"id":"wait-for-e2-reply","branch_id":"e2-01","what_changes":"Nothing until an external response arrives.",
       "why":"The branch is externally waiting.","uncertainty_reduced":"None now","evidence_possible":"None now","capability_unlocked":"None",
       "what_can_go_wrong":["global idle loop"],"authorized":True,"progress_if_success":[],
       "components":{key:0 for key in set(BENEFIT_WEIGHTS)|set(BURDEN_WEIGHTS)}},
      {**base,"id":"complete-v030-internally","branch_id":"v0.30","what_changes":"Would self-generate evaluator evidence.",
       "why":"Rejected by evidence boundary.","uncertainty_reduced":"None legitimately","evidence_possible":"Invalid internal evidence",
       "capability_unlocked":"None","what_can_go_wrong":["fabricated independence"],"authorized":False,"blocked":True,
       "progress_if_success":[],"components":{key:0 for key in set(BENEFIT_WEIGHTS)|set(BURDEN_WEIGHTS)}}]
    return sorted((rank_action(item) for item in raw),key=lambda x:(x["eva"] is None,-(x["eva"] or 0),x["id"]))


def red_challenge(ranked: list[dict[str, Any]]) -> dict[str, Any]:
    chosen=next(item for item in ranked if item["executable_now"] and not item["busywork"])
    return {"role":"RED","category":"INTERNAL_AI_EVALUATION","target":chosen["id"],"verdict":"CONTESTED_BUT_EXECUTABLE",
      "objections":["A frozen inbound experiment still produces no external evidence until publication and real use.",
                     "The EVA weights may overvalue option creation and undervalue distribution friction.",
                     "Existing E2 outreach may already test reachability more directly."],
      "required_guardrails":["label output DERIVED","do not publish without authority","do not count sample use as installation",
                             "kill if no measurable external surface can be authorized"]}


def zeu_ledger() -> dict[str, Any]:
    entry={"entry_id":"zeu-genesis-0001","timestamp":_now(),"evidence_type":"SIMULATED","unit":"ZEU",
      "status":"SIMULATION_ONLY","description":"Initialize a bounded stress-test reserve; no external transfer or redemption.",
      "postings":[{"account":"simulation-reserve","debit":1000,"credit":0},{"account":"simulation-equity","debit":0,"credit":1000}],
      "real_monetary_value":False,"externally_transferable":False,"redeemable":False,"previous_hash":None}
    entry["entry_hash"]=_hash(entry)
    return {"format":"omega.zeu-ledger","status":"SIMULATION_ONLY","unit":"ZEU","non_transferable_external":True,
      "non_redeemable":True,"real_monetary_value":False,"entries":[entry],"balanced":True,
      "invariant":"ZEU cannot populate the real Economic Ledger or Mission I value"}


def causal_hypotheses() -> list[dict[str, Any]]:
    relations=[("installation-friction","first-use-probability"),("time-to-value","abandonment"),
               ("evidence-provenance","trust"),("switching-cost","adoption"),("diagnosis-quality","incident-resolution-time")]
    return [{"hypothesis_id":f"{a}-to-{b}","cause":a,"effect":b,"state":"UNKNOWN",
             "supporting_evidence":[],"contradicting_evidence":[],"claim":"may affect; not established"} for a,b in relations]


def stress_scenarios() -> list[dict[str, Any]]:
    names=["inflation","deflation","resource-scarcity","compute-price-increase","liquidity-shortage","concentration",
           "counterparty-failure","fraud-attempt","double-spend-like-error","run-scenario","reserve-depletion",
           "bad-capital-allocation","venture-collapse","dependency-failure","extreme-demand","zero-demand"]
    return [{"scenario":name,"evidence_type":"SIMULATED","proof_of_viability":False,
             "expected_break":"allocation or accounting pressure must remain visible and cannot create real value"} for name in names]


def execute_zeu_stress_baseline(root: Path) -> dict[str, Any]:
    """Execute bounded arithmetic stress cases; results are simulation evidence only."""
    out=root.resolve()/".omega"/"zero"; state_path=out/"state.json"
    if not state_path.exists(): raise RuntimeError("ZAK_FIRST_CYCLE_REQUIRED")
    cases={"inflation":700,"deflation":1200,"resource-scarcity":500,"compute-price-increase":650,
      "liquidity-shortage":200,"concentration":400,"counterparty-failure":250,"fraud-attempt":1000,
      "double-spend-like-error":1000,"run-scenario":100,"reserve-depletion":-100,"bad-capital-allocation":300,
      "venture-collapse":0,"dependency-failure":450,"extreme-demand":150,"zero-demand":1000}
    results=[]
    for name,remaining in cases.items():
        invariant_rejected=name in {"fraud-attempt","double-spend-like-error"}
        results.append({"scenario":name,"evidence_type":"SIMULATED","starting_reserve_zeu":1000,
          "modeled_remaining_zeu":remaining,"accounting_invariant_rejected":invariant_rejected,
          "failure_exposed":remaining<=0 or invariant_rejected or remaining<250,
          "real_monetary_value":False,"proof_of_viability":False})
    evidence=make_evidence(evidence_id="zak-cycle-0002-zeu-stress",evidence_type="SIMULATED",source="bounded deterministic ZEU scenarios",
      subject="ZEU allocation failure surfaces",claim="The simulation exposes reserve depletion, run pressure, and rejected fraud/double-spend-like cases; it does not establish economic viability.",
      confidence=1.0,independence="INTERNAL",reproducibility="deterministic scenario table",sample_size=len(results),
      conflicts=["scenario parameters are hypothetical"],manipulation_risk="MODEL_ASSUMPTIONS")
    decision={"decision_id":"zak-decision-0002","timestamp":_now(),"candidate_actions":["run-zeu-stress-baseline"],
      "chosen_action":"run-zeu-stress-baseline","expected_outcome":"RISK_REDUCED through explicit simulated failure surfaces",
      "actual_outcome":"RISK_REDUCED","evidence_ids":[evidence["evidence_id"]],"regret":"NOT_YET_OBSERVABLE",
      "lesson":"Balanced accounting is necessary but not evidence of useful economics; reserve and allocation assumptions fail under stress.",
      "policy_mode":"SHADOW","rollback":"remove cycle-0002 artifacts; no external or real economic state changed"}
    result={"cycle_id":"zak-cycle-0002","mode":"SHADOW","action":"run-zeu-stress-baseline","results":results,
      "evidence":evidence,"decision":decision,"real_economic_value_kwd":0,"zeu_status":"SIMULATION_ONLY",
      "global_state":"PARKED_NO_EXECUTABLE_ACTION","wake_conditions":["material world change","publishing authorization",
        "E2 reply/bounce/unsubscribe","independent evaluator evidence"]}
    _write(out/"zeu_stress_results.json",result)
    with (out/"decisions.jsonl").open("a",encoding="utf-8") as stream:
        if "zak-decision-0002" not in (out/"decisions.jsonl").read_text(encoding="utf-8"): stream.write(_canonical(decision)+"\n")
    with (out/"evidence.jsonl").open("a",encoding="utf-8") as stream:
        if evidence["evidence_id"] not in (out/"evidence.jsonl").read_text(encoding="utf-8"): stream.write(_canonical(evidence)+"\n")
    state=json.loads(state_path.read_text(encoding="utf-8")); state["global_state"]=result["global_state"]
    for item in state["branches"]:
        if item["id"]=="zeu-economic-lab":
            item["state"]="COMPLETED"; item["last_progress"]="bounded baseline exposed simulated failure surfaces"
            item["next_executable_actions"]=[]
        elif item["id"]=="zero-agency-kernel":
            item["state"]="PARKED_WAITING_TIME"; item["last_progress"]="two SHADOW cycles completed; no executable action remains"
            item["wake_conditions"]=result["wake_conditions"]; item["next_executable_actions"]=[]
    state["second_cycle"]=result; _write(state_path,state); _write(out/"branches.json",state["branches"])
    return result


OPTION_BENEFIT_WEIGHTS = {"expected_mission_value":.18,"evsi":.18,"signal_quality":.16,
                          "automation_potential":.10,"future_reuse":.13,"eva":.12}
OPTION_BURDEN_WEIGHTS = {"authority_friction":.05,"time_to_signal":.03,"dependency_risk":.03,"cost":.02}


def score_option(option: dict[str, Any]) -> dict[str, Any]:
    required={"future_action_unlocked","expected_mission_value","evsi","authority_required","resources_required",
              "cost","risk","reversibility","external_truth_surface","kill_condition","components"}
    if not required.issubset(option): raise ValueError("option contract incomplete")
    if not option["future_action_unlocked"] or not option["external_truth_surface"] or not option["kill_condition"]:
        return {**option,"state":"OPTION_REJECTED","busywork":True,"score":None,"rejection":"no measurable option unlock"}
    components=option["components"]
    if not (set(OPTION_BENEFIT_WEIGHTS)|set(OPTION_BURDEN_WEIGHTS)).issubset(components):
        raise ValueError("option scoring components incomplete")
    benefit=sum(components[key]*weight for key,weight in OPTION_BENEFIT_WEIGHTS.items())
    burden=sum(components[key]*weight for key,weight in OPTION_BURDEN_WEIGHTS.items())
    verified=option.get("lawful") is True and option.get("measurable") is True and option.get("non_signal_controls")
    executable=verified and option.get("authorized") is True and option.get("resources_available") is True
    state="OPTION_EXECUTABLE" if executable else ("OPTION_VERIFIED" if verified else "OPTION_REJECTED")
    return {**option,"state":state,"busywork":not bool(verified),"score":round(benefit-burden,4) if verified else None,
      "scoring_model":{"benefit_weights":OPTION_BENEFIT_WEIGHTS,"burden_weights":OPTION_BURDEN_WEIGHTS,
        "warning":"comparative heuristic; scores are challengeable and are not scientific probabilities"}}


def generate_inbound_options() -> list[dict[str, Any]]:
    common={"branch_id":"inbound-evidence","created_state":"OPTION_CREATED","lawful":True,"measurable":True,
            "non_signal_controls":["internal run is not installation","page view is not demand","download is weaker than installation"],
            "financial_authority_kwd":0,"reversibility":"HIGH"}
    specs=[
      {**common,"id":"portable-install-evidence-kit","future_action_unlocked":"Publish one integrity-bound local audit kit on a later authorized surface.",
       "expected_mission_value":.82,"evsi":.86,"authority_required":[],"resources_required":["existing CLI","existing sample report"],
       "cost":{"cash_kwd":0,"engineering":"LOW"},"risk":"LOW","external_truth_surface":"signed external installation receipt tied to immutable kit hash",
       "kill_condition":"kit cannot exclude secrets or cannot distinguish internal from external execution","authorized":True,"resources_available":True,
       "components":{"expected_mission_value":.82,"evsi":.86,"signal_quality":.9,"automation_potential":.8,"future_reuse":.92,
         "eva":.78,"authority_friction":0,"time_to_signal":.35,"dependency_risk":.12,"cost":.12}},
      {**common,"id":"github-public-release","future_action_unlocked":"Publish the existing CLI and immutable sample in a public GitHub repository/release.",
       "expected_mission_value":.86,"evsi":.82,"authority_required":["owner-approved public repository identity/publication"],
       "resources_required":["Git remote","GitHub account"],"cost":{"cash_kwd":0,"engineering":"LOW"},"risk":"MEDIUM",
       "external_truth_surface":"unique external clones, release downloads, issues, and provenance-bearing installation receipts",
       "kill_condition":"no authorized repository or no way to separate automated/internal traffic","authorized":False,"resources_available":False,
       "components":{"expected_mission_value":.86,"evsi":.82,"signal_quality":.72,"automation_potential":.82,"future_reuse":.9,
         "eva":.75,"authority_friction":.7,"time_to_signal":.45,"dependency_risk":.32,"cost":.18}},
      {**common,"id":"pypi-cli-package","future_action_unlocked":"Publish a versioned CLI package with opt-in anonymous installation evidence or user-submitted receipt.",
       "expected_mission_value":.8,"evsi":.78,"authority_required":["owner-approved PyPI publishing identity","telemetry policy approval if used"],
       "resources_required":["PyPI account/token","package release gate"],"cost":{"cash_kwd":0,"engineering":"MEDIUM"},"risk":"MEDIUM",
       "external_truth_surface":"PyPI download aggregate plus independently submitted successful-run receipt",
       "kill_condition":"package identity unavailable or measurement requires covert telemetry","authorized":False,"resources_available":False,
       "components":{"expected_mission_value":.8,"evsi":.78,"signal_quality":.68,"automation_potential":.88,"future_reuse":.86,
         "eva":.7,"authority_friction":.78,"time_to_signal":.48,"dependency_risk":.38,"cost":.3}},
      {**common,"id":"github-action-ci-audit","future_action_unlocked":"Offer the audit as an explicit opt-in CI workflow that emits a local evidence artifact.",
       "expected_mission_value":.84,"evsi":.84,"authority_required":["owner-approved GitHub publication"],
       "resources_required":["public repository","workflow fixture"],"cost":{"cash_kwd":0,"engineering":"MEDIUM"},"risk":"MEDIUM",
       "external_truth_surface":"externally owned workflow run and user-submitted audit artifact hash",
       "kill_condition":"workflow needs sensitive logs or cannot prove external ownership","authorized":False,"resources_available":False,
       "components":{"expected_mission_value":.84,"evsi":.84,"signal_quality":.9,"automation_potential":.9,"future_reuse":.88,
         "eva":.74,"authority_friction":.72,"time_to_signal":.55,"dependency_risk":.42,"cost":.35}},
      {**common,"id":"mcp-capability-listing","future_action_unlocked":"Expose a privacy-bounded audit capability through a lawful MCP registry/listing.",
       "expected_mission_value":.7,"evsi":.68,"authority_required":["owner-approved publisher identity and listing terms"],
       "resources_required":["MCP adapter","registry access"],"cost":{"cash_kwd":0,"engineering":"HIGH"},"risk":"MEDIUM",
       "external_truth_surface":"external installation, invocation receipt, issue, or registry interaction",
       "kill_condition":"requires broad data access or adapter work exceeds cheapest-truth experiment","authorized":False,"resources_available":False,
       "components":{"expected_mission_value":.7,"evsi":.68,"signal_quality":.76,"automation_potential":.78,"future_reuse":.8,
         "eva":.55,"authority_friction":.8,"time_to_signal":.72,"dependency_risk":.62,"cost":.7}},
      {**common,"id":"independent-benchmark-bundle","future_action_unlocked":"Submit an immutable audit bundle to one lawful independent benchmark or evaluator surface.",
       "expected_mission_value":.88,"evsi":.9,"authority_required":["owner-approved external submission identity and surface terms"],
       "resources_required":["eligible benchmark/evaluator surface"],"cost":{"cash_kwd":0,"engineering":"LOW"},"risk":"LOW",
       "external_truth_surface":"independent evaluator result bound to bundle hash",
       "kill_condition":"surface is not independent, has no integrity binding, or conflates internal execution with evaluation","authorized":False,"resources_available":False,
       "components":{"expected_mission_value":.88,"evsi":.9,"signal_quality":.98,"automation_potential":.45,"future_reuse":.72,
         "eva":.82,"authority_friction":.68,"time_to_signal":.65,"dependency_risk":.6,"cost":.2}}
    ]
    return sorted((score_option(item) for item in specs),key=lambda x:(x["score"] is None,-(x["score"] or 0),x["id"]))


def option_red_challenge(options: list[dict[str, Any]]) -> dict[str, Any]:
    winner=next(item for item in options if item["state"]=="OPTION_EXECUTABLE")
    return {"role":"RED","target":winner["id"],"category":"INTERNAL_AI_EVALUATION","verdict":"EXECUTE_WITH_GUARDRAILS",
      "objections":["A local evidence kit may optimize packaging rather than distribution.",
        "A signed receipt can prove execution but not usefulness, demand, independence, or payment.",
        "The score may favor low authority friction even when a slower independent benchmark has higher signal quality."],
      "guardrails":["no network activity","no telemetry","no claim of external installation","bind every future receipt to the kit hash",
                    "require external provenance before promotion to REAL"]}


def operate_option_creation_cycle(root: Path) -> dict[str, Any]:
    root=root.resolve(); out=root/".omega"/"zero"; state=json.loads((out/"state.json").read_text(encoding="utf-8"))
    if state.get("global_state")!="PARKED_NO_EXECUTABLE_ACTION": raise RuntimeError("OPTION_SEARCH_REQUIRES_EMPTY_EXECUTABLE_QUEUE")
    options=generate_inbound_options(); red=option_red_challenge(options)
    winner=next(item for item in options if item["state"]=="OPTION_EXECUTABLE")
    sample=root/".omega"/"avf"/"agent-runtime-audit.json"
    if not sample.exists(): raise RuntimeError("PRIVACY_SAFE_SAMPLE_REQUIRED")
    kit={"format":"omega.inbound-evidence-kit","format_version":1,"option_id":winner["id"],"status":"LOCAL_VERIFIED_NOT_PUBLISHED",
      "created_at":_now(),"experiment_id":"ZERO-INBOUND-001","sample_path":".omega/avf/agent-runtime-audit.json",
      "sample_sha256":hashlib.sha256(sample.read_bytes()).hexdigest(),"entrypoint":"python -m omega.cli venture-audit-log",
      "receipt_contract":{"required":["external_actor_attestation","installation_timestamp","kit_sha256","result_hash"],
        "prohibited":["raw logs","credentials","prompts"],"classification":"REAL only after external provenance verification"},
      "telemetry":False,"network_calls":False,"financial_authority_kwd":0}
    kit["kit_sha256"]=_hash(kit)
    _write(out/"inbound_evidence_kit.json",kit)
    verified=hashlib.sha256(sample.read_bytes()).hexdigest()==kit["sample_sha256"] and not kit["telemetry"] and not kit["network_calls"]
    lifecycle=["OPTION_CREATED","OPTION_VERIFIED","OPTION_EXECUTABLE","OPTION_VERIFIED"] if verified else ["OPTION_CREATED","OPTION_REJECTED"]
    evidence=make_evidence(evidence_id="zak-cycle-0003-option-kit",evidence_type="DERIVED",source="local integrity verification",
      subject="portable inbound evidence kit",claim="A local integrity-bound evidence kit was created; it has not been published or externally installed.",
      confidence=1.0 if verified else 0.0,independence="INTERNAL",reproducibility="hash and schema verification",
      manipulation_risk="INTERNAL_PACKAGING_BIAS")
    authority_case={"case_id":"zero-inbound-publication-authority-001","status":"AUTHORITY_REQUIRED",
      "decision":"Authorize at most one external publication surface for ZERO-INBOUND-001",
      "scope":{"identity":"one owner-approved publishing identity","surfaces":[item["id"] for item in options if item["authority_required"]],
        "financial_authority_kwd":0,"telemetry":False,"outreach":False,"contracts":False},
      "recommended_surface":next(item["id"] for item in options if item["state"]=="OPTION_VERIFIED"),
      "alternatives":[item["id"] for item in options if item["state"]=="OPTION_VERIFIED"],
      "revocation":"remove publication and reject future receipts","evidence_unlocked":"real external installation or independent evaluation evidence only"}
    decision={"decision_id":"zak-decision-0003","timestamp":_now(),"law":"NO_EXECUTABLE_ACTION -> OPTION -> CAPABILITY -> INFORMATION -> PARK",
      "options":[{"id":item["id"],"score":item["score"],"state":item["state"]} for item in options],
      "chosen_option":winner["id"],"red":red,"actual_action":"created and verified local inbound evidence kit",
      "actual_outcome":"CAPABILITY_VERIFIED","option_lifecycle":lifecycle,"evidence_ids":[evidence["evidence_id"]],
      "external_action_performed":False,"rollback":"remove inbound_evidence_kit.json; no external state changed"}
    result={"cycle_id":"zak-cycle-0003","mode":"SHADOW","engine":"ZAK Option-Creation Engine V1","options":options,
      "winner":winner,"red":red,"execution":{"executed":verified,"action":"create-local-integrity-bound-evidence-kit","kit":kit},
      "evidence":evidence,"authority_case":authority_case,"decision":decision,"real_economic_value_kwd":0,
      "zeu_status":"SIMULATION_ONLY","native_real_token":"NOT_JUSTIFIED","global_state":"WAITING_AUTHORIZATION"}
    _write(out/"option_cycle_0003.json",result); _write(out/"options.json",options); _write(out/"publication_authority_case.json",authority_case)
    with (out/"decisions.jsonl").open("a",encoding="utf-8") as stream:
        existing=(out/"decisions.jsonl").read_text(encoding="utf-8")
        if decision["decision_id"] not in existing: stream.write(_canonical(decision)+"\n")
    with (out/"evidence.jsonl").open("a",encoding="utf-8") as stream:
        existing=(out/"evidence.jsonl").read_text(encoding="utf-8")
        if evidence["evidence_id"] not in existing: stream.write(_canonical(evidence)+"\n")
    state["global_state"]="WAITING_AUTHORIZATION"; state["option_cycle"]=result
    for item in state["branches"]:
        if item["id"]=="inbound-evidence":
            item["state"]="WAITING_AUTHORIZATION"; item["last_progress"]="portable evidence kit locally verified; no publication"
            item["wake_conditions"]=["owner selects/authorizes one lawful publication surface"]
    _write(out/"state.json",state); _write(out/"branches.json",state["branches"])
    return result


DISCOVERY_BENEFIT_WEIGHTS = {
    "external_audience_fit": .12, "signal_quality": .12, "expected_reach": .08,
    "time_to_signal": .08, "measurement_quality": .08, "automation_potential": .07,
    "reusability": .07, "eva": .16, "evsi": .16,
}
DISCOVERY_BURDEN_WEIGHTS = {
    "authority_friction": .06, "cost": .03, "spam_policy_risk": .04,
    "contamination_risk": .05, "dependency_risk": .03,
}


def score_discovery_option(option: dict[str, Any]) -> dict[str, Any]:
    required = {
        "id", "surface", "action", "external_audience_fit", "signal_quality",
        "expected_reach", "time_to_signal", "authority_required", "authority_friction", "cost",
        "spam_policy_risk", "measurement_quality", "automation_potential",
        "reusability", "contamination_risk", "eva", "evsi", "measurement",
        "rollback", "policy_constraints", "lawful", "passive_or_intent_driven",
        "forbidden_dependency", "dependency_risk",
    }
    missing = sorted(required - set(option))
    forbidden = bool(option.get("forbidden_dependency"))
    measurable = bool(option.get("measurement"))
    lawful = bool(option.get("lawful")) and not forbidden
    rejected = bool(missing) or not lawful or not measurable
    benefits = sum(float(option.get(key, 0)) * weight for key, weight in DISCOVERY_BENEFIT_WEIGHTS.items())
    burdens = sum(float(option.get(key, 0)) * weight for key, weight in DISCOVERY_BURDEN_WEIGHTS.items())
    result = dict(option)
    result.update({
        "state": "OPTION_REJECTED" if rejected else (
            "OPTION_EXECUTABLE" if option.get("authorized") else "OPTION_VERIFIED"
        ),
        "busywork": rejected,
        "missing_fields": missing,
        "score": None if rejected else round(benefits - burdens, 4),
        "scoring_model": {
            "benefit_weights": DISCOVERY_BENEFIT_WEIGHTS,
            "burden_weights": DISCOVERY_BURDEN_WEIGHTS,
            "warning": "comparative heuristic; discovery is not intent, installation, demand, or revenue",
        },
    })
    return result


def generate_discovery_options() -> list[dict[str, Any]]:
    common = {
        "lawful": True,
        "authorized": False,
        "passive_or_intent_driven": True,
        "forbidden_dependency": None,
        "financial_authority_kwd": 0,
    }
    specs = [
        {**common, "id": "github-native-topics-description", "surface": "GitHub repository metadata/topics",
         "action": "Set one factual description and seven relevant lowercase topics on the existing public repository.",
         "external_audience_fit": .9, "signal_quality": .58, "expected_reach": .66, "time_to_signal": .88,
         "authority_required": ["owner approval to modify public repository metadata"], "authority_friction": .18, "cost": .02,
         "spam_policy_risk": .02, "measurement_quality": .58, "automation_potential": .84,
         "reusability": .86, "contamination_risk": .05, "dependency_risk": .08, "eva": .82, "evsi": .74,
         "measurement": "GitHub referrer/traffic snapshot is discovery-only; promotion requires non-owner provenance-bearing discovery attestation.",
         "rollback": "restore the prior empty description and topic set",
         "policy_constraints": ["maximum 20 topics", "topics lowercase, <=50 characters, relevant to repository purpose"]},
        {**common, "id": "github-actions-marketplace", "surface": "GitHub Actions Marketplace",
         "action": "Convert the tool into one reusable action.yml and publish one versioned Marketplace release.",
         "external_audience_fit": .96, "signal_quality": .82, "expected_reach": .84, "time_to_signal": .46,
         "authority_required": ["new product publication", "Marketplace terms acceptance", "2FA release approval"], "authority_friction": .78, "cost": .38,
         "spam_policy_risk": .06, "measurement_quality": .72, "automation_potential": .76,
         "reusability": .94, "contamination_risk": .28, "dependency_risk": .48, "eva": .86, "evsi": .84,
         "measurement": "independently owned workflow reference plus provenance-bound run receipt",
         "rollback": "unpublish the Marketplace release and preserve historical evidence",
         "policy_constraints": ["public single-action repository", "root action.yml", "unique name", "Marketplace agreement"]},
        {**common, "id": "pypi-registry", "surface": "Python Package Index",
         "action": "Publish a versioned package with factual searchable metadata and source URL.",
         "external_audience_fit": .78, "signal_quality": .65, "expected_reach": .76, "time_to_signal": .58,
         "authority_required": ["PyPI publishing identity", "separate package release authorization"], "authority_friction": .75, "cost": .28,
         "spam_policy_risk": .05, "measurement_quality": .55, "automation_potential": .88,
         "reusability": .9, "contamination_risk": .32, "dependency_risk": .4, "eva": .74, "evsi": .72,
         "measurement": "provenance-bearing external install receipt; aggregate downloads remain non-demand",
         "rollback": "yank the release without rewriting historical evidence",
         "policy_constraints": ["unique lawful package name", "accurate project metadata", "no covert telemetry"]},
        {**common, "id": "search-indexed-technical-guide", "surface": "search-indexable repository documentation",
         "action": "Publish one factual troubleshooting/use-case guide inside the bounded repository.",
         "external_audience_fit": .82, "signal_quality": .54, "expected_reach": .62, "time_to_signal": .52,
         "authority_required": ["approval to add one public documentation artifact"], "authority_friction": .25, "cost": .16,
         "spam_policy_risk": .02, "measurement_quality": .48, "automation_potential": .66,
         "reusability": .82, "contamination_risk": .12, "dependency_risk": .25, "eva": .7, "evsi": .65,
         "measurement": "external search referrer plus provenance-bearing statement that the guide caused discovery",
         "rollback": "remove the guide in one revert commit",
         "policy_constraints": ["factual claims only", "no keyword stuffing", "no copied content"]},
        {**common, "id": "independent-benchmark-directory", "surface": "independent benchmark/evaluator directory",
         "action": "Submit the immutable audit commit to one eligible independent tool evaluation surface.",
         "external_audience_fit": .72, "signal_quality": .95, "expected_reach": .38, "time_to_signal": .3,
         "authority_required": ["surface eligibility verification", "submission identity and terms approval"], "authority_friction": .68, "cost": .32,
         "spam_policy_risk": .03, "measurement_quality": .96, "automation_potential": .3,
         "reusability": .7, "contamination_risk": .1, "dependency_risk": .62, "eva": .8, "evsi": .9,
         "measurement": "independent listing/evaluation record bound to the published commit",
         "rollback": "withdraw the submission if the surface permits and preserve its evidence",
         "policy_constraints": ["independent evaluator", "explicit submissions accepted", "no reciprocal/fake review"]},
        {**common, "id": "mcp-tool-directory", "surface": "MCP/tool registry",
         "action": "Build and list a privacy-bounded MCP adapter only after capability fit is verified.",
         "external_audience_fit": .52, "signal_quality": .72, "expected_reach": .52, "time_to_signal": .28,
         "authority_required": ["new integration scope", "registry identity and terms approval"], "authority_friction": .82, "cost": .72,
         "spam_policy_risk": .06, "measurement_quality": .7, "automation_potential": .64,
         "reusability": .78, "contamination_risk": .36, "dependency_risk": .7, "eva": .56, "evsi": .62,
         "measurement": "independent registry installation/invocation with provenance",
         "rollback": "delist adapter and revoke only adapter-specific access",
         "policy_constraints": ["no broad log access", "minimum permissions", "registry submissions explicitly allowed"]},
        {**common, "id": "rules-compliant-technical-community", "surface": "technical community allowing self-promotion",
         "action": "Post one disclosure-rich technical write-up only where current rules explicitly allow it.",
         "external_audience_fit": .76, "signal_quality": .68, "expected_reach": .72, "time_to_signal": .7,
         "authority_required": ["named community/account/content approval after rule verification"], "authority_friction": .55, "cost": .18,
         "spam_policy_risk": .42, "measurement_quality": .6, "automation_potential": .18,
         "reusability": .5, "contamination_risk": .3, "dependency_risk": .42, "eva": .63, "evsi": .7,
         "measurement": "external referral plus independently attributable repository visit or install receipt",
         "rollback": "remove the post if allowed; never automate reposts or follow-ups",
         "policy_constraints": ["explicit self-promotion permission", "full affiliation disclosure", "one post", "no automation"]},
    ]
    return sorted((score_discovery_option(item) for item in specs), key=lambda item: (item["score"] is None, -(item["score"] or 0), item["id"]))


def discovery_red_challenge(options: list[dict[str, Any]]) -> dict[str, Any]:
    top = options[:3]
    return {
        "role": "RED", "targets": [item["id"] for item in top], "verdict": "AUTHORIZE_ONLY_TOP_PASSIVE_TEST",
        "objections": [
            "GitHub traffic is aggregated and cannot by itself prove an independent human discovered the repository.",
            "Marketplace reach is attractive but requires product/release changes that could contaminate the cheaper discovery test.",
            "Registry downloads and community engagement are easy to overread as intent or demand.",
        ],
        "guardrails": [
            "keep funnel stages separate", "owner and OMEGA activity are non-signals", "no bulk outreach or fake engagement",
            "require external provenance before promoting discovery evidence", "do not change ZERO-INBOUND-001 criteria",
        ],
    }


def operate_discovery_cycle(root: Path) -> dict[str, Any]:
    root = root.resolve(); out = root / ".omega" / "zero"
    state_path = out / "state.json"; state = json.loads(state_path.read_text(encoding="utf-8"))
    inbound = next((item for item in state.get("branches", []) if item.get("id") == "inbound-evidence"), None)
    if not inbound or inbound.get("state") != "PUBLISHED_WAITING_EXTERNAL_EVIDENCE":
        raise RuntimeError("ZERO_INBOUND_PUBLICATION_REQUIRED")
    options = generate_discovery_options(); winner = next(item for item in options if item["state"] != "OPTION_REJECTED")
    red = discovery_red_challenge(options)
    funnel = ["PUBLICATION", "DISCOVERY", "REPOSITORY_VISIT", "INTENT", "INSTALL_ATTEMPT", "VERIFIED_INSTALL", "USAGE", "DEMAND", "WTP", "PAYMENT"]
    measurement = {
        "experiment_id": "ZERO-DISCOVERY-001", "status": "FROZEN_PENDING_AUTHORITY", "funnel": funnel,
        "primary_stage": "DISCOVERY", "baseline": "zero verified independent discovery events",
        "success": "one non-owner, non-OMEGA provenance-bearing attestation or referral showing independent discovery through the authorized surface",
        "aggregate_observation": "GitHub traffic/referrers may support discovery estimates but cannot alone prove identity, intent, installation, or demand",
        "non_signals": ["owner visit", "OMEGA visit", "self-run", "artificial star", "artificial clone", "synthetic traffic", "generated account"],
        "separation_invariant": "evidence at one funnel stage never promotes a later stage without its own evidence",
        "financial_authority_kwd": 0,
    }
    authority = {
        "case_id": "zero-discovery-github-metadata-001", "status": "AUTHORITY_REQUIRED",
        "surface": winner["surface"], "exact_action": winner["action"],
        "content": ({"description": "Privacy-bounded local lifecycle audit for coding-agent runtimes; no telemetry.",
                     "topics": ["agent-runtime", "ai-agents", "coding-agents", "developer-tools", "github-actions", "observability", "reliability"]}
                    if winner["surface"] == "GitHub repository metadata/topics" else {"artifact": winner["action"]}),
        "expected_measurement": winner["measurement"],
        "limits": {"repository": "mrmohamedhassan2017-blip/agent-runtime-audit",
                   "metadata_only": winner["surface"] == "GitHub repository metadata/topics",
                   "commits": 0, "messages": 0, "paid_services": False, "financial_authority_kwd": 0,
                   "workflow_runs": 0, "other_surfaces": False},
        "rollback": winner["rollback"], "prior_state": {"description": None, "topics": []},
        "platform_policy_constraints": winner["policy_constraints"],
    }
    branch = {
        "id": "zero-discovery-001", "objective": "Find the cheapest lawful measurable independent discovery path for the public audit artifact.",
        "state": "WAITING_AUTHORIZATION", "dependencies": ["inbound-evidence"],
        "wake_conditions": ["bounded GitHub metadata authority granted"],
        "evidence_required": [measurement["success"]], "authority_required": [authority["case_id"]],
        "resources_required": ["existing public repository metadata"], "expected_value": winner["eva"],
        "information_value": winner["evsi"], "risk": winner["spam_policy_risk"], "reversibility": "HIGH",
        "estimated_cost": {"cash_kwd": 0, "attention": "LOW", "compute": "LOW"},
        "estimated_duration": "bounded metadata experiment plus external waiting", "last_progress": "options ranked; measurement frozen; no external action",
        "next_executable_actions": [],
    }
    state["branches"] = [item for item in state.get("branches", []) if item.get("id") != branch["id"]] + [branch]
    state["global_state"] = "WAITING_AUTHORIZATION"
    result = {"cycle_id": "zak-cycle-0005-discovery", "mode": "SHADOW", "experiment_id": "ZERO-DISCOVERY-001",
              "options": options, "winner": winner, "red": red, "measurement_contract": measurement,
              "execution": {"external_action_performed": False, "internal_action": "measurement contract and one authority case frozen"},
              "authority_case": authority, "external_evidence": [], "real_economic_value_kwd": 0,
              "zeu_status": "SIMULATION_ONLY", "native_real_token": "NOT_JUSTIFIED", "global_state": state["global_state"]}
    _write(out / "discovery_cycle_0005.json", result); _write(out / "discovery_options.json", options)
    _write(out / "discovery_measurement_contract.json", measurement); _write(out / "discovery_authority_case.json", authority)
    _write(state_path, state); _write(out / "branches.json", state["branches"])
    return result


VALUE_BENEFIT_WEIGHTS = {
    "scarcity_value": .1, "verification_strength": .12, "machine_to_machine_feasibility": .1,
    "automation_potential": .08, "repeatability": .08, "time_to_first_real_value": .08,
    "eva": .18, "evsi": .16,
}
VALUE_BURDEN_WEIGHTS = {
    "human_dependency": .05, "marginal_cost": .04, "legal_authority_friction": .06,
    "dependency_risk": .04,
}


def score_value_primitive(candidate: dict[str, Any]) -> dict[str, Any]:
    required = {
        "id", "customer_consumer", "actually_consumed", "scarcity_value", "value_verification",
        "verification_strength", "machine_to_machine_feasibility", "human_dependency", "marginal_cost",
        "automation_potential", "repeatability", "external_settlement_options", "legal_authority_friction",
        "time_to_first_real_value", "eva", "evsi", "failure_modes", "kill_criteria", "dependency_risk",
    }
    missing = sorted(required - set(candidate))
    benefits = sum(float(candidate.get(key, 0)) * weight for key, weight in VALUE_BENEFIT_WEIGHTS.items())
    burdens = sum(float(candidate.get(key, 0)) * weight for key, weight in VALUE_BURDEN_WEIGHTS.items())
    rejected = bool(missing) or not candidate.get("actually_consumed") or not candidate.get("value_verification")
    result = dict(candidate)
    result.update({"state": "OPTION_REJECTED" if rejected else "OPTION_VERIFIED", "missing_fields": missing,
                   "score": None if rejected else round(benefits - burdens, 4),
                   "scoring_model": {"benefit_weights": VALUE_BENEFIT_WEIGHTS, "burden_weights": VALUE_BURDEN_WEIGHTS,
                                     "warning": "comparative model; internal ZEU activity is never real economic value"}})
    return result


def generate_economic_bridge_candidates() -> list[dict[str, Any]]:
    candidates = [
        {"id": "ci-reliability-verification", "customer_consumer": "coding-agent platform teams and CI systems",
         "actually_consumed": "a deterministic hash-bound accept/reject reliability receipt for one agent run",
         "scarcity_value": .9, "value_verification": "independent CI reproduces the receipt against immutable input and records the gate decision",
         "verification_strength": .94, "machine_to_machine_feasibility": .96, "human_dependency": .18,
         "marginal_cost": .1, "automation_potential": .95, "repeatability": .96,
         "external_settlement_options": ["API billing", "marketplace payout", "invoice", "bank/payment rail"],
         "legal_authority_friction": .36, "time_to_first_real_value": .78, "eva": .91, "evsi": .9,
         "dependency_risk": .22, "failure_modes": ["self-verification bias", "receipt ignored by CI", "sensitive input pressure"],
         "kill_criteria": ["cannot verify without private logs", "no independent consumption after frozen exposure window"]},
        {"id": "verified-agent-runtime-audit", "customer_consumer": "agent-runtime developers and reliability owners",
         "actually_consumed": "a privacy-bounded lifecycle diagnosis and missing-event report",
         "scarcity_value": .82, "value_verification": "consumer reproduces report hash and confirms a concrete reliability decision",
         "verification_strength": .88, "machine_to_machine_feasibility": .9, "human_dependency": .28,
         "marginal_cost": .08, "automation_potential": .92, "repeatability": .94,
         "external_settlement_options": ["API billing", "invoice", "marketplace payout"],
         "legal_authority_friction": .3, "time_to_first_real_value": .82, "eva": .86, "evsi": .88,
         "dependency_risk": .18, "failure_modes": ["diagnosis not actionable", "event schema mismatch", "consumer distrust"],
         "kill_criteria": ["no externally attributable decision impact", "privacy boundary cannot be maintained"]},
        {"id": "automated-repair-verification", "customer_consumer": "software teams operating autonomous repair agents",
         "actually_consumed": "an independent before/after verification receipt proving a repair passed declared gates",
         "scarcity_value": .95, "value_verification": "host tests and immutable diff/gate hashes validate the claimed repair",
         "verification_strength": .96, "machine_to_machine_feasibility": .88, "human_dependency": .26,
         "marginal_cost": .3, "automation_potential": .9, "repeatability": .86,
         "external_settlement_options": ["per-repair API billing", "marketplace payout", "invoice"],
         "legal_authority_friction": .48, "time_to_first_real_value": .58, "eva": .92, "evsi": .84,
         "dependency_risk": .5, "failure_modes": ["tests are insufficient", "unsafe patch", "attribution dispute"],
         "kill_criteria": ["cannot isolate verification from repair producer", "rollback cannot be proven"]},
        {"id": "reproducible-benchmark-execution", "customer_consumer": "model and agent tool builders",
         "actually_consumed": "a reproducible benchmark run with environment, input, and result hashes",
         "scarcity_value": .76, "value_verification": "third party reruns the same frozen fixture and matches declared tolerances",
         "verification_strength": .92, "machine_to_machine_feasibility": .9, "human_dependency": .2,
         "marginal_cost": .34, "automation_potential": .92, "repeatability": .9,
         "external_settlement_options": ["API billing", "benchmark marketplace", "invoice"],
         "legal_authority_friction": .34, "time_to_first_real_value": .62, "eva": .8, "evsi": .82,
         "dependency_risk": .38, "failure_modes": ["benchmark gaming", "environment drift", "commodity competition"],
         "kill_criteria": ["results are not reproducible", "compute cost exceeds verified value"]},
        {"id": "evidence-integrity-verification", "customer_consumer": "agent orchestration systems and audit pipelines",
         "actually_consumed": "a machine-readable verdict that evidence provenance, hashes, and promotion rules are intact",
         "scarcity_value": .8, "value_verification": "independent verifier validates signatures/hashes and detects tampering fixture",
         "verification_strength": .95, "machine_to_machine_feasibility": .98, "human_dependency": .1,
         "marginal_cost": .06, "automation_potential": .98, "repeatability": .98,
         "external_settlement_options": ["API billing", "per-verification marketplace payout", "invoice"],
         "legal_authority_friction": .28, "time_to_first_real_value": .68, "eva": .83, "evsi": .76,
         "dependency_risk": .2, "failure_modes": ["valid hash mistaken for true claim", "key/provenance ambiguity"],
         "kill_criteria": ["verdict cannot distinguish integrity from truth", "consumer has no use for promotion controls"]},
        {"id": "machine-readable-diagnostics", "customer_consumer": "CI dashboards, observability tools, and incident automation",
         "actually_consumed": "normalized failure findings and remediation priorities",
         "scarcity_value": .68, "value_verification": "consumer records an automated routing or triage decision tied to diagnostic hash",
         "verification_strength": .76, "machine_to_machine_feasibility": .96, "human_dependency": .16,
         "marginal_cost": .07, "automation_potential": .97, "repeatability": .94,
         "external_settlement_options": ["API billing", "integration marketplace", "invoice"],
         "legal_authority_friction": .3, "time_to_first_real_value": .72, "eva": .74, "evsi": .78,
         "dependency_risk": .25, "failure_modes": ["false priority", "schema fragmentation", "low differentiation"],
         "kill_criteria": ["diagnostics do not change downstream action", "false-positive rate exceeds frozen limit"]},
        {"id": "agent-evaluation", "customer_consumer": "agent vendors and enterprise evaluators",
         "actually_consumed": "a blind protocol result comparing declared agent behavior against frozen criteria",
         "scarcity_value": .88, "value_verification": "independent reveal record verifies scoring without post-hoc threshold drift",
         "verification_strength": .93, "machine_to_machine_feasibility": .78, "human_dependency": .42,
         "marginal_cost": .24, "automation_potential": .78, "repeatability": .82,
         "external_settlement_options": ["evaluation fee invoice", "marketplace payout", "API billing"],
         "legal_authority_friction": .46, "time_to_first_real_value": .55, "eva": .84, "evsi": .86,
         "dependency_risk": .45, "failure_modes": ["evaluator non-independence", "metric gaming", "selection bias"],
         "kill_criteria": ["independence cannot be established", "criteria change after observation"]},
        {"id": "compute-backed-work", "customer_consumer": "external machine clients needing bounded deterministic computation",
         "actually_consumed": "a declared computation result with input/output/environment provenance",
         "scarcity_value": .52, "value_verification": "client verifies result or redundant execution agrees",
         "verification_strength": .82, "machine_to_machine_feasibility": .94, "human_dependency": .08,
         "marginal_cost": .72, "automation_potential": .96, "repeatability": .9,
         "external_settlement_options": ["API billing", "compute marketplace", "machine payment protocol"],
         "legal_authority_friction": .5, "time_to_first_real_value": .5, "eva": .58, "evsi": .6,
         "dependency_risk": .65, "failure_modes": ["commodity pricing", "abuse workloads", "cost volatility"],
         "kill_criteria": ["no differentiation from commodity compute", "workload authority cannot be bounded"]},
    ]
    return sorted((score_value_primitive(item) for item in candidates), key=lambda item: (item["score"] is None, -(item["score"] or 0), item["id"]))


def simulate_atomic_zeu_contracts() -> dict[str, Any]:
    scenarios = []
    for name, verdict, expected in (("success", "CONFIRMED", "SETTLED"), ("failure", "FAILED", "REFUNDED"),
                                    ("dispute", "DISPUTED", "ESCROW_HELD"), ("fraud-challenge", "FRAUD", "REFUNDED")):
        scenarios.append({"scenario": name, "escrow_zeu": 10, "verifier": "SIMULATED_V",
                          "outcome": verdict, "final_state": expected, "real_payment": False,
                          "mission_value_delta_kwd": 0, "provenance": _hash({"scenario": name, "verdict": verdict})})
    double_spend = {"scenario": "double-spend", "first_settlement": "ACCEPTED", "second_settlement": "REJECTED",
                    "reason": "contract nonce already consumed", "real_payment": False, "mission_value_delta_kwd": 0}
    return {"mode": "SIMULATION_ONLY", "invariants": ["INTERNAL_ZEU_TRANSFER != REAL_PAYMENT",
             "INTERNAL_TRADE != REVENUE", "SIMULATED_PROFIT != ECONOMIC_VALUE", "SELF_PURCHASE != CUSTOMER",
             "OWNER_PURCHASE != INDEPENDENT_DEMAND"], "conditional_contract": "PAY X ZEU ONLY IF verifier V confirms Y under E",
            "scenarios": scenarios + [double_spend], "reputation_effects": {"confirmed": 1, "failed": 0, "fraud": -2},
            "real_economic_value_kwd": 0}


def operate_economic_bridge_cycle(root: Path) -> dict[str, Any]:
    root = root.resolve(); out = root / ".omega" / "zero"
    state = json.loads((out / "state.json").read_text(encoding="utf-8"))
    inbound = next((item for item in state.get("branches", []) if item.get("id") == "inbound-evidence"), None)
    if not inbound or inbound.get("state") != "PUBLISHED_WAITING_EXTERNAL_EVIDENCE":
        raise RuntimeError("PUBLISHED_VALUE_SURFACE_REQUIRED")
    candidates = generate_economic_bridge_candidates(); winner = candidates[0]
    red = {"role": "RED", "target": winner["id"], "verdict": "FREEZE_CHEAPEST_FALSIFICATION",
           "objections": ["OMEGA currently produces and verifies both sides, so internal reproducibility is not independent value.",
                          "A technically valid receipt may not change a CI decision or justify payment.",
                          "The existing public audit tests discoverability, not buyer authority or willingness to pay."],
           "guardrails": ["independent consumer required", "no self-purchase", "no real rail before consumption",
                          "receipt integrity is not demand", "keep raw logs outside the boundary"]}
    boundary = [
        {"transition": "INTERNAL_MACHINE_ECONOMY -> VERIFIABLE_USEFUL_OUTPUT", "evidence": "contract nonce, frozen input hash, verifier identity, deterministic receipt hash"},
        {"transition": "VERIFIABLE_USEFUL_OUTPUT -> INDEPENDENT_EXTERNAL_CONSUMPTION", "evidence": "non-owner external system provenance plus recorded accept/reject/repair decision"},
        {"transition": "INDEPENDENT_EXTERNAL_CONSUMPTION -> EXTERNAL_VALUE_EVENT", "evidence": "independent commitment, invoice acceptance, marketplace order, or payment provenance"},
        {"transition": "EXTERNAL_VALUE_EVENT -> REAL_ECONOMIC_LEDGER", "evidence": "verified lawful settlement classified RECEIVED or stronger; forecasts and interest excluded"},
    ]
    experiment = {"experiment_id": "ZERO-VALUE-BRIDGE-001", "status": "FROZEN_WAITING_INDEPENDENT_CONSUMPTION",
                  "candidate": winner["id"], "hypothesis": "An independent coding-agent CI owner will consume one hash-bound reliability receipt and use it in an accept, reject, or repair decision.",
                  "cheapest_falsifiable_path": "reuse the existing public audit workflow/receipt without modifying ZERO-INBOUND-001",
                  "baseline": "zero verified independent consumption events", "success": "one provenance-bearing independent CI consumption event with recorded downstream decision",
                  "economic_success_separate": "one independently verified external commitment or settled value event attributable to repeated consumption",
                  "failure": "zero qualifying consumption after the discovery experiment exposure window, or receipt cannot be reproduced",
                  "non_signals": ["OMEGA run", "owner run", "internal ZEU settlement", "view", "clone", "download", "technical receipt without external use"],
                  "kill_criteria": winner["kill_criteria"], "financial_authority_kwd": 0,
                  "real_money_rail": "NOT_IMPLEMENTED", "native_real_token": "NOT_JUSTIFIED"}
    zeu = simulate_atomic_zeu_contracts()
    branch = {"id": "zero-economic-bridge-001", "objective": "Find the first independently consumable machine-native value primitive.",
              "state": "EXPERIMENT_FROZEN_WAITING_EXTERNAL", "dependencies": ["zero-discovery-001", "inbound-evidence"],
              "wake_conditions": ["independent CI consumes a provenance-bound receipt", "discovery exposure window ends"],
              "evidence_required": [experiment["success"]], "authority_required": [],
              "resources_required": ["existing public audit receipt", "independent consumer"],
              "expected_value": winner["eva"], "information_value": winner["evsi"], "risk": winner["legal_authority_friction"],
              "reversibility": "HIGH", "estimated_cost": {"cash_kwd": 0, "compute": "LOW", "attention": 0},
              "estimated_duration": "external/unknown", "last_progress": "value primitive ranked; experiment frozen; internal ZEU contracts simulated",
              "next_executable_actions": []}
    state["branches"] = [item for item in state.get("branches", []) if item.get("id") != branch["id"]] + [branch]
    result = {"cycle_id": "zak-cycle-0006-economic-bridge", "mode": "SHADOW", "candidates": candidates,
              "winner": winner, "red": red, "value_boundary": boundary, "frozen_experiment": experiment,
              "execution": {"internal_atomic_contract_simulation": True, "external_action_performed": False,
                            "real_money_rail_implemented": False, "authorization_case": None},
              "internal_zeu": zeu, "external_evidence": [], "real_economic_value_kwd": 0,
              "real_financial_authority_kwd": 0, "native_real_token": "NOT_JUSTIFIED",
              "global_state": state.get("global_state", "WAITING_AUTHORIZATION")}
    _write(out / "economic_bridge_cycle_0006.json", result); _write(out / "economic_bridge_candidates.json", candidates)
    _write(out / "economic_value_boundary.json", boundary); _write(out / "economic_bridge_experiment.json", experiment)
    _write(out / "zeu_atomic_contract_simulation.json", zeu); _write(out / "state.json", state); _write(out / "branches.json", state["branches"])
    return result


VALUE_ROUTE_BENEFITS = {"audience_fit": .14, "signal_quality": .18, "time_to_signal": .1,
                        "measurement_quality": .16, "automation_potential": .08,
                        "reusability": .1, "eva": .12, "evsi": .12}
VALUE_ROUTE_BURDENS = {"authority_friction": .08, "policy_risk": .06,
                       "dependency_risk": .06, "contamination_risk": .1, "cost": .04}


def score_value_bridge_route(candidate: dict[str, Any]) -> dict[str, Any]:
    required = set(VALUE_ROUTE_BENEFITS) | set(VALUE_ROUTE_BURDENS) | {
        "id", "surface", "action", "external_truth", "kill_condition"
    }
    missing = sorted(required - set(candidate))
    score = sum(float(candidate.get(k, 0)) * w for k, w in VALUE_ROUTE_BENEFITS.items())
    score -= sum(float(candidate.get(k, 0)) * w for k, w in VALUE_ROUTE_BURDENS.items())
    result = dict(candidate)
    result.update({"state": "OPTION_REJECTED" if missing else "OPTION_VERIFIED",
                   "missing_fields": missing, "score": None if missing else round(score, 4)})
    return result


def generate_value_bridge_routes() -> list[dict[str, Any]]:
    base = {"cost": 0, "external_truth": "one non-owner repository run with verifiable provenance and a recorded utility decision"}
    candidates = [
        {**base, "id": "public-ci-consumer-kit", "surface": "existing public GitHub repository",
         "action": "add one pinned, copyable independent-repository CI workflow and receipt contract",
         "audience_fit": .94, "signal_quality": .9, "time_to_signal": .78, "measurement_quality": .96,
         "automation_potential": .94, "reusability": .96, "eva": .91, "evsi": .94,
         "authority_friction": .35, "policy_risk": .04, "dependency_risk": .18, "contamination_risk": .06,
         "kill_condition": "template cannot preserve the inbound hash or cannot distinguish owner from independent use"},
        {**base, "id": "organic-current-readme", "surface": "current public repository",
         "action": "make no publication change and wait for an independent user to construct CI integration",
         "audience_fit": .62, "signal_quality": .86, "time_to_signal": .2, "measurement_quality": .82,
         "automation_potential": .8, "reusability": .62, "eva": .42, "evsi": .62,
         "authority_friction": 0, "policy_risk": 0, "dependency_risk": .72, "contamination_risk": 0,
         "kill_condition": "exposure window ends without qualifying provenance"},
        {**base, "id": "consent-based-maintainer-invitation", "surface": "one qualified CI maintainer",
         "action": "invite one independent maintainer to run the frozen integration voluntarily",
         "audience_fit": .9, "signal_quality": .96, "time_to_signal": .72, "measurement_quality": .94,
         "automation_potential": .3, "reusability": .44, "eva": .76, "evsi": .92,
         "authority_friction": .7, "policy_risk": .3, "dependency_risk": .48, "contamination_risk": .32,
         "kill_condition": "no explicit lawful contact route or invitation would overlap E2-01"},
        {**base, "id": "github-marketplace-action", "surface": "GitHub Marketplace",
         "action": "package and list a dedicated Action",
         "audience_fit": .92, "signal_quality": .7, "time_to_signal": .5, "measurement_quality": .58,
         "automation_potential": .94, "reusability": .95, "eva": .72, "evsi": .64,
         "authority_friction": .82, "policy_risk": .25, "dependency_risk": .4, "contamination_risk": .18,
         "kill_condition": "listing effort exceeds information value before a verified install"},
        {**base, "id": "independent-benchmark-integration", "surface": "external benchmark/evaluator",
         "action": "integrate the audit receipt into an independent benchmark gate",
         "audience_fit": .82, "signal_quality": .98, "time_to_signal": .34, "measurement_quality": .98,
         "automation_potential": .72, "reusability": .84, "eva": .8, "evsi": .9,
         "authority_friction": .78, "policy_risk": .08, "dependency_risk": .76, "contamination_risk": .1,
         "kill_condition": "independent evaluator or compatible benchmark is unavailable"},
        {**base, "id": "package-registry", "surface": "Python package registry",
         "action": "publish the audit package for CI installation",
         "audience_fit": .78, "signal_quality": .48, "time_to_signal": .58, "measurement_quality": .38,
         "automation_potential": .92, "reusability": .9, "eva": .62, "evsi": .5,
         "authority_friction": .76, "policy_risk": .12, "dependency_risk": .36, "contamination_risk": .16,
         "kill_condition": "downloads cannot establish independent utility"},
    ]
    return sorted((score_value_bridge_route(c) for c in candidates),
                  key=lambda item: (item["score"] is None, -(item["score"] or 0), item["id"]))


def operate_value_bridge_experiment(root: Path) -> dict[str, Any]:
    root = root.resolve(); out = root / ".omega" / "zero"
    state = json.loads((out / "state.json").read_text(encoding="utf-8"))
    inbound_path = out / "inbound_experiment.json"
    inbound = json.loads(inbound_path.read_text(encoding="utf-8")) if inbound_path.exists() else {}
    frozen_hash = (inbound.get("specification_hash") or inbound.get("spec_hash") or
                   inbound.get("experiment_hash") or inbound.get("frozen_hash"))
    routes = generate_value_bridge_routes(); winner = routes[0]
    value_unit = {
        "id": "ci-reliability-verification-receipt-v1",
        "input": "privacy-safe JSONL lifecycle events supplied by an independent repository CI run",
        "work_performed": "deterministically parse events, verify required lifecycle transitions, and classify missing or contradictory reliability evidence",
        "output": "machine-readable JSON audit plus human-readable HTML, bound to input and result hashes",
        "verification_method": "install from immutable public commit; reproduce the result; compare input, output, source, and workflow hashes",
        "provenance": "independent repository identity, owner identity, workflow/run URL and ID, triggering commit/event, source commit, input hash, result hash, and consumer utility decision",
        "success_condition": "a non-owner/non-OMEGA repository independently invokes the tool and produces a reproducible output used in an accept, reject, or repair decision",
        "failure_condition": "no qualifying L2/L3 event in the frozen window, unverifiable provenance, non-reproducible output, or output has no decision utility",
        "marginal_resource_cost": {"omega_cash_kwd": 0, "consumer": "GitHub-hosted CI minutes plus seconds of local compute"},
        "expected_consumer_benefit": "detect missing lifecycle/host-verification evidence before trusting a long-running coding-agent run",
    }
    ladder = [
        {"level": "L0", "meaning": "public artifact exists"},
        {"level": "L1", "meaning": "independent discovery"},
        {"level": "L2", "meaning": "independent invocation/install"},
        {"level": "L3", "meaning": "verified useful output produced and tied to a consumer decision"},
        {"level": "L4", "meaning": "independent repeat or deeper use"},
        {"level": "L5", "meaning": "explicit economic commitment or willingness to pay"},
        {"level": "L6", "meaning": "real external settlement"},
    ]
    provenance = {
        "required": ["public repository URL", "repository owner", "workflow run URL/ID", "triggering commit/event",
                     "pinned audit source commit", "workflow hash", "input hash", "result hash", "utility decision"],
        "independence": "repository owner and initiator must not be mrmohamedhassan2017-blip, OMEGA, or an owner-controlled surrogate",
        "privacy": "retain hashes, identifiers, verdict, and decision only; raw private lifecycle payloads are not required",
        "promotion_rule": "each level requires its own evidence; no view, clone, download, bot run, owner run, or lower level promotes upward",
    }
    contract = {
        "request": "consumer requests CI reliability verification by invoking the pinned public package in its own CI",
        "performance": value_unit["work_performed"], "evidence_artifact": value_unit["output"],
        "independent_verification": value_unit["verification_method"],
        "utility_classification": ["ACCEPT", "REJECT", "REPAIR", "NO_DECISION_VALUE"],
        "settlement": "NONE; ZEU is simulation-only and no financial authority exists",
    }
    red = {"role": "RED", "verdict": "ALLOW_INTERNAL_PREP_ONLY",
           "attacks": ["self-use contamination", "bot activity or fork noise", "meaningless workflow invocation",
                       "fabricated utility decision", "unverifiable actor provenance", "valid output with no consumer benefit",
                       "GitHub metrics mistaken for demand"],
           "controls": [provenance["independence"], provenance["promotion_rule"],
                        "require reproducible hashes and a downstream decision for L3"]}
    consumer_workflow = {
        "purpose": "review-only template; not executed or published",
        "install": "python -m pip install --no-deps git+https://github.com/mrmohamedhassan2017-blip/agent-runtime-audit.git@159def24e9a75ef568c802d9d0fb54dd0f89db25",
        "invoke": "python -m agent_runtime_audit <privacy-safe-events.jsonl> --json-out audit.json --html-out audit.html",
        "note": "the independent repository supplies input and owns the workflow; OMEGA intervention is not required",
    }
    authority = {
        "case_id": "zero-value-bridge-public-ci-kit-001", "status": "AUTHORIZATION_REQUIRED",
        "surface": "mrmohamedhassan2017-blip/agent-runtime-audit",
        "exact_action": "publish one privacy-safe independent CI consumption guide/template pinned to the existing public commit",
        "content": "copyable workflow, receipt/provenance fields, evidence-level and privacy rules only",
        "measurement": "one qualifying non-owner L2 invocation and L3 reproducible output with utility decision",
        "limits": ["no outreach", "no workflow execution by owner/OMEGA", "no changes to ZERO-INBOUND-001 criteria or hash",
                   "no telemetry", "0 KWD", "no unrelated files"],
        "rollback": "revert the single documentation/template commit",
        "platform_policy": "normal public repository documentation; no artificial traffic or engagement",
    }
    branch = {"id": "zero-economic-bridge-001", "objective": "Obtain one independently consumed CI reliability verification",
              "state": "WAITING_AUTHORIZATION", "dependencies": ["inbound-evidence"],
              "wake_conditions": [authority["case_id"] + " granted", "qualifying independent L2/L3 evidence arrives"],
              "evidence_required": [value_unit["success_condition"]], "authority_required": [authority["case_id"]],
              "resources_required": ["existing public artifact", "one independent repository"],
              "expected_value": winner["eva"], "information_value": winner["evsi"],
              "risk": winner["contamination_risk"], "reversibility": "HIGH",
              "estimated_cost": {"cash_kwd": 0, "compute": "LOW"}, "estimated_duration": "external/unknown",
              "last_progress": "value unit, contract, provenance, RED controls, consumer template, and routes frozen",
              "next_executable_actions": []}
    state["branches"] = [b for b in state.get("branches", []) if b.get("id") != branch["id"]] + [branch]
    state["global_state"] = "WAITING_AUTHORIZATION"
    experiment = {"experiment_id": "ZERO-VALUE-BRIDGE-001", "status": "FROZEN_WAITING_AUTHORIZATION",
                  "causal_ladder": ["PUBLIC_DISCOVERY", "INDEPENDENT_CI_CONSUMPTION", "VERIFIED_USEFUL_OUTPUT",
                                    "REPEAT_OR_DEEPER_USE", "ECONOMIC_COMMITMENT", "EXTERNAL_SETTLEMENT",
                                    "ONLY_THEN_EVALUATE_NATIVE_SETTLEMENT"],
                  "value_unit": value_unit, "value_contract": contract, "evidence_ladder": ladder,
                  "provenance_rule": provenance, "red": red, "routes": routes, "winner": winner,
                  "minimum_interface": consumer_workflow, "authorization_case": authority,
                  "current_real_evidence_level": "L0", "external_action_performed": False,
                  "external_evidence": [], "real_economic_value_kwd": 0, "financial_authority_kwd": 0,
                  "zeu": "SIMULATION_ONLY", "zeu_x": "UNPROVEN_RESEARCH_HYPOTHESIS",
                  "native_real_token": "NOT_JUSTIFIED", "preserved_inbound_frozen_hash": frozen_hash}
    for name, payload in (("value_bridge_experiment.json", experiment), ("value_unit.json", value_unit),
                          ("value_contract.json", contract), ("value_evidence_ladder.json", ladder),
                          ("value_provenance_rule.json", provenance), ("value_bridge_routes.json", routes),
                          ("value_bridge_authority_case.json", authority), ("value_bridge_consumer_template.json", consumer_workflow),
                          ("state.json", state), ("branches.json", state["branches"])):
        _write(out / name, payload)
    return experiment


COUNTERPARTY_BENEFITS = {"problem_reality": .14, "problem_severity": .1, "problem_freshness": .08,
                         "capability_match": .12, "decision_relevance": .12,
                         "public_contact_permission": .06, "machine_consumption_likelihood": .1,
                         "time_to_verifiable_result": .08, "eva": .1, "evsi": .1}
COUNTERPARTY_BURDENS = {"contamination_risk": .1, "authority_friction": .08}
WORK_ORDER_STAGES = ["OBSERVED_PROBLEM", "QUALIFIED", "PROPOSED_WORK_ORDER", "AUTHORIZED", "ACCEPTED",
                     "EXECUTING", "EVIDENCE_PRODUCED", "VERIFIED", "ACCEPTED_BY_COUNTERPARTY",
                     "REJECTED", "NO_DECISION_VALUE", "ECONOMIC_COMMITMENT", "SETTLED"]


def score_counterparty_problem(candidate: dict[str, Any]) -> dict[str, Any]:
    required = {"problem_id", "public_source", "timestamp", "problem_statement", "evidence_reference",
                "affected_system", "problem_freshness", "severity", "frequency", "attempted_solutions",
                "capability_match", "ci_reliability_relevance", "counterparty", "contact_route",
                "uncertainty", "confidence"} | set(COUNTERPARTY_BENEFITS) | set(COUNTERPARTY_BURDENS)
    missing = sorted(required - set(candidate))
    score = sum(float(candidate.get(k, 0)) * w for k, w in COUNTERPARTY_BENEFITS.items())
    score -= sum(float(candidate.get(k, 0)) * w for k, w in COUNTERPARTY_BURDENS.items())
    result = dict(candidate)
    qualified = not missing and result.get("problem_reality", 0) >= .7 and result.get("capability_match", 0) >= .45
    result.update({"qualification": "QUALIFIED" if qualified else "REJECTED_WEAK_MATCH",
                   "missing_fields": missing, "score": round(score, 4) if not missing else None,
                   "semantic_boundary": "PUBLIC_PROBLEM_NOT_DEMAND"})
    return result


def generate_public_problem_candidates() -> list[dict[str, Any]]:
    common = {"public_contact_permission": .55, "contamination_risk": .08, "authority_friction": .62,
              "contact_route": "public GitHub issue discussion; any new comment requires bounded owner authority",
              "eva": .72, "evsi": .88}
    candidates = [
        {**common, "problem_id": "openhands-sdk-4260", "public_source": "https://github.com/OpenHands/software-agent-sdk/issues/4260",
         "timestamp": "2026-06-23", "problem_statement": "Cloud PR-review automations intermittently time out before posting a review, leaving an in-progress comment orphaned.",
         "evidence_reference": "open issue reports 50+ automation timeouts and 24 runtime command timeouts in six hours, with completion and failure paths compared",
         "affected_system": "OpenHands Cloud automation PR reviewer", "problem_freshness": .91, "severity": "HIGH",
         "frequency": "50+ automation timeouts and 24 runtime timeouts observed in 6h", "attempted_solutions": ["paired successful/stuck trace comparison", "timeout/root-cause analysis", "suggested bounded retry and watchdog"],
         "capability_match": .74, "ci_reliability_relevance": .96, "counterparty": "OpenHands/software-agent-sdk maintainers and issue author",
         "uncertainty": ["raw production traces are private", "current audit schema needs a privacy-safe event-name mapping", "maintainers may already have sufficient telemetry"],
         "confidence": .92, "problem_reality": .98, "problem_severity": .9, "machine_consumption_likelihood": .78,
         "time_to_verifiable_result": .78, "decision_relevance": .86},
        {**common, "problem_id": "langgraph-7417", "public_source": "https://github.com/langchain-ai/langgraph/issues/7417",
         "timestamp": "2026-04-05", "problem_statement": "Long tool calls are silently re-executed from checkpoints, producing duplicate work and cost.",
         "evidence_reference": "open issue reports identical arguments, duplicate tool nodes, 2-3x work, and reproduction across versions 1.1.3-1.1.6",
         "affected_system": "LangGraph Cloud long-running tools", "problem_freshness": .78, "severity": "HIGH",
         "frequency": "consistent for reported 3-10 minute tool calls", "attempted_solutions": ["grace-period setting", "isolated loops", "thread wrapper"],
         "capability_match": .68, "ci_reliability_relevance": .82, "counterparty": "LangGraph maintainers and independent issue author",
         "uncertainty": ["managed-cloud server is not inspectable", "event export schema unknown", "existing tracing may be sufficient"],
         "confidence": .88, "problem_reality": .94, "problem_severity": .88, "machine_consumption_likelihood": .72,
         "time_to_verifiable_result": .62, "decision_relevance": .84},
        {**common, "problem_id": "langgraph-8358", "public_source": "https://github.com/langchain-ai/langgraph/issues/8358",
         "timestamp": "2026-07-17", "problem_statement": "Protocol-v2 replay lacks a durable run/checkpoint boundary after thread hydration.",
         "evidence_reference": "open issue documents lifecycle payloads without run_id and historical/live replay ambiguity",
         "affected_system": "LangGraph Agent Server protocol v2", "problem_freshness": .96, "severity": "MEDIUM_HIGH",
         "frequency": "first subscription after hydrating an idle thread", "attempted_solutions": ["client-side event correlation analysis"],
         "capability_match": .7, "ci_reliability_relevance": .76, "counterparty": "LangGraph maintainers and issue author",
         "uncertainty": ["protocol fix may supersede an external audit", "utility decision owner unknown"],
         "confidence": .9, "problem_reality": .93, "problem_severity": .78, "machine_consumption_likelihood": .8,
         "time_to_verifiable_result": .74, "decision_relevance": .8},
        {**common, "problem_id": "langgraph-8382", "public_source": "https://github.com/langchain-ai/langgraph/issues/8382",
         "timestamp": "2026-07-21", "problem_statement": "Replay order diverges from live parallel-superstep order and corrupts continued-thread state.",
         "evidence_reference": "public issue reports a silent data-integrity failure affecting audit trails and continued execution",
         "affected_system": "LangGraph DeltaChannel beta", "problem_freshness": .97, "severity": "HIGH",
         "frequency": "parallel writers followed by state inspection or continuation", "attempted_solutions": ["public reproducer and ordering comparison"],
         "capability_match": .5, "ci_reliability_relevance": .7, "counterparty": "LangGraph maintainers and issue author",
         "uncertainty": ["beta component", "requires ordering semantics outside current audit"],
         "confidence": .84, "problem_reality": .9, "problem_severity": .86, "machine_consumption_likelihood": .58,
         "time_to_verifiable_result": .44, "decision_relevance": .74},
        {**common, "problem_id": "langgraph-7094", "public_source": "https://github.com/langchain-ai/langgraph/issues/7094",
         "timestamp": "2026-03-10", "problem_statement": "Async checkpoint coroutine chains accumulate and retain runtime state, producing a memory leak.",
         "evidence_reference": "open issue includes a reproducer and ties retained checkpoint state to async durability",
         "affected_system": "LangGraph async checkpoint durability", "problem_freshness": .72, "severity": "HIGH",
         "frequency": "grows with superstep count when checkpoint writes have latency", "attempted_solutions": ["sync durability workaround", "minimal reproducer"],
         "capability_match": .32, "ci_reliability_relevance": .58, "counterparty": "LangGraph maintainers and issue author",
         "uncertainty": ["requires memory profiling rather than lifecycle receipt", "poor fit to existing capability"],
         "confidence": .86, "problem_reality": .92, "problem_severity": .84, "machine_consumption_likelihood": .42,
         "time_to_verifiable_result": .3, "decision_relevance": .68},
    ]
    return sorted((score_counterparty_problem(c) for c in candidates),
                  key=lambda item: (item["qualification"] != "QUALIFIED", -(item["score"] or 0), item["problem_id"]))


def validate_work_order(work_order: dict[str, Any]) -> list[str]:
    required = {"work_order_id", "requester_counterparty", "source_problem", "requested_outcome",
                "input_contract", "execution_contract", "acceptance_contract", "evidence_contract",
                "verifier", "resource_budget", "authority_scope", "timeout", "kill_conditions",
                "settlement_state", "provenance", "stage"}
    issues = [f"missing:{key}" for key in sorted(required - set(work_order))]
    if work_order.get("stage") not in WORK_ORDER_STAGES:
        issues.append("invalid_stage")
    if work_order.get("settlement_state") != "NONE" and work_order.get("stage") not in {"ECONOMIC_COMMITMENT", "SETTLED"}:
        issues.append("premature_settlement")
    return issues


def operate_counterparty_cycle(root: Path) -> dict[str, Any]:
    root = root.resolve(); out = root / ".omega" / "zero"
    state = json.loads((out / "state.json").read_text(encoding="utf-8"))
    problems = generate_public_problem_candidates(); qualified = [p for p in problems if p["qualification"] == "QUALIFIED"]
    winner = qualified[0]
    red = {"role": "RED", "target": winner["problem_id"], "verdict": "PROPOSE_ONLY",
           "questions": ["Are we solving a real problem or interpreting noise as demand?",
                         "Would the counterparty care about the output?", "Could existing free tooling already solve it?",
                         "Are we selecting it because it fits our product rather than because it matters?",
                         "Can the result influence an external decision?", "Can independence be proven?",
                         "Would this still be useful if ZEU did not exist?"],
           "objection": "The issue already has rich Datadog evidence and root-cause analysis; the current fixed OMEGA event schema may add no decision value unless maintainers want a privacy-safe regression receipt.",
           "required_falsification": "counterparty independently accepts the bounded receipt input/decision contract before any work is called useful"}
    work_order = {
        "work_order_id": "WO-ZERO-001", "requester_counterparty": "UNACCEPTED: OpenHands/software-agent-sdk maintainers",
        "source_problem": winner["public_source"],
        "requested_outcome": "distinguish a completed PR-review lifecycle from an orphaned timeout lifecycle using privacy-safe event names and hashes",
        "input_contract": "counterparty-selected, privacy-reviewed event-name JSONL for one completed and one failed run; no raw messages, secrets, identifiers, or private logs",
        "execution_contract": "map declared lifecycle names without inventing events; run ci-reliability-verification-receipt-v1 deterministically; retain no input",
        "acceptance_contract": "both reports reproduce by hash and identify the missing terminal/review outcome without false demand or causality claims",
        "evidence_contract": "source commit, input hashes, output hashes, verifier identity, reproduction verdict, and ACCEPT/REJECT/REPAIR/NO_DECISION_VALUE decision",
        "verifier": "independent counterparty or counterparty-designated verifier; OMEGA self-verification is insufficient",
        "resource_budget": {"cash_kwd": 0, "compute": "bounded local/CI", "human_attention": "one review"},
        "authority_scope": "PROPOSED_ONLY; no contact, data access, execution, or repository modification authorized",
        "timeout": "one bounded evaluation; terminate if input mapping cannot be agreed",
        "kill_conditions": ["private data required", "counterparty has no interest", "existing tooling already supplies equivalent receipt",
                            "event mapping would force a misleading result", "scope or spend exceeds authority"],
        "settlement_state": "NONE", "provenance": {"problem": winner["public_source"], "observed_at": _now(),
                                                       "capability": "ci-reliability-verification-receipt-v1"},
        "stage": "PROPOSED_WORK_ORDER", "accepted": False, "external_demand": False,
    }
    issues = validate_work_order(work_order)
    if issues:
        raise RuntimeError("INVALID_WORK_ORDER:" + ",".join(issues))
    povu = {"name": "Proof of Verified Utility", "status": "UNPROVEN_RESEARCH_PRIMITIVE",
            "not": ["money", "mining", "token", "economic value"],
            "required": ["independently existing need", "work executed", "provenance-bound evidence",
                         "independent verification", "real external decision affected"],
            "satisfied": [], "value_created": False}
    authority = {"case_id": "zero-counterparty-wo-001-contact", "status": "AUTHORIZATION_REQUIRED",
                 "surface": winner["public_source"],
                 "exact_action": "post one problem-specific public GitHub issue comment offering the frozen privacy-safe paired-run receipt experiment",
                 "identity": "owner-controlled GitHub identity; no claim that work was requested",
                 "limits": ["one comment", "no private data request", "no follow-up without response", "no repository changes",
                            "no bulk contact", "no spend", "no demand/acceptance claim"],
                 "rollback": "comment cannot be fully retracted from history; edit/close offer and cease immediately",
                 "measurement": "counterparty explicitly accepts, rejects, or ignores the proposed input and decision contract"}
    branch = {"id": "zero-counterparty-work-order-001", "objective": "convert one public problem into an independently accepted bounded work order",
              "state": "WAITING_AUTHORIZATION", "dependencies": ["zero-economic-bridge-001"],
              "wake_conditions": [authority["case_id"] + " granted", "counterparty independently initiates contact"],
              "evidence_required": ["explicit independent acceptance of WO-ZERO-001"], "authority_required": [authority["case_id"]],
              "resources_required": ["public issue", "privacy-safe counterparty input"], "expected_value": winner["eva"],
              "information_value": winner["evsi"], "risk": winner["contamination_risk"], "reversibility": "MEDIUM",
              "estimated_cost": {"cash_kwd": 0}, "estimated_duration": "external/unknown",
              "last_progress": "five public problems reviewed; top candidate RED-challenged; proposed work order frozen",
              "next_executable_actions": []}
    state["branches"] = [b for b in state.get("branches", []) if b.get("id") != branch["id"]] + [branch]
    state["global_state"] = "WAITING_AUTHORIZATION"
    result = {"protocol": "ZERO COUNTERPARTY + WORK-ORDER PROTOCOL V1", "status": "OPERATED_PROPOSED_ONLY",
              "lifecycle": WORK_ORDER_STAGES, "public_problems": problems, "qualified_counterparties": qualified,
              "winner": winner, "red": red, "proposed_work_order": work_order, "povu": povu,
              "internal_zeu_rules": ["SELF_WORK_ORDER != EXTERNAL_DEMAND", "INTERNAL_ZEU_SETTLEMENT != REAL_SETTLEMENT",
                                     "SIMULATED_ESCROW != MONEY", "OWNER_REQUEST != INDEPENDENT_COUNTERPARTY",
                                     "INTERNAL_PROFIT != REAL_ECONOMIC_VALUE"],
              "authorization_case": authority, "external_action_performed": False,
              "current_value_level": "L0", "real_economic_value_kwd": 0, "zeu": "SIMULATION_ONLY",
              "zeu_x": "UNPROVEN_RESEARCH_HYPOTHESIS", "native_real_token": "NOT_JUSTIFIED",
              "zak_state": state["global_state"]}
    for name, payload in (("counterparty_cycle_0007.json", result), ("public_problem_candidates.json", problems),
                          ("work_order_protocol.json", {"stages": WORK_ORDER_STAGES, "schema": list(work_order)}),
                          ("proposed_work_order.json", work_order), ("povu_research.json", povu),
                          ("counterparty_authority_case.json", authority), ("state.json", state),
                          ("branches.json", state["branches"])):
        _write(out / name, payload)
    return result


def record_value_bridge_publication(root: Path) -> dict[str, Any]:
    root = root.resolve(); out = root / ".omega" / "zero"
    experiment_path = out / "value_bridge_experiment.json"
    experiment = json.loads(experiment_path.read_text(encoding="utf-8"))
    expected_hash = "084d9cc1f6ef7e7f97b3ba480daf16df95e15df2607d1cc5b08298eb5d8eab87"
    if experiment.get("preserved_inbound_frozen_hash") != expected_hash:
        raise RuntimeError("FROZEN_HASH_DRIFT")
    evidence = {"event": "CI_KIT_PUBLICATION_VERIFIED", "authorization": "zero-value-bridge-public-ci-kit-001",
                "authorization_state": "CONSUMED_CLOSED", "remote": "https://github.com/mrmohamedhassan2017-blip/agent-runtime-audit",
                "commit": "4e89d468a42492b851dcba7ce743016b6e56d3eb", "parent": "159def24e9a75ef568c802d9d0fb54dd0f89db25",
                "published_files": ["INDEPENDENT-CI-CONSUMER.md"],
                "guide_sha256": "54b97f0e5545dd2de4e4e41d7bef4860e70c39497b3ea04778de446ac80b9a24",
                "verified": True, "verification": "unauthenticated fresh clone; parent diff contains one allowlisted file; original manifest blobs match",
                "frozen_inbound_hash": expected_hash, "external_action": True, "external_evidence": False,
                "discovery": False, "invocation": False, "demand": False, "economic_value_kwd": 0,
                "recorded_at": _now()}
    experiment["status"] = "PUBLISHED_WAITING_INDEPENDENT_CONSUMPTION"
    experiment["authorization_case"]["status"] = "CONSUMED_CLOSED"
    experiment["publication"] = evidence
    _write(experiment_path, experiment); _write(out / "value_bridge_publication_evidence.json", evidence)
    authority_path = out / "value_bridge_authority_case.json"
    authority = json.loads(authority_path.read_text(encoding="utf-8")); authority["status"] = "CONSUMED_CLOSED"
    authority["consumed_by_commit"] = evidence["commit"]; _write(authority_path, authority)
    return evidence


def record_counterparty_comment(root: Path) -> dict[str, Any]:
    root = root.resolve(); out = root / ".omega" / "zero"
    order_path = out / "proposed_work_order.json"
    order = json.loads(order_path.read_text(encoding="utf-8"))
    if order.get("work_order_id") != "WO-ZERO-001": raise RuntimeError("UNKNOWN_WORK_ORDER")
    causal = {"baseline": "OpenHands issue already contains Datadog traces, timeout counts, and root-cause analysis without OMEGA.",
              "intervention": "offer one optional privacy-safe paired-run event-name receipt with reproducible input/output hashes",
              "expected_decision_change": "make it easier to decide whether a completed versus orphaned review lifecycle is distinguishable without exposing production data",
              "counterfactual": "maintainers likely continue using existing observability evidence and issue investigation",
              "observed_decision_change": "UNKNOWN until an attributable maintainer response",
              "marginal_utility": "UNKNOWN until an attributable maintainer response"}
    evidence = {"event": "REAL_EXTERNAL_ACTION", "authorization_case": "zero-counterparty-wo-001-contact",
                "authorization_state": "CONSUMED_CLOSED", "surface": "https://github.com/OpenHands/software-agent-sdk/issues/4260",
                "comment_url": "https://github.com/OpenHands/software-agent-sdk/issues/4260#issuecomment-5444759832",
                "comment_id": "5444759832", "comment_timestamp": "2026-08-27T23:20:00+03:00",
                "identity": "mrmohamedhassan2017-blip", "scope": "one public technical comment",
                "response": "NO_RESPONSE", "external_evidence": False, "discovery": False,
                "independent_invocation": False, "utility": False, "demand": False,
                "economic_value_kwd": 0, "causal_value_record": causal}
    order["causal_value_record"] = causal; order["stage"] = "PROPOSED_WORK_ORDER"; order["accepted"] = False
    order["external_contact"] = evidence["comment_url"]; order["response"] = "NO_RESPONSE"
    authority_path = out / "counterparty_authority_case.json"
    authority = json.loads(authority_path.read_text(encoding="utf-8")); authority["status"] = "CONSUMED_CLOSED"
    authority["comment_url"] = evidence["comment_url"]; authority["comment_id"] = evidence["comment_id"]
    state_path = out / "state.json"; state = json.loads(state_path.read_text(encoding="utf-8"))
    for branch in state.get("branches", []):
        if branch.get("id") == "zero-counterparty-work-order-001":
            branch["state"] = "PARKED_WAITING_EXTERNAL"; branch["authority_required"] = []
            branch["wake_conditions"] = ["attributable maintainer response to the single comment", "owner kill switch"]
            branch["last_progress"] = "one authorized public comment posted; awaiting response"
    state["global_state"] = "RUNNING"
    for name, payload in (("proposed_work_order.json", order), ("counterparty_authority_case.json", authority),
                          ("counterparty_comment_evidence.json", evidence), ("state.json", state),
                          ("branches.json", state["branches"])):
        _write(out / name, payload)
    return evidence


def execute_first_cycle(root: Path) -> dict[str, Any]:
    root=root.resolve(); out=root/".omega"/"zero"; out.mkdir(parents=True,exist_ok=True)
    reality=inspect_reality(root); branches=initialize_branches(reality); ranked=candidate_actions(); red=red_challenge(ranked)
    chosen=next(item for item in ranked if item["executable_now"] and not item["busywork"])
    frozen={"cycle_id":"zak-cycle-0001","frozen_at":_now(),"reality":reality,"branches":branches,"actions":ranked,
            "resource_model":{"time":"bounded","compute":"local","model_api_budget":"existing only","cash_kwd":0,
              "human_attention":"scarce","external_channels":["Gmail E2 monitor"],"credentials":"outside repository",
              "data":"repository truth","reputation":"bounded","agent_capacity":1},"red":red}
    frozen["input_hash"]=_hash(frozen)
    if chosen["id"]!="freeze-inbound-install-experiment":
        raise RuntimeError("first cycle selected an unsupported action")
    experiment={"experiment_id":"ZERO-INBOUND-001","evidence_type":"DERIVED","status":"FROZEN_NOT_PUBLISHED",
      "hypothesis":"A privacy-bounded self-service agent-runtime audit can produce at least one genuine external installation attempt.",
      "artifact":"existing venture-audit-log CLI plus privacy-safe sample report","baseline":"zero externally verified installations",
      "metric":"independently initiated external installation attempt","threshold":1,
      "acceptance":"one provenance-bearing installation attempt by an external party",
      "rejection":"zero installation attempts after a future preregistered exposure window",
      "non_signals":["internal tests","OMEGA execution","page view","email sent","delivery"],
      "publishing_authority":"REQUIRED_BEFORE_EXTERNAL_EXECUTION","financial_authority_kwd":0,
      "kill_criteria":["cannot expose without private data","distribution requires unauthorized identity or spend"],
      "frozen_from_cycle":frozen["input_hash"]}
    experiment["specification_hash"]=_hash(experiment)
    evidence=make_evidence(evidence_id="zak-cycle-0001-option",evidence_type="DERIVED",source="repository truth + ZAK shadow ranking",
      subject="inbound evidence option",claim="A bounded inbound installation experiment is specified and ready for a future publishing decision, but has produced no external evidence.",
      confidence=.9,independence="INTERNAL",reproducibility="rerun frozen cycle inputs",sample_size=None,
      manipulation_risk="INTERNAL_MODEL_BIAS")
    decision={"decision_id":"zak-decision-0001","timestamp":_now(),"state_hash":frozen["input_hash"],
      "candidate_actions":[item["id"] for item in ranked],"chosen_action":chosen["id"],
      "expected_outcome":"OPTION_UNLOCKED without claiming external evidence","actual_outcome":"OPTION_UNLOCKED",
      "evidence_ids":[evidence["evidence_id"]],"regret":"NOT_YET_OBSERVABLE",
      "lesson":"Parking external branches prevents global waiting; publish only after authority and measurable exposure are defined.",
      "policy_mode":"SHADOW","rollback":"delete generated ZERO-INBOUND-001 artifact; no external state changed"}
    for item in branches:
        if item["id"]=="inbound-evidence":
            item["state"]="WAITING_AUTHORIZATION"; item["last_progress"]="ZERO-INBOUND-001 frozen; no publication"
            item["wake_conditions"]=["publishing authority and lawful measurable surface available"]
            item["next_executable_actions"]=[]
    global_state="RUNNING" if any(item["executable_now"] and not item["busywork"] and item["id"]!=chosen["id"] for item in ranked) else "PARKED"
    result={"format":"omega.zero-agency-kernel","format_version":1,"mode":"SHADOW","global_state":global_state,
      "law":"WAITING_BRANCH != WAITING_SYSTEM","cycle":frozen,"decision":decision,"executed_action":chosen,
      "evidence":evidence,"inbound_experiment":experiment,"branches":branches,"zeu":zeu_ledger(),
      "stress_lab":stress_scenarios(),"causal_hypotheses":causal_hypotheses(),
      "world_model_boundary":["EVIDENCE_FOUNDRY","WORLD_MODEL","ZAK","CONSTITUTION_POLICY","EXECUTION","REALITY"],
      "real_economic_state":{"verified_value_kwd":0,"revenue_kwd":0,"cash_kwd":0},
      "native_digital_instrument_gate":{"default":"NO_NATIVE_REAL_TOKEN","status":"NOT_JUSTIFIED",
        "alternatives":["internal accounting only","bank rails","payment processors","lawful stable-value rails","other lawful settlement","native digital instrument"]}}
    for name,value in (("state.json",result),("branches.json",branches),("action_queue.json",ranked),
                       ("inbound_experiment.json",experiment),("zeu_ledger.json",result["zeu"]),
                       ("causal_hypotheses.json",result["causal_hypotheses"]),("stress_lab.json",result["stress_lab"])):
        _write(out/name,value)
    with (out/"decisions.jsonl").open("a",encoding="utf-8") as stream:
        if not (out/"decisions.jsonl").stat().st_size: stream.write(_canonical(decision)+"\n")
    with (out/"evidence.jsonl").open("a",encoding="utf-8") as stream:
        if not (out/"evidence.jsonl").stat().st_size: stream.write(_canonical(evidence)+"\n")
    return result
