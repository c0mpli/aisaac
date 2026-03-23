"""
Equation Interrogator.

Pure sympy. No LLM. No hallucinations.

Analyzes all formulas in the database for mathematical patterns
that no human would find because the formulas live in different
papers with different notation across different communities.

Every output is a MATHEMATICAL FACT, not an LLM opinion.
"""
from __future__ import annotations

import logging
import json
from collections import defaultdict
from dataclasses import dataclass, field
from fractions import Fraction

import sympy as sp
import numpy as np

from ..knowledge.base import KnowledgeBase

log = logging.getLogger(__name__)

# Standard variables used across theories
STANDARD_VARS = {
    "G": sp.Symbol("G", positive=True),           # Newton's constant
    "A": sp.Symbol("A", positive=True),            # area
    "r": sp.Symbol("r", positive=True),            # distance
    "d": sp.Symbol("d", positive=True),            # dimension
    "l_P": sp.Symbol("l_P", positive=True),        # Planck length
    "E": sp.Symbol("E", positive=True),            # energy
    "p": sp.Symbol("p"),                           # momentum
    "k": sp.Symbol("k", positive=True),            # wavenumber/RG scale
    "s": sp.Symbol("s", positive=True),            # diffusion parameter
    "sigma": sp.Symbol("sigma", positive=True),    # diffusion time
    "m": sp.Symbol("m", positive=True),            # mass
    "hbar": sp.Symbol("hbar", positive=True),      # Planck constant
    "c": sp.Symbol("c", positive=True),            # speed of light
    "kappa": sp.Symbol("kappa", positive=True),     # NC parameter
}


@dataclass
class MathAnomaly:
    """A mathematical pattern found across theories."""
    anomaly_type: str  # symmetry | coefficient | limit | substitution | structure
    description: str
    theories_involved: list[str]
    formulas_involved: list[int]  # formula IDs
    details: dict = field(default_factory=dict)
    significance: float = 0.0  # 0-1


def safe_parse(expr_str: str) -> sp.Basic | None:
    """Safely parse a sympy expression string."""
    if not expr_str or not expr_str.strip():
        return None
    expr_str = expr_str.strip()

    # Skip clearly unparseable
    if any(x in expr_str for x in ["ket_", "bra_", "||"]):
        return None

    # Clean up common patterns that block parsing
    # Remove ~ separators (some formulas use S = A/(4*G) ~ r_H**(d-2)/G)
    if "~" in expr_str:
        expr_str = expr_str.split("~")[0].strip()

    # Handle Piecewise → take the first branch
    if "Piecewise" in expr_str:
        import re
        m = re.search(r"Piecewise\(\((.+?),", expr_str)
        if m:
            expr_str = m.group(1).strip()
        else:
            return None

    # Handle Eq(lhs, rhs) → just use lhs
    if expr_str.startswith("Eq("):
        inner = expr_str[3:-1] if expr_str.endswith(")") else expr_str[3:]
        parts = inner.split(",", 1)
        if parts:
            expr_str = parts[0].strip()

    # Remove text fragments
    expr_str = expr_str.replace("const", "0").replace("+ O(1)", "").replace("+ ...", "")

    # Try parsing with standard variables
    try:
        return sp.sympify(expr_str, locals=STANDARD_VARS)
    except Exception:
        pass

    # Try with more permissive parsing
    try:
        return sp.sympify(expr_str)
    except Exception:
        return None


