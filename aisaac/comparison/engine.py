"""
Multi-Level Comparison Engine.

Six layers of comparison, from superficial to deep:
1. Structural: expression tree topology
2. Dimensional: same physical dimensions
3. Numerical: same numbers when evaluated
4. Limiting: one reduces to another in a limit
5. Symmetry: same symmetry group structure
6. ML-assisted: embedding similarity + clustering

Each layer produces ComparisonResult objects that feed into
the conjecture generator.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import sympy as sp
from sympy.parsing.sympy_parser import parse_expr, standard_transformations, implicit_multiplication

from ..knowledge.base import KnowledgeBase

log = logging.getLogger(__name__)


@dataclass
class ComparisonResult:
    """Result of comparing two formulas."""
    formula_a_id: int
    formula_b_id: int
    theory_a: str
    theory_b: str
    quantity_type_a: str
    quantity_type_b: str
    # Scores per level (0-1, None if not checked)
    structural_score: Optional[float] = None
    dimensional_score: Optional[float] = None
    numerical_score: Optional[float] = None
    limit_score: Optional[float] = None
    symmetry_score: Optional[float] = None
    embedding_score: Optional[float] = None
    # Combined
    combined_score: float = 0.0
    match_type: str = ""  # exact | structural | partial | analogous | none
    details: dict = field(default_factory=dict)

    def compute_combined(self):
        """Weighted combination of available scores."""
        scores = []
        weights = []
        for s, w in [
            (self.structural_score, 2.0),
            (self.dimensional_score, 1.5),
            (self.numerical_score, 3.0),   # numerical agreement is strongest evidence
            (self.limit_score, 2.0),
            (self.symmetry_score, 1.0),
            (self.embedding_score, 0.5),   # ML is weakest (finds candidates, not proves)
        ]:
            if s is not None:
                scores.append(s * w)
                weights.append(w)
        self.combined_score = sum(scores) / sum(weights) if weights else 0.0


# ── Structural Comparison ────────────────────────────────────────

class StructuralMatcher:
    """
    Compare expression tree topology.
    
    Two formulas match structurally if they have the same tree shape,
    even with different symbols. E.g.:
      A * x^(-n) * y^m  ≈  B * p^(-n) * q^m  (same structure)
    """

    def compare(self, expr_a: str, expr_b: str) -> tuple[float, dict]:
        """
        Compare two sympy expression strings structurally.
        Returns (score, details).
        """
        try:
            ea = _safe_parse(expr_a)
            eb = _safe_parse(expr_b)
        except Exception as e:
            return 0.0, {"error": str(e)}

        if ea is None or eb is None:
            return 0.0, {"error": "parse failure"}

        # Get expression tree structure
        tree_a = self._to_tree(ea)
        tree_b = self._to_tree(eb)

        # Tree edit distance (normalized)
        ted = self._tree_edit_distance(tree_a, tree_b)
        max_size = max(self._tree_size(tree_a), self._tree_size(tree_b), 1)
        score = max(0, 1.0 - ted / max_size)

        # Check for exact match after simplification
        try:
            diff = sp.simplify(ea - eb)
            if diff == 0:
                return 1.0, {"match": "exact_after_simplification"}
        except Exception:
            pass

        # Check structural skeleton
        skel_a = self._skeleton(ea)
        skel_b = self._skeleton(eb)
        skel_match = skel_a == skel_b

        return score, {
            "tree_edit_distance": ted,
            "max_tree_size": max_size,
            "skeleton_match": skel_match,
            "skeleton_a": str(skel_a),
            "skeleton_b": str(skel_b),
        }

    def _to_tree(self, expr, depth: int = 0) -> tuple:
        """Convert sympy expression to nested tuple tree."""
        if depth > 50:
            return (type(expr).__name__, str(expr))
        try:
            args = expr.args
            if args and isinstance(args, (list, tuple)):
                return (type(expr).__name__, tuple(self._to_tree(a, depth + 1) for a in args))
        except (TypeError, AttributeError):
            pass
        return (type(expr).__name__, str(expr))

    def _tree_size(self, tree) -> int:
        if isinstance(tree[1], tuple):
            return 1 + sum(self._tree_size(c) for c in tree[1])
        return 1

    def _tree_edit_distance(self, t1, t2) -> int:
        """Simplified tree edit distance."""
        if not isinstance(t1[1], tuple) and not isinstance(t2[1], tuple):
            return 0 if t1[0] == t2[0] else 1
        if not isinstance(t1[1], tuple) or not isinstance(t2[1], tuple):
            return max(self._tree_size(t1), self._tree_size(t2))

        if t1[0] != t2[0]:
            cost = 1
        else:
            cost = 0

        children1 = list(t1[1]) if isinstance(t1[1], tuple) else []
        children2 = list(t2[1]) if isinstance(t2[1], tuple) else []

        # Simple alignment (not full optimal TED, but fast)
        n, m = len(children1), len(children2)
        for i in range(min(n, m)):
            cost += self._tree_edit_distance(children1[i], children2[i])
        cost += abs(n - m)  # unmatched children
        return cost

    def _skeleton(self, expr) -> str:
        """
        Replace all symbols with placeholders to get structural skeleton.
        E.g., A * x**(-n) → _c * _x**(-_n)
        """
        try:
            syms = list(expr.free_symbols)
            subs = {s: sp.Symbol(f"_v{i}") for i, s in enumerate(sorted(syms, key=str))}
            return str(expr.subs(subs))
        except (AttributeError, TypeError):
            return str(expr)


# ── Dimensional Matching ────────────────────────────────────────

class DimensionalMatcher:
    """
    Check if two formulas have the same physical dimensions.
    Same dimensions → might represent the same physical quantity.
    """

    # Dimension database: common QG quantities and their dimensions
    # In natural units (ℏ=c=1): [M] = [L]⁻¹ = [T]⁻¹
    QUANTITY_DIMENSIONS = {
        "spectral_dimension": "dimensionless",
        "newton_correction": "[L]^{-1}",  # potential V(r) has dim of energy/mass
        "black_hole_entropy": "dimensionless",  # S/k_B
        "bh_entropy_log_correction": "dimensionless",
        "area_gap": "[L]^2",
        "graviton_propagator_modification": "[L]^2",  # in momentum space: [p]^{-2}
        "dispersion_relation_modification": "[L]^{-1}",  # energy correction
    }

    def compare(self, formula_a: dict, formula_b: dict) -> tuple[float, dict]:
        """Compare dimensions of two formulas."""
        qt_a = formula_a.get("quantity_type", "other")
        qt_b = formula_b.get("quantity_type", "other")

        # Same quantity type → dimensions must match
        if qt_a == qt_b and qt_a in self.QUANTITY_DIMENSIONS:
            return 1.0, {"reason": f"same quantity type: {qt_a}"}

        # Different quantity types but could still have same dimensions
        dim_a = self.QUANTITY_DIMENSIONS.get(qt_a, "unknown")
        dim_b = self.QUANTITY_DIMENSIONS.get(qt_b, "unknown")

        if dim_a == "unknown" or dim_b == "unknown":
            return 0.5, {"reason": "unknown dimensions"}
        if dim_a == dim_b:
            return 0.8, {"reason": f"same dimensions: {dim_a}"}
        return 0.0, {"reason": f"different dimensions: {dim_a} vs {dim_b}"}


# ── Numerical Comparison ────────────────────────────────────────

class NumericalMatcher:
    """
    Evaluate two formulas on the same inputs and compare outputs.
    Catches cases where formulas look different symbolically
    but are numerically identical.
    """

    def compare(
        self, expr_a: str, expr_b: str,
        common_vars: list[str] | None = None,
        n_samples: int = 100,
        rtol: float = 0.05,
    ) -> tuple[float, dict]:
        """
        Numerically compare two expressions.
        Returns (score, details) where score is fraction of test
        points where the expressions agree within rtol.
        """
        try:
            ea = _safe_parse(expr_a)
            eb = _safe_parse(expr_b)
        except Exception as e:
            return 0.0, {"error": str(e)}

        if ea is None or eb is None:
            return 0.0, {"error": "parse failure"}

        # Find common free symbols
        syms_a = ea.free_symbols
        syms_b = eb.free_symbols

        if common_vars:
            # Use specified common variables
            var_map = {}
            for v in common_vars:
                sa = sp.Symbol(v)
                if sa in syms_a and sa in syms_b:
                    var_map[v] = sa
        else:
            # Try to match by name
            var_map = {}
            for sa in syms_a:
                for sb in syms_b:
                    if str(sa) == str(sb):
                        var_map[str(sa)] = sa

        if not var_map:
            return 0.0, {"error": "no common variables found"}

        symbols = list(var_map.values())

        # Generate random test points (positive values, log-uniform for physics)
        rng = np.random.default_rng(42)
        test_points = np.exp(rng.uniform(-5, 5, (n_samples, len(symbols))))

        matches = 0
        errors = 0
        for i in range(n_samples):
            subs = {s: float(test_points[i, j]) for j, s in enumerate(symbols)}
            try:
                va = complex(ea.subs(subs))
                vb = complex(eb.subs(subs))
                if np.isnan(va) or np.isnan(vb) or np.isinf(va) or np.isinf(vb):
                    errors += 1
                    continue
                if abs(va) < 1e-30 and abs(vb) < 1e-30:
                    matches += 1
                elif abs(va - vb) / max(abs(va), abs(vb), 1e-30) < rtol:
                    matches += 1
            except Exception:
                errors += 1

        valid = n_samples - errors
        score = matches / max(valid, 1)

        return score, {
            "matches": matches,
            "valid_samples": valid,
            "errors": errors,
            "common_variables": list(var_map.keys()),
        }


# ── Limit Matching ──────────────────────────────────────────────

class LimitMatcher:
    """
    Check if one formula reduces to another in a specific limit.
    E.g., does formula A → formula B when parameter P → 0?
    
    This is checked both symbolically and numerically.
    """

    # Common limits to check
    LIMITS = [
        ("G", 0, "classical limit"),
        ("l_P", 0, "classical limit"),
        ("alpha_prime", 0, "point particle limit"),
        ("theta_NC", 0, "commutative limit"),
        ("gamma_I", 1, "specific Immirzi value"),
        ("hbar", 0, "classical limit"),
    ]

    def check_limits(
        self, expr_a: str, expr_b: str,
        theory_a: str, theory_b: str,
    ) -> list[tuple[float, dict]]:
        """Check all relevant limits between two expressions."""
        results = []
        try:
            ea = _safe_parse(expr_a)
            eb = _safe_parse(expr_b)
        except Exception:
            return results

        if ea is None or eb is None:
            return results

        for param, limit_val, limit_name in self.LIMITS:
            sym = sp.Symbol(param)
            if sym in ea.free_symbols or sym in eb.free_symbols:
                try:
                    # Take limit of expr_a and compare with expr_b
                    limit_a = sp.limit(ea, sym, limit_val)
                    # Check if limit_a structurally matches expr_b
                    diff = sp.simplify(limit_a - eb)
                    if diff == 0:
                        results.append((1.0, {
                            "limit_type": limit_name,
                            "parameter": param,
                            "limit_value": limit_val,
                            "direction": f"{theory_a} → {theory_b} as {param} → {limit_val}",
                        }))
                    else:
                        # Check numerical agreement at limit
                        score, _ = NumericalMatcher().compare(str(limit_a), str(eb))
                        if score > 0.8:
                            results.append((score, {
                                "limit_type": limit_name,
                                "parameter": param,
                                "limit_value": limit_val,
                                "agreement": "numerical",
                            }))
                except Exception:
                    continue
        return results


# ── Full Comparison Pipeline ─────────────────────────────────────

class ComparisonEngine:
    """
    Run all comparison levels between all formula pairs.
    
    Optimization: don't compare everything with everything.
    Pre-filter by quantity type and dimensional match first.
    """

    def __init__(self, kb: KnowledgeBase):
        self.kb = kb
        self.structural = StructuralMatcher()
        self.dimensional = DimensionalMatcher()
        self.numerical = NumericalMatcher()
        self.limit = LimitMatcher()

    def compare_all(
        self, 
        min_score: float = 0.3,
        same_theory_ok: bool = False,
    ) -> list[ComparisonResult]:
        """
        Compare all formula pairs across theories.
        
        Strategy:
        1. Group formulas by quantity type
        2. Within each group, compare cross-theory pairs
        3. Also compare formulas with same dimensions but different quantity labels
        """
        all_formulas = self.kb.get_all_formulas(
            formula_types=["prediction", "correction", "key_equation", "mapping"]
        )
        log.info(f"Comparing {len(all_formulas)} formulas...")

        # Group by quantity type
        by_quantity: dict[str, list[dict]] = {}
        for f in all_formulas:
            qt = f["quantity_type"]
            by_quantity.setdefault(qt, []).append(f)

        results = []

        # Compare within same quantity type (highest priority)
        for qt, formulas in by_quantity.items():
            if qt == "other":
                continue  # skip unclassified for targeted comparison
            pairs = self._cross_theory_pairs(formulas, same_theory_ok)
            for fa, fb in pairs:
                r = self._compare_pair(fa, fb)
                if r.combined_score >= min_score:
                    results.append(r)
                    log.info(
                        f"  Match ({r.combined_score:.2f}): "
                        f"{r.theory_a}/{qt} ↔ {r.theory_b}/{qt}"
                    )

        # Also compare "other" formulas using structural/embedding similarity
        if "other" in by_quantity:
            others = by_quantity["other"]
            pairs = self._cross_theory_pairs(others, same_theory_ok)
            for fa, fb in pairs:
                # Only structural comparison for unclassified
                score, details = self.structural.compare(
                    fa.get("normalized_sympy", fa.get("sympy_expr", "")),
                    fb.get("normalized_sympy", fb.get("sympy_expr", "")),
                )
                if score >= 0.7:
                    r = ComparisonResult(
                        formula_a_id=fa["id"],
                        formula_b_id=fb["id"],
                        theory_a=fa["theory_slug"],
                        theory_b=fb["theory_slug"],
                        quantity_type_a=fa["quantity_type"],
                        quantity_type_b=fb["quantity_type"],
                        structural_score=score,
                        combined_score=score,
                        match_type="structural",
                        details=details,
                    )
                    results.append(r)

        results.sort(key=lambda r: r.combined_score, reverse=True)
        log.info(f"Found {len(results)} matches above threshold {min_score}")
        return results

    def compare_for_quantity(
        self, quantity_type: str, min_score: float = 0.3,
    ) -> list[ComparisonResult]:
        """Compare all predictions for a specific quantity across theories."""
        formulas = self.kb.get_predictions_for_quantity(quantity_type)
        log.info(f"Comparing {len(formulas)} predictions for {quantity_type}")

        results = []
        pairs = self._cross_theory_pairs(formulas, same_theory_ok=False)
        for fa, fb in pairs:
            r = self._compare_pair(fa, fb)
            if r.combined_score >= min_score:
                results.append(r)

        results.sort(key=lambda r: r.combined_score, reverse=True)
        return results

    def _compare_pair(self, fa: dict, fb: dict) -> ComparisonResult:
        """Full multi-level comparison of two formulas."""
        expr_a = fa.get("normalized_sympy") or fa.get("sympy_expr", "")
        expr_b = fb.get("normalized_sympy") or fb.get("sympy_expr", "")

        result = ComparisonResult(
            formula_a_id=fa["id"],
            formula_b_id=fb["id"],
            theory_a=fa["theory_slug"],
            theory_b=fb["theory_slug"],
            quantity_type_a=fa["quantity_type"],
            quantity_type_b=fb["quantity_type"],
        )

        # Level 1: Structural
        if expr_a and expr_b:
            s, d = self.structural.compare(expr_a, expr_b)
            result.structural_score = s
            result.details["structural"] = d

        # Level 2: Dimensional
        s, d = self.dimensional.compare(fa, fb)
        result.dimensional_score = s
        result.details["dimensional"] = d

        # Level 3: Numerical
        if expr_a and expr_b:
            s, d = self.numerical.compare(expr_a, expr_b)
            result.numerical_score = s
            result.details["numerical"] = d

        # Level 4: Limit
        if expr_a and expr_b:
            limit_results = self.limit.check_limits(
                expr_a, expr_b, fa["theory_slug"], fb["theory_slug"]
            )
            if limit_results:
                best_limit = max(limit_results, key=lambda x: x[0])
                result.limit_score = best_limit[0]
                result.details["limit"] = best_limit[1]

        result.compute_combined()

        # Classify match type
        if result.combined_score > 0.9:
            result.match_type = "exact"
        elif result.combined_score > 0.7:
            result.match_type = "structural"
        elif result.combined_score > 0.5:
            result.match_type = "partial"
        elif result.combined_score > 0.3:
            result.match_type = "analogous"
        else:
            result.match_type = "none"

        return result

    def _cross_theory_pairs(
        self, formulas: list[dict], same_theory_ok: bool
    ) -> list[tuple[dict, dict]]:
        """Generate pairs of formulas from different theories."""
        pairs = []
        for i, fa in enumerate(formulas):
            for fb in formulas[i + 1:]:
                if same_theory_ok or fa["theory_slug"] != fb["theory_slug"]:
                    pairs.append((fa, fb))
        return pairs


# ── Utility ──────────────────────────────────────────────────────

def _safe_parse(expr_str: str):
    """Safely parse a sympy expression string."""
    if not expr_str or expr_str.strip() == "":
        return None
    try:
        transformations = standard_transformations + (implicit_multiplication,)
        result = parse_expr(expr_str, transformations=transformations)
        if isinstance(result, sp.Basic):
            return result
        return None
    except Exception:
        try:
            result = sp.sympify(expr_str)
            if isinstance(result, sp.Basic):
                return result
            return None
        except Exception:
            return None
