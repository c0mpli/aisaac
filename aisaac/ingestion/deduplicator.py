"""
Formula Deduplicator.

The same formula appears in many papers (e.g., S = A/4 appears in
hundreds of papers across all approaches). We need to:
1. Detect when two extracted formulas are the same
2. Merge them (keep the best metadata from each)
3. Track provenance (which papers contain this formula)

Dedup is done at multiple levels:
- Exact match (normalized sympy strings)
- Structural match (same expression tree up to variable names)
- Numerical match (evaluate and compare)
"""
from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional

import numpy as np
import sympy as sp

from ..knowledge.base import KnowledgeBase

log = logging.getLogger(__name__)


@dataclass
class FormulaCluster:
    """A group of formulas that are all the same formula."""
    canonical_id: int                # the "best" representative
    member_ids: list[int]
    theory_slugs: list[str]         # which theories have this formula
    paper_ids: list[int]            # all papers containing this formula
    match_type: str                  # exact | structural | numerical
    canonical_description: str


class FormulaDeduplicator:
    """
    Deduplicate formulas across the knowledge base.
    """

    def __init__(self, kb: KnowledgeBase):
        self.kb = kb

    def deduplicate(
        self,
        structural_threshold: float = 0.95,
        numerical_threshold: float = 0.99,
    ) -> list[FormulaCluster]:
        """
        Find and group duplicate formulas.
        
        Returns list of FormulaCluster objects. The canonical_id
        is the formula with the highest confidence score in each cluster.
        """
        all_formulas = self.kb.get_all_formulas()
        if len(all_formulas) < 2:
            return []

        # Level 1: Exact string match on normalized sympy
        clusters = self._exact_match_clusters(all_formulas)
        
        # Level 2: Structural match on remaining unclustered
        clustered_ids = set()
        for c in clusters:
            clustered_ids.update(c.member_ids)
        
        remaining = [f for f in all_formulas if f["id"] not in clustered_ids]
        if remaining:
            struct_clusters = self._structural_match_clusters(remaining, structural_threshold)
            clusters.extend(struct_clusters)
            for c in struct_clusters:
                clustered_ids.update(c.member_ids)

        # Level 3: Numerical match on remaining
        remaining = [f for f in all_formulas if f["id"] not in clustered_ids]
        if remaining and len(remaining) < 500:  # numerical is expensive
            num_clusters = self._numerical_match_clusters(remaining, numerical_threshold)
            clusters.extend(num_clusters)

        log.info(
            f"Deduplication: {len(all_formulas)} formulas → "
            f"{len(clusters)} clusters + "
            f"{len(all_formulas) - sum(len(c.member_ids) for c in clusters)} unique"
        )
        return clusters

    def _exact_match_clusters(self, formulas: list[dict]) -> list[FormulaCluster]:
        """Group by exact normalized sympy expression."""
        groups: dict[str, list[dict]] = defaultdict(list)
        
        for f in formulas:
            key = (f.get("normalized_sympy") or f.get("sympy_expr", "")).strip()
            if key:
                groups[key].append(f)

        clusters = []
        for key, members in groups.items():
            if len(members) >= 2:
                # Pick canonical: highest confidence
                members.sort(key=lambda f: f.get("confidence", 0), reverse=True)
                clusters.append(FormulaCluster(
                    canonical_id=members[0]["id"],
                    member_ids=[m["id"] for m in members],
                    theory_slugs=list(set(m["theory_slug"] for m in members)),
                    paper_ids=list(set(m["paper_id"] for m in members)),
                    match_type="exact",
                    canonical_description=members[0].get("description", ""),
                ))

        return clusters

    def _structural_match_clusters(
        self, formulas: list[dict], threshold: float,
    ) -> list[FormulaCluster]:
        """Group by structural similarity of expression trees."""
        from ..comparison.engine import StructuralMatcher
        matcher = StructuralMatcher()

        # Simple greedy clustering
        assigned = set()
        clusters = []

        for i, fa in enumerate(formulas):
            if fa["id"] in assigned:
                continue
            
            expr_a = fa.get("normalized_sympy") or fa.get("sympy_expr", "")
            if not expr_a:
                continue

            cluster_members = [fa]
            assigned.add(fa["id"])

            for fb in formulas[i+1:]:
                if fb["id"] in assigned:
                    continue
                expr_b = fb.get("normalized_sympy") or fb.get("sympy_expr", "")
                if not expr_b:
                    continue

                score, _ = matcher.compare(expr_a, expr_b)
                if score >= threshold:
                    cluster_members.append(fb)
                    assigned.add(fb["id"])

            if len(cluster_members) >= 2:
                cluster_members.sort(key=lambda f: f.get("confidence", 0), reverse=True)
                clusters.append(FormulaCluster(
                    canonical_id=cluster_members[0]["id"],
                    member_ids=[m["id"] for m in cluster_members],
                    theory_slugs=list(set(m["theory_slug"] for m in cluster_members)),
                    paper_ids=list(set(m["paper_id"] for m in cluster_members)),
                    match_type="structural",
                    canonical_description=cluster_members[0].get("description", ""),
                ))

        return clusters

    def _numerical_match_clusters(
        self, formulas: list[dict], threshold: float,
    ) -> list[FormulaCluster]:
        """Group by numerical evaluation match."""
        from ..comparison.engine import NumericalMatcher
        matcher = NumericalMatcher()

        assigned = set()
        clusters = []

        for i, fa in enumerate(formulas):
            if fa["id"] in assigned:
                continue

            expr_a = fa.get("normalized_sympy") or fa.get("sympy_expr", "")
            if not expr_a:
                continue

            cluster_members = [fa]
            assigned.add(fa["id"])

            for fb in formulas[i+1:]:
                if fb["id"] in assigned:
                    continue
                expr_b = fb.get("normalized_sympy") or fb.get("sympy_expr", "")
                if not expr_b:
                    continue

                score, _ = matcher.compare(expr_a, expr_b, n_samples=50)
                if score >= threshold:
                    cluster_members.append(fb)
                    assigned.add(fb["id"])

            if len(cluster_members) >= 2:
                cluster_members.sort(key=lambda f: f.get("confidence", 0), reverse=True)
                clusters.append(FormulaCluster(
                    canonical_id=cluster_members[0]["id"],
                    member_ids=[m["id"] for m in cluster_members],
                    theory_slugs=list(set(m["theory_slug"] for m in cluster_members)),
                    paper_ids=list(set(m["paper_id"] for m in cluster_members)),
                    match_type="numerical",
                    canonical_description=cluster_members[0].get("description", ""),
                ))

        return clusters

    def get_cross_theory_duplicates(self) -> list[FormulaCluster]:
        """
        Find formulas that appear in MULTIPLE theories.
        These are the most interesting: different derivations
        arriving at the same answer.
        """
        clusters = self.deduplicate()
        return [c for c in clusters if len(c.theory_slugs) >= 2]
