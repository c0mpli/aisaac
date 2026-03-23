"""
Symbolic regression on VERIFIED spectral dimension data.

Every number here is hand-checked against the original publication.
No LLM extraction. No database queries. Hardcoded with citations.

This is Planck's method: fit a function to cross-theory predictions,
then see what the function tells you about the underlying structure.
"""
import numpy as np
import pandas as pd
from pysr import PySRRegressor

# ============================================================
# VERIFIED SPECTRAL DIMENSION DATA
# Each value manually confirmed from the original paper
# ============================================================

data = {
    "theory": [
        "AS",        # Asymptotic Safety
        "CDT",       # Causal Dynamical Triangulations
        "HL",        # Horava-Lifshitz
        "LQG",       # Loop Quantum Gravity
        "NCG_kappa", # Noncommutative Geometry (κ-Minkowski)
    ],

    # TARGET: UV spectral dimension
    "d_s": [
        2.0,   # Lauscher & Reuter 2005 hep-th/0508202 (EXACT, analytical)
        1.80,  # Ambjorn+ 2005 hep-th/0505113 (numerical, ±0.25)
        2.0,   # Horava 2009 arXiv:0902.3657 (EXACT, d_s = 1+D/z, z=3, D=3)
        2.0,   # Modesto 2009 arXiv:0812.2214 (EXACT, spin foam)
        3.0,   # Benedetti 2009 arXiv:0811.1396 (EXACT, κ-Poincare)
    ],

    # ERROR BARS (0 = exact analytical result)
    "d_s_error": [
        0.0,   # AS: exact
        0.25,  # CDT: Monte Carlo
        0.0,   # HL: exact
        0.0,   # LQG: exact (but model-dependent)
        0.0,   # NCG: exact
    ],

    # ============================================================
    # THEORY FEATURES — independently defined, NOT from d_s
    # ============================================================

    # Does the theory preserve exact Lorentz invariance?
    "preserves_lorentz": [1, 1, 0, 1, 0],

    # Does the theory require a preferred time foliation?
    "has_foliation": [0, 1, 1, 0, 0],

    # Is spacetime fundamentally discrete in this theory?
    "is_discrete": [0, 1, 0, 1, 0],

    # UV dynamical critical exponent z
    # AS: 2 (from η_N=-2, effective z=2) — INTERPRETIVE, see note
    # CDT: 2 (from numerical fit, approximate)
    # HL: 3 (by construction)
    # LQG: 2 (from area spectrum scaling)
    # NCG: 1 (no anisotropic scaling)
    "z_exponent": [2, 2, 3, 2, 1],

    # Is the theory background-independent?
    "background_independent": [0, 1, 0, 1, 0],

    # Is causality a fundamental input?
    "causality_fundamental": [0, 1, 1, 0, 0],
}

df = pd.DataFrame(data)

feature_cols = [
    "preserves_lorentz",
    "has_foliation",
    "is_discrete",
    "z_exponent",
    "background_independent",
    "causality_fundamental",
]

X = df[feature_cols].values
y = df["d_s"].values
errors = df["d_s_error"].values

# Weight: exact results weighted more than numerical
weights = 1.0 / np.maximum(errors, 0.05)
weights = weights / weights.sum()

print("=" * 60)
print("VERIFIED SPECTRAL DIMENSION DATA FOR PySR")
print("=" * 60)
print(df[["theory", "d_s", "d_s_error"] + feature_cols].to_string(index=False))
print()
print(f"WARNING: 5 data points, {len(feature_cols)} features. Overfitting is guaranteed.")
print("The value is in physical interpretability, not R² score.")
print()

# ============================================================
# RUN 1: All features
# ============================================================

print("=" * 60)
print("RUN 1: All features")
print("=" * 60)

model = PySRRegressor(
    niterations=1000,
    binary_operators=["+", "-", "*", "/"],
    unary_operators=["sqrt", "abs"],
    maxsize=15,
    populations=30,
    population_size=50,
    ncycles_per_iteration=500,
    weight_optimize=0.01,
    # Default MSE loss, weights handled by PySR internally
    temp_equation_file=True,
    tempdir="/tmp/pysr_verified_1",
    random_state=42,
    deterministic=True,
    parallelism="serial",
    timeout_in_seconds=300,
)

print(f"Running PySR: {len(y)} points, {len(feature_cols)} features...")
model.fit(X, y, weights=weights, variable_names=feature_cols)

print()
print("Equations by complexity:")
for i, row in model.equations_.iterrows():
    print(f"  complexity={int(row['complexity']):2d}  loss={float(row['loss']):.6f}  {row['equation']}")

print()
print("Verification:")
for i, row in df.iterrows():
    predicted = model.predict(X[i:i+1])[0]
    actual = row["d_s"]
    error = row["d_s_error"]
    match = "✓" if abs(predicted - actual) <= max(error, 0.1) else "✗"
    print(f"  {row['theory']:12s}: actual={actual:.2f}±{error:.2f}, predicted={predicted:.2f} {match}")

# ============================================================
# RUN 2: Without z_exponent (since z assignments are interpretive)
# ============================================================