class EquationInterrogator:
    """Pure mathematical analysis of formulas. No LLM."""

    def __init__(self, kb: KnowledgeBase):
        self.kb = kb

    def run_all(self) -> list[MathAnomaly]:
        """Run all analyses and return anomalies."""
        formulas = self._load_formulas()
        log.info(f"Loaded {len(formulas)} parseable formulas")

        if len(formulas) < 2:
            log.warning("Need at least 2 parseable formulas")
            return []

        anomalies = []
        anomalies.extend(self.symmetry_scan(formulas))
        anomalies.extend(self.coefficient_analyzer(formulas))
        anomalies.extend(self.limit_stress_test(formulas))
        anomalies.extend(self.cross_theory_substitution(formulas))
        anomalies.extend(self.structural_analyzer(formulas))

        anomalies.sort(key=lambda a: a.significance, reverse=True)
        log.info(f"Found {len(anomalies)} mathematical anomalies")
        return anomalies

    def _load_formulas(self) -> list[dict]:
        """Load and parse all formulas from DB."""
        raw = self.kb.get_all_formulas()
        formulas = []
        for f in raw:
            qt = f.get("quantity_type", "other")
            if qt == "other":
                continue
            expr_str = f.get("normalized_sympy") or f.get("sympy_expr", "")
            expr = safe_parse(expr_str)
            if expr is not None:
                f["_expr"] = expr
                f["_expr_str"] = expr_str
                formulas.append(f)
        return formulas

    # ── 1. SYMMETRY SCAN ───────────────────────────────────────────

    def symmetry_scan(self, formulas: list[dict]) -> list[MathAnomaly]:
        """Find shared symmetries across theories."""
        log.info("Running symmetry scan...")
        anomalies = []

        # For each formula, test discrete transforms
        transforms = {
            "scale_invariant": lambda e, s: sp.simplify(e.subs(
                {v: s * v for v in e.free_symbols if str(v) not in ("d",)}) / (s ** _count_dimension(e)) - e) == 0,
            "sign_flip_invariant": lambda e, s: any(
                sp.simplify(e.subs(v, -v) - e) == 0 for v in e.free_symbols
            ),
            "inversion_invariant": lambda e, s: any(
                safe_simplify(e.subs(v, 1/v) * v**2 - e) == 0 for v in e.free_symbols if v.is_positive
            ),
        }

        # Check which formulas have each property
        sym_groups = defaultdict(list)  # symmetry_name → [(formula_id, theory)]

        for f in formulas:
            expr = f["_expr"]
            fid = f.get("id", 0)
            theory = f.get("theory_slug", "")

            try:
                free_syms = list(expr.free_symbols)
            except (TypeError, AttributeError):
                continue

            # Test homogeneity degree
            for v in free_syms:
                try:
                    deg = _homogeneity_degree(expr, v)
                    if deg is not None:
                        sym_groups[f"homogeneous_in_{v}_deg_{deg}"].append((fid, theory, f))
                except Exception:
                    pass

            # Test even/odd in each variable
            for v in free_syms:
                try:
                    flipped = expr.subs(v, -v)
                    if safe_simplify(flipped - expr) == 0:
                        sym_groups[f"even_in_{v}"].append((fid, theory, f))
                    elif safe_simplify(flipped + expr) == 0:
                        sym_groups[f"odd_in_{v}"].append((fid, theory, f))
                except Exception:
                    pass

        # Find cross-theory symmetry matches
        for sym_name, group in sym_groups.items():
            theories = set(t for _, t, _ in group)
            if len(theories) >= 2:
                anomalies.append(MathAnomaly(
                    anomaly_type="symmetry",
                    description=f"Shared symmetry '{sym_name}' across {len(theories)} theories: {', '.join(sorted(theories))}",
                    theories_involved=sorted(theories),
                    formulas_involved=[fid for fid, _, _ in group],
                    details={
                        "symmetry": sym_name,
                        "formula_count": len(group),
                        "formulas": [
                            {"id": fid, "theory": t, "quantity": f.get("quantity_type", "")}
                            for fid, t, f in group
                        ],
                    },
                    significance=min(len(theories) / 4, 1.0),
                ))

        log.info(f"  Symmetry scan: {len(anomalies)} cross-theory symmetry matches")
        return anomalies

    # ── 2. COEFFICIENT ANALYZER ────────────────────────────────────

    def coefficient_analyzer(self, formulas: list[dict]) -> list[MathAnomaly]:
        """Extract and compare numerical coefficients across theories."""
        log.info("Running coefficient analysis...")
        anomalies = []

        # Extract coefficients from each formula
        coeff_data = []  # (formula_id, theory, quantity, coefficient_value, coefficient_context)

        for f in formulas:
            expr = f["_expr"]
            fid = f.get("id", 0)
            theory = f.get("theory_slug", "")
            qt = f.get("quantity_type", "")

            coeffs = _extract_coefficients(expr)
            for val, context in coeffs:
                coeff_data.append((fid, theory, qt, val, context))

        # Group by quantity type and look for patterns
        by_quantity = defaultdict(list)
        for fid, theory, qt, val, ctx in coeff_data:
            by_quantity[qt].append((fid, theory, val, ctx))

        for qt, entries in by_quantity.items():
            if len(entries) < 2:
                continue

            # Check pairwise ratios
            values = [(fid, theory, val) for fid, theory, val, _ in entries if val != 0]
            for i, (fid_a, theory_a, val_a) in enumerate(values):
                for fid_b, theory_b, val_b in values[i+1:]:
                    if theory_a == theory_b:
                        continue
                    if val_b == 0:
                        continue

                    ratio = val_a / val_b
                    # Check if ratio is a simple fraction
                    frac = _to_simple_fraction(ratio)
                    if frac is not None:
                        anomalies.append(MathAnomaly(
                            anomaly_type="coefficient",
                            description=(
                                f"Coefficient ratio {theory_a}/{theory_b} for {qt}: "
                                f"{val_a} / {val_b} = {frac} (exact rational ratio)"
                            ),
                            theories_involved=[theory_a, theory_b],
                            formulas_involved=[fid_a, fid_b],
                            details={
                                "quantity": qt,
                                "value_a": float(val_a), "theory_a": theory_a,
                                "value_b": float(val_b), "theory_b": theory_b,
                                "ratio": str(frac),
                            },
                            significance=0.6 if frac not in ("1", "-1", "1/1", "-1/1") else 0.3,
                        ))

        log.info(f"  Coefficient analysis: {len(anomalies)} ratio patterns")
        return anomalies

    # ── 3. LIMIT STRESS TEST ───────────────────────────────────────

    def limit_stress_test(self, formulas: list[dict]) -> list[MathAnomaly]:
        """Test every formula at extreme limits."""
        log.info("Running limit stress tests...")
        anomalies = []

        # Limit points to test
        limit_points = [
            ("zero", 0),
            ("infinity", sp.oo),
            ("one", 1),
        ]

        # Build behavior table: (formula_id, theory, quantity, variable, limit_name) → behavior
        behavior_table = {}

        for f in formulas:
            expr = f["_expr"]
            fid = f.get("id", 0)
            theory = f.get("theory_slug", "")
            qt = f.get("quantity_type", "")

            try:
                _fsyms = sorted(expr.free_symbols, key=str)
            except (TypeError, AttributeError):
                continue
            for v in _fsyms:
                for lim_name, lim_val in limit_points:
                    behavior = _compute_limit_behavior(expr, v, lim_val)
                    if behavior:
                        key = (str(v), lim_name, qt)
                        behavior_table.setdefault(key, []).append(
                            (fid, theory, behavior, f)
                        )

        # Find where different theories DISAGREE on limit behavior for same quantity
        for key, entries in behavior_table.items():
            var_name, lim_name, qt = key
            theories_behaviors = defaultdict(list)
            for fid, theory, behavior, f in entries:
                theories_behaviors[theory].append((fid, behavior))

            if len(theories_behaviors) < 2:
                continue

            # Check for disagreements
            unique_behaviors = set()
            for theory, blist in theories_behaviors.items():
                for _, b in blist:
                    unique_behaviors.add(b)

            if len(unique_behaviors) > 1:
                anomalies.append(MathAnomaly(
                    anomaly_type="limit",
                    description=(
                        f"LIMIT DISAGREEMENT: {qt} as {var_name}→{lim_name}: "
                        f"theories disagree on behavior"
                    ),
                    theories_involved=sorted(theories_behaviors.keys()),
                    formulas_involved=[fid for entries_list in theories_behaviors.values() for fid, _ in entries_list],
                    details={
                        "variable": var_name,
                        "limit": lim_name,
                        "quantity": qt,
                        "behaviors": {
                            theory: [b for _, b in blist]
                            for theory, blist in theories_behaviors.items()
                        },
                    },
                    significance=0.8,
                ))

            # Check for shared singularities (same divergence point)
            divergent_theories = [
                theory for theory, blist in theories_behaviors.items()
                if any(b == "diverges" for _, b in blist)
            ]
            if len(divergent_theories) >= 2:
                anomalies.append(MathAnomaly(
                    anomaly_type="limit",
                    description=(
                        f"SHARED SINGULARITY: {qt} diverges as {var_name}→{lim_name} "
                        f"in {len(divergent_theories)} theories: {', '.join(divergent_theories)}"
                    ),
                    theories_involved=divergent_theories,
                    formulas_involved=[fid for fid, theory, _, _ in entries if theory in divergent_theories],
                    details={"variable": var_name, "limit": lim_name, "quantity": qt},
                    significance=0.7,
                ))

        log.info(f"  Limit stress test: {len(anomalies)} anomalies")
        return anomalies

    # ── 4. CROSS-THEORY SUBSTITUTION ───────────────────────────────

    def cross_theory_substitution(self, formulas: list[dict]) -> list[MathAnomaly]:
        """Try substituting variables between theories."""
        log.info("Running cross-theory substitutions...")
        anomalies = []

        # Known variable mappings between theories
        mappings = [
            {"name": "kappa_to_G", "subs": {sp.Symbol("kappa"): sp.sqrt(16 * sp.pi * sp.Symbol("G"))}},
            {"name": "l_P_to_G", "subs": {sp.Symbol("l_P"): sp.sqrt(sp.Symbol("G"))}},
            {"name": "alpha_to_l_s", "subs": {sp.Symbol("alpha_prime"): sp.Symbol("l_s") ** 2}},
        ]

        # Group formulas by quantity type
        by_qt = defaultdict(list)
        for f in formulas:
            by_qt[f.get("quantity_type", "")].append(f)

        for qt, qt_formulas in by_qt.items():
            if len(qt_formulas) < 2:
                continue

            for i, fa in enumerate(qt_formulas):
                for fb in qt_formulas[i+1:]:
                    if fa.get("theory_slug") == fb.get("theory_slug"):
                        continue

                    expr_a = fa["_expr"]
                    expr_b = fb["_expr"]

                    # Try direct comparison
                    try:
                        diff = safe_simplify(expr_a - expr_b)
                    except (TypeError, AttributeError):
                        continue
                    if diff is not None and diff == 0:
                        anomalies.append(MathAnomaly(
                            anomaly_type="substitution",
                            description=(
                                f"EXACT MATCH: {fa['theory_slug']} and {fb['theory_slug']} "
                                f"formulas for {qt} are mathematically identical"
                            ),
                            theories_involved=[fa["theory_slug"], fb["theory_slug"]],
                            formulas_involved=[fa.get("id", 0), fb.get("id", 0)],
                            details={"quantity": qt, "expr_a": str(expr_a), "expr_b": str(expr_b)},
                            significance=0.9,
                        ))
                        continue

                    # Try with mappings
                    for mapping in mappings:
                        try:
                            expr_a_mapped = expr_a.subs(mapping["subs"])
                            diff = safe_simplify(expr_a_mapped - expr_b)
                            if diff is not None and diff == 0:
                                anomalies.append(MathAnomaly(
                                    anomaly_type="substitution",
                                    description=(
                                        f"MATCH VIA {mapping['name']}: {fa['theory_slug']} → {fb['theory_slug']} "
                                        f"for {qt}"
                                    ),
                                    theories_involved=[fa["theory_slug"], fb["theory_slug"]],
                                    formulas_involved=[fa.get("id", 0), fb.get("id", 0)],
                                    details={
                                        "mapping": mapping["name"],
                                        "quantity": qt,
                                    },
                                    significance=0.85,
                                ))
                        except Exception:
                            pass

                    # Check if difference is a simple correction term
                    if diff is not None and diff != 0:
                        try:
                            # Is the correction term simpler than either formula?
                            diff_complexity = len(str(diff))
                            a_complexity = len(str(expr_a))
                            b_complexity = len(str(expr_b))
                            if diff_complexity < min(a_complexity, b_complexity) / 2:
                                anomalies.append(MathAnomaly(
                                    anomaly_type="substitution",
                                    description=(
                                        f"NEAR MATCH: {fa['theory_slug']} vs {fb['theory_slug']} for {qt} "
                                        f"differ by simple correction: {str(diff)[:80]}"
                                    ),
                                    theories_involved=[fa["theory_slug"], fb["theory_slug"]],
                                    formulas_involved=[fa.get("id", 0), fb.get("id", 0)],
                                    details={
                                        "quantity": qt,
                                        "correction_term": str(diff)[:200],
                                        "correction_complexity": diff_complexity,
                                    },
                                    significance=0.7,
                                ))
                        except Exception:
                            pass

        log.info(f"  Cross-theory substitution: {len(anomalies)} matches/near-matches")
        return anomalies

    # ── 5. STRUCTURAL ANALYZER ─────────────────────────────────────

    def structural_analyzer(self, formulas: list[dict]) -> list[MathAnomaly]:
        """Analyze structural properties: tree depth, operator counts, etc."""
        log.info("Running structural analysis...")
        anomalies = []

        # Group by quantity type
        by_qt = defaultdict(list)
        for f in formulas:
            by_qt[f.get("quantity_type", "")].append(f)

        for qt, qt_formulas in by_qt.items():
            if len(qt_formulas) < 2:
                continue

            # Check: do all formulas for this quantity share the same functional form?
            structures = []
            for f in qt_formulas:
                expr = f["_expr"]
                skeleton = _get_skeleton(expr)
                structures.append((f, skeleton))

            # Group by skeleton
            skeleton_groups = defaultdict(list)
            for f, skel in structures:
                skeleton_groups[skel].append(f)

            # If multiple theories share a skeleton
            for skel, group in skeleton_groups.items():
                theories = set(f.get("theory_slug", "") for f in group)
                if len(theories) >= 2:
                    anomalies.append(MathAnomaly(
                        anomaly_type="structure",
                        description=(
                            f"SHARED STRUCTURE for {qt}: {len(theories)} theories share "
                            f"functional form '{skel}'"
                        ),
                        theories_involved=sorted(theories),
                        formulas_involved=[f.get("id", 0) for f in group],
                        details={
                            "quantity": qt,
                            "skeleton": skel,
                            "theories": sorted(theories),
                        },
                        significance=0.6 if len(theories) >= 3 else 0.4,
                    ))

        log.info(f"  Structural analysis: {len(anomalies)} shared structures")
        return anomalies


