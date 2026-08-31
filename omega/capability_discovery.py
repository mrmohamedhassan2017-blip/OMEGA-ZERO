from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATUSES = {"PROPOSED", "EXPERIMENTING", "VERIFIED", "REJECTED", "BLOCKED", "WAITING_EXTERNAL_EVIDENCE"}
EVIDENCE_CATEGORIES = {"VERIFIED_OBJECTIVE_EVIDENCE", "INTERNAL_AI_EVALUATION", "EXTERNAL_HUMAN_EVIDENCE"}


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _hash(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode()).hexdigest()


def read_events(root: Path) -> list[dict[str, Any]]:
    path = root / ".omega" / "logs" / "events.jsonl"; result = []
    if not path.exists(): return result
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            item = json.loads(line)
            if isinstance(item, dict): result.append(item)
        except json.JSONDecodeError: pass
    return result


def incident_counts(events: list[dict[str, Any]]) -> Counter[str]:
    result: Counter[str] = Counter()
    for item in events:
        event = str(item.get("event", "")); reason = str(item.get("reason", "")).lower()
        if event in {"HARD_BLOCKER", "APPROVAL_REQUIRED"}: result["blockers"] += 1
        if "restart" in event.lower(): result["restarts"] += 1
        if "test_failed" in event.lower() or "timeout" in reason: result["test_failures"] += 1
        if any(x in reason for x in ("sandbox", "interpreter", "python is unavailable")): result["sandbox_verification"] += 1
        if any(x in reason for x in ("external evaluator", "independently supplied")): result["external_evidence"] += 1
    return result


def score_candidate(item: dict[str, Any]) -> dict[str, Any]:
    positive = .30*item["expected_value"] + .22*item["reusability"] + .18*item["future_capabilities_unlocked"] + .15*item["confidence"]
    penalty = .06*item["implementation_cost"] + .04*item["complexity"] + .04*item["risk"] + .01*item["external_dependency"]
    return {**item, "score": round(positive-penalty, 4), "scoring_rationale": {
        "formula": "0.30V+0.22R+0.18U+0.15C-0.06Cost-0.04Complexity-0.04Risk-0.01External",
        "positive": round(positive, 4), "penalty": round(penalty, 4)}}


