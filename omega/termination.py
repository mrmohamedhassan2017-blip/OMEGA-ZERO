from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from math import isfinite
from statistics import mean
from typing import Iterable


class StopReason(str, Enum):
    CONTINUE = "CONTINUE"
    GOAL_REACHED = "GOAL_REACHED"
    DIMINISHING_RETURNS = "DIMINISHING_RETURNS"
    LOCAL_OPTIMUM = "LOCAL_OPTIMUM"
    NO_NOVEL_MUTATIONS = "NO_NOVEL_MUTATIONS"
    RESOURCE_EXHAUSTION = "RESOURCE_EXHAUSTION"
    REGRESSION_RISK = "REGRESSION_RISK"
    EVALUATION_UNCERTAINTY = "EVALUATION_UNCERTAINTY"


@dataclass(frozen=True)
class Observation:
    value: float
    cost: float
    novelty: float
    regression_risk: float
    uncertainty: float
    resources_left: float
    tests_passed: bool = True


@dataclass(frozen=True)
class Policy:
    name: str = "HYBRID_EVSI"
    goal: float = 1.0
    min_gain_per_cost: float = .01
    risk_limit: float = .20
    uncertainty_limit: float = .35
    novelty_floor: float = .05
    window: int = 4
    restart_budget: int = 2


def decide(history: Iterable[Observation], policy: Policy = Policy(), restarts_used: int = 0) -> dict:
    h = list(history)
    invalid_policy = _invalid_policy(policy, restarts_used)
    if invalid_policy:
        return _result(
            StopReason.EVALUATION_UNCERTAINTY,
            "Termination policy contains invalid parameters.",
            {"observations": len(h), "invalid_policy": invalid_policy,
             "policy": _policy_evidence(policy, restarts_used)},
        )
    if not h:
        return _result(StopReason.EVALUATION_UNCERTAINTY, "No observations exist.",
                       {"policy": _policy_evidence(policy, restarts_used)})
    invalid = _invalid_measurements(h)
    if invalid:
        return _result(
            StopReason.EVALUATION_UNCERTAINTY,
            "Observations contain invalid or non-finite measurements.",
            {"observations": len(h), "invalid_measurements": invalid,
             "policy": _policy_evidence(policy, restarts_used)},
        )
    x = h[-1]
    evidence = {"observations": len(h), "value": x.value, "resources_left": x.resources_left,
                "regression_risk": x.regression_risk, "uncertainty": x.uncertainty,
                "tests_passed": x.tests_passed,
                "policy": _policy_evidence(policy, restarts_used)}
    if x.resources_left <= 0:
        return _result(StopReason.RESOURCE_EXHAUSTION, "No authorized resource remains.", evidence)
    if not x.tests_passed or x.regression_risk >= policy.risk_limit:
        return _result(StopReason.REGRESSION_RISK, "Candidate exceeds the frozen safety boundary.", evidence)
    if x.value >= policy.goal and x.uncertainty < policy.uncertainty_limit:
        return _result(StopReason.GOAL_REACHED, "Goal is met with bounded evaluation uncertainty.", evidence)
    if x.uncertainty >= policy.uncertainty_limit:
        return _result(StopReason.EVALUATION_UNCERTAINTY, "Evidence cannot distinguish progress from noise.", evidence)
    w = h[-policy.window:]
    max_novelty = max(o.novelty for o in w)
    evidence["window_observations"] = len(w)
    evidence["max_novelty"] = max_novelty
    if len(w) >= policy.window and max_novelty <= 1e-9:
        return _result(StopReason.NO_NOVEL_MUTATIONS, "Recent mutations are behaviorally redundant.", evidence)
    if len(w) >= policy.window:
        gains = [max(0.0, b.value-a.value) / max(b.cost, 1e-9) for a, b in zip(w, w[1:])]
        evidence["mean_gain_per_cost"] = mean(gains)
        if mean(gains) < policy.min_gain_per_cost:
            reason = StopReason.LOCAL_OPTIMUM if max_novelty >= policy.novelty_floor else StopReason.DIMINISHING_RETURNS
            if reason == StopReason.LOCAL_OPTIMUM and restarts_used < policy.restart_budget:
                return _result(StopReason.CONTINUE, "Escape local optimum with one bounded diverse restart.", evidence,
                               action="DIVERSIFY_RESTART")
            return _result(reason, "Expected marginal value is below continuation cost.", evidence)
    return _result(StopReason.CONTINUE, "Expected information or value remains positive.", evidence)


