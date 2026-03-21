# Second Run Results — Quantum Gravity (with sympy verification)

## Run Parameters
- **Date:** March 22, 2026
- **Model:** Claude Sonnet 4 (`claude-sonnet-4-20250514`)
- **Mode:** `--compare-only` (re-used 162 formulas from first run, no re-extraction)
- **Papers:** 76 across 8 quantum gravity theories
- **Formulas:** 162
- **Conjectures generated:** 17 (34 total including duplicates before dedup)
- **Known connections recall:** 11/14 (79%) — up from 0% in first run

## Key Improvement
Added sympy-verified conjecture generation: LLM writes Python/sympy code to derive relationships, code is executed in sandbox, only confirmed results become conjectures. Falls back to LLM prose if sympy finds nothing.

## Results Summary

| Status | Count |
|--------|-------|
| Verified (by system) | 6 |
| Known (rediscovered) | 2 |
| Disproved (by system) | 4 |
| Inconclusive | 5 |

## Known Connections Found (11/14 = 79% recall)

Found:
- Spectral dimension → 2 at short distances (Asymptotic Safety)
- Spectral dimension → 2 at short distances (Horava-Lifshitz)
- Spectral dimension universality across 5+ approaches
- Bekenstein-Hawking entropy from string theory microstate counting
- Bekenstein-Hawking entropy from LQG state counting
- Logarithmic correction to BH entropy: coefficient debate
- Leading quantum correction to Newton's potential (universal form)
- AdS/CFT: gravity in d+1 dimensions = CFT in d dimensions
- Ryu-Takayanagi: entanglement entropy = minimal surface area
- Planck-scale modified dispersion relation (multiple approaches)
- Carlip's argument for universal d_s → 2

Missed:
- Spectral dimension flows to 2 (CDT) — likely classification issue, CDT formulas exist but weren't matched
- Area quantization in LQG — no formulas extracted for area spectrum
- Running of Newton's constant near UV fixed point — formulas exist but comparison didn't flag it

## Verified Conjectures (System Assessment)

### 1. η = 2(1-z) / η = 2z-2 (Anomalous Dimension ↔ Lifshitz Scaling)
- **Sympy verified:** Yes (algebra confirmed)
- **Expert assessment needed:** The correct relation is η = 3(z-1)/z, not η = 2(z-1). Sympy confirmed the LLM's algebra was internally consistent, but the LLM started from wrong premises. This shows sympy verification catches algebra errors within the derivation but NOT errors in the setup.
- **Duplicate:** System generated two versions of the same claim (sign flip).

### 2. Scale-dependent holographic entropy deviation
- **Formula:** c³A/(4ℏG) - A/(4G) = A/(4G)(c³/ℏ - 1)
- **Assessment:** Algebraically trivial (just subtracting two expressions). The physical claim about scale-dependent c breaking entropy universality may be interesting but needs expert review.

### 3. Causal Set Spectral Dimension Matches CDT in Classical Limit
- **Assessment:** Both theories predict d_s → d at large scales. This is expected and not novel. The specific claim about convergence is imprecise.

### 4. LQG and Asymptotic Safety log corrections equivalence
- **Formula:** S_LQG = S_AS + (3/2)ln(ln 2) + const
- **Assessment:** Needs expert check. Is the AS log correction coefficient real or hallucinated? (Previous run fabricated N/6 coefficient.)

### 5. Universal Spectral Structure of Entanglement Entropy
- **Formula:** S_A = -Σ p_i ln p_i
- **Assessment:** This is just the definition of von Neumann entropy. The claim that RT and SSEE compute the same thing is interesting but the LaTeX is trivial.

## Comparison with First Run

| Metric | Run 1 (March 21) | Run 2 (March 22) |
|--------|-------------------|-------------------|
| Known connections recall | 0/14 (0%) | 11/14 (79%) |
| Verified conjectures | 4 | 6 |
| Disproved conjectures | 4 | 4 |
| Hallucinated formulas | Yes (N/6 fabricated) | TBD (need expert review) |
| Sympy verification | No | Yes |
| Duplicate detection | No | Partial (still generated η=2(1-z) and η=2z-2) |

## Remaining Issues

1. **Sympy verifies algebra, not physics.** It confirmed η = 2(z-1) is internally consistent but the derivation itself was wrong. Need to also verify that the starting formulas are correctly extracted from papers.
2. **Duplicate conjectures.** Same relationship generated twice with different signs.
3. **Trivial conjectures pass verification.** "S = -Σ p_i ln p_i" is a definition, not a discovery. Need a triviality filter.
4. **Log correction claim needs checking.** Is the AS log correction coefficient real this time or fabricated again?
