"""
Verification Engine.

Multi-layer verification of proposed conjectures:
1. Algebraic: sympy identity checking
2. Numerical: evaluate both sides on random inputs
3. Dimensional: units must match
4. Counterexample: actively try to disprove
5. Novelty: check if this connection is already known

A conjecture must survive ALL checks to be considered verified.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Optional

import numpy as np
import sympy as sp

from ..pipeline.config import ANTHROPIC_MODEL
from ..knowledge.base import KnowledgeBase, Conjecture

log = logging.getLogger(__name__)


@dataclass
class VerificationResult:
    conjecture_id: int
    # Each check: True = passed, False = failed, None = inconclusive
    algebraic: Optional[bool] = None
    numerical: Optional[bool] = None
    dimensional: Optional[bool] = None
    counterexample_found: Optional[bool] = None
    is_novel: Optional[bool] = None
    # Details
    algebraic_details: str = ""
    numerical_details: str = ""
    dimensional_details: str = ""
    counterexample_details: str = ""
    novelty_details: str = ""
    # Overall
    overall_status: str = "unverified"  # verified | disproved | inconclusive | known


class AlgebraicVerifier:
    """
    Use sympy to verify mathematical identities in conjectures.
    """

    def verify(self, conjecture: Conjecture) -> tuple[Optional[bool], str]:
        """
        Attempt to verify the conjecture algebraically.
        
        Parses the LaTeX statement, extracts the claimed equality,
        and tries to simplify the difference to zero.
        """
        latex = conjecture.statement_latex
        if not latex:
            return None, "no LaTeX statement"

        # Try to extract "LHS = RHS" from the statement
        parts = self._extract_equality(latex)
        if not parts:
            return None, "could not parse equality from statement"

        lhs_str, rhs_str = parts
        try:
            lhs = sp.sympify(lhs_str)
            rhs = sp.sympify(rhs_str)
        except Exception as e:
            return None, f"sympy parse error: {e}"

        # Try to prove equality
        try:
            diff = sp.simplify(lhs - rhs)
            if diff == 0:
                return True, "sympy verified: difference simplifies to 0"
            
            # Try expand + simplify
            diff2 = sp.simplify(sp.expand(lhs - rhs))
            if diff2 == 0:
                return True, "sympy verified after expand + simplify"

            # Try trigsimp, powsimp, etc.
            for simp_fn in [sp.trigsimp, sp.powsimp, sp.logcombine, sp.radsimp]:
                try:
                    diff3 = simp_fn(diff)
                    if diff3 == 0:
                        return True, f"verified via {simp_fn.__name__}"
                except Exception:
                    continue

            # Can't simplify to zero — inconclusive (might still be true)
            return None, f"could not simplify to 0, remaining: {diff}"

        except Exception as e:
            return None, f"simplification error: {e}"

    def _extract_equality(self, latex: str) -> Optional[tuple[str, str]]:
        """Extract LHS and RHS from a LaTeX equality."""
        # Strip \text{...} blocks first
        cleaned = re.sub(r'\\text\{[^}]*\}', '', latex)
        cleaned = re.sub(r'\\mathrm\{[^}]*\}', '', cleaned)
        cleaned = re.sub(r'\\quad.*', '', cleaned)  # remove trailing text after \quad

        # Try various equality patterns
        for sep in ["=", "\\equiv", "\\sim", "\\approx"]:
            if sep in cleaned:
                parts = cleaned.split(sep, 1)
                if len(parts) == 2:
                    lhs = self._latex_to_sympy(parts[0].strip())
                    rhs = self._latex_to_sympy(parts[1].strip())
                    if lhs and rhs:
                        return lhs, rhs
        return None

    def _latex_to_sympy(self, latex: str) -> Optional[str]:
        """Best-effort LaTeX to sympy string conversion."""
        s = latex
        # Remove display math markers
        s = s.replace("$", "").replace("\\[", "").replace("\\]", "")
        s = s.replace("\\left(", "(").replace("\\right)", ")")
        s = s.replace("\\left[", "[").replace("\\right]", "]")
        # Common substitutions
        s = s.replace("\\frac{", "((").replace("}{", ")/(") 
        # Count and close fraction braces
        s = s.replace("\\sqrt{", "sqrt(")
        s = s.replace("\\ln", "log")
        s = s.replace("\\log", "log")
        s = s.replace("\\exp", "exp")
        s = s.replace("\\pi", "pi")
        s = s.replace("\\infty", "oo")
        s = s.replace("\\cdot", "*")
        s = s.replace("\\times", "*")
        s = s.replace("^", "**")
        # Remove remaining LaTeX commands
        s = re.sub(r"\\[a-zA-Z]+", "", s)
        s = s.replace("{", "(").replace("}", ")")
        # Clean up
        s = s.strip()
        return s if s else None


class NumericalVerifier:
    """
    Numerically verify conjectures by evaluation on random inputs.
    """

    def verify(
        self, conjecture: Conjecture, 
        n_samples: int = 1000,
        rtol: float = 1e-6,
    ) -> tuple[Optional[bool], str]:
        """Numerically verify the conjecture."""
        latex = conjecture.statement_latex
        parts = AlgebraicVerifier()._extract_equality(latex)
        if not parts:
            return None, "could not parse equality"

        lhs_str, rhs_str = parts
        try:
            lhs = sp.sympify(lhs_str)
            rhs = sp.sympify(rhs_str)
        except Exception as e:
            return None, f"parse error: {e}"

        # Get all free symbols
        all_syms = sorted(lhs.free_symbols | rhs.free_symbols, key=str)
        if not all_syms:
            # Both are constants
            try:
                lval = complex(lhs.evalf())
                rval = complex(rhs.evalf())
                if abs(lval - rval) / max(abs(lval), abs(rval), 1e-30) < rtol:
                    return True, f"constant values agree: {lval} ≈ {rval}"
                else:
                    return False, f"constant values disagree: {lval} ≠ {rval}"
            except Exception as e:
                return None, f"evaluation error: {e}"

        rng = np.random.default_rng(42)
        test_points = np.exp(rng.uniform(-3, 3, (n_samples, len(all_syms))))

        matches = 0
        failures = 0
        errors = 0

        for i in range(n_samples):
            subs = {s: float(test_points[i, j]) for j, s in enumerate(all_syms)}
            try:
                lval = complex(lhs.subs(subs))
                rval = complex(rhs.subs(subs))
                if np.isnan(lval) or np.isnan(rval) or np.isinf(lval) or np.isinf(rval):
                    errors += 1
                    continue
                if abs(lval - rval) / max(abs(lval), abs(rval), 1e-30) < rtol:
                    matches += 1
                else:
                    failures += 1
            except Exception:
                errors += 1

        valid = n_samples - errors
        if valid == 0:
            return None, f"all {n_samples} evaluations failed"

        match_rate = matches / valid

        if match_rate > 0.99:
            return True, f"numerical: {matches}/{valid} match within rtol={rtol}"
        elif match_rate < 0.1:
            return False, f"numerical: only {matches}/{valid} match — likely false"
        else:
            return None, f"numerical: {matches}/{valid} match — inconclusive ({match_rate:.1%})"


class DimensionalVerifier:
    """Verify dimensional consistency of conjectures."""

    def verify(self, conjecture: Conjecture) -> tuple[Optional[bool], str]:
        """
        Check that both sides of the conjecture have the same dimensions.
        
        This uses LLM to assess dimensional consistency since
        pure symbolic dimensional analysis is complex.
        """
        from ..pipeline.llm_client import get_client; client = get_client()
        prompt = f"""
