"""
Assumption Extractor (Agent 1).

Reads each paper and extracts EVERY assumption — explicit AND implicit.
This is the foundation of the premise discovery engine.
"""
from __future__ import annotations

import json
import logging
import time
import re
from typing import Optional

from ..knowledge.base import KnowledgeBase
from ..pipeline.llm_client import get_client

log = logging.getLogger(__name__)

ASSUMPTION_PROMPT = """\
You are a philosopher of physics analyzing the foundational assumptions of a scientific paper.

## Paper Info
Title: {title}
Authors: {authors}
Year: {year}
Theory: {theory_slug}
Abstract: {abstract}

## Paper Content
{content}

## Task
Extract EVERY assumption this paper makes. Be exhaustive. Extract AT LEAST 10.

EXPLICIT assumptions: things the paper states it assumes.
Example: "We assume a 4-dimensional Lorentzian manifold"

IMPLICIT assumptions: things the paper never states because the authors consider them obvious, but which COULD be wrong.
Examples:
- Spacetime is continuous (not stated, just used)
- The metric signature is fixed (never questioned)
- Locality holds at all scales (silently assumed)
- Background independence is necessary (assumed but debatable)
- Unitarity is preserved (assumed without justification)

METHODOLOGICAL assumptions: choices about how to approach the problem.
- Which variables are treated as fundamental
- Which limit is taken first
- Which degrees of freedom are quantized

For each assumption, provide:
- "text": the assumption stated clearly (one sentence)
- "type": "explicit" | "implicit" | "mathematical" | "physical" | "methodological"
- "is_stated": true if paper explicitly states it, false if inferred
- "category": "spacetime_structure" | "symmetry" | "causality" | "quantization" | "information" | "thermodynamics" | "mathematical_framework" | "other"
- "how_fundamental": "core" (removing it changes everything) | "auxiliary" (could be modified) | "universal" (shared by all approaches)
- "what_if_wrong": one sentence on what changes if this assumption is dropped
- "confidence": 0.0-1.0 how confident you are this is actually an assumption of the paper

Return ONLY a JSON array. Focus especially on IMPLICIT assumptions — those are where breakthroughs hide.
"""


class AssumptionExtractor:
    """Extract assumptions from physics papers."""

    def __init__(self, kb: KnowledgeBase):
        self.kb = kb
        self.client = get_client()

    def extract_from_paper(self, paper: dict, content: str) -> list[dict]:
        """Extract assumptions from a single paper."""
        title = paper.get("title", "")
        theory_tags = paper.get("theory_tags", [])
        if isinstance(theory_tags, str):
            theory_tags = json.loads(theory_tags)
        theory_slug = theory_tags[0] if theory_tags else "unknown"

        # Truncate content
        max_chars = 60_000
        if len(content) > max_chars:
            third = max_chars // 3
            content = content[:third] + "\n\n[...truncated...]\n\n" + content[-third:]

        prompt = ASSUMPTION_PROMPT.format(
            title=title,
            authors=paper.get("authors", ""),
            year=paper.get("year", ""),
            theory_slug=theory_slug,
            abstract=paper.get("abstract", ""),
            content=content,
        )

        try:
            assumptions_data = self.client.complete_json(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                phase="assumption_extraction",
            )
        except Exception as e:
            log.error(f"Assumption extraction failed for '{title}': {e}")
            return []

        if not isinstance(assumptions_data, list):
            if isinstance(assumptions_data, dict):
                # Sometimes LLM wraps in {"assumptions": [...]}
                for key in ("assumptions", "results", "data"):
                    if key in assumptions_data and isinstance(assumptions_data[key], list):
                        assumptions_data = assumptions_data[key]
                        break
                else:
                    return []
            else:
                return []

        results = []
        paper_id = paper.get("id", 0)

        for ad in assumptions_data:
            try:
                aid = self.kb.insert_assumption(
                    paper_id=paper_id,
                    theory_slug=theory_slug,
                    assumption_text=ad.get("text", ""),
                    assumption_type=ad.get("type", "implicit"),
                    is_stated=1 if ad.get("is_stated", False) else 0,
                    category=ad.get("category", "other"),
                    how_fundamental=ad.get("how_fundamental", "auxiliary"),
                    what_if_wrong=ad.get("what_if_wrong", ""),
                    confidence=float(ad.get("confidence", 0.5)),
                )
                results.append({"id": aid, **ad})
            except Exception as e:
                log.warning(f"Failed to store assumption: {e}")
                continue

        log.info(f"Extracted {len(results)} assumptions from '{title}'")
        return results

    def extract_all_unprocessed(self, max_workers: int = 6) -> int:
        """Extract assumptions from all papers that haven't been processed yet.

        Uses parallel workers since each paper is independent.
        Gemini Flash handles 6 concurrent requests easily.
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed

        processed = set()
        existing = self.kb.get_assumptions()
        for a in existing:
            processed.add(a.get("paper_id"))

        all_papers = self.kb.conn.execute("SELECT * FROM papers").fetchall()
        unprocessed = [dict(p) for p in all_papers if p["id"] not in processed]

        log.info(f"Extracting assumptions from {len(unprocessed)} papers ({max_workers} workers)...")
        total = 0
        completed = 0

        import threading
        _rate_lock = threading.Lock()
        _last_call = [0.0]  # mutable for closure
        MIN_INTERVAL = 4.5  # seconds between calls (keeps under 15 RPM)

        def _process(paper):
            # Throttle: ensure MIN_INTERVAL between API calls
            with _rate_lock:
                now = time.time()
                wait = MIN_INTERVAL - (now - _last_call[0])
                if wait > 0:
                    time.sleep(wait)
                _last_call[0] = time.time()

            content = f"Title: {paper['title']}\n\nAbstract: {paper['abstract']}"
            return paper['title'], self.extract_from_paper(paper, content)

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {pool.submit(_process, p): p for p in unprocessed}
            for future in as_completed(futures):
                completed += 1
                try:
                    title, results = future.result()
                    n = len(results)
                    total += n
                    log.info(f"  [{completed}/{len(unprocessed)}] {title[:60]}... → {n} assumptions")
                except Exception as e:
                    paper = futures[future]
                    log.warning(f"  [{completed}/{len(unprocessed)}] {paper['title'][:60]}... FAILED: {e}")

        log.info(f"Total assumptions extracted: {total}")
        return total


def _extract_json(text: str) -> str:
    """Extract JSON from LLM response."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*\n?", "", text)
        text = re.sub(r"\n?```\s*$", "", text)
    for i, ch in enumerate(text):
        if ch in "[{":
            depth = 0
            for j in range(i, len(text)):
                if text[j] == ch:
                    depth += 1
                elif text[j] == ("]" if ch == "[" else "}"):
                    depth -= 1
                    if depth == 0:
                        return text[i : j + 1]
            return text[i:]
    return text
