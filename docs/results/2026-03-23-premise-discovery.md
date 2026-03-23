# Premise Discovery Run — March 23, 2026

## Run Parameters
- **Date:** March 23, 2026
- **Papers:** 76 across 8 quantum gravity theories
- **Assumptions extracted:** 876 (from ~40 papers, ~50% success rate via Claude Code CLI)
- **Contradictions found:** 91 (across 28 theory pairs)
- **Convergent results:** 9 (all premise-independent)
- **Shared assumptions:** 6 (across 6+ theories), 4 droppable candidates
- **Obstacles cataloged:** 226 (212 marked universal)
- **Premise shifts generated:** 39 (12 new + 27 from prior run)
- **Top score:** 0.653
- **LLM backends:** Gemini 2.5 Flash (extraction), Claude Code CLI (reframing)
- **API cost:** ~$0 (Gemini free tier + Claude subscription)

## Summary Statistics

| Phase | Count |
|-------|-------|
| Assumptions extracted | 876 |
| Contradictions | 91 |
| Convergent results | 9 |
| Shared assumptions (6+ theories) | 6 |
| Droppable candidates | 4 |
| Obstacles | 226 |
| Universal obstacles | 212 |
| Premise shifts | 39 |
| Shifts scoring > 0.5 | 39 |
| Shifts scoring > 0.6 | 10 |

## Top 10 Premise Shifts (Ranked)

### 1. Dimension-Causality Duality (score: 0.65, type: unification)
**Current premise:** Spacetime has a fixed number of dimensions (typically 4), and causal structure emerges from the metric tensor as a derived property.

**Proposed shift:** Effective spacetime dimensionality and causal connectivity are dual descriptions of the same underlying degree of freedom. More causal connections = higher effective dimension. The 'dimension-causality duality' makes both concepts emergent from a network geometry.

**Historical analog:** AdS/CFT — gravity in the bulk and gauge theory on the boundary appeared completely different until Maldacena showed they're equivalent.

### 2. Scale-Dependent Ontology (score: 0.65, type: contradiction_embrace)
**Current premise:** Spacetime has a fixed ontological status — either fundamental or emergent — invariant across all energy scales.

**Proposed shift:** Fundamentality and emergence are scale-dependent quantum properties. Spacetime transitions between ontological states: fundamental-continuum at macroscopic scales, emergent-discrete at Planck scales, pure information at trans-Planckian scales.

**Historical analog:** QM resolving wave-particle duality by making the distinction observer-dependent.

### 3. Irreducible Theoretical Duality (score: 0.65, type: contradiction_embrace)
**Current premise:** Physical theories must have a single mathematical foundation — fundamental degrees of freedom are either continuous or discrete, but not both.

**Proposed shift:** Quantum gravity requires irreducible duality — discrete and continuous descriptions are equally valid and necessary. No single framework captures the complete description.

**Historical analog:** Bohr's complementarity principle.

### 4. Discrete-Continuous Complementarity (score: 0.65, type: unification)
**Current premise:** Discrete and continuous descriptions of spacetime are fundamentally incompatible.

**Proposed shift:** 'Discrete' and 'continuous' are measurement-dependent manifestations of the same geometric entity, related by quantum superposition at the Planck scale.

**Historical analog:** Wave-particle duality — Einstein's photoelectric effect and de Broglie's matter waves.

### 5. Gravity IS Entanglement (score: 0.64, type: unification)
**Current premise:** Gravity is a fundamental geometric force; quantum entanglement is an information-theoretic phenomenon.

**Proposed shift:** The Einstein field equations are the macroscopic encoding of entanglement entropy dynamics. Spacetime geometry is the emergent description of underlying quantum information networks.

**Historical analog:** Maxwell's unification of electricity and magnetism.

### 6. 2D is Fundamental (score: 0.64, type: obstacle_inversion)
**Current premise:** UV dimensional reduction to d=2 is a pathological artifact indicating theoretical breakdown.

**Proposed shift:** Two dimensions IS the fundamental dimensionality of reality. Higher dimensions are emergent holographic projections. The 'pathological' reduction reveals the true fundamental structure.

**Historical analog:** Perelman classifying Ricci flow singularities instead of avoiding them — the 'pathology' became the key to the proof.

### 7. Theory Space Holography (score: 0.63, type: obstacle_inversion)
**Current premise:** The proliferation of incompatible approaches represents theoretical confusion to be resolved.

**Proposed shift:** Each approach is a holographic projection of a higher-dimensional theoretical structure. Like a 3D object casting different 2D shadows, the fundamental structure casts different theoretical 'shadows' depending on which degrees of freedom we manifest.

**Historical analog:** Schrödinger, Heisenberg, and Feynman formulations — initially competing, recognized as equivalent.

### 8. Observer-Dependent Spacetime (score: 0.62, type: contradiction_embrace)
**Current premise:** Spacetime has definite, observer-independent ontological status.

**Proposed shift:** Spacetime exists in quantum superposition of discrete/continuous states until probed. The measurement apparatus determines which aspect becomes definite.

**Historical analog:** Wave-particle duality in QM.

### 9. Universal Dimensional Flow (score: 0.62, type: unification)
**Current premise:** UV dimensional reduction, holographic duality, and anomalous scaling are separate phenomena.

**Proposed shift:** All QG theories exhibit a universal dimensional flow D(E) — UV reduction to d=2, IR emergence of d=4, and holographic duality are different manifestations of the same flow.

**Historical analog:** Wilson's RG unifying critical phenomena — different phase transitions follow universal scaling laws.

### 10. Computational Substrate (score: 0.61, type: contradiction_embrace)
**Current premise:** Spacetime provides the basic ontological arena for all physical processes.

**Proposed shift:** Physical reality is fundamentally algorithmic/informational. 'Spacetime' (discrete or continuous) emerges from underlying quantum computation. The metric tensor, causal sets, and holographic boundaries are different 'user interfaces' to the same process.

**Historical analog:** Statistical mechanics revealing thermodynamics as emergent from microscopic dynamics.

## Expert Assessment Needed

These premise shifts are AI-generated research directions, not results. Key questions for physicists:

1. **#1 (Dimension-Causality Duality):** Has anyone formalized a precise relationship between causal graph connectivity and spectral dimension? This seems testable in CDT simulations.

2. **#5 (Gravity = Entanglement):** This is essentially the ER=EPR conjecture (Maldacena & Susskind 2013). Not novel, but the system found it independently from the data.

3. **#6 (2D is Fundamental):** This is close to 't Hooft's idea and Carlip's arguments. The system correctly identified it as an obstacle inversion. How novel is the specific framing?

4. **#9 (Universal Dimensional Flow):** Is there a master function D(E) that all approaches share? This seems like a concrete, testable prediction.

## What Worked vs Previous Runs

| Metric | Formula Matching (Run 1-2) | Premise Discovery (This Run) |
|--------|---------------------------|------------------------------|
| Output type | Specific formulas (often wrong) | Research directions (qualitative) |
| Hallucination risk | High (fabricated coefficients) | Low (no specific math claimed) |
| Novelty | 0/4 genuinely novel | TBD — needs expert review |
| Actionability | "Here's an equation" (usually wrong) | "Here's a question to investigate" (usually reasonable) |
| Value to physicist | Low without verification | Medium — saves literature review time |

## Next Steps
- Get physicist review of top 5 shifts
- Run `aisaac --premise-report --problem "spectral dimension universality"` for focused analysis
- Scale to 500 papers and re-run to see if shifts change or stabilize
