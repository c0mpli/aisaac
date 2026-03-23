"""
Structured Formula Extractor.

Instead of asking the LLM to freestyle extract formulas from a whole paper,
this asks NARROW questions about EACH equation individually:

1. Is this equation a prediction, key result, correction, or just setup?
2. What quantity does it predict?
3. Does it contain a numerical value? What is it?
4. Is this derived here or cited from another paper?

Narrow questions → reliable answers → no hallucinated formulas.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from ..knowledge.base import KnowledgeBase, ExtractedFormula
from ..pipeline.llm_client import get_client

log = logging.getLogger(__name__)


CLASSIFY_EQUATION_PROMPT = """\
You are classifying a single equation from a physics paper.

Paper: {title}
Theory: {theory_tags}

Equation (from {environment} environment, section: {section}):
```
{equation_latex}
```

Context before equation:
{context_before}

Context after equation:
{context_after}

Answer these questions as JSON. Be precise and conservative.

{{
    "is_key_result": true/false,
    "result_type": "prediction|key_equation|correction|mapping|definition|intermediate|unclear",
    "quantity_type": "<one of: spectral_dimension, newton_correction, black_hole_entropy, bh_entropy_log_correction, dispersion_relation_modification, graviton_propagator_modification, running_gravitational_coupling, area_gap, entanglement_entropy_area_law, cosmological_constant, other>",
    "has_numerical_value": true/false,
    "numerical_value": <number or null>,
    "numerical_description": "<what the number represents, or null>",
    "is_derived_here": true/false,
    "cited_from": "<arxiv ID or author name if cited, null if derived here>",
    "one_line_description": "<what this equation says physically, max 20 words>",
    "confidence": 0.0-1.0
}}

Rules:
- "prediction" = a TESTABLE quantitative prediction this paper makes
- "key_equation" = a defining equation of the theoretical framework
- "correction" = a modification to a known result (GR, Newton, etc.)
- "mapping" = an explicit connection to another theoretical approach
- "definition" = notation setup, not a result
- "intermediate" = step in a derivation, not a final result
- Only mark is_key_result=true for predictions, key_equations, corrections, and mappings.
- If uncertain, set result_type="unclear" and is_key_result=false.

Return ONLY the JSON object.
"""


class StructuredExtractor:
    """Extract formulas one equation at a time with narrow classification questions."""

    def __init__(self, kb: KnowledgeBase):
        self.kb = kb
        self.client = get_client()

    def extract_from_equations(
        self,
        paper: dict,
        raw_equations: list,
        max_equations: int = 40,
    ) -> list[ExtractedFormula]:
        """
        Classify each equation individually.

        Args:
            paper: Paper metadata dict
            raw_equations: List of RawEquation objects from LaTeX parser
            max_equations: Max equations to classify (API cost control)
        """
        title = paper.get("title", "")
        theory_tags = paper.get("theory_tags", [])
        if isinstance(theory_tags, str):
            theory_tags = json.loads(theory_tags)
        paper_id = paper.get("id", 0)

        # Prioritize labeled equations and those in results sections
        priority_sections = {"result", "conclusion", "discussion", "prediction",
                           "entropy", "correction", "spectral", "propagator"}

        def eq_priority(eq):
            section = (getattr(eq, "section", "") or "").lower()
            has_priority = any(s in section for s in priority_sections)
            has_label = bool(getattr(eq, "label", None))
            return (not has_priority, not has_label)

        sorted_eqs = sorted(raw_equations, key=eq_priority)
        selected = sorted_eqs[:max_equations]

        # Classify equations in parallel (6 workers, throttled)
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import threading
        import time as _time

        _rate_lock = threading.Lock()
        _last_call = [0.0]
        MIN_INTERVAL = 4.5  # stay under 15 RPM

        def _classify_one(eq):
            with _rate_lock:
                now = _time.time()
                wait = MIN_INTERVAL - (now - _last_call[0])
                if wait > 0:
                    _time.sleep(wait)
                _last_call[0] = _time.time()
            return eq, self._classify_equation(
                title=title,
                theory_tags=", ".join(theory_tags) if isinstance(theory_tags, list) else theory_tags,
                equation_latex=eq.latex,
                environment=getattr(eq, "environment", "equation"),
                section=getattr(eq, "section", "unknown"),
                context_before=getattr(eq, "context_before", "")[-200:],
                context_after=getattr(eq, "context_after", "")[:200],
            )

        classifications = []
        with ThreadPoolExecutor(max_workers=6) as pool:
            futures = {pool.submit(_classify_one, eq): eq for eq in selected}
            for future in as_completed(futures):
                try:
                    eq, classification = future.result()
                    if classification and classification.get("is_key_result"):
                        classifications.append((eq, classification))
                except Exception:
                    pass

        extracted = []
        for eq, classification in classifications:

            # Build ExtractedFormula from classification
            ef = ExtractedFormula(
                paper_id=paper_id,
                latex=eq.latex,
                sympy_expr="",
                formula_type=classification.get("result_type", "other"),
                quantity_type=classification.get("quantity_type", "other"),
                theory_slug=theory_tags[0] if theory_tags else "unknown",
                description=classification.get("one_line_description", ""),
                variables=[],
                regime="",
                approximations="",
                confidence=float(classification.get("confidence", 0.5)),
            )

            # Store numerical value in description if present
            if classification.get("has_numerical_value") and classification.get("numerical_value") is not None:
                ef.description += f" [value: {classification['numerical_value']}]"
                if classification.get("numerical_description"):
                    ef.description += f" ({classification['numerical_description']})"

            # Mark if cited vs derived
            if not classification.get("is_derived_here") and classification.get("cited_from"):
                ef.approximations = f"Cited from {classification['cited_from']}"

            fid = self.kb.insert_formula(ef)
            ef.id = fid
            extracted.append(ef)

        log.info(f"  Structured extraction: {len(extracted)}/{len(selected)} equations are key results")
        return extracted

    def _classify_equation(self, **kwargs) -> dict | None:
        """Ask the LLM to classify a single equation."""
        prompt = CLASSIFY_EQUATION_PROMPT.format(**kwargs)

        try:
            raw = self.client.complete(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=512,
                temperature=0.1,
                phase="extraction",
            )
            # Extract JSON
            raw = raw.strip()
            if raw.startswith("```"):
                import re
                raw = re.sub(r"^```(?:json)?\s*\n?", "", raw)
                raw = re.sub(r"\n?```\s*$", "", raw)

            # Find JSON object
            for i, ch in enumerate(raw):
                if ch == "{":
                    depth = 0
                    for j in range(i, len(raw)):
                        if raw[j] == "{":
                            depth += 1
                        elif raw[j] == "}":
                            depth -= 1
                            if depth == 0:
                                return json.loads(raw[i:j+1])
                    break

            return json.loads(raw)
        except Exception as e:
            log.debug(f"  Classification failed: {e}")
            return None
