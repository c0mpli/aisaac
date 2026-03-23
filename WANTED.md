# What This Project Needs

## A physicist willing to verify ~50 numbers

The system reads papers, extracts formulas, maps the landscape across 8 quantum gravity approaches, and runs symbolic regression to find cross-theory patterns. Everything works except the last mile: **the extracted numerical values need verification against original publications.**

LLMs get numbers wrong. Our database says CDT predicts d_s = 1.5 (from a fit formula) when the actual Monte Carlo result is 1.80 ± 0.25. It says NCG predicts d_s = 3 (from one specific κ-Minkowski model) when the standard Connes NCG result is d_s = 2. Every downstream analysis inherits these errors.

## What needs checking

~50 numerical predictions across 8 theories for these quantities:

### Spectral dimension (UV value)
| Theory | Our DB says | Needs verification |
|--------|------------|-------------------|
| CDT | 1.5 (from fit) | Ambjorn-Jurkiewicz-Loll 2005: 1.80 ± 0.25? |
| Asymptotic Safety | 2.0 | Lauscher-Reuter 2005: exact 2? |
| Horava-Lifshitz | 2.0 (z=3) | Horava 2009: exact for z=3? |
| NCG | 3.0 (κ-Minkowski) | Is this the standard result or one model? Connes gives 2? |
| Causal Sets | ~2 | Eichhorn-Mizera 2014? Carlip estimate? |
| LQG | ~2 | Modesto 2009? Which calculation? |

### BH entropy log correction coefficient
| Theory | Our DB says | Needs verification |
|--------|------------|-------------------|
| LQG | -3/2 | Kaul-Majumdar 2000: -3/2? Or Ghosh-Mitra: -1/2? |
| LQG (alt) | -2 | Which calculation? |
| Asymptotic Safety | -2 | Which paper? |
| String Theory | -1/2 | Sen's entropy function? For which BH? |

### Newton correction coefficient
| Theory | Our DB says | Needs verification |
|--------|------------|-------------------|
| Donoghue | 41/(10π) | Donoghue 1994: confirmed? |
| String theory | ? | What's the string theory prediction? |

### Dispersion relation modifications
| Theory | Our DB says | Needs verification |
|--------|------------|-------------------|
| Horava-Lifshitz | ω² ~ k⁶ | For z=3, correct? |
| LQG | polymer quantization | What's the specific numerical prediction? |
| NCG (κ-Minkowski) | sinh(p/κ) | Exact form? |

### Running gravitational coupling
| Theory | Our DB says | Needs verification |
|--------|------------|-------------------|
| Asymptotic Safety | g*λ* ≈ 0.12-0.14 | Reuter-Saueressig: scheme-dependent? |
| AS anomalous dimension | η_N = 2 | At the fixed point, exact? |

## Why this matters

With verified data, we can run symbolic regression (PySR) across theories. Planck found E=hf by fitting a function to blackbody data. We want to fit a function to the "data" of 8 theories' predictions. If a single function fits all theories' spectral dimension values, that function might encode structure that no individual theory contains.

Our first (unverified) PySR run found: **d_s ≈ 6 / (2 + preserves_lorentz + has_foliation)**. This fits the data perfectly but uses wrong input values. With correct numbers, the formula will be different — and potentially meaningful.

## What "a weekend" looks like

1. Pick a quantity (e.g., spectral dimension)
2. For each of the 6-8 theories that predict it, find THE standard paper
3. Write down the exact numerical value, uncertainty, and conditions
4. Note which approximations were used and what regime it's valid in
5. Flag cases where different calculations within the same theory disagree

That's ~3 hours per quantity, ~6-8 quantities, ~20-25 hours total.

## What you get

- Co-authorship on any paper that comes from the verified PySR results
- A complete tool for mapping cross-theory predictions in your field
- The satisfaction of potentially finding a mathematical pattern that nobody noticed because the numbers lived in different papers with different notation

## Contact

Open an issue on this repo or email [your contact].

## The system is ready. It just needs an astronomer to point the telescope.
