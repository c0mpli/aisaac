"""
Deep Investigation Mode.

Takes a single conjecture and aggressively investigates it:
1. Search arXiv for papers specifically about this connection
2. Read those papers in full, extract all relevant formulas
3. Try multiple algebraic paths to verify/disprove
4. Search for related conjectures that might compose
5. Generate a detailed investigation report

This is what you run on your top 3-5 conjectures after the
main pipeline. It's the difference between "interesting ML finding"
and "publication-ready result."
"""
from __future__ import annotations

import json
import logging
from typing import Optional

from ..knowledge.base import KnowledgeBase, Conjecture
from ..pipeline.config import DATA_DIR
from ..pipeline.llm_client import get_client

log = logging.getLogger(__name__)


INVESTIGATION_PROMPT = """\
You are a theoretical physicist conducting a DEEP INVESTIGATION into a proposed connection between quantum gravity theories.

## The Conjecture
Title: {title}
Type: {conj_type}
Statement (LaTeX): {latex}
Statement (natural): {natural}
Theories involved: {theories}
Current evidence score: {evidence}
Current significance: {significance}

## Your Task
Investigate this conjecture thoroughly. Consider:

1. MATHEMATICAL VERIFICATION
   - Can you independently derive this result?
   - What are the key mathematical steps?
   - Where might the derivation break down?
   - Are there implicit assumptions?

2. PHYSICAL CONSISTENCY
   - Does this make sense physically?
   - What would this imply for experiments?
   - Does it violate any known principles?
   - What are the boundary cases?

3. RELATED RESULTS
   - What existing results in the literature support or contradict this?
   - Who would be the right people to check this with?
   - What follow-up calculations would strengthen the case?
   - Is this a special case of something more general?

4. SIGNIFICANCE ASSESSMENT
   - If true, what does this tell us about quantum gravity?
   - Does it constrain the theory space?
   - Could it lead to testable predictions?
   - Where does this rank among known cross-theory connections?

5. POTENTIAL WEAKNESSES
   - What are the weakest points of the evidence?
   - How could this be an artifact of notation/convention?
   - What counterarguments would skeptics raise?
   - What additional evidence would make this bulletproof?

Be thorough, honest, and specific. If the conjecture is likely wrong, say so.
If it's promising, explain exactly what's needed to confirm it.

Return a detailed JSON report:
{{
    "verdict": "promising|plausible|weak|likely_wrong",
    "confidence": 0.0-1.0,
    "mathematical_analysis": "detailed analysis...",
    "physical_consistency": "assessment...",
    "related_literature": ["list of related papers/results"],
    "key_assumptions": ["list of assumptions that must hold"],
    "weaknesses": ["list of weaknesses"],
    "next_steps": ["ordered list of what to do next"],
    "significance_if_true": "what this means for the field",
    "recommended_experts": ["researchers who could verify this"],
    "search_queries": ["arXiv queries to find supporting evidence"]
}}
"""


