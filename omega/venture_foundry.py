from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MISSION_I_TARGET_KWD = 50_000_000
VENTURE_STATES = {"DISCOVERED","RESEARCHING","EXPERIMENTING","BUILDING","VALIDATING","LAUNCH_READY","OPERATING","SCALING","PAUSED","KILLED","EXITED"}
ECONOMIC_CLASSES = {"FORECAST","SIGNAL","COMMITMENT","RECEIVABLE","RECEIVED","SETTLED","OWNER_WITHDRAWABLE"}
DEMAND_STRENGTH = {"PAGE_VIEW":1,"CLICK":2,"SIGNUP":3,"QUALIFIED_REPLY":4,"DEMO_REQUEST":5,"INSTALLATION":6,
                   "REPEATED_USAGE":7,"EXPLICIT_WTP":8,"PURCHASE_COMMITMENT":9,"PAYMENT":10,"REPEAT_PAYMENT":11,
                   "RETENTION":12,"EXPANSION":13}
CONTACT_SIGNAL_STRENGTH = {"DELIVERED":1,"ENGAGED":2,"QUALIFIED_REPLY":3,"DEMO_REQUEST":4,"INSTALL_ATTEMPT":5,
                           "WTP_SIGNAL":6,"PURCHASE_COMMITMENT":7,"VERIFIED_PAYMENT":8,"REPEAT_PAYMENT":9}

SOURCES = [
 {"id":"so-2025","url":"https://survey.stackoverflow.co/2025/ai","claim":"AI agent use is concentrated in software development while trust and accuracy remain concerns.","confidence":.9},
 {"id":"langchain-2025","url":"https://www.langchain.com/state-of-agent-engineering","claim":"A 1,300+ respondent survey reports production agent adoption and reliability engineering needs.","confidence":.85},
 {"id":"temporal-2025","url":"https://temporal.io/pages/state-of-development-2025","claim":"Teams report broad AI use but substantially lower availability of reliable supporting frameworks.","confidence":.8},
 {"id":"codex-win-34503","url":"https://github.com/openai/codex/issues/34503","claim":"A public Windows issue reports background agent dispatch stalling with application lifecycle effects.","confidence":.75},
 {"id":"csa-2026","url":"https://www.itpro.com/technology/artificial-intelligence/workers-cant-identify-work-produced-by-ai-agents-business-risks","claim":"Reported organizations struggle to identify agent actions and constrain inherited access.","confidence":.7},
 {"id":"sysadmin-manual","url":"https://www.reddit.com/r/sysadmin/comments/1qoxt8o/whats_the_one_manual_process_in_your_workflow_you/","claim":"Practitioners describe approval-sensitive automation, undocumented systems, and tribal knowledge.","confidence":.55},
]

PROBLEMS = [
 ("agent-runtime-audit","AI platform engineer","prove a background agent is alive, owned, and recoverable","agent failures can be silent or tied to terminal lifecycle"),
 ("agent-host-verification","engineering lead","verify agent changes outside the agent sandbox","sandbox limits can be confused with implementation failure"),
 ("agent-action-provenance","security engineer","attribute every agent action","agent and human activity can be hard to distinguish"),
 ("agent-permission-drift","identity engineer","detect excessive inherited agent access","agents can inherit human or shared-account privileges"),
 ("agent-restart-recovery","platform engineer","resume safely after worker crashes","retry and checkpoint behavior is difficult to validate"),
 ("agent-test-evidence","QA lead","separate claimed from host-verified test success","AI output is distrusted without objective verification"),
 ("agent-state-transition","SRE","find untested lifecycle transitions","rare recovery paths escape normal tests"),
 ("agent-incident-memory","engineering manager","prevent recurrence of previously solved agent failures","incident lessons remain scattered across logs and chats"),
 ("agent-audit-export","compliance lead","export reviewable agent evidence without secrets","raw logs leak sensitive payloads or omit provenance"),
 ("agent-cost-attribution","FinOps lead","attribute agent execution costs to tasks","agent activity spans tools and identities"),
 ("manual-approval-map","IT operations lead","automate routine steps while preserving approvals","teams distrust automation around consequential actions"),
 ("tribal-workflow-capture","small IT team","turn undocumented workflows into testable runbooks","mystery systems depend on tribal knowledge"),
 ("automation-preflight","sysadmin","detect unsafe automation assumptions before execution","automation can amplify a misunderstood process"),
 ("agent-observability-gap","agent developer","identify missing telemetry before production","generic monitoring does not explain agent decisions"),
 ("agent-release-gate","software vendor","gate agent-generated releases on reproducible evidence","speed can outrun QA and governance"),
 ("agent-data-boundary","privacy engineer","prove private inputs are absent from exports","review artifacts may reveal hidden evidence"),
 ("agent-human-handoff","support lead","preserve context when automation reaches a human-only step","handoffs lose state and repeat work"),
 ("agent-failure-replay","test engineer","replay agent incidents deterministically","production-only failures are hard to reproduce"),
 ("agent-vendor-comparison","CTO","compare agent reliability using the same acceptance contract","vendor claims are difficult to compare"),
 ("agent-readiness-report","consultant","produce a bounded agent deployment readiness report","buyers face integration and reliability uncertainty"),
]


