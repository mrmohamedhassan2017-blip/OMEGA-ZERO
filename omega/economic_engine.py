from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


CONSTITUTION_ID = "ZERO-AUTONOMOUS-ECONOMIC-ENGINE-V2.0"
TARGET_USD = 1_000_000.0


class RealityLevel(str, Enum):
    L0 = "INTERNAL_HYPOTHESIS"
    L1 = "REAL_EXTERNAL_CONTACT"
    L2 = "VERIFIED_MARKET_RESPONSE"
    L3 = "VERIFIED_COMMERCIAL_COMMITMENT"
    L4 = "VERIFIED_PAYMENT"
    L5 = "VERIFIED_PROFIT"
    L6 = "REPEATED_ECONOMIC_ENGINE"
    L7 = "SCALABLE_ECONOMIC_ENGINE"


class AuthorityClass(str, Enum):
    A0 = "OBSERVE_READ"
    A1 = "INTERNAL_EXECUTION"
    A2 = "EXTERNAL_ACTION_PREPARATION"
    A3 = "AUTHORIZED_EXTERNAL_WRITE"
    A4 = "CONTRACTUAL_COMMITMENT"
    A5 = "FINANCIAL_ACTION"
    A6 = "SENSITIVE_SECURITY_ACTION"


class ApprovalPolicy(str, Enum):
    PREAUTHORIZED = "PREAUTHORIZED"
    PER_ACTION = "PER_ACTION"
    PER_CLASS = "PER_CLASS"
    PER_ACCOUNT = "PER_ACCOUNT"
    PER_MISSION = "PER_MISSION"
    HUMAN_REQUIRED = "HUMAN_REQUIRED"
    PROHIBITED = "PROHIBITED"


AUTHORITY_ORDER = {
    AuthorityClass.A0: 0,
    AuthorityClass.A1: 1,
    AuthorityClass.A2: 2,
    AuthorityClass.A3: 3,
    AuthorityClass.A4: 4,
    AuthorityClass.A5: 5,
    AuthorityClass.A6: 6,
}

LADDER_ORDER = {
    RealityLevel.L0: 0,
    RealityLevel.L1: 1,
    RealityLevel.L2: 2,
    RealityLevel.L3: 3,
    RealityLevel.L4: 4,
    RealityLevel.L5: 5,
    RealityLevel.L6: 6,
    RealityLevel.L7: 7,
}