print()
print("=" * 60)
print("RUN 2: Without z_exponent (removing interpretive feature)")
print("=" * 60)

feature_cols_no_z = [c for c in feature_cols if c != "z_exponent"]
X_no_z = df[feature_cols_no_z].values

model2 = PySRRegressor(
    niterations=1000,
    binary_operators=["+", "-", "*", "/"],
    unary_operators=["sqrt", "abs"],
    maxsize=15,
    populations=30,
    population_size=50,
    ncycles_per_iteration=500,
    weight_optimize=0.01,
    # Default MSE loss, weights handled by PySR internally
    temp_equation_file=True,
    tempdir="/tmp/pysr_verified_2",
    random_state=42,
    deterministic=True,
    parallelism="serial",
    timeout_in_seconds=300,
)

print(f"Running PySR: {len(y)} points, {len(feature_cols_no_z)} features...")
model2.fit(X_no_z, y, weights=weights, variable_names=feature_cols_no_z)

print()
print("Equations by complexity:")
for i, row in model2.equations_.iterrows():
    print(f"  complexity={int(row['complexity']):2d}  loss={float(row['loss']):.6f}  {row['equation']}")

print()
print("Verification:")
for i, row in df.iterrows():
    predicted = model2.predict(X_no_z[i:i+1])[0]
    actual = row["d_s"]
    error = row["d_s_error"]
    match = "✓" if abs(predicted - actual) <= max(error, 0.1) else "✗"
    print(f"  {row['theory']:12s}: actual={actual:.2f}±{error:.2f}, predicted={predicted:.2f} {match}")

# ============================================================
# PREDICTIONS
# ============================================================

print()
print("=" * 60)
print("PREDICTIONS")
print("=" * 60)

# Emergent Gravity
# preserves_lorentz=1, has_foliation=0, is_discrete=0,
# z_exponent=1, background_independent=0, causality_fundamental=0
eg_all = np.array([[1, 0, 0, 1, 0, 0]])
eg_no_z = np.array([[1, 0, 0, 0, 0]])
eg_pred1 = model.predict(eg_all)[0]
eg_pred2 = model2.predict(eg_no_z)[0]

print(f"\nEmergent Gravity:")
print(f"  (lorentz=1, foliation=0, discrete=0, z=1, bg_indep=0, causal=0)")
print(f"  Run 1 (with z):    d_s = {eg_pred1:.3f}")
print(f"  Run 2 (without z): d_s = {eg_pred2:.3f}")

# Causal Sets (sanity check — known to be anomalous, d_s > 4)
cs_all = np.array([[1, 0, 1, 1, 0, 1]])
cs_no_z = np.array([[1, 0, 1, 0, 1]])
cs_pred1 = model.predict(cs_all)[0]
cs_pred2 = model2.predict(cs_no_z)[0]

print(f"\nCausal Sets (sanity check — actual: d_s > 4, anomalous):")
print(f"  (lorentz=1, foliation=0, discrete=1, z=1, bg_indep=0, causal=1)")
print(f"  Run 1 (with z):    d_s = {cs_pred1:.3f}")
print(f"  Run 2 (without z): d_s = {cs_pred2:.3f}")
print(f"  (If formula gives <4, it cannot capture causal sets' anomalous behavior)")

# ============================================================
# HONEST ASSESSMENT
# ============================================================

print()
print("=" * 60)
print("HONEST ASSESSMENT")
print("=" * 60)
print("""
1. With 5 data points and 5-6 features, ANY formula can overfit.
   R² = 1.0 is expected, not impressive.

2. The value is whether the formula is PHYSICALLY INTERPRETABLE:
   - Does it use features that make physical sense?
   - Does the direction of dependence make sense?
   - Is it consistent with known limits?

3. The emergent gravity prediction is the only novel output.
   If both runs agree on d_s ≈ 2, that's a weak prediction
   (most theories give ~2, so the mean works).
   If they disagree, the data is insufficient to constrain EG.

4. The causal sets prediction tests the formula's limits.
   CS is known to be anomalous (d_s increases, not decreases).
   If the formula can't capture this, it's missing physics.

5. z_exponent assignments for AS, CDT, LQG are interpretive.
   If results change significantly between Run 1 and Run 2,
   the z assignments are driving the fit, which is unreliable.
""")

# Save results
best1 = model.get_best()
best2 = model2.get_best()

import json
results = {
    "run1_best_equation": str(best1["equation"]),
    "run1_best_loss": float(best1["loss"]),
    "run2_best_equation": str(best2["equation"]),
    "run2_best_loss": float(best2["loss"]),
    "emergent_gravity_run1": float(eg_pred1),
    "emergent_gravity_run2": float(eg_pred2),
    "causal_sets_run1": float(cs_pred1),
    "causal_sets_run2": float(cs_pred2),
    "verified_data": data,
    "notes": "5 data points, overfitting guaranteed. Value is in interpretability not R².",
}

with open("data/pysr_verified_results.json", "w") as f:
    json.dump(results, f, indent=2, default=str)

print(f"Results saved to data/pysr_verified_results.json")