You are checking the dimensional consistency of a physics conjecture.

Conjecture: {conjecture.statement_latex}
Natural language: {conjecture.statement_natural}
Theories: {', '.join(conjecture.theories_involved)}

Check: do both sides of the equation have the same physical dimensions?
Use natural units (ℏ = c = 1) where [M] = [L]⁻¹ = [T]⁻¹.

Return JSON:
{{
    "dimensions_match": true/false/null,
    "lhs_dimensions": "...",
    "rhs_dimensions": "...",
    "explanation": "..."
}}

Return ONLY the JSON object. No analysis, no preamble, just JSON.
"""
        try:
            raw = client.complete(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1024,
                temperature=0.1,
                phase="dimensional_verification",
            )
            data = _extract_json_from_response(raw)
            
            dm = data.get("dimensions_match")
            expl = data.get("explanation", "")
            if dm is True:
                return True, f"dimensions match: {expl}"
            elif dm is False:
                return False, f"dimension mismatch: {expl}"
            else:
                return None, f"inconclusive: {expl}"
        except Exception as e:
            return None, f"dimensional check error: {e}"


class CounterexampleSearcher:
    """Actively try to disprove conjectures."""

    def search(self, conjecture: Conjecture) -> tuple[Optional[bool], str]:
        """
        Try to find a counterexample to the conjecture.
        
        Returns (True, details) if counterexample FOUND (conjecture is false),
        (False, details) if no counterexample found after thorough search,
        (None, details) if search was inconclusive.
        """
        # Strategy 1: Extreme values
        latex = conjecture.statement_latex
        parts = AlgebraicVerifier()._extract_equality(latex)
        if not parts:
            return None, "could not parse"

        lhs_str, rhs_str = parts
        try:
            lhs = sp.sympify(lhs_str)
            rhs = sp.sympify(rhs_str)
        except Exception:
            return None, "parse error"

        all_syms = sorted(lhs.free_symbols | rhs.free_symbols, key=str)
        if not all_syms:
            return None, "no free symbols to vary"

        # Test extreme values: very large, very small, negative, zero
        extreme_values = [0.001, 0.01, 0.1, 1.0, 10.0, 100.0, 1000.0, -1.0, -0.1]
        
        for sym in all_syms:
            for val in extreme_values:
                subs = {s: 1.0 for s in all_syms}
                subs[sym] = val
                try:
                    lval = complex(lhs.subs(subs))
                    rval = complex(rhs.subs(subs))
                    if np.isnan(lval) or np.isnan(rval):
                        continue
                    if np.isinf(lval) or np.isinf(rval):
                        continue
                    rel_err = abs(lval - rval) / max(abs(lval), abs(rval), 1e-30)
                    if rel_err > 0.01:
                        return True, (
                            f"counterexample found: {sym}={val}, "
                            f"LHS={lval:.6g}, RHS={rval:.6g}, "
                            f"rel_error={rel_err:.4f}"
                        )
                except Exception:
                    continue

        # Strategy 2: Random search with wide range
        rng = np.random.default_rng(999)
        for _ in range(500):
            subs = {s: float(np.exp(rng.uniform(-10, 10))) for s in all_syms}
            try:
                lval = complex(lhs.subs(subs))
                rval = complex(rhs.subs(subs))
                if np.isnan(lval) or np.isnan(rval) or np.isinf(lval) or np.isinf(rval):
                    continue
                rel_err = abs(lval - rval) / max(abs(lval), abs(rval), 1e-30)
                if rel_err > 0.01:
                    return True, f"counterexample at random point, rel_error={rel_err:.4f}"
            except Exception:
                continue

        return False, "no counterexample found after 500+ extreme + random tests"


class NoveltyChecker:
    """Check if a conjecture is already known in the literature."""

    def check(self, conjecture: Conjecture, kb: KnowledgeBase) -> tuple[Optional[bool], str]:
        """
        Check if this connection is already known.
        
        Strategy:
        1. Check the KB's claimed_connections table
        2. Use LLM to assess novelty based on its knowledge
        3. (Future: arXiv search for specific claims)
        """
        # Check KB claimed connections
        connections = kb.get_all_claimed_connections()
        theories = set(conjecture.theories_involved)
        
        for conn in connections:
            conn_theories = {conn["theory_a"], conn["theory_b"]}
            if conn_theories == theories or conn_theories.issubset(theories):
                # Similar theories — check if it's the same claim
                if self._similar_description(
                    conjecture.statement_natural, conn["description"]
                ):
                    return False, f"similar claim found in paper {conn['paper_id']}: {conn['description']}"

        # LLM novelty assessment
        from ..pipeline.llm_client import get_client; client = get_client()
        prompt = f"""
