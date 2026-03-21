# First Run Results — Quantum Gravity

## Run Parameters
- **Date:** March 21, 2026
- **Model:** Claude Sonnet 4 (`claude-sonnet-4-20250514`)
- **Papers ingested:** 76 across 8 quantum gravity theories
- **Formulas extracted:** 162 (113 classified as "other", 49 with specific quantity types)
- **Cross-theory matches found:** 45
- **Conjectures generated:** 17
- **API calls:** 309 (extraction: 76, normalization: 162, conjecture: 33, verification: 32, paper writing: 6)
- **Tokens used:** 1,025,602 input + 159,899 output
- **API cost:** $5.48

## Theories Covered
| Theory | Papers | Formulas |
|--------|--------|----------|
| Loop Quantum Gravity | — | 29 |
| Asymptotic Safety | — | 26 |
| Causal Dynamical Triangulations | — | 23 |
| Horava-Lifshitz Gravity | — | 23 |
| String Theory | — | 23 |
| Noncommutative Geometry | — | 19 |
| Emergent Gravity / Holographic | — | 11 |
| Causal Sets | — | 8 |

## Results Summary

| Status | Count | Example |
|--------|-------|---------|
| Verified (by system) | 4 | η = 2(z-1) connecting asymptotic safety and Horava-Lifshitz |
| Known (rediscovered) | 1 | Bekenstein-Hawking entropy universality |
| Disproved (by system) | 4 | Universal 1/r³ correction structure (counterexample found) |
| Inconclusive | 8 | Universal RG flow structure |

**After expert review: 0 out of 4 "verified" conjectures were correct and publishable.** See detailed analysis below.

## Expert Assessment of "Verified" Conjectures

An honest evaluation of each conjecture the system marked as verified:

### Conjecture 1: η = 2(z-1)
**Claimed:** Anomalous dimension in asymptotic safety equals twice the Lifshitz exponent deviation.

**Assessment:** Algebra error. The correct derivation gives η = 3(z-1)/z, not η = 2(z-1). For z=3 the conjecture says η=4, but the actual answer is η=2. Even the correct version is a one-liner that everyone already knows implicitly. The d_s → 2 universality has been discussed since 2009 by Carlip, Calcagni, Eichhorn, and others.

| Novel? | Correct? | Publishable? |
|--------|----------|-------------|
| No | Algebra wrong | No |

### Conjecture 2: Spectral Dimension Equivalence (Causal Sets ↔ Emergent Gravity)
**Claimed:** Spectral dimension measured through diffusion in emergent gravity equals topological dimension when causal sets achieve optimal dimensional structure.

**Assessment:** The Gamma function formula is textbook causal set theory from 1978. The causal set spectral dimension part is essentially tautological (if a causal set embeds in d dimensions, you recover d). The emergent gravity connection IS genuinely novel — nobody has published it — but it's completely unsupported. There's no mechanism, no derivation, just two things placed next to each other.

| Novel? | Correct? | Publishable? |
|--------|----------|-------------|
| Partially | Tautological + unsupported | No |

### Conjecture 3: Universal Log Correction N/6 = 3/2
**Claimed:** LQG's -3/2 log coefficient matches asymptotic safety's N/6 when N=9 matter fields.

**Assessment:** The LQG side (-3/2 coefficient) is real. The asymptotic safety side (N/6 coefficient) doesn't exist. The LLM fabricated it. No paper in asymptotic safety produces a log correction of the form N/6. The system equated a real number with a hallucinated one.

| Novel? | Correct? | Publishable? |
|--------|----------|-------------|
| Vacuously (premise fabricated) | LLM hallucination | No |

### Conjecture 4: Universal Polynomial Dispersion Relations
**Claimed:** All quantum gravity theories with a fundamental length scale produce polynomial corrections to E² = p².

**Assessment:** This is known lore stated less accurately than existing papers. Experts already say "common feature" not "all" because there are counterexamples (causal sets preserve Lorentz invariance). The polynomial restriction is also wrong — LQG gives sin(p/κ) corrections, not polynomial.

| Novel? | Correct? | Publishable? |
|--------|----------|-------------|
| No (less accurate than existing work) | Over-stated | No |

## Lessons Learned

1. **The LLM hallucinates formulas.** Conjecture 3 equated a real coefficient with a fabricated one. The verification engine couldn't catch this because it doesn't know what's in the actual papers.

2. **Sympy verification is essential.** Conjecture 1 has an algebra error that sympy would have caught. We've since added sympy-verified conjecture generation (LLM writes code, sympy executes it, only confirmed relationships become conjectures).

3. **"Verified" ≠ "correct."** The verification engine checks dimensional consistency and novelty via LLM — neither catches algebra errors or fabricated premises. True verification requires either sympy proof or expert review.

4. **The pipeline works as engineering.** It successfully ingested papers, extracted formulas, found cross-theory matches, and generated conjectures. The failure mode is conjecture quality, not pipeline mechanics.

5. **Domain expertise is irreplaceable.** Every conjecture that looked promising to the system was immediately identified as trivial, wrong, or fabricated by an expert. The system is a tool for experts, not a replacement for them.

## What This Means for the Project

The system is a **proof of concept** that demonstrates:
- Automated cross-theory comparison is feasible
- Formula extraction from physics papers works
- The comparison engine finds real structural matches
- Conjecture generation needs fundamental improvement (sympy-verified approach now implemented)

The system is NOT yet capable of:
- Independent discovery
- Replacing expert judgment
- Publishing without thorough human review

## Next Steps

See [ROADMAP.md](../ROADMAP.md) for the full plan. Key priorities:
1. Sympy-verified conjecture generation (implemented, needs testing)
2. Scale to 2000+ papers for richer formula base
3. Semantic Scholar API for real novelty checking
4. Expert-in-the-loop validation workflow