def _hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()


def generate_theses() -> list[dict[str, Any]]:
    result=[]
    for i,(identifier,persona,job,pain) in enumerate(PROBLEMS):
        sources=[SOURCES[i%len(SOURCES)],SOURCES[(i+1)%len(SOURCES)]]
        result.append({"id":identifier,"customer":persona,"job_to_be_done":job,"pain":pain,
          "current_workaround":"manual log review, generic monitoring, or ad-hoc scripts","frequency":"recurring when agents execute",
          "economic_cost":"unverified; expected in engineering time and incident risk","urgency":"signal-supported, not customer-verified",
          "willingness_to_pay_evidence":[],"existing_alternatives":["generic observability","manual review"],
          "why_alternatives_fail":"hypothesis: lack agent-specific ownership, evidence, and lifecycle semantics",
          "reachable_channels":["AI agent engineering communities","developer tooling teams"],
          "evidence":[{"source":s["url"],"claim":s["claim"],"confidence":s["confidence"],"observed_at":"2026-08-27"} for s in sources],
          "evidence_confidence":round(sum(s["confidence"] for s in sources)/len(sources),2),
          "unknowns":["actual willingness to pay","buyer authority","switching cost","market size"]})
    return result


def score(thesis: dict[str, Any]) -> dict[str, Any]:
    evidence=thesis["evidence_confidence"]; fit=.95 if thesis["id"] in {"agent-runtime-audit","agent-host-verification","agent-incident-memory"} else .65
    values={"pain":.75,"willingness_to_pay":.15,"market_size":.55,"frequency":.8,"urgency":.65,
      "build_ability":fit,"time_to_mvp":.88,"validation_cost":.85,"scalability":.82,"recurring_revenue":.7,
      "distribution_leverage":.6,"retention":.65,"defensibility":.62,"risk":.28,"external_dependency":.35,"evidence":evidence}
    positive=sum(values[k] for k in ("pain","willingness_to_pay","market_size","frequency","urgency","build_ability","time_to_mvp","validation_cost","scalability","recurring_revenue","distribution_leverage","retention","defensibility"))/13
    total=round(.72*positive+.18*evidence-.10*((values["risk"]+values["external_dependency"])/2),4)
    return {**thesis,"score":total,"score_inputs":values,"scoring_rationale":"0.72 mean(value,feasibility,growth,defensibility)+0.18 evidence-0.10 mean(risk,external dependency)"}


def court(candidate: dict[str, Any]) -> dict[str, Any]:
    no_wtp=not candidate["willingness_to_pay_evidence"]
    recommendation="RUN_EXPERIMENT" if candidate["evidence_confidence"]>=.6 else "WAIT_FOR_EVIDENCE"
    return {"venture_id":candidate["id"],"builder":{"proposal":"local agent reliability evidence auditor","evidence":candidate["evidence"]},
      "prosecutor":{"arguments":["generic observability is entrenched","no direct willingness-to-pay evidence","source claims do not prove this product demand"]},
      "defender":{"arguments":["reliability and trust recur across independent public sources","OMEGA has verified lifecycle/evidence experience"]},
      "evidence_officer":{"facts":[e["claim"] for e in candidate["evidence"]],"assumptions":["buyers will pay", "agent-specific semantics outperform generic tools"],"external_human_evidence":[]},
      "judge":{"recommendation":recommendation,"confidence":.62 if no_wtp else .75,"reason":"Run a reversible demand test before building beyond an auditable local MVP."}}


def economic_ledger(entries: list[dict[str, Any]]) -> dict[str, Any]:
    for entry in entries:
        if entry.get("classification") not in ECONOMIC_CLASSES or not all(entry.get(k) is not None for k in ("source","timestamp","evidence","venture","verification_status")):
            raise ValueError("economic entry lacks classification or provenance")
    realized=sum(float(e["amount_kwd"]) for e in entries if e["classification"] in {"RECEIVED","SETTLED","OWNER_WITHDRAWABLE"} and e["verification_status"]=="VERIFIED")
    return {"format":"omega.economic-ledger","mission_target_kwd":MISSION_I_TARGET_KWD,"entries":entries,
            "verified_realized_economic_value_kwd":realized,"invariant":"forecasts and valuation are never realized cash"}


