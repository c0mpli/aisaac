# AIsaac Roadmap

## Current State (v0.2 — March 2026)

### Core Pipeline
- 76 papers ingested, 162 formulas extracted across 8 QG theories
- 17 conjectures generated, 4 verified, 1 known rediscovered, 4 disproved
- 11/14 known connections recalled (79%)
- Full pipeline: ingest → extract → compare → cluster → conjecture → verify → report

### Premise Discovery Engine (NEW)
- 876 assumptions extracted from 76 papers
- 91 contradictions found across 28 theory pairs
- 9 convergent results (all premise-independent)
- 39 ranked premise shifts from 5 breakthrough patterns
- 226 obstacles cataloged (212 universal)

### Breakthrough Pattern Matcher (NEW)
- 35 historical breakthroughs dataset (labeled symptoms → fix)
- 9 symptom types detected in current QG field (66 total symptoms)
- RandomForest pattern matching against historical paradigm shifts

### Symbolic Regression (NEW)
- PySR on hand-verified spectral dimension data (5 theories)
- Best formula: d_s = |1.6 - lorentz - foliation| + 1.4
- Emergent gravity prediction: d_s = 2.0
- Honest: 5 data points, overfitting guaranteed

### Multi-Backend LLM Routing (NEW)
- 5 backends: Anthropic, Gemini, OpenAI, Claude Code CLI, proxy
- Agent-specific routing (Gemini Flash for extraction, Pro for reasoning, GPT for creativity)

### Key Finding
All 8 QG theories assume continuous spacetime (876 assumptions, keyword analysis). Even "discrete" theories (LQG, causal sets) use continuous manifold math as scaffolding. This is known to physicists but systematically confirmed from data for the first time.

### Current Bottleneck
LLM-extracted numerical values are unreliable. PySR needs hand-verified numbers from original papers. ~50 values across 6-8 quantities need physicist verification.

---

## Phase 1: Fix What's Broken

### Formula classification
- 113/162 formulas classified as "other" — comparison engine ignores them
- Re-extract with improved prompt (done) but need to validate classification accuracy
- Add a post-extraction reclassification pass: LLM reviews "other" formulas and reassigns

### Known connections validator
- Currently 0/14 recall due to overly strict theory-set matching
- Fix: match on ANY theory overlap + keyword similarity, not full subset

### Verification engine
- Algebraic verifier can't parse most physics LaTeX into sympy
- Add LLM-assisted verification: ask Claude to check the math step-by-step
- Separate "dimensionally consistent" from "algebraically proven"

---

## Phase 2: Scale Up Data

### More papers (target: 2000+)
- Run Tier 2 ingestion (high-impact papers per approach)
- Add cross-theory review papers (Carlip 2017, Addazi et al 2022)
- Prioritize papers with quantitative predictions over philosophical reviews

### Better formula extraction
- Two-pass extraction: first pass gets all equations, second pass classifies
- Add equation deduplication across papers (same formula cited in 10 papers = 1 entry)
- Extract numerical VALUES not just symbolic forms (e.g., "coefficient = -3/2")

### Semantic Scholar integration (free API, no key)
- Search for papers citing multiple QG approaches
- Get citation counts for priority scoring
- Real literature novelty check for conjectures

---

## Phase 3: Smarter Comparison

### Numerical comparison
- Extract and compare numerical predictions (not just structural similarity)
- Build a table: quantity × theory → numerical value
- Flag disagreements as interesting, not just agreements

### Notation normalization v2
- Current normalizer misses ~40% of aliases
- Build a lookup table from extracted formulas: "these 5 symbols all mean Newton's constant"
- Use dimensional analysis to catch normalization errors

### Cross-theory formula mapping
- When two formulas match structurally, automatically derive the variable mapping
- E.g., "LQG's γ maps to string theory's g_s via γ = f(g_s)"

---

## Phase 4: Better Conjectures

### Conjecture quality
- Current conjectures are often vague ("universal structure exists")
- Force generator to produce testable predictions: "compute X in theory A, it should equal Y"
- Add a "so what?" filter: reject conjectures that are trivially true

### Multi-theory conjectures
- Current system only compares pairs of theories
- Add N-way comparison: "this quantity agrees across 5 theories"
- These universal results are the most interesting findings

### Counterexample-driven refinement
- When a conjecture is disproved, ask: "what's the closest TRUE statement?"
- Near-misses (off by a factor of 2, or holds in a limit) are often more interesting

---

## Phase 5: Real Novelty Checking

### Semantic Scholar API
- For each conjecture, search for papers mentioning both theories + quantity type
- Check if the specific mathematical relation appears in any paper
- Confidence levels: "no results found" vs "similar but not identical" vs "already published"

### arXiv full-text search
- Search arXiv for the specific LaTeX expression
- Check if the conjecture's variable mapping appears anywhere

### Citation graph analysis
- If two papers from different theories cite each other, the connection is likely known
- Novel connections = formulas from papers with zero cross-citations

---

## Phase 6: Production Quality

### Parallel extraction
- Current: sequential (1 paper at a time due to rate limits)
- Use API with batch endpoint or multiple keys for 10x throughput

### Incremental updates
- Don't re-extract everything on each run
- Track which papers have been processed, only extract new ones
- Re-run comparison when new formulas are added

### Web interface
- Browse conjectures, formulas, theory connections
- Interactive formula space visualization (not just static PNG)
- Click a conjecture → see all evidence (papers, formulas, scores)

### Reproducibility
- Pin all extracted formulas to paper+equation number
- Every conjecture traces back to specific formulas from specific papers
- A physicist can check each step of the reasoning chain

---

## Long-term Vision

### 10,000+ papers
- Full Tier 3-4 ingestion
- At this scale, the ML clustering becomes meaningful
- Expect to find connections invisible at 76-paper scale

### Multi-field expansion
- Same architecture works for any field with competing mathematical frameworks
- Candidates: quantum computing error correction, climate models, protein folding approaches

### Physicist-in-the-loop
- System proposes conjectures, physicist validates/rejects
- Rejections become training signal for better conjecture generation
- Build toward a system that only proposes things worth checking
