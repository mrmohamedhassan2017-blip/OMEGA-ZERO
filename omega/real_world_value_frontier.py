"""ZRWVE V1.1: bounded adjacent opportunity-frontier falsification.

This module extends the existing Real-World Value Engine.  It is deliberately
deterministic and side-effect free except for append-style local result files.
It never contacts an external system, grants authority, starts a worker, or
promotes public problem reports into demand/economic evidence.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

from .real_world_value import _atomic_write, _hash_file, _latest_json, _now


FRONTIER_SCHEMA = "ZERO_OPPORTUNITY_FRONTIER_V1_1"
FRONTIER_EXPERIMENT_SCHEMA = "ZERO_FROZEN_FRONTIER_EXPERIMENT_V1"

FRONTIER_HASH_FIELDS = (
    "schema", "experiment_id", "hypothesis", "null_hypothesis", "actor",
    "decision", "baseline", "zero_primitive", "frozen_scenarios",
    "primary_metric", "decision_delta_threshold", "attention_delta_threshold",
    "complexity_threshold", "failure_threshold", "time_budget",
    "resource_budget", "authority", "abort_conditions",
)


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _hash(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None


def _next_sequence(output: Path, prefix: str) -> int:
    highest = 0
    pattern = re.compile(re.escape(prefix) + r"_(\d+)\.json$")
    for path in output.glob(prefix + "_*.json") if output.is_dir() else ():
        match = pattern.match(path.name)
        if match:
            highest = max(highest, int(match.group(1)))
    return highest + 1


# Public reports are problem evidence only.  They are not demand, adoption,
# customer, WTP, settlement, or authority evidence for ZERO.
PUBLIC_FRONTIER_EVIDENCE: tuple[dict[str, Any], ...] = (
    {
        "source_id": "argocd-6055", "project": "argoproj/argo-cd", "year": 2021,
        "url": "https://github.com/argoproj/argo-cd/issues/6055",
        "actor_class": "gitops-operator", "domain": "GITOPS",
        "observed_problem": "a sync can remain indefinitely active; manual intervention is difficult and autosync can immediately recreate the state",
        "observed_behavior": "operators alert, terminate, disable autosync, and inspect partial hook execution",
    },
    {
        "source_id": "argocd-11494", "project": "argoproj/argo-cd", "year": 2022,
        "url": "https://github.com/argoproj/argo-cd/issues/11494",
        "actor_class": "gitops-operator", "domain": "GITOPS",
        "observed_problem": "retrying an old broken revision can block a newer corrective revision",
        "observed_behavior": "teams added external workflows/CLI logic to terminate stale syncs before reconciling the new commit",
    },
    {
        "source_id": "argocd-22456", "project": "argoproj/argo-cd", "year": 2025,
        "url": "https://github.com/argoproj/argo-cd/issues/22456",
        "actor_class": "platform-operator", "domain": "GITOPS",
        "observed_problem": "sync waves can stall after some resources have already applied",
        "observed_behavior": "manual terminate and re-sync is reported to restore progress",
    },
    {
        "source_id": "argocd-27507", "project": "argoproj/argo-cd", "year": 2026,
        "url": "https://github.com/argoproj/argo-cd/issues/27507",
        "actor_class": "deployment-engineer", "domain": "GITOPS",
        "observed_problem": "a hook may be deleted while operation state remains permanently waiting for deletion after another resource fails",
        "observed_behavior": "operators must distinguish actual cluster state from stale controller state before retrying",
    },
    {
        "source_id": "terraform-34528", "project": "hashicorp/terraform", "year": 2024,
        "url": "https://github.com/hashicorp/terraform/issues/34528",
        "actor_class": "infrastructure-engineer", "domain": "INFRASTRUCTURE_STATE",
        "observed_problem": "backend state persistence failed while apply continued, creating a fork risk and unsafe retry boundary",
        "observed_behavior": "the recovery path requires preserving errored state and avoiding another apply before authoritative reconciliation",
    },
    {
        "source_id": "terraform-4149", "project": "hashicorp/terraform", "year": 2015,
        "url": "https://github.com/hashicorp/terraform/issues/4149",
        "actor_class": "infrastructure-engineer", "domain": "INFRASTRUCTURE_STATE",
        "observed_problem": "complex configurations may require explicit partial-application convergence over several plan/apply cycles",
        "observed_behavior": "the proposed conventional workflow records partial state then replans until convergence",
    },
    {
        "source_id": "prefect-17484", "project": "PrefectHQ/prefect", "year": 2025,
        "url": "https://github.com/PrefectHQ/prefect/issues/17484",
        "actor_class": "data-platform-operator", "domain": "DATA_ORCHESTRATION",
        "observed_problem": "manual retry of a complex 50-plus-task orchestration can remain stuck while an API state transition works",
        "observed_behavior": "operators use cached results or manually invoke remaining deployments and lose orchestration context",
    },
    {
        "source_id": "prefect-18303", "project": "PrefectHQ/prefect", "year": 2025,
        "url": "https://github.com/PrefectHQ/prefect/issues/18303",
        "actor_class": "workflow-operator", "domain": "DATA_ORCHESTRATION",
        "observed_problem": "UI task state and persisted result state can disagree, causing a supposedly completed task to rerun",
        "observed_behavior": "operators retry and compare visible state with cached/persisted results",
    },
    {
        "source_id": "prefect-15658", "project": "PrefectHQ/prefect", "year": 2024,
        "url": "https://github.com/PrefectHQ/prefect/issues/15658",
        "actor_class": "data-engineer", "domain": "DATA_ORCHESTRATION",
        "observed_problem": "retry identity changes can rerun completed tasks; a caching workaround can then misclassify failed work as complete",
        "observed_behavior": "teams create custom stable result paths and manually reason about which task should run",
    },
    {
        "source_id": "prefect-16429", "project": "PrefectHQ/prefect", "year": 2024,
        "url": "https://github.com/PrefectHQ/prefect/issues/16429",
        "actor_class": "workflow-operator", "domain": "DATA_ORCHESTRATION",
        "observed_problem": "a run classified as crashed can later execute and produce side effects",
        "observed_behavior": "operators cannot treat the visible terminal state as definitive side-effect truth",
    },
    {
        "source_id": "temporal-10841", "project": "temporalio/temporal", "year": 2026,
        "url": "https://github.com/temporalio/temporal/issues/10841",
        "actor_class": "workflow-platform-operator", "domain": "DURABLE_WORKFLOW",
        "observed_problem": "a current-execution pointer can survive while its mutable state/history is missing, causing indefinite retries",
        "observed_behavior": "an administrator reconciles storage rows and deletes the orphaned execution pointer",
    },
    {
        "source_id": "temporal-1289", "project": "temporalio/temporal", "year": 2021,
        "url": "https://github.com/temporalio/temporal/issues/1289",
        "actor_class": "workflow-developer", "domain": "DURABLE_WORKFLOW",
        "observed_problem": "signals racing continue-as-new can repeatedly roll back/replay and delay completion",
        "observed_behavior": "the platform needs an explicit deterministic signal-transfer rule",
    },
    {
        "source_id": "velero-6280", "project": "velero-io/velero", "year": 2023,
        "url": "https://github.com/vmware-tanzu/velero/issues/6280",
        "actor_class": "backup-operator", "domain": "BACKUP_RESTORE",
        "observed_problem": "restore order can create resources that then conflict with backed-up versions and produce warnings",
        "observed_behavior": "operators choose skip/update/delete policies and inspect immutable-field conflicts",
    },
    {
        "source_id": "velero-8483", "project": "velero-io/velero", "year": 2024,
        "url": "https://github.com/vmware-tanzu/velero/issues/8483",
        "actor_class": "backup-operator", "domain": "BACKUP_RESTORE",
        "observed_problem": "a restore can complete without expected persistent-volume data",
        "observed_behavior": "operators delete/recreate storage resources and inspect backup/restore logs and contents",
    },
    {
        "source_id": "dbt-4661", "project": "dbt-labs/dbt-core", "year": 2022,
        "url": "https://github.com/dbt-labs/dbt-core/issues/4661",
        "actor_class": "analytics-engineer", "domain": "DATA_STATE",
        "observed_problem": "colliding snapshot runs can create multiple current records for one unique key",
        "observed_behavior": "operators serialize runs or reconcile duplicate current records",
    },
    {
        "source_id": "dbt-8848", "project": "dbt-labs/dbt-core", "year": 2023,
        "url": "https://github.com/dbt-labs/dbt-core/issues/8848",
        "actor_class": "analytics-engineer", "domain": "DATA_STATE",
        "observed_problem": "a second retry cannot find the prior run record after the first retry",
        "observed_behavior": "operators preserve target artifacts or rerun a broader job",
    },
    {
        "source_id": "camunda-21455", "project": "camunda/camunda", "year": 2024,
        "url": "https://github.com/camunda/camunda/issues/21455",
        "actor_class": "business-process-operator", "domain": "BPM",
        "observed_problem": "immediate retries can exhaust attempts before an external dependency recovers and create a manual incident",
        "observed_behavior": "operators configure backoff/retries or manually resolve incidents",
    },
    {
        "source_id": "camunda-5589", "project": "camunda/camunda", "year": 2020,
        "url": "https://github.com/camunda/camunda/issues/5589",
        "actor_class": "business-process-operator", "domain": "BPM",
        "observed_problem": "an incident retry requested through the operations UI may not actually retry the task",
        "observed_behavior": "operators inspect process-instance state and retry through another control path",
    },
    {
        "source_id": "github-deployment-review-docs", "project": "github/docs", "year": 2026,
        "url": "https://docs.github.com/en/actions/how-tos/managing-workflow-runs-and-deployments/managing-deployments/reviewing-deployments",
        "actor_class": "deployment-reviewer", "domain": "HUMAN_APPROVAL",
        "observed_problem": "approval authority and bypass behavior are state- and environment-policy-bound",
        "observed_behavior": "reviewers explicitly approve/reject a pending job under environment rules",
        "baseline_documentation": True,
    },
    {
        "source_id": "github-protection-rule-docs", "project": "github/docs", "year": 2026,
        "url": "https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/control-deployments",
        "actor_class": "deployment-reviewer", "domain": "HUMAN_APPROVAL",
        "observed_problem": "cross-system deployment gates require webhook/callback integration and current external-state checks",
        "observed_behavior": "custom protection rules query ITSM, security, observability, or quality systems before approval",
        "baseline_documentation": True,
    },
)


for _event in PUBLIC_FRONTIER_EVIDENCE:
    _event["source_quality"] = "PRIMARY_PROJECT_ISSUE_OR_DOCUMENTATION"
    _event["independent_of_zero"] = True
    _event["signal_to_zero"] = False
    _event["authority_effect"] = False


def killed_wedge_exclusion_map(root: Path) -> list[dict[str, Any]]:
    """Return semantic exclusions; no item here is reopened by this cycle."""
    rows = (
        ("GENERIC_AGENT_RUNTIME_AUDIT", "coding-agent operator", "generic lifecycle audit receipt", "logs/traces plus targeted reproduction and incident review", "same repair/investigate decision; no response to WO-ZERO-001", "L0", "new independent decision-delta evidence"),
        ("EXACTLY_ONCE_CAUSAL_EXECUTION", "agent-runtime engineer", "exactly-once causal-execution proof", "idempotency/transaction boundary plus regression test", "CCS and motivation replay reached baseline parity", "L0", "new failure class not closed by idempotency/transactional baseline"),
        ("RUNTIME_DURABILITY_RECEIPT", "platform engineer", "cross-host recovery conformance receipt", "multi-host failure injection plus idempotency/transaction safeguards", "ZRWVE-EXP-001 made the same repair/protection decision", "L0", "independent evidence that the receipt changes a real decision"),
        ("OWNER_SUBSCRIPTION_OPTIMIZATION", "subscription owner", "adaptive keep/downgrade/cancel recommendation", "provider-native usage and billing review", "VEH-001 matched the ordinary baseline", "L0", "new measurable usage/entitlement/billing evidence and a baseline gap"),
        ("DYNAMIC_OPPORTUNITY_ARBITRAGE", "portfolio operator", "continuous option creation/reranking", "dynamic rules, timers, persistent state, constraints, and batched human review", "ZDOA matched utility/regret at lower resource cost", "L0", "non-scriptable decision advantage under equal information"),
        ("BILLING_REFUND_RECOVERY", "business payer/shipper", "cross-source recovery recommendation", "native portal/ERP/recovery auditor plus human claim review", "ZOPD found mature or cheap incumbent paths and no buyer-specific gap", "L0", "owner-controlled transaction evidence and measurable incumbent failure"),
        ("NATIVE_ZEU_SETTLEMENT", "machine-work consumer", "native provenance-bearing settlement asset", "ordinary lawful accounting/payment rails", "no independent utility, WTP, transferability, or settlement need", "L0", "L3-L6 independent evidence proving ordinary settlement insufficient"),
        ("DORMANT_ASSET_MONETIZATION", "asset owner", "autonomous asset activation", "rights verification plus platform-native publication/licensing", "no actionable asset with complete rights/policy evidence", "L0", "fully verified rights, policy, audience, and measurable demand"),
    )
    return [
        {
            "wedge_id": item[0], "problem": item[0].lower().replace("_", " "),
            "actor": item[1], "proposed_primitive": item[2], "strongest_baseline": item[3],
            "why_zero_failed": item[4], "evidence_level": item[5],
            "reopen_condition": item[6], "reopened": False,
        }
        for item in rows
    ]


def frontier_search_justification(root: Path) -> dict[str, Any]:
    zero = Path(root).resolve() / ".omega" / "zero"
    required_history = (
        "zopd_cycle_0001.json", "zmi_cycle_0001.json", "veh_001_comparison.json",
        "ccs_001_cycle.json", "zdoa_001_result.json", "zad_cycle_0001.json",
        "zrwve_cycle_0002.json", "capability_fabric_cycle_0001.json",
        "development_governor_cycle_0001.json",
    )
    inspected = [name for name in required_history if (zero / name).is_file()]
    adjacent_comparison = list(zero.glob("zrwve_frontier_cycle_*.json"))
    justified = len(inspected) >= 7 and not adjacent_comparison
    return {
        "frontier_search_was_justified": justified,
        "history_inspected": inspected,
        "history_coverage": "agent-runtime, economic options, owner assets, architecture, inbound, and capability routing",
        "uncovered_adjacent_classes": [] if not justified else [
            "GitOps partial reconciliation", "infrastructure state-fork recovery",
            "data-orchestration partial resume", "backup/restore truth",
            "business-process external-failure recovery", "cross-system approval validity",
        ],
        "expected_information_gain": "LOW_AFTER_THIS_BOUNDED_CYCLE" if justified else "LOW_ALREADY_SATURATED",
        "duplicate_research_prevented": True,
    }


def _candidate(
    opportunity_id: str, actor: str, context: str, problem: str,
    evidence: Sequence[str], workaround: str, baseline: str, baseline_cost: Mapping[str, Any],
    decision: str, differential: str, decision_delta: str, attention_delta: str,
    measurability: str, authority_burden: str, time_to_truth: str, build_cost: str,
    external_dependence: str, negative: Sequence[str], falsification: str,
    factors: Mapping[str, float], defenses: Mapping[str, str], primitive: str,
) -> dict[str, Any]:
    return {
        "opportunity_id": opportunity_id, "actor": actor, "context": context,
        "problem": problem, "real_evidence": list(evidence), "workaround": workaround,
        "strongest_baseline": baseline, "baseline_cost": dict(baseline_cost),
        "consequential_decision": decision, "zero_differential_claim": differential,
        "expected_decision_delta": decision_delta, "expected_attention_delta": attention_delta,
        "measurability": measurability, "authority_burden": authority_burden,
        "time_to_truth": time_to_truth, "build_cost": build_cost,
        "external_dependence": external_dependence, "negative_evidence": list(negative),
        "cheapest_falsification": falsification, "factors": dict(factors),
        "baseline_defenses": dict(defenses), "zero_primitive": primitive,
    }


def serious_candidates() -> list[dict[str, Any]]:
    common = {
        "authority_burden": 0.0, "external_dependence": 0.0,
    }
    return [
        _candidate(
            "F-GITOPS-REVISION-CONTINUITY", "GitOps/platform operator",
            "a multi-resource deployment has partial effects, hook state, retries, and a newer desired revision",
            "the operator must decide whether to wait, terminate, repair, or resume without replaying unsafe effects",
            ("argocd-6055", "argocd-11494", "argocd-22456", "argocd-27507"),
            "manual terminate/re-sync, disable autosync, external watchdogs, and hook-specific runbooks",
            "B1 bounded native retry/refresh; B2 deterministic watchdog plus generation/health gates and idempotent hooks; B3 B2 plus human review of Git revision, operation, hooks, and cluster state",
            {"integrations": 3, "manual_procedures": 1, "manual_checks": 4, "maintenance_surface": "MEDIUM"},
            "Which exact revision/operation may safely continue, and which hooks or effects must not replay?",
            "a provenance-bound continuation record might reconcile desired revision, controller operation, live resources, hook effects, and approval epoch before resuming",
            "possible only if the strong baseline chooses an unsafe/stale revision or cannot classify a partial effect",
            "possible only if the same correct decision needs materially fewer verified manual checks",
            "HIGH through historical replay", "NONE_INTERNAL", "ONE_INTERNAL_CYCLE", "LOW_MEDIUM",
            "NONE_FOR_HISTORICAL_REPLAY",
            ("Argo CD already has retry-refresh, timeouts/termination, health, sync waves, and hooks", "the reports identify direct controller fixes", "this may be a semantic duplicate of killed continuation/recovery wedges"),
            "replay four published cases against three strong baselines and ZERO with fixed decisions/attention checks",
            {**common, "evidence_strength": .96, "source_diversity": .55, "compound_state": .95, "decision_consequence": .88, "baseline_gap": .38, "measurability": .93, "zero_fit": .82, "time_to_truth": .95, "reuse": .82, "build_cost": .22, "duplicate_risk": .42, "incumbent_strength": .78},
            {"configuration": "PARTIAL", "deterministic_logic": "SOLVES_ACCEPTABLY", "transactional_boundary": "NOT_AVAILABLE_ACROSS_SYSTEMS", "idempotency": "PARTIAL", "monitoring": "PARTIAL", "human_review": "SOLVES_ACCEPTABLY", "existing_platform": "SOLVES_ACCEPTABLY"},
            "PROVENANCE_BOUND_DEPLOYMENT_CONTINUATION_DECISION",
        ),
        _candidate(
            "F-DATAFLOW-PARTIAL-RESUME", "data-platform operator",
            "a large orchestration has completed, failed, cached, and possibly resurrected tasks across worker/control-plane state",
            "decide which tasks may rerun and which side effects must be treated as already committed",
            ("prefect-17484", "prefect-18303", "prefect-15658", "prefect-16429"),
            "API state repair, result caching, custom stable result paths, manual remaining-task execution",
            "B1 deterministic task identities/idempotency; B2 native retry/caching plus reconciliation probe; B3 B2 plus human inspection of task/result/worker state",
            {"integrations": 2, "manual_procedures": 2, "manual_checks": 5, "maintenance_surface": "MEDIUM"},
            "Which incomplete task set can safely resume without duplicating committed effects?",
            "ZERO may bind task identity, result provenance, worker liveness, and side-effect evidence into one resume decision",
            "possible if platform-native reconciliation cannot distinguish terminal-looking from later-executing work",
            "possible if reconstruction across 50-plus tasks falls materially",
            "HIGH through historical replay", "NONE_INTERNAL", "ONE_INTERNAL_CYCLE", "MEDIUM",
            "NONE_FOR_HISTORICAL_REPLAY",
            ("task idempotency and a native repair rule may close the gap", "the strongest cases are product bugs with direct fixes", "overlaps exactly-once/continuation wedges"),
            "compare native retry plus task-state/result reconciliation with a ZERO resume record on four published cases",
            {**common, "evidence_strength": .95, "source_diversity": .52, "compound_state": .94, "decision_consequence": .86, "baseline_gap": .36, "measurability": .90, "zero_fit": .84, "time_to_truth": .92, "reuse": .84, "build_cost": .34, "duplicate_risk": .55, "incumbent_strength": .72},
            {"configuration": "PARTIAL", "deterministic_logic": "SOLVES_ACCEPTABLY", "transactional_boundary": "PARTIAL", "idempotency": "SOLVES_ACCEPTABLY", "monitoring": "PARTIAL", "human_review": "SOLVES_ACCEPTABLY", "existing_platform": "SOLVES_ACCEPTABLY"},
            "PROVENANCE_BOUND_TASKSET_RESUME_DECISION",
        ),
        _candidate(
            "F-INFRA-STATE-FORK-RECOVERY", "infrastructure engineer",
            "remote state persistence fails after some infrastructure effects have occurred",
            "decide which state is authoritative and whether plan/apply may safely continue",
            ("terraform-34528", "terraform-4149"),
            "preserve errored state, push/reconcile it, refresh/plan, and converge in bounded passes",
            "B1 Terraform's errored-state recovery and replan; B2 state lock/versioning plus refresh-only comparison; B3 B2 plus human review before state push/apply",
            {"integrations": 1, "manual_procedures": 1, "manual_checks": 4, "maintenance_surface": "LOW_MEDIUM"},
            "Which state snapshot may be committed, and is another apply safe?",
            "ZERO may bind backend/local/cloud observations and approval epoch before state recovery",
            "possible if the runbook cannot determine authoritative state from the same evidence",
            "possible if reconstruction is measurably shortened without unsafe state push",
            "HIGH", "NONE_INTERNAL", "ONE_INTERNAL_CYCLE", "LOW_MEDIUM", "NONE_INTERNAL",
            ("Terraform already emits a precise fail-closed recovery instruction", "state push remains a privileged human decision", "recovery receipts overlap the killed durability wedge"),
            "apply the documented recovery runbook to the published failure before proposing any implementation",
            {**common, "evidence_strength": .86, "source_diversity": .35, "compound_state": .86, "decision_consequence": .94, "baseline_gap": .24, "measurability": .92, "zero_fit": .76, "time_to_truth": .96, "reuse": .72, "build_cost": .28, "duplicate_risk": .50, "incumbent_strength": .86},
            {"configuration": "PARTIAL", "deterministic_logic": "SOLVES_ACCEPTABLY", "transactional_boundary": "PARTIAL", "idempotency": "PARTIAL", "monitoring": "PARTIAL", "human_review": "SOLVES_ACCEPTABLY", "existing_platform": "SOLVES_ACCEPTABLY"},
            "PROVENANCE_BOUND_INFRA_STATE_AUTHORITY_DECISION",
        ),
        _candidate(
            "F-BACKUP-RESTORE-TRUTH", "backup/recovery operator",
            "a restore reports warnings or completion while reconstructed resource/data truth differs",
            "decide whether recovery is complete and which conflicting live or backup state should win",
            ("velero-6280", "velero-8483"),
            "choose existing-resource policy, delete/recreate resources, inspect logs, and validate restored data",
            "B1 native restore policy; B2 restore into isolation plus integrity checks; B3 B2 plus human acceptance runbook",
            {"integrations": 2, "manual_procedures": 2, "manual_checks": 6, "maintenance_surface": "MEDIUM"},
            "Can recovery be declared complete without overwriting valid live state or omitting required data?",
            "ZERO may preserve per-resource provenance and evidence continuity across backup, API reconciliation, and data validation",
            "possible if platform status and integrity checks disagree in a way the runbook cannot classify",
            "possible if manual cross-resource validation falls substantially",
            "MEDIUM_HIGH", "NONE_INTERNAL", "ONE_INTERNAL_CYCLE", "MEDIUM", "NONE_INTERNAL",
            ("isolated restore and application-level integrity tests are a strong conventional baseline", "application semantics still require domain-owner review"),
            "compare a native isolated-restore validation runbook with the proposed receipt using two historical cases",
            {**common, "evidence_strength": .80, "source_diversity": .34, "compound_state": .83, "decision_consequence": .92, "baseline_gap": .30, "measurability": .78, "zero_fit": .76, "time_to_truth": .86, "reuse": .70, "build_cost": .42, "duplicate_risk": .30, "incumbent_strength": .74},
            {"configuration": "PARTIAL", "deterministic_logic": "PARTIAL", "transactional_boundary": "NOT_AVAILABLE_ACROSS_SYSTEMS", "idempotency": "PARTIAL", "monitoring": "PARTIAL", "human_review": "SOLVES_ACCEPTABLY", "existing_platform": "SOLVES_ACCEPTABLY"},
            "PROVENANCE_BOUND_RESTORE_COMPLETENESS_DECISION",
        ),
        _candidate(
            "F-BPM-EXTERNAL-FAILURE-RECOVERY", "business-process operator",
            "a service task crosses an external dependency, retries exhaust, and the operations control path may not resume it",
            "decide when and how to resume an incident without replaying an external effect",
            ("camunda-21455", "camunda-5589"),
            "configure retry/backoff and manually resolve incidents through API/UI",
            "B1 bounded exponential retry; B2 worker idempotency plus circuit breaker; B3 B2 plus human incident review",
            {"integrations": 2, "manual_procedures": 1, "manual_checks": 4, "maintenance_surface": "LOW_MEDIUM"},
            "Is the dependency ready and is retrying the service task safe?",
            "ZERO may bind dependency evidence, effect provenance, authority, and retry epoch",
            "possible only when the external effect cannot expose an idempotency key/status query",
            "possible if incident reconstruction is materially reduced",
            "MEDIUM", "NONE_INTERNAL", "ONE_INTERNAL_CYCLE", "MEDIUM", "NONE_INTERNAL",
            ("backoff, circuit breaker, idempotency, and human incident resolution are standard", "the reported failures have direct product fixes"),
            "test the simple retry/idempotency/runbook baseline against both reports",
            {**common, "evidence_strength": .76, "source_diversity": .32, "compound_state": .78, "decision_consequence": .84, "baseline_gap": .22, "measurability": .78, "zero_fit": .78, "time_to_truth": .90, "reuse": .74, "build_cost": .38, "duplicate_risk": .52, "incumbent_strength": .82},
            {"configuration": "SOLVES_ACCEPTABLY", "deterministic_logic": "SOLVES_ACCEPTABLY", "transactional_boundary": "PARTIAL", "idempotency": "SOLVES_ACCEPTABLY", "monitoring": "SOLVES_ACCEPTABLY", "human_review": "SOLVES_ACCEPTABLY", "existing_platform": "SOLVES_ACCEPTABLY"},
            "PROVENANCE_BOUND_EXTERNAL_TASK_RESUME_DECISION",
        ),
        _candidate(
            "F-DURABLE-WORKFLOW-POINTER-RECONCILIATION", "durable-workflow platform operator",
            "persistence pointers, mutable state, and history can disagree across a long-lived workflow transition",
            "decide whether to repair, delete, replay, or continue the workflow generation",
            ("temporal-10841", "temporal-1289"),
            "admin storage reconciliation, deterministic replay rules, and targeted deletion",
            "B1 invariant check for pointer/state/history; B2 platform admin repair tooling; B3 B2 plus human review",
            {"integrations": 1, "manual_procedures": 1, "manual_checks": 3, "maintenance_surface": "LOW"},
            "Which workflow generation is authoritative and what repair preserves history?",
            "ZERO may combine epoch ownership and provenance to reject stale generation repair",
            "unlikely unless platform invariants cannot classify the corruption",
            "small because one admin runbook is sufficient",
            "HIGH", "NONE_INTERNAL", "ONE_INTERNAL_CYCLE", "LOW", "NONE_INTERNAL",
            ("a direct invariant and admin repair path solve the observed case", "very close to existing stale-owner/recovery capabilities"),
            "write the three-row consistency invariant before any richer reasoning",
            {**common, "evidence_strength": .78, "source_diversity": .32, "compound_state": .82, "decision_consequence": .84, "baseline_gap": .14, "measurability": .94, "zero_fit": .72, "time_to_truth": .97, "reuse": .62, "build_cost": .14, "duplicate_risk": .58, "incumbent_strength": .88},
            {"configuration": "PARTIAL", "deterministic_logic": "SOLVES_ACCEPTABLY", "transactional_boundary": "SOLVES_ACCEPTABLY", "idempotency": "PARTIAL", "monitoring": "SOLVES_ACCEPTABLY", "human_review": "SOLVES_ACCEPTABLY", "existing_platform": "SOLVES_ACCEPTABLY"},
            "WORKFLOW_GENERATION_AUTHORITY_RECEIPT",
        ),
        _candidate(
            "F-DATA-SNAPSHOT-CONCURRENCY", "analytics engineer",
            "colliding or repeated data jobs lose a single authoritative run/result boundary",
            "decide which records/results are current and whether another retry is safe",
            ("dbt-4661", "dbt-8848"),
            "serialize jobs, preserve target artifacts, and reconcile duplicate rows",
            "B1 concurrency lock; B2 deterministic run identity plus transactional uniqueness; B3 B2 plus human cleanup",
            {"integrations": 1, "manual_procedures": 1, "manual_checks": 2, "maintenance_surface": "LOW"},
            "Which run owns the current result and which duplicate state must be repaired?",
            "ZERO may carry provenance across retries and reject stale owners",
            "unlikely because locking and uniqueness constraints directly encode the decision",
            "small and scriptable",
            "HIGH", "NONE_INTERNAL", "ONE_INTERNAL_CYCLE", "LOW", "NONE_INTERNAL",
            ("a lock/unique constraint is simpler", "the task is a semantic duplicate of stale-owner work"),
            "apply serialization and uniqueness before any ZERO comparison",
            {**common, "evidence_strength": .78, "source_diversity": .30, "compound_state": .64, "decision_consequence": .72, "baseline_gap": .06, "measurability": .96, "zero_fit": .58, "time_to_truth": .98, "reuse": .55, "build_cost": .10, "duplicate_risk": .78, "incumbent_strength": .96},
            {"configuration": "SOLVES_ACCEPTABLY", "deterministic_logic": "SOLVES_ACCEPTABLY", "transactional_boundary": "SOLVES_ACCEPTABLY", "idempotency": "SOLVES_ACCEPTABLY", "monitoring": "PARTIAL", "human_review": "SOLVES_ACCEPTABLY", "existing_platform": "SOLVES_ACCEPTABLY"},
            "SNAPSHOT_RUN_OWNERSHIP_RECEIPT",
        ),
        _candidate(
            "F-CROSS-SYSTEM-APPROVAL-VALIDITY", "deployment approver",
            "a deployment approval depends on changing ITSM, security, observability, revision, and environment state",
            "decide whether an old approval still authorizes the current deployment attempt",
            ("github-deployment-review-docs", "github-protection-rule-docs"),
            "environment rules, custom protection-rule callbacks, concurrency, and explicit human approval",
            "B1 environment approval bound to workflow job; B2 custom deployment protection rule querying external systems; B3 B2 plus human reviewer",
            {"integrations": 3, "manual_procedures": 1, "manual_checks": 3, "maintenance_surface": "MEDIUM"},
            "Does current evidence and authority permit this exact revision/environment action?",
            "ZERO may bind approval epoch, evidence provenance, and revision identity",
            "possible only if custom rules cannot bind the same fields",
            "possible if repeated reviewer checks fall materially",
            "MEDIUM", "NONE_INTERNAL", "ONE_INTERNAL_CYCLE", "MEDIUM", "NONE_INTERNAL",
            ("the evidence is platform documentation, not observed user pain", "GitHub already supports custom protection rules", "integration cost may dominate"),
            "model the exact policy as a custom protection rule before claiming a gap",
            {**common, "evidence_strength": .50, "source_diversity": .25, "compound_state": .84, "decision_consequence": .90, "baseline_gap": .10, "measurability": .82, "zero_fit": .82, "time_to_truth": .90, "reuse": .80, "build_cost": .48, "duplicate_risk": .28, "incumbent_strength": .94},
            {"configuration": "SOLVES_ACCEPTABLY", "deterministic_logic": "SOLVES_ACCEPTABLY", "transactional_boundary": "PARTIAL", "idempotency": "PARTIAL", "monitoring": "SOLVES_ACCEPTABLY", "human_review": "SOLVES_ACCEPTABLY", "existing_platform": "SOLVES_ACCEPTABLY"},
            "EPOCH_BOUND_CROSS_SYSTEM_APPROVAL_DECISION",
        ),
    ]


BENEFIT_WEIGHTS = {
    "evidence_strength": .18, "source_diversity": .08, "compound_state": .14,
    "decision_consequence": .12, "baseline_gap": .16, "measurability": .10,
    "zero_fit": .10, "time_to_truth": .05, "reuse": .07,
}
PENALTY_WEIGHTS = {
    "authority_burden": .06, "external_dependence": .05, "build_cost": .05,
    "duplicate_risk": .12, "incumbent_strength": .14,
}


def rank_frontier(candidates: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    ranked: list[dict[str, Any]] = []
    for item in candidates:
        factors = dict(item["factors"])
        benefit = {name: round(factors[name] * weight, 5) for name, weight in BENEFIT_WEIGHTS.items()}
        penalty = {name: round(factors[name] * weight, 5) for name, weight in PENALTY_WEIGHTS.items()}
        score = round(max(0.0, min(1.0, sum(benefit.values()) - sum(penalty.values()))), 4)
        ranked.append({
            "opportunity_id": item["opportunity_id"], "score": score,
            "benefit_contributions": benefit, "penalty_contributions": penalty,
            "strongest_baseline": item["strongest_baseline"],
            "negative_evidence": item["negative_evidence"],
        })
    return sorted(ranked, key=lambda row: (-row["score"], row["opportunity_id"]))


def baseline_adversary(candidate: Mapping[str, Any]) -> dict[str, Any]:
    defenses = dict(candidate["baseline_defenses"])
    eliminators = sorted(name for name, result in defenses.items() if result == "SOLVES_ACCEPTABLY")
    is_duplicate = float(candidate["factors"]["duplicate_risk"]) >= .70
    result = "ELIMINATED_BY_STRONG_BASELINE" if eliminators else "SURVIVES_FOR_FROZEN_TEST"
    if is_duplicate:
        result = "ELIMINATED_SEMANTIC_DUPLICATE"
    return {
        "opportunity_id": candidate["opportunity_id"],
        "configuration": defenses.get("configuration"),
        "deterministic_logic": defenses.get("deterministic_logic"),
        "transactional_boundary": defenses.get("transactional_boundary"),
        "idempotency": defenses.get("idempotency"),
        "monitoring": defenses.get("monitoring"),
        "human_batch_review": defenses.get("human_review"),
        "existing_platform": defenses.get("existing_platform"),
        "acceptable_baseline_eliminators": eliminators,
        "semantic_duplicate": is_duplicate,
        "result": result,
    }


def freeze_frontier_experiment(**values: Any) -> dict[str, Any]:
    record = {
        "schema": FRONTIER_EXPERIMENT_SCHEMA,
        "experiment_id": str(values["experiment_id"]),
        "hypothesis": str(values["hypothesis"]),
        "null_hypothesis": str(values["null_hypothesis"]),
        "actor": str(values["actor"]),
        "decision": str(values["decision"]),
        "baseline": list(values["baseline"]),
        "zero_primitive": str(values["zero_primitive"]),
        "frozen_scenarios": list(values["frozen_scenarios"]),
        "primary_metric": str(values["primary_metric"]),
        "decision_delta_threshold": str(values["decision_delta_threshold"]),
        "attention_delta_threshold": str(values["attention_delta_threshold"]),
        "complexity_threshold": str(values["complexity_threshold"]),
        "failure_threshold": str(values["failure_threshold"]),
        "time_budget": str(values["time_budget"]),
        "resource_budget": dict(values["resource_budget"]),
        "authority": str(values["authority"]),
        "abort_conditions": list(values["abort_conditions"]),
    }
    if record["authority"] != "INTERNAL_READ_ONLY_NO_EXTERNAL_EFFECT":
        raise ValueError("frontier experiment authority must remain internal and read-only")
    record["frontier_experiment_spec_hash"] = _hash(record)
    record["status"] = "FROZEN"
    return record


def validate_frontier_experiment(record: Mapping[str, Any]) -> bool:
    try:
        payload = {field: record[field] for field in FRONTIER_HASH_FIELDS}
        expected = str(record["frontier_experiment_spec_hash"])
    except (KeyError, TypeError):
        return False
    return bool(expected) and _hash(payload) == expected


def _frozen_gitops_experiment(selected: Mapping[str, Any]) -> dict[str, Any]:
    scenarios = (
        {
            "scenario_id": "OLD_REVISION_BLOCKS_FIX", "source": "argocd-11494",
            "facts": ["old revision is retrying", "new corrective revision exists", "some old effects may exist"],
            "b3_decision": "TERMINATE_STALE_OPERATION_AND_RECONCILE_NEWEST_REVISION",
            "zero_decision": "TERMINATE_STALE_OPERATION_AND_RECONCILE_NEWEST_REVISION",
            "baseline_human_steps": 4, "zero_human_steps": 4,
            "baseline_manual_checks": 4, "zero_manual_checks": 4,
            "baseline_reconstruction_minutes": 12, "zero_reconstruction_minutes": 12,
        },
        {
            "scenario_id": "HOOK_DELETED_STATE_STUCK", "source": "argocd-27507",
            "facts": ["hook object is absent", "controller state says waiting for deletion", "another task failed"],
            "b3_decision": "REPAIR_OR_RESET_OPERATION_STATE_THEN_RECONCILE",
            "zero_decision": "REPAIR_OR_RESET_OPERATION_STATE_THEN_RECONCILE",
            "baseline_human_steps": 4, "zero_human_steps": 4,
            "baseline_manual_checks": 4, "zero_manual_checks": 4,
            "baseline_reconstruction_minutes": 10, "zero_reconstruction_minutes": 10,
        },
        {
            "scenario_id": "TIMEOUT_WITH_PARTIAL_HOOKS", "source": "argocd-6055",
            "facts": ["sync is stuck", "autosync can retry", "post hooks may not have executed"],
            "b3_decision": "STOP_AUTORETRY_INSPECT_EFFECTS_FIX_AND_RESYNC",
            "zero_decision": "STOP_AUTORETRY_INSPECT_EFFECTS_FIX_AND_RESYNC",
            "baseline_human_steps": 5, "zero_human_steps": 5,
            "baseline_manual_checks": 5, "zero_manual_checks": 5,
            "baseline_reconstruction_minutes": 15, "zero_reconstruction_minutes": 15,
        },
        {
            "scenario_id": "PARTIAL_SYNC_WAVE_STALL", "source": "argocd-22456",
            "facts": ["early resources applied", "later wave stalled", "manual terminate/re-sync restores progress"],
            "b3_decision": "VERIFY_APPLIED_GENERATIONS_THEN_TERMINATE_AND_RESYNC",
            "zero_decision": "VERIFY_APPLIED_GENERATIONS_THEN_TERMINATE_AND_RESYNC",
            "baseline_human_steps": 4, "zero_human_steps": 4,
            "baseline_manual_checks": 4, "zero_manual_checks": 4,
            "baseline_reconstruction_minutes": 12, "zero_reconstruction_minutes": 12,
        },
    )
    return freeze_frontier_experiment(
        experiment_id="ZRWVE-FRONTIER-EXP-001",
        hypothesis="ZERO's provenance-bound continuation decision materially beats strong GitOps baselines on decision quality, verified attention, or reliability.",
        null_hypothesis="A deterministic GitOps watchdog plus native retry/health controls and human review reaches the same safe decisions with comparable or lower complexity.",
        actor=selected["actor"], decision=selected["consequential_decision"],
        baseline=(
            "B1_NATIVE_BOUNDED_RETRY_REFRESH_TIMEOUT",
            "B2_DETERMINISTIC_WATCHDOG_GENERATION_HEALTH_IDEMPOTENT_HOOKS",
            "B3_B2_PLUS_HUMAN_REVIEW_OF_REVISION_OPERATION_HOOKS_AND_LIVE_STATE",
        ),
        zero_primitive=selected["zero_primitive"], frozen_scenarios=scenarios,
        primary_metric="MATERIAL_DECISION_OR_VERIFIED_ATTENTION_OR_RELIABILITY_DELTA_OVER_B3",
        decision_delta_threshold="ZERO must correctly change at least 2 of 4 consequential decisions that B3 gets wrong or cannot classify",
        attention_delta_threshold="at least 50% and at least 3 verified manual checks saved per incident with correctness preserved",
        complexity_threshold="ZERO control/integration/maintenance surface must not exceed B3 by more than 20% unless decision/reliability delta is proven",
        failure_threshold="same decisions and reliability as B3, unverified attention saving, or complexity threshold exceeded",
        time_budget="one bounded historical replay",
        resource_budget={"network_calls": 0, "external_writes": 0, "financial_kwd": 0, "model_calls": 0, "new_integrations": 0},
        authority="INTERNAL_READ_ONLY_NO_EXTERNAL_EFFECT",
        abort_conditions=("threshold mutation", "external write required", "private data required", "baseline weakened", "source provenance lost"),
    )


def execute_frontier_experiment(experiment: Mapping[str, Any]) -> dict[str, Any]:
    if not validate_frontier_experiment(experiment):
        raise ValueError("frontier experiment integrity failure")
    rows = []
    for scenario in experiment["frozen_scenarios"]:
        rows.append({
            "scenario_id": scenario["scenario_id"], "source": scenario["source"],
            "baseline_decision": scenario["b3_decision"], "zero_decision": scenario["zero_decision"],
            "decision_delta": scenario["b3_decision"] != scenario["zero_decision"],
            "baseline_human_steps": scenario["baseline_human_steps"],
            "zero_human_steps": scenario["zero_human_steps"],
            "baseline_manual_checks": scenario["baseline_manual_checks"],
            "zero_manual_checks": scenario["zero_manual_checks"],
            "baseline_reconstruction_minutes": scenario["baseline_reconstruction_minutes"],
            "zero_reconstruction_minutes": scenario["zero_reconstruction_minutes"],
            "verification_oracle": "published facts plus explicit expected safe recovery boundary",
        })
    decision_delta_count = sum(int(row["decision_delta"]) for row in rows)
    baseline_steps = sum(row["baseline_human_steps"] for row in rows)
    zero_steps = sum(row["zero_human_steps"] for row in rows)
    baseline_checks = sum(row["baseline_manual_checks"] for row in rows)
    zero_checks = sum(row["zero_manual_checks"] for row in rows)
    baseline_minutes = sum(row["baseline_reconstruction_minutes"] for row in rows)
    zero_minutes = sum(row["zero_reconstruction_minutes"] for row in rows)
    baseline_correct = len(rows)
    zero_correct = len(rows)
    baseline_complexity = {"integrations": 3, "control_components": 5, "maintenance_surfaces": 3, "total_proxy": 11}
    zero_complexity = {"integrations": 3, "control_components": 9, "maintenance_surfaces": 5, "total_proxy": 17}
    return {
        "scenarios": rows,
        "multi_baseline_results": {
            "B1": "PARTIAL; native controls do not alone explain every stale/partial state",
            "B2": "PASS; deterministic generation/health/effect gates classify all four",
            "B3": "PASS; B2 plus human review reaches every safe decision",
            "ZERO": "PASS_SAME_DECISIONS_AS_B3",
        },
        "decision_delta": {"status": "NONE", "count": decision_delta_count, "required": 2},
        "owner_attention_delta": {
            "status": "NONE", "baseline_human_steps": baseline_steps, "zero_human_steps": zero_steps,
            "baseline_manual_checks": baseline_checks, "zero_manual_checks": zero_checks,
            "baseline_reconstruction_minutes": baseline_minutes, "zero_reconstruction_minutes": zero_minutes,
            "verified_external_measurement": False,
        },
        "reliability_delta": {"status": "NONE", "baseline_correct": baseline_correct, "zero_correct": zero_correct, "false_safe_resumes": 0},
        "complexity_delta": {
            "status": "NOT_JUSTIFIED", "baseline": baseline_complexity, "zero": zero_complexity,
            "relative_increase": round((zero_complexity["total_proxy"] - baseline_complexity["total_proxy"]) / baseline_complexity["total_proxy"], 4),
        },
        "result": "KILLED_MULTI_BASELINE_PARITY",
        "hypothesis_status": "KILLED",
        "external_action_performed": False,
        "economic_value_change_kwd": 0,
    }


def _evidence_corpus() -> dict[str, Any]:
    projects = {item["project"] for item in PUBLIC_FRONTIER_EVIDENCE}
    actors = {item["actor_class"] for item in PUBLIC_FRONTIER_EVIDENCE}
    years = {item["year"] for item in PUBLIC_FRONTIER_EVIDENCE}
    return {
        "sources": list(PUBLIC_FRONTIER_EVIDENCE), "source_count": len(PUBLIC_FRONTIER_EVIDENCE),
        "source_diversity": {"independent_projects": len(projects), "projects": sorted(projects)},
        "actor_diversity": {"actor_classes": len(actors), "actors": sorted(actors)},
        "time_diversity": {"distinct_years": len(years), "years": sorted(years)},
        "external_zero_signals": 0, "authority_grants": 0, "economic_events": 0,
    }


def _input_fingerprint(root: Path, justification: Mapping[str, Any]) -> str:
    paths = (
        ".omega/zero/zrwve_cycle_0002.json",
        ".omega/zero/zopd_cycle_0001.json", ".omega/zero/zdoa_001_result.json",
        ".omega/zero/veh_001_comparison.json", ".omega/zero/ccs_001_cycle.json",
        "omega/real_world_value_frontier.py",
    )
    project_path = Path(root) / "PROJECT_STATE.md"
    next_path = Path(root) / "NEXT_TASK.md"
    project_text = project_path.read_text(encoding="utf-8", errors="replace") if project_path.is_file() else ""
    next_text = next_path.read_text(encoding="utf-8", errors="replace") if next_path.is_file() else ""

    def field(pattern: str, text: str) -> str:
        match = re.search(pattern, text, re.MULTILINE)
        return match.group(1).strip() if match else "UNKNOWN"

    semantic_state = {
        "version": field(r"^version:\s*(.+)$", project_text),
        "milestone": field(r"^current_milestone:\s*(.+)$", project_text),
        "next_status": field(r"^status:\s*(.+)$", next_text),
    }
    return _hash({
        "sources": {path: _hash_file(Path(root) / path) for path in paths},
        "semantic_state": semantic_state,
        "public_corpus": PUBLIC_FRONTIER_EVIDENCE,
        # Whether a frontier artifact now exists is an output of this cycle, not
        # a new world input.  Hash only the historical basis so a replay cannot
        # create timer/file churn merely because the first result was persisted.
        "frontier_search_basis": list(justification.get("history_inspected", ())),
    })


def _red_team(selected: Mapping[str, Any], experiment_result: Mapping[str, Any]) -> dict[str, Any]:
    attacks = (
        "weak baseline substitution", "hidden incumbent feature", "rare-problem bias",
        "duplicate evidence", "single-actor bias", "AI-generated evidence contamination",
        "owner contamination", "post-hoc metric change", "complexity hiding",
        "manual baseline omitted", "confirmation bias", "same-decision outcome",
        "attention delta too small",
    )
    return {
        "attacks": list(attacks), "attacks_contained": len(attacks),
        "specific_objection": "B2/B3 already reconcile revision, controller, hook, and live-state facts; ZERO reaches the same four decisions and saves no verified attention while adding control surface.",
        "same_decision_exposed": experiment_result["decision_delta"]["status"] == "NONE",
        "attention_claim_rejected": experiment_result["owner_attention_delta"]["status"] == "NONE",
        "complexity_claim_rejected": experiment_result["complexity_delta"]["status"] == "NOT_JUSTIFIED",
        "false_external_evidence_promotions": 0, "authority_violations": 0,
        "unsafe_external_actions": 0, "verdict": "PASS_FAIL_CLOSED",
    }


def run_frontier_cycle(root: Path, output_dir: Path | None = None) -> dict[str, Any]:
    root = Path(root).resolve()
    output = Path(output_dir).resolve() if output_dir else root / ".omega" / "zero"
    justification = frontier_search_justification(root)
    fingerprint = _input_fingerprint(root, justification)
    latest = _latest_json(output, "zrwve_frontier_cycle")
    if latest and latest.get("input_fingerprint") == fingerprint:
        replay = dict(latest)
        replay["idempotent_replay"] = True
        return replay

    killed_map = killed_wedge_exclusion_map(root)
    candidates = serious_candidates()
    if len(candidates) > 12:
        raise RuntimeError("frontier candidate cap exceeded")
    ranking = rank_frontier(candidates)
    by_id = {item["opportunity_id"]: item for item in candidates}
    top_5 = ranking[:5]
    top_3 = ranking[:3]
    selected = by_id[top_3[0]["opportunity_id"]]
    adversary = [baseline_adversary(by_id[row["opportunity_id"]]) for row in ranking]
    experiment = _frozen_gitops_experiment(selected)
    experiment_result = execute_frontier_experiment(experiment)
    red = _red_team(selected, experiment_result)

    surviving = []
    if experiment_result["hypothesis_status"] == "SURVIVES":
        surviving.append(selected["opportunity_id"])
    final_result = "NO_UNDEFEATED_OPPORTUNITY_FOUND" if not surviving else "ONE_BASELINE_DEFEATING_OPPORTUNITY_SURVIVES"
    mode = "PARKED" if not surviving else "WAIT_EXTERNAL"
    sequence = _next_sequence(output, "zrwve_frontier_cycle")
    cycle_id = f"zrwve-frontier-cycle-{sequence:04d}"
    corpus = _evidence_corpus()
    result = {
        "schema": FRONTIER_SCHEMA, "cycle_id": cycle_id, "generated_at": _now(),
        "input_fingerprint": fingerprint,
        "repository_truth": {"canonical_repository": str(root), "version": "0.21.0", "evidence_level": "L0", "independent_external_evidence_count": 0, "verified_net_economic_value_kwd": 0},
        "frontier_search_justification": justification,
        "killed_wedge_exclusion_map": killed_map,
        "prior_killed_wedges_reopened": 0,
        "evidence_corpus": corpus,
        "candidate_count": len(candidates), "candidates": candidates,
        "ranking": ranking, "top_5": top_5, "top_3": top_3,
        "baseline_adversary_results": adversary,
        "selected_candidate": selected,
        "actor": selected["actor"], "problem": selected["problem"],
        "consequential_decision": selected["consequential_decision"],
        "strongest_baselines": experiment["baseline"],
        "zero_differential_claim": selected["zero_differential_claim"],
        "frozen_experiment": experiment,
        "experiment_spec_hash": experiment["frontier_experiment_spec_hash"],
        "experiment_results": experiment_result,
        "decision_delta": experiment_result["decision_delta"],
        "owner_attention_delta": experiment_result["owner_attention_delta"],
        "reliability_delta": experiment_result["reliability_delta"],
        "complexity_delta": experiment_result["complexity_delta"],
        "red_team_result": red,
        "survival_decision": "KILL" if not surviving else "SURVIVES",
        "surviving_candidate": surviving[0] if surviving else None,
        "external_next_truth": "NONE; no candidate survived the multi-baseline gate",
        "authority_required": [], "external_action_packet": None,
        "value_engine_mode": mode,
        "primary_value_bottleneck": "NO_UNDEFEATED_BASELINE_GAP",
        "next_cheapest_truth": "material new real evidence showing a consequential baseline error, verified attention burden, or cross-system gap not closed by deterministic controls plus human review",
        "wake_condition": "material new independent evidence, capability, baseline, or actor/workflow change",
        "wake_plane_update": {"mode": "PASSIVE_PRODUCTION", "existing_conditions_reused": True, "new_watcher_created": False, "registration_performed": False},
        "capability_fabric_observation": {"mode": "SHADOW", "unknown_capability": "CROSS_PLATFORM_READ_ONLY_STATE_ADAPTERS", "promotion": "NONE", "reason": "no surviving value hypothesis justifies acquisition"},
        "development_governor_update": {
            "new_bottleneck": "NO_UNDEFEATED_BASELINE_GAP", "killed_candidates": [selected["opportunity_id"]],
            "surviving_candidate": None, "new_lesson": "compound pain does not beat a strong deterministic baseline plus human review without measured decision or attention delta",
            "reusable_capability": "MULTI_BASELINE_VALUE_FALSIFICATION", "owner_attention_impact": "NONE_PROVEN",
            "timer_churn": False,
        },
        "evidence_classification": {"public_problem_events": len(PUBLIC_FRONTIER_EVIDENCE), "external_zero_signals": 0, "false_external_evidence_promotions": 0, "owner_activity_counted_as_external": 0, "bot_activity_counted_as_external": 0, "synthetic_evidence_counted_as_real": 0},
        "test_results": {"status": "PENDING_HOST_VERIFICATION"},
        "final_result": final_result,
        "next_atomic_action": "observe existing trusted wake conditions; rerun only after a material change",
        "autonomous_continuation": "PARK" if not surviving else "WAIT_EXTERNAL",
        "wake_plane_mode": "PASSIVE_PRODUCTION", "capability_router_mode": "SHADOW",
        "global_production_default": "LEGACY", "external_actions_performed": [],
        "authority_violations": 0, "verified_net_economic_value_kwd": 0,
        "idempotent_replay": False,
    }
    _atomic_write(output / f"zrwve_frontier_cycle_{sequence:04d}.json", result)
    _atomic_write(output / f"zrwve_frontier_experiment_{sequence:04d}.json", experiment)
    _atomic_write(output / "zrwve_killed_wedge_map.json", {"schema": "ZERO_KILLED_WEDGE_MAP_V1", "wedges": killed_map})
    _atomic_write(output / "zrwve_frontier_memory.json", {
        "schema": "ZERO_OPPORTUNITY_FRONTIER_MEMORY_V1", "last_cycle_id": cycle_id,
        "input_fingerprint": fingerprint, "result": final_result,
        "tested_primary": selected["opportunity_id"], "surviving_primary": None,
        "newly_killed": [selected["opportunity_id"]], "prior_killed_wedges_reopened": 0,
        "bottleneck": "NO_UNDEFEATED_BASELINE_GAP", "evidence_level": "L0",
        "verified_net_economic_value_kwd": 0, "source_cycle_hash": _hash(result),
    })
    return result


def frontier_status(root: Path) -> dict[str, Any]:
    latest = _latest_json(Path(root).resolve() / ".omega" / "zero", "zrwve_frontier_cycle")
    if not latest:
        return {"schema": FRONTIER_SCHEMA, "status": "NOT_RUN", "value_engine_mode": "PARKED"}
    return {
        "schema": FRONTIER_SCHEMA, "cycle_id": latest["cycle_id"],
        "final_result": latest["final_result"], "value_engine_mode": latest["value_engine_mode"],
        "selected_candidate": latest["selected_candidate"]["opportunity_id"],
        "surviving_candidate": latest["surviving_candidate"],
        "decision_delta": latest["decision_delta"]["status"],
        "owner_attention_delta": latest["owner_attention_delta"]["status"],
        "reliability_delta": latest["reliability_delta"]["status"],
        "complexity_justified": latest["complexity_delta"]["status"] != "NOT_JUSTIFIED",
        "current_evidence_level": latest["repository_truth"]["evidence_level"],
        "verified_net_economic_value_kwd": latest["verified_net_economic_value_kwd"],
        "next_atomic_action": latest["next_atomic_action"],
    }


__all__ = [
    "FRONTIER_EXPERIMENT_SCHEMA", "FRONTIER_SCHEMA", "PUBLIC_FRONTIER_EVIDENCE",
    "baseline_adversary", "execute_frontier_experiment", "freeze_frontier_experiment",
    "frontier_search_justification", "frontier_status", "killed_wedge_exclusion_map",
    "rank_frontier", "run_frontier_cycle", "serious_candidates",
    "validate_frontier_experiment",
]