def compare_policies(fixtures: list[dict], policies: list[Policy]) -> dict:
    rows = []
    for p in policies:
        correct = unsafe = waste = 0
        for f in fixtures:
            got = decide(f["history"], p, f.get("restarts_used", 0))["reason"]
            correct += got == f["expected"]
            unsafe += got == StopReason.CONTINUE.value and f["expected"] in {
                StopReason.REGRESSION_RISK.value,
                StopReason.RESOURCE_EXHAUSTION.value,
                StopReason.EVALUATION_UNCERTAINTY.value,
            }
            waste += got == StopReason.CONTINUE.value and f["expected"] != StopReason.CONTINUE.value
        utility = correct * 10 - unsafe * 100 - waste * 2
        rows.append({"policy": p.name, "correct": correct, "unsafe_continuations": unsafe,
                     "wasteful_continuations": waste, "utility": utility})
    rows.sort(key=lambda r: (-r["utility"], -r["correct"], r["policy"]))
    return {"winner": rows[0]["policy"], "results": rows, "baseline_unchanged": True}


def mutate_policy(baseline: Policy, fixtures: list[dict]) -> dict:
    candidates = [baseline,
                  replace(baseline, name="LOWER_UNCERTAINTY", uncertainty_limit=.25),
                  replace(baseline, name="STRICTER_RISK", risk_limit=.10),
                  replace(baseline, name="HIGHER_EVSI_BAR", min_gain_per_cost=.03)]
    comparison = compare_policies(fixtures, candidates)
    winner = next(p for p in candidates if p.name == comparison["winner"])
    winner_result = next(r for r in comparison["results"] if r["policy"] == winner.name)
    baseline_result = next(r for r in comparison["results"] if r["policy"] == baseline.name)
    accepted = (
        winner != baseline
        and winner_result["utility"] > baseline_result["utility"]
        and winner_result["unsafe_continuations"] == 0
    )
    selected = winner if accepted else baseline
    comparison["baseline_unchanged"] = not accepted
    return {"accepted": accepted, "selected": selected, "candidate": winner,
            "comparison": comparison,
            "baseline_rule": "Mutation cannot replace baseline without strictly higher fixture utility and zero unsafe continuation."}


def _result(reason: StopReason, why: str, evidence: dict, action: str = "STOP") -> dict:
    if reason == StopReason.CONTINUE and action == "STOP":
        action = "CONTINUE"
    return {"reason": reason.value, "action": action, "why": why, "evidence": evidence}


def _policy_evidence(policy: Policy, restarts_used: int) -> dict:
    return {
        "name": policy.name,
        "goal": policy.goal,
        "min_gain_per_cost": policy.min_gain_per_cost,
        "risk_limit": policy.risk_limit,
        "uncertainty_limit": policy.uncertainty_limit,
        "novelty_floor": policy.novelty_floor,
        "window": policy.window,
        "restart_budget": policy.restart_budget,
        "restarts_used": restarts_used,
    }


def _invalid_measurements(history: list[Observation]) -> list[str]:
    invalid = []
    for index, observation in enumerate(history):
        values = {
            "value": observation.value,
            "cost": observation.cost,
            "novelty": observation.novelty,
            "regression_risk": observation.regression_risk,
            "uncertainty": observation.uncertainty,
            "resources_left": observation.resources_left,
        }
        finite = {
            name: isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value)
            for name, value in values.items()
        }
        invalid.extend(f"{index}.{name}" for name, valid in finite.items() if not valid)
        if finite["cost"] and observation.cost < 0:
            invalid.append(f"{index}.cost")
        for name in ("novelty", "regression_risk", "uncertainty"):
            value = getattr(observation, name)
            if finite[name] and not 0 <= value <= 1:
                invalid.append(f"{index}.{name}")
        if not isinstance(observation.tests_passed, bool):
            invalid.append(f"{index}.tests_passed")
    return sorted(set(invalid))


def _invalid_policy(policy: Policy, restarts_used: int) -> list[str]:
    invalid = []
    numeric = {
        "goal": policy.goal,
        "min_gain_per_cost": policy.min_gain_per_cost,
        "risk_limit": policy.risk_limit,
        "uncertainty_limit": policy.uncertainty_limit,
        "novelty_floor": policy.novelty_floor,
    }
    finite = {
        name: isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value)
        for name, value in numeric.items()
    }
    invalid.extend(name for name, valid in finite.items() if not valid)
    if finite["min_gain_per_cost"] and policy.min_gain_per_cost < 0:
        invalid.append("min_gain_per_cost")
    for name in ("risk_limit", "uncertainty_limit", "novelty_floor"):
        if finite[name] and not 0 <= getattr(policy, name) <= 1:
            invalid.append(name)
    if not isinstance(policy.window, int) or isinstance(policy.window, bool) or policy.window <= 0:
        invalid.append("window")
    if not isinstance(policy.restart_budget, int) or isinstance(policy.restart_budget, bool) or policy.restart_budget < 0:
        invalid.append("restart_budget")
    if not isinstance(restarts_used, int) or isinstance(restarts_used, bool) or restarts_used < 0:
        invalid.append("restarts_used")
    return sorted(set(invalid))
