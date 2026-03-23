"""
Convergence Analyzer (Agent 3).

Find results that hold REGARDLESS of starting premises.
These are the most robust predictions -- they constrain the correct theory.

Key insight: convergence from INDEPENDENT premises is real evidence.
Convergence from SHARED premises might be circular.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field

from ..knowledge.base import KnowledgeBase

log = logging.getLogger(__name__)


@dataclass
class ConvergenceResult:
    quantity_type: str
    value_description: str
    theories_agree: list[str]
    theories_disagree: list[str]
    shared_assumptions: list[str]  # assumptions common to ALL agreeing theories
    independent_assumptions: list[str]  # assumptions that DIFFER among agreeing theories
    is_premise_independent: bool  # True if agreeing theories have different premises
    strength: str  # "strong" | "moderate" | "weak"
    implication: str  # what this convergence tells us


class ConvergenceAnalyzer:
    """Find premise-independent convergent results."""

    def __init__(self, kb: KnowledgeBase):
        self.kb = kb

    def analyze_all(self) -> list[ConvergenceResult]:
        """Find all convergent results across theories."""
        formulas = self.kb.get_all_formulas()
        assumptions = self.kb.get_assumptions()

        # Group formulas by quantity type
        by_quantity: dict[str, list[dict]] = defaultdict(list)
        for f in formulas:
            qt = f.get("quantity_type", "other")
            if qt != "other":
                by_quantity[qt].append(f)

        # Group assumptions by theory
        assumptions_by_theory: dict[str, list[str]] = defaultdict(list)
        for a in assumptions:
            assumptions_by_theory[a["theory_slug"]].append(a["assumption_text"])

        results = []
        for qt, formulas_list in by_quantity.items():
            theories = list(set(f["theory_slug"] for f in formulas_list))
            if len(theories) < 2:
                continue

            result = self._analyze_quantity(qt, theories, formulas_list, assumptions_by_theory)
            if result:
                results.append(result)

        # Sort by number of agreeing theories (most agreement first)
        results.sort(key=lambda r: len(r.theories_agree), reverse=True)
        log.info(f"Found {len(results)} convergent results")
        return results

    def _analyze_quantity(
        self,
        quantity_type: str,
        theories: list[str],
        formulas: list[dict],
        assumptions_by_theory: dict[str, list[str]],
    ) -> ConvergenceResult | None:
        """Analyze convergence for a specific quantity type."""
        if len(theories) < 2:
            return None

        # Find shared vs independent assumptions among these theories
        assumption_sets: dict[str, set[str]] = {}
        for t in theories:
            assumption_sets[t] = set(assumptions_by_theory.get(t, []))

        # Shared = intersection of all assumption sets
        non_empty = [s for s in assumption_sets.values() if s]
        if non_empty:
            shared = set.intersection(*non_empty)
        else:
            shared = set()

        # Independent = assumptions NOT shared by all
        all_assumptions = set.union(*assumption_sets.values()) if assumption_sets else set()
        independent = all_assumptions - shared

        is_independent = len(independent) > len(shared)

        strength = (
            "strong" if len(theories) >= 4 and is_independent else
            "moderate" if len(theories) >= 3 else
            "weak"
        )

        implication = (
            f"{quantity_type} converges across {len(theories)} theories with "
            f"{'independent' if is_independent else 'shared'} premises. "
            f"{'This is strong evidence the result is physical.' if is_independent else 'May be an artifact of shared assumptions.'}"
        )

        return ConvergenceResult(
            quantity_type=quantity_type,
            value_description=f"Predictions from {len(theories)} theories",
            theories_agree=theories,
            theories_disagree=[],
            shared_assumptions=list(shared)[:10],
            independent_assumptions=list(independent)[:10],
            is_premise_independent=is_independent,
            strength=strength,
            implication=implication,
        )

    def find_premise_independent_results(self) -> list[ConvergenceResult]:
        """The holy grail: results that hold across ALL premise sets."""
        all_results = self.analyze_all()
        return [r for r in all_results if r.is_premise_independent]
