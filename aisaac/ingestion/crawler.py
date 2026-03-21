"""
arXiv Paper Crawler.

Tiered ingestion strategy:
  Tier 1: ~200 key reviews + foundational papers (manual seeds + review detection)
  Tier 2: ~2000 most-cited per approach
  Tier 3: ~10K recent frontier (2020-2026)
  Tier 4: full corpus (background)

Priority: papers citing MULTIPLE approaches ranked higher (bridge papers).
"""
from __future__ import annotations

import time
import json
import logging
import re
from pathlib import Path
from typing import Iterator, Optional

import arxiv
import requests

from ..pipeline.config import (
    THEORIES, PAPERS_DIR, Tier, TheoryDef,
)
from ..knowledge.base import KnowledgeBase, Paper

log = logging.getLogger(__name__)


class ArxivCrawler:
    """Bulk download and index papers from arXiv."""

    # Rate limit: arXiv API asks for 3s between requests
    RATE_LIMIT_SECONDS = 3.0

    def __init__(self, kb: KnowledgeBase):
        self.kb = kb
        self.client = arxiv.Client(
            page_size=100,
            delay_seconds=self.RATE_LIMIT_SECONDS,
            num_retries=3,
        )

    # ── Tier 1: Seeded Reviews ───────────────────────────────────

    def ingest_tier1(self) -> int:
        """
        Ingest manually curated review/foundational papers.
        These are the most important papers per approach.
        """
        count = 0
        for theory in THEORIES:
            for aid in theory.key_reviews_arxiv_ids:
                paper = self._fetch_paper_by_id(aid, theory, tier=1, is_review=True)
                if paper:
                    self.kb.insert_paper(paper)
                    count += 1
                    log.info(f"[Tier1] {theory.slug}: {paper.title[:60]}...")
        log.info(f"Tier 1 complete: {count} papers ingested")
        return count

    # ── Tier 2: High Impact ──────────────────────────────────────

    def ingest_tier2(self, max_per_theory: int = 250) -> int:
        """Search for high-impact papers per approach."""
        count = 0
        for theory in THEORIES:
            for query_text in theory.search_queries:
                results = self._search(
                    query_text, 
                    categories=theory.arxiv_categories,
                    max_results=max_per_theory,
                    sort_by=arxiv.SortCriterion.Relevance,
                )
                for paper in results:
                    paper.tier = 2
                    self.kb.insert_paper(paper)
                    count += 1
            log.info(f"[Tier2] {theory.slug}: ingested papers")
        log.info(f"Tier 2 complete: {count} papers ingested")
        return count

    # ── Tier 3: Recent Frontier ──────────────────────────────────

    def ingest_tier3(self, start_year: int = 2020, max_per_query: int = 500) -> int:
        """Recent papers that might contain new results."""
        count = 0
        # Cross-theory queries are especially valuable
        cross_queries = [
            "quantum gravity spectral dimension universal",
            "quantum gravity approaches comparison",
            "black hole entropy logarithmic correction quantum gravity",
            "quantum gravity Newton correction leading order",
            "dimensional reduction quantum gravity Planck scale",
            "entanglement entropy area law quantum gravity",
            "modified dispersion relation quantum gravity",
            "quantum gravity phenomenology",
        ]
        all_queries = cross_queries.copy()
        for theory in THEORIES:
            all_queries.extend(theory.search_queries)

        for query_text in all_queries:
            results = self._search(
                query_text,
                max_results=max_per_query,
                sort_by=arxiv.SortCriterion.SubmittedDate,
            )
            for paper in results:
                if paper.year >= start_year:
                    paper.tier = 3
                    self.kb.insert_paper(paper)
                    count += 1
        log.info(f"Tier 3 complete: {count} papers ingested")
        return count

    # ── Bridge Paper Detection ───────────────────────────────────

    def find_bridge_papers(self) -> list[dict]:
        """
        Find papers that cite or discuss multiple QG approaches.
        These are the most likely to contain cross-theory insights.
        """
        bridge_queries = [
            "loop quantum gravity string theory comparison",
            "causal dynamical triangulations asymptotic safety",
            "causal sets loop quantum gravity",
            "noncommutative geometry string theory gravity",
            "emergent gravity loop quantum gravity",
            "Horava-Lifshitz causal dynamical triangulations",
            "quantum gravity approaches review comparison survey",
            "spectral dimension approaches quantum gravity universal",
        ]
        bridges = []
        for q in bridge_queries:
            results = self._search(q, max_results=50)
            for p in results:
                if len(p.theory_tags) >= 2:
                    bridges.append(p)
                    self.kb.insert_paper(p)
        log.info(f"Found {len(bridges)} bridge papers")
        return [{"arxiv_id": b.arxiv_id, "title": b.title, "theories": b.theory_tags} for b in bridges]

    # ── PDF Download ─────────────────────────────────────────────

    def download_pdf(self, arxiv_id: str) -> Optional[Path]:
        """Download a paper's PDF to local storage."""
        safe_id = arxiv_id.replace("/", "_")
        pdf_path = PAPERS_DIR / f"{safe_id}.pdf"
        if pdf_path.exists():
            return pdf_path

        url = f"https://arxiv.org/pdf/{arxiv_id}"
        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            pdf_path.write_bytes(resp.content)
            time.sleep(self.RATE_LIMIT_SECONDS)
            return pdf_path
        except Exception as e:
            log.warning(f"Failed to download PDF {arxiv_id}: {e}")
            return None

    def download_latex_source(self, arxiv_id: str) -> Optional[Path]:
        """Download LaTeX source (preferred over PDF for formula extraction)."""
        safe_id = arxiv_id.replace("/", "_")
        src_dir = PAPERS_DIR / f"{safe_id}_src"
        if src_dir.exists():
            return src_dir

        url = f"https://arxiv.org/e-print/{arxiv_id}"
        try:
            resp = requests.get(url, timeout=60)
            resp.raise_for_status()
            src_dir.mkdir(parents=True, exist_ok=True)
            # Source is usually a gzipped tar
            tar_path = src_dir / "source.tar.gz"
            tar_path.write_bytes(resp.content)
            # Extract
            import tarfile, gzip
            try:
                with tarfile.open(tar_path) as tf:
                    tf.extractall(src_dir, filter="data")
            except (tarfile.ReadError, gzip.BadGzipFile):
                # Sometimes it's just a single .tex file, not tar
                tex_path = src_dir / "main.tex"
                tex_path.write_bytes(resp.content)
            time.sleep(self.RATE_LIMIT_SECONDS)
            return src_dir
        except Exception as e:
            log.warning(f"Failed to download source {arxiv_id}: {e}")
            return None

    # ── Internal ─────────────────────────────────────────────────

    def _fetch_paper_by_id(
        self, arxiv_id: str, theory: TheoryDef, 
        tier: int = 1, is_review: bool = False
    ) -> Optional[Paper]:
        """Fetch a single paper by arXiv ID."""
        try:
            search = arxiv.Search(id_list=[arxiv_id])
            results = list(self.client.results(search))
            if not results:
                log.warning(f"Paper {arxiv_id} not found on arXiv")
                return None
            r = results[0]
            return Paper(
                arxiv_id=arxiv_id,
                title=r.title,
                authors=[a.name for a in r.authors],
                year=r.published.year if r.published else 0,
                abstract=r.summary or "",
                theory_tags=[theory.slug],
                is_review=is_review,
                tier=tier,
            )
        except Exception as e:
            log.warning(f"Error fetching {arxiv_id}: {e}")
            return None

    def _search(
        self, query: str, 
        categories: list[str] | None = None,
        max_results: int = 100,
        sort_by: arxiv.SortCriterion = arxiv.SortCriterion.Relevance,
    ) -> list[Paper]:
        """Search arXiv and return Paper objects."""
        # Build category filter
        if categories:
            cat_filter = " OR ".join(f"cat:{c}" for c in categories)
            full_query = f"({query}) AND ({cat_filter})"
        else:
            full_query = query

        search = arxiv.Search(
            query=full_query,
            max_results=max_results,
            sort_by=sort_by,
        )
        papers = []
        try:
            for r in self.client.results(search):
                # Tag which theories this paper might relate to
                tags = self._auto_tag_theories(r.title, r.summary or "")
                papers.append(Paper(
                    arxiv_id=r.entry_id.split("/abs/")[-1] if "/abs/" in r.entry_id else r.entry_id.split("/")[-1],
                    title=r.title,
                    authors=[a.name for a in r.authors],
                    year=r.published.year if r.published else 0,
                    abstract=r.summary or "",
                    theory_tags=tags,
                ))
        except Exception as e:
            log.warning(f"Search error for '{query}': {e}")
        return papers

    def _auto_tag_theories(self, title: str, abstract: str) -> list[str]:
        """Auto-detect which QG approaches a paper discusses."""
        text = (title + " " + abstract).lower()
        tags = []
        keywords_map = {
            "string_theory": ["string theory", "superstring", "m-theory", "ads/cft", "worldsheet", "brane"],
            "loop_quantum_gravity": ["loop quantum gravity", "spin foam", "spin network", "ashtekar", "lqg"],
            "cdt": ["causal dynamical triangulation", "cdt", "dynamical triangulation"],
            "asymptotic_safety": ["asymptotic safety", "functional renormalization group", "uv fixed point"],
            "causal_sets": ["causal set", "causet", "sorkin"],
            "horava_lifshitz": ["horava", "hořava", "lifshitz gravity", "anisotropic scaling"],
            "noncommutative_geometry": ["noncommutative geometry", "noncommutative spacetime", "spectral triple", "connes"],
            "emergent_gravity": ["emergent gravity", "entropic gravity", "er=epr", "ryu-takayanagi", "verlinde gravity"],
        }
        for slug, kws in keywords_map.items():
            if any(kw in text for kw in kws):
                tags.append(slug)
        if not tags:
            tags = ["unclassified"]
        return tags
