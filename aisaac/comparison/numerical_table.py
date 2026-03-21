"""
Numerical Prediction Table.

Instead of comparing symbolic expressions, extract and compare
NUMERICAL predictions across theories. Numbers don't lie.

Builds a table: quantity × theory → numerical value/coefficient.
Disagreements and agreements in this table are real physics.
"""
from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field

import sympy as sp
from rich.console import Console
from rich.table import Table

from ..knowledge.base import KnowledgeBase

log = logging.getLogger(__name__)
console = Console()


@dataclass
class NumericalPrediction:
    theory: str
    quantity_type: str
    description: str
    value: float | str  # float if numeric, str if symbolic
    uncertainty: float | None = None
    paper_arxiv_id: str = ""
    formula_id: int = 0
    source_latex: str = ""


@dataclass
class QuantityComparison:
    quantity_type: str
    predictions: list[NumericalPrediction]
    theories_agree: list[str] = field(default_factory=list)
    theories_disagree: list[str] = field(default_factory=list)
    consensus_value: float | str | None = None
    is_universal: bool = False
    is_gap: bool = False  # True if some theories have no prediction


def extract_numerical_predictions(kb: KnowledgeBase) -> list[NumericalPrediction]:
    """Extract numerical predictions from all formulas in the knowledge base."""
    predictions = []
    formulas = kb.get_all_formulas()

    for f in formulas:
        qt = f.get("quantity_type", "other")
        if qt == "other":
            continue

        theory = f.get("theory_slug", "")
        desc = f.get("description", "")
        latex = f.get("latex", "")
        sympy_str = f.get("normalized_sympy") or f.get("sympy_expr", "")

        # Strategy 1: Try to evaluate sympy expression to a number
        num_val = _try_evaluate_sympy(sympy_str)

        # Strategy 2: Extract numbers from description text
        if num_val is None:
            num_val = _extract_number_from_text(desc + " " + latex, qt)

        # Strategy 3: Extract key coefficients
        if num_val is None:
            num_val = _extract_coefficient(sympy_str, qt)

        if num_val is not None:
            predictions.append(NumericalPrediction(
                theory=theory,
                quantity_type=qt,
                description=desc[:100],
                value=num_val,
                formula_id=f.get("id", 0),
                source_latex=latex[:100],
                paper_arxiv_id=str(f.get("paper_id", "")),
            ))

    return predictions


def build_comparison_table(
    predictions: list[NumericalPrediction],
) -> list[QuantityComparison]:
    """Build quantity × theory comparison table."""
    from collections import defaultdict

    by_quantity = defaultdict(list)
    for p in predictions:
        by_quantity[p.quantity_type].append(p)

    comparisons = []
    for qt, preds in sorted(by_quantity.items()):
        # Group by theory
        by_theory = defaultdict(list)
        for p in preds:
            by_theory[p.theory].append(p)

        comp = QuantityComparison(
            quantity_type=qt,
            predictions=preds,
        )

        # Check agreement
        numeric_values = {}
        for theory, theory_preds in by_theory.items():
            # Take the most confident prediction per theory
            vals = [p.value for p in theory_preds if isinstance(p.value, (int, float))]
            if vals:
                numeric_values[theory] = vals[0]

        if len(numeric_values) >= 2:
            values = list(numeric_values.values())
            mean = sum(values) / len(values)
            spread = max(values) - min(values)
            rel_spread = spread / abs(mean) if mean != 0 else float('inf')

            if rel_spread < 0.1:  # Within 10%
                comp.theories_agree = list(numeric_values.keys())
                comp.consensus_value = mean
                comp.is_universal = len(comp.theories_agree) >= 3
            else:
                # Find which agree and which disagree
                for t, v in numeric_values.items():
                    if abs(v - mean) / abs(mean) < 0.1:
                        comp.theories_agree.append(t)
                    else:
                        comp.theories_disagree.append(t)
                comp.consensus_value = mean

        comparisons.append(comp)

    return comparisons


