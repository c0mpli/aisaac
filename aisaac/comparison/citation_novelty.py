"""
Citation-aware novelty detection.

The key insight: two papers from different theories that compute
the same quantity but DON'T cite each other = potentially novel connection.
Two papers that DO cite each other = already known, skip it.

Uses Semantic Scholar API (free, no key) to build citation graphs.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

import requests

from ..knowledge.base import KnowledgeBase

log = logging.getLogger(__name__)

S2_API = "https://api.semanticscholar.org/graph/v1"
RATE_DELAY = 3.0  # seconds between requests


@dataclass
class CitationLink:
    paper_a_arxiv: str
    paper_b_arxiv: str
    a_cites_b: bool
    b_cites_a: bool

    @property
    def connected(self) -> bool:
        return self.a_cites_b or self.b_cites_a


@dataclass
class NovelMatch:
    """A formula match between papers that don't cite each other."""
    formula_a: dict
    formula_b: dict
    theory_a: str
    theory_b: str
    quantity_type: str
    match_score: float
    citation_link: CitationLink
    novelty_reason: str


def build_citation_index(kb: KnowledgeBase) -> dict[str, set[str]]:
    """
    Build a citation index: arxiv_id → set of arxiv_ids it cites.
    Uses Semantic Scholar API.
    """
    papers = kb.conn.execute("SELECT arxiv_id FROM papers").fetchall()
    arxiv_ids = [p["arxiv_id"] for p in papers]

    cites = {}  # arxiv_id → set of cited arxiv_ids
    total = len(arxiv_ids)

    for i, aid in enumerate(arxiv_ids):
        if aid in cites:
            continue

        refs = _get_references(aid)
        if refs is not None:
            cites[aid] = refs
            log.info(f"  [{i+1}/{total}] {aid}: {len(refs)} references")
        else:
            cites[aid] = set()
            log.debug(f"  [{i+1}/{total}] {aid}: API unavailable")

        time.sleep(RATE_DELAY)

    return cites


def check_citation_link(
    cites: dict[str, set[str]],
    arxiv_a: str,
    arxiv_b: str,
) -> CitationLink:
    """Check if two papers cite each other."""
    a_refs = cites.get(arxiv_a, set())
    b_refs = cites.get(arxiv_b, set())

    return CitationLink(
        paper_a_arxiv=arxiv_a,
        paper_b_arxiv=arxiv_b,
        a_cites_b=arxiv_b in a_refs or _normalize_id(arxiv_b) in {_normalize_id(r) for r in a_refs},
        b_cites_a=arxiv_a in b_refs or _normalize_id(arxiv_a) in {_normalize_id(r) for r in b_refs},
    )


def find_novel_matches(
    kb: KnowledgeBase,
    comparison_results: list,
    cites: dict[str, set[str]],
) -> list[NovelMatch]:
    """
    Find formula matches where the source papers don't cite each other.
    These are the gold: same physics, no awareness of each other.
    """
    formulas_cache = {f["id"]: f for f in kb.get_all_formulas()}
    papers_cache = {}
    for row in kb.conn.execute("SELECT id, arxiv_id FROM papers").fetchall():
        papers_cache[row["id"]] = row["arxiv_id"]

    novel = []
    seen = set()

    for r in comparison_results:
        fa = formulas_cache.get(r.formula_a_id, {})
        fb = formulas_cache.get(r.formula_b_id, {})

        if not fa or not fb:
            continue

        # Skip same-theory matches
        if fa.get("theory_slug") == fb.get("theory_slug"):
            continue

        arxiv_a = papers_cache.get(fa.get("paper_id"))
        arxiv_b = papers_cache.get(fb.get("paper_id"))

        if not arxiv_a or not arxiv_b:
            continue

        # Skip duplicates
        pair_key = tuple(sorted([arxiv_a, arxiv_b]))
        if pair_key in seen:
            continue
        seen.add(pair_key)

        link = check_citation_link(cites, arxiv_a, arxiv_b)

        if not link.connected:
            novel.append(NovelMatch(
                formula_a=fa,
                formula_b=fb,
                theory_a=fa.get("theory_slug", ""),
                theory_b=fb.get("theory_slug", ""),
                quantity_type=fa.get("quantity_type", ""),
                match_score=r.combined_score,
                citation_link=link,
                novelty_reason=f"Papers {arxiv_a} and {arxiv_b} compute similar {fa.get('quantity_type', '')} "
                               f"but do not cite each other",
            ))

    # Sort by match score (highest first)
    novel.sort(key=lambda x: x.match_score, reverse=True)
    return novel


def _get_references(arxiv_id: str) -> set[str] | None:
    """Get list of papers cited by this paper via Semantic Scholar."""
    s2_id = f"ArXiv:{_normalize_id(arxiv_id)}"

    try:
        resp = requests.get(
            f"{S2_API}/paper/{s2_id}/references",
            params={"fields": "externalIds", "limit": 500},
            timeout=10,
        )

        if resp.status_code == 429:
            time.sleep(10)
            resp = requests.get(
                f"{S2_API}/paper/{s2_id}/references",
                params={"fields": "externalIds", "limit": 500},
                timeout=10,
            )

        if resp.status_code != 200:
            return None

        data = resp.json()
        refs = set()
        for item in data.get("data", []):
            cited = item.get("citedPaper", {})
            ext_ids = cited.get("externalIds") or {}
            if ext_ids.get("ArXiv"):
                refs.add(ext_ids["ArXiv"])
        return refs

    except Exception as e:
        log.debug(f"Failed to get references for {arxiv_id}: {e}")
        return None


def _normalize_id(arxiv_id: str) -> str:
    """Normalize arxiv ID format (remove version, handle old/new format)."""
    aid = arxiv_id.strip()
    # Remove version suffix
    if "v" in aid.split("/")[-1]:
        aid = aid.rsplit("v", 1)[0]
    return aid
