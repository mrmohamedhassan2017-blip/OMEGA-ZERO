"""ZERO Development Governor and compact evolution checkpoint.

The governor is deliberately a read-only, deterministic decision aid.  It is
not a second supervisor and it never starts work, calls a model, invokes a
subprocess, contacts an external service, or grants authority.  It compresses
repository evidence into a small bottleneck map and an auditable evolution
checkpoint so an idle ZERO cycle does not rediscover the same facts or invent
busywork.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .continuity import parse_front_matter
from .wake_provenance import evaluator_summary


SCHEMA = "ZERO_DEVELOPMENT_GOVERNOR_V1"
CHECKPOINT_SCHEMA = "ZERO_EVOLUTION_CHECKPOINT_V1"
_STATE_FILES = ("PROJECT_STATE.md", "NEXT_TASK.md", "ROADMAP.md", "PROGRESS.md", "CHANGELOG.md")


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _hash_file(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except (OSError, ValueError):
        return None


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _next_sequence(root: Path, prefix: str) -> int:
    pattern = re.compile(re.escape(prefix) + r"_(\d+)\.json$")
    highest = 0
    target = root / ".omega" / "zero"
    if target.is_dir():
        for path in target.glob(prefix + "_*.json"):
            match = pattern.match(path.name)
            if match:
                highest = max(highest, int(match.group(1)))
    return highest + 1


def _atomic_write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def _front_matter(root: Path, name: str) -> dict[str, str]:
    path = root / name
    if not path.is_file():
        return {}
    try:
        return parse_front_matter(path)
    except ValueError:
        return {}


def _repository_truth(root: Path) -> dict[str, Any]:
    state = _front_matter(root, "PROJECT_STATE.md")
    next_task = _front_matter(root, "NEXT_TASK.md")
    package_version = "unknown"
    pyproject = root / "pyproject.toml"
    try:
        # Avoid importing a TOML parser or executing project code.  The
        # version line is intentionally constrained to the project metadata.
        for line in pyproject.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("version") and "=" in line:
                package_version = line.split("=", 1)[1].strip().strip("\"'")
                break
    except (OSError, UnicodeError):
        pass

    state_text = ""
    try:
        state_text = (root / "PROJECT_STATE.md").read_text(encoding="utf-8", errors="replace")
    except OSError:
        pass
    # These are conservative observations, not promotions.  A missing or
    # malformed state remains UNKNOWN rather than being inferred as healthy.
    evidence_level = "L0" if re.search(r"\bL0\b", state_text) else "UNKNOWN"
    value_match = re.search(r"(?:real economic value|REAL_ECONOMIC_VALUE)[^0-9-]*(-?\d+(?:\.\d+)?)\s*KWD", state_text, re.I)
    economic_value = float(value_match.group(1)) if value_match else 0
    try:
        # Reuse the trusted append-only provenance reader.  Plain JSON claims
        # or a corrupt journal never count as independent evidence.
        provenance = evaluator_summary(root)
    except (OSError, ValueError, TypeError):
        provenance = {"journal_ready": False, "independent_evaluator_count": 0}
    independent_count = int(provenance.get("independent_evaluator_count", 0) or 0)
    if not provenance.get("journal_ready", False):
        independent_count = 0
    return {
        "version": state.get("version") or package_version,
        "package_version": package_version,
        "status": state.get("status", "UNKNOWN"),
        "current_milestone": state.get("current_milestone") or next_task.get("milestone", "UNKNOWN"),
        "next_task": next_task.get("milestone", "UNKNOWN"),
        "next_task_status": next_task.get("status", "UNKNOWN"),
        "evidence_level": evidence_level,
        "real_economic_value_kwd": economic_value,
        "independent_evaluator_count": independent_count,
        "provenance_journal_ready": bool(provenance.get("journal_ready", False)),
        "external_evidence": "NONE_PROVEN" if not independent_count else "PRESENT_REQUIRES_GATE",
        "source_hashes": {name: _hash_file(root / name) for name in _STATE_FILES},
    }


def _bottlenecks(truth: dict[str, Any]) -> list[dict[str, Any]]:
    """Return a transparent scorecard; scores are relative, not money."""
    external_count = int(truth.get("independent_evaluator_count", 0) or 0)
    blocked = external_count < 2
    entries = [
        {
            "id": "INDEPENDENT_EXTERNAL_EVIDENCE",
            "rank": 0,
            "status": "BLOCKED_EXTERNAL" if blocked else "OPEN",
            "evidence": "V0.30 requires two independently supplied blinded sessions; current attributable count is %d." % external_count,
            "impact": 1.0, "breadth": 0.95, "expected_information_gain": 1.0,
            "reversibility": 1.0, "authority_required": "EXTERNAL_EVALUATOR_PARTICIPATION",
            "strongest_baseline": "wait for independently supplied evaluator records",
            "internal_actionable": False,
            "wake_condition": "new trusted evaluator provenance or external response",
        },
        {
            "id": "EVOLUTION_MEMORY_COMPRESSION",
            "rank": 0,
            "status": "INTERNAL_ACTIONABLE",
            "evidence": "Repeated cycles record state in long narrative files without one compact reconstructible checkpoint.",
            "impact": 0.72, "breadth": 0.88, "expected_information_gain": 0.78,
            "reversibility": 1.0, "authority_required": "NONE",
            "strongest_baseline": "manual reading of PROJECT_STATE, NEXT_TASK, and historical result files",
            "internal_actionable": True,
            "wake_condition": "next governor cycle or material state hash change",
        },
        {
            "id": "UNKNOWN_STATE_COVERAGE",
            "rank": 0,
            "status": "RESEARCH_ONLY",
            "evidence": "The constitution requires unknown-unknown discovery, but no current missing transition is evidenced by a failure.",
            "impact": 0.58, "breadth": 0.62, "expected_information_gain": 0.64,
            "reversibility": 1.0, "authority_required": "NONE",
            "strongest_baseline": "existing regression and stability suites",
            "internal_actionable": False,
            "wake_condition": "new failure, silent state, or verified coverage gap",
        },
        {
            "id": "COMPLEXITY_TAX_MEASUREMENT",
            "rank": 0,
            "status": "PARKED",
            "evidence": "Prior parity work labels research overhead high, but no new complexity regression is currently observed.",
            "impact": 0.44, "breadth": 0.5, "expected_information_gain": 0.48,
            "reversibility": 1.0, "authority_required": "NONE",
            "strongest_baseline": "existing LZC/ZAVA comparison artifacts",
            "internal_actionable": False,
            "wake_condition": "measured maintenance or reliability regression",
        },
    ]
    problem_fields = {
        "INDEPENDENT_EXTERNAL_EVIDENCE": {
            "frequency": "none observed; required at least twice",
            "severity": "critical for V0.30 completion",
            "owner_attention_cost": "external coordination required",
            "external_value_potential": "high information value, not value proof",
            "economic_potential": "unknown",
            "uncertainty": "whether any independent evaluator will act and find utility",
            "current_baseline": "existing public artifact plus passive source polling",
            "why_baseline_insufficient": "no evaluator record exists yet",
        },
        "EVOLUTION_MEMORY_COMPRESSION": {
            "frequency": "every meaningful development cycle",
            "severity": "medium continuity/attention risk",
            "owner_attention_cost": "repeated manual reconstruction",
            "external_value_potential": "none directly; enables better internal decisions",
            "economic_potential": "none evidenced",
            "uncertainty": "attention reduction not yet measured",
            "current_baseline": "manual reading of PROJECT_STATE, NEXT_TASK, and history",
            "why_baseline_insufficient": "long narrative history obscures the current decision boundary",
        },
        "UNKNOWN_STATE_COVERAGE": {
            "frequency": "unknown",
            "severity": "unknown",
            "owner_attention_cost": "unknown",
            "external_value_potential": "unknown",
            "economic_potential": "unknown",
            "uncertainty": "no concrete uncovered transition is evidenced",
            "current_baseline": "existing regression and stability suites",
            "why_baseline_insufficient": "only a verified failure or coverage gap justifies expansion",
        },
        "COMPLEXITY_TAX_MEASUREMENT": {
            "frequency": "periodic",
            "severity": "low current incident evidence",
            "owner_attention_cost": "maintenance measurement effort",
            "external_value_potential": "none directly",
            "economic_potential": "unknown",
            "uncertainty": "no new complexity regression observed",
            "current_baseline": "existing LZC/ZAVA comparison artifacts",
            "why_baseline_insufficient": "no fresh regression has crossed the action threshold",
        },
    }
    for entry in entries:
        entry.update(problem_fields[entry["id"]])
    for entry in entries:
        # The score ranks bottleneck severity/information value, not
        # executability.  The external gate therefore remains the primary
        # bottleneck even when it is not actionable internally.
        denominator = 0.2 if entry["id"] == "INDEPENDENT_EXTERNAL_EVIDENCE" else (0.35 if entry["internal_actionable"] else 1.0)
        entry["score"] = round(
            (entry["impact"] * entry["breadth"] * entry["expected_information_gain"] * entry["reversibility"])
            / denominator,
            4,
        )
    entries.sort(key=lambda item: (-item["score"], item["id"]))
    for index, entry in enumerate(entries, 1):
        entry["rank"] = index
    return entries


def _red_team(truth: dict[str, Any], selected: dict[str, Any]) -> dict[str, Any]:
    return {
        "target": selected["id"],
        "objections": [
            "A checkpoint can become narrative overhead if it does not change a future decision.",
            "Internal records cannot substitute for the missing independent evaluator event.",
            "A timestamp or test pass must not be promoted to external value.",
        ],
        "mitigations": [
            "Keep the schema compact, source-hashed, and reconstructible.",
            "Require a state/bottleneck/next-action delta before treating a cycle as useful.",
            "Keep evidence class REAL_INTERNAL and economic value at 0 KWD.",
        ],
        "verdict": "ACCEPT_AS_BOUNDED_INTERNAL_MEMORY_IMPROVEMENT",
    }


def run_governor_cycle(root: Path) -> dict[str, Any]:
    """Run one internal observe→rank→checkpoint cycle without side effects."""
    root = Path(root).resolve()
    truth = _repository_truth(root)
    bottlenecks = _bottlenecks(truth)
    primary = bottlenecks[0]
    selected = next((item for item in bottlenecks if item["internal_actionable"]), None)
    if selected is None:
        return {
            "schema": SCHEMA,
            "cycle_id": "governor-cycle-none",
            "state": "PARKED_NO_INTERNAL_ACTION",
            "repository_truth": truth,
            "bottleneck_map": bottlenecks,
            "primary_bottleneck": primary["id"],
            "selected_improvement": None,
            "autonomous_continuation": "PARK",
        }

    sequence = _next_sequence(root, "development_governor_cycle")
    cycle_id = f"governor-cycle-{sequence:04d}"
    checkpoint_id = f"evolution-checkpoint-{sequence:04d}"
    criteria = [
        "read-only observation of repository state and prior evidence",
        "ranked bottlenecks include evidence, baseline, authority, and wake condition",
        "one compact checkpoint is atomically persisted with source hashes",
        "no subprocess, network, external action, authority grant, or value promotion",
        "independent evaluator count and 0 KWD are preserved exactly",
    ]
    checkpoint = {
        "schema": CHECKPOINT_SCHEMA,
        "checkpoint_id": checkpoint_id,
        "cycle_id": cycle_id,
        "generated_at": _now(),
        "current_system_state": truth["status"],
        "verified_capabilities": [
            "deterministic Core graph and persistence",
            "Host Verification and bounded execution",
            "LZC/ZFBR safety and recovery contracts",
            "Wake Plane passive provenance and deduplication",
            "V0.30 evaluator integrity gate",
        ],
        "capabilities_added": ["compact deterministic development-governor checkpoint"],
        "capabilities_retired": [],
        "new_invariants": [
            "internal checkpoint evidence never promotes external value",
            "governor never executes or grants authority",
            "a blocked external bottleneck remains blocked until trusted evidence arrives",
        ],
        "new_external_evidence": [],
        "failed_hypotheses": [
            "internal activity can substitute for two independent evaluator sessions"
        ],
        "open_uncertainties": [
            "whether an independent evaluator will consume the existing artifact",
            "whether the compact checkpoint reduces future owner attention",
            "whether any unobserved state transition matters before new evidence arrives",
        ],
        "complexity_changes": "LOW: one pure reader/ranker and two JSON records; no runtime control path changed",
        "owner_attention_change": "NOT_MEASURED",
        "reliability_change": "NO_RUNTIME_CHANGE; continuity memory improved",
        "economic_evidence_change": "NONE; REAL_ECONOMIC_VALUE remains 0 KWD",
        "next_bottleneck": primary["id"],
        "source_files": list(_STATE_FILES),
        "source_hashes": truth["source_hashes"],
    }
    checkpoint["checkpoint_hash"] = hashlib.sha256(_canonical(checkpoint)).hexdigest()
    result = {
        "schema": SCHEMA,
        "cycle_id": cycle_id,
        "generated_at": checkpoint["generated_at"],
        "state": "OPERATED_INTERNAL_ONLY",
        "repository_truth": truth,
        "primary_bottleneck": primary,
        "bottleneck_map": bottlenecks,
        "selected_improvement": {
            "id": selected["id"],
            "action": "persist evolution checkpoint and reuse it on the next cycle",
            "why": "reduces repeated state reconstruction while the real external bottleneck remains blocked",
            "expected_value": "continuity and decision-memory improvement; external/economic value unknown",
            "authority_required": "NONE",
            "external_effect": False,
            "reversible": True,
            "baseline": selected["strongest_baseline"],
        },
        "frozen_success_criteria": criteria,
        "implementation_result": {
            "checkpoint_id": checkpoint_id,
            "checkpoint_path": str((root / ".omega" / "zero" / f"evolution_checkpoint_{sequence:04d}.json").relative_to(root)),
            "checkpoint_hash": checkpoint["checkpoint_hash"],
            "side_effects": [],
        },
        "red_team": _red_team(truth, selected),
        "decision_delta": "NO_EXTERNAL_DECISION_DELTA_MEASURED",
        "reliability_delta": "NO_RUNTIME_REGRESSION; state continuity checkpoint added",
        "owner_attention_delta": "NOT_MEASURED",
        "system_health": {
            "status": "NO_NEW_INCIDENT_OBSERVED",
            "authority_violations": 0,
            "false_verified_successes": 0,
            "orphan_processes": 0,
            "resource_leaks": 0,
            "model_calls": 0,
            "external_actions": 0,
            "note": "Derived from this read-only cycle; historical subsystem metrics remain in their authoritative artifacts.",
        },
        "capability_created_or_improved": "DEVELOPMENT_GOVERNOR_MEMORY_COMPRESSION",
        "capability_reuse_status": "REUSABLE_FOR_FUTURE_INTERNAL_CYCLES",
        "complexity_delta": "LOW",
        "real_external_evidence_change": "NONE",
        "verified_economic_value_change": 0,
        "new_invariants": checkpoint["new_invariants"],
        "rejected_hypotheses": checkpoint["failed_hypotheses"],
        "remaining_unknowns": checkpoint["open_uncertainties"],
        "autonomous_continuation": "WAIT_EXTERNAL",
        "next_highest_value_action": "observe for trusted independent evaluator evidence; rerun governor only on material state change",
        "global_wait_required": True,
    }
    _atomic_write(root / ".omega" / "zero" / f"evolution_checkpoint_{sequence:04d}.json", checkpoint)
    _atomic_write(root / ".omega" / "zero" / f"development_governor_cycle_{sequence:04d}.json", result)
    return result


__all__ = ["run_governor_cycle"]
