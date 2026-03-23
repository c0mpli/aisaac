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
    # Theory-specific parameters (physicist-verified where possible)
    z: float = 1.0              # dynamical critical exponent (HL: 3, others: 1)
    d_top: float = 4.0          # topological dimension assumed
    eta: float = 0.0            # anomalous dimension (AS: 2, others: 0)
    is_discrete: float = 0.0    # 0 = continuous, 1 = discrete
    is_background_indep: float = 0.0
    has_foliation: float = 0.0  # 0 = no, 1 = yes (CDT, HL)
    preserves_lorentz: float = 1.0
    # Benedetti's conjecture: d_s = dimension of maximal commutative subspace
    n_commuting_dirs: float = 4.0  # how many directions "commute" at Planck scale
    uncertainty: float = 0.0    # measurement/calculation uncertainty


# ══════════════════════════════════════════════════════════════════
# VERIFIED DATA — numbers checked against original publications
# DO NOT change these without citing the paper
# ══════════════════════════════════════════════════════════════════

def build_spectral_dimension_data() -> list[TheoryDataPoint]:
    """
    UV spectral dimension predictions — VERIFIED from original papers.

    Sources:
      CDT:  Ambjorn, Jurkiewicz, Loll (2005) hep-th/0505113
      AS:   Lauscher & Reuter (2005) hep-th/0508202
      HL:   Horava (2009) arXiv:0902.3657
      LQG:  Modesto (2009) arXiv:0812.2214
      CS:   Eichhorn & Mizera (2014) arXiv:1311.2530
      NCG:  Benedetti (2009) arXiv:0811.1396
      EG:   NOT COMPUTED — prediction target
    """
    return [
        # ── d_s ≈ 2 cluster ──────────────────────────────
        TheoryDataPoint(
            theory="asymptotic_safety", quantity="spectral_dimension",
            value=2.0, uncertainty=0.0,  # EXACT from η_N = 2 at NGFP
            z=1.0, d_top=4.0, eta=2.0,
            is_discrete=0, is_background_indep=0, has_foliation=0, preserves_lorentz=1,
            n_commuting_dirs=float('nan'),  # NOT DEFINED for AS — no NC structure
        ),
        TheoryDataPoint(
            theory="cdt", quantity="spectral_dimension",
            value=1.80, uncertainty=0.25,  # Monte Carlo numerical result
            z=1.0, d_top=4.0, eta=0.0,
            is_discrete=1, is_background_indep=1, has_foliation=1, preserves_lorentz=1,
            n_commuting_dirs=float('nan'),  # NOT DEFINED for CDT — no NC structure
        ),
        TheoryDataPoint(
            theory="horava_lifshitz", quantity="spectral_dimension",
            value=2.0, uncertainty=0.0,  # EXACT: d_s = 1 + (d-1)/z = 1+3/3 = 2
            z=3.0, d_top=4.0, eta=0.0,
            is_discrete=0, is_background_indep=0, has_foliation=1, preserves_lorentz=0,
            n_commuting_dirs=float('nan'),  # NOT DEFINED for HL — no NC structure
        ),
        TheoryDataPoint(
            theory="loop_quantum_gravity", quantity="spectral_dimension",
            value=2.0, uncertainty=0.0,  # Modesto 2009, Planck scale
            z=1.0, d_top=4.0, eta=0.0,
            is_discrete=1, is_background_indep=1, has_foliation=0, preserves_lorentz=1,
            n_commuting_dirs=float('nan'),  # NOT DEFINED for LQG — debatable
        ),
        # ── d_s = 3 (NCG) ────────────────────────────────
        TheoryDataPoint(
            theory="ncg_kappa_minkowski", quantity="spectral_dimension",
            value=3.0, uncertainty=0.0,  # EXACT: Benedetti 2009
            # κ-Minkowski: 3 spatial dirs commute, time doesn't
            z=1.0, d_top=4.0, eta=0.0,
            is_discrete=0, is_background_indep=0, has_foliation=0, preserves_lorentz=0,
            n_commuting_dirs=3.0,  # ONLY theory where this is independently defined
        ),
        # ── Causal sets: anomalous (d_s INCREASES) ───────
        # Eichhorn & Mizera 2014: d_s > d_top for small causal sets
        # This is qualitatively different — nonlocality adds effective dimensions
        # Excluding from PySR fit (doesn't fit the same pattern)
        # But noting: CS nonlocality → MORE commuting directions → d_s > 4
    ]


def build_emergent_gravity_prediction() -> TheoryDataPoint:
    """
    Emergent gravity: d_s has NOT been computed.
    This is the prediction target.

    Properties of emergent gravity:
    - Spacetime emerges from entanglement
    - No fundamental metric
    - Holographic (boundary encodes bulk)
    - No foliation
    - Lorentz invariance preserved (low energy)
    - Not fundamentally discrete

    Benedetti conjecture: d_s = n_commuting_dirs
    Question: how many directions "commute" in emergent gravity at Planck scale?
    """
    return TheoryDataPoint(
        theory="emergent_gravity", quantity="spectral_dimension",
        value=float('nan'),  # UNKNOWN — this is what we're predicting
        z=1.0, d_top=4.0, eta=0.0,
        is_discrete=0, is_background_indep=0, has_foliation=0, preserves_lorentz=1,
        n_commuting_dirs=float('nan'),  # also unknown
    )


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
        "z", "d_top", "eta", "n_commuting_dirs",
        "is_discrete", "is_background_indep", "has_foliation", "preserves_lorentz",
    ]

    X = np.array([[
        d.z, d.d_top, d.eta, d.n_commuting_dirs,
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
