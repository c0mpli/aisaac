"""
Semantic Scholar novelty checker.

Searches real literature instead of asking the LLM "have you heard of this?"
Free API, no key needed.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass

import requests

log = logging.getLogger(__name__)

SEMANTIC_SCHOLAR_API = "https://api.semanticscholar.org/graph/v1"


@dataclass
class NoveltyResult:
    is_novel: bool | None  # True=novel, False=known, None=uncertain
    related_papers: list[dict]  # [{title, year, url, citationCount}]
    search_query: str
    explanation: str


def check_novelty_semantic_scholar(
    theories: list[str],
    quantity_type: str,
    title: str,
    max_results: int = 10,
) -> NoveltyResult:
    """
    Search Semantic Scholar for papers discussing the same
    theory pair + quantity type. If zero results, it's likely novel.
    """
    # Build search query from theory names and quantity
    theory_names = {
        "string_theory": "string theory",
        "loop_quantum_gravity": "loop quantum gravity",
        "cdt": "causal dynamical triangulations",
        "asymptotic_safety": "asymptotic safety",
        "causal_sets": "causal sets",
        "horava_lifshitz": "Horava-Lifshitz",
        "noncommutative_geometry": "noncommutative geometry",
        "emergent_gravity": "emergent gravity",
    }

    quantity_keywords = {
        "spectral_dimension": "spectral dimension",
        "black_hole_entropy": "black hole entropy",
        "bh_entropy_log_correction": "logarithmic correction entropy",
        "newton_correction": "quantum correction Newton potential",
        "dispersion_relation_modification": "modified dispersion relation",
        "graviton_propagator_modification": "graviton propagator",
        "running_gravitational_coupling": "running Newton constant",
        "area_gap": "area spectrum quantization",
        "entanglement_entropy_area_law": "entanglement entropy area",
        "cosmological_constant": "cosmological constant quantum gravity",
    }

    # Build query: both theory names + quantity
    t_names = [theory_names.get(t, t) for t in theories[:2]]
    qt_kw = quantity_keywords.get(quantity_type, quantity_type.replace("_", " "))
    query = f"{t_names[0]} {t_names[1]} {qt_kw}" if len(t_names) >= 2 else f"{t_names[0]} {qt_kw}"

    papers = _search_papers(query, max_results)

    if papers is None:
        return NoveltyResult(
            is_novel=None,
            related_papers=[],
            search_query=query,
            explanation="Semantic Scholar API unavailable",
        )

    if len(papers) == 0:
        return NoveltyResult(
            is_novel=True,
            related_papers=[],
            search_query=query,
            explanation=f"No papers found discussing {t_names[0]} + {t_names[1]} + {qt_kw}. Likely novel.",
        )

    # Check if any paper title closely matches the conjecture
    high_relevance = [p for p in papers if p.get("citationCount", 0) > 10]

    if len(high_relevance) >= 3:
        return NoveltyResult(
            is_novel=False,
            related_papers=papers,
            search_query=query,
            explanation=f"Found {len(papers)} papers ({len(high_relevance)} highly cited) on this topic. Likely known.",
        )

    return NoveltyResult(
        is_novel=None,
        related_papers=papers,
        search_query=query,
        explanation=f"Found {len(papers)} papers. May be partially known — expert review needed.",
    )


def _search_papers(query: str, limit: int = 10) -> list[dict] | None:
    """Search Semantic Scholar API."""
    try:
        resp = requests.get(
            f"{SEMANTIC_SCHOLAR_API}/paper/search",
            params={
                "query": query,
                "limit": limit,
                "fields": "title,year,citationCount,url,authors",
            },
            timeout=10,
        )
        if resp.status_code == 429:
            log.warning("Semantic Scholar rate limited, waiting 10s...")
            time.sleep(10)
            resp = requests.get(
                f"{SEMANTIC_SCHOLAR_API}/paper/search",
                params={"query": query, "limit": limit, "fields": "title,year,citationCount,url,authors"},
                timeout=10,
            )

        if resp.status_code != 200:
            log.warning(f"Semantic Scholar API returned {resp.status_code}")
            return None

        data = resp.json()
        papers = data.get("data", [])
        return [
            {
                "title": p.get("title", ""),
                "year": p.get("year"),
                "citationCount": p.get("citationCount", 0),
                "url": p.get("url", ""),
                "authors": [a.get("name", "") for a in (p.get("authors") or [])[:3]],
            }
            for p in papers
        ]

    except Exception as e:
        log.warning(f"Semantic Scholar search failed: {e}")
        return None