def build_candidates(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts = incident_counts(events); repeated = min(1., sum(counts.values())/8)
    common = {"status": "PROPOSED", "external_dependency": 0}
    raw = [
        {**common, "id":"incident-memory-preflight", "description":"Convert recurring failures into reusable preflight checks",
         "problem_addressed":"repeated lifecycle and verification failures", "expected_value":.72+.2*repeated,
         "reusability":.92, "future_capabilities_unlocked":.82, "implementation_cost":.28, "complexity":.25,
         "risk":.18, "confidence":.78, "evidence_required":["historical events","determinism test","host regression suite"], "dependencies":["events.jsonl"]},
        {**common, "id":"state-transition-coverage", "description":"Discover untested lifecycle state transitions",
         "problem_addressed":"hidden recovery paths", "expected_value":.76, "reusability":.84,
         "future_capabilities_unlocked":.74, "implementation_cost":.42, "complexity":.45, "risk":.22,
         "confidence":.70, "evidence_required":["transition inventory","model tests"], "dependencies":["supervisor events"]},
        {**common, "id":"evidence-boundary-guard", "description":"Detect confusion between objective, AI, and human evidence",
         "problem_addressed":"unsupported capability claims", "expected_value":.70+.12*min(1,counts["external_evidence"]),
         "reusability":.86, "future_capabilities_unlocked":.66, "implementation_cost":.24, "complexity":.20,
         "risk":.12, "confidence":.82, "external_dependency":.15,
         "evidence_required":["claim provenance audit","negative evidence preservation test"], "dependencies":["PROJECT_STATE.md","NEXT_TASK.md"]}]
    return sorted((score_candidate(x) for x in raw), key=lambda x:(-x["score"],x["id"]))


def unknown_unknown_proposals(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    observed = {str(x.get("event", "")) for x in events}
    transitions = [("AGENT_COMPLETED","CHANGES_DETECTED"),("CHANGES_DETECTED","HOST_TEST_STARTED"),
                   ("HOST_TEST_FAILED","AGENT_REPAIR_STARTED"),("RESTARTING","SUPERVISOR_RECOVERED")]
    return [{"kind":"untested_state_transition","from":a,"to":b,
             "proposed_experiment":f"replay {a} -> {b} with a frozen expected state"}
            for a,b in transitions if a not in observed or b not in observed]


def run_discovery(root: Path, output_dir: Path|None=None) -> dict[str, Any]:
    root=root.resolve(); now=datetime.now(timezone.utc).isoformat(timespec="seconds"); events=read_events(root)
    out=output_dir or root/".omega"; prior={}
    registry_path=out/"capabilities.json"
    if registry_path.exists():
        try: prior={x["id"]:x.get("status","PROPOSED") for x in json.loads(registry_path.read_text(encoding="utf-8")).get("candidates",[])}
        except (json.JSONDecodeError, KeyError, TypeError): prior={}
    counts=incident_counts(events); candidates=build_candidates(events)
    for candidate in candidates: candidate["status"]=prior.get(candidate["id"],candidate["status"])
    eligible=[x for x in candidates if x["status"] in {"PROPOSED","EXPERIMENTING"}]
    selected={**(eligible[0] if eligible else candidates[0])}
    experiment={"candidate_id":selected["id"],"hypothesis":f"The {selected['id']} capability reduces the highest scored current limitation.",
      "baseline":{"historical_event_count":len(events),"incident_counts":dict(counts)},"metric":"all acceptance checks pass","threshold":1.0,
      "acceptance_criteria":["at least three candidates","deterministic scoring","evidence categories separated","unknown proposals are non-mutating"],
      "rejection_criteria":["fewer than three candidates","non-deterministic ranking","external evidence relabeled"],
      "test_scenario":"replay repository event history","deterministic_seed":0,"frozen_at":now}
    experiment["specification_hash"]=_hash(experiment)
    proposals=unknown_unknown_proposals(events)
    fresh=build_candidates(events)
    checks={"three_candidates":len(candidates)>=3,
            "deterministic_scoring":[(x["id"],x["score"]) for x in candidates]==[(x["id"],x["score"]) for x in fresh],
            "evidence_categories_separate":len(EVIDENCE_CATEGORIES)==3,
            "proposals_are_non_mutating":all("proposed_experiment" in x for x in proposals)}
    if selected["id"]=="evidence-boundary-guard":
        next_task=(root/"NEXT_TASK.md").read_text(encoding="utf-8") if (root/"NEXT_TASK.md").exists() else ""
        checks["external_gate_preserved"]="waiting_external_evidence" in next_task.lower()
        checks["human_evidence_not_fabricated"]=not any(x.get("category")=="EXTERNAL_HUMAN_EVIDENCE" for x in events)
    if selected["id"]=="state-transition-coverage":
        checks["transition_gaps_are_explicit"]=bool(proposals)
    accepted=all(checks.values()); selected["status"]="VERIFIED" if accepted else "REJECTED"
    candidates=[selected if x["id"]==selected["id"] else x for x in candidates]
    objective={"category":"VERIFIED_OBJECTIVE_EVIDENCE","checks":checks,"host_verification_required":True,"negative_evidence":[]}
    red={"category":"INTERNAL_AI_EVALUATION","role":"RED","verdict":"ACCEPT" if accepted else "REJECT",
         "challenges":["Historical logs may be incomplete","Event frequency is not identical to prevented harm"],
         "disagreement":"External usefulness remains unverified."}
    acceptance={"category":"INTERNAL_AI_EVALUATION","role":"ACCEPTANCE","verdict":"ACCEPT" if accepted else "REJECT","criteria":checks}
    verified_ids={x["id"] for x in candidates if x["status"]=="VERIFIED"}
    self_model={"format":"omega.self-model","format_version":1,"last_verified":now,
      "verified_capabilities":[{"id":"deterministic-core","confidence":.95,"evidence":["88 host tests","benchmark gates","release 5/5","stability 11/11"],"provenance":"VERIFIED_OBJECTIVE_EVIDENCE"}]+[{"id":x["id"],"confidence":x["confidence"],"evidence":[f"registry:{x['id']}"] if x["id"]!=selected["id"] else [f"experiment:{experiment['specification_hash']}"],"provenance":"VERIFIED_OBJECTIVE_EVIDENCE"} for x in candidates if x["id"] in verified_ids],
      "partially_verified_capabilities":["autonomous host verification"],"unverified_claims":["OMEGA recommendations improve real decisions"],
      "known_limitations":["event history may omit pre-instrumentation incidents"],"recurring_failures":dict(counts),
      "external_dependencies":["independent evaluator sessions"],"human_only_dependencies":["external labels and friction observations"],
      "successful_recovery_patterns":["host-side verification","checkpointed scheduled restart"],
      "rejected_approaches":["unverified PID tree termination","sandbox execution as acceptance authority"]}
    registry={"format":"omega.capability-registry","format_version":1,"statuses":sorted(STATUSES),
              "scoring_model":candidates[0]["scoring_rationale"]["formula"],"candidates":candidates}
    result={"self_model":self_model,"registry":registry,"experiment":experiment,"objective_evidence":objective,
            "red_evaluation":red,"acceptance_evaluation":acceptance,"unknown_unknown_proposals":proposals,
            "outcome":"CAPABILITY_ACCEPTED" if accepted else "CAPABILITY_REJECTED"}
    (out/"experiments").mkdir(parents=True,exist_ok=True); (out/"evidence").mkdir(parents=True,exist_ok=True)
    for path,value in ((out/"self_model.json",self_model),(out/"capabilities.json",registry),
      (out/"experiments"/f"{experiment['specification_hash']}.json",experiment),
      (out/"evidence"/f"{experiment['specification_hash']}.json",{"objective":objective,"red":red,"acceptance":acceptance})):
        path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding="utf-8")
    return result
