"""
Formula Extractor.

LLM-powered extraction of KEY formulas from physics papers.
Not every equation matters — a paper might have 50 equations
but only 2-3 are results. The LLM identifies predictions,
key equations, corrections, and mappings.
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Optional


from ..pipeline.config import ANTHROPIC_MODEL, ANTHROPIC_MAX_TOKENS, QuantityType, FormulaType
from ..pipeline.llm_client import get_client
from ..knowledge.base import KnowledgeBase, ExtractedFormula, Paper

log = logging.getLogger(__name__)


EXTRACTION_PROMPT = """\
You are a theoretical physicist specializing in quantum gravity. You are reading a paper and must extract ALL formulas that constitute key RESULTS — not intermediate steps or definitions.

## Paper Info
Title: {title}
Authors: {authors}
Year: {year}
Abstract: {abstract}
Theory tags: {theory_tags}

## Paper Content (relevant sections)
{content}

## Task
Extract formulas that are:
1. **PREDICTIONS** — quantitative predictions about observables (spectral dimension, corrections to Newton's law, black hole entropy, dispersion relations, etc.)
2. **KEY EQUATIONS** — the defining/fundamental equations of the approach presented
3. **CORRECTIONS** — modifications to known physics (GR, QFT, Newtonian gravity)
4. **MAPPINGS** — explicit mathematical connections to other quantum gravity approaches

SKIP: definitions, notation setup, intermediate derivation steps, standard textbook equations unless re-derived with novel corrections.

## DIVERSITY REQUIREMENT
Extract formulas across DIVERSE quantity types. Do not extract more than 2 formulas for any single quantity_type (e.g., max 2 for black_hole_entropy). Prioritize extracting at least one formula from EACH of these categories if present in the paper:
- spectral_dimension (effective dimension vs scale)
- newton_correction (quantum corrections to gravitational potential)
- dispersion_relation_modification (modified E-p relation)
- graviton_propagator_modification (UV-modified propagator)
- bh_entropy_log_correction (subleading log terms in entropy)
- running_gravitational_coupling (scale-dependent G or Λ)

## For each formula, provide:
- `latex`: the formula in LaTeX (clean, well-formed)
- `formula_type`: one of ["prediction", "key_equation", "correction", "mapping"]
- `quantity_type`: one of the specific types below. You MUST classify into a specific type — only use "other" if it truly fits NONE:
    - "spectral_dimension": any d_s, spectral dimension, return probability, diffusion on geometry, dimensional flow/reduction
    - "newton_correction": any modification to V(r) = -Gm1m2/r, quantum correction to gravitational potential, graviton exchange correction
    - "black_hole_entropy": any S_BH, Bekenstein-Hawking entropy, microstate counting, horizon entropy, area law S=A/4
    - "bh_entropy_log_correction": any logarithmic correction to BH entropy, subleading ln(A) term, coefficient of log correction
    - "dispersion_relation_modification": any E^2 = p^2 + corrections, modified dispersion relation, Lorentz-violating dispersion, Planck-scale E-p
    - "graviton_propagator_modification": any modified graviton propagator, UV graviton behavior, momentum-space gravity propagator
    - "running_gravitational_coupling": any G(k), running Newton constant, scale-dependent G or Λ, gravitational beta function, RG flow of G
    - "area_gap": any minimum area, area spectrum, area eigenvalue, discrete area quantization
    - "entanglement_entropy_area_law": any Ryu-Takayanagi, holographic entanglement entropy, S_EE proportional to area
    - "cosmological_constant": any Λ prediction, vacuum energy, dark energy from QG
    - "heat_kernel_coefficient": any heat kernel expansion, Seeley-DeWitt coefficient
    - "other": ONLY if none of the above apply
- `theory_slug`: one of ["string_theory", "loop_quantum_gravity", "cdt", "asymptotic_safety", "causal_sets", "horava_lifshitz", "noncommutative_geometry", "emergent_gravity"]
- `description`: 1-2 sentences explaining what this formula represents physically
- `variables`: list of {{"symbol": "...", "meaning": "...", "dimensions": "..."}}
- `regime`: where is this formula valid? (e.g., "near Planck scale", "large volume limit", "weak field")
- `approximations`: what approximations were made? (e.g., "leading order in l_P/r", "semiclassical limit")
- `confidence`: 0.0-1.0 how confident are you this is a genuine key result (not a definition or intermediate step)?
- `claimed_connections`: if the paper claims this formula relates to another approach, describe the connection

Return ONLY a JSON array. If there are no extractable key formulas, return [].
Important: be thorough but selective. Extract the MAIN RESULTS, not every equation.
"""


NORMALIZATION_PROMPT = """\
You are normalizing a physics formula to standard notation.

## Original formula
LaTeX: {latex}
Description: {description}
Theory: {theory_slug}
Variables: {variables}

## Standard notation conventions
- Newton's constant: G (not G_N, κ², etc.)
- Planck length: l_P (not l_p, ℓ_P, l_{{Pl}})
- Planck mass: M_P (not m_P, M_{{Pl}})
- Cosmological constant: \\Lambda
- Speed of light: c
- Reduced Planck constant: \\hbar
- Spacetime dimension: d (total), d-1 (spatial)
- Metric signature: (-+++)
- Natural units: \\hbar = c = 1 unless explicitly needed
- Immirzi parameter: \\gamma_I
- String tension: \\alpha'
- String coupling: g_s
- NC parameter: \\theta

## Task
1. Rewrite the formula in standard notation
2. Express everything in natural units (\\hbar = c = 1) where possible
3. Convert any κ = √(16πG) or κ² = 16πG to explicit G
4. Make all Planck-scale quantities explicit: l_P = √(G\\hbar/c³) → √G in natural units

Return JSON:
{{
    "normalized_latex": "...",
    "normalized_sympy": "...",  // sympy-parseable Python expression string
    "substitutions_made": ["list of what you changed"],
    "dimensional_check": "dimensions of the result"
}}
"""


class FormulaExtractor:
    """Extract key formulas from physics papers using LLM."""

    def __init__(self, kb: KnowledgeBase):
        self.kb = kb
        self.client = get_client()

    def extract_from_text(
        self, 
        paper: Paper | dict, 
        content: str,
        normalize: bool = True,
    ) -> list[ExtractedFormula]:
        """
        Extract key formulas from paper text.
        
        Args:
            paper: Paper metadata (Paper object or dict with title, authors, etc.)
            content: The paper text (LaTeX or extracted text)
            normalize: Whether to also normalize notation
            
        Returns:
            List of ExtractedFormula objects (already inserted into KB)
        """
        if isinstance(paper, dict):
            title = paper.get("title", "")
            authors = paper.get("authors", [])
            year = paper.get("year", 0)
            abstract = paper.get("abstract", "")
            theory_tags = paper.get("theory_tags", [])
            paper_id = paper.get("id", 0)
        else:
            title = paper.title
            authors = paper.authors
            year = paper.year
            abstract = paper.abstract
            theory_tags = paper.theory_tags
            paper_id = paper.id or 0

        # Truncate content to fit context window (~150K chars ≈ ~50K tokens)
        max_chars = 150_000
        if len(content) > max_chars:
            # Keep intro + results + conclusions, skip middle
            third = max_chars // 3
            content = content[:third] + "\n\n[...middle sections truncated...]\n\n" + content[-third:]

        prompt = EXTRACTION_PROMPT.format(
            title=title,
            authors=", ".join(authors) if isinstance(authors, list) else authors,
            year=year,
            abstract=abstract,
            theory_tags=", ".join(theory_tags) if isinstance(theory_tags, list) else theory_tags,
            content=content,
        )

        try:
            raw = self.client.complete(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                phase="extraction",
            )
            raw = _extract_json(raw.strip())
            formulas_data = json.loads(raw)
        except Exception as e:
            log.error(f"Formula extraction failed for '{title}': {e}")
            return []

        if not isinstance(formulas_data, list):
            log.warning(f"Expected list, got {type(formulas_data)} for '{title}'")
            return []

        extracted = []
        for fd in formulas_data:
            try:
                ef = ExtractedFormula(
                    paper_id=paper_id,
                    latex=fd.get("latex", ""),
                    sympy_expr="",
                    formula_type=fd.get("formula_type", "other"),
                    quantity_type=fd.get("quantity_type", "other"),
                    theory_slug=fd.get("theory_slug", theory_tags[0] if theory_tags else "unknown"),
                    description=fd.get("description", ""),
                    variables=fd.get("variables", []),
                    regime=fd.get("regime", ""),
                    approximations=fd.get("approximations", ""),
                    confidence=float(fd.get("confidence", 0.5)),
                )
                # Normalize notation if requested
                if normalize and ef.latex:
                    norm = self._normalize(ef)
                    if norm:
                        ef.normalized_latex = norm.get("normalized_latex", "")
                        ef.normalized_sympy = norm.get("normalized_sympy", "")

                fid = self.kb.insert_formula(ef)
                ef.id = fid
                extracted.append(ef)
                log.debug(f"  Extracted: {ef.description[:60]}... (conf={ef.confidence:.2f})")
            except Exception as e:
                log.warning(f"Failed to process formula entry: {e}")
                continue

        log.info(f"Extracted {len(extracted)} formulas from '{title}'")
        return extracted

    def _normalize(self, formula: ExtractedFormula) -> Optional[dict]:
        """Normalize a formula to standard notation using LLM."""
        prompt = NORMALIZATION_PROMPT.format(
            latex=formula.latex,
            description=formula.description,
            theory_slug=formula.theory_slug,
            variables=json.dumps(formula.variables),
        )
        try:
            raw = self.client.complete(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2048,
                temperature=0.1,
                phase="normalization",
            )
            raw = _extract_json(raw.strip())
            return json.loads(raw)
        except Exception as e:
            log.warning(f"Normalization failed: {e}")
            return None

    def extract_from_file(
        self, paper: Paper | dict, filepath: Path, normalize: bool = True
    ) -> list[ExtractedFormula]:
        """Extract formulas from a local file (LaTeX or PDF)."""
        filepath = Path(filepath)

        if filepath.suffix == ".tex" or filepath.is_dir():
            content = self._read_latex(filepath)
        elif filepath.suffix == ".pdf":
            content = self._read_pdf(filepath)
        else:
            log.warning(f"Unknown file type: {filepath}")
            return []

        return self.extract_from_text(paper, content, normalize=normalize)

    def _read_latex(self, path: Path) -> str:
        """Read LaTeX source from a file or directory."""
        if path.is_dir():
            tex_files = list(path.glob("*.tex"))
            if not tex_files:
                return ""
            # Try to find main file
            main = None
            for f in tex_files:
                text = f.read_text(errors="replace")
                if r"\begin{document}" in text:
                    main = f
                    break
            if main is None:
                main = tex_files[0]
            return main.read_text(errors="replace")
        return path.read_text(errors="replace")

    def _read_pdf(self, path: Path) -> str:
        """Extract text from PDF."""
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(str(path))
            text_parts = []
            for page in reader.pages:
                t = page.extract_text()
                if t:
                    text_parts.append(t)
            return "\n".join(text_parts)
        except Exception as e:
            log.warning(f"PDF extraction failed for {path}: {e}")
            return ""


def _extract_json(text: str) -> str:
    """Extract JSON from LLM response that might be wrapped in markdown."""
    # Try to find JSON array
    text = text.strip()
    if text.startswith("```"):
        # Remove markdown code block
        text = re.sub(r"^```(?:json)?\s*\n?", "", text)
        text = re.sub(r"\n?```\s*$", "", text)
    # Find first [ or {
    for i, ch in enumerate(text):
        if ch in "[{":
            # Find matching close
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