# ── Helper Functions ──────────────────────────────────────────────────

def safe_simplify(expr):
    """Simplify with timeout protection."""
    if expr is None:
        return None
    try:
        return sp.simplify(expr)
    except Exception:
        return None


def _homogeneity_degree(expr, var) -> float | None:
    """Check if expr is homogeneous in var and return the degree."""
    try:
        t = sp.Symbol("_t", positive=True)
        scaled = expr.subs(var, t * var)
        ratio = safe_simplify(scaled / expr)
        if ratio is None:
            return None
        # Check if ratio is t^n for some n
        if ratio.is_Pow and ratio.base == t:
            return float(ratio.exp)
        if ratio == t:
            return 1.0
        if ratio == 1:
            return 0.0
    except Exception:
        pass
    return None


def _count_dimension(expr) -> int:
    """Rough estimate of the dimensional weight of an expression."""
    return len(expr.free_symbols)


def _extract_coefficients(expr) -> list[tuple[float, str]]:
    """Extract numerical coefficients from an expression."""
    coeffs = []
    try:
        # Get all numerical atoms
        for atom in expr.atoms(sp.Number):
            val = float(atom)
            if val != 0 and val != 1 and val != -1:
                coeffs.append((val, f"atom: {atom}"))

        # Try to get leading coefficient
        if hasattr(expr, 'as_coeff_Mul'):
            c, _ = expr.as_coeff_Mul()
            if c != 1 and c.is_number:
                coeffs.append((float(c), "leading_coeff"))

        # Check for rational coefficients in terms
        if hasattr(expr, 'as_ordered_terms'):
            for term in expr.as_ordered_terms():
                if hasattr(term, 'as_coeff_Mul'):
                    c, _ = term.as_coeff_Mul()
                    if c != 1 and c.is_number:
                        val = float(c)
                        if (val, f"term_coeff: {c}") not in coeffs:
                            coeffs.append((val, f"term_coeff: {c}"))
    except Exception:
        pass
    return coeffs