def find_prediction_gaps(kb: KnowledgeBase) -> list[dict]:
    """Find quantities that some theories predict but others don't.

    These gaps are research opportunities: can Theory B compute
    what Theory A predicts?
    """
    formulas = kb.get_all_formulas()

    from collections import defaultdict
    coverage = defaultdict(set)  # quantity_type → set of theories

    for f in formulas:
        qt = f.get("quantity_type", "other")
        if qt == "other":
            continue
        coverage[qt].add(f.get("theory_slug", ""))

    all_theories = {
        "string_theory", "loop_quantum_gravity", "cdt",
        "asymptotic_safety", "causal_sets", "horava_lifshitz",
        "noncommutative_geometry", "emergent_gravity",
    }

    gaps = []
    for qt, theories_with in sorted(coverage.items()):
        theories_without = all_theories - theories_with
        if theories_with and theories_without:
            gaps.append({
                "quantity_type": qt,
                "has_prediction": sorted(theories_with),
                "missing_prediction": sorted(theories_without),
                "coverage": f"{len(theories_with)}/{len(all_theories)}",
            })

    return gaps


def print_numerical_table(comparisons: list[QuantityComparison]):
    """Print a rich table of numerical predictions."""
    table = Table(title="Numerical Predictions Across Theories")
    table.add_column("Quantity", style="bold")
    table.add_column("Theory")
    table.add_column("Value", justify="right")
    table.add_column("Description", max_width=50)

    for comp in comparisons:
        for i, p in enumerate(comp.predictions):
            qty_label = comp.quantity_type if i == 0 else ""
            val_str = f"{p.value:.4g}" if isinstance(p.value, float) else str(p.value)
            table.add_row(qty_label, p.theory, val_str, p.description)
        table.add_row("", "", "", "")  # blank separator

    console.print(table)


def print_gap_table(gaps: list[dict]):
    """Print prediction gaps."""
    table = Table(title="Prediction Gaps (Research Opportunities)")
    table.add_column("Quantity", style="bold")
    table.add_column("Has Prediction", style="green")
    table.add_column("Missing", style="red")
    table.add_column("Coverage")

    for g in gaps:
        table.add_row(
            g["quantity_type"],
            ", ".join(g["has_prediction"]),
            ", ".join(g["missing_prediction"]),
            g["coverage"],
        )

    console.print(table)


def _try_evaluate_sympy(expr_str: str) -> float | None:
    """Try to evaluate a sympy expression to a pure number."""
    if not expr_str:
        return None
    try:
        expr = sp.sympify(expr_str)
        if not isinstance(expr, sp.Basic):
            return None
        # Only works if expression has no free symbols
        if expr.free_symbols:
            return None
        val = float(expr.evalf())
        if not (val != val):  # not NaN
            return val
    except Exception:
        pass
    return None


def _extract_number_from_text(text: str, quantity_type: str) -> float | None:
    """Extract numerical values from description text. Domain-agnostic."""
    text = text.lower().replace("−", "-").replace("–", "-")

    # Look for patterns like "= 2", "≈ 1.98", "→ 2", "is approximately 3/2"
    patterns = [
        r"(?:=|≈|→|\\approx|\\to|\\sim)\s*([-]?[\d.]+(?:\s*[±]\s*[\d.]+)?)",
        r"(?:equals?|gives?|yields?|predicts?|is)\s+([-]?[\d.]+)",
        r"([-]?[\d]+/[\d]+)",  # fractions like 3/2
    ]

    for pat in patterns:
        m = re.search(pat, text)
        if m:
            try:
                val_str = m.group(1).strip()
                if "/" in val_str:
                    num, den = val_str.split("/")
                    return float(num) / float(den)
                return float(val_str)
            except ValueError:
                continue

    return None


def _extract_coefficient(sympy_str: str, quantity_type: str) -> float | None:
    """Extract leading coefficient from a sympy expression."""
    if not sympy_str:
        return None
    try:
        expr = sp.sympify(sympy_str)
        if not isinstance(expr, sp.Basic):
            return None

        # For simple expressions like "2" or "Rational(3,2)"
        if not expr.free_symbols:
            val = float(expr.evalf())
            if not (val != val):
                return val

        # Try to extract leading coefficient
        if hasattr(expr, 'as_leading_term'):
            lt = expr.as_leading_term()
            if not lt.free_symbols:
                return float(lt.evalf())
    except Exception:
        pass
    return None