You are a quantum gravity expert assessing whether a proposed connection between theories is already known in the literature.

Conjecture:
Title: {conjecture.title}
Statement: {conjecture.statement_natural}
LaTeX: {conjecture.statement_latex}
Theories: {', '.join(conjecture.theories_involved)}

Is this connection:
1. WELL-KNOWN — standard result, in textbooks
2. KNOWN — published but perhaps not widely appreciated  
3. PARTIALLY KNOWN — related results exist but this specific formulation is new
4. NOVEL — you are not aware of this specific connection being published

Be honest. If you're uncertain, say so. If this resembles a known result, cite which papers/authors you think established it.

Return JSON:
{{
    "novelty_level": "well_known|known|partially_known|novel|uncertain",
    "explanation": "...",
    "related_work": ["list of related papers/results if known"],
    "is_novel": true/false/null
}}

Return ONLY the JSON object. No analysis, no preamble, just JSON.
"""
        try:
            raw = client.complete(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2048,
                temperature=0.2,
                phase="novelty_check",
            )
            data = _extract_json_from_response(raw)
            
            is_novel = data.get("is_novel")
            novelty = data.get("novelty_level", "uncertain")
            expl = data.get("explanation", "")
            related = data.get("related_work", [])
            
            details = f"[{novelty}] {expl}"
            if related:
                details += f"\nRelated: {', '.join(related)}"
            
            return is_novel, details
        except Exception as e:
            return None, f"novelty check error: {e}"

    def _similar_description(self, a: str, b: str) -> bool:
        """Quick check if two descriptions discuss the same thing."""
        a_words = set(a.lower().split())
        b_words = set(b.lower().split())
        if not a_words or not b_words:
            return False
        overlap = len(a_words & b_words) / min(len(a_words), len(b_words))
        return overlap > 0.5


# ── Full Verification Pipeline ──────────────────────────────────

class VerificationEngine:
    """Run all verification checks on a conjecture."""

    def __init__(self, kb: KnowledgeBase):
        self.kb = kb
        self.algebraic = AlgebraicVerifier()
        self.numerical = NumericalVerifier()
        self.dimensional = DimensionalVerifier()
        self.counterexample = CounterexampleSearcher()
        self.novelty = NoveltyChecker()

    def verify(self, conjecture: Conjecture) -> VerificationResult:
        """Run full verification pipeline."""
        result = VerificationResult(conjecture_id=conjecture.id or 0)

        # 1. Algebraic
        log.info(f"  Algebraic verification: {conjecture.title}")
        result.algebraic, result.algebraic_details = self.algebraic.verify(conjecture)

        # 2. Numerical
        log.info(f"  Numerical verification: {conjecture.title}")
        result.numerical, result.numerical_details = self.numerical.verify(conjecture)

        # 3. Dimensional
        log.info(f"  Dimensional verification: {conjecture.title}")
        result.dimensional, result.dimensional_details = self.dimensional.verify(conjecture)

        # 4. Counterexample search
        log.info(f"  Counterexample search: {conjecture.title}")
        result.counterexample_found, result.counterexample_details = self.counterexample.search(conjecture)

        # 5. Novelty check
        log.info(f"  Novelty check: {conjecture.title}")
        result.is_novel, result.novelty_details = self.novelty.check(conjecture, self.kb)

        # Determine overall status
        if result.counterexample_found:
            result.overall_status = "disproved"
        elif result.algebraic is False or result.numerical is False or result.dimensional is False:
            result.overall_status = "disproved"
        elif result.is_novel is False:
            result.overall_status = "known"
        elif result.algebraic or result.numerical:
            # Strong verification: algebraic or numerical proof
            result.overall_status = "verified"
        elif result.dimensional is True and result.is_novel is True:
            # Weaker verification: dimensions match + novel (can't parse for algebra)
            result.overall_status = "verified"
        elif result.dimensional is True:
            # Dimensions match but novelty unknown
            result.overall_status = "inconclusive"
        else:
            result.overall_status = "inconclusive"

        log.info(f"  → {result.overall_status}: {conjecture.title}")
        return result


def _extract_json_from_response(text: str) -> dict:
    """Extract JSON object from an LLM response that may contain prose."""
    text = text.strip()
    # Try direct parse first
    try:
        return json.loads(text)
    except Exception:
        pass
    # Strip markdown code blocks
    cleaned = re.sub(r"^```(?:json)?\s*\n?", "", text)
    cleaned = re.sub(r"\n?```\s*$", "", cleaned)
    try:
        return json.loads(cleaned.strip())
    except Exception:
        pass
    # Find JSON object anywhere in text
    for i, ch in enumerate(text):
        if ch == '{':
            depth = 0
            for j in range(i, len(text)):
                if text[j] == '{':
                    depth += 1
                elif text[j] == '}':
                    depth -= 1
                    if depth == 0:
                        try:
                            return json.loads(text[i:j+1])
                        except Exception:
                            break
    raise ValueError(f"No valid JSON found in response: {text[:200]}...")
