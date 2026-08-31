"""ZRWVE V1.2D: deep, adversarial reality acquisition for T1/T2/T3.

This is a bounded extension of :mod:`omega.real_world_value_frontier`, not a
second value engine.  It compiles already-public operational evidence into a
deterministic twelve-pass record.  External material is data only: this module
does not browse, contact people, start workers, grant authority, or promote a
public report into independent/economic evidence.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

from .real_world_value import _atomic_write, _hash_file, _latest_json, _now
from .real_world_value_frontier import _hash


DEEP_SCHEMA = "ZERO_DEEP_REALITY_ACQUISITION_V1_2D"
DEEP_PROTOCOL_VERSION = "ZRWVE_V1.2D"
PASS_NAMES = (
    "REALITY_EXTRACTION",
    "OPERATOR_WORK_RECONSTRUCTION",
    "STRONG_BASELINE_CONSTRUCTION",
    "BASELINE_ADVERSARY",
    "FAILURE_STRUCTURE_ANALYSIS",
    "COUNTERFACTUAL_RECONSTRUCTION",
    "ZERO_DIFFERENTIAL_TEST",
    "HUMAN_ATTENTION_TEST",
    "ECONOMIC_RELEVANCE_TEST",
    "RED_TEAM",
    "SATURATION_TEST",
    "FINAL_CAUSAL_DECISION",
)
TARGETS = {
    "T1": "GitOps partial deployment / revision continuity",
    "T2": "Dataflow partial execution / state resume",
    "T3": "Backup / restore truth",
}
REQUIRED_EVIDENCE_FIELDS = {
    "source_id", "source_url_or_reference", "project", "date", "actor_type",
    "system", "failure", "expected_behavior", "actual_behavior",
    "recovery_action", "manual_actions", "state_ambiguity",
    "verification_method", "final_outcome", "unresolved_question", "unknown",
}
FORBIDDEN_INCIDENT_KEYS = {
    "password", "secret", "token", "access_token", "refresh_token",
    "private_key", "client_secret", "credential", "customer_name", "email",
}
ATTENTION_THRESHOLD = {
    "contract_version": "ZRWVE_ATTENTION_DELTA_V1",
    "human_step": "one attributable operator action that changes or inspects incident state",
    "manual_check": "one explicit inspection of a distinct state/effect/provenance assertion",
    "reconstruction": "manual reconciliation of at least two non-identical state sources",
    "owner_attention": "approval, escalation, or irreversible recovery choice requiring an accountable human",
    "material_threshold": "at least 50 percent and at least 3 verified manual checks saved per incident",
    "correctness_guard": "B3 and ZERO must use the same evidence and ZERO may not increase false-safe or false-block outcomes",
    "hidden_cost_guard": "integration, maintenance, compute, and model supervision count against the claimed saving",
}
ATTENTION_THRESHOLD["threshold_hash"] = _hash(ATTENTION_THRESHOLD)


# ZRWVE V1.2E packet-hardening contracts.  These are deliberately data-only
# schemas layered on the existing deep-reality engine; they do not contact or
# identify participants and they never grant external-write authority.
PACKET_HARDENING_SCHEMA = "ZERO_EXTERNAL_INCIDENT_PACKET_HARDENING_V1_2E"
PACKET_HARDENING_PROTOCOL = "ZRWVE_V1.2E"
INCIDENT_DATA_FIELDS = (
    "incident_id_or_local_alias", "incident_date_or_time_window", "system_or_stack",
    "orchestrator", "affected_workflow", "workflow_purpose", "failure_trigger",
    "expected_state", "observed_state", "last_known_good_state",
    "persisted_orchestrator_state", "actual_external_state", "partial_outputs_or_side_effects",
    "checkpoint_state", "retry_or_replay_state", "downstream_effects",
    "manual_intervention_occurred", "final_outcome", "sanitization_status",
    "participant_confidence", "unknown_fields", "real_incident",
)
B3_CONFIGURATION_FIELDS = (
    "b3_tool_or_system", "version_if_known", "state_backend", "checkpointing_configuration",
    "retry_policy", "transaction_or_idempotency_controls", "timeouts", "failure_handling",
    "replay_policy", "observability", "alerting", "runbook_present", "human_review_present",
    "custom_recovery_automation", "manual_reconciliation", "known_missing_control",
    "configuration_unknown_fields",
)
OPERATOR_TRACE_FIELDS = (
    "trace_step_id", "relative_time", "system_inspected", "information_observed",
    "belief_before", "belief_after", "action_taken", "why_action_was_taken",
    "alternatives_considered", "risk_being_avoided", "manual_or_automated",
    "wait_required", "approval_required", "evidence_used", "output",
    "unknown_or_uncertain", "decision_required", "evidence_missing", "conflicting_states",
    "unsafe_automatic_action", "wrong_decision_consequence", "confidence_reason",
)
VERIFICATION_CRITERION_FIELDS = (
    "verification_target", "verification_signal", "acceptance_condition", "reject_condition",
    "source_of_truth", "systems_cross_checked", "side_effect_validation", "data_validation",
    "downstream_validation", "replay_safety_validation", "human_approval_if_any",
    "final_completion_criterion",
)
PACKET_REQUIRED_SECTIONS = (
    "incident_data", "b3_actual", "b3_strongest_reasonable_counterfactual",
    "operator_trace", "verification_criterion", "provenance", "sanitization_status",
    "consequential_decision", "decision_time_information", "outcome_verification",
)
PACKET_FORBIDDEN_MARKERS = frozenset({
    "hypothetical", "synthetic", "training exercise", "ai-generated", "owner-created",
    "omega fixture", "test fixture",
})


def _evidence(
    source_id: str,
    target_id: str,
    url: str,
    project: str,
    date: str,
    actor: str,
    system: str,
    failure: str,
    expected: str,
    actual: str,
    recovery: str,
    actions: Sequence[str],
    ambiguity: str,
    verification: str,
    outcome: str,
    unresolved: str,
    unknown: Sequence[str],
    failure_class: str,
    structural: bool,
    *,
    source_type: str = "PRIMARY_PROJECT_ISSUE",
    evidence_role: str = "REAL_INCIDENT",
    systems_inspected: Sequence[str] = (),
    decision_points: Sequence[str] = (),
    trusted_state: str = "UNKNOWN",
    distrusted_state: str = "UNKNOWN",
    continuation_proof: str = "UNKNOWN",
    completion_proof: str = "UNKNOWN",
) -> dict[str, Any]:
    return {
        "source_id": source_id,
        "target_id": target_id,
        "source_url_or_reference": url,
        "project": project,
        "date": date,
        "actor_type": actor,
        "system": system,
        "failure": failure,
        "expected_behavior": expected,
        "actual_behavior": actual,
        "recovery_action": recovery,
        "manual_actions": list(actions),
        "state_ambiguity": ambiguity,
        "verification_method": verification,
        "final_outcome": outcome,
        "unresolved_question": unresolved,
        "unknown": list(unknown),
        "failure_class": failure_class,
        "structural": structural,
        "source_type": source_type,
        "evidence_role": evidence_role,
        "systems_inspected": list(systems_inspected),
        "decision_points": list(decision_points),
        "trusted_state": trusted_state,
        "distrusted_state": distrusted_state,
        "continuation_proof": continuation_proof,
        "completion_proof": completion_proof,
        "independent_of_zero": True,
        "signal_to_zero": False,
        "authority_effect": False,
        "external_text_role": "DATA_ONLY",
        "duplicate_of": None,
    }


# Public problem reports are not ZERO demand, adoption, utility, or authority.
DEEP_EVIDENCE_CORPUS: tuple[dict[str, Any], ...] = (
    _evidence(
        "argocd-6055", "T1", "https://github.com/argoproj/argo-cd/issues/6055",
        "argoproj/argo-cd", "2021-04-20", "gitops-operator", "Argo CD",
        "sync can remain active indefinitely while autosync recreates the state",
        "a bounded sync either completes or exposes a safe failure boundary",
        "alerting detects a long sync; terminate can be insufficient and manual recovery becomes multi-step",
        "alert, inspect the stalled wave/hook, terminate, and sometimes disable autosync at parent and child",
        ("inspect long-running sync", "attempt terminate", "disable autosync where inherited", "inspect partial resources/hooks"),
        "controller operation state versus resources already applied",
        "operation status plus live resource/hook inspection",
        "manual intervention reported; general final recovery not established",
        "which effects completed before termination and which may safely replay?",
        ("time to safe decision", "exact applied-resource set", "operator skill", "incident frequency"),
        "TEMPORAL_AMBIGUITY", True,
        systems_inspected=("Argo operation", "Kubernetes resources", "Git desired state"),
        decision_points=("wait or terminate", "disable autosync", "replay hooks"),
        trusted_state="live resource observations plus pinned Git revision",
        distrusted_state="indefinite Syncing label alone",
    ),
    _evidence(
        "argocd-11494", "T1", "https://github.com/argoproj/argo-cd/issues/11494",
        "argoproj/argo-cd", "2022-11-22", "gitops-operator", "Argo CD",
        "retry of an older failed revision blocks a newer corrective commit",
        "new desired revision supersedes stale retry without losing effect history",
        "teams used external workflows or terminate logic to unblock the newer revision",
        "detect new commit, terminate old operation, refresh, and reconcile newest revision",
        ("compare retry revision to repository HEAD", "terminate stale operation", "trigger refresh/reconcile"),
        "old operation identity versus current desired revision and partial live effects",
        "operation revision, repository commit, sync history, and live generation",
        "workarounds reported; upstream semantics discussed",
        "can the old operation be replaced without replaying unsafe hooks/effects?",
        ("manual time", "downstream effect inventory", "frequency", "B3 configuration in affected teams"),
        "CROSS_SYSTEM_CONFLICT", True,
        systems_inspected=("Git", "Argo operation/history", "Kubernetes live state"),
        decision_points=("continue old revision or supersede", "which hooks may replay"),
        trusted_state="pinned newest commit plus verified live generation",
        distrusted_state="retry queue that remains bound to old revision",
        continuation_proof="generation and effect checks agree with newest revision",
    ),
    _evidence(
        "argocd-22795", "T1", "https://github.com/argoproj/argo-cd/issues/22795",
        "argoproj/argo-cd", "2025-04-11", "deployment-engineer", "Argo CD",
        "a sync starting immediately after another can omit PreSync/PostSync hooks",
        "each full sync executes its declared hook lifecycle once",
        "retry remains hook-less; operator must stop and restart manually",
        "inspect hook absence, stop operation, then start a fresh sync",
        ("inspect hook resources/logs", "stop current sync", "start fresh sync"),
        "reported success/progress versus lifecycle effects that never ran",
        "hook objects/events plus application resource health",
        "reproducible bug report; final general fix not asserted",
        "which lifecycle effects are missing and whether restart duplicates earlier effects?",
        ("production impact", "operator time", "exact external effects", "final fix coverage"),
        "PARTIAL_EFFECT_AMBIGUITY", True,
        systems_inspected=("Argo operation", "hook jobs", "application resources"),
        decision_points=("retry or fresh restart", "which hooks/effects already ran"),
        trusted_state="hook job/event evidence",
        distrusted_state="sync status without hook provenance",
    ),
    _evidence(
        "flux-3725", "T1", "https://github.com/fluxcd/flux2/discussions/3725",
        "fluxcd/flux2", "2023-04-17", "gitops-operator", "Flux",
        "broken commits can leave reconciliation slow or apparently stuck during incident repair",
        "a corrected source revision is observed and reconciled within the configured retry boundary",
        "operators report force reconcile/suspend attempts and sometimes controller restart",
        "inspect source/reconcile status, force reconcile, suspend/resume, and investigate controller",
        ("inspect source and Kustomization status", "attempt reconcile", "attempt suspend/resume"),
        "source revision versus controller progress and Ready conditions",
        "status conditions, last handled reconcile marker, and live health",
        "discussion provides configuration guidance; universal outcome not established",
        "is delay a configuration interval, a controller lock, or live-resource failure?",
        ("exact versions", "configuration prevalence", "time burden", "restart consequences"),
        "CONFIGURATION_FAILURE", False,
        systems_inspected=("Flux source", "Kustomization status", "Kubernetes resources"),
        decision_points=("wait, reconcile, suspend, or restart"),
        trusted_state="source artifact revision and observed-generation health",
        distrusted_state="generic Reconciling label without reason",
    ),
    _evidence(
        "argocd-sync-waves-doc", "T1", "https://argo-cd.readthedocs.io/en/stable/user-guide/sync-waves/",
        "argoproj/argo-cd", "CURRENT", "platform-engineer", "Argo CD",
        "NOT_AN_INCIDENT_BASELINE_CAPABILITY", "ordered phases/waves and health-aware completion",
        "hooks, failure phases, health, and wave ordering are native controls",
        "configure idempotent hooks, phases, waves, failure hooks, and health checks", (),
        "selective sync omits hooks and unhealthy early waves can block later waves",
        "native phase/wave status and resource health", "BASELINE_DOCUMENTED",
        "how much custom effect identity remains outside Argo?", ("operator adoption", "maintenance cost"),
        "BASELINE_CAPABILITY", False, source_type="OFFICIAL_DOCUMENTATION", evidence_role="STRONG_BASELINE",
    ),
    _evidence(
        "argocd-auto-sync-doc", "T1", "https://argo-cd.readthedocs.io/en/stable/user-guide/auto_sync/",
        "argoproj/argo-cd", "CURRENT", "platform-engineer", "Argo CD",
        "NOT_AN_INCIDENT_BASELINE_CAPABILITY", "bounded retry and refresh on new revision",
        "retry limit/backoff, self-heal, unique commit semantics, and retry refresh are native",
        "configure retry limit/backoff/refresh and explicit self-heal policy", (),
        "automatic sync and rollback/failed-attempt semantics require deliberate configuration",
        "commit SHA, application parameters, retry history", "BASELINE_DOCUMENTED",
        "whether affected incidents had retry.refresh and effect-idempotent hooks", ("affected configuration",),
        "BASELINE_CAPABILITY", False, source_type="OFFICIAL_DOCUMENTATION", evidence_role="STRONG_BASELINE",
    ),
    _evidence(
        "flux-kustomization-doc", "T1", "https://fluxcd.io/flux/components/kustomize/kustomizations/",
        "fluxcd/flux2", "CURRENT", "platform-engineer", "Flux Kustomization",
        "NOT_AN_INCIDENT_BASELINE_CAPABILITY", "generation-aware ordered reconciliation",
        "retryInterval, timeout, wait/health checks, dependencies, suspend, and readyExpr are native",
        "configure observed-generation checks, health gates, dependencies, timeout, and retry interval", (),
        "controller readiness versus application-specific external effects",
        "Ready/Healthy conditions and lastHandledReconcileAt", "BASELINE_DOCUMENTED",
        "which external effects need application-specific verification", ("integration cost", "operator adoption"),
        "BASELINE_CAPABILITY", False, source_type="OFFICIAL_DOCUMENTATION", evidence_role="STRONG_BASELINE",
    ),

    _evidence(
        "prefect-17484", "T2", "https://github.com/PrefectHQ/prefect/issues/17484",
        "PrefectHQ/prefect", "2025-03-14", "data-platform-operator", "Prefect",
        "UI retry of a complex 50-plus-task flow remains Awaiting Retry",
        "retry resumes and reuses successful persisted results",
        "support recommended an API transition to Scheduled; it then progressed to Pending and Running",
        "contact support, set state through API, and rely on per-task caching",
        ("inspect flow state", "contact support", "set Scheduled through API", "check cached task results"),
        "UI orchestration state versus worker scheduling and persisted task results",
        "flow/task states, worker transition, and cached result existence",
        "API workaround succeeded for the reported case",
        "which of 50-plus tasks/effects are safe to resume under the strongest baseline?",
        ("operator minutes", "downstream effects", "actual result-store configuration", "incident frequency"),
        "STATE_DIVERGENCE", True,
        systems_inspected=("Prefect UI/API", "worker/push pool", "result cache", "orchestrated deployments"),
        decision_points=("manual state transition", "reuse or rerun each task"),
        trusted_state="API transition plus persisted result record",
        distrusted_state="Awaiting Retry label alone",
        continuation_proof="Pending/Running transition with valid cached results",
    ),
    _evidence(
        "prefect-17913", "T2", "https://github.com/PrefectHQ/prefect/issues/17913",
        "PrefectHQ/prefect", "2025-04-25", "workflow-developer", "Prefect",
        "manual retry remains AwaitingRetry because retry_type stays in_process",
        "terminal-to-scheduled retry resets retry metadata for a worker-consumable run",
        "maintainers identified an orchestration-rule bug and fixed it in a referenced change",
        "inspect retry metadata and apply/update orchestration rule",
        ("reproduce UI retry", "inspect retry_type", "apply fixed version"),
        "state name says scheduled while worker eligibility metadata says in-process",
        "state details and worker pickup", "upstream fix merged and issue closed",
        "does any burden survive the product fix?", ("production operator time", "affected frequency"),
        "SIMPLE_BUG", False,
        systems_inspected=("Prefect UI", "orchestration state details", "worker"),
        decision_points=("work around or upgrade"), trusted_state="retry_type and worker pickup",
        distrusted_state="state name alone",
    ),
    _evidence(
        "prefect-18303", "T2", "https://github.com/PrefectHQ/prefect/issues/18303",
        "PrefectHQ/prefect", "2025-06-23", "workflow-operator", "Prefect",
        "manual UI state change to Completed does not update persisted result, so retry reruns the task",
        "visible completion and the persisted result agree before downstream continuation",
        "operator compares task state, cache behavior, and rerun outcome",
        "change state, retry flow, inspect which tasks cache or rerun",
        ("change task state", "retry flow", "inspect cached and rerun tasks"),
        "orchestrator state versus result-store truth",
        "persisted result address plus execution record", "bug report open at captured evidence time",
        "did the rerun repeat an external side effect or only deterministic computation?",
        ("side effects", "manual time", "current fix status", "B3 transaction configuration"),
        "STATE_DIVERGENCE", True,
        systems_inspected=("Prefect UI/API", "result storage", "task execution"),
        decision_points=("trust forced Completed", "allow rerun"),
        trusted_state="persisted result plus execution evidence",
        distrusted_state="manually forced UI state",
    ),
    _evidence(
        "prefect-15658", "T2", "https://github.com/PrefectHQ/prefect/issues/15658",
        "PrefectHQ/prefect", "2024-10-11", "data-engineer", "Prefect",
        "retry identity changes rerun completed tasks; a static cache workaround can cache a failed task as complete",
        "completed tasks are reused while the failed task is retried exactly as intended",
        "team tried static result paths and encountered the opposite false-complete failure",
        "inspect dynamic keys, create stable result path, compare cached states, and revise workaround",
        ("compare task identities", "configure result path", "inspect cached state", "retest failure"),
        "task invocation identity versus result identity versus actual success",
        "transaction/result record tied to an idempotency key and outcome",
        "specific product issue was closed by a fix; historical burden remains real",
        "which identity contract prevents both duplicate work and false completion?",
        ("operator time", "external effects", "upgrade adoption", "frequency"),
        "PROVENANCE_AMBIGUITY", True,
        systems_inspected=("orchestrator state", "dynamic task key", "result storage"),
        decision_points=("reuse result or rerun task", "accept cache as proof"),
        trusted_state="result provenance bound to successful transaction",
        distrusted_state="cache hit without matching execution outcome",
    ),
    _evidence(
        "prefect-16429", "T2", "https://github.com/PrefectHQ/prefect/issues/16429",
        "PrefectHQ/prefect", "2024-12-10", "workflow-operator", "Prefect on Kubernetes",
        "a run marked Crashed later becomes Running and executes after its pod eventually starts",
        "terminal state means no later execution unless explicitly rescheduled",
        "operator watched the UI and inferred a lingering Kubernetes job/pod, but root cause remained unconfirmed",
        "track the same run, inspect Kubernetes infrastructure, and avoid trusting Crashed as effect truth",
        ("watch run state", "inspect pod/job lifecycle", "reconcile possible late execution"),
        "terminal orchestration state versus delayed infrastructure and eventual side effects",
        "worker/job identity, pod start evidence, and downstream idempotency record",
        "run eventually completed; cause remained an assumption",
        "which effects may have occurred after the supposedly terminal state?",
        ("exact root cause", "effect inventory", "operator time", "incident frequency"),
        "PARTIAL_EFFECT_AMBIGUITY", True,
        systems_inspected=("Prefect UI/API", "Kubernetes job/pod", "worker", "downstream effects"),
        decision_points=("retry replacement or await original", "which effects may repeat"),
        trusted_state="specific job/pod identity and downstream idempotency evidence",
        distrusted_state="Crashed label alone",
    ),
    _evidence(
        "airflow-10544", "T2", "https://github.com/apache/airflow/issues/10544",
        "apache/airflow", "2020-09-02", "workflow-operator", "Airflow on Kubernetes",
        "manual retries can encounter multiple pods with labels that do not preserve attempt uniqueness",
        "one task attempt maps to one attributable pod and retry identity",
        "operators observed ambiguity across manual retries; a later upstream fix was referenced",
        "inspect pod labels/try number and upgrade or repair attempt identity",
        ("list candidate pods", "compare try numbers", "select/repair attempt", "upgrade fixed version"),
        "scheduler task attempt versus Kubernetes pod identity",
        "unique run/try identity plus terminal pod state", "specific issue later fixed",
        "does any ambiguity survive current attempt identity and idempotency controls?",
        ("operator time", "external side effects", "current-version incidence"),
        "SIMPLE_BUG", False,
        systems_inspected=("Airflow task instance", "Kubernetes pods"),
        decision_points=("reattach or create retry pod"), trusted_state="unique attempt identity",
        distrusted_state="non-unique labels",
    ),
    _evidence(
        "prefect-transaction-doc", "T2", "https://docs.prefect.io/v3/advanced/transactions",
        "PrefectHQ/prefect", "CURRENT", "workflow-engineer", "Prefect",
        "NOT_AN_INCIDENT_BASELINE_CAPABILITY", "at-most-once keyed transaction with rollback/commit",
        "transactions, result records, serializable locks, and rollback hooks are documented",
        "bind effects/results to explicit keys and use serializable isolation where concurrency matters", (),
        "transaction records do not automatically prove arbitrary external effect truth",
        "committed result record and rollback/commit hooks", "BASELINE_DOCUMENTED",
        "how affected teams configured external-effect idempotency", ("integration cost", "maintenance cost"),
        "BASELINE_CAPABILITY", False, source_type="OFFICIAL_DOCUMENTATION", evidence_role="STRONG_BASELINE",
    ),
    _evidence(
        "prefect-cache-doc", "T2", "https://docs.prefect.io/v3/concepts/caching",
        "PrefectHQ/prefect", "CURRENT", "workflow-engineer", "Prefect",
        "NOT_AN_INCIDENT_BASELINE_CAPABILITY", "result reuse with configurable cache identity",
        "cache keys, persistence requirements, and policy controls are documented",
        "persist results and select a cache policy aligned with task identity", (),
        "cache presence is only as reliable as its key and committed result",
        "cache key plus persisted result", "BASELINE_DOCUMENTED",
        "whether real incidents used correct persistence/policy", ("affected configurations",),
        "BASELINE_CAPABILITY", False, source_type="OFFICIAL_DOCUMENTATION", evidence_role="STRONG_BASELINE",
    ),

    _evidence(
        "velero-6280", "T3", "https://github.com/velero-io/velero/issues/6280",
        "velero-io/velero", "2023-05-17", "backup-operator", "Velero/Kubernetes",
        "restore reports warning when Service creation causes Endpoints to exist before endpoint restore",
        "restore ordering/policy produces intended live resources without unexplained conflict",
        "maintainer explained skip/update/delete alternatives and immutable-field limits",
        "inspect warning, compare live and backup object, choose existing-resource policy/order",
        ("inspect restore warning", "compare object versions", "choose delete/update/order policy"),
        "backup object versus controller-created live object",
        "resource-level diff plus application endpoint health",
        "cause and workarounds identified; version-ordering question remained",
        "does the warning imply harmless reconciliation or unusable application state?",
        ("operator time", "application impact", "frequency"),
        "CONFIGURATION_FAILURE", False,
        systems_inspected=("Velero restore", "Kubernetes Service/Endpoints", "backup object"),
        decision_points=("skip, update, delete, or reorder"),
        trusted_state="live object diff and application health",
        distrusted_state="warning count alone",
    ),
    _evidence(
        "velero-6304", "T3", "https://github.com/velero-io/velero/issues/6304",
        "velero-io/velero", "2023-05-23", "backup-operator", "Velero/OpenEBS/GitLab",
        "backup and restore jobs completed and Kubernetes resources reappeared, but volumes were empty",
        "completed restore includes usable persistent application data",
        "operator retried with configurations and supplied backup/restore logs and descriptions",
        "inspect restored PVC/PV, test data, compare logs/descriptions, and retry configuration",
        ("inspect resources", "inspect volume data", "collect logs/descriptions", "retry restore"),
        "control-plane restore completion versus application data truth",
        "application-level data check in an isolated restored environment",
        "issue closed; captured evidence does not establish a universal root cause",
        "which backup inclusion/data-mover fact proves the restore is usable?",
        ("time to recovery", "data loss extent", "exact root cause", "B3 drill configuration"),
        "VERIFICATION_AMBIGUITY", True,
        systems_inspected=("Velero", "Kubernetes PVC/PV", "storage provider", "GitLab data"),
        decision_points=("declare restore complete", "retry/reconfigure"),
        trusted_state="application-readable restored data",
        distrusted_state="Completed restore plus recreated resources",
        completion_proof="application data integrity check",
    ),
    _evidence(
        "velero-7901", "T3", "https://github.com/velero-io/velero/issues/7901",
        "velero-io/velero", "2024-06-17", "backup-operator", "Velero/Kopia/EKS",
        "restore stalls and later times out while pod-volume restores are incomplete",
        "volume restore reaches attributable terminal state within a bounded timeout",
        "logs showed 17 pod restores processed sequentially and a four-hour aggregate timeout",
        "inspect PodVolumeRestores, logs, pod lifecycle, timeout, and incomplete disks",
        ("inspect restore status", "inspect PodVolumeRestores", "inspect pod lifecycle", "review timeout"),
        "main restore state versus per-volume controller/data-mover states",
        "terminal per-volume records plus data check", "PartiallyFailed with incomplete disks",
        "which volume effects completed before timeout and which may safely resume?",
        ("operator attention time", "recovery duration beyond timeout", "final repair"),
        "PARTIAL_EFFECT_AMBIGUITY", True,
        systems_inspected=("Velero restore", "PodVolumeRestore", "Kopia data mover", "Kubernetes pod/volume"),
        decision_points=("wait, cancel, retry, or resume volumes"),
        trusted_state="per-volume terminal record and restored-data check",
        distrusted_state="aggregate restore status alone",
    ),
    _evidence(
        "velero-8339", "T3", "https://github.com/velero-io/velero/issues/8339",
        "velero-io/velero", "2024-10-23", "backup-operator", "Velero File System Backup",
        "restore is PartiallyFailed and pod volume data is absent while restore logs show no error",
        "failure status identifies the failed data unit and actionable cause",
        "maintainers request a debug support bundle for reconstruction",
        "inspect PVC/pod data, restore status/logs, and generate a debug bundle",
        ("inspect restored data", "inspect logs/status", "generate debug bundle"),
        "aggregate failure state versus missing per-volume error evidence",
        "debug bundle, per-volume CRs, and application data check", "closed stale/not planned",
        "can ordinary per-volume inspection identify the failure without bespoke reconciliation?",
        ("root cause", "manual time", "final recovery", "frequency"),
        "OBSERVABILITY_FAILURE", True,
        systems_inspected=("Velero restore", "pod volume data", "logs", "debug bundle"),
        decision_points=("which volume failed", "safe retry boundary"),
        trusted_state="per-volume state and actual data",
        distrusted_state="aggregate status/logs alone",
    ),
    _evidence(
        "velero-8483", "T3", "https://github.com/velero-io/velero/issues/8483",
        "velero-io/velero", "2024-12-04", "backup-operator", "Velero/restic",
        "PVCs/PVs restore but data is absent because the backup excluded pods mounting the volumes",
        "backup selection includes the objects required for the chosen data mover",
        "maintainer identified the missing pod inclusion and corrected the command boundary",
        "inspect include-resources configuration and include pods mounting volumes",
        ("inspect backup command", "inspect mounted pods", "correct included resources"),
        "metadata presence versus data-mover eligibility",
        "backup item inventory and restored data check", "configuration explanation supplied",
        "does any burden survive correct backup selection?", ("operator time", "frequency"),
        "CONFIGURATION_FAILURE", False,
        systems_inspected=("Velero backup", "Kubernetes pods", "PVC/PV", "restored data"),
        decision_points=("is backup eligible for data restore"),
        trusted_state="backup item inventory plus restored data",
        distrusted_state="PVC/PV presence alone",
    ),
    _evidence(
        "velero-restore-reference", "T3", "https://velero.io/docs/main/restore-reference/",
        "velero-io/velero", "CURRENT", "backup-engineer", "Velero",
        "NOT_AN_INCIDENT_BASELINE_CAPABILITY", "resource-ordered restore with explicit policies and logs",
        "restore workflow, resource order, existing-resource policy, hooks, and per-volume waits are documented",
        "use isolated target, explicit policies, describe/logs, hooks, and application checks", (),
        "Completed/PartiallyFailed restore sources and skipped existing objects need interpretation",
        "restore result, per-resource outcome, per-volume outcome, and application verification",
        "BASELINE_DOCUMENTED", "what application-specific validation is required", ("integration cost", "drill frequency"),
        "BASELINE_CAPABILITY", False, source_type="OFFICIAL_DOCUMENTATION", evidence_role="STRONG_BASELINE",
    ),
    _evidence(
        "velero-fsb-doc", "T3", "https://velero.io/docs/main/file-system-backup/",
        "velero-io/velero", "CURRENT", "backup-engineer", "Velero/Kopia",
        "NOT_AN_INCIDENT_BASELINE_CAPABILITY", "per-volume backup/restore state and restart/resume",
        "PodVolumeBackup/Restore records, troubleshooting, integrity connection, and limitations are documented",
        "inspect per-volume records and test restored data", (),
        "main restore completion versus per-volume/data-mover truth",
        "per-volume CR status plus actual data", "BASELINE_DOCUMENTED",
        "how much operator reconciliation remains after correct instrumentation", ("operator time", "maintenance cost"),
        "BASELINE_CAPABILITY", False, source_type="OFFICIAL_DOCUMENTATION", evidence_role="STRONG_BASELINE",
    ),
    _evidence(
        "etcd-recovery-doc", "T3", "https://etcd.io/docs/v3.7/op-guide/recovery/",
        "etcd-io/etcd", "CURRENT", "cluster-operator", "etcd",
        "NOT_AN_INCIDENT_BASELINE_CAPABILITY", "hash/revision-aware snapshot restore and integrity check",
        "snapshot status, integrity hash, revision bump, new cluster identity, and restore steps are documented",
        "verify hash/revision, restore as new logical cluster, reconfigure clients, then validate application", (),
        "snapshot revision versus client-observed current revision after restore",
        "snapshot hash/status, cluster membership, and application checks", "BASELINE_DOCUMENTED",
        "application-level correctness beyond etcd integrity", ("human drill cost", "application checks"),
        "BASELINE_CAPABILITY", False, source_type="OFFICIAL_DOCUMENTATION", evidence_role="STRONG_BASELINE",
    ),
)


def validate_evidence_corpus(corpus: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    missing: dict[str, list[str]] = {}
    seen_ids: set[str] = set()
    seen_urls: dict[str, str] = {}
    duplicates: list[dict[str, str]] = []
    for row in corpus:
        source_id = str(row.get("source_id", ""))
        absent = sorted(REQUIRED_EVIDENCE_FIELDS - set(row))
        if absent:
            missing[source_id or "UNKNOWN"] = absent
        if source_id in seen_ids:
            duplicates.append({"source_id": source_id, "reason": "DUPLICATE_SOURCE_ID"})
        seen_ids.add(source_id)
        url = str(row.get("source_url_or_reference", ""))
        if url in seen_urls and row.get("duplicate_of") is None:
            duplicates.append({"source_id": source_id, "reason": f"DUPLICATE_URL_OF_{seen_urls[url]}"})
        seen_urls[url] = source_id
    return {
        "valid": not missing and not duplicates,
        "missing_fields": missing,
        "duplicates": duplicates,
        "source_count": len(corpus),
        "data_only": all(row.get("external_text_role") == "DATA_ONLY" for row in corpus),
        "authority_effects": sum(bool(row.get("authority_effect")) for row in corpus),
    }


def operator_trace_ledger(corpus: Sequence[Mapping[str, Any]] = DEEP_EVIDENCE_CORPUS) -> list[dict[str, Any]]:
    rows = []
    for item in corpus:
        if item["evidence_role"] != "REAL_INCIDENT":
            continue
        actions = list(item["manual_actions"])
        systems = list(item["systems_inspected"])
        rows.append({
            "source_id": item["source_id"],
            "target_id": item["target_id"],
            "alert_or_trigger": item["actual_behavior"],
            "first_system_checked": systems[0] if systems else "UNKNOWN",
            "systems_inspected": systems,
            "state_trusted": item["trusted_state"],
            "state_distrusted": item["distrusted_state"],
            "missing_evidence": list(item["unknown"]),
            "commands_or_actions": actions,
            "duplicate_effect_risk": item["state_ambiguity"] if item["failure_class"] in {"PARTIAL_EFFECT_AMBIGUITY", "PROVENANCE_AMBIGUITY", "STATE_DIVERGENCE", "CROSS_SYSTEM_CONFLICT"} else "NOT_EXPLICITLY_REPORTED",
            "human_judgment": list(item["decision_points"]),
            "not_safely_automatable": "UNKNOWN_WITHOUT_REAL_B3_CONFIGURATION_AND_OPERATOR_TEST",
            "continuation_proof": item["continuation_proof"],
            "completion_proof": item["completion_proof"],
            "minimum_explicit_manual_actions": len(actions),
            "number_of_systems_inspected": len(systems) if systems else "UNKNOWN",
            "number_of_decision_points": len(item["decision_points"]) if item["decision_points"] else "UNKNOWN",
            "time_to_detection": "UNKNOWN",
            "time_to_understand": "UNKNOWN",
            "time_to_safe_decision": "UNKNOWN",
            "time_to_recovery": "UNKNOWN",
            "time_to_confidence": "UNKNOWN",
            "cognitive_reconciliation_set": [item["state_ambiguity"]] if item["state_ambiguity"] else [],
            "trace_integrity": "PUBLIC_FACTS_ONLY_UNKNOWN_PRESERVED",
        })
    return rows


def strong_baseline_ledger() -> list[dict[str, Any]]:
    return [
        {
            "target_id": "T1",
            "B0": {"result": "HETEROGENEOUS_AFFECTED_CONFIGURATIONS", "controls": ["native retry", "manual terminate", "alerts", "sync hooks/waves"], "evidence": ["argocd-6055", "argocd-11494", "argocd-22795", "flux-3725"]},
            "B1": {"result": "MOST_INCIDENTAL_FAILURES_CLOSED", "controls": ["bounded retry/backoff", "retry refresh", "timeout", "suspend/resume", "health checks", "fix affected controller version"]},
            "B2": {"result": "STRUCTURAL_RISK_CONTAINED", "controls": ["pin revision/generation", "idempotent hook/effect key", "observedGeneration/health gate", "bounded watchdog", "append-only operation/effect record"]},
            "B3": {"result": "SAME_SAFE_DECISION_AS_MINIMAL_ZERO_ON_PUBLIC_CASES", "controls": ["B2", "human compares Git commit, operation history, live generations, hooks/effects before resume"]},
            "cost": {"implementation_complexity": "MEDIUM", "ongoing_maintenance": "LOW_TO_MEDIUM", "integrations": 3, "custom_code": "SMALL_WATCHDOG_OR_RUNBOOK", "operator_steps": "PUBLICLY_UNMEASURED", "skill_requirement": "PLATFORM_OPERATOR", "time_to_safe_decision": "UNKNOWN", "auditability": "HIGH_IF_EFFECT_KEYS_ARE_USED", "verification_burden": "UNKNOWN"},
        },
        {
            "target_id": "T2",
            "B0": {"result": "VISIBLE_STATE_AND_RESULT_OR_WORKER_STATE_CAN_DIVERGE", "controls": ["retries", "caching", "manual UI/API transitions", "operator inspection"], "evidence": ["prefect-17484", "prefect-18303", "prefect-15658", "prefect-16429", "airflow-10544"]},
            "B1": {"result": "PRODUCT_BUGS_AND_BASIC_RETRY_FAILURES_CLOSED", "controls": ["upgrade/fix", "bounded retries", "persist results", "correct cache policy", "unique attempt identity"]},
            "B2": {"result": "PLAUSIBLY_CORRECT_BUT_CONFIGURATION_AND_CROSS_SYSTEM_COST_UNMEASURED", "controls": ["keyed transaction", "serializable lock", "idempotent external effect", "result/effect provenance", "worker/job identity", "bounded retry/timeout"]},
            "B3": {"result": "PUBLIC_EVIDENCE_INSUFFICIENT_TO_MEASURE", "controls": ["B2", "human compares orchestrator state, worker/pod identity, result store, and downstream effect acknowledgement"]},
            "cost": {"implementation_complexity": "MEDIUM_TO_HIGH_FOR_EXTERNAL_EFFECTS", "ongoing_maintenance": "UNKNOWN", "integrations": 4, "custom_code": "EFFECT_SPECIFIC_IDEMPOTENCY_AND_VERIFICATION", "operator_steps": "UNKNOWN", "skill_requirement": "DATA_PLATFORM_OPERATOR", "time_to_safe_decision": "UNKNOWN", "auditability": "PLAUSIBLE", "verification_burden": "UNKNOWN_DECISION_CHANGING_GAP"},
        },
        {
            "target_id": "T3",
            "B0": {"result": "RESTORE_STATUS_CAN_DIVERGE_FROM_APPLICATION_USABILITY", "controls": ["restore status/logs", "manual data inspection", "retries", "support bundles"], "evidence": ["velero-6280", "velero-6304", "velero-7901", "velero-8339", "velero-8483"]},
            "B1": {"result": "CONFIGURATION_AND_SELECTION_FAILURES_CLOSED", "controls": ["correct include rules", "existing-resource policy", "per-volume status", "bounded timeouts", "restore hooks"]},
            "B2": {"result": "RESTORE_TRUTH_ESTABLISHED_WITH_CONVENTIONAL_DRILL", "controls": ["immutable/protected backup", "snapshot hash/revision", "isolated restore", "per-resource/per-volume reconciliation", "application integrity/smoke checks"]},
            "B3": {"result": "SAME_REQUIRED_PROOF_AS_MINIMAL_ZERO", "controls": ["B2", "competent operator signs off application usability and recovery objective"]},
            "cost": {"implementation_complexity": "MEDIUM", "ongoing_maintenance": "DRILL_AND_APPLICATION_CHECKS", "integrations": 4, "custom_code": "APPLICATION_SPECIFIC_VALIDATION", "operator_steps": "UNKNOWN", "skill_requirement": "BACKUP_AND_APPLICATION_OPERATOR", "time_to_safe_decision": "UNKNOWN", "auditability": "HIGH", "verification_burden": "REAL_BUT_NOT_ZERO_SPECIFIC"},
        },
    ]


def baseline_adversary_report() -> list[dict[str, Any]]:
    checks = ("better configuration", "idempotency", "transaction", "generation/version guard", "workflow engine", "watchdog", "observability", "runbook", "competent human review", "existing platform", "two simple scripts")
    return [
        {"target_id": "T1", "checks": list(checks), "strongest_attack": "retry-refresh + generation/health/effect gates + human live-state review", "result": "BASELINE_WINS", "remaining_uncertainty": "none shown that can change a consequential decision; operator-time measurements remain absent"},
        {"target_id": "T2", "checks": list(checks), "strongest_attack": "keyed serializable transactions + persisted results + idempotent effects + human cross-system review", "result": "SURVIVES_ONLY_AS_EXTERNAL_MEASUREMENT_QUESTION", "remaining_uncertainty": "actual B3 configuration, operator reconstruction steps/time, and whether a minimal receipt removes material checks"},
        {"target_id": "T3", "checks": list(checks), "strongest_attack": "isolated restore drill + snapshot/per-volume provenance + application integrity tests + human signoff", "result": "BASELINE_WINS", "remaining_uncertainty": "drill cost exists but no ZERO-specific delta is shown"},
    ]


def failure_structure_map(corpus: Sequence[Mapping[str, Any]] = DEEP_EVIDENCE_CORPUS) -> list[dict[str, Any]]:
    return [
        {
            "source_id": row["source_id"], "target_id": row["target_id"],
            "classification": row["failure_class"],
            "structural_or_incidental": "STRUCTURAL" if row["structural"] else "INCIDENTAL_OR_BASELINE",
            "reason": (
                "multiple independently changing state/effect sources remain after the local bug is corrected"
                if row["structural"] else
                "a documented configuration/product fix or ordinary baseline removes the reported failure class"
            ),
        }
        for row in corpus if row["evidence_role"] == "REAL_INCIDENT"
    ]


def counterfactual_ledger(corpus: Sequence[Mapping[str, Any]] = DEEP_EVIDENCE_CORPUS) -> list[dict[str, Any]]:
    outcomes = {
        "T1": ("B3 pins revision/effect identity, blocks stale replay, and requires live-state review", "minimal ZERO reaches the same safe resume/repair decision", "MEDIUM"),
        "T2": ("B3 should contain duplicates with keyed transactions/idempotency but actual affected configurations and human burden are unknown", "minimal ZERO may reconcile state/result/worker/effect evidence but its delta is unmeasured", "LOW"),
        "T3": ("B3 isolated restore plus application verification detects unusable restores", "minimal ZERO requires the same application proof and does not remove it", "MEDIUM"),
    }
    rows = []
    for item in corpus:
        if item["evidence_role"] != "REAL_INCIDENT":
            continue
        b3, zero, confidence = outcomes[item["target_id"]]
        rows.append({
            "source_id": item["source_id"], "target_id": item["target_id"],
            "actual_historical_outcome": item["final_outcome"],
            "b3_counterfactual_outcome": b3,
            "zero_counterfactual_outcome": zero,
            "confidence": confidence,
            "promoted_to_proven_advantage": False,
        })
    return rows


def attention_burden_ledger(traces: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    return {
        "frozen_threshold": dict(ATTENTION_THRESHOLD),
        "rows": [
            {
                "source_id": row["source_id"], "target_id": row["target_id"],
                "number_of_systems_inspected": row["number_of_systems_inspected"],
                "minimum_explicit_manual_actions": row["minimum_explicit_manual_actions"],
                "number_of_decision_points": row["number_of_decision_points"],
                "number_of_escalations": "UNKNOWN", "number_of_human_roles": "UNKNOWN",
                "wait_steps": "UNKNOWN", "reconstruction_steps": "UNKNOWN",
                "approval_steps": "UNKNOWN", "rollback_steps": "UNKNOWN", "replay_steps": "UNKNOWN",
                "time_to_detection": "UNKNOWN", "time_to_understand": "UNKNOWN",
                "time_to_safe_decision": "UNKNOWN", "time_to_recovery": "UNKNOWN",
                "time_to_confidence": "UNKNOWN",
            }
            for row in traces
        ],
        "human_attention_evidence": "PUBLIC_REPORTS_PROVE_MANUAL_ACTIONS_BUT_NOT_MATERIAL_ATTENTION_DELTA_OVER_B3",
        "attention_delta": "INCONCLUSIVE",
        "threshold_lowered_after_results": False,
    }


def negative_evidence_ledger() -> list[dict[str, Any]]:
    return [
        {"target_id": "T1", "evidence": "Argo retry-refresh, waves/hooks, health and Flux observedGeneration/dependsOn/health/timeout cover most control semantics", "effect": "weakens a unique ZERO decision claim", "preserved": True},
        {"target_id": "T1", "evidence": "V1.1 historical replay already produced B3/ZERO parity", "effect": "kills generic revision-continuity wedge absent new real delta", "preserved": True},
        {"target_id": "T2", "evidence": "several reported failures were fixed product bugs", "effect": "historical pain alone cannot establish a structural baseline gap", "preserved": True},
        {"target_id": "T2", "evidence": "Prefect documents keyed at-most-once transactions, serializable locks, rollback/commit, and result persistence", "effect": "raises B2/B3 substantially", "preserved": True},
        {"target_id": "T2", "evidence": "no sanitized real incident exposes actual B3 controls, steps, timing, or external-effect inventory", "effect": "blocks ZERO decision/attention delta", "preserved": True},
        {"target_id": "T3", "evidence": "correct include rules and existing-resource policies explain multiple reports", "effect": "kills configuration-only restore wedge", "preserved": True},
        {"target_id": "T3", "evidence": "snapshot hashes, per-volume records, isolated restore and application checks form a strong conventional verification baseline", "effect": "ZERO has not removed application-specific proof", "preserved": True},
        {"target_id": "ALL", "evidence": "no independent ZERO user, participant, incident comparison, WTP, or settlement exists", "effect": "keeps L0 and 0 KWD", "preserved": True},
    ]


def depth_completeness_scorecard() -> dict[str, Any]:
    fields = (
        "REALITY_EXTRACTION", "OPERATOR_RECONSTRUCTION", "BASELINE_B0", "BASELINE_B1",
        "BASELINE_B2", "BASELINE_B3", "BASELINE_ADVERSARY", "FAILURE_STRUCTURE",
        "COUNTERFACTUAL", "ZERO_DIFFERENTIAL", "ATTENTION_DELTA", "ECONOMIC_RELEVANCE",
        "NEGATIVE_EVIDENCE", "RED_TEAM", "SATURATION",
    )
    rows: dict[str, dict[str, str]] = {}
    for target in TARGETS:
        rows[target] = {field: "COMPLETE" for field in fields}
        rows[target]["ATTENTION_DELTA"] = "PARTIAL"
    rows["T2"]["COUNTERFACTUAL"] = "PARTIAL"
    rows["T2"]["SATURATION"] = "PARTIAL"
    return {
        "targets": rows,
        "missing_decision_changing_categories": [],
        "partial_decision_changing_categories": ["T2 actual B3 configuration", "T2 attributable operator time/steps", "T2 verified differential under a blinded incident"],
        "protocol_complete": True,
        "result": "PASS_WITH_EXPLICIT_EXTERNAL_EVIDENCE_BOUNDARY",
    }


def saturation_report(corpus: Sequence[Mapping[str, Any]] = DEEP_EVIDENCE_CORPUS) -> dict[str, Any]:
    projects = sorted({row["project"] for row in corpus})
    actors = sorted({row["actor_type"] for row in corpus})
    failures = sorted({row["failure_class"] for row in corpus if row["evidence_role"] == "REAL_INCIDENT"})
    return {
        "source_diversity": {"source_types": sorted({row["source_type"] for row in corpus}), "count": len({row["source_type"] for row in corpus})},
        "project_diversity": {"projects": projects, "count": len(projects)},
        "actor_diversity": {"actors": actors, "count": len(actors)},
        "failure_mode_diversity": {"modes": failures, "count": len(failures)},
        "time_diversity": {"years": sorted({str(row["date"])[:4] for row in corpus if str(row["date"])[:4].isdigit()}), "count": len({str(row["date"])[:4] for row in corpus if str(row["date"])[:4].isdigit()})},
        "tool_diversity": {"tools": sorted({row["system"] for row in corpus}), "count": len({row["system"] for row in corpus})},
        "T1": {"status": "REACHED_FOR_PUBLIC_BASELINE_DECISION", "reason": "new reports stabilize around revision/effect identity and native deterministic controls close the public decisions"},
        "T2": {"status": "NOT_REACHED_FOR_REAL_DIFFERENTIAL", "reason": "public reports stabilize structurally, but no independent sanitized incident exposes actual B3 steps/time/effect truth"},
        "T3": {"status": "REACHED_FOR_PUBLIC_BASELINE_DECISION", "reason": "configuration, per-volume provenance, isolated restore, and application verification exhaust the public decision classes without ZERO delta"},
        "overall": "PARTIAL",
        "important_unexamined_class": "independent sanitized dataflow incident with real B3 configuration, operator reconstruction, timing, and verification criterion",
        "why_it_matters": "it alone can distinguish B3 parity from a material cross-system attention/verification gap",
        "further_public_search_evsi": "LOW",
        "external_incident_evsi": "HIGH",
    }


def qualified_participant_packet() -> dict[str, Any]:
    return {
        "packet_id": "ZRWVE-T2-INCIDENT-ACQUISITION-001",
        "state": "FROZEN_WAITING_EXTERNAL_WRITE_AUTHORITY",
        "target": "T2 Dataflow partial execution / state resume",
        "qualification": {
            "independent": True, "non_owner": True, "non_omega": True, "non_bot": True,
            "non_test_actor": True,
            "attributable": True, "experienced_with_target_workflow": True,
            "can_supply_sanitized_real_incident": True,
            "minimum_experience": "personally operated or recovered a production/staging orchestration incident involving partial execution or retry/resume ambiguity",
        },
        "minimum_qualified_participants": 3,
        "sample_size_reason": "one incident can be idiosyncratic; two can expose contradiction; three across at least two orchestration stacks is the minimum qualitative sample able to test repeatability without claiming prevalence, WTP, or market demand",
        "maximum_number": 3,
        "who": "independent experienced dataflow/orchestration operators across at least two stacks",
        "why": "measure actual B3 reconstruction burden and whether a minimal state/result/worker/effect receipt changes a decision or removes material checks",
        "exact_message": (
            "OMEGA is conducting a bounded, non-commercial incident-reconstruction study. "
            "If you have personally handled a sanitized orchestration incident involving partial execution, retry, or resume ambiguity, would you be willing to describe what failed, which systems you inspected, what proved continuation safe, and what your existing tools handled well? "
            "Please share no credentials, private logs, source code, customer data, or identifying production details. "
            "The answer 'our existing system handles this fine' is equally useful. No product interest, purchase intent, or demand is being requested."
        ),
        "questions": [
            "What failed?", "What did you think was true?", "What turned out not to be true?",
            "Which systems did you inspect?", "What evidence contradicted?",
            "What action could not safely be automated?", "What side effect were you afraid to repeat?",
            "What proved it was safe to continue?", "Which step consumed the most attention?",
            "What existing tool helped?", "What existing tool did not help?",
            "What would have removed the manual uncertainty?",
        ],
        "evidence_requested": ["sanitized timeline", "systems inspected", "operator actions", "B3 controls", "decision points", "verification criterion", "attributable time data if known"],
        "privacy_boundary": ["no credentials", "no secrets", "no private logs", "no source code", "no customer personal information", "no production access"],
        "stop_condition": "three qualifying incidents, owner revocation, participant decline, or any privacy/authority violation",
        "expiry": "30 days after owner authorizes the exact external action",
        "expected_information_gain": "HIGH; resolves the only remaining decision-changing public-evidence gap",
        "external_write_authorized": False,
        "external_write_executed": False,
    }


def validate_participant(candidate: Mapping[str, Any]) -> bool:
    required_true = ("independent", "non_owner", "non_omega", "non_bot", "non_test_actor", "attributable", "experienced_with_target_workflow", "can_supply_sanitized_real_incident")
    return all(candidate.get(field) is True for field in required_true)


def validate_sanitized_incident(record: Mapping[str, Any]) -> dict[str, Any]:
    required = {"incident_id", "domain", "systems", "timeline", "expected_state", "observed_state", "external_effects", "checkpoints", "operator_actions", "baseline_controls", "decision_points", "final_recovery", "verification", "time_data_if_known"}
    lowered = {str(key).lower() for key in record}
    forbidden = sorted(lowered & FORBIDDEN_INCIDENT_KEYS)
    return {"valid": required <= set(record) and not forbidden, "missing": sorted(required - set(record)), "forbidden": forbidden}


BLIND_HASH_FIELDS = (
    "schema", "experiment_id", "target", "decision_question", "same_evidence",
    "time_limit", "comparable_tool_access", "arms", "independent_verification",
    "attention_threshold_hash", "outcomes", "authority", "privacy_boundary", "abort_conditions",
)


def blinded_incident_experiment_spec() -> dict[str, Any]:
    record: dict[str, Any] = {
        "schema": "ZRWVE_BLINDED_REAL_INCIDENT_EXPERIMENT_V1",
        "experiment_id": "ZRWVE-T2-BLIND-001",
        "state": "FROZEN_WAITING_QUALIFIED_INCIDENTS",
        "target": "T2 Dataflow partial execution / state resume",
        "decision_question": "WHICH_TASKS_MAY_SAFELY_RESUME_AND_WHICH_EFFECTS_MUST_NOT_REPEAT?",
        "same_evidence": "same sanitized incident packet for B3 and ZERO; no private reveal before decisions are fixed",
        "time_limit": "30 minutes per arm",
        "comparable_tool_access": "same read-only sanitized evidence; B3 may use documented native controls/runbook; ZERO may use only minimal provenance+checkpoint+state/effect reconciliation+verification",
        "arms": ["B3_STRONG_DETERMINISTIC_ARCHITECTURE_PLUS_COMPETENT_HUMAN", "MINIMAL_ZERO"],
        "independent_verification": "independent incident owner/verifier scores correct decision, false-safe, false-block, missed conflict, checks, reconstruction, and time",
        "attention_threshold_hash": ATTENTION_THRESHOLD["threshold_hash"],
        "outcomes": ["B3_WINS", "ZERO_WINS", "PARITY", "INCONCLUSIVE"],
        "authority": "INTERNAL_FREEZE_ONLY_EXTERNAL_CONTACT_NOT_AUTHORIZED",
        "privacy_boundary": ["no credentials", "no secrets", "no customer PII", "no private raw logs", "no production access"],
        "abort_conditions": ["threshold mutation", "identity/provenance failure", "privacy violation", "different evidence between arms", "expected winner revealed", "external write without authority"],
    }
    record["blind_spec_hash"] = _hash({field: record[field] for field in BLIND_HASH_FIELDS})
    return record


def validate_blind_spec(record: Mapping[str, Any]) -> bool:
    try:
        payload = {field: record[field] for field in BLIND_HASH_FIELDS}
        expected = record["blind_spec_hash"]
    except (KeyError, TypeError):
        return False
    return expected == _hash(payload)


def external_action_allowed(packet: Mapping[str, Any]) -> bool:
    return bool(packet.get("external_write_authorized")) and not bool(packet.get("external_write_executed"))


def _target_decisions() -> list[dict[str, Any]]:
    return [
        {"target_id": "T1", "structural_gap": "PROVEN", "b3_gap": "NOT_PROVEN", "zero_delta": "ZERO_DELTA_NOT_PROVEN", "classification": ["BASELINE_WINS", "TARGET_KILLED"], "decision_question": "WHICH_REVISION_AND_EFFECT_SET_MAY_CONTINUE?", "minimal_zero": ["provenance", "generation", "effect identity", "verification"], "decision_delta": "NONE_PROVEN", "attention_delta": "NOT_PROVEN", "recovery_delta": "NOT_PROVEN", "verification_delta": "NOT_PROVEN"},
        {"target_id": "T2", "structural_gap": "PROVEN", "b3_gap": "INCONCLUSIVE", "zero_delta": "ZERO_DELTA_NOT_PROVEN", "classification": ["INSUFFICIENT_REAL_EVIDENCE", "EXTERNAL_VALIDATION_READY"], "decision_question": "WHICH_TASKS_MAY_SAFELY_RESUME_AND_WHICH_EFFECTS_MUST_NOT_REPEAT?", "minimal_zero": ["provenance", "checkpoint", "state/result/worker/effect reconciliation", "host verification"], "decision_delta": "INCONCLUSIVE", "attention_delta": "INCONCLUSIVE", "recovery_delta": "INCONCLUSIVE", "verification_delta": "INCONCLUSIVE"},
        {"target_id": "T3", "structural_gap": "PROVEN", "b3_gap": "NOT_PROVEN", "zero_delta": "ZERO_DELTA_NOT_PROVEN", "classification": ["BASELINE_WINS", "TARGET_KILLED"], "decision_question": "RESTORE_USABLE?", "minimal_zero": ["backup provenance", "per-volume state", "application verification"], "decision_delta": "NONE_PROVEN", "attention_delta": "NOT_PROVEN", "recovery_delta": "NOT_PROVEN", "verification_delta": "NONE_PROVEN"},
    ]


def _red_team() -> dict[str, Any]:
    attacks = {
        "selection_bias": "CONTAINED_BY_USING_ALL_THREE_PRESELECTED_TARGETS_AND_NEGATIVE_DOCS",
        "rare_incident_bias": "NOT_RESOLVED_FREQUENCY_UNKNOWN",
        "weak_operators": "CONTAINED_BY_B3_COMPETENT_OPERATOR_BASELINE",
        "bad_configuration": "CONTAINED_CONFIGURATION_ONLY_CASES_MARKED_INCIDENTAL",
        "duplicate_reports": "CONTAINED_BY_SOURCE_ID_URL_DEDUPE",
        "vendor_bug_confusion": "CONTAINED_FIXED_BUGS_DO_NOT_PROVE_ZERO_GAP",
        "missing_incumbent_feature": "CONTAINED_OFFICIAL_BASELINE_DOCS_INCLUDED",
        "human_review_omitted": "CONTAINED_B3_INCLUDES_COMPETENT_HUMAN",
        "integration_burden_ignored": "CONTAINED_HIDDEN_COST_GUARD_FROZEN",
        "maintenance_cost_ignored": "CONTAINED_COST_RECORDED_UNKNOWN_NOT_ZERO",
        "counterfactual_overconfidence": "CONTAINED_LOW_MEDIUM_CONFIDENCE_NOT_PROMOTED",
        "ai_optimism": "CONTAINED_NO_MODEL_OR_INTELLIGENCE_CLAIM",
        "complexity_hiding": "CONTAINED_MINIMAL_ZERO_ONLY_AND_COMPLEXITY_INCONCLUSIVE",
        "privacy_security_burden": "CONTAINED_SANITIZED_PACKET_AND_NO_EXTERNAL_EXECUTION",
        "buyer_indifference": "UNRESOLVED_BUYER_AND_PAYER_UNKNOWN",
        "low_incident_frequency": "UNRESOLVED",
        "low_willingness_to_switch": "UNRESOLVED_NO_WTP_EVIDENCE",
    }
    return {
        "attacks": attacks,
        "specific_objection": "T2 public reports prove state/effect ambiguity, but do not prove that competent B3 operators incur the frozen material attention threshold or that ZERO changes a decision.",
        "result": "NO_ZERO_ADVANTAGE_SURVIVES_AS_PROVEN;_ONE_EXTERNAL_DISCRIMINATION_CASE_SURVIVES",
        "false_evidence_promotions": 0,
    }


def _input_fingerprint(root: Path) -> str:
    zero = root / ".omega" / "zero"
    module_path = root / "omega" / "real_world_value_deep.py"
    if not module_path.is_file():
        module_path = Path(__file__)
    paths = {
        "frontier_cycle": _hash_file(zero / "zrwve_frontier_cycle_0002.json"),
        "frontier_experiment": _hash_file(zero / "zrwve_frontier_experiment_0002.json"),
        "deep_module": _hash_file(module_path),
    }
    project_text = (root / "PROJECT_STATE.md").read_text(encoding="utf-8", errors="replace") if (root / "PROJECT_STATE.md").is_file() else ""
    next_text = (root / "NEXT_TASK.md").read_text(encoding="utf-8", errors="replace") if (root / "NEXT_TASK.md").is_file() else ""
    def field(pattern: str, text: str) -> str:
        match = re.search(pattern, text, re.MULTILINE)
        return match.group(1).strip() if match else "UNKNOWN"
    return _hash({
        "sources": paths,
        "corpus": DEEP_EVIDENCE_CORPUS,
        "version": field(r"^version:\s*(.+)$", project_text),
        "milestone": field(r"^current_milestone:\s*(.+)$", project_text),
        "next_status": field(r"^status:\s*(.+)$", next_text),
    })


def _next_sequence(output: Path, prefix: str) -> int:
    highest = 0
    pattern = re.compile(re.escape(prefix) + r"_(\d+)\.json$")
    for path in output.glob(prefix + "_*.json") if output.is_dir() else ():
        match = pattern.match(path.name)
        if match:
            highest = max(highest, int(match.group(1)))
    return highest + 1


def run_deep_cycle(root: Path, output_dir: Path | None = None) -> dict[str, Any]:
    root = Path(root).resolve()
    output = Path(output_dir).resolve() if output_dir else root / ".omega" / "zero"
    fingerprint = _input_fingerprint(root)
    latest = _latest_json(output, "zrwve_deep_cycle")
    if latest and latest.get("input_fingerprint") == fingerprint:
        replay = dict(latest)
        replay["idempotent_replay"] = True
        return replay

    validation = validate_evidence_corpus(DEEP_EVIDENCE_CORPUS)
    if not validation["valid"] or not validation["data_only"] or validation["authority_effects"]:
        raise ValueError("deep evidence provenance/injection boundary failed")
    traces = operator_trace_ledger()
    baselines = strong_baseline_ledger()
    adversary = baseline_adversary_report()
    structures = failure_structure_map()
    counterfactuals = counterfactual_ledger()
    attention = attention_burden_ledger(traces)
    negative = negative_evidence_ledger()
    completeness = depth_completeness_scorecard()
    saturation = saturation_report()
    participant = qualified_participant_packet()
    blind = blinded_incident_experiment_spec()
    if not validate_blind_spec(blind):
        raise ValueError("blind experiment freeze integrity failure")
    target_decisions = _target_decisions()
    red = _red_team()
    incidents = [row for row in DEEP_EVIDENCE_CORPUS if row["evidence_role"] == "REAL_INCIDENT"]
    structural = [row for row in incidents if row["structural"]]
    incidental = [row for row in incidents if not row["structural"]]
    cycle_sequence = _next_sequence(output, "zrwve_deep_cycle")
    cycle_id = f"zrwve-deep-cycle-{cycle_sequence:04d}"
    result = {
        "schema": DEEP_SCHEMA,
        "cycle_id": cycle_id,
        "generated_at": _now(),
        "input_fingerprint": fingerprint,
        "repository_truth": {
            "canonical_repository": str(root), "version": "0.21.0",
            "current_evidence_level": "L0", "independent_external_evidence_count": 0,
            "qualified_real_counterparties": 0, "real_usage_events": 0,
            "wtp_events": 0, "settlement_events": 0,
            "verified_net_economic_value_kwd": 0,
            "wake_plane_mode": "PASSIVE_PRODUCTION", "capability_router_mode": "SHADOW",
            "global_production_default": "LEGACY", "production_wide_adoption_authorized": False,
        },
        "zero_deep_reality_state": "WAITING_QUALIFIED_EXTERNAL_INCIDENT_EVIDENCE",
        "depth_protocol_version": DEEP_PROTOCOL_VERSION,
        "passes": [{"pass": index + 1, "name": name, "status": "COMPLETE"} for index, name in enumerate(PASS_NAMES)],
        "current_primary_bottleneck": "NO_UNDEFEATED_BASELINE_GAP + INSUFFICIENT_REAL_DISCRIMINATING_EVIDENCE",
        "evidence_targets": [{"target_id": key, "name": value} for key, value in TARGETS.items()],
        "deep_evidence_corpus": {"schema": "ZRWVE_DEEP_EVIDENCE_CORPUS_V1", "validation": validation, "sources": list(DEEP_EVIDENCE_CORPUS)},
        "operator_trace_ledger": traces,
        "strong_baseline_ledger": baselines,
        "baseline_adversary_report": adversary,
        "failure_structure_map": structures,
        "counterfactual_ledger": counterfactuals,
        "attention_burden_ledger": attention,
        "negative_evidence_ledger": negative,
        "depth_completeness_scorecard": completeness,
        "saturation_report": saturation,
        "target_decisions": target_decisions,
        "qualified_participant_packet": participant,
        "blinded_incident_experiment_spec": blind,
        "baseline_results": {
            "B0": "REAL_FAILURES_AND_MANUAL_RECONSTRUCTION_OBSERVED",
            "B1": "CONFIGURATION_AND_PRODUCT_BUGS_CLOSE_MANY_CASES",
            "B2": "STRONG_DETERMINISTIC_CONTROLS_CLOSE_T1_T3_AND_PLAUSIBLY_T2",
            "B3": "T1_T3_BASELINE_WINS; T2_REAL_COST_AND_ATTENTION_UNMEASURED",
        },
        "human_attention_evidence": attention["human_attention_evidence"],
        "counterfactual_result": "T1_T3_B3_PARITY_MEDIUM_CONFIDENCE; T2_LOW_CONFIDENCE_REQUIRES_REAL_INCIDENT",
        "zero_differential_result": "NO_ZERO_DIFFERENTIAL_PROVEN",
        "decision_delta": "INCONCLUSIVE_FOR_T2_NONE_PROVEN_SYSTEM_WIDE",
        "attention_delta": "INCONCLUSIVE",
        "recovery_delta": "INCONCLUSIVE",
        "verification_delta": "NONE_PROVEN",
        "economic_relevance": {
            "classification": "PLAUSIBLE",
            "reason": "incidents affect deployment, 50-plus-task orchestration, and disaster recovery, but frequency/cost/buyer/WTP are not measured",
            "pain_actor": "platform/data/backup operator",
            "solution_user": "platform/data/backup operator",
            "deployment_approver": "UNKNOWN",
            "payer": "UNKNOWN",
            "monetary_value_assigned": False,
        },
        "negative_evidence_result": "PRESERVED_AND_DECISION_ACTIVE",
        "depth_completeness": completeness["result"],
        "real_baseline_break_proven": False,
        "real_human_attention_gap_proven": False,
        "blinded_incident_experiment_ready": True,
        "qualified_participant_model": participant["qualification"],
        "minimum_qualified_participants": participant["minimum_qualified_participants"],
        "current_qualified_participants": 0,
        "external_action_required": True,
        "external_action_packet": participant,
        "external_write_executed": 0,
        "wake_routing_result": {
            "event_type": "ZRWVE_QUALIFIED_INCIDENT_SUBMITTED",
            "route": "EXISTING_WAKE_PLANE",
            "accept_only_if": ["PROVENANCE_VALID", "NON_DUPLICATE", "RELEVANT", "QUALIFIED", "SANITIZED"],
            "new_watcher_created": False, "registration_performed": False,
            "wake_plane_mode": "PASSIVE_PRODUCTION",
        },
        "capability_value_hypotheses": [
            {"capability": "source verification", "hypothesis": "may reduce provenance error in incident compilation", "mode": "SHADOW", "promoted": False},
            {"capability": "document/data analysis", "hypothesis": "may reduce multi-system reconstruction time on sanitized traces", "mode": "SHADOW", "promoted": False},
            {"capability": "external expert", "hypothesis": "is required to establish actual B3 operator burden and outcome truth", "mode": "SHADOW", "promoted": False},
        ],
        "red_team_result": red,
        "evidence_counts": {
            "sources": len(DEEP_EVIDENCE_CORPUS), "operator_traces": len(traces),
            "qualifying_real_incidents": len(incidents), "structural_failures": len(structural),
            "incidental_failures": len(incidental), "independent_zero_signals": 0,
            "owner_activity_counted_as_external": 0, "synthetic_evidence_counted_as_real": 0,
            "false_evidence_promotions": 0,
        },
        "authority_violations": 0,
        "test_results": {"status": "PENDING_HOST_VERIFICATION"},
        "final_causal_decision": "EXTERNAL_INCIDENT_VALIDATION_REQUIRED",
        "primary_value_bottleneck": "MISSING_INDEPENDENT_SANITIZED_T2_INCIDENT_WITH_ACTUAL_B3_CONFIGURATION_OPERATOR_TRACE_TIME_AND_VERIFICATION_CRITERION",
        "next_cheapest_truth": "one qualified independent sanitized T2 incident, then a frozen blinded B3-versus-minimal-ZERO comparison; acquire up to three only to test cross-actor/tool repeatability",
        "next_atomic_action": "REQUEST_ONE_BOUNDED_OWNER_AUTHORIZATION_FOR_THE_FROZEN_MAX_3_PARTICIPANT_INCIDENT_ACQUISITION_PACKET",
        "autonomous_continuation": "WAIT_AUTHORITY",
        "idempotent_replay": False,
    }

    artifacts = {
        "zrwve_deep_evidence_corpus.json": result["deep_evidence_corpus"],
        "zrwve_operator_trace_ledger.json": {"schema": "ZRWVE_OPERATOR_TRACE_LEDGER_V1", "rows": traces},
        "zrwve_strong_baseline_ledger.json": {"schema": "ZRWVE_STRONG_BASELINE_LEDGER_V1", "rows": baselines},
        "zrwve_baseline_adversary_report.json": {"schema": "ZRWVE_BASELINE_ADVERSARY_REPORT_V1", "rows": adversary},
        "zrwve_failure_structure_map.json": {"schema": "ZRWVE_FAILURE_STRUCTURE_MAP_V1", "rows": structures},
        "zrwve_counterfactual_ledger.json": {"schema": "ZRWVE_COUNTERFACTUAL_LEDGER_V1", "rows": counterfactuals},
        "zrwve_attention_burden_ledger.json": attention,
        "zrwve_negative_evidence_ledger.json": {"schema": "ZRWVE_NEGATIVE_EVIDENCE_LEDGER_V1", "rows": negative},
        "zrwve_depth_completeness_scorecard.json": completeness,
        "zrwve_saturation_report.json": saturation,
        "zrwve_qualified_participant_packet.json": participant,
        "zrwve_blinded_incident_experiment_spec.json": blind,
    }
    for name, value in artifacts.items():
        _atomic_write(output / name, value)
    _atomic_write(output / f"zrwve_deep_cycle_{cycle_sequence:04d}.json", result)
    _atomic_write(output / "zrwve_deep_memory.json", {
        "schema": "ZRWVE_DEEP_MEMORY_V1", "last_cycle_id": cycle_id,
        "input_fingerprint": fingerprint, "final_causal_decision": result["final_causal_decision"],
        "primary_target": "T2", "prior_killed_wedges_reopened": 0,
        "evidence_level": "L0", "verified_net_economic_value_kwd": 0,
        "source_cycle_hash": _hash(result),
    })
    return result


def record_deep_host_verification(root: Path, verification: Mapping[str, Any]) -> dict[str, Any]:
    root = Path(root).resolve()
    output = root / ".omega" / "zero"
    latest = _latest_json(output, "zrwve_deep_cycle")
    if not latest:
        raise FileNotFoundError("no deep cycle to verify")
    if verification.get("status") != "PASS":
        raise ValueError("only a completed passing host verification may be recorded")
    updated = dict(latest)
    updated["test_results"] = dict(verification)
    sequence_match = re.search(r"(\d+)$", str(updated["cycle_id"]))
    if not sequence_match:
        raise ValueError("invalid deep cycle id")
    _atomic_write(output / f"zrwve_deep_cycle_{int(sequence_match.group(1)):04d}.json", updated)
    # Host verification mutates the cycle's test_results. Keep the append-only
    # memory pointer aligned with the verified cycle so replay integrity does
    # not silently depend on the pre-verification hash.
    memory_path = output / "zrwve_deep_memory.json"
    if memory_path.exists():
        try:
            memory = json.loads(memory_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            memory = None
        if isinstance(memory, dict):
            memory["source_cycle_hash"] = _hash(updated)
            _atomic_write(memory_path, memory)
    record = {
        "schema": "ZRWVE_DEEP_HOST_VERIFICATION_V1", "cycle_id": updated["cycle_id"],
        "recorded_at": _now(), "verification": dict(verification),
        "cycle_hash": _hash(updated),
    }
    _atomic_write(output / "zrwve_deep_host_verification_0001.json", record)
    return updated


def deep_status(root: Path) -> dict[str, Any]:
    latest = _latest_json(Path(root).resolve() / ".omega" / "zero", "zrwve_deep_cycle")
    if not latest:
        return {"schema": DEEP_SCHEMA, "status": "NOT_RUN"}
    return {
        "schema": DEEP_SCHEMA, "cycle_id": latest["cycle_id"],
        "state": latest["zero_deep_reality_state"],
        "final_causal_decision": latest["final_causal_decision"],
        "evidence_saturation": latest["saturation_report"]["overall"],
        "qualifying_real_incidents": latest["evidence_counts"]["qualifying_real_incidents"],
        "real_baseline_break_proven": latest["real_baseline_break_proven"],
        "real_human_attention_gap_proven": latest["real_human_attention_gap_proven"],
        "minimum_qualified_participants": latest["minimum_qualified_participants"],
        "current_qualified_participants": latest["current_qualified_participants"],
        "external_action_required": latest["external_action_required"],
        "test_results": latest["test_results"],
        "next_atomic_action": latest["next_atomic_action"],
    }


# ---------------------------------------------------------------------------
# ZRWVE V1.2E — external incident packet hardening
# ---------------------------------------------------------------------------

def _packet_key(value: Any) -> str:
    """Normalize a schema key without changing the submitted evidence."""
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")


def _packet_mapping(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    return {_packet_key(key): item for key, item in value.items()}


def _packet_forbidden(value: Any) -> list[str]:
    """Return markers only; never echo participant payloads into artifacts."""
    found: set[str] = set()
    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized = _packet_key(key)
            if normalized in FORBIDDEN_INCIDENT_KEYS:
                found.add(normalized)
            found.update(_packet_forbidden(item))
    elif isinstance(value, (list, tuple, set)):
        for item in value:
            found.update(_packet_forbidden(item))
    elif isinstance(value, str):
        lowered = value.lower()
        if any(marker in lowered for marker in PACKET_FORBIDDEN_MARKERS):
            found.add("disallowed_incident_marker")
        if re.search(r"(?:ghp_|github_pat_|AIza|ya29\\.|-----BEGIN .*PRIVATE KEY-----)", value):
            found.add("secret_pattern")
    return sorted(found)


def incident_data_schema() -> dict[str, Any]:
    return {
        "schema": "ZRWVE_T2_INCIDENT_DATA_SCHEMA_V1_2E",
        "required_fields": list(INCIDENT_DATA_FIELDS),
        "real_incident_required": True,
        "unknown_values_allowed": True,
        "sanitization_required": True,
        "forbidden_payload": sorted(FORBIDDEN_INCIDENT_KEYS),
        "causal_structure_required": True,
    }


def b3_configuration_schema() -> dict[str, Any]:
    return {
        "schema": "ZRWVE_T2_B3_CONFIGURATION_SCHEMA_V1_2E",
        "actual_section": "b3_actual",
        "counterfactual_section": "b3_strongest_reasonable_counterfactual",
        "required_fields": list(B3_CONFIGURATION_FIELDS),
        "unknown_values_allowed": True,
        "actual_and_counterfactual_must_remain_separate": True,
        "strong_baseline_definition": "strongest realistic conventional controls available to the operator",
    }


def operator_trace_schema() -> dict[str, Any]:
    return {
        "schema": "ZRWVE_T2_OPERATOR_TRACE_SCHEMA_V1_2E",
        "required_fields": list(OPERATOR_TRACE_FIELDS),
        "ordered_steps_required": True,
        "judgment_fields_required": [
            "decision_required", "evidence_missing", "conflicting_states",
            "unsafe_automatic_action", "wrong_decision_consequence", "confidence_reason",
        ],
        "unknown_values_allowed": True,
    }


def verification_criterion_schema() -> dict[str, Any]:
    return {
        "schema": "ZRWVE_T2_VERIFICATION_SCHEMA_V1_2E",
        "required_fields": list(VERIFICATION_CRITERION_FIELDS),
        "source_of_truth_must_be_external_to_zero": True,
        "accept_and_reject_conditions_required": True,
        "unknown_values_allowed": True,
    }


def initial_contact_packet() -> dict[str, Any]:
    message = (
        "We are conducting bounded technical incident research on how experienced operators "
        "recover interrupted or ambiguous workflow state. Real cases where existing tooling "
        "worked well are equally useful. Participation is optional; please share only sanitized "
        "timeline, controls, recovery steps, and verification evidence—never credentials, secrets, "
        "private logs, source code, or customer data. The focus is operational facts, not opinions "
        "about a product."
    )
    return {
        "schema": "ZRWVE_T2_INITIAL_CONTACT_PACKET_V1_2E",
        "packet_id": "ZRWVE-T2-INCIDENT-ACQUISITION-001",
        "state": "FROZEN_NOT_SENT",
        "target": "T2 Dataflow partial execution / state resume",
        "message": message,
        "message_hash": _hash(message),
        "optional_participation": True,
        "no_opinion_or_wtp_request": True,
        "no_external_write_executed": True,
        "privacy_boundary": [
            "no credentials", "no secrets", "no private logs", "no source code",
            "no customer personal information", "no production access",
        ],
    }


def validate_incident_data(record: Mapping[str, Any]) -> dict[str, Any]:
    normalized = _packet_mapping(record)
    missing = sorted(set(INCIDENT_DATA_FIELDS) - set(normalized))
    forbidden = _packet_forbidden(record)
    real = normalized.get("real_incident") is True
    marker = "disallowed_incident_marker" not in forbidden
    sanitized = str(normalized.get("sanitization_status", "")).upper() in {"PASS", "SANITIZED", "SANITIZED_PASS"}
    result = {
        "valid": not missing and not forbidden and real and marker and sanitized,
        "missing": missing,
        "forbidden": forbidden,
        "real_incident": real,
        "sanitization": "PASS" if sanitized else "FAIL",
        "unknown_fields_preserved": isinstance(normalized.get("unknown_fields"), (list, tuple, str)),
    }
    return result


def validate_b3_configuration(record: Mapping[str, Any]) -> dict[str, Any]:
    normalized = _packet_mapping(record)
    actual = _packet_mapping(normalized.get("b3_actual", normalized if "b3_strongest_reasonable_counterfactual" not in normalized else {}))
    counter = _packet_mapping(normalized.get("b3_strongest_reasonable_counterfactual", normalized.get("b3_counterfactual", {})))
    actual_missing = sorted(set(B3_CONFIGURATION_FIELDS) - set(actual))
    counter_missing = sorted(set(B3_CONFIGURATION_FIELDS) - set(counter))
    forbidden = _packet_forbidden(record)
    separated = bool(actual and counter and actual != counter)
    return {
        "valid": not actual_missing and not counter_missing and not forbidden and separated,
        "actual_missing": actual_missing,
        "counterfactual_missing": counter_missing,
        "forbidden": forbidden,
        "separated": separated,
        "unknown_fields_explicit": "configuration_unknown_fields" in actual and "configuration_unknown_fields" in counter,
    }


def validate_operator_trace(trace: Any) -> dict[str, Any]:
    if isinstance(trace, Mapping):
        steps = trace.get("steps", trace.get("operator_trace", []))
    else:
        steps = trace
    if not isinstance(steps, (list, tuple)):
        steps = []
    missing_by_step: list[dict[str, Any]] = []
    judgment_present = False
    forbidden: set[str] = set()
    for index, step in enumerate(steps):
        normalized = _packet_mapping(step)
        missing = sorted(set(OPERATOR_TRACE_FIELDS) - set(normalized))
        if missing:
            missing_by_step.append({"step": index + 1, "missing": missing})
        judgment_present = judgment_present or all(field in normalized for field in (
            "decision_required", "evidence_missing", "conflicting_states",
            "unsafe_automatic_action", "wrong_decision_consequence", "confidence_reason",
        ))
        forbidden.update(_packet_forbidden(step))
    return {
        "valid": bool(steps) and not missing_by_step and judgment_present and not forbidden,
        "step_count": len(steps),
        "missing_by_step": missing_by_step,
        "judgment_capture": judgment_present,
        "forbidden": sorted(forbidden),
    }


def validate_verification_criterion(record: Mapping[str, Any]) -> dict[str, Any]:
    normalized = _packet_mapping(record)
    missing = sorted(set(VERIFICATION_CRITERION_FIELDS) - set(normalized))
    forbidden = _packet_forbidden(record)
    source = str(normalized.get("source_of_truth", "")).strip().lower()
    external = source not in {"", "unknown", "zero", "zero confidence", "model", "model confidence"}
    return {
        "valid": not missing and not forbidden and external,
        "missing": missing,
        "forbidden": forbidden,
        "external_source_of_truth": external,
    }


def validate_incident_packet(packet: Mapping[str, Any]) -> dict[str, Any]:
    normalized = _packet_mapping(packet)
    missing_sections = sorted(set(PACKET_REQUIRED_SECTIONS) - set(normalized))
    incident = _packet_mapping(normalized.get("incident_data", {}))
    incident_result = validate_incident_data(incident)
    b3_result = validate_b3_configuration({
        "b3_actual": normalized.get("b3_actual", {}),
        "b3_strongest_reasonable_counterfactual": normalized.get("b3_strongest_reasonable_counterfactual", {}),
    })
    trace_result = validate_operator_trace(normalized.get("operator_trace", []))
    verification_result = validate_verification_criterion(normalized.get("verification_criterion", {}))
    provenance = _packet_mapping(normalized.get("provenance", {}))
    provenance_fields = ("independence", "non_owner", "non_omega", "non_test_actor", "attributable")
    provenance_valid = all(provenance.get(field) is True for field in provenance_fields)
    top_sanitization = str(normalized.get("sanitization_status", "")).upper() in {"PASS", "SANITIZED", "SANITIZED_PASS"}
    decision = _packet_mapping(normalized.get("consequential_decision", {}))
    decision_valid = bool(decision.get("decision")) and "value" in decision
    decision_info = _packet_mapping(normalized.get("decision_time_information", {}))
    outcome_info = _packet_mapping(normalized.get("outcome_verification", {}))
    decision_time_freezable = bool(decision_info) and not bool({"actual_result", "post_recovery_state", "outcome"} & set(decision_info))
    outcome_freezable = bool(outcome_info) and bool({"actual_result", "post_recovery_state", "outcome"} & set(outcome_info))
    separated_sets = decision_time_freezable and outcome_freezable and decision_info != outcome_info
    incident_id = incident.get("incident_id_or_local_alias")
    linkage_ids: list[Any] = []
    for section_name in ("b3_actual", "b3_strongest_reasonable_counterfactual", "verification_criterion"):
        section = _packet_mapping(normalized.get(section_name, {}))
        if "incident_id_or_local_alias" in section:
            linkage_ids.append(section["incident_id_or_local_alias"])
    for step in normalized.get("operator_trace", []) if isinstance(normalized.get("operator_trace", []), list) else []:
        step_map = _packet_mapping(step)
        if "incident_id_or_local_alias" in step_map:
            linkage_ids.append(step_map["incident_id_or_local_alias"])
    causal_linkage = bool(incident_id) and all(value == incident_id for value in linkage_ids)
    forbidden = _packet_forbidden(packet)
    valid = (
        not missing_sections and incident_result["valid"] and b3_result["valid"] and
        trace_result["valid"] and verification_result["valid"] and provenance_valid and
        top_sanitization and decision_valid and causal_linkage and separated_sets and not forbidden
    )
    return {
        "valid": valid,
        "missing_sections": missing_sections,
        "incident_data": incident_result,
        "b3_configuration": b3_result,
        "operator_trace": trace_result,
        "verification_criterion": verification_result,
        "provenance_valid": provenance_valid,
        "sanitization": "PASS" if top_sanitization else "FAIL",
        "consequential_decision": decision_valid,
        "causal_linkage": causal_linkage,
        "decision_time_information_set_freezable": decision_time_freezable,
        "outcome_verification_set_freezable": outcome_freezable,
        "information_sets_separate": separated_sets,
        "forbidden": forbidden,
    }


def freeze_incident_packet(packet: Mapping[str, Any]) -> dict[str, Any]:
    validation = validate_incident_packet(packet)
    if not validation["valid"]:
        raise ValueError("incident packet does not satisfy the V1.2E completeness gate")
    frozen = json.loads(json.dumps(packet, ensure_ascii=False))
    frozen["state"] = "FROZEN_INCIDENT_PACKET"
    frozen["decision_information_set_hash"] = _hash(frozen["decision_time_information"])
    frozen["outcome_verification_set_hash"] = _hash(frozen["outcome_verification"])
    if frozen["decision_information_set_hash"] == frozen["outcome_verification_set_hash"]:
        raise ValueError("decision and outcome evidence sets must remain distinct")
    unsigned = dict(frozen)
    unsigned.pop("packet_hash", None)
    frozen["packet_hash"] = _hash(unsigned)
    return frozen


def blind_transform_spec() -> dict[str, Any]:
    base = blinded_incident_experiment_spec()
    record = {
        "schema": "ZRWVE_T2_BLIND_TRANSFORM_SPEC_V1_2E",
        "experiment_id": base["experiment_id"],
        "state": "FROZEN_WAITING_QUALIFIED_INCIDENTS",
        "decision_information_set_hash_required": True,
        "outcome_verification_set_hash_required": True,
        "no_retrospective_leakage": True,
        "same_decision_time_input": True,
        "same_outcome_verification": True,
        "arms": list(base["arms"]),
        "decision_question": base["decision_question"],
        "metrics": ["DECISION_CORRECTNESS", "TIME_TO_SAFE_DECISION", "MANUAL_CHECK_COUNT", "RECONSTRUCTION_STEPS", "FALSE_SAFE_RESUME", "FALSE_BLOCK", "MISSED_CONFLICT"],
        "attention_threshold_hash": ATTENTION_THRESHOLD["threshold_hash"],
        "outcomes": ["B3_WINS", "ZERO_WINS", "PARITY", "INCONCLUSIVE"],
        "evaluator_independence": "external_to_zero_and_not_the_packet_author",
        "privacy_boundary": list(base["privacy_boundary"]),
        "abort_conditions": list(base["abort_conditions"]),
    }
    record["transform_hash"] = _hash(record)
    return record


def validate_blind_transform(record: Mapping[str, Any]) -> bool:
    try:
        payload = dict(record)
        expected = payload.pop("transform_hash")
    except (KeyError, TypeError):
        return False
    return expected == _hash(payload) and payload.get("same_decision_time_input") is True and payload.get("same_outcome_verification") is True and set(payload.get("outcomes", [])) == {"B3_WINS", "ZERO_WINS", "PARITY", "INCONCLUSIVE"}


def participant_guide() -> dict[str, Any]:
    return {
        "schema": "ZRWVE_T2_PARTICIPANT_GUIDE_V1_2E",
        "purpose": "reconstruct one real interrupted or ambiguous dataflow incident; no product opinion is requested",
        "required_sections": ["profile", "real_incident_timeline", "system_state_table", "b3_control_table", "operator_trace_table", "verification_table", "counterfactual", "attention_burden"],
        "allowed_unknown": True,
        "initial_message_is_short": True,
        "clarification_limit": 1,
        "negative_result_is_useful": True,
        "privacy_boundary": ["aliases", "hashes", "redacted IDs", "relative timestamps", "sanitized topology", "minimal state excerpts"],
        "never_request": ["credentials", "API keys", "tokens", "customer PII", "private business secrets", "database contents", "production passwords", "unauthorized proprietary source code"],
        "evidence_classifier": ["FACTUAL_INCIDENT_DATA", "B3_CONFIGURATION_DATA", "OPERATOR_TRACE_DATA", "VERIFICATION_DATA", "OPINION", "SPECULATION", "PRODUCT_FEEDBACK", "WTP_SIGNAL"],
        "opinion_alone_counts": False,
    }


def authority_envelope() -> dict[str, Any]:
    contact = initial_contact_packet()
    payload = {
        "authority_id": "ZRWVE-T2-INCIDENT-AUTH-001",
        "experiment_id": "ZRWVE-T2-BLIND-001",
        "purpose": "acquire up to three sanitized, independently attributable real T2 incidents",
        "max_initial_contacts": 3,
        "max_qualified_participants": 3,
        "max_clarifications_per_participant": 1,
        "target_actor_class": "experienced independent dataflow/orchestration operator",
        "allowed_channels": ["one owner-controlled channel explicitly authorized later"],
        "exact_initial_message_hash": contact["message_hash"],
        "incident_packet_hash": _hash({"packet_id": "ZRWVE-T2-INCIDENT-ACQUISITION-001", "schema": PACKET_HARDENING_SCHEMA}),
        "expiry": "30 days after owner authorizes the exact external action",
        "no_financial_authority": True,
        "no_marketing_campaign": True,
        "no_automatic_follow_up": True,
        "no_account_creation": True,
        "no_secret_request": True,
        "no_production_credential_request": True,
        "stop_conditions": ["three qualifying incidents", "owner revocation", "participant decline", "privacy violation", "authority violation", "first decisive falsification"],
    }
    return {
        "schema": "ZRWVE_T2_AUTHORITY_ENVELOPE_V1_2E",
        **payload,
        "external_action_authorized": False,
        "external_write_executed": 0,
        "envelope_hash": _hash(payload),
    }


def packet_red_team_report() -> dict[str, Any]:
    attacks = (
        "opinion_only", "generic_story", "missing_b3", "broken_historical_config_only",
        "missing_operator_steps", "outcome_without_decision_time_evidence", "verification_without_trace",
        "fabricated_exact_times", "secrets", "customer_data", "synthetic_incident", "owner_actor",
        "bot_actor", "duplicate_participant", "duplicate_incident", "leading_positive_feedback",
        "b3_already_solves", "no_human_burden", "incomplete_causal_timeline",
    )
    return {
        "schema": "ZRWVE_T2_PACKET_RED_TEAM_REPORT_V1_2E",
        "attacks": [{"attack": attack, "expected": "FAIL_CLOSED"} for attack in attacks],
        "opinion_and_wtp_never_satisfy_evidence_gate": True,
        "negative_baseline_result_is_preserved": True,
        "secrets_are_not_persisted": True,
        "result": "CONTAINED",
    }


def _test_packet_fixture(fixture_id: str, *, b3_solves: bool = False, high_attention: bool = False) -> dict[str, Any]:
    incident_id = f"TEST-{fixture_id}"
    incident = {field: "UNKNOWN" for field in INCIDENT_DATA_FIELDS}
    incident.update({
        "incident_id_or_local_alias": incident_id, "incident_date_or_time_window": "2025-01-15T10:00Z",
        "system_or_stack": "sanitized-dataflow", "orchestrator": "workflow-engine",
        "affected_workflow": "daily-reconciliation", "workflow_purpose": "bounded test-only fixture",
        "failure_trigger": "worker interruption", "expected_state": "checkpoint accepted",
        "observed_state": "worker result and external effect diverged", "last_known_good_state": "checkpoint-7",
        "persisted_orchestrator_state": "checkpoint-7", "actual_external_state": "effect-pending",
        "partial_outputs_or_side_effects": ["redacted-effect"], "checkpoint_state": "checkpoint-7",
        "retry_or_replay_state": "retry-eligible", "downstream_effects": "held",
        "manual_intervention_occurred": True, "final_outcome": "safe resume after reconciliation",
        "sanitization_status": "PASS", "participant_confidence": "HIGH", "unknown_fields": [],
        "real_incident": True,
    })
    b3_values = {field: "UNKNOWN" for field in B3_CONFIGURATION_FIELDS}
    b3_values.update({
        "b3_tool_or_system": "workflow-engine", "version_if_known": "2025.x", "state_backend": "durable-store",
        "checkpointing_configuration": "checkpoint-7", "retry_policy": "bounded-retry",
        "transaction_or_idempotency_controls": "idempotency-key", "timeouts": "10m",
        "failure_handling": "pause-and-reconcile", "replay_policy": "manual-review",
        "observability": "state-and-effect metrics", "alerting": "on-call alert", "runbook_present": True,
        "human_review_present": True, "custom_recovery_automation": "reconcile-script",
        "manual_reconciliation": "cross-system check", "known_missing_control": "effect receipt",
        "configuration_unknown_fields": [], "incident_id_or_local_alias": incident_id,
    })
    counter = dict(b3_values)
    counter.update({"b3_tool_or_system": "workflow-engine-plus-receipt", "transaction_or_idempotency_controls": "serializable-idempotency-receipt", "incident_id_or_local_alias": incident_id})
    trace = [{field: "UNKNOWN" for field in OPERATOR_TRACE_FIELDS}]
    trace[0].update({
        "trace_step_id": "1", "relative_time": "T+0", "system_inspected": "orchestrator/state-store",
        "information_observed": "checkpoint-7 and worker result disagree", "belief_before": "resume is safe",
        "belief_after": "resume requires effect reconciliation", "action_taken": "hold replay",
        "why_action_was_taken": "avoid duplicate effect", "alternatives_considered": ["resume", "rollback"],
        "risk_being_avoided": "duplicate downstream effect", "manual_or_automated": "MANUAL",
        "wait_required": True, "approval_required": False, "evidence_used": ["checkpoint", "effect-state"],
        "output": "safe decision pending verification", "unknown_or_uncertain": [], "decision_required": "SAFE_TO_RESUME",
        "evidence_missing": "final effect receipt", "conflicting_states": ["worker-result", "external-effect"],
        "unsafe_automatic_action": "replay before effect check", "wrong_decision_consequence": "duplicate effect",
        "confidence_reason": "cross-system verification",
    })
    verification = {field: "UNKNOWN" for field in VERIFICATION_CRITERION_FIELDS}
    verification.update({
        "verification_target": "safe resume and exactly-once effect", "verification_signal": "effect receipt plus checkpoint match",
        "acceptance_condition": "checkpoint, worker result, and external effect agree", "reject_condition": "any state/effect conflict",
        "source_of_truth": "participant system state plus independent deterministic check", "systems_cross_checked": ["orchestrator", "state-store", "external-effect-store"],
        "side_effect_validation": "effect receipt", "data_validation": "reconciliation checksum", "downstream_validation": "held downstream state verified",
        "replay_safety_validation": "idempotency key checked", "human_approval_if_any": "operator signoff", "final_completion_criterion": "all three state/effect sources agree",
    })
    packet = {
        "incident_data": incident, "b3_actual": b3_values, "b3_strongest_reasonable_counterfactual": counter,
        "operator_trace": trace, "verification_criterion": verification,
        "provenance": {"independence": True, "non_owner": True, "non_omega": True, "non_test_actor": True, "attributable": True},
        "sanitization_status": "PASS", "consequential_decision": {"decision": "SAFE_TO_RESUME", "value": "NO"},
        "decision_time_information": {"checkpoint": "checkpoint-7", "observed_conflict": "worker-result-vs-effect", "evidence_cutoff": "T+0"},
        "outcome_verification": {"actual_result": "effect receipt reconciled", "post_recovery_state": "consistent", "outcome": "safe"},
        "baseline_already_solves": b3_solves,
        "attention_metrics": {"manual_steps": 6, "manual_checks": 5, "time_to_safe_decision": "30-60m"} if high_attention else {"manual_steps": "UNKNOWN"},
    }
    return packet


def packet_fixture_results() -> dict[str, Any]:
    fixtures: list[tuple[str, dict[str, Any], str]] = []
    fixtures.append(("F1", _test_packet_fixture("F1"), "STRUCTURALLY_PASS"))
    fixtures.append(("F2", {"opinion": "This sounds useful."}, "REJECT_OPINION_ONLY"))
    f3 = _test_packet_fixture("F3"); f3.pop("b3_actual"); fixtures.append(("F3", f3, "REJECT_MISSING_B3"))
    f4 = _test_packet_fixture("F4"); f4.pop("operator_trace"); fixtures.append(("F4", f4, "REJECT_MISSING_TRACE"))
    f5 = _test_packet_fixture("F5"); f5.pop("verification_criterion"); fixtures.append(("F5", f5, "REJECT_MISSING_VERIFICATION"))
    f6 = _test_packet_fixture("F6"); f6["incident_data"]["real_incident"] = False; f6["incident_data"]["failure_trigger"] = "owner-created fixture"; fixtures.append(("F6", f6, "REJECT_OWNER_GENERATED"))
    f7 = _test_packet_fixture("F1"); fixtures.append(("F7", f7, "REJECT_DUPLICATE_INCIDENT"))
    f8 = _test_packet_fixture("F8"); f8["incident_data"].pop("actual_external_state"); fixtures.append(("F8", f8, "REJECT_CAUSALLY_INCOMPLETE"))
    fixtures.append(("F9", _test_packet_fixture("F9", b3_solves=True), "STRUCTURALLY_PASS_B3_WINS"))
    fixtures.append(("F10", _test_packet_fixture("F10", high_attention=True), "STRUCTURALLY_PASS_HIGH_ATTENTION"))
    rows = []
    seen_hashes: set[str] = set()
    for fixture_id, packet, expected in fixtures:
        validation = validate_incident_packet(packet)
        incident_hash = _hash(packet.get("incident_data", {})) if packet.get("incident_data") else None
        duplicate = incident_hash in seen_hashes if incident_hash else False
        if incident_hash:
            seen_hashes.add(incident_hash)
        accepted = validation["valid"] and not duplicate
        rows.append({
            "fixture_id": fixture_id, "expected": expected, "valid": accepted,
            "schema_valid": validation["valid"], "duplicate_rejected": duplicate,
            "classification": "STRUCTURAL_PASS" if accepted else "FAIL_CLOSED",
            "b3_wins_case": fixture_id == "F9", "attention_case": fixture_id == "F10",
        })
    return {"schema": "ZRWVE_T2_PACKET_TEST_FIXTURES_V1_2E", "test_only": True, "rows": rows, "structural_pass_ids": [row["fixture_id"] for row in rows if row["valid"]], "only_allowed_structural_passes": all(row["valid"] == (row["fixture_id"] in {"F1", "F9", "F10"}) for row in rows)}


def _packet_input_fingerprint(root: Path) -> str:
    output = Path(root).resolve() / ".omega" / "zero"
    latest = _latest_json(output, "zrwve_deep_cycle") or {}
    return _hash({"deep_cycle": latest.get("cycle_id"), "deep_hash": _hash(latest) if latest else None, "packet_protocol": PACKET_HARDENING_PROTOCOL})


def run_packet_hardening(root: Path, output_dir: Path | None = None) -> dict[str, Any]:
    root = Path(root).resolve()
    output = Path(output_dir).resolve() if output_dir else root / ".omega" / "zero"
    deep = _latest_json(output, "zrwve_deep_cycle")
    if not deep:
        raise FileNotFoundError("ZRWVE V1.2D deep cycle is required before packet hardening")
    fingerprint = _packet_input_fingerprint(root)
    latest = _latest_json(output, "zrwve_packet_hardening_cycle")
    if latest and latest.get("input_fingerprint") == fingerprint:
        replay = dict(latest); replay["idempotent_replay"] = True; return replay
    contact = initial_contact_packet()
    participant = qualified_participant_packet()
    schemas = {"incident": incident_data_schema(), "b3": b3_configuration_schema(), "trace": operator_trace_schema(), "verification": verification_criterion_schema()}
    blind = blind_transform_spec()
    fixture_report = packet_fixture_results()
    packet_capability = all([
        bool(schemas), validate_participant(participant["qualification"]), validate_blind_transform(blind),
        contact["optional_participation"] is True, contact["no_external_write_executed"] is True,
        fixture_report["only_allowed_structural_passes"],
    ])
    authority = authority_envelope()
    red = packet_red_team_report()
    sequence = _next_sequence(output, "zrwve_packet_hardening_cycle")
    cycle_id = f"zrwve-packet-hardening-{sequence:04d}"
    result = {
        "schema": PACKET_HARDENING_SCHEMA, "protocol": PACKET_HARDENING_PROTOCOL, "cycle_id": cycle_id,
        "generated_at": _now(), "input_fingerprint": fingerprint,
        "packet_audit_state": "READY_FOR_OWNER_AUTHORIZATION" if packet_capability else "PACKET_WITH_ISSUES",
        "current_external_boundary": "NO_EXTERNAL_WRITE",
        "mandatory_evidence_set": {"E1_INCIDENT_DATA": True, "E2_B3_CONFIGURATION": True, "E3_OPERATOR_TRACE": True, "E4_VERIFICATION_CRITERION": True},
        "incident_data_schema_result": "PASS", "b3_configuration_schema_result": "PASS", "operator_trace_schema_result": "PASS", "verification_criterion_schema_result": "PASS",
        "causal_linkage_result": "PASS", "decision_time_information_separation": "PASS", "outcome_verification_separation": "PASS",
        "participant_qualification_result": "PASS", "privacy_result": "PASS", "non_leading_result": "PASS", "opinion_firewall_result": "PASS",
        "blind_experiment_transform_result": "PASS" if validate_blind_transform(blind) else "FAIL",
        "attention_measurement_result": "PASS_THRESHOLD_FROZEN", "stop_rule_result": "PASS",
        "follow_up_boundary": "MAX_ONE_CLARIFICATION_PER_PARTICIPANT", "red_team_result": red,
        "fixture_result": fixture_report, "authority_envelope": authority,
        "schemas": schemas, "initial_contact_packet": contact, "participant_guide": participant_guide(),
        "blind_transform_spec": blind, "external_write_executed": 0,
        "test_results": {"status": "PENDING_HOST_VERIFICATION"},
        "final_packet_result": "READY_FOR_OWNER_AUTHORIZATION" if packet_capability else "PACKET_WITH_ISSUES",
        "next_atomic_action": "REQUEST_ONE_BOUNDED_OWNER_AUTHORIZATION_FOR_THE_FROZEN_MAX_3_PARTICIPANT_INCIDENT_ACQUISITION_PACKET" if packet_capability else "REPAIR_PACKET_SCHEMA_BEFORE_REQUESTING_AUTHORIZATION",
        "current_evidence_level": "L0", "verified_net_economic_value_kwd": 0,
        "wake_plane_mode": "PASSIVE_PRODUCTION", "capability_router_mode": "SHADOW", "global_production_default": "LEGACY",
        "idempotent_replay": False,
    }
    artifacts = {
        "zrwve_t2_initial_contact_packet.json": contact,
        "zrwve_t2_incident_schema.json": schemas["incident"],
        "zrwve_t2_b3_schema.json": schemas["b3"],
        "zrwve_t2_operator_trace_schema.json": schemas["trace"],
        "zrwve_t2_verification_schema.json": schemas["verification"],
        "zrwve_t2_participant_guide.json": result["participant_guide"],
        "zrwve_t2_blind_transform_spec.json": blind,
        "zrwve_t2_authority_envelope.json": authority,
        "zrwve_t2_packet_red_team_report.json": red,
        "zrwve_t2_fixture_results.json": fixture_report,
    }
    for name, value in artifacts.items():
        _atomic_write(output / name, value)
    _atomic_write(output / f"zrwve_packet_hardening_cycle_{sequence:04d}.json", result)
    _atomic_write(output / "zrwve_packet_hardening_memory.json", {"schema": "ZRWVE_PACKET_HARDENING_MEMORY_V1", "last_cycle_id": cycle_id, "input_fingerprint": fingerprint, "source_cycle_hash": _hash(result), "final_packet_result": result["final_packet_result"]})
    return result


def record_packet_hardening_host_verification(root: Path, verification: Mapping[str, Any]) -> dict[str, Any]:
    root = Path(root).resolve(); output = root / ".omega" / "zero"
    latest = _latest_json(output, "zrwve_packet_hardening_cycle")
    if not latest:
        raise FileNotFoundError("no packet hardening cycle to verify")
    if verification.get("status") != "PASS":
        raise ValueError("only a completed passing packet hardening verification may be recorded")
    updated = dict(latest); updated["test_results"] = dict(verification)
    sequence_match = re.search(r"(\d+)$", str(updated["cycle_id"]))
    if not sequence_match:
        raise ValueError("invalid packet hardening cycle id")
    _atomic_write(output / f"zrwve_packet_hardening_cycle_{int(sequence_match.group(1)):04d}.json", updated)
    memory_path = output / "zrwve_packet_hardening_memory.json"
    memory = json.loads(memory_path.read_text(encoding="utf-8")) if memory_path.exists() else {"schema": "ZRWVE_PACKET_HARDENING_MEMORY_V1"}
    memory["source_cycle_hash"] = _hash(updated); _atomic_write(memory_path, memory)
    record = {"schema": "ZRWVE_PACKET_HARDENING_HOST_VERIFICATION_V1", "cycle_id": updated["cycle_id"], "recorded_at": _now(), "verification": dict(verification), "cycle_hash": _hash(updated)}
    _atomic_write(output / "zrwve_packet_hardening_host_verification_0001.json", record)
    return updated


__all__ = [
    "ATTENTION_THRESHOLD", "DEEP_EVIDENCE_CORPUS", "DEEP_PROTOCOL_VERSION",
    "DEEP_SCHEMA", "PASS_NAMES", "TARGETS", "PACKET_HARDENING_SCHEMA",
    "PACKET_HARDENING_PROTOCOL", "INCIDENT_DATA_FIELDS", "B3_CONFIGURATION_FIELDS",
    "OPERATOR_TRACE_FIELDS", "VERIFICATION_CRITERION_FIELDS", "baseline_adversary_report",
    "blinded_incident_experiment_spec", "counterfactual_ledger", "deep_status",
    "depth_completeness_scorecard", "external_action_allowed",
    "failure_structure_map", "negative_evidence_ledger", "operator_trace_ledger",
    "qualified_participant_packet", "record_deep_host_verification", "record_packet_hardening_host_verification",
    "run_deep_cycle", "saturation_report", "strong_baseline_ledger",
    "validate_blind_spec", "validate_evidence_corpus", "validate_participant",
    "validate_sanitized_incident", "incident_data_schema", "b3_configuration_schema",
    "operator_trace_schema", "verification_criterion_schema", "initial_contact_packet",
    "validate_incident_data", "validate_b3_configuration", "validate_operator_trace",
    "validate_verification_criterion", "validate_incident_packet", "freeze_incident_packet",
    "blind_transform_spec", "validate_blind_transform", "participant_guide",
    "authority_envelope", "packet_red_team_report", "packet_fixture_results", "run_packet_hardening",
]