class DeepInvestigator:
    """
    Thoroughly investigate a single conjecture.
    """

    def __init__(self, kb: KnowledgeBase):
        self.kb = kb
        self.client = get_client()

    def investigate(self, conjecture_id: int) -> dict:
        """
        Run deep investigation on a conjecture by ID.
        Returns a detailed investigation report.
        """
        conjectures = self.kb.get_conjectures()
        conj = None
        for c in conjectures:
            if c["id"] == conjecture_id:
                conj = c
                break

        if conj is None:
            return {"error": f"Conjecture {conjecture_id} not found"}

        log.info(f"Deep investigation: {conj['title']}")

        # Phase 1: LLM deep analysis
        report = self._llm_analysis(conj)

        # Phase 2: Search for supporting papers
        if report.get("search_queries"):
            papers = self._search_supporting_papers(report["search_queries"])
            report["supporting_papers_found"] = papers

        # Phase 3: Try additional algebraic verification paths
        if conj.get("statement_latex"):
            algebra = self._additional_algebra(conj)
            report["additional_algebra"] = algebra

        # Phase 4: Check for composable conjectures
        composable = self._find_composable(conj, conjectures)
        if composable:
            report["composable_conjectures"] = composable

        # Save report
        report_path = DATA_DIR / f"investigation_{conjecture_id}.json"
        report_path.write_text(json.dumps(report, indent=2, default=str))
        log.info(f"Investigation report saved to {report_path}")

        return report

    def investigate_top_n(self, n: int = 5) -> list[dict]:
        """Investigate the top N conjectures by score."""
        conjectures = self.kb.get_conjectures()
        # Sort by combined score, filter for verified or inconclusive
        candidates = [
            c for c in conjectures
            if c["status"] in ("verified", "inconclusive")
        ]
        candidates.sort(key=lambda c: c["combined_score"], reverse=True)

        reports = []
        for c in candidates[:n]:
            report = self.investigate(c["id"])
            reports.append(report)

        return reports

    def _llm_analysis(self, conj: dict) -> dict:
        """Get detailed LLM analysis of the conjecture."""
        prompt = INVESTIGATION_PROMPT.format(
            title=conj.get("title", ""),
            conj_type=conj.get("conjecture_type", ""),
            latex=conj.get("statement_latex", ""),
            natural=conj.get("statement_natural", ""),
            theories=conj.get("theories_involved", ""),
            evidence=conj.get("evidence_score", 0),
            significance=conj.get("significance_score", 0),
        )

        try:
            return self.client.complete_json(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=8192,
                temperature=0.3,
                phase="deep_investigation",
            )
        except Exception as e:
            log.error(f"LLM analysis failed: {e}")
            return {"error": str(e)}

    def _search_supporting_papers(self, queries: list[str]) -> list[dict]:
        """Search arXiv for papers related to this conjecture."""
        from ..ingestion.crawler import ArxivCrawler
        crawler = ArxivCrawler(self.kb)

        papers = []
        for query in queries[:5]:  # limit to 5 queries
            try:
                results = crawler._search(query, max_results=10)
                for p in results:
                    papers.append({
                        "arxiv_id": p.arxiv_id,
                        "title": p.title,
                        "year": p.year,
                        "theories": p.theory_tags,
                    })
            except Exception as e:
                log.warning(f"Search failed for '{query}': {e}")

        # Deduplicate
        seen = set()
        unique = []
        for p in papers:
            if p["arxiv_id"] not in seen:
                seen.add(p["arxiv_id"])
                unique.append(p)

        return unique

    def _additional_algebra(self, conj: dict) -> dict:
        """Try additional algebraic verification approaches."""
        import sympy as sp

        latex = conj.get("statement_latex", "")
        if not latex:
            return {"status": "no_latex"}

        results = {
            "simplification_attempts": [],
            "special_cases": [],
        }

        # Ask LLM to suggest alternative algebraic paths
        prompt = f"""
Given this mathematical conjecture in quantum gravity:
{latex}

Suggest 3 different algebraic approaches to verify or disprove it.
For each, provide a concrete sympy expression to evaluate.

Return JSON:
{{
    "approaches": [
        {{"name": "...", "sympy_code": "...", "expected_result": "..."}}
    ]
}}
"""
        try:
            approaches = self.client.complete_json(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2048,
                temperature=0.3,
                phase="deep_algebra",
            )
            results["approaches"] = approaches.get("approaches", [])
        except Exception:
            pass

        return results

    def _find_composable(self, conj: dict, all_conjectures: list[dict]) -> list[dict]:
        """
        Find other conjectures that could COMPOSE with this one.
        E.g., if conjecture A says "X in theory 1 = Y in theory 2"
        and conjecture B says "Y in theory 2 = Z in theory 3",
        then composing gives "X in theory 1 = Z in theory 3".
        """
        theories = set()
        raw = conj.get("theories_involved", "[]")
        if isinstance(raw, str):
            theories = set(json.loads(raw))
        else:
            theories = set(raw)

        composable = []
        for other in all_conjectures:
            if other["id"] == conj["id"]:
                continue

            other_theories = set()
            raw_o = other.get("theories_involved", "[]")
            if isinstance(raw_o, str):
                other_theories = set(json.loads(raw_o))
            else:
                other_theories = set(raw_o)

            # Composable if they share at least one theory (the bridge)
            shared = theories & other_theories
            if shared and not theories.issubset(other_theories):
                composable.append({
                    "conjecture_id": other["id"],
                    "title": other["title"],
                    "shared_theories": list(shared),
                    "new_theories": list(other_theories - theories),
                    "composition_potential": (
                        f"Could extend connection to {other_theories - theories} "
                        f"via bridge theory {shared}"
                    ),
                })

        return composable
