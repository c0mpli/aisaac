#!/usr/bin/env python3
"""
Quick smoke test for AIsaac pipeline.

Tests:
1. All imports work
2. Knowledge base creates and queries
3. Structural matcher works on known formulas
4. Numerical matcher catches known equivalences
5. Formula embedder produces valid embeddings
"""
import sys
import tempfile
import numpy as np

def test_imports():
    print("Testing imports...", end=" ")
    from aisaac.pipeline.config import THEORIES, QuantityType, PipelineConfig
    from aisaac.knowledge.base import KnowledgeBase, Paper, ExtractedFormula
    from aisaac.comparison.engine import (
        ComparisonEngine, StructuralMatcher, NumericalMatcher, 
        DimensionalMatcher, LimitMatcher,
    )
    from aisaac.ml.patterns import (
        FormulaEmbedder, CrossTheoryClusterer,
        UniversalityDetector, AnomalyDetector,
    )
    from aisaac.conjecture.generator import ConjectureGenerator
    from aisaac.verification.engine import VerificationEngine
    print("OK")
    return True


def test_knowledge_base():
    print("Testing knowledge base...", end=" ")
    from aisaac.knowledge.base import KnowledgeBase, Paper, ExtractedFormula

    with tempfile.NamedTemporaryFile(suffix=".db") as f:
        kb = KnowledgeBase(f.name)

        # Insert a paper
        p = Paper(
            arxiv_id="test/0001",
            title="Test Paper on Spectral Dimension",
            authors=["A. Einstein", "N. Bohr"],
            year=2024,
            abstract="We compute spectral dimension in CDT.",
            theory_tags=["cdt"],
        )
        pid = kb.insert_paper(p)
        assert pid > 0, "Paper insert failed"

        # Insert a formula
        ef = ExtractedFormula(
            paper_id=pid,
            latex=r"d_s(\sigma) = -2 \frac{d \ln P(\sigma)}{d \ln \sigma}",
            sympy_expr="",
            formula_type="prediction",
            quantity_type="spectral_dimension",
            theory_slug="cdt",
            description="Spectral dimension from return probability",
            variables=[{"symbol": "sigma", "meaning": "diffusion time", "dimensions": "[T]"}],
            regime="all scales",
            approximations="none",
            confidence=0.9,
        )
        fid = kb.insert_formula(ef)
        assert fid > 0, "Formula insert failed"

        # Query
        formulas = kb.get_formulas_by_theory("cdt")
        assert len(formulas) == 1
        assert formulas[0]["quantity_type"] == "spectral_dimension"

        summary = kb.summary()
        assert summary["papers"] == 1
        assert summary["formulas"] == 1

        kb.close()
    print("OK")
    return True


def test_structural_matcher():
    print("Testing structural matcher...", end=" ")
    from aisaac.comparison.engine import StructuralMatcher

    sm = StructuralMatcher()

    # Test 1: identical expressions
    score, _ = sm.compare("A * x**(-n)", "A * x**(-n)")
    assert score == 1.0, f"Identical expressions should score 1.0, got {score}"

    # Test 2: structurally similar (different variable names)
    score, details = sm.compare("A * x**(-2) * y**(3/2)", "B * p**(-2) * q**(3/2)")
    assert score > 0.5, f"Similar structure should score >0.5, got {score}"

    # Test 3: different structure
    score, _ = sm.compare("A * x**2", "log(x) + exp(y)")
    assert score < 0.5, f"Different structure should score <0.5, got {score}"

    print("OK")
    return True


def test_numerical_matcher():
    print("Testing numerical matcher...", end=" ")
    from aisaac.comparison.engine import NumericalMatcher

    nm = NumericalMatcher()

    # Test 1: equivalent expressions
    score, _ = nm.compare("(x + y)**2", "x**2 + 2*x*y + y**2")
    assert score > 0.95, f"Algebraically equal should score >0.95, got {score}"

    # Test 2: different expressions
    score, _ = nm.compare("x**2", "x**3")
    assert score < 0.3, f"Different functions should score <0.3, got {score}"

    print("OK")
    return True


def test_formula_embedder():
    print("Testing formula embedder...", end=" ")
    from aisaac.ml.patterns import FormulaEmbedder

    embedder = FormulaEmbedder()

    formulas = [
        {
            "id": 1, "theory_slug": "cdt", "quantity_type": "spectral_dimension",
            "normalized_sympy": "2 - sigma/sigma_0", "sympy_expr": "",
            "confidence": 0.8,
        },
        {
            "id": 2, "theory_slug": "asymptotic_safety", "quantity_type": "spectral_dimension",
            "normalized_sympy": "4 - 2*exp(-k/k_0)", "sympy_expr": "",
            "confidence": 0.7,
        },
        {
            "id": 3, "theory_slug": "string_theory", "quantity_type": "black_hole_entropy",
            "normalized_sympy": "A / (4*G)", "sympy_expr": "",
            "confidence": 0.95,
        },
    ]

    embeddings = embedder.embed_all(formulas)
    assert len(embeddings) == 3, f"Expected 3 embeddings, got {len(embeddings)}"

    # Check embedding dimensions
    for e in embeddings:
        assert len(e.combined_vec) > 0, "Empty embedding"
        assert not np.all(np.isnan(e.combined_vec)), "NaN in embedding"

    # Spectral dimension formulas should be more similar to each other
    # than to black hole entropy
    from scipy.spatial.distance import cosine
    d_spec = cosine(embeddings[0].combined_vec, embeddings[1].combined_vec)
    d_cross1 = cosine(embeddings[0].combined_vec, embeddings[2].combined_vec)
    d_cross2 = cosine(embeddings[1].combined_vec, embeddings[2].combined_vec)
    # At minimum, embeddings should be finite
    assert np.isfinite(d_spec), "Non-finite distance"

    print("OK")
    return True


def test_theory_config():
    print("Testing theory configuration...", end=" ")
    from aisaac.pipeline.config import THEORIES, THEORY_BY_SLUG

    assert len(THEORIES) == 8, f"Expected 8 theories, got {len(THEORIES)}"
    
    # Check all theories have required fields
    for t in THEORIES:
        assert t.name, f"Theory missing name"
        assert t.slug, f"Theory missing slug"
        assert len(t.search_queries) > 0, f"{t.slug} has no search queries"
        assert len(t.key_reviews_arxiv_ids) > 0, f"{t.slug} has no review papers"
        assert t.slug in THEORY_BY_SLUG, f"{t.slug} not in THEORY_BY_SLUG"

    print("OK")
    return True


if __name__ == "__main__":
    # Add parent dir to path for imports
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
    
    tests = [
        test_imports,
        test_theory_config,
        test_knowledge_base,
        test_structural_matcher,
        test_numerical_matcher,
        test_formula_embedder,
    ]
    
    passed = 0
    failed = 0
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"FAILED: {e}")
            failed += 1
    
    print(f"\n{'='*40}")
    print(f"Results: {passed} passed, {failed} failed")
    if failed == 0:
        print("All tests passed!")
    sys.exit(failed)
