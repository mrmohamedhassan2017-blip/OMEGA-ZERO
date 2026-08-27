from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ScoringProfile:
    name: str = "balanced-v1"
    confidence_weight: float = 0.55
    dependency_weight: float = 0.08
    evidence_weight: float = 0.25
    dependency_cap: int = 5

    def __post_init__(self) -> None:
        weights = (self.confidence_weight, self.dependency_weight, self.evidence_weight)
        if any(weight < 0 for weight in weights) or not any(weight > 0 for weight in weights):
            raise ValueError("scoring weights must be non-negative and at least one must be positive")
        if self.dependency_cap < 1:
            raise ValueError("dependency_cap must be at least 1")

    def to_dict(self) -> dict:
        return asdict(self)


DEFAULT_SCORING_PROFILE = ScoringProfile()

