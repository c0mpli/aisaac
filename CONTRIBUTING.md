# Contributing to AIsaac

## Adding a New Scientific Domain

AIsaac works on any field with competing theoretical frameworks. Here's how to add yours:

### Step 1: Define your theories

Create a file like `examples/domains/your_field.py` with:

```python
DOMAIN = {
    "name": "Your Field",
    "theories": [
        {
            "name": "Theory A",
            "slug": "theory_a",
            "key_object": "what this theory is built on",
            "arxiv_categories": ["cond-mat.str-el"],
            "search_queries": ["search terms for arXiv"],
            "seed_papers": ["arXiv IDs of key papers"],
            "key_parameters": ["coupling constants, etc."],
        },
        # ... more theories
    ],
    "comparable_quantities": [
        {
            "slug": "observable_name",
            "name": "Human Readable Name",
            "description": "What this quantity measures",
            "keywords": ["terms that identify this quantity in papers"],
        },
        # ... more quantities
    ],
}
```

### Step 2: Update pipeline/config.py

Convert your domain definition into `TheoryDef` entries in the `THEORIES` list. Update the `QuantityType` enum to include your comparable quantities.

### Step 3: Update the extraction prompt

In `ingestion/extractor.py`, update the `quantity_type` list in `EXTRACTION_PROMPT` to include your domain's quantity types with keyword descriptions.

### Step 4: Add known connections (optional but recommended)

In `knowledge/known_connections.py`, add `KnownConnection` entries for results that are already established in your field. The system should rediscover these — if it doesn't, something is wrong.

### Step 5: Add seed formulas to the demo (optional)

In `demo.py`, add manually curated seed formulas from your domain to validate the comparison engine offline before hitting the API.

### Step 6: Run

```bash
uv run aisaac --tier 1
```

---

## Adding a New Comparison Level

The comparison engine in `comparison/engine.py` has multiple matchers. To add a new one:

1. Create a class with a `compare(expr_a, expr_b) -> (score, details)` method
2. Register it in `ComparisonEngine.__init__`
3. Add its score to the `combined_score` calculation

---

## Improving Formula Extraction

The LLM extraction quality determines everything downstream. Key files:

- `ingestion/extractor.py` — the extraction and normalization prompts
- `ingestion/latex_parser.py` — pre-parsing LaTeX to feed the LLM structured input
- `knowledge/normalizer.py` — notation standardization rules

To improve extraction:
- Add more examples to the extraction prompt for your domain
- Add domain-specific notation aliases to `normalizer.py`
- Test on 10 papers manually before scaling up

---

## Code Style

```bash
pip install black ruff
black aisaac/
ruff check aisaac/ --fix
```

---

## Pull Request Process

1. Fork the repo
2. Create a feature branch
3. Make your changes
4. Run the offline demo: `uv run python -m aisaac.demo`
5. Submit a PR with a description of what you changed and why
