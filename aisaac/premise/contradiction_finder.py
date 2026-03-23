"""
Contradiction Finder (Agent 2).

Finds where two trusted theories make contradictory assumptions.
Not disagreements in results (symptoms) -- disagreements in PREMISES (causes).

Types:
1. DIRECT: Theory A assumes X, Theory B assumes NOT X
2. IMPLICIT: Both derive results that can't both be true -> trace back to which assumption differs
3. META-LEVEL: Incompatible mathematical frameworks
"""
from __future__ import annotations

import json
import logging
import re
from collections import defaultdict
from difflib import SequenceMatcher

from ..knowledge.base import KnowledgeBase
from ..pipeline.llm_client import get_client

log = logging.getLogger(__name__)

CONTRADICTION_PROMPT = """\
You are analyzing assumptions from two different quantum gravity theories to find CONTRADICTIONS.

## Theory A: {theory_a}
Assumptions:
{assumptions_a}

## Theory B: {theory_b}
Assumptions:
{assumptions_b}

## Task
Find where these two theories make CONTRADICTORY assumptions. Not just different -- contradictory.
One says X, the other says NOT X (or something incompatible with X).

For each contradiction found:
- "assumption_a": which assumption from Theory A (quote the text exactly)
- "assumption_b": which assumption from Theory B (quote the text exactly)
- "description": explain the contradiction in one sentence
- "severity": "fundamental" (core premises clash) | "moderate" (auxiliary clash) | "technical" (methodological difference)
- "resolution_candidates": list of 1-3 ways this could be resolved (e.g., "one theory is wrong about X", "both are approximations of a deeper truth", "they apply in different regimes")

Return ONLY a JSON array. If no genuine contradictions exist, return [].
Be strict -- a contradiction means they CANNOT both be right about the same thing.
"""


class ContradictionFinder:
    """Find contradictions between theories' assumptions."""

    def __init__(self, kb: KnowledgeBase):
        self.kb = kb
        self.client = get_client()

    def find_all(self) -> list[dict]:
        """Find contradictions between all pairs of theories."""
        assumptions = self.kb.get_assumptions()

        # Group by theory
        by_theory = defaultdict(list)
        for a in assumptions:
            by_theory[a["theory_slug"]].append(a)

        theories = sorted(by_theory.keys())
        all_contradictions = []

        for i, ta in enumerate(theories):
            for tb in theories[i + 1 :]:
                contras = self._compare_theories(ta, tb, by_theory[ta], by_theory[tb])
                all_contradictions.extend(contras)

        log.info(f"Found {len(all_contradictions)} contradictions across {len(theories)} theories")
        return all_contradictions

    def _compare_theories(
        self,
        theory_a: str,
        theory_b: str,
        assumptions_a: list[dict],
        assumptions_b: list[dict],
    ) -> list[dict]:
        """Find contradictions between two theories."""
        # Format assumptions for the prompt
        fmt_a = "\n".join(
            f"- [{a['assumption_type']}] {a['assumption_text']} (category: {a['category']})"
            for a in assumptions_a[:20]  # limit to top 20
        )
        fmt_b = "\n".join(
            f"- [{a['assumption_type']}] {a['assumption_text']} (category: {a['category']})"
            for a in assumptions_b[:20]
        )

        if not fmt_a or not fmt_b:
            return []

        prompt = CONTRADICTION_PROMPT.format(
            theory_a=theory_a,
            theory_b=theory_b,
            assumptions_a=fmt_a,
            assumptions_b=fmt_b,
        )

        try:
            raw = self.client.complete(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                phase="contradiction_finding",
            )
            raw = _extract_json(raw.strip())
            data = json.loads(raw)
        except Exception as e:
            log.warning(f"Contradiction finding failed for {theory_a} vs {theory_b}: {e}")
            return []

        if not isinstance(data, list):
            return []

        results = []
        # Map assumption texts back to IDs
        text_to_id_a = {a["assumption_text"]: a["id"] for a in assumptions_a}
        text_to_id_b = {a["assumption_text"]: a["id"] for a in assumptions_b}

        for d in data:
            a_text = d.get("assumption_a", "")
            b_text = d.get("assumption_b", "")

            # Find closest match
            a_id = _find_closest_id(a_text, text_to_id_a)
            b_id = _find_closest_id(b_text, text_to_id_b)

            cid = self.kb.insert_contradiction(
                assumption_a_id=a_id or 0,
                assumption_b_id=b_id or 0,
                theory_a=theory_a,
                theory_b=theory_b,
                description=d.get("description", ""),
                resolution_candidates=json.dumps(d.get("resolution_candidates", [])),
                severity=d.get("severity", "moderate"),
            )
            results.append({"id": cid, **d, "theory_a": theory_a, "theory_b": theory_b})

        log.info(f"  {theory_a} vs {theory_b}: {len(results)} contradictions")
        return results

    def trace_result_to_premise(self, result_a: dict, result_b: dict) -> dict:
        """Given two conflicting results, trace backward to find which
        differing assumption causes the difference."""
        prompt = f"""Two quantum gravity theories produce conflicting results:

Theory A ({result_a.get('theory_slug', '')}): {result_a.get('description', '')}
Formula: {result_a.get('latex', '')}

Theory B ({result_b.get('theory_slug', '')}): {result_b.get('description', '')}
Formula: {result_b.get('latex', '')}

Which ASSUMPTION difference between these two theories is most likely responsible for the different results?
Answer in JSON: {{"differing_assumption": "...", "how_it_causes_difference": "...", "which_is_likely_right": "...", "how_to_test": "..."}}"""

        try:
            raw = self.client.complete(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                phase="premise_tracing",
            )
            return json.loads(_extract_json(raw.strip()))
        except Exception:
            return {}


# ── Helpers ──────────────────────────────────────────────────────


def _extract_json(text: str) -> str:
    """Extract JSON from LLM response that might be wrapped in markdown."""
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


def _find_closest_id(query: str, text_to_id: dict[str, int], threshold: float = 0.5) -> int | None:
    """Find the ID of the assumption whose text best matches *query*.

    Uses ``difflib.SequenceMatcher`` for fuzzy matching so that minor
    LLM paraphrasing (dropped punctuation, re-ordered words, etc.)
    does not prevent a match.

    Returns ``None`` if no candidate exceeds *threshold*.
    """
    if not query or not text_to_id:
        return None

    # Fast path: exact match
    if query in text_to_id:
        return text_to_id[query]

    best_id: int | None = None
    best_ratio = 0.0
    query_lower = query.lower()

    for text, aid in text_to_id.items():
        ratio = SequenceMatcher(None, query_lower, text.lower()).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_id = aid

    return best_id if best_ratio >= threshold else None
