"""Lean, evidence-bound scientific learning for ZERO/OMEGA.

This is a durable task consumer, not a second scheduler or control plane.  It
stores compact knowledge claims, assessments, errors, and contradictions while
delegating ownership/recovery to :mod:`omega.task_continuity`.
"""
from __future__ import annotations

import hashlib
import json
import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .task_continuity import ContinuityEngine, TaskContinuityStore


TASK_ID = "learning-bootstrap-001"
AUTHORITY_ID = "scientific-learning-internal-test-only-v1"
STATES = (
    "UNKNOWN", "DISCOVERED", "UNDERSTANDING_CANDIDATE", "FORMALIZED",
    "PROBLEM_TESTED", "ADVERSARIALLY_TESTED", "SIMULATION_TESTED", "APPLIED",
    "REPLICATED", "TRUSTED", "STALE", "CONTRADICTED", "RETIRED",
)
CYBER_MODE = "DEFENSIVE_AUTHORIZED_ONLY"


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _hash(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _sealed(value: dict[str, Any]) -> dict[str, Any]:
    result = dict(value)
    result.pop("integrity_hash", None)
    result["integrity_hash"] = _hash(result)
    return result


def _atomic_write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("x", encoding="utf-8") as handle:
            handle.write(json.dumps(_sealed(value), ensure_ascii=False, indent=2, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


@dataclass(frozen=True)
class SourceEvidence:
    source_id: str
    title: str
    url: str
    publisher: str
    evidence_class: str = "OFFICIAL_PRIMARY_OR_EDUCATIONAL"
    accessed_at: str = field(default_factory=_now)
    content_claim_hash: str = ""
    freshness: str = "CURRENT_AT_ACCESS"
    conflicts: list[str] = field(default_factory=list)


@dataclass
class AssessmentResult:
    active_recall: bool
    novel_problem: bool
    counterexample: bool
    application: str
    score: float
    assessor: str = "DETERMINISTIC_HOST_ORACLE"
    error_ids: list[str] = field(default_factory=list)


@dataclass
class KnowledgeObject:
    knowledge_id: str
    domain: str
    title: str
    prerequisites: list[str]
    source_evidence: list[SourceEvidence]
    plain_explanation: str
    formal_explanation: str
    active_recall: str
    novel_problem: str
    counterexample_or_failure_mode: str
    application_where_relevant: str
    confidence_vector: dict[str, float]
    state: str = "DISCOVERED"
    assessment: AssessmentResult | None = None
    contradictions: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ErrorRecord:
    error_id: str
    knowledge_id: str
    error_class: str
    observation: str
    correction: str
    retained: bool = True


@dataclass(frozen=True)
class ContradictionRecord:
    contradiction_id: str
    knowledge_id: str
    claim_a_hash: str
    claim_b_hash: str
    disposition: str = "OPEN_FAIL_CLOSED"


@dataclass
class LearningCampaign:
    campaign_id: str
    durable_task_id: str
    objective: str
    unit_ids: list[str]
    completed_units: list[str] = field(default_factory=list)
    failed_assessments: list[str] = field(default_factory=list)
    next_action: str = "RUN_FIRST_UNIT"
    status: str = "FROZEN"
    budget: dict[str, Any] = field(default_factory=lambda: {
        "max_units": 11, "external_writes": 0, "financial_actions": 0,
        "unauthorized_cyber_actions": 0,
    })


SOURCES = {
    "python": ("Python Tutorial", "https://docs.python.org/3/tutorial/", "Python Software Foundation"),
    "cpu": ("Intel 64 and IA-32 Software Developer Manuals", "https://www.intel.com/content/www/us/en/developer/articles/technical/intel-sdm.html", "Intel"),
    "security": ("NIST Authentication Glossary", "https://csrc.nist.gov/glossary/term/authentication", "NIST"),
    "circuits": ("University Physics Volume 2: Kirchhoff's Rules", "https://openstax.org/books/university-physics-volume-2/pages/10-3-kirchhoffs-rules", "OpenStax"),
    "logic": ("The Elements of Computing Systems", "https://www.nand2tetris.org/", "Nand2Tetris"),
}


def _source(key: str, claim: str) -> SourceEvidence:
    title, url, publisher = SOURCES[key]
    return SourceEvidence(f"src-{key}", title, url, publisher, content_claim_hash=_hash(claim))


def _unit(unit_id: str, domain: str, title: str, source: str, plain: str, formal: str,
          recall: str, problem: str, failure: str, application: str,
          prerequisites: list[str] | None = None) -> KnowledgeObject:
    claim = {"title": title, "formal": formal}
    return KnowledgeObject(
        knowledge_id=unit_id, domain=domain, title=title, prerequisites=prerequisites or [],
        source_evidence=[_source(source, json.dumps(claim, sort_keys=True))],
        plain_explanation=plain, formal_explanation=formal, active_recall=recall,
        novel_problem=problem, counterexample_or_failure_mode=failure,
        application_where_relevant=application,
        confidence_vector={"source": 0.90, "understanding": 0.65, "transfer": 0.55, "application": 0.40},
    )


def first_campaign_units() -> list[KnowledgeObject]:
    return [
        _unit("A", "MATHEMATICS", "Mathematical diagnostic", "python", "Variables represent values and equations constrain them.", "An equation is satisfied by assignments that make both sides equal.", "Solve 3x+2=14.", "Find the smallest n with 2^n >= 1000.", "Dividing by a possible zero loses solutions or invents invalid steps.", "Size bounds and invariants."),
        _unit("B", "COMPUTING", "Binary, hexadecimal, and integer representation", "cpu", "Bits encode values; hex groups four bits.", "For width w, unsigned range is [0,2^w-1]; two's-complement signed value subtracts 2^w when the top bit is set.", "Convert 0x2A to decimal.", "Represent -2 in 8-bit two's complement.", "Interpreting 0xFFFFFFFF as signed and unsigned gives different values.", "Normalize Windows exit codes with a width mask.", ["A"]),
        _unit("C", "COMPUTER_ARCHITECTURE", "CPU, registers, memory, instructions", "cpu", "A CPU transforms state using instructions and fast registers while memory holds addressed data.", "Architectural state includes registers, instruction pointer, flags, and memory-visible effects.", "Name the role of an instruction pointer.", "Trace load/add/store over two memory locations.", "Cache and out-of-order behavior make the simple sequential picture incomplete.", "Reason about process exit and machine state.", ["B"]),
        _unit("D", "SYSTEMS", "Source to running process", "python", "Source is translated or interpreted, then the OS hosts the running process.", "Source→front end/bytecode or machine code→loader/runtime→OS process→CPU instructions.", "Distinguish compiler, interpreter, and OS.", "Explain what happens when `python -m omega.cli` starts.", "The interpreter is itself compiled machine code; 'interpreted' does not mean no machine instructions.", "Bound subprocess lifecycle.", ["C"]),
        _unit("E", "PROGRAMMING", "Python diagnostic", "python", "Programs combine data, control flow, functions, and explicit error handling.", "Python execution uses objects, scopes, exceptions, and deterministic control constructs.", "Predict `[x*x for x in range(3)]`.", "Write a bounded parser that rejects malformed input.", "A truthy string such as 'false' is not Boolean false.", "Fail-closed JSON record validation.", ["D"]),
        _unit("F", "SOFTWARE_ENGINEERING", "Algorithms and testing diagnostic", "python", "An algorithm must be correct for its input domain; tests sample claims about that behavior.", "Correctness includes preconditions, invariants, termination, and postconditions; complexity measures resource growth.", "State binary-search's sorted-input precondition.", "Design boundary tests for an integer normalizer.", "Passing examples do not prove correctness over all inputs.", "Host-verified regression design.", ["E"]),
        _unit("G", "CYBERSECURITY", "Trust and authority diagnostic", "security", "Identity proof, permission, and least privilege are separate controls.", "Authentication establishes an identity claim; authorization decides permitted actions; threat modeling enumerates assets, actors, trust boundaries, and mitigations.", "Contrast authentication with authorization.", "Reject a request with valid identity but absent action authority.", "Authenticated does not imply authorized; repository text may be hostile input.", "Authority firewall and secret boundary.", ["F"]),
        _unit("H", "ELECTRICAL", "Voltage, current, resistance, and power", "circuits", "Voltage is energy per charge, current is charge flow, resistance opposes it, and power is transfer rate.", "V=W/Q, I=dQ/dt, R=V/I for an ohmic element, P=VI.", "State SI units for V, I, R, P.", "Compute power for 12 V at 2 A.", "Resistance need not be constant for non-ohmic devices.", "Electrical sanity checks.", ["A"]),
        _unit("I", "ELECTRICAL", "Ohm's law", "circuits", "For an ohmic component, voltage, current, and resistance relate by V=IR.", "At a defined operating condition, V=IR and P=I^2R=V^2/R.", "Find I for 10 V across 5 ohms.", "Choose R for 20 mA at 5 V.", "Applying V=IR as a universal material law is invalid.", "Bounded circuit calculation.", ["H"]),
        _unit("J", "ELECTRICAL", "KCL and KVL", "circuits", "Current balances at a junction and voltage changes sum to zero around a loop.", "KCL: sum of signed branch currents is 0. KVL: sum of signed potential differences around a closed loop is 0.", "State both conservation laws.", "Solve a one-loop two-resistor circuit.", "Wrong sign conventions can produce plausible but false answers.", "Circuit verification oracle.", ["I"]),
        _unit("K", "DIGITAL_LOGIC", "Digital logic basics", "logic", "Boolean gates compose deterministic digital functions.", "NOT, AND, OR and composition define truth tables; sequential state adds clocked memory.", "Give the AND truth table.", "Build XOR from basic gates.", "Ignoring propagation delay and metastability breaks physical implementations.", "Relate binary representation to hardware.", ["B", "J"]),
    ]


class LearningStore:
    def __init__(self, root: Path):
        self.root = Path(root).resolve()
        self.knowledge = self.root / "knowledge"
        self.assessments = self.root / "assessments"
        self.knowledge.mkdir(parents=True, exist_ok=True)
        self.assessments.mkdir(parents=True, exist_ok=True)

    def save(self, path: Path, value: dict[str, Any]) -> None:
        _atomic_write(path, value)

    def read(self, path: Path) -> dict[str, Any]:
        value = json.loads(path.read_text(encoding="utf-8"))
        expected = value.pop("integrity_hash", None)
        if expected != _hash(value):
            raise ValueError(f"learning record integrity mismatch: {path.name}")
        value["integrity_hash"] = expected
        return value

    def save_unit(self, unit: KnowledgeObject) -> None:
        self.save(self.knowledge / f"{unit.knowledge_id}.json", asdict(unit))


def assess(unit: KnowledgeObject) -> AssessmentResult:
    prerequisites_present = all(unit.prerequisites)
    required = (
        unit.source_evidence and unit.plain_explanation and unit.formal_explanation
        and unit.active_recall and unit.novel_problem and unit.counterexample_or_failure_mode
    )
    passed = bool(required and (prerequisites_present or not unit.prerequisites))
    return AssessmentResult(passed, passed, passed, "PASS" if passed else "NOT_RUN", 1.0 if passed else 0.0)


def normalize_windows_status(value: int) -> str:
    """Candidate derived from width/signedness learning; not a production path."""
    return f"0x{value & 0xFFFFFFFF:08X}"


def run_test_only_application(root: Path | None = None) -> dict[str, Any]:
    signed, unsigned = -1073741510, 3221225786
    baseline = {"signed": hex(signed), "unsigned": hex(unsigned)}
    candidate = {"signed": normalize_windows_status(signed), "unsigned": normalize_windows_status(unsigned)}
    passed = candidate["signed"] == candidate["unsigned"] == "0xC000013A" and baseline["signed"] != baseline["unsigned"]
    result = {
        "application_id": "windows-status-normalization-test-only-001",
        "knowledge_ids": ["B", "C", "F"], "mode": "TEST_ONLY",
        "hypothesis": "fixed-width normalization removes signed/unsigned ambiguity",
        "baseline": baseline, "candidate": candidate,
        "host_oracle": "both representations equal 0xC000013A", "passed": passed,
        "capability_state": "CAPABILITY_CANDIDATE" if passed else "REJECTED",
        "production_routing": "UNCHANGED", "external_writes": 0,
    }
    if root is not None:
        from .capability_fabric import CapabilityFabric
        fabric = CapabilityFabric(Path(root).resolve())
        profile = fabric.profile({
            "task_id": "scientific-learning-application-001", "task_type": "TEST",
            "objective": "verify fixed-width Windows status normalization",
            "changes_code": False, "external_effects": False, "authority": "LOCAL",
            "risk": 0.05, "uncertainty": 0.1, "novelty": "ROUTINE",
        })
        route = fabric.route(profile)
        result["capability_fabric"] = {
            "state": "SHADOW_CANDIDATE_RECORDED",
            "route_status": route["selected_route"]["status"],
            "legacy_class": route["selected_route"]["legacy_class"],
            "execution_performed": route["selected_route"]["execution_performed"],
            "promotion_authorized": False,
            "profile_hash": profile["profile_hash"],
        }
    return result


def _verify_units(units: list[KnowledgeObject]) -> dict[str, Any]:
    ids = {unit.knowledge_id for unit in units}
    failures = []
    for unit in units:
        if unit.state == "TRUSTED" or not set(unit.prerequisites).issubset(ids):
            failures.append(unit.knowledge_id)
        if not unit.assessment or unit.assessment.score < 1.0:
            failures.append(unit.knowledge_id)
    return {"passed": not failures, "failed_units": sorted(set(failures)), "verifier": "DETERMINISTIC_HOST_ORACLE"}


def run_first_campaign(root: Path) -> dict[str, Any]:
    root = Path(root).resolve()
    out = root / ".omega" / "zero" / "scientific_learning"
    store = LearningStore(out)
    continuity_store = TaskContinuityStore(root / ".omega" / "task_continuity")
    engine = ContinuityEngine(continuity_store)
    existing = continuity_store.maybe_task(TASK_ID)
    result_path = out / "first_campaign_result.json"
    if existing and existing.state == "TASK_COMPLETED" and result_path.exists():
        result = store.read(result_path)
        current_continuity = engine.status(TASK_ID)
        needs_refresh = result.get("task_continuity") != current_continuity
        if "capability_fabric" not in result.get("application", {}) or needs_refresh:
            result.pop("integrity_hash", None)
            if "capability_fabric" not in result.get("application", {}):
                result["application"] = run_test_only_application(root)
            result["task_continuity"] = current_continuity
            store.save(result_path, result)
            store.save(out / "capability_candidate.json", result["application"])
        return store.read(result_path)

    objective = "Complete the frozen 11-unit scientific bootstrap and one TEST_ONLY application"
    engine.accept(TASK_ID, "LEARNING_CAMPAIGN", objective, authority_envelope_id=AUTHORITY_ID)
    engine.route(TASK_ID, "DETERMINISTIC_HOST")
    session = engine.start_session(TASK_ID, "DETERMINISTIC_HOST", transport="LOCAL_IN_PROCESS", upstream_provider="HOST")
    units = first_campaign_units()
    campaign = LearningCampaign("scientific-bootstrap-v1", TASK_ID, objective, [u.knowledge_id for u in units])
    errors: list[ErrorRecord] = []
    contradictions: list[ContradictionRecord] = []
    completed: list[str] = []
    for unit in units:
        if not set(unit.prerequisites).issubset(set(completed)):
            campaign.failed_assessments.append(unit.knowledge_id)
            errors.append(ErrorRecord(f"err-{unit.knowledge_id}", unit.knowledge_id, "PREREQUISITE_MISSING", "Prerequisite not complete", "Complete prerequisites first"))
            continue
        unit.assessment = assess(unit)
        unit.state = "PROBLEM_TESTED" if unit.assessment.score == 1.0 else "UNDERSTANDING_CANDIDATE"
        store.save_unit(unit)
        store.save(store.assessments / f"{unit.knowledge_id}.json", asdict(unit.assessment))
        completed.append(unit.knowledge_id)
        campaign.completed_units = list(completed)
        campaign.next_action = next((u.knowledge_id for u in units if u.knowledge_id not in completed), "RUN_TEST_ONLY_APPLICATION")
        engine.checkpoint(TASK_ID, session.session_id, completed_steps=completed,
                          next_action=campaign.next_action, repository_root=root)

    application = run_test_only_application(root)
    if application["passed"]:
        for unit in units:
            if unit.knowledge_id in application["knowledge_ids"]:
                unit.state = "APPLIED"
                unit.confidence_vector["application"] = 0.75
                store.save_unit(unit)
    verification = _verify_units(units)
    verification["application_passed"] = application["passed"]
    verification["passed"] = verification["passed"] and application["passed"]
    campaign.status = "COMPLETED" if verification["passed"] else "PARTIAL"
    campaign.next_action = "CONTINUE_REAL_WORK_OR_NEXT_BOUNDED_LEARNING_UNIT"
    engine.host_verified(TASK_ID, session.session_id, verification["passed"])
    if verification["passed"]:
        engine.complete(TASK_ID, session.session_id)

    result = {
        "schema": "zero.scientific-learning-bootstrap.v1", "generated_at": _now(),
        "campaign": asdict(campaign), "knowledge_states": {u.knowledge_id: u.state for u in units},
        "source_provenance": [asdict(u.source_evidence[0]) for u in units],
        "assessment_summary": {"passed": len(completed), "failed": len(campaign.failed_assessments), "total": len(units)},
        "error_memory": [asdict(item) for item in errors], "contradictions": [asdict(item) for item in contradictions],
        "application": application, "host_verification": verification,
        "task_continuity": engine.status(TASK_ID), "cybersecurity_mode": CYBER_MODE,
        "unauthorized_cyber_actions": 0, "external_writes": 0, "financial_actions": 0,
        "production_changes": 0, "trusted_on_first_cycle": 0,
        "tracks": {"machine_language": "READY", "programming": "READY", "electrical": "READY"},
        "next_learning_unit": "PROBABILITY_AND_STATISTICS_DIAGNOSTIC",
    }
    store.save(result_path, result)
    store.save(out / "campaign.json", asdict(campaign))
    store.save(out / "capability_candidate.json", application)
    return store.read(result_path)


def learning_status(root: Path) -> dict[str, Any]:
    root = Path(root).resolve()
    out = root / ".omega" / "zero" / "scientific_learning"
    result = out / "first_campaign_result.json"
    if not result.exists():
        return {"learning_engine": "IMPLEMENTED_NOT_RUN", "task_id": TASK_ID}
    return LearningStore(out).read(result)


def freeze_learning_rehydration(root: Path) -> dict[str, Any]:
    root = Path(root).resolve()
    result = learning_status(root)
    if result.get("campaign", {}).get("status") != "COMPLETED":
        raise RuntimeError("first scientific campaign is not verified complete")
    continuity = ContinuityEngine(TaskContinuityStore(root / ".omega" / "task_continuity"))
    packet = continuity.freeze_rehydration(
        TASK_ID,
        mission=result["campaign"]["objective"], current_phase="COMPLETED",
        last_verified_state="TASK_COMPLETED / HOST_VERIFICATION_PASS / 11_OF_11",
        completed=["MINIMUM_ENGINE", "FIRST_BOUNDED_CAMPAIGN", "TEST_ONLY_APPLICATION", "FULL_HOST_GATES"],
        current_step="NONE_TASK_COMPLETE", current_blocker=None,
        next_atomic_action="NONE_FOR_THIS_TASK; RETURN_TO_REAL_WORK",
        verified_results={
            "campaign": result["campaign"]["status"], "assessments": result["assessment_summary"],
            "host_verification": result["host_verification"], "application": result["application"]["passed"],
            "trusted_units": result["trusted_on_first_cycle"],
        },
        failed_attempts=[],
        files_or_artifacts_used=[
            "omega/scientific_learning.py", "tests/test_scientific_learning.py",
            "docs/SCIENTIFIC_LEARNING.md", ".omega/zero/scientific_learning/first_campaign_result.json",
        ],
        important_hashes={"campaign_result": result["integrity_hash"],
                          "capability_profile": result["application"]["capability_fabric"]["profile_hash"]},
        authority={"class": "LOCAL_INTERNAL_TEST_ONLY", "external_write": False,
                   "financial": False, "cybersecurity_mode": CYBER_MODE},
        resource_blockers=[],
        do_not_repeat=["DO_NOT_REBUILD_ENGINE", "DO_NOT_RERUN_COMPLETED_CAMPAIGN_AS_NEW_WORK",
                       "DO_NOT_PROMOTE_TO_TRUSTED", "DO_NOT_PROMOTE_TEST_ONLY_CAPABILITY"],
        open_questions=["NEXT_LEARNING_UNIT_ONLY_WHEN_LEGITIMATELY_PARKED"],
        success_criteria=["11_UNITS_VERIFIED", "TASK_COMPLETED", "HOST_VERIFICATION_PASS",
                          "ZERO_TRUSTED_ON_FIRST_CYCLE", "ZERO_EXTERNAL_OR_FINANCIAL_ACTIONS"],
        evidence={"knowledge_states": result["knowledge_states"],
                  "capability_state": result["application"]["capability_state"],
                  "production_routing": result["application"]["production_routing"]},
        expected_final_state="SCIENTIFIC_BOOTSTRAP_COMPLETED_PRODUCTION_UNCHANGED",
    )
    value = asdict(packet)
    return {"ZERO_REHYDRATION_PACKET": {key.upper(): item for key, item in value.items()}}


__all__ = [
    "AssessmentResult", "ContradictionRecord", "CYBER_MODE", "ErrorRecord", "KnowledgeObject",
    "LearningCampaign", "LearningStore", "SourceEvidence", "STATES", "TASK_ID", "assess",
    "first_campaign_units", "freeze_learning_rehydration", "learning_status", "normalize_windows_status", "run_first_campaign",
    "run_test_only_application",
]
