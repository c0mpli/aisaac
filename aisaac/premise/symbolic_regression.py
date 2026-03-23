"""
Symbolic Regression on Cross-Theory Predictions.

Planck's method: fit a function to the data, then reverse-engineer
what assumption produces that function.

The "data" here isn't experimental — it's the predictions of 8 theories.
Each theory is like a different instrument measuring the same reality.
If a single function f(x) fits all theories' predictions for a quantity,
then f encodes the unknown structure and x encodes what actually
differs between theories.
"""
from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass, field

log = logging.getLogger(__name__)


@dataclass
class TheoryDataPoint:
    theory: str
    quantity: str
    value: float
    # Theory-specific parameters that might explain the value
    z: float = 1.0          # dynamical critical exponent (HL: 3, others: 1)
    d_top: float = 4.0      # topological dimension assumed
    eta: float = 0.0        # anomalous dimension (AS: 2, others: 0)
    n_dof: float = 1.0      # effective degrees of freedom
    is_discrete: float = 0.0  # 0 = continuous, 1 = discrete
    is_background_indep: float = 0.0  # 0 = no, 1 = yes
    has_foliation: float = 0.0  # 0 = no, 1 = yes (CDT, HL)
    preserves_lorentz: float = 1.0  # 0 = breaks, 1 = preserves


def build_spectral_dimension_data() -> list[TheoryDataPoint]:
    """
    Spectral dimension predictions from each theory.
    These are the actual numbers from the papers in the DB.
    """
    return [
        TheoryDataPoint(
            theory="asymptotic_safety", quantity="spectral_dimension",
            value=2.0,  # exact, from η_N = 2 at fixed point
            z=1.0, d_top=4.0, eta=2.0, n_dof=1.0,
            is_discrete=0, is_background_indep=0, has_foliation=0, preserves_lorentz=1,
        ),
        TheoryDataPoint(
            theory="cdt", quantity="spectral_dimension",
            value=1.5,  # from fit D_S(σ) = a - b/(c+σ), σ→0 gives ~3/2
            z=1.0, d_top=4.0, eta=0.0, n_dof=1.0,
            is_discrete=1, is_background_indep=1, has_foliation=1, preserves_lorentz=1,
        ),
        TheoryDataPoint(
            theory="horava_lifshitz", quantity="spectral_dimension",
            value=2.0,  # exact: d_s = 1 + (d-1)/z = 1 + 3/3 = 2 for z=3
            z=3.0, d_top=4.0, eta=0.0, n_dof=1.0,
            is_discrete=0, is_background_indep=0, has_foliation=1, preserves_lorentz=0,
        ),
        TheoryDataPoint(
            theory="noncommutative_geometry", quantity="spectral_dimension",
            value=3.0,  # κ-Minkowski gives d_s=3 in UV, NOT 2
            z=1.0, d_top=4.0, eta=0.0, n_dof=1.0,
            is_discrete=0, is_background_indep=0, has_foliation=0, preserves_lorentz=0,
        ),
        TheoryDataPoint(
            theory="causal_sets", quantity="spectral_dimension",
            value=2.0,  # Carlip's estimate, approximate
            z=1.0, d_top=4.0, eta=0.0, n_dof=1.0,
            is_discrete=1, is_background_indep=1, has_foliation=0, preserves_lorentz=1,
        ),
        TheoryDataPoint(
            theory="loop_quantum_gravity", quantity="spectral_dimension",
            value=2.0,  # from various calculations
            z=1.0, d_top=4.0, eta=0.0, n_dof=1.0,
            is_discrete=1, is_background_indep=1, has_foliation=0, preserves_lorentz=1,
        ),
    ]


def build_log_correction_data() -> list[TheoryDataPoint]:
    """
    BH entropy logarithmic correction coefficient from each theory.
    S = A/4G + c * ln(A/4G) + ...
    What is c?
    """
    return [
        TheoryDataPoint(
            theory="loop_quantum_gravity", quantity="bh_log_correction",
            value=-1.5,  # -3/2 from Kaul-Majumdar
            z=1.0, d_top=4.0, eta=0.0, n_dof=1.0,
            is_discrete=1, is_background_indep=1, has_foliation=0, preserves_lorentz=1,
        ),
        TheoryDataPoint(
            theory="loop_quantum_gravity_alt", quantity="bh_log_correction",
            value=-2.0,  # alternative calculation gives -2
            z=1.0, d_top=4.0, eta=0.0, n_dof=1.0,
            is_discrete=1, is_background_indep=1, has_foliation=0, preserves_lorentz=1,
        ),
        TheoryDataPoint(
            theory="asymptotic_safety", quantity="bh_log_correction",
            value=-2.0,  # from Euclidean gravity methods (d=4)
            z=1.0, d_top=4.0, eta=2.0, n_dof=1.0,
            is_discrete=0, is_background_indep=0, has_foliation=0, preserves_lorentz=1,
        ),
        TheoryDataPoint(
            theory="string_theory", quantity="bh_log_correction",
            value=-0.5,  # from Sen's entropy function for extremal BH
            z=1.0, d_top=10.0, eta=0.0, n_dof=1.0,
            is_discrete=0, is_background_indep=0, has_foliation=0, preserves_lorentz=1,
        ),
    ]


