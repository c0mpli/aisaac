# Symbolic Regression on Verified Spectral Dimension Data

**Date:** March 24, 2026
**Method:** PySR (symbolic regression) on hand-verified cross-theory predictions
**Approach:** Planck's method — fit a function to predictions from multiple theories, see what the function reveals

## Verified Input Data

Every number confirmed against the original publication. No LLM extraction.

| Theory | d_s (UV) | Error | Source |
|--------|----------|-------|--------|
| Asymptotic Safety | 2.0 | exact | Lauscher & Reuter 2005, hep-th/0508202 |
| CDT | 1.80 | ±0.25 | Ambjorn, Jurkiewicz, Loll 2005, hep-th/0505113 |
| Horava-Lifshitz | 2.0 | exact | Horava 2009, arXiv:0902.3657 |
| LQG (spin foam) | 2.0 | exact | Modesto 2009, arXiv:0812.2214 |
| NCG (κ-Minkowski) | 3.0 | exact | Benedetti 2009, arXiv:0811.1396 |

Not included (anomalous behavior): Causal Sets (d_s increases beyond 4, Eichhorn & Mizera 2014).
Not computed by any theory: Emergent Gravity.

## Theory Features (independently defined, NOT derived from d_s)

| Theory | Lorentz | Foliation | Discrete | z | Background-indep | Causality |
|--------|---------|-----------|----------|---|-----------------|-----------|
| AS | 1 | 0 | 0 | 2 | 0 | 0 |
| CDT | 1 | 1 | 1 | 2 | 1 | 1 |
| HL | 0 | 1 | 0 | 3 | 0 | 1 |
| LQG | 1 | 0 | 1 | 2 | 1 | 0 |
| NCG | 0 | 0 | 0 | 1 | 0 | 0 |

## PySR Results

### Run 1: All 6 features

**Best equation (loss = 0.0):**
```
d_s = |preserves_lorentz + causality_fundamental - 1.6| + 1.4
```

Verification:
- AS: |1 + 0 - 1.6| + 1.4 = 0.6 + 1.4 = **2.0** ✓
- CDT: |1 + 1 - 1.6| + 1.4 = 0.4 + 1.4 = **1.8** ✓
- HL: |0 + 1 - 1.6| + 1.4 = 0.6 + 1.4 = **2.0** ✓
- LQG: |1 + 0 - 1.6| + 1.4 = 0.6 + 1.4 = **2.0** ✓
- NCG: |0 + 0 - 1.6| + 1.4 = 1.6 + 1.4 = **3.0** ✓

### Run 2: Without z_exponent (removing interpretive feature)

**Best equation (loss = 0.0):**
```
d_s = |1.6 - has_foliation - preserves_lorentz| + 1.4
```

Verification:
- AS: |1.6 - 0 - 1| + 1.4 = 0.6 + 1.4 = **2.0** ✓
- CDT: |1.6 - 1 - 1| + 1.4 = 0.4 + 1.4 = **1.8** ✓
- HL: |1.6 - 1 - 0| + 1.4 = 0.6 + 1.4 = **2.0** ✓
- LQG: |1.6 - 0 - 1| + 1.4 = 0.6 + 1.4 = **2.0** ✓
- NCG: |1.6 - 0 - 0| + 1.4 = 1.6 + 1.4 = **3.0** ✓

## Predictions

### Emergent Gravity (not computed by any theory)

| | Lorentz | Foliation | Discrete | z | BG-indep | Causal |
|---|---------|-----------|----------|---|----------|--------|
| EG | 1 | 0 | 0 | 1 | 0 | 0 |

- **Run 1 prediction: d_s = 2.0**
- **Run 2 prediction: d_s = 2.0**
- Both runs agree.

### Causal Sets (sanity check — known to be anomalous, d_s > 4)

- Run 1 prediction: d_s = 1.8
- Run 2 prediction: d_s = 2.0
- **Both wrong.** Causal sets are anomalous (d_s increases). The formula can't capture this — it only models theories where d_s decreases in the UV.

## Interpretation

Both runs found formulas with the same structure:

**d_s = |constant - (structural constraints)| + 1.4**

The pattern: start from a "base" ≈ 3 (NCG's value when no constraints apply), subtract structural constraints (Lorentz invariance, foliation, causality), take absolute value, add 1.4.

- **No constraints** (NCG): d_s = 3.0 — maximum freedom
- **One constraint** (AS, HL, LQG): d_s = 2.0
- **Two constraints** (CDT): d_s = 1.8 — most constrained

Run 1 uses `preserves_lorentz + causality_fundamental` as the constraint.
Run 2 uses `has_foliation + preserves_lorentz` as the constraint.
Both give the same predictions because the binary features happen to sum to the same values.

## What This Means

The formula says: **the UV spectral dimension measures how much geometric freedom remains after imposing structural constraints.** More constraints = lower d_s. This is physically sensible — restricting the geometry reduces the number of effective directions a random walker can explore.

## Honest Limitations

1. **5 data points, 6 features.** Overfitting is guaranteed. R² = 1.0 is expected, not impressive.
2. **Only 3 distinct d_s values** (1.8, 2.0, 3.0). Any formula that maps 3 binary combinations to 3 values will fit.
3. **The emergent gravity prediction (d_s = 2.0) is the mean.** Most theories give ~2, so predicting 2 is the safe default, not a deep insight.
4. **Causal sets are anomalous and the formula can't capture it.** This means the formula misses at least one class of physics.
5. **Feature assignments are debatable.** CDT "preserves Lorentz" is arguable (it enforces Lorentzian signature but has a foliation). Different assignments → different formulas.

## What Would Make This Meaningful

- **More data points.** If 10+ theories with verified d_s values and genuine numerical spread were available, PySR could find non-trivial patterns.
- **Non-binary features.** Continuous parameters (like z_exponent) with verified values would give PySR more to work with.
- **Multiple quantities simultaneously.** Fitting d_s AND log correction AND Newton coefficient together would constrain the function space much more tightly.
- **A physicist verifying the feature assignments.** Whether CDT "preserves Lorentz" or not changes the result.

## Novel Output

The emergent gravity prediction (d_s = 2.0) is not novel — it's the modal value. The pattern "constraints reduce d_s" is physically intuitive but not new.

The genuinely useful output is the **framework**: applying symbolic regression to cross-theory predictions. With more verified data points, this method could find non-trivial relationships that no single theory contains.
