"""Versioned semantic contracts for graph relations and core operations."""

CONTRACT_VERSION = "1.0"

EDGE_CONTRACTS = {
    "depends_on": {"direction": "source -> prerequisite", "meaning": "source requires target to hold or be resolved"},
    "supports": {"direction": "supporter -> supported", "meaning": "source increases support for target"},
    "contradicts": {"direction": "challenger -> challenged", "meaning": "source conflicts with target; impact is symmetric"},
    "relates_to": {"direction": "source -> related", "meaning": "non-inferential association; ignored by core propagation"},
}

OPERATION_CONTRACTS = {
    "WHY": "Return prerequisites reachable through outgoing depends_on, supporters reachable through incoming supports, and direct challenges.",
    "BREAK_IT": "Rank non-fact premises by disclosed confidence, dependency, and evidence risk components.",
    "PROVE_IT": "Return a node-type-aware falsifiable test protocol; never claim that execution occurred.",
    "WHAT_IF": "Propagate structural impact to dependents, supported nodes, and both sides of contradictions without claiming causality.",
}