def run_symbolic_regression(
    data: list[TheoryDataPoint],
    quantity_name: str = "unknown",
    max_iterations: int = 100,
    populations: int = 30,
) -> dict:
    """
    Run PySR on cross-theory prediction data.

    Input: theory predictions + theory-specific parameters
    Output: the simplest function that fits all predictions

    If the function contains a term not in any theory,
    that's a candidate for a new physical concept.
    """
    try:
        from pysr import PySRRegressor
    except ImportError:
        log.error("PySR not installed: uv pip install pysr")
        return {"error": "PySR not installed"}

    if len(data) < 3:
        return {"error": f"Need at least 3 data points, got {len(data)}"}

    # Build feature matrix X and target y
    feature_names = [
        "z", "d_top", "eta", "n_dof",
        "is_discrete", "is_background_indep", "has_foliation", "preserves_lorentz",
    ]

    X = np.array([[
        d.z, d.d_top, d.eta, d.n_dof,
        d.is_discrete, d.is_background_indep, d.has_foliation, d.preserves_lorentz,
    ] for d in data])

    y = np.array([d.value for d in data])

    log.info(f"Running PySR on {quantity_name}: {len(data)} data points, {len(feature_names)} features")
    log.info(f"  Values: {[d.value for d in data]}")
    log.info(f"  Theories: {[d.theory for d in data]}")

    # Configure PySR
    model = PySRRegressor(
        niterations=max_iterations,
        populations=populations,
        binary_operators=["+", "-", "*", "/"],
        unary_operators=["sqrt", "log", "abs"],
        maxsize=20,           # keep formulas simple
        maxdepth=5,
        parsimony=0.01,       # prefer simpler
        population_size=50,
        timeout_in_seconds=120,
        temp_equation_file=True,
        verbosity=0,
    )

    try:
        model.fit(X, y, variable_names=feature_names)
    except Exception as e:
        log.error(f"PySR fitting failed: {e}")
        return {"error": str(e)}

    # Extract results
    equations = []
    try:
        for i in range(len(model.equations_)):
            row = model.equations_.iloc[i]
            equations.append({
                "complexity": int(row["complexity"]),
                "loss": float(row["loss"]),
                "equation": str(row["equation"]),
            })
    except Exception as e:
        log.warning(f"Could not parse PySR equations: {e}")

    best = str(model.sympy()) if hasattr(model, 'sympy') else "unknown"
    best_score = float(model.score(X, y)) if hasattr(model, 'score') else 0.0

    result = {
        "quantity": quantity_name,
        "n_datapoints": len(data),
        "theories": [d.theory for d in data],
        "values": [d.value for d in data],
        "best_equation": best,
        "best_score": best_score,
        "all_equations": equations[:10],
        "feature_names": feature_names,
    }

    log.info(f"  Best equation: {best} (R² = {best_score:.4f})")

    # Check: does the best equation use unexpected terms?
    unexpected_terms = []
    known_relations = {"d_top", "z", "eta", "1", "2", "3", "4"}
    equation_str = str(best).lower()
    for feat in feature_names:
        if feat in equation_str and feat not in {"z", "d_top", "eta"}:
            unexpected_terms.append(feat)

    if unexpected_terms:
        result["unexpected_terms"] = unexpected_terms
        result["interpretation"] = (
            f"The best-fit function uses {unexpected_terms} — "
            f"parameters that no single theory considers fundamental. "
            f"This suggests the spectral dimension depends on whether "
            f"the theory is discrete/continuous or has a foliation."
        )

    return result


def run_all_regressions() -> list[dict]:
    """Run symbolic regression on all available cross-theory quantities."""
    results = []

    # 1. Spectral dimension
    ds_data = build_spectral_dimension_data()
    results.append(run_symbolic_regression(ds_data, "spectral_dimension"))

    # 2. Log correction coefficient
    log_data = build_log_correction_data()
    results.append(run_symbolic_regression(log_data, "bh_log_correction"))

    return results