class EconomicFailure(str, Enum):
    MARKET_REJECTION = "MARKET_REJECTION"
    NO_DEMAND = "NO_DEMAND"
    PRICING_FAILURE = "PRICING_FAILURE"
    CAPABILITY_FAILURE = "CAPABILITY_FAILURE"
    QUALITY_FAILURE = "QUALITY_FAILURE"
    PAYMENT_FAILURE = "PAYMENT_FAILURE"
    FRAUD_DETECTED = "FRAUD_DETECTED"
    AUTHORITY_BLOCKER = "AUTHORITY_BLOCKER"
    PLATFORM_LIMIT = "PLATFORM_LIMIT"
    RESOURCE_FAILURE = "RESOURCE_FAILURE"
    TECHNICAL_FAILURE = "TECHNICAL_FAILURE"
    NEGATIVE_UNIT_ECONOMICS = "NEGATIVE_UNIT_ECONOMICS"
    LIQUIDITY_RISK = "LIQUIDITY_RISK"
    REPUTATION_RISK = "REPUTATION_RISK"
    LEGAL_RISK = "LEGAL_RISK"
    SECURITY_SCOPE_FAILURE = "SECURITY_SCOPE_FAILURE"
    EVIDENCE_FAILURE = "EVIDENCE_FAILURE"
    CAUSAL_UNCERTAINTY = "CAUSAL_UNCERTAINTY"
    UNKNOWN_FAILURE = "UNKNOWN_FAILURE"


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _hash(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


@dataclass(frozen=True)
class AuthorityContext:
    authority_class: AuthorityClass
    authority_source: str
    approval_policy: ApprovalPolicy
    approval_evidence: str | None = None
    approval_expiry: str | None = None
    revocation_state: str = "ACTIVE"

    def allows(self, required: AuthorityClass, observed_at: str | None = None) -> bool:
        if self.revocation_state != "ACTIVE":
            return False
        if self.approval_policy in {ApprovalPolicy.PROHIBITED, ApprovalPolicy.HUMAN_REQUIRED}:
            return False
        if AUTHORITY_ORDER[self.authority_class] < AUTHORITY_ORDER[required]:
            return False
        if required.value in {AuthorityClass.A3.value, AuthorityClass.A4.value, AuthorityClass.A5.value, AuthorityClass.A6.value}:
            if not self.approval_evidence:
                return False
            if self.approval_expiry:
                at = datetime.fromisoformat(observed_at or _now())
                expiry = datetime.fromisoformat(self.approval_expiry)
                if expiry <= at:
                    return False
        return True


@dataclass(frozen=True)
class EconomicEvidence:
    evidence_id: str
    source: str
    observed_at: str
    freshness_class: str
    source_type: str
    independence: str
    supports: list[str]
    confidence: float
    valid_until: str | None = None
    revalidation_policy: str | None = None
    contradicts: list[str] = field(default_factory=list)

    def is_current(self, at: str | None = None) -> bool:
        if self.valid_until is None:
            return True
        return datetime.fromisoformat(self.valid_until) > datetime.fromisoformat(at or _now())


@dataclass(frozen=True)
class EconomicClaim:
    claim_id: str
    claim_type: str
    claim_value: float | str | bool
    claim_unit: str
    created_at: str
    evidence_refs: list[str]
    evidence_confidence: float
    reality_level: RealityLevel
    authority_context: AuthorityContext
    last_verified_at: str | None = None
    contradicting_evidence: list[str] = field(default_factory=list)
    expiry_policy: str = "REVALIDATE_ON_EXTERNAL_CHANGE"
    current_status: str = "UNVERIFIED"
    derived_from_claims: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class OpportunityObject:
    opportunity_id: str
    source: str
    source_evidence: list[str]
    discovered_at: str
    problem: str
    customer_class: str
    market_class: str
    evidence_level: RealityLevel
    expected_gross_revenue: float
    expected_net_value: float
    estimated_execution_time: float
    estimated_compute_cost: float
    estimated_financial_cost: float
    estimated_human_cost: float
    p_acceptance: float
    p_payment_given_acceptance: float
    evidence_confidence: float
    repeatability_factor: float
    defensibility_factor: float
    strategic_reuse_factor: float
    information_value: float
    capability_gain_value: float
    reputation_value: float
    repeat_potential: float
    scale_potential: float
    authority_class_required: AuthorityClass
    approval_policy: ApprovalPolicy
    legal_risk: float
    platform_risk: float
    reputation_risk: float
    fraud_risk: float
    security_risk: float
    capability_fit: float
    execution_confidence: float
    unknowns: list[str]
    critical_assumption: str
    cheapest_truth_experiment: str
    kill_conditions: list[str]
    scale_conditions: list[str]
    evidence_refs: list[str]
    state: str
    next_action: str


@dataclass(frozen=True)
class CashFlowState:
    pipeline_value: float = 0.0
    contracted_value: float = 0.0
    earned_value: float = 0.0
    accounts_receivable: float = 0.0
    settled_value: float = 0.0
    available_cash: float = 0.0
    withdrawn_value: float = 0.0
    committed_cost: float = 0.0
    cash_at_risk: float = 0.0
    upcoming_obligations: float = 0.0
    runway: str = "UNKNOWN"
    working_capital: float = 0.0
    verified_net_cash_profit: float = 0.0
    verified_realized_economic_value: float = 0.0
    verified_asset_value: float = 0.0
    unrealized_estimated_asset_value: float = 0.0


@dataclass(frozen=True)
class ScaleAssessment:
    marginal_revenue: float
    marginal_cost: float
    marginal_failure_rate: float
    marginal_support_load: float
    marginal_cash_requirement: float
    marginal_reputation_risk: float
    marginal_platform_risk: float
    concentration_risk: float
    authority_valid: bool
    liquidity_acceptable: bool

    def decision(self) -> str:
        mev = self.marginal_revenue - self.marginal_cost - self.marginal_cash_requirement
        if mev <= 0:
            return EconomicFailure.NEGATIVE_UNIT_ECONOMICS.value
        if not self.liquidity_acceptable:
            return EconomicFailure.LIQUIDITY_RISK.value
        if self.concentration_risk > 0.75:
            return "CONCENTRATION_RISK"
        if not self.authority_valid:
            return EconomicFailure.AUTHORITY_BLOCKER.value
        return "SCALE_ALLOWED"


@dataclass(frozen=True)
class CausalObservation:
    problem: str
    context: str
    intervention: str
    observed_outcome: str
    alternative_explanation: str
    control_or_baseline: str
    causal_confidence: float
    replication_count: int
    contradicting_cases: list[str]
    resulting_policy: str


@dataclass(frozen=True)
class EconomicEvent:
    event_id: str
    opportunity_id: str
    timestamp: str
    event_type: str
    amount: float
    currency: str
    gross_value: float
    cost: float
    net_value: float
    evidence_reference: str
    counterparty_class: str
    source: str
    authority_class: AuthorityClass
    confidence: float
    settlement_state: str
    original_currency: str | None = None
    original_amount: float | None = None
    converted_currency: str | None = None
    converted_amount: float | None = None
    fx_rate: float | None = None
    fx_source: str | None = None
    fx_evidence_timestamp: str | None = None
    conversion_timestamp: str | None = None
    idempotency_key: str | None = None
    previous_hash: str | None = None
    ledger_hash: str | None = None


@dataclass(frozen=True)
class EconomicMissionState:
    mission_id: str = "ZERO-ECONOMIC-MISSION"
    target_usd: float = TARGET_USD
    reality_level: RealityLevel = RealityLevel.L0
    verified_net_economic_value_usd: float = 0.0
    evidence_level: str = "L0"

    @property
    def target_remaining_usd(self) -> float:
        return max(0.0, self.target_usd - self.verified_net_economic_value_usd)


@dataclass(frozen=True)
class EconomicEngineState:
    constitution_id: str
    mission_state: EconomicMissionState
    cash_flow: CashFlowState
    opportunity_count: int
    claim_count: int
    ledger_event_count: int
    current_highest_value_hypothesis: str
    current_critical_assumption: str
    next_cheapest_truth_experiment: str
    current_authority_class: AuthorityClass
    current_approval_policy: ApprovalPolicy
    current_approval_state: str
    parallel_control_plane_created: bool = False


PLATFORM_STATES = {
    "UNVERIFIED", "DISCOVERY_ONLY", "PREPARATION_ONLY",
    "EXECUTION_REQUIRES_APPROVAL", "AUTHORIZED_EXECUTION", "PAYOUT_BLOCKED",
    "COUNTRY_INELIGIBLE", "KYC_REQUIRED", "HUMAN_ACTION_REQUIRED",
    "POLICY_UNCLEAR", "PROHIBITED",
}


@dataclass(frozen=True)
class EconomicPlatform:
    platform_id: str
    platform_name: str
    official_url: str
    platform_class: str
    opportunity_classes: tuple[str, ...]
    country_eligibility: str = "UNKNOWN"
    account_required: str = "UNKNOWN"
    kyc_required: str = "UNKNOWN"
    payment_methods: tuple[str, ...] = ("UNKNOWN",)
    payout_eligibility: str = "UNKNOWN"
    fees: str = "UNKNOWN"
    ai_usage_policy: str = "UNKNOWN"
    automation_policy: str = "UNKNOWN"
    human_action_required: bool = True
    authority_class_required: AuthorityClass = AuthorityClass.A2
    approval_policy: ApprovalPolicy = ApprovalPolicy.PER_ACTION
    policy_evidence_refs: tuple[str, ...] = ()
    policy_verified_at: str | None = None
    policy_freshness: str = "UNVERIFIED"
    risk_state: str = "UNKNOWN"
    discovery_enabled: bool = False
    execution_enabled: bool = False
    payout_enabled: bool = False
    economic_score: float = 0.0
    cheapest_truth_experiment: str = "Verify current official policy before any action."
    state: str = "UNVERIFIED"
    critical_assumption: str = "UNKNOWN"
    expected_information_gain: str = "UNKNOWN"
    kill_condition: str = "Policy, authority, or evidence boundary fails."
    success_evidence: str = "Independent external evidence, not owner/self activity."

    def __post_init__(self) -> None:
        if self.state not in PLATFORM_STATES:
            raise ValueError(f"invalid platform state: {self.state}")


def _platform(
    platform_id: str,
    platform_name: str,
    official_url: str,
    platform_class: str,
    opportunity_classes: tuple[str, ...],
    *,
    state: str = "UNVERIFIED",
    evidence: tuple[str, ...] = (),
    discovery: bool = False,
    execution: bool = False,
    payout: bool = False,
    authority: AuthorityClass = AuthorityClass.A2,
    approval: ApprovalPolicy = ApprovalPolicy.PER_ACTION,
    ai_policy: str = "UNKNOWN",
    automation_policy: str = "UNKNOWN",
    account_required: str = "UNKNOWN",
    kyc_required: str = "UNKNOWN",
    payout_eligibility: str = "UNKNOWN",
    fees: str = "UNKNOWN",
    human_required: bool = True,
    risk: str = "UNKNOWN",
    critical_assumption: str = "UNKNOWN",
    experiment: str = "Verify current official policy before any action.",
    eig: str = "UNKNOWN",
    score: float = 0.0,
    now: str | None = None,
) -> EconomicPlatform:
    return EconomicPlatform(
        platform_id=platform_id,
        platform_name=platform_name,
        official_url=official_url,
        platform_class=platform_class,
        opportunity_classes=opportunity_classes,
        account_required=account_required,
        kyc_required=kyc_required,
        payout_eligibility=payout_eligibility,
        fees=fees,
        ai_usage_policy=ai_policy,
        automation_policy=automation_policy,
        human_action_required=human_required,
        authority_class_required=authority,
        approval_policy=approval,
        policy_evidence_refs=evidence,
        policy_verified_at=now if evidence else None,
        policy_freshness="CURRENT_OFFICIAL_EVIDENCE" if evidence else "UNVERIFIED",
        risk_state=risk,
        discovery_enabled=discovery,
        execution_enabled=execution,
        payout_enabled=payout,
        economic_score=round(score, 4),
        cheapest_truth_experiment=experiment,
        state=state,
        critical_assumption=critical_assumption,
        expected_information_gain=eig,
    )


def build_platform_registry(root: Path) -> dict[str, Any]:
    """Build the conservative economic platform registry.

    This is an internal registry only.  It records current official evidence
    where available, fails closed on unknown policy/eligibility/payout facts,
    and never grants external-write, contractual, financial, or security
    authority.
    """
    root = root.resolve()
    now = _now()
    platforms: list[EconomicPlatform] = [
        _platform(
            "github", "GitHub", "https://docs.github.com/",
            "DEVELOPER_PRODUCT", ("public artifact discovery", "issues", "actions"),
            state="DISCOVERY_ONLY", evidence=(
                "https://docs.github.com/en/site-policy/acceptable-use-policies/github-acceptable-use-policies",
                "https://docs.github.com/en/actions/reference/security/secure-use",
            ),
            discovery=True, execution=False, payout=False, authority=AuthorityClass.A0,
            ai_policy="Commercial AI/content-use policies exist; not equivalent to permission for outreach or scraping.",
            automation_policy="Official acceptable-use policies prohibit spam/abuse and impose service-usage limits.",
            account_required="YES_FOR_WRITE; NO_FOR_PUBLIC_READ",
            kyc_required="NO_FOR_PUBLIC_READ", payout_eligibility="N/A_FOR_DISCOVERY",
            fees="UNKNOWN_OR_USAGE_DEPENDENT", human_required=False, risk="LOW_IF_READ_ONLY",
            critical_assumption="Independent developers can discover the existing public artifact without owner-generated engagement.",
            experiment="Continue passive public GitHub inbound observation; do not count owner views/stars/clones as demand.",
            eig="MEDIUM", score=0.66, now=now,
        ),
        _platform(
            "github-sponsors", "GitHub Sponsors", "https://docs.github.com/en/sponsors",
            "DEVELOPER_PRODUCT", ("open-source sponsorship",),
            state="KYC_REQUIRED", evidence=(
                "https://docs.github.com/en/sponsors/getting-started-with-github-sponsors/about-github-sponsors",
                "https://docs.github.com/sponsors/receiving-sponsorships-through-github-sponsors/tax-information-for-github-sponsors",
            ),
            discovery=True, execution=False, payout=False, authority=AuthorityClass.A5,
            account_required="YES", kyc_required="YES_TAX_AND_SUPPORTED_REGION",
            payout_eligibility="SUPPORTED_REGION_REQUIRED", fees="UNKNOWN",
            human_required=True, risk="PAYOUT_AND_IDENTITY_GATE",
            critical_assumption="A sponsorship page would produce economic evidence after independent utility exists.",
            experiment="Prepare only after L2/L3 utility evidence; do not enable payout without owner KYC/financial authority.",
            eig="LOW_BEFORE_DEMAND", score=0.22, now=now,
        ),
        _platform(
            "upwork", "Upwork", "https://www.upwork.com/legal",
            "FREELANCE", ("contract work", "AI policy/compliance services"),
            state="HUMAN_ACTION_REQUIRED", evidence=("https://www.upwork.com/legal",),
            discovery=True, execution=False, payout=False, authority=AuthorityClass.A3,
            ai_policy="Official legal center references platform AI use; seller-side autonomous AI policy remains not fully verified.",
            automation_policy="UNKNOWN; fail closed before any proposal or message.",
            account_required="YES", kyc_required="UNKNOWN", payout_eligibility="UNKNOWN",
            fees="UNKNOWN", human_required=True, risk="REPUTATION_AND_POLICY_UNCLEAR",
            critical_assumption="A human-reviewed freelance opportunity can be qualified without spam or misrepresentation.",
            experiment="Read-only opportunity qualification only; any proposal requires one explicit A3 approval.",
            eig="MEDIUM", score=0.45, now=now,
        ),
    ]
    catalog = {
        "fiverr": ("Fiverr", "https://www.fiverr.com/", "FREELANCE"),
        "freelancer": ("Freelancer.com", "https://www.freelancer.com/", "FREELANCE"),
        "contra": ("Contra", "https://contra.com/", "FREELANCE"),
        "toptal": ("Toptal", "https://www.toptal.com/", "FREELANCE"),
        "guru": ("Guru", "https://www.guru.com/", "FREELANCE"),
        "peopleperhour": ("PeoplePerHour", "https://www.peopleperhour.com/", "FREELANCE"),
        "malt": ("Malt", "https://www.malt.com/", "FREELANCE"),
        "workana": ("Workana", "https://www.workana.com/", "FREELANCE"),
        "product-hunt": ("Product Hunt", "https://www.producthunt.com/", "DEVELOPER_PRODUCT"),
        "rapidapi": ("RapidAPI", "https://rapidapi.com/", "DEVELOPER_PRODUCT"),
        "gumroad": ("Gumroad", "https://gumroad.com/", "DEVELOPER_PRODUCT"),
        "lemon-squeezy": ("Lemon Squeezy", "https://www.lemonsqueezy.com/", "DEVELOPER_PRODUCT"),
        "paddle": ("Paddle", "https://www.paddle.com/", "DEVELOPER_PRODUCT"),
        "topcoder": ("Topcoder", "https://www.topcoder.com/", "COMPETITION"),
        "kaggle": ("Kaggle", "https://www.kaggle.com/", "COMPETITION"),
        "devpost": ("Devpost", "https://devpost.com/", "COMPETITION"),
        "direct-b2b": ("Direct B2B", "owner-controlled direct channel", "DIRECT"),
        "own-website": ("Own Website", "owner-controlled website", "DIRECT"),
        "own-saas": ("Own SaaS", "owner-controlled SaaS", "DIRECT"),
        "hackerone": ("HackerOne", "https://www.hackerone.com/", "AUTHORIZED_SECURITY_DISCOVERY_ONLY"),
        "bugcrowd": ("Bugcrowd", "https://www.bugcrowd.com/", "AUTHORIZED_SECURITY_DISCOVERY_ONLY"),
        "intigriti": ("Intigriti", "https://www.intigriti.com/", "AUTHORIZED_SECURITY_DISCOVERY_ONLY"),
        "yeswehack": ("YesWeHack", "https://www.yeswehack.com/", "AUTHORIZED_SECURITY_DISCOVERY_ONLY"),
        "synack": ("Synack", "https://www.synack.com/", "AUTHORIZED_SECURITY_DISCOVERY_ONLY"),
    }
    for platform_id, (name, url, platform_class) in catalog.items():
        if platform_class == "DIRECT":
            state = "PREPARATION_ONLY"
            authority = AuthorityClass.A2
            score = 0.52 if platform_id == "own-website" else 0.49
            experiment = "Prepare a privacy-safe landing/evidence packet; publication or contact still requires explicit authority."
            eig = "MEDIUM"
            critical = "A passive owner-controlled surface can convert existing artifact visibility into attributable external intent."
        elif platform_class == "AUTHORIZED_SECURITY_DISCOVERY_ONLY":
            state = "POLICY_UNCLEAR"
            authority = AuthorityClass.A6
            score = 0.08
            experiment = "Passive policy parsing only; no account action or testing without a complete official authorization contract."
            eig = "LOW_UNTIL_SCOPE_VERIFIED"
            critical = "Official scope and safe-harbor boundaries can be completely frozen before any security action."
        else:
            state = "UNVERIFIED"
            authority = AuthorityClass.A3
            score = 0.18
            experiment = "Verify official policy, account, payout, AI, and automation constraints before any external write."
            eig = "UNKNOWN"
            critical = "The platform allows lawful, non-spam discovery or preparation by this owner identity."
        platforms.append(_platform(
            platform_id, name, url, platform_class, ("market evidence",),
            state=state, authority=authority, approval=ApprovalPolicy.PER_ACTION,
            risk="UNKNOWN_FAIL_CLOSED", critical_assumption=critical,
            experiment=experiment, eig=eig, score=score, now=now,
        ))

    selected = sorted(
        (p for p in platforms if p.state in {"DISCOVERY_ONLY", "PREPARATION_ONLY", "HUMAN_ACTION_REQUIRED"}),
        key=lambda item: (-item.economic_score, item.platform_id),
    )[:3]
    first = selected[0] if selected else None
    report = {
        "format": "omega.economic-platform-registry",
        "version": 1,
        "generated_at": now,
        "canonical_repository": str(root),
        "platform_states": sorted(PLATFORM_STATES),
        "platforms": [_serialize(item) for item in platforms],
        "platform_count": len(platforms),
        "policy_verified_count": sum(bool(p.policy_evidence_refs) for p in platforms),
        "verified_discovery_platforms": [p.platform_id for p in platforms if p.discovery_enabled],
        "execution_ready_platforms": [p.platform_id for p in platforms if p.execution_enabled],
        "payout_ready_platforms": [p.platform_id for p in platforms if p.payout_enabled],
        "policy_unknown_platforms": [p.platform_id for p in platforms if p.state in {"UNVERIFIED", "POLICY_UNCLEAR"}],
        "human_required_platforms": [p.platform_id for p in platforms if p.human_action_required],
        "top_3_channels": [_serialize(item) for item in selected],
        "selected_first_experiment": None if first is None else {
            "platform_id": first.platform_id,
            "critical_assumption": first.critical_assumption,
            "cheapest_truth_experiment": first.cheapest_truth_experiment,
            "authority_required": first.authority_class_required.value,
            "approval_required": first.approval_policy.value,
            "expected_information_gain": first.expected_information_gain,
            "kill_condition": first.kill_condition,
            "success_evidence": first.success_evidence,
            "executed": False,
            "external_evidence_created": False,
        },
        "external_actions": 0,
        "financial_actions": 0,
        "security_actions": 0,
        "reality_level_before": RealityLevel.L0.value,
        "reality_level_after": RealityLevel.L0.value,
        "registry_state": "IMPLEMENTED_PREPARE_ONLY",
    }
    report["registry_hash"] = _hash(report)
    return report


def run_platform_registry(root: Path) -> dict[str, Any]:
    base = root.resolve() / ".omega" / "zero" / "economic"
    report = build_platform_registry(root)
    _write(base / "platform_registry.json", report)
    return report


def economic_utility(opportunity: OpportunityObject, *, opportunity_cost: float = 0.0,
                     failure_risk_adjusted_loss: float = 0.0) -> float:
    gross = (
        opportunity.expected_net_value
        * opportunity.p_acceptance
        * opportunity.p_payment_given_acceptance
        * opportunity.repeatability_factor
        * opportunity.defensibility_factor
        * opportunity.strategic_reuse_factor
        * opportunity.evidence_confidence
    )
    costs = (
        opportunity.estimated_execution_time
        + opportunity.estimated_financial_cost
        + opportunity.estimated_compute_cost
        + opportunity.estimated_human_cost
        + opportunity_cost
        + opportunity.legal_risk
        + opportunity.platform_risk
        + opportunity.reputation_risk
        + opportunity.fraud_risk
        + opportunity.security_risk
        + failure_risk_adjusted_loss
    )
    return round(gross + opportunity.information_value + opportunity.capability_gain_value + opportunity.reputation_value - costs, 6)


def validate_promotion(target: RealityLevel, evidence: list[EconomicEvidence], claims: list[EconomicClaim]) -> tuple[bool, str]:
    if target == RealityLevel.L0:
        return True, "internal hypothesis allowed"
    current = [item for item in evidence if item.is_current()]
    if target == RealityLevel.L1:
        return any(item.source_type == "EXTERNAL_CONTACT" for item in current), "L1 requires real external contact"
    if target == RealityLevel.L2:
        return any(item.source_type == "MARKET_RESPONSE" and item.independence == "THIRD_PARTY" for item in current), "L2 requires verified market response"
    if target == RealityLevel.L3:
        return any(claim.claim_type == "COMMERCIAL_COMMITMENT" and claim.current_status == "VERIFIED" for claim in claims), "L3 requires verified commercial commitment"
    if target == RealityLevel.L4:
        return any(claim.claim_type == "PAYMENT_RECEIVED" and claim.current_status == "VERIFIED" for claim in claims), "L4 requires verified payment"
    if target == RealityLevel.L5:
        return any(claim.claim_type == "NET_VERIFIED_VALUE" and float(claim.claim_value) > 0 and claim.current_status == "VERIFIED" for claim in claims), "L5 requires verified profit"
    if target == RealityLevel.L6:
        return any(claim.claim_type == "ENGINE_REPEATABLE" and claim.current_status == "VERIFIED" for claim in claims), "L6 requires repeatable engine evidence"
    if target == RealityLevel.L7:
        return any(claim.claim_type == "ENGINE_SCALABLE" and claim.current_status == "VERIFIED" for claim in claims), "L7 requires scale gate evidence"
    return False, "unknown level"


def validate_claim(claim: EconomicClaim, evidence_by_id: dict[str, EconomicEvidence]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    refs = [evidence_by_id.get(ref) for ref in claim.evidence_refs]
    if any(ref is None for ref in refs):
        errors.append("missing_evidence")
    if any(ref and not ref.is_current() for ref in refs):
        errors.append("stale_evidence")
    if claim.contradicting_evidence:
        errors.append("contradicting_evidence_present")
    if claim.claim_type == "CUSTOMER_DEMAND_CONFIRMED" and not any(ref and ref.source_type == "MARKET_RESPONSE" and ref.independence == "THIRD_PARTY" for ref in refs):
        errors.append("proposal_or_owner_activity_is_not_demand")
    if claim.claim_type == "PAYMENT_RECEIVED" and claim.reality_level != RealityLevel.L4:
        errors.append("payment_claim_requires_L4")
    if claim.claim_type == "NET_VERIFIED_VALUE" and float(claim.claim_value) > 0 and claim.reality_level != RealityLevel.L5:
        errors.append("profit_claim_requires_L5")
    return not errors, errors


class EconomicLedger:
    def __init__(self, events: list[EconomicEvent] | None = None):
        self.events = events or []

    def append(self, event: EconomicEvent) -> EconomicEvent:
        if event.idempotency_key and any(item.idempotency_key == event.idempotency_key for item in self.events):
            raise ValueError("DUPLICATE_ECONOMIC_SIDE_EFFECT_REQUIRES_RECONCILIATION")
        previous = self.events[-1].ledger_hash if self.events else None
        payload = asdict(event)
        payload["authority_class"] = event.authority_class.value
        payload["previous_hash"] = previous
        payload["ledger_hash"] = None
        ledger_hash = _hash(payload)
        committed = EconomicEvent(**{**asdict(event), "previous_hash": previous, "ledger_hash": ledger_hash})
        self.events.append(committed)
        return committed

    def verify(self) -> tuple[bool, str]:
        previous = None
        for event in self.events:
            payload = asdict(event)
            if payload["previous_hash"] != previous:
                return False, "broken_previous_hash"
            expected = payload["ledger_hash"]
            payload["ledger_hash"] = None
            payload["authority_class"] = event.authority_class.value
            if _hash(payload) != expected:
                return False, "ledger_hash_mismatch"
            previous = expected
        return True, "ledger hash chain verified"

    def cash_flow(self) -> CashFlowState:
        settled = sum(event.net_value for event in self.events if event.settlement_state == "SETTLED")
        receivable = sum(event.net_value for event in self.events if event.settlement_state == "RECEIVABLE")
        contracted = sum(event.net_value for event in self.events if event.settlement_state == "CONTRACTED")
        earned = sum(event.net_value for event in self.events if event.settlement_state in {"EARNED", "RECEIVABLE", "SETTLED"})
        costs = sum(event.cost for event in self.events)
        return CashFlowState(
            contracted_value=contracted,
            earned_value=earned,
            accounts_receivable=receivable,
            settled_value=settled,
            available_cash=settled,
            committed_cost=costs,
            working_capital=settled - costs,
            verified_net_cash_profit=max(0.0, settled - costs),
            verified_realized_economic_value=max(0.0, settled - costs),
        )


def bootstrap_reality_audit(root: Path) -> dict[str, Any]:
    root = root.resolve()
    now = _now()
    mission = EconomicMissionState()
    authority = AuthorityContext(
        authority_class=AuthorityClass.A0,
        authority_source="repository truth and existing passive observation authority",
        approval_policy=ApprovalPolicy.PER_ACTION,
        approval_evidence=None,
    )
    evidence = [
        EconomicEvidence("v030-waiting", "PROJECT_STATE.md", now, "CURRENT", "INTERNAL_STATE", "OMEGA", ["V0.30 waiting external evidence"], 1.0),
        EconomicEvidence("e2-sent", ".omega/avf", now, "CURRENT", "EXTERNAL_ACTION", "OWNER_AUTHORIZED", ["E2-01 sent; no demand signal"], 1.0),
        EconomicEvidence("wake-plane-running", ".omega/wake-plane/heartbeat.json", now, "CURRENT", "INTERNAL_STATE", "OMEGA", ["Wake Plane passive production running"], 1.0),
        EconomicEvidence("zero-value-zero", "PROJECT_STATE.md", now, "CURRENT", "INTERNAL_STATE", "OMEGA", ["economic value remains 0"], 1.0),
    ]
    claims = [
        EconomicClaim("claim-real-value-zero", "NET_VERIFIED_VALUE", 0.0, "USD", now, ["zero-value-zero"], 1.0, RealityLevel.L0, authority, now, current_status="VERIFIED"),
        EconomicClaim("claim-v030-waiting", "CUSTOMER_DEMAND_CONFIRMED", False, "BOOLEAN", now, ["v030-waiting"], 1.0, RealityLevel.L0, authority, now, current_status="UNVERIFIED"),
    ]
    opportunities = [
        OpportunityObject(
            opportunity_id="opp-independent-economic-evidence",
            source="repository truth",
            source_evidence=["v030-waiting", "e2-sent"],
            discovered_at=now,
            problem="No verified external economic evidence exists yet.",
            customer_class="independent coding-agent developer/team",
            market_class="developer reliability tooling",
            evidence_level=RealityLevel.L0,
            expected_gross_revenue=0.0,
            expected_net_value=0.0,
            estimated_execution_time=0.1,
            estimated_compute_cost=0.0,
            estimated_financial_cost=0.0,
            estimated_human_cost=0.0,
            p_acceptance=0.0,
            p_payment_given_acceptance=0.0,
            evidence_confidence=1.0,
            repeatability_factor=0.0,
            defensibility_factor=0.0,
            strategic_reuse_factor=0.2,
            information_value=0.7,
            capability_gain_value=0.1,
            reputation_value=0.0,
            repeat_potential=0.0,
            scale_potential=0.0,
            authority_class_required=AuthorityClass.A0,
            approval_policy=ApprovalPolicy.PER_ACTION,
            legal_risk=0.0,
            platform_risk=0.0,
            reputation_risk=0.0,
            fraud_risk=0.0,
            security_risk=0.0,
            capability_fit=0.8,
            execution_confidence=0.9,
            unknowns=["independent demand", "willingness to pay", "repeatability"],
            critical_assumption="A qualified independent party will find enough utility to respond, install, or evaluate.",
            cheapest_truth_experiment="Wait for already authorized passive external evidence or request one bounded external evaluation action.",
            kill_conditions=["independent NO_DECISION_VALUE", "baseline parity persists across independent evaluators"],
            scale_conditions=["verified payment", "positive profit", "repeatable acquisition"],
            evidence_refs=["v030-waiting", "e2-sent"],
            state="PARKED_WAITING_EXTERNAL_EVIDENCE",
            next_action="WAIT_FOR_GENUINE_EXTERNAL_EVIDENCE_OR_VALID_MATERIAL_WAKE",
        )
    ]
    ledger = EconomicLedger()
    cash = ledger.cash_flow()
    state = EconomicEngineState(
        constitution_id=CONSTITUTION_ID,
        mission_state=mission,
        cash_flow=cash,
        opportunity_count=len(opportunities),
        claim_count=len(claims),
        ledger_event_count=0,
        current_highest_value_hypothesis="Independent external evidence is the bottleneck for any economic claim.",
        current_critical_assumption=opportunities[0].critical_assumption,
        next_cheapest_truth_experiment=opportunities[0].cheapest_truth_experiment,
        current_authority_class=AuthorityClass.A0,
        current_approval_policy=ApprovalPolicy.PER_ACTION,
        current_approval_state="NO_CURRENT_EXTERNAL_OR_FINANCIAL_APPROVAL",
    )
    return {
        "state": state,
        "opportunities": opportunities,
        "claims": claims,
        "evidence": evidence,
        "ledger": ledger,
        "causal_memory": [
            CausalObservation(
                problem="Economic evidence absent",
                context="E2-01, ZERO-INBOUND, V0.30 have no qualified independent positive signal",
                intervention="passive observation and evidence gating",
                observed_outcome="0 KWD verified value",
                alternative_explanation="insufficient exposure, weak offer, or wrong audience",
                control_or_baseline="no promotion without external proof",
                causal_confidence=0.0,
                replication_count=0,
                contradicting_cases=[],
                resulting_policy="park economic scaling until genuine evidence arrives",
            )
        ],
    }


def verify_economic_engine(root: Path) -> dict[str, Any]:
    audit = bootstrap_reality_audit(root)
    evidence = audit["evidence"]
    claims = audit["claims"]
    ledger: EconomicLedger = audit["ledger"]
    evidence_by_id = {item.evidence_id: item for item in evidence}
    claim_results = {claim.claim_id: validate_claim(claim, evidence_by_id) for claim in claims}
    promotion_checks = {level.name: validate_promotion(level, evidence, claims)[0] for level in RealityLevel}
    ledger_ok, ledger_reason = ledger.verify()
    stale = EconomicEvidence("stale-market", "fixture", "2020-01-01T00:00:00+00:00", "STALE", "MARKET_RESPONSE", "THIRD_PARTY", ["demand"], 0.8, "2020-01-02T00:00:00+00:00")
    expired = AuthorityContext(AuthorityClass.A3, "fixture", ApprovalPolicy.PER_ACTION, "expired approval", "2020-01-02T00:00:00+00:00")
    scale = ScaleAssessment(10, 12, 0.1, 0.1, 0, 0, 0, 0.1, True, True)
    checks = {
        "reality_ladder_no_self_promotion": promotion_checks["L0"] and not promotion_checks["L2"] and not promotion_checks["L4"] and not promotion_checks["L7"],
        "proposal_not_demand": claim_results["claim-v030-waiting"][0] is False,
        "cash_profit_liquidity_separated": audit["state"].cash_flow.available_cash == 0 and audit["state"].cash_flow.verified_net_cash_profit == 0,
        "unrealized_asset_excluded": audit["state"].cash_flow.unrealized_estimated_asset_value == 0,
        "stale_evidence_rejected": stale.is_current(_now()) is False,
        "expired_approval_blocked": expired.allows(AuthorityClass.A3) is False,
        "lower_authority_blocks_external_write": audit["state"].current_authority_class == AuthorityClass.A0,
        "owner_activity_not_independent": not any(item.source_type == "MARKET_RESPONSE" and item.independence == "THIRD_PARTY" for item in evidence),
        "ledger_hash_integrity": ledger_ok,
        "scale_blocks_negative_unit_economics": scale.decision() == EconomicFailure.NEGATIVE_UNIT_ECONOMICS.value,
        "security_requires_scope": AuthorityContext(AuthorityClass.A5, "fixture", ApprovalPolicy.PER_ACTION, "financial approval").allows(AuthorityClass.A6) is False,
        "unknown_failure_bounded": EconomicFailure.UNKNOWN_FAILURE.value in {item.value for item in EconomicFailure},
        "wake_does_not_create_authority": audit["state"].current_approval_state == "NO_CURRENT_EXTERNAL_OR_FINANCIAL_APPROVAL",
        "parallel_control_plane_not_created": audit["state"].parallel_control_plane_created is False,
    }
    return {
        "constitution_id": CONSTITUTION_ID,
        "implemented": all(checks.values()),
        "checks": checks,
        "ledger_reason": ledger_reason,
        "claim_results": {key: {"valid": value[0], "errors": value[1]} for key, value in claim_results.items()},
        "promotion_checks": promotion_checks,
    }


def run_bootstrap(root: Path) -> dict[str, Any]:
    audit = bootstrap_reality_audit(root)
    verification = verify_economic_engine(root)
    base = root.resolve() / ".omega" / "zero" / "economic"
    mission_state: EconomicMissionState = audit["state"].mission_state
    payload = {
        "constitution_id": CONSTITUTION_ID,
        "engine_state": _serialize(audit["state"]),
        "mission": _serialize(mission_state),
        "cash_flow": _serialize(audit["state"].cash_flow),
        "opportunities": [_serialize(item) for item in audit["opportunities"]],
        "claims": [_serialize(item) for item in audit["claims"]],
        "evidence": [_serialize(item) for item in audit["evidence"]],
        "ledger": [_serialize(item) for item in audit["ledger"].events],
        "causal_memory": [_serialize(item) for item in audit["causal_memory"]],
        "verification": verification,
        "external_writes": 0,
        "financial_actions": 0,
        "security_actions": 0,
    }
    payload["mission"]["target_remaining_usd"] = mission_state.target_remaining_usd
    payload["engine_state"]["mission_state"]["target_remaining_usd"] = mission_state.target_remaining_usd
    payload["state_hash"] = _hash(payload)
    _write(base / "mission.json", payload["mission"])
    _write(base / "state.json", payload)
    _write(base / "opportunities" / "opp-independent-economic-evidence.json", payload["opportunities"][0])
    _write(base / "claims" / "claim-real-value-zero.json", payload["claims"][0])
    _write(base / "ledger" / "ledger.json", payload["ledger"])
    _write(base / "evidence" / "bootstrap-evidence.json", payload["evidence"])
    _write(base / "reports" / "bootstrap_reality_audit.json", payload)
    return payload


def load_state(root: Path) -> dict[str, Any] | None:
    path = root.resolve() / ".omega" / "zero" / "economic" / "state.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def status(root: Path) -> dict[str, Any]:
    payload = load_state(root)
    if payload is None:
        return {
            "constitution_id": CONSTITUTION_ID,
            "implemented": False,
            "state": "NOT_BOOTSTRAPPED",
            "reality_level": None,
            "verified_net_economic_value_usd": 0.0,
            "target_remaining_usd": TARGET_USD,
        }
    state = payload["engine_state"]
    cash = payload["cash_flow"]
    return {
        "constitution_id": payload["constitution_id"],
        "implemented": payload["verification"]["implemented"],
        "reality_level": state["mission_state"]["reality_level"],
        "verified_net_economic_value_usd": state["mission_state"]["verified_net_economic_value_usd"],
        "target_remaining_usd": TARGET_USD - state["mission_state"]["verified_net_economic_value_usd"],
        "pipeline_value": cash["pipeline_value"],
        "contracted_value": cash["contracted_value"],
        "earned_value": cash["earned_value"],
        "accounts_receivable": cash["accounts_receivable"],
        "settled_value": cash["settled_value"],
        "available_cash": cash["available_cash"],
        "committed_cost": cash["committed_cost"],
        "cash_at_risk": cash["cash_at_risk"],
        "working_capital": cash["working_capital"],
        "current_highest_value_hypothesis": state["current_highest_value_hypothesis"],
        "next_cheapest_truth_experiment": state["next_cheapest_truth_experiment"],
        "authority": state["current_authority_class"],
        "approval": state["current_approval_policy"],
        "approval_state": state["current_approval_state"],
    }


def _serialize(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if hasattr(value, "__dataclass_fields__"):
        return {key: _serialize(item) for key, item in asdict(value).items()}
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    if isinstance(value, dict):
        return {key: _serialize(item) for key, item in value.items()}
    return value