def audit_agent_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Create a privacy-bounded lifecycle report; raw reasons and payloads never leave the input."""
    names=[str(x.get("event","UNKNOWN")) for x in events]; counts={name:names.count(name) for name in sorted(set(names))}
    required={"AGENT_STARTED","AGENT_COMPLETED","CHANGES_DETECTED","HOST_TEST_STARTED","HOST_TEST_PASSED"}
    missing=sorted(required-set(names)); findings=[]
    if names.count("AGENT_STARTED")>names.count("AGENT_COMPLETED"): findings.append("agent execution without matching completion")
    if "HOST_TEST_STARTED" in names and not ({"HOST_TEST_PASSED","HOST_TEST_FAILED"}&set(names)): findings.append("host verification started without terminal result")
    if "HARD_BLOCKER" in names: findings.append("hard blocker recorded; inspect protected source log locally")
    return {"format":"omega.agent-runtime-audit","format_version":1,"event_count":len(events),"event_counts":counts,
            "required_lifecycle_events_missing":missing,"findings":findings,"raw_payloads_included":False,
            "credentials_included":False,"assessment":"REVIEW" if findings or missing else "PASS",
            "limitations":["event logs do not prove process ownership","absence of an event is not proof an action did not occur"]}


def render_agent_audit_html(report: dict[str, Any]) -> str:
    rows="".join(f"<tr><td>{name}</td><td>{count}</td></tr>" for name,count in report["event_counts"].items())
    findings="".join(f"<li>{item}</li>" for item in report["findings"]+report["limitations"])
    return ("<!doctype html><meta charset='utf-8'><title>Agent Runtime Audit</title>"
            "<style>body{font:16px system-ui;max-width:850px;margin:40px auto;padding:0 18px}table{border-collapse:collapse}td{padding:7px 14px;border:1px solid #ccc}.PASS{color:#087}.REVIEW{color:#b50}</style>"
            f"<h1>Agent Runtime Audit</h1><h2 class='{report['assessment']}'>{report['assessment']}</h2>"
            f"<p>{report['event_count']} events analyzed. Raw payloads and credentials excluded.</p><table>{rows}</table><h3>Findings and limits</h3><ul>{findings}</ul>")


def run_foundry(root: Path, output_dir: Path|None=None) -> dict[str, Any]:
    theses=sorted((score(x) for x in generate_theses()),key=lambda x:(-x["score"],x["id"])); finalists=theses[:5]
    courts=[court(x) for x in finalists]; experiments=[]
    for item in finalists[:3]:
        spec={"venture_id":item["id"],"hypothesis":"A target buyer will request a follow-up after seeing an honest local audit demo.",
          "baseline":"zero external demand signals","metric":"qualified evaluator requests follow-up","threshold":1,
          "acceptance":"at least one independently supplied qualified follow-up","rejection":"no qualified follow-up after a preregistered outreach sample",
          "cheapest_truth":"private non-deceptive demo and evaluator packet","frozen_at":datetime.now(timezone.utc).isoformat(timespec="seconds")}
        spec["specification_hash"]=_hash(spec); experiments.append(spec)
    selected=finalists[0]; ledger=economic_ledger([])
    dashboard={"mission_target_kwd":MISSION_I_TARGET_KWD,"verified_economic_progress_kwd":0,"verified_cash_kwd":0,
      "revenue_kwd":0,"gross_profit_kwd":0,"net_profit_kwd":0,"costs_kwd":0,"capital_deployed_kwd":0,
      "active_ventures":1,"experiments_running":0,"ventures_killed":0,"best_performing_venture":None,
      "highest_risk_venture":selected["id"],"next_economic_hypothesis":experiments[0]["hypothesis"],
      "current_blockers":["no real external demand signal","no authorization for financial execution"],"mode":"SIMULATION_RECOMMENDATION"}
    venture={"venture_id":selected["id"],"thesis":selected,"customer":selected["customer"],
      "value_proposition":"Produce a local, provenance-preserving reliability and recovery report for AI agent runtimes.",
      "business_model":"unverified SaaS or software-enabled service hypothesis","pricing_hypothesis":"unverified",
      "metrics":["qualified follow-up","time to first audit","findings accepted"],"experiments":[experiments[0]],
      "costs":[],"risks":["crowded observability market","sensitive logs","unproven willingness to pay"],
      "decisions":[courts[0]],"current_state":"EXPERIMENTING","kill_criteria":"no qualified signal after frozen outreach sample",
      "scale_criteria":"repeat paid use with positive unit economics"}
    result={"gate":"E1","e0_verified_by_host":False,"portfolio":theses,"finalists":finalists,"courts":courts,
      "experiments":experiments,"selected_venture":venture,"ledger":ledger,"dashboard":dashboard,
      "external_evidence":[],"status":"WAITING_FOR_REAL_DEMAND_SIGNAL"}
    out=output_dir or root/".omega"/"avf"; out.mkdir(parents=True,exist_ok=True)
    for name,value in (("portfolio.json",theses),("venture_court.json",courts),("experiments.json",experiments),
                       ("selected_venture.json",venture),("economic_ledger.json",ledger),("dashboard.json",dashboard)):
        (out/name).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding="utf-8")
    return result


def advance_e2(root: Path, output_dir: Path|None=None) -> dict[str, Any]:
    """Productize E1 and freeze E2 without performing unauthorized external actions."""
    out=output_dir or root/".omega"/"avf"; out.mkdir(parents=True,exist_ok=True)
    positioning=[
      {"id":"local-recovery-audit","buyer":"AI platform engineering lead","user":"SRE or agent developer","prevented_event":"silent worker death or unsafe recovery","measurable_outcome":"produce a lifecycle-gap report in under five minutes without uploading raw logs","wtp_hypothesis":"team may pay for CI/policy integration; unverified"},
      {"id":"agent-release-evidence","buyer":"engineering manager","user":"QA/release engineer","prevented_event":"unverified agent changes reaching release","measurable_outcome":"attach reproducible host-verification evidence to an agent run","wtp_hypothesis":"may fit existing release-tool budget; unverified"},
      {"id":"privacy-safe-incident-pack","buyer":"security or compliance lead","user":"incident responder","prevented_event":"secret-bearing raw logs shared during review","measurable_outcome":"export findings and counts without reasons/payloads","wtp_hypothesis":"service-led audit may be easier to validate; unverified"}]
    segments=[
      {"id":"coding-agent-platform-teams","pain":.9,"urgency":.85,"reachability":.7,"wtp":.35,"fit":.95},
      {"id":"windows-heavy-local-agent-teams","pain":.88,"urgency":.8,"reachability":.72,"wtp":.28,"fit":.98},
      {"id":"devops-sre-agent-owners","pain":.82,"urgency":.82,"reachability":.65,"wtp":.45,"fit":.88},
      {"id":"enterprise-internal-agent-teams","pain":.78,"urgency":.75,"reachability":.3,"wtp":.65,"fit":.7}]
    for x in segments: x["score"]=round(.25*x["pain"]+.22*x["urgency"]+.18*x["reachability"]+.15*x["wtp"]+.2*x["fit"],4)
    segments.sort(key=lambda x:(-x["score"],x["id"])); selected_segment=segments[0]
    competition=[
      {"category":"LLM tracing/evals","products":["LangSmith","Arize Phoenix","Langfuse"],"strength":"model/tool traces, evaluations, datasets, monitoring","source":"official product documentation","gap_hypothesis":"not focused on OS process ownership, terminal independence, PID reuse, scheduled-worker recovery, and host-verification evidence"},
      {"category":"durable workflows","products":["Temporal"],"strength":"crash recovery and durable execution","source":"official Temporal documentation","gap_hypothesis":"general workflow runtime rather than a low-install audit of existing local agent processes"},
      {"category":"generic process monitoring","products":["OS tools and APM"],"strength":"process and infrastructure telemetry","source":"category analysis","gap_hypothesis":"lacks agent milestone, backend-change, host-test, and evidence-boundary semantics"}]
    trust={"data_inspected":["event name","timestamp","non-sensitive lifecycle counters"],"data_not_collected":["raw reason","payload","prompt","credentials","private reveal"],
      "processing":"local only; no network path in the MVP","permissions":["read one user-selected JSONL file","write user-selected reports"],
      "limitations":["does not prove process ownership","does not replace tracing or durable workflow engines","may flag incomplete custom event schemas"],
      "reproducibility":"run venture-audit-log twice against the same immutable input and compare JSON","certifications":[]}
    channels=[
      {"id":"targeted-design-partner-intro","buyer_quality":.9,"cost":"low","rules":"consent-based one-to-one contact","automation_feasibility":"draft only","spam_risk":"low","requires":"authorized contact/account","signal_quality":"high"},
      {"id":"open-source-repository","buyer_quality":.6,"cost":"low","rules":"honest README and issue templates","automation_feasibility":"prepare locally","spam_risk":"low","requires":"publishing authorization and repository","signal_quality":"medium"},
      {"id":"developer-community-post","buyer_quality":.55,"cost":"low","rules":"community self-promotion rules","automation_feasibility":"draft only","spam_risk":"medium","requires":"authorized account and human review","signal_quality":"medium"},
      {"id":"vendor-partnership","buyer_quality":.85,"cost":"medium","rules":"direct legitimate outreach","automation_feasibility":"research/draft only","spam_risk":"low","requires":"business identity and authorization","signal_quality":"high"}]
    experiment_path=out/"e2_demand_experiments.json"; experiments=[]
    if experiment_path.exists():
        try: experiments=json.loads(experiment_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError: experiments=[]
    if not experiments:
        for identifier,metric,threshold in (("qualified-response","qualified buyer replies",1),("demo-request","independent demo requests",1),("install-attempt","real external installation attempts",1),("pricing-response","buyer supplies acceptable price range",1)):
            spec={"id":identifier,"hypothesis":f"The selected segment will produce at least {threshold} {metric} for the privacy-safe local audit offer.",
              "segment":selected_segment["id"],"offer":"five-minute local agent lifecycle audit; no raw-log upload","channel":"targeted-design-partner-intro",
              "success_metric":metric,"threshold":threshold,"rejection_metric":"zero qualified signals after 10 consent-based qualified exposures",
              "minimum_evidence":"timestamped externally supplied response attributable to a qualified role","frozen_at":datetime.now(timezone.utc).isoformat(timespec="seconds")}
            spec["specification_hash"]=_hash(spec); experiments.append(spec)
    queue=[{"action":"send consent-based design-partner invitation","purpose":"run frozen qualified-response experiment","venture":"agent-runtime-audit","expected_value":"first external demand evidence","required_credential_account_authorization":"authorized business identity and approved contact channel","reversibility":"message cannot be unsent but no financial commitment","risk":"reputational/spam","exact_next_step":"human authorizes identity, recipients, and channel rules"},
           {"action":"publish audit MVP repository or package","purpose":"enable real installation attempt","venture":"agent-runtime-audit","expected_value":"installation and issue signals","required_credential_account_authorization":"publishing account and explicit release authorization","reversibility":"release can be deprecated but remains historically visible","risk":"security/support/reputation","exact_next_step":"security review and authorized publisher executes release"}]
    fund={"name":"OMEGA_CAPABILITY_INVESTMENT_FUND","balance_kwd":0,"verified_available_kwd":0,"mode":"RECOMMENDATION_ONLY",
      "allocation_buckets":["operational reserve","venture reinvestment","new venture experiments","OMEGA capability R&D","safety reserve"],
      "allocation_policy":"dynamic from runway, evidence, expected economic ROI, capability ROI, reversibility, and concentration; no permanent percentages","self_authority_increase":False}
    frontier=[
      {"id":"independent-model-evaluation","problem":"internal evaluator correlation","capability_gain":.78,"economic_benefit":"higher confidence in audit findings","required_capital_kwd":100,"required_compute":"external model calls","required_data":"frozen cases","required_external_services":["independent model provider"],"required_expertise":"evaluation design","dependencies":["funded authorization"],"unlocks":["multi-model RED review"],"confidence":.65,"evidence":["Capability RED limitation"]},
      {"id":"cross-runtime-fixture-library","problem":"audit currently validates OMEGA event schema","capability_gain":.9,"economic_benefit":"broader product fit","required_capital_kwd":0,"required_compute":"local","required_data":"lawfully supplied anonymized runtime fixtures","required_external_services":[],"required_expertise":"agent runtime formats","dependencies":["external fixture contributors"],"unlocks":["vendor-neutral audit"],"confidence":.8,"evidence":["MVP limitation"]},
      {"id":"signed-evidence-bundles","problem":"reports lack issuer identity proof","capability_gain":.72,"economic_benefit":"enterprise trust","required_capital_kwd":250,"required_compute":"minimal","required_data":"key custody policy","required_external_services":["optional managed key service"],"required_expertise":"applied cryptography","dependencies":["security review"],"unlocks":["verifiable audit exchange"],"confidence":.6,"evidence":["trust package boundary"]}]
    for item in frontier:
        denominator=max(1,item["required_capital_kwd"]); item["capability_roi_per_kwd"]=round(item["capability_gain"]/denominator,6)
        item["economic_roi"]="UNVERIFIED"
    investment_cases=[]
    for item in frontier:
        if item["required_capital_kwd"]<=fund["verified_available_kwd"]:
            investment_cases.append({"capability":item["id"],"cost":item["required_capital_kwd"],"expected_gain":item["capability_gain"],"alternatives":["defer","seek no-cost fixture contribution"],"evidence":item["evidence"],"downside":"engineering opportunity cost","reversibility":"high","prosecutor_objection":"demand is not yet verified","judge_recommendation":"PREPARE_ONLY_NO_SPEND"})
    result={"gate":"E2_PREPARED_NOT_ACHIEVED","selected_segment":selected_segment,"segments":segments,"positioning":positioning,
      "competitive_gap":competition,"differentiated_wedge":"privacy-bounded local lifecycle/recovery/host-verification audit; complementary to tracing and durable execution",
      "trust_package":trust,"demand_experiments":experiments,"channels":channels,"external_action_queue":queue,
      "capability_investment_fund":fund,"capability_frontier":frontier,"capability_investment_cases":investment_cases,
      "verified_external_demand_signals":0,"verified_economic_value_kwd":0}
    for name,value in result.items():
        if isinstance(value,(dict,list)): (out/f"e2_{name}.json").write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding="utf-8")
    return result


def broker_action(identity: dict[str, Any], action: dict[str, Any]) -> dict[str, Any]:
    allowed=(identity.get("authorized") is True and identity.get("revoked") is False and
             action.get("channel") in identity.get("channels",[]) and action.get("action") in identity.get("permissions",[]))
    return {"action_id":action["id"],"status":"AUTHORIZED_FOR_ADAPTER" if allowed else "QUEUED",
            "executed":False,"reason":"adapter execution is not connected" if allowed else "explicit identity/channel/action authorization unavailable",
            "audit":{"identity_id":identity.get("identity_id"),"channel":action.get("channel"),"permission_checked":True,
                     "credential_presence_treated_as_permission":False}}


def gmail_broker_grant(authorization: dict[str, Any], target: dict[str, Any]) -> dict[str, Any]:
    """Issue a narrow Gmail grant; credentials alone can never make this pass."""
    scope=authorization.get("scope",{}); channel=authorization.get("channel",{}); kill=authorization.get("kill_switch",{})
    qualified=qualify_target(target)
    allowed=(authorization.get("status")=="E2_EXECUTABLE" and
             authorization.get("identity",{}).get("owner_authorized") is True and
             channel.get("id")=="gmail" and channel.get("authorized") is True and channel.get("policy_verified") is True and
             qualified["qualified"] and kill.get("revoked") is False and
             scope.get("contacts_used",0)<scope.get("maximum_qualified_contacts",0) and
             scope.get("financial_authority_kwd")==0 and scope.get("message_variants")==1 and
             scope.get("automated_follow_up") is False)
    return {"authorized":allowed,"issued_by":"OMEGA_EXTERNAL_ACTION_BROKER","experiment_id":authorization.get("experiment_id"),
      "channel":"gmail","account":channel.get("account"),"message_sha256":authorization.get("frozen_message",{}).get("sha256"),
      "contacts_used":scope.get("contacts_used",0),"contacts_maximum":scope.get("maximum_qualified_contacts",0),
      "revoked":kill.get("revoked",True),"target_id":target.get("target_id"),"qualification":qualified,
      "reason":"bounded E2-01 action authorized" if allowed else "authorization, qualification, quota, or kill-switch check failed"}


def founder_os(root: Path, output_dir: Path|None=None) -> dict[str, Any]:
    out=output_dir or root/".omega"/"avf"; out.mkdir(parents=True,exist_ok=True); e2=advance_e2(root,out)
    unknowns=[
      ("problem-exists",.65,.9,.18,"10 qualified exposures"),("pain-severe",.55,.95,.2,"qualified problem interview"),
      ("buyer-authority",.3,.92,.15,"buyer-role reply"),("will-install",.35,.82,.25,"external installation attempt"),
      ("will-trust",.45,.88,.2,"trust-package review"),("will-pay",.2,1.0,.2,"explicit WTP response"),
      ("reachable",.45,.95,.1,"authorized targeted contact"),("retain",.2,.75,.55,"repeated usage cohort"),
      ("profitable",.2,.8,.7,"verified unit-economics cohort"),("safe-operation",.72,.9,.2,"security and privacy regression")]
    ledger=[]
    for name,prob,importance,cost,experiment in unknowns:
        evsi=round(importance*(1-abs(prob-.5)*2),4); ledger.append({"id":name,"probability":prob,"economic_importance":importance,
          "evidence":[],"confidence":"INTERNAL_ESTIMATE","cheapest_falsification_experiment":experiment,"experiment_cost_index":cost,
          "evsi":evsi,"evsi_per_cost":round(evsi/max(cost,.01),4),"last_update":"2026-08-27"})
    ledger.sort(key=lambda x:(-x["evsi_per_cost"],x["id"]))
    graph={"nodes":[{"id":"revenue","type":"outcome"},{"id":"customers-pay","type":"assumption"},
      {"id":"pain-severe","type":"assumption"},{"id":"trust","type":"assumption"},{"id":"value","type":"assumption"},
      {"id":"reachability","type":"assumption"},{"id":"budget-authority","type":"assumption"}],
      "edges":[["revenue","customers-pay"],["customers-pay","pain-severe"],["customers-pay","trust"],
               ["customers-pay","value"],["customers-pay","reachability"],["customers-pay","budget-authority"]],
      "fatal_upstream_assumption":"reachability","next_test":"authorized market contact"}
    roles={"user":"agent developer or SRE","champion":"AI platform engineering lead","buyer":"engineering director or platform owner",
      "budget_owner":"VP Engineering/CTO or delegated platform budget owner","security_reviewer":"security/privacy engineering",
      "technical_approver":"platform/SRE lead","economic_decision_maker":"budget owner"}
    identity={"identity_id":"UNCONFIGURED","credential":None,"channels":[],"permissions":[],"authorized":False,"revoked":False,
      "rate_limits":{},"financial_limits_kwd":0,"content_constraints":["no spam","no deception","approved identity only"]}
    action={"id":"e2-qualified-contact-001","action":"SEND_APPROVED_BUSINESS_MESSAGE","channel":"AUTHORIZED_ONE_TO_ONE",
      "purpose":"test frozen qualified-response hypothesis","venture":"agent-runtime-audit"}
    broker=broker_action(identity,action)
    decision_case={"proposal":"authorize one bounded consent-based E2 contact experiment","evidence":"E0/E1 technical verification and frozen E2 criteria; no demand evidence yet",
      "prosecution":["reputational risk","recipient qualification may be weak","one response does not prove a market"],
      "defense":["market contact is the highest-value unresolved upstream assumption","experiment is bounded and reversible except message delivery"],
      "recommendation":"APPROVE_BOUNDED_EXPERIMENT_ONLY","confidence":.72,"expected_upside":"first legitimate demand or rejection evidence",
      "downside":"time and reputational cost","reversibility":"stop after any message; no funds or contracts",
      "alternatives":["authorized private design-partner introduction","authorized public repository release"],
      "minimum_authorization":{"identity":"real business/person identity approved by its owner","channel":"one approved account/channel",
        "recipients":"up to 10 qualified opt-in, warm, or rules-compliant recipients","content":"one reviewed offer and follow-up policy",
        "rate_limit":"maximum 10 initial contacts; no automated follow-up without reply","financial_authority_kwd":0,"revocation":"immediate kill switch"}}
    board={"founder_thesis":"local lifecycle evidence may reduce agent reliability risk","product_evidence":"92+ host tests and real OMEGA audit",
      "economic_evidence":"none","capability_evidence":"host verification and incident memory","red_case":decision_case["prosecution"],
      "risk":["unproven WTP","incumbent response","privacy perception"],"alternatives":decision_case["alternatives"],
      "recommendation":"RUN_BOUNDED_MARKET_CONTACT_AFTER_AUTHORIZATION","confidence":.7,
      "minority_objection":"open-source observability incumbents may erase the wedge","conditions":["preserve frozen criteria","record rejections","no bulk outreach"],
      "next_evidence_required":"qualified external reply, demo request, installation, or explicit rejection"}
    frontiers={"AVAILABLE_NOW":["local audit","privacy-safe report","frozen experiments"],
      "ECONOMICALLY_JUSTIFIABLE_NEXT":["cross-runtime fixture adapter after lawful fixture access"],
      "RESOURCE_CONSTRAINED_FUTURE":["independent model evaluation","signed evidence bundles"]}
    result={"optimization":"VERIFIED_LONG_TERM_VALUE_CREATION","uncertainty_ledger":ledger,"assumption_graph":graph,
      "stakeholder_roles":roles,"outcome_metrics":["incident diagnosis time","agent downtime","orphaned processes","false-success states","recovery evidence"],
      "time_to_value":{"understand_target_minutes":2,"install_target_minutes":3,"first_scan_target_minutes":1,"first_finding_target_minutes":5,"measured_external":False},
      "trust":e2["trust_package"],"demand_strength":DEMAND_STRENGTH,"verified_demand_events":[],"loss_memory":[],
      "external_identity":identity,"external_action_broker":broker,"decision_case":decision_case,"board_review":board,
      "feature_deletion_candidates":[],"reputation_ledger":[],"unit_economics":{"status":"INSUFFICIENT_EVIDENCE"},
      "treasury":{"connected":False,"verified_cash_kwd":0,"tax_reserve_kwd":0,"owner_withdrawable_kwd":0},
      "survival":{"fixed_cost_kwd":0,"variable_cost_kwd":0,"capital_at_risk_kwd":0,"maximum_authorized_loss_kwd":0},
      "capability_frontiers":frontiers,"learning_velocity":{"important_hypotheses_tested":0,"external_measurement_started":False},
      "calibration":{"comparable_outcomes":0,"status":"INSUFFICIENT_SAMPLE"},"mission_verified_value_kwd":0,
      "next_decision":"obtain minimum bounded external authorization; do not build additional internal features first"}
    for name,value in result.items():
        if isinstance(value,(dict,list)): (out/f"founder_{name}.json").write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding="utf-8")
    return result


def qualify_target(target: dict[str, Any]) -> dict[str, Any]:
    checks={"operates_coding_agents":target.get("operates_coding_agents") is True,
            "runtime_responsibility":target.get("runtime_responsibility") is True,
            "plausible_pain":bool(target.get("pain_evidence")),
            "authority_or_influence":target.get("authority") in {"USER","CHAMPION","BUYER","BUDGET_OWNER","TECHNICAL_APPROVER"},
            "channel_permits_contact":target.get("channel_permits_contact") is True}
    return {"target_id":target.get("target_id"),"qualified":all(checks.values()),"checks":checks,
            "rationale":[name for name,value in checks.items() if value],"missing":[name for name,value in checks.items() if not value]}


def classify_response(response: dict[str, Any]) -> dict[str, Any]:
    signal=str(response.get("signal","ENGAGED"))
    if signal not in CONTACT_SIGNAL_STRENGTH: raise ValueError("unsupported market signal")
    return {"signal":signal,"strength":CONTACT_SIGNAL_STRENGTH[signal],"e2_satisfied":signal in {"QUALIFIED_REPLY","DEMO_REQUEST","INSTALL_ATTEMPT","WTP_SIGNAL","PURCHASE_COMMITMENT","VERIFIED_PAYMENT","REPEAT_PAYMENT"},
      "learning":{"pain_confirmation":response.get("pain_confirmation"),"pain_rejection":response.get("pain_rejection"),
      "current_workaround":response.get("current_workaround"),"urgency":response.get("urgency"),"objection":response.get("objection"),
      "security_concern":response.get("security_concern"),"integration_concern":response.get("integration_concern"),
      "pricing_response":response.get("pricing_response"),"authority_level":response.get("authority_level"),
      "next_requested_action":response.get("next_requested_action")},"provenance":response.get("provenance"),"external":True}


def market_barrier(root: Path, output_dir: Path|None=None) -> dict[str, Any]:
    out=output_dir or root/".omega"/"avf"; out.mkdir(parents=True,exist_ok=True); founder=founder_os(root,out)
    policy={"status":"READY_FOR_AUTHORIZATION","identity":{"required":"genuine owner-approved business/person identity","configured":False},
      "channel":{"required":"one owner-approved rules-compliant external channel","configured":False},
      "scope":{"venture":"agent-runtime-audit","experiment":"qualified-response","message_variants":1,"maximum_recipients":10,"automated_follow_up":False},
      "limits":{"financial_authority_kwd":0,"per_experiment_recipients":10,"parallel_batches":1},
      "revocation":{"kill_switch":True,"effect":"block all new actions immediately"},"audit":"immutable append-only action events required"}
    frozen_files=sorted((out).glob("e2_demand_experiments.json")); frozen=[]
    if frozen_files:
        try: frozen=json.loads(frozen_files[0].read_text(encoding="utf-8"))
        except json.JSONDecodeError: frozen=[]
    saved_authorization=None; authorization_path=root/".omega"/"avf"/"market_authorization.json"
    if authorization_path.exists():
        try: saved_authorization=json.loads(authorization_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError: saved_authorization=None
    saved_state=saved_authorization.get("status") if saved_authorization else None
    channel_ready=bool(saved_authorization and saved_authorization.get("channel",{}).get("authorized") is True and
                       saved_authorization.get("channel",{}).get("policy_verified") is True)
    if saved_state=="E2_EXECUTABLE" and channel_ready:
        controller_state="E2_EXECUTABLE"
    elif saved_state=="CHANNEL_READY" and channel_ready:
        controller_state="CHANNEL_READY"
    elif saved_authorization and saved_authorization.get("identity",{}).get("owner_authorized"):
        controller_state="AUTHORIZED_PENDING_CHANNEL"
    else:
        controller_state="READY_FOR_AUTHORIZATION"
    controller={"state":controller_state,"pipeline":["select qualified targets","verify channel policy","select frozen experiment","send permitted communication","record delivery","ingest response","classify signal","update uncertainty ledger","update assumption graph","choose next experiment"],
      "selected_experiment":frozen[0] if frozen else None,"targets":[],"actions_executed":saved_authorization.get("audit",{}).get("actions_executed",0) if saved_authorization else 0,
      "reason":"channel verified; awaiting genuinely qualified targets" if controller_state=="E2_EXECUTABLE" else "authorized identity and channel unavailable"}
    treasury={"name":"OMEGA_AUTONOMOUS_TREASURY","mode":"DISABLED","rails":["BANK","PAYMENT_PROCESSOR","STABLECOIN_BLOCKCHAIN","OTHER_LAWFUL"],
      "architecture":["OMEGA_INTELLIGENCE","TREASURY_POLICY","TRANSACTION_PROPOSAL","RISK_POLICY_CHECK","ISOLATED_SIGNER","NETWORK","RECONCILIATION"],
      "private_key_policy":"never prompts, reasoning context, logs, repository, evidence bundles, or environment dumps",
      "controls":["isolated signer","least privilege","address allowlist","transaction/daily/monthly limits","network/token allowlists","simulation before signing","intent verification","kill switch","immutable audit","reconciliation"],
      "stablecoin_risks":["issuer","depeg","smart contract","chain","bridge","custody","liquidity","counterparty","regulatory","fees"],
      "speculation":{"enabled":False,"leverage":False,"yield_chasing":False},"connected":False,"transactions":[]}
    authorization_case={"blocker":"AUTHORIZED_EXTERNAL_IDENTITY_AND_CHANNEL_REQUIRED","identity_requirement":policy["identity"]["required"],
      "channel_requirement":policy["channel"]["required"],"scope":policy["scope"],"limits":policy["limits"],
      "revocation_mechanism":policy["revocation"],"experiment_unlocked":controller["selected_experiment"],
      "automatic_after_authorization":["validate up to 10 supplied/authorized targets","reject unqualified targets","verify channel permission","send one frozen variant through a connected adapter","record delivery without calling it demand","ingest and classify replies","preserve negative evidence","recompute reachability belief","stop/modify/continue from frozen criteria"],
      "unrelated_decisions_required":[]}
    result={"policy":policy,"saved_authorization":saved_authorization,"market_contact_controller":controller,"signal_hierarchy":CONTACT_SIGNAL_STRENGTH,
      "response_schema":{"required":["signal","provenance"],"negative_evidence_preserved":True},"treasury":treasury,
      "authorization_case":authorization_case,"verified_external_signals":[],"mission_verified_value_kwd":0,
      "highest_evsi":founder["uncertainty_ledger"][0]}
    for name,value in result.items():
        if isinstance(value,(dict,list)): (out/f"market_{name}.json").write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding="utf-8")
    return result
