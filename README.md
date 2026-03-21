# AIsaac

**AI that reads an entire scientific field and finds connections humans miss.**

Point it at any domain with competing theoretical frameworks — quantum gravity, turbulence modeling, condensed matter, pharmacology, climate models — and it reads the papers, extracts mathematical predictions, compares across approaches, and surfaces connections buried in notation differences across thousands of papers.

No single researcher can hold 50,000 papers in their head. AIsaac can.

---

## What It Does

```
Papers (arXiv) ──→ Extract formulas ──→ Normalize notation ──→ Compare across theories
                        (LLM)              (sympy + LLM)          (6 levels)
                                                                      │
                    ┌─────────────────────────────────────────────────┘
                    │
                    ▼
              ML clustering ──→ Generate conjectures ──→ Verify ──→ Report
            (embed + HDBSCAN)        (LLM)           (algebra +     (LaTeX
                                                      numerical +    paper
                                                      dimensional)   draft)
```

**Input:** A scientific field defined by its competing theories, seed papers, and comparable quantities.

**Output:** Ranked conjectures about cross-theory connections, with verification status and evidence chains back to specific papers and formulas.

---

## Run Results

See [docs/results/](docs/results/) for detailed run reports with expert assessments.

---

## Quick Start

### 1. Install

```bash
git clone https://github.com/c0mpli/aisaac.git
cd aisaac
uv venv --python 3.11
source .venv/bin/activate
uv pip install -e .
```

### 2. Run the offline demo (no API needed)

```bash
uv run python -m aisaac.demo
```

This validates the full pipeline on manually seeded formulas — comparison engine, clustering, symmetry analysis, anomaly detection — all without touching arXiv or any LLM API.

### 3. Run the full pipeline

Pick one backend:

```bash
# Option A: Anthropic API (pay-per-token, ~$3-5 for Tier 1)
export ANTHROPIC_API_KEY=sk-ant-...
uv run aisaac --tier 1

# Option B: Claude Code CLI (uses your Pro/Max subscription, no extra cost)
# Install: npm i -g @anthropic-ai/claude-code && claude login
uv run aisaac --tier 1

# Option C: Any OpenAI-compatible proxy
export AISAAC_PROXY_URL=http://localhost:8317/v1
uv run aisaac --tier 1
```

### 4. Check results

```bash
uv run aisaac --status          # DB summary
uv run aisaac --conjectures     # List all conjectures with status
uv run aisaac --compare-only    # Re-run analysis on existing data (cheap)
```

Output files in `data/`:
- `report.md` — full ranked conjecture list
- `paper_draft.tex` — draft paper sections
- `formula_space.png` — UMAP visualization of formula embeddings
- `theory_connections.png` — cross-theory connection graph

---

## How to Add Your Own Domain

AIsaac is domain-agnostic. Quantum gravity is just the demo. To use it on your field:

### 1. Define your theories in `pipeline/config.py`

Each theory needs: name, slug, arXiv categories, search queries, seed paper IDs, key parameters.

### 2. Define comparable quantities

What predictions do your theories make about the same thing? In QG it's spectral dimension, black hole entropy, Newton corrections. In turbulence it might be Reynolds stress, dissipation rate, wall functions.

### 3. Update the extraction prompt

Tell the LLM what formula types to look for in your domain. See `ingestion/extractor.py`.

### 4. Add known connections for validation

What results are already established? The system should rediscover these. If it doesn't, the pipeline has a bug.

See `examples/domains/` for templates:
- `quantum_gravity.py` — full working example
- `turbulence.py` — skeleton for CFD turbulence models
- `condensed_matter.py` — skeleton for strongly correlated electrons

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full step-by-step guide.

---

## Architecture

```
aisaac/
├── ingestion/          # Paper reading and formula extraction
│   ├── crawler.py      # arXiv bulk download (tiered: 200 → 2K → 10K papers)
│   ├── extractor.py    # LLM-powered formula extraction + classification
│   ├── latex_parser.py # Pre-parse LaTeX equations for structured LLM input
│   ├── deduplicator.py # Same formula in different papers = one entry
│   └── citation_graph.py
│
├── knowledge/          # Structured knowledge base
│   ├── base.py         # SQLite storage: papers, formulas, predictions, conjectures
│   ├── normalizer.py   # Translate all notation to common symbols (κ²/16π → G)
│   └── known_connections.py  # Ground truth for validation
│
├── comparison/         # Multi-level comparison engine
│   ├── engine.py       # Structural, dimensional, numerical, limit matching
│   └── symmetry.py     # Compare symmetry structures across theories
│
├── ml/                 # Pattern detection
│   ├── patterns.py     # Formula embeddings, HDBSCAN clustering, anomaly detection
│   └── semantic.py     # Sentence-transformer semantic matching
│
├── conjecture/         # Hypothesis generation
│   └── generator.py    # LLM proposes connections from comparison evidence
│
├── verification/       # Verify proposed conjectures
│   └── engine.py       # Algebraic (sympy), numerical, dimensional, counterexample, novelty
│
├── pipeline/           # Orchestration
│   ├── aisaac.py       # Main pipeline controller (10-phase, resumable)
│   ├── config.py       # Domain configuration (theories, quantities, settings)
│   ├── llm_client.py   # 3-backend LLM client with retry + caching
│   └── state.py        # Crash-safe checkpoint system
│
└── output/
    ├── paper_writer.py     # Generate LaTeX paper draft
    └── visualizations.py   # UMAP plots, theory connection graphs
```

---

## What to Expect

**The system reliably finds known connections.** If two theories in your field agree on a prediction, AIsaac will surface it. This validates that the pipeline works.

**Novel discoveries depend on the domain.** The system finds patterns in notation and structure. Whether those patterns represent deep physics or superficial coincidences requires domain expertise to judge.

**The tool itself is the contribution.** No single researcher reads all approaches to a problem deeply. AIsaac does. Even if every conjecture turns out to be known, the systematic cross-comparison has value.

**Typical costs:**
- Tier 1 (reviews, ~50-80 papers): $3-5 with Sonnet API, or free with Claude Code CLI
- Tier 2 (high-impact, ~2000 papers): $50-100
- Tier 3 (recent frontier, ~10K papers): $200-500

---

## CLI Reference

```
aisaac --tier 1              # Full pipeline on review papers
aisaac --tier 2              # Scale up to high-impact papers
aisaac --compare-only        # Re-run analysis on existing DB (no extraction cost)
aisaac --status              # Show pipeline state and DB summary
aisaac --conjectures         # List all conjectures with status
aisaac --validate            # Check recall against known connections
aisaac --investigate 3       # Deep-dive into conjecture #3
aisaac --reset               # Reset pipeline state for fresh run
```

---

## License

MIT. See [LICENSE](LICENSE).

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). The most valuable contribution is adding a new scientific domain — pick a field you know, define the theories and comparable quantities, and run it.