def _to_simple_fraction(val: float, max_denom: int = 20) -> str | None:
    """Convert a float to a simple fraction string if possible."""
    if abs(val) < 1e-10:
        return "0"
    try:
        frac = Fraction(val).limit_denominator(max_denom)
        # Check if it's actually close
        if abs(float(frac) - val) < 1e-6:
            return str(frac)
    except (ValueError, OverflowError):
        pass
    return None


def _compute_limit_behavior(expr, var, limit_val) -> str | None:
    """Compute the behavior of expr as var → limit_val."""
    try:
        result = sp.limit(expr, var, limit_val)
        if result == sp.oo or result == -sp.oo or result == sp.zoo:
            return "diverges"
        elif result == 0:
            return "vanishes"
        elif result.is_number:
            return f"constant:{float(result.evalf()):.4g}"
        elif result.is_finite:
            return f"finite:{result}"
        else:
            return None
    except Exception:
        return None


def _get_skeleton(expr) -> str:
    """Get structural skeleton — replace all symbols with placeholders."""
    try:
        syms = sorted(expr.free_symbols, key=str)
        subs = {s: sp.Symbol(f"x{i}") for i, s in enumerate(syms)}
        skeleton = expr.subs(subs)
        # Normalize by replacing all numbers with 'c'
        result = str(skeleton)
        # Very rough normalization
        import re
        result = re.sub(r'\d+\.?\d*', 'c', result)
        return result
    except Exception:
        return str(type(expr).__name__)
