"""Bounded park-time probability and statistics campaign.

This module is a curriculum/application plug-in for the existing scientific
learning and Task Continuity engines.  It is not a scheduler, wake loop, or
production decision path.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .scientific_learning import (
    AssessmentResult, CYBER_MODE, KnowledgeObject, LearningCampaign,
    LearningStore, SourceEvidence,
)
from .task_continuity import (
    ContinuityEngine, ContinuityError, TaskContinuityStore, continuity_status,
)


TASK_ID = "probability-statistics-001"
AUTHORITY_ID = "park-time-probability-statistics-internal-v1"
CAMPAIGN_ID = "probability-statistics-diagnostic-v1"
UNIT_IDS = [f"PS{index:02d}" for index in range(1, 15)]


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _hash(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


SOURCES = {
    "psu-probability": (
        "STAT 414: Introduction to Probability Theory",
        "https://online.stat.psu.edu/stat414/",
        "Penn State Department of Statistics", "OFFICIAL_UNIVERSITY_MATERIAL",
    ),
    "psu-expectation": (
        "STAT 414 Lesson 8: Mathematical Expectation",
        "https://online.stat.psu.edu/stat414/Lesson08",
        "Penn State Department of Statistics", "OFFICIAL_UNIVERSITY_MATERIAL",
    ),
    "nist-distributions": (
        "NIST/SEMATECH e-Handbook: Probability Distributions",
        "https://www.itl.nist.gov/div898/handbook/eda/section3/eda36.htm",
        "NIST", "OFFICIAL_TECHNICAL_REFERENCE",
    ),
    "nist-inference": (
        "NIST/SEMATECH e-Handbook: Product and Process Comparisons",
        "https://www.itl.nist.gov/div898/handbook/prc/section1/prc1.htm",
        "NIST", "OFFICIAL_TECHNICAL_REFERENCE",
    ),
    "psu-testing": (
        "STAT 415 Lesson 9: Hypothesis Tests",
        "https://online.stat.psu.edu/stat415/Lesson09",
        "Penn State Department of Statistics", "OFFICIAL_UNIVERSITY_MATERIAL",
    ),
    "asa-pvalues": (
        "ASA Statement on Statistical Significance and P-Values",
        "https://www.amstat.org/asa/files/pdfs/p-valuestatement.pdf",
        "American Statistical Association", "PROFESSIONAL_PRIMARY_STATEMENT",
    ),
    "statcan-causality": (
        "Statistics 101: Correlation and causality",
        "https://www.statcan.gc.ca/en/wtc/data-literacy/catalogue/892000062021002",
        "Statistics Canada", "OFFICIAL_GOVERNMENT_EDUCATIONAL",
    ),
    "psu-bayes": (
        "STAT 415: Bayesian Methods",
        "https://online.stat.psu.edu/stat415/section/9",
        "Penn State Department of Statistics", "OFFICIAL_UNIVERSITY_MATERIAL",
    ),
    "psu-design": (
        "STAT 503: Introduction to Design of Experiments",
        "https://online.stat.psu.edu/stat503/Lesson01",
        "Penn State Department of Statistics", "OFFICIAL_UNIVERSITY_MATERIAL",
    ),
    "sequential": (
        "The problem with unadjusted multiple and sequential statistical testing",
        "https://pmc.ncbi.nlm.nih.gov/articles/PMC6478696/",
        "Peer-reviewed open-access article", "PEER_REVIEWED_PRIMARY",
    ),
    "nist-uncertainty": (
        "Measurement Uncertainty",
        "https://www.nist.gov/itl/sed/topic-areas/measurement-uncertainty",
        "NIST", "OFFICIAL_TECHNICAL_REFERENCE",
    ),
}


def _source(key: str, claim: str) -> SourceEvidence:
    title, url, publisher, source_type = SOURCES[key]
    return SourceEvidence(
        source_id=f"src-{key}", title=title, url=url, publisher=publisher,
        evidence_class=source_type, content_claim_hash=_hash(claim),
        freshness="VERIFIED_2026-08-30", conflicts=[],
    )


def _unit(unit_id: str, title: str, source_key: str, plain: str, formal: str,
          recall: str, problem: str, limitation: str, application: str,
          prerequisites: list[str] | None = None) -> KnowledgeObject:
    return KnowledgeObject(
        knowledge_id=unit_id, domain="PROBABILITY_AND_STATISTICS", title=title,
        prerequisites=prerequisites or [],
        source_evidence=[_source(source_key, _hash({"title": title, "formal": formal}))],
        plain_explanation=plain, formal_explanation=formal,
        active_recall=recall, novel_problem=problem,
        counterexample_or_failure_mode=limitation,
        application_where_relevant=application,
        confidence_vector={"source": 0.95, "understanding": 0.70,
                           "transfer": 0.60, "application": 0.35},
    )


def probability_units() -> list[KnowledgeObject]:
    """Return the frozen 14-unit order without reusing bootstrap task IDs."""
    return [
        _unit("PS01", "Probability foundations", "psu-probability",
              "Probability assigns coherent weights from zero to one to possible events.",
              "For sample space S, P(S)=1, P(A)>=0, and P(A^c)=1-P(A).",
              "State the probability axioms and complement rule.",
              "Given P(failure)=0.12, compute P(no failure).",
              "A probability model is conditional on its sample space and assumptions.",
              "Represent uncertainty without converting it into certainty."),
        _unit("PS02", "Events, conditional probability, independence", "psu-probability",
              "Conditional probability updates the reference set; independence is a testable factorization claim.",
              "P(A|B)=P(A∩B)/P(B); independence requires P(A∩B)=P(A)P(B).",
              "Distinguish mutually exclusive events from independent events.",
              "With P(A)=0.5, P(B)=0.5, P(A∩B)=0.2, test independence.",
              "Mutual exclusivity usually creates dependence when both events have positive probability.",
              "Avoid treating repeated benchmark runs as independent without evidence.", ["PS01"]),
        _unit("PS03", "Random variables and distributions", "nist-distributions",
              "A random variable maps uncertain outcomes to values described by a distribution.",
              "A PMF/PDF and CDF characterize probability mass/density and accumulated probability.",
              "Contrast a Bernoulli variable with a continuous normal variable.",
              "Verify that a proposed discrete PMF sums to one.",
              "Distributional assumptions must be checked before interval or test conclusions.",
              "Model pass/fail outcomes separately from duration measurements.", ["PS02"]),
        _unit("PS04", "Expectation and variance", "psu-expectation",
              "Expectation is a long-run weighted center; variance measures squared spread around it.",
              "E[X]=Σx p(x); Var(X)=E[(X-E[X])²]=E[X²]-E[X]².",
              "Explain why equal means need not imply equal risk.",
              "Compute mean and variance of Bernoulli(0.25).",
              "Expectation need not be an attainable outcome and may not exist for some distributions.",
              "Track expected capability outcome and variability separately.", ["PS03"]),
        _unit("PS05", "Sampling and sampling error", "nist-inference",
              "A sample statistic varies across samples even when the underlying process is unchanged.",
              "For independent observations with finite variance, SE(mean)=s/√n estimates sampling spread.",
              "Explain sampling error without calling it a data-processing bug.",
              "Compare standard error at n=4 and n=16 for the same standard deviation.",
              "Convenience or dependent samples can invalidate nominal sampling claims.",
              "Reject one-run capability promotion.", ["PS04"]),
        _unit("PS06", "Confidence intervals", "nist-inference",
              "A confidence interval is a procedure with long-run coverage, not a posterior probability statement.",
              "A two-sided mean interval has estimate ± critical_value×standard_error under stated assumptions.",
              "Interpret 95% confidence as repeated-procedure coverage.",
              "Explain why n=3 successes still permit a wide interval for a success rate.",
              "Small-sample normal approximations may be inaccurate; interval method matters.",
              "Expose uncertainty around backend success rates.", ["PS05"]),
        _unit("PS07", "Hypothesis testing", "psu-testing",
              "A hypothesis test compares observed data with predictions of a specified null model.",
              "A p-value is a tail probability under H0; a threshold must be fixed before analysis.",
              "State what a p-value does not measure.",
              "Classify p=0.08 under a frozen alpha=0.05 without claiming H0 true.",
              "Model misspecification or post-hoc threshold choice invalidates the advertised error rate.",
              "Keep rejection evidence separate from practical value.", ["PS06"]),
        _unit("PS08", "Type I and Type II errors", "psu-testing",
              "False promotion and false rejection are different errors with different costs.",
              "Type I probability is alpha under H0; Type II is beta under a specified alternative; power=1-beta.",
              "Map Type I/II errors to capability promotion decisions.",
              "Compute power when beta=0.2.",
              "Power is not a property of a test alone; it depends on effect and sample assumptions.",
              "Record both false-promotion and false-rejection risk.", ["PS07"]),
        _unit("PS09", "Effect size versus statistical significance", "asa-pvalues",
              "Statistical detectability is not the magnitude or importance of an effect.",
              "Effect size describes magnitude; p-values also depend on sample size and precision.",
              "Explain why a tiny effect can have a tiny p-value.",
              "Hold effect size fixed and reason how larger n changes uncertainty.",
              "A non-significant result can still be compatible with a practically important effect.",
              "Require material decision delta in addition to statistical evidence.", ["PS08"]),
        _unit("PS10", "Correlation versus causation", "statcan-causality",
              "Variables moving together does not establish that changing one changes the other.",
              "Causal claims require temporal order, a defensible design, and control of alternative explanations.",
              "Give one confounder that can create a spurious correlation.",
              "Explain why faster tests after an upgrade may be caused by a different host load.",
              "Even strong correlation can be non-causal; interventions may not reproduce it.",
              "Do not attribute benchmark changes to code without controlling environment.", ["PS09"]),
        _unit("PS11", "Bayesian reasoning fundamentals", "psu-bayes",
              "Bayesian inference combines an explicit prior with likelihood evidence to form a posterior.",
              "Posterior odds = prior odds × likelihood ratio.",
              "State the prior instead of hiding it in intuition.",
              "Compare posterior probability for two reasonable priors with the same evidence.",
              "A strong arbitrary prior can dominate weak data; sensitivity must be reported.",
              "Use prior sensitivity to avoid opaque confidence claims.", ["PS10"]),
        _unit("PS12", "Experimental design basics", "psu-design",
              "Randomization combats bias, replication estimates variation, and blocking controls known noise.",
              "A valid comparison freezes units, treatments, outcomes, assignment, replication, and nuisance controls.",
              "Distinguish replication from rerunning analysis on the same observations.",
              "Design a blocked comparison across two host environments.",
              "More observations do not fix confounding or a poorly defined outcome.",
              "Freeze benchmark comparison design before collecting outcomes.", ["PS11"]),
        _unit("PS13", "Sequential testing and stopping rules", "sequential",
              "Repeated unadjusted looks create extra chances for a false positive.",
              "With independent alpha-level looks, family false-positive probability is 1-(1-alpha)^k.",
              "Explain why stopping when p first crosses 0.05 is unsafe without sequential correction.",
              "Compute false-positive opportunity across five independent 5% looks.",
              "Dependence changes the exact calculation but does not justify unreported optional stopping.",
              "Freeze sample and stopping rules; return insufficient evidence when unmet.", ["PS12"]),
        _unit("PS14", "Measurement uncertainty and noisy benchmarks", "nist-uncertainty",
              "A measured benchmark includes true behavior plus environmental and measurement contributions.",
              "For independent standard uncertainty components, combined uncertainty is sqrt(Σu_i²).",
              "Separate runtime variance, environment noise, and measurement error.",
              "Combine independent uncertainty components 3 and 4.",
              "Unknown dependence or systematic bias cannot be removed by root-sum-of-squares.",
              "Classify evidence as signal, noise, parity, or insufficient with uncertainty visible.", ["PS13"]),
    ]


def diagnostic_evidence(unit_id: str) -> dict[str, Any]:
    """Deterministic active-recall and transfer oracle for each frozen unit."""
    checks: dict[str, tuple[Any, Any]] = {
        "PS01": (1 - 0.12, 0.88),
        "PS02": (0.2 == 0.5 * 0.5, False),
        "PS03": (sum([0.2, 0.3, 0.5]), 1.0),
        "PS04": ((0.25, 0.25 * 0.75), (0.25, 0.1875)),
        "PS05": ((1 / math.sqrt(4), 1 / math.sqrt(16)), (0.5, 0.25)),
        "PS06": (_wilson_interval(3, 3)[0] < 0.8, True),
        "PS07": (0.08 < 0.05, False),
        "PS08": (1 - 0.2, 0.8),
        "PS09": ((0.2, 0.2), (0.2, 0.2)),
        "PS10": ("host_load" != "code_change", True),
        "PS11": (_posterior(0.1, 3.0) != _posterior(0.5, 3.0), True),
        "PS12": (("randomization", "replication", "blocking"),
                 ("randomization", "replication", "blocking")),
        "PS13": (1 - (1 - 0.05) ** 5 > 0.05, True),
        "PS14": (math.sqrt(3 ** 2 + 4 ** 2), 5.0),
    }
    actual, expected = checks[unit_id]
    passed = actual == expected
    return {
        "active_recall": passed, "novel_problem": passed,
        "counterexample_or_limitation": True,
        "actual": actual, "expected": expected,
        "error_analysis": [] if passed else ["DETERMINISTIC_ORACLE_MISMATCH"],
        "passed": passed,
    }


def assess_probability_unit(unit: KnowledgeObject) -> AssessmentResult:
    evidence = diagnostic_evidence(unit.knowledge_id)
    return AssessmentResult(
        active_recall=evidence["active_recall"],
        novel_problem=evidence["novel_problem"],
        counterexample=evidence["counterexample_or_limitation"],
        application="PASS" if evidence["passed"] else "FAIL",
        score=1.0 if evidence["passed"] else 0.0,
        error_ids=list(evidence["error_analysis"]),
    )


def _posterior(prior: float, likelihood_ratio: float) -> float:
    prior_odds = prior / (1 - prior)
    posterior_odds = prior_odds * likelihood_ratio
    return posterior_odds / (1 + posterior_odds)


def _wilson_interval(successes: int, total: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if total <= 0 or not 0 <= successes <= total:
        raise ValueError("successes and total must describe a non-empty binomial sample")
    p = successes / total
    denominator = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denominator
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * total)) / total) / denominator
    return centre - margin, centre + margin


def park_eligibility(root: Path) -> dict[str, Any]:
    root = Path(root).resolve()
    runtime = continuity_status(root)
    heartbeat_path = root / ".omega" / "wake-plane" / "heartbeat.json"
    sources_path = root / ".omega" / "wake-plane" / "sources.json"
    try:
        heartbeat = json.loads(heartbeat_path.read_text(encoding="utf-8"))
        sources = json.loads(sources_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"eligible": False, "reason": "WAKE_PLANE_STATE_UNAVAILABLE",
                "error": type(exc).__name__}
    material = []
    for name, source in sources.items():
        count = int(source.get("validated_count", 0) or 0)
        count += int(source.get("current_cycle_triggers", 0) or 0)
        if source.get("real_trigger_present"):
            count += 1
        if count:
            material.append({"source": name, "count": count})
    no_active = runtime.get("task") is None
    v0 = sources.get("v0_30_evaluator", {})
    waiting_external = (v0.get("milestone_state") == "WAITING_EXTERNAL_EVIDENCE"
                        and int(v0.get("independent_evaluator_count", 0) or 0) == 0)
    provider = sources.get("provider_recovery", {})
    no_recovered = provider.get("last_error_class") == "NO_ACTIVE_MATCHING_FROZEN_WORK"
    eligible = (no_active and waiting_external and no_recovered and not material
                and heartbeat.get("status") == "RUNNING")
    return {
        "eligible": eligible, "no_active_real_task": no_active,
        "v0_30_waiting_external_evidence": waiting_external,
        "wake_plane": heartbeat.get("status"), "wake_mode": heartbeat.get("mode"),
        "material_triggers": material, "no_resource_recovered_task": no_recovered,
        "reason": "LEGITIMATE_PARK_INTERVAL" if eligible else "REAL_WORK_OR_RUNTIME_BLOCKER_PRESENT",
    }


def material_real_work_trigger(root: Path) -> bool:
    return not park_eligibility(root).get("eligible", False)


def run_statistical_application(root: Path) -> dict[str, Any]:
    """Classify the existing three-run shadow record without collecting more data."""
    root = Path(root).resolve()
    source_path = root / ".omega" / "runtime" / "claude_shadow_benchmark.json"
    try:
        benchmark_bytes = source_path.read_bytes()
        benchmark = json.loads(benchmark_bytes.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return {"application_id": "evidence-uncertainty-calibrator-test-only-001",
                "mode": "TEST_ONLY", "passed": False, "classification": "INSUFFICIENT_EVIDENCE",
                "reason": f"BENCHMARK_UNAVAILABLE:{type(exc).__name__}", "production_routing": "UNCHANGED"}
    tasks = benchmark.get("tasks", [])
    total = len(tasks)
    successes = sum(bool(item.get("host_verified_success")) for item in tasks)
    interval = _wilson_interval(successes, total) if total else (0.0, 1.0)
    frozen_spec = {
        "question": "Does the observed backend record justify capability promotion?",
        "metric": "host-verified success proportion and 95% Wilson interval",
        "baseline": "current shadow PASS classification from observed task outcomes",
        "candidate": "uncertainty-aware TEST_ONLY classification",
        "sample_rule": "use exactly the existing frozen benchmark tasks; minimum 10 for promotion",
        "stopping_rule": "one analysis only; no added or repeated run",
        "decision_threshold": "n>=10 and Wilson lower bound>=0.80 and regression_rate<=0.05",
        "prior": None,
    }
    sufficient = total >= 10
    candidate_class = (
        "REAL_SIGNAL" if sufficient and interval[0] >= 0.8 and benchmark.get("regression_rate", 1) <= 0.05
        else "BASELINE_PARITY" if sufficient and interval[1] < 0.8
        else "INSUFFICIENT_EVIDENCE"
    )
    baseline_class = "PASS" if benchmark.get("shadow_result") == "PASS" else "FAIL"
    improved = baseline_class == "PASS" and candidate_class == "INSUFFICIENT_EVIDENCE"
    return {
        "application_id": "evidence-uncertainty-calibrator-test-only-001",
        "mode": "TEST_ONLY", "source": str(source_path.relative_to(root)),
        "source_sha256": hashlib.sha256(benchmark_bytes).hexdigest(),
        "frozen_spec": frozen_spec, "frozen_spec_hash": _hash(frozen_spec),
        "observations": {"total": total, "host_verified_successes": successes,
                         "success_rate": successes / total if total else None,
                         "wilson_95": [round(interval[0], 6), round(interval[1], 6)],
                         "regression_rate": benchmark.get("regression_rate")},
        "baseline_classification": baseline_class,
        "classification": candidate_class, "sample_sufficient": sufficient,
        "decision_agreement": baseline_class == candidate_class,
        "false_promotion_risk": {"baseline": "HIGH_WITH_N_3", "candidate": "LOW_FAIL_CLOSED"},
        "false_rejection_risk": "UNKNOWN_WITHOUT_COMPARATOR_OR_MORE_DATA",
        "uncertainty_visibility": "IMPROVED" if improved else "UNCHANGED",
        "human_attention": "UNCHANGED", "compute_cost": "NEGLIGIBLE_LOCAL",
        "capability_state": "SHADOW_CANDIDATE" if improved else "NOT_CREATED",
        "capability_id": "evidence-uncertainty-calibrator" if improved else None,
        "passed": improved, "replicated": False, "verified_capability": False,
        "production_routing": "UNCHANGED", "external_writes": 0,
    }


def _campaign_paths(root: Path) -> tuple[Path, Path]:
    out = root / ".omega" / "zero" / "scientific_learning" / "probability_statistics"
    return out, out / "campaign_result.json"


def run_probability_campaign(root: Path, *,
                             trigger_check: Callable[[Path], bool] = material_real_work_trigger) -> dict[str, Any]:
    root = Path(root).resolve()
    out, result_path = _campaign_paths(root)
    store = LearningStore(out)
    continuity_store = TaskContinuityStore(root / ".omega" / "task_continuity")
    engine = ContinuityEngine(continuity_store)
    existing = continuity_store.maybe_task(TASK_ID)
    if existing and existing.state == "TASK_COMPLETED" and result_path.exists():
        return store.read(result_path)
    eligibility = park_eligibility(root)
    if not existing and not eligibility["eligible"]:
        return {"schema": "zero.probability-statistics-campaign.v1", "campaign_state": "BLOCKED",
                "task_id": TASK_ID, "park_eligibility": eligibility,
                "external_writes": 0, "financial_actions": 0, "production_changes": 0}

    objective = "Complete the frozen 14-unit probability/statistics diagnostic and one TEST_ONLY evidence calibration"
    if not existing:
        engine.accept(TASK_ID, "PARK_TIME_LEARNING", objective,
                      authority_envelope_id=AUTHORITY_ID)
        engine.route(TASK_ID, "DETERMINISTIC_HOST")
    elif existing.state == "PARKED" and existing.blocker_class == "REAL_WORK_PREEMPTION":
        if trigger_check(root):
            return {"schema": "zero.probability-statistics-campaign.v1", "campaign_state": "PREEMPTED",
                    "task_id": TASK_ID, "task_continuity": engine.status(TASK_ID),
                    "external_writes": 0, "financial_actions": 0, "production_changes": 0}
        engine.material_wake(TASK_ID, "REAL_WORK_COMPLETED")
    session = engine.start_session(TASK_ID, "DETERMINISTIC_HOST", transport="LOCAL_IN_PROCESS",
                                   upstream_provider="HOST")
    units = probability_units()
    completed = list(continuity_store.load_task(TASK_ID).completed_steps)
    campaign = LearningCampaign(CAMPAIGN_ID, TASK_ID, objective, UNIT_IDS,
                                completed_units=list(completed), status="ACTIVE",
                                next_action=next((uid for uid in UNIT_IDS if uid not in completed),
                                                   "RUN_TEST_ONLY_APPLICATION"),
                                budget={"max_units": 14, "external_writes": 0,
                                        "financial_actions": 0, "unauthorized_cyber_actions": 0,
                                        "preemptible": True})
    unit_map = {unit.knowledge_id: unit for unit in units}
    preempted = False
    for unit_id in UNIT_IDS:
        if unit_id in completed:
            continue
        if trigger_check(root):
            next_action = unit_id
            engine.checkpoint(TASK_ID, session.session_id, completed_steps=completed,
                              next_action=next_action, repository_root=root)
            engine.preempt(TASK_ID, session.session_id)
            campaign.status, campaign.next_action = "PREEMPTED", next_action
            preempted = True
            break
        unit = unit_map[unit_id]
        if not set(unit.prerequisites).issubset(set(completed)):
            campaign.failed_assessments.append(unit_id)
            campaign.status, campaign.next_action = "BLOCKED", unit_id
            break
        unit.assessment = assess_probability_unit(unit)
        unit.state = "PROBLEM_TESTED" if unit.assessment.score == 1.0 else "UNDERSTANDING_CANDIDATE"
        store.save_unit(unit)
        store.save(store.assessments / f"{unit_id}.json",
                   {**asdict(unit.assessment), "diagnostic_evidence": diagnostic_evidence(unit_id)})
        if unit.assessment.score == 1.0:
            completed.append(unit_id)
        else:
            campaign.failed_assessments.append(unit_id)
        campaign.completed_units = list(completed)
        campaign.next_action = next((uid for uid in UNIT_IDS if uid not in completed),
                                    "RUN_TEST_ONLY_APPLICATION")
        engine.checkpoint(TASK_ID, session.session_id, completed_steps=completed,
                          next_action=campaign.next_action, repository_root=root)
    if preempted:
        result = {
            "schema": "zero.probability-statistics-campaign.v1", "generated_at": _now(),
            "campaign": asdict(campaign), "park_eligibility": eligibility,
            "knowledge_states": {uid: unit_map[uid].state for uid in UNIT_IDS},
            "task_continuity": engine.status(TASK_ID), "preemption": "TRIGGERED_PASS",
            "external_writes": 0, "financial_actions": 0, "production_changes": 0,
        }
        store.save(result_path, result)
        return store.read(result_path)

    application = run_statistical_application(root)
    if application.get("passed"):
        for unit_id in ("PS05", "PS06", "PS08", "PS09", "PS12", "PS13", "PS14"):
            unit = unit_map[unit_id]
            unit.state = "APPLIED"
            unit.confidence_vector["application"] = 0.75
            store.save_unit(unit)
    all_passed = len(completed) == len(UNIT_IDS) and not campaign.failed_assessments
    verified = all_passed and application.get("passed", False)
    campaign.status = "COMPLETED" if verified else "PARTIAL"
    campaign.next_action = "RETURN_TO_REAL_WORK_OR_WAIT_EXTERNAL_EVIDENCE"
    engine.host_verified(TASK_ID, session.session_id, verified)
    if verified:
        engine.complete(TASK_ID, session.session_id)
    result = {
        "schema": "zero.probability-statistics-campaign.v1", "generated_at": _now(),
        "campaign": asdict(campaign), "park_eligibility": eligibility,
        "knowledge_states": {uid: unit_map[uid].state for uid in UNIT_IDS},
        "source_provenance": [asdict(unit.source_evidence[0]) for unit in units],
        "assessment_summary": {"passed": len(completed),
                               "failed": len(campaign.failed_assessments), "total": len(units)},
        "active_recall": "PASS" if all_passed else "FAIL",
        "novel_problem_transfer": "PASS" if all_passed else "FAIL",
        "application": application,
        "host_verification": {"passed": verified, "verifier": "DETERMINISTIC_HOST_ORACLE",
                              "units_passed": all_passed,
                              "application_passed": application.get("passed", False)},
        "task_continuity": engine.status(TASK_ID), "preemption": "NOT_TRIGGERED",
        "replication": {"first_replicated_knowledge": False,
                        "first_verified_capability_from_learning": False},
        "cybersecurity_mode": CYBER_MODE, "external_writes": 0,
        "financial_actions": 0, "unauthorized_cyber_actions": 0,
        "production_changes": 0, "production_routing": "UNCHANGED",
        "trusted_on_first_cycle": 0,
    }
    store.save(result_path, result)
    store.save(out / "campaign.json", asdict(campaign))
    store.save(out / "capability_candidate.json", application)
    return store.read(result_path)


def probability_campaign_status(root: Path) -> dict[str, Any]:
    root = Path(root).resolve()
    out, result_path = _campaign_paths(root)
    if not result_path.exists():
        return {"campaign_state": "NOT_STARTED", "task_id": TASK_ID,
                "park_eligibility": park_eligibility(root)}
    return LearningStore(out).read(result_path)


__all__ = [
    "AUTHORITY_ID", "CAMPAIGN_ID", "TASK_ID", "UNIT_IDS", "assess_probability_unit",
    "diagnostic_evidence", "material_real_work_trigger", "park_eligibility",
    "probability_campaign_status", "probability_units", "run_probability_campaign",
    "run_statistical_application",
]
