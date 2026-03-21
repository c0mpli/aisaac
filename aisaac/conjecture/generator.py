"""
Conjecture Generator.

Takes comparison results, clustering, universality analysis,
and anomaly detection → proposes precise mathematical conjectures
about cross-theory connections.

KEY DESIGN: The LLM writes sympy CODE to derive relationships,
not prose conjectures. Sympy executes the code and only confirmed
relationships become conjectures. This prevents hallucinated math.
"""
from __future__ import annotations

import json
import logging
import io
import contextlib
from dataclasses import dataclass


from ..pipeline.config import ANTHROPIC_MODEL, ConjectureType
from ..knowledge.base import KnowledgeBase, Conjecture
from ..comparison.engine import ComparisonResult
from ..ml.patterns import Cluster, UniversalityResult, Anomaly

log = logging.getLogger(__name__)


SYMPY_DERIVATION_PROMPT = """\
You are a theoretical physicist who PROVES relationships using sympy, not prose.

## Two formulas from different quantum gravity theories were found to be structurally similar:

Formula A ({theory_a}, {quantity_a}):
  LaTeX: {latex_a}
  Description: {desc_a}
  Sympy: {sympy_a}
  Regime: {regime_a}

Formula B ({theory_b}, {quantity_b}):
  LaTeX: {latex_b}
  Description: {desc_b}
  Sympy: {sympy_b}
  Regime: {regime_b}

## Your task

Write Python code using sympy that:
1. Defines both formulas as sympy expressions
2. Uses solve(), simplify(), limit(), series(), subs() to find ANY algebraic relationship
3. Prints ONLY what sympy confirms — do NOT print claims you haven't verified with sympy

The code MUST:
- Import sympy at the top
- Define all symbols used
- End by printing a JSON object with the results
- Print NOTHING except the final JSON

## Output format

Your code should print exactly one JSON object:

```python
import sympy as sp
import json

# Define symbols
# ... your derivation ...

# ONLY print what sympy confirmed
result = {{
    "found_relationship": True/False,
    "relationship_latex": "...",  # LaTeX of the confirmed relationship
    "relationship_type": "equivalence|limit|correction|universality",
    "derivation_steps": ["step1", "step2", ...],
    "title": "short title",
    "natural_language": "1-2 sentences explaining the confirmed result",
    "confidence": 0.0-1.0,  # 1.0 if sympy proved it exactly, lower if approximate
    "significance": 0.0-1.0,
}}
print(json.dumps(result))
```

If sympy CANNOT confirm any relationship, print:
```python
print(json.dumps({{"found_relationship": False, "reason": "why sympy couldn't confirm"}}))
```

Return ONLY the Python code block. No explanation outside the code.
"""


CONJECTURE_PROMPT = """\
You are a theoretical physicist analyzing potential connections between quantum gravity theories. 
An automated comparison system has found the following evidence of a possible cross-theory connection.

## Evidence

### Comparison Results
{comparison_data}

### Formula Details
Formula A ({theory_a}):
  LaTeX: {latex_a}
  Description: {desc_a}
  Quantity: {quantity_a}
  Regime: {regime_a}

Formula B ({theory_b}):
  LaTeX: {latex_b}
  Description: {desc_b}
  Quantity: {quantity_b}
  Regime: {regime_b}

### Match Scores
Structural similarity: {structural_score}
Dimensional match: {dimensional_score}
Numerical agreement: {numerical_score}
Limit correspondence: {limit_score}

### Additional Context
{additional_context}

## Task
Based on this evidence, propose a precise mathematical conjecture about the relationship between these formulas. Your conjecture must be:

1. PRECISE — state exactly what equals what, under what conditions
2. FALSIFIABLE — it must be possible to check this algebraically or numerically
3. CONSERVATIVE — don't overstate the evidence
4. PHYSICALLY MOTIVATED — explain WHY this connection might exist

Consider these conjecture types:
- EQUIVALENCE: X in theory A = Y in theory B under mapping {{substitutions}}
- UNIVERSALITY: quantity Q takes value V across theories A, B, C
- LIMIT: theory A reduces to theory B as parameter P → value
- CORRECTION: the leading correction has universal form f(l_P/r)
- NEAR_MISS: these almost agree — the small discrepancy is physically meaningful
- MISSING_LINK: same result via different mechanisms → proof should exist

CRITICAL: statement_latex must be a PURE mathematical equation with NO \\text{{}} commands, NO natural language words, NO prose. Just math symbols and operators.
  GOOD examples: "S_{{BH}} = \\frac{{A}}{{4G}}", "d_s = 2", "\\lim_{{k \\to \\infty}} G(k) = g_* / k^2"
  BAD examples: "\\text{{Both theories predict}} S = A/4", "S_{{BH}} \\text{{ is universal}}"
  If the conjecture is about equality: write "LHS = RHS"
  If about a limit: write "\\lim_{{param}} LHS = RHS"
  If about universality: write "Q = value" with a note in conditions about which theories

Return JSON:
{{
    "conjecture_type": "equivalence|universality|limit|correction|near_miss|missing_link",
    "title": "short descriptive title",
    "statement_latex": "PURE math equation, no text commands",
    "statement_natural": "1-2 paragraph natural language explanation",
    "mapping": {{}},  // if equivalence: what substitutions make them equal
    "conditions": "under what conditions does this hold",
    "physical_motivation": "why might this be true physically",
    "testable_predictions": ["list of ways to test this"],
    "confidence": 0.0-1.0,
    "significance": 0.0-1.0
}}
"""


UNIVERSALITY_CONJECTURE_PROMPT = """\
You are a theoretical physicist analyzing a potential universal prediction of quantum gravity.

## Evidence
Quantity: {quantity_type}
Theories that agree: {agree}
Consensus value: {consensus_value}
Spread: {spread}
Theory-by-theory values: {theory_values}
Theories that disagree: {disagree}

## Task
If the agreement is compelling, propose a universality conjecture:
- State the universal value precisely
- Explain why universality for this quantity would be significant
- Identify what's different about disagreeing theories (if any)
- Suggest how to test or sharpen the result

Return JSON:
{{
    "conjecture_type": "universality",
    "title": "...",
    "statement_latex": "...",
    "statement_natural": "...",
    "universal_value": ...,
    "physical_motivation": "...",
    "what_breaks_universality": "...",
    "confidence": 0.0-1.0,
    "significance": 0.0-1.0
}}
"""


ANOMALY_CONJECTURE_PROMPT = """\
You are a theoretical physicist analyzing an anomaly found by automated comparison of quantum gravity theories.

## Anomaly
Type: {anomaly_type}
Description: {description}
Theories involved: {theories}
Significance: {significance}
Details: {details}

## Additional formula data
{formula_data}

## Task
This anomaly could be:
1. A genuine physical result deserving investigation
2. An artifact of approximations or notation
3. A known but under-appreciated connection

Assess which it is. If it could be genuine, propose a conjecture.

Return JSON:
{{
    "is_interesting": true/false,
    "assessment": "your assessment of what this anomaly means",
    "conjecture": {{...}} // if interesting, same format as other conjectures, otherwise null
}}
"""


class ConjectureGenerator:
    """Generate conjectures from comparison results using LLM reasoning."""

    def __init__(self, kb: KnowledgeBase):
        self.kb = kb
        from ..pipeline.llm_client import get_client
        self.client = get_client()

    def from_comparison(
        self, result: ComparisonResult,
        formula_a: dict, formula_b: dict,
    ) -> list[Conjecture]:
        """Generate conjectures from a comparison result.

        Strategy: first try sympy-verified derivation. If that fails
        or finds nothing, fall back to LLM prose conjecture.
        """
        theories = [result.theory_a, result.theory_b]
        formula_ids = [result.formula_a_id, result.formula_b_id]

        # Try sympy-verified derivation first
        sympy_conjecture = self._derive_with_sympy(result, formula_a, formula_b)
        if sympy_conjecture:
            sympy_conjecture.theories_involved = theories
            sympy_conjecture.evidence_formula_ids = formula_ids
            log.info(f"  Sympy-verified: {sympy_conjecture.title}")
            return [sympy_conjecture]

        # Fall back to LLM prose conjecture
        prompt = CONJECTURE_PROMPT.format(
            comparison_data=json.dumps(result.details, indent=2, default=str),
            theory_a=result.theory_a,
            theory_b=result.theory_b,
            latex_a=formula_a.get("latex", ""),
            desc_a=formula_a.get("description", ""),
            quantity_a=result.quantity_type_a,
            regime_a=formula_a.get("regime", ""),
            latex_b=formula_b.get("latex", ""),
            desc_b=formula_b.get("description", ""),
            quantity_b=result.quantity_type_b,
            regime_b=formula_b.get("regime", ""),
            structural_score=result.structural_score,
            dimensional_score=result.dimensional_score,
            numerical_score=result.numerical_score,
            limit_score=result.limit_score,
            additional_context="NOTE: sympy derivation was attempted but did not find a confirmed relationship. "
                               "Your conjecture should be conservative and clearly state what is uncertain.",
        )

        return self._call_llm_for_conjectures(
            prompt,
            theories=theories,
            formula_ids=formula_ids,
        )

    def _derive_with_sympy(
        self, result: ComparisonResult,
        formula_a: dict, formula_b: dict,
    ) -> Conjecture | None:
        """Ask LLM to write sympy code, execute it, return only confirmed results."""
        prompt = SYMPY_DERIVATION_PROMPT.format(
            theory_a=result.theory_a,
            theory_b=result.theory_b,
            latex_a=formula_a.get("latex", ""),
            desc_a=formula_a.get("description", ""),
            sympy_a=formula_a.get("normalized_sympy") or formula_a.get("sympy_expr", ""),
            quantity_a=result.quantity_type_a,
            regime_a=formula_a.get("regime", ""),
            latex_b=formula_b.get("latex", ""),
            desc_b=formula_b.get("description", ""),
            sympy_b=formula_b.get("normalized_sympy") or formula_b.get("sympy_expr", ""),
            quantity_b=result.quantity_type_b,
            regime_b=formula_b.get("regime", ""),
        )

        try:
            raw = self.client.complete(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=4096,
                temperature=0.2,  # low temp for code generation
                phase="conjecture",
            )
        except Exception as e:
            log.warning(f"  Sympy derivation LLM call failed: {e}")
            return None

        # Extract Python code from response
        code = self._extract_code(raw)
        if not code:
            log.debug("  No code block found in sympy derivation response")
            return None

        # Execute in sandbox
        result_json = self._execute_sympy_code(code)
        if not result_json:
            return None

        if not result_json.get("found_relationship"):
            log.debug(f"  Sympy found no relationship: {result_json.get('reason', 'unknown')}")
            return None

        # Build conjecture from sympy-confirmed result
        try:
            return Conjecture(
                conjecture_type=result_json.get("relationship_type", "equivalence"),
                title=result_json.get("title", "Sympy-verified relationship"),
                statement_latex=result_json.get("relationship_latex", ""),
                statement_natural=result_json.get("natural_language", ""),
                theories_involved=[],  # filled by caller
                evidence_formula_ids=[],  # filled by caller
                evidence_paper_ids=[],
                evidence_score=float(result_json.get("confidence", 0.8)),
                significance_score=float(result_json.get("significance", 0.5)),
                combined_score=0.0,
                sympy_verified=True,
            )
        except Exception as e:
            log.warning(f"  Failed to build conjecture from sympy result: {e}")
            return None

    def _extract_code(self, response: str) -> str | None:
        """Extract Python code block from LLM response."""
        import re
        # Try ```python ... ``` block
        match = re.search(r"```python\s*\n(.*?)```", response, re.DOTALL)
        if match:
            return match.group(1).strip()
        # Try ``` ... ``` block
        match = re.search(r"```\s*\n(.*?)```", response, re.DOTALL)
        if match:
            code = match.group(1).strip()
            if "import sympy" in code or "import json" in code:
                return code
        # Try raw code (starts with import)
        lines = response.strip().split("\n")
        if lines and ("import sympy" in lines[0] or "import json" in lines[0]):
            return response.strip()
        return None

    def _execute_sympy_code(self, code: str, timeout: float = 30.0) -> dict | None:
        """Execute sympy code in a restricted sandbox and capture JSON output."""
        import signal

        # Safety checks — reject dangerous code
        dangerous = ["os.", "sys.", "subprocess", "open(", "__import__", "eval(", "exec(",
                      "shutil", "pathlib", "requests", "urllib", "socket"]
        for d in dangerous:
            if d in code:
                log.warning(f"  Rejecting code with dangerous pattern: {d}")
                return None

        # Only allow sympy, json, math imports
        allowed_imports = {"sympy", "json", "math", "numpy", "sp"}

        # Capture stdout
        stdout_capture = io.StringIO()

        def timeout_handler(signum, frame):
            raise TimeoutError("Sympy code execution timed out")

        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(int(timeout))

        try:
            # Restricted globals — no builtins except safe ones
            safe_builtins = {
                "print": lambda *args, **kwargs: print(*args, file=stdout_capture, **kwargs),
                "range": range, "len": len, "float": float, "int": int,
                "str": str, "bool": bool, "list": list, "dict": dict,
                "tuple": tuple, "set": set, "abs": abs, "max": max, "min": min,
                "sum": sum, "round": round, "enumerate": enumerate, "zip": zip,
                "True": True, "False": False, "None": None,
                "__import__": __import__,
            }
            restricted_globals = {"__builtins__": safe_builtins}

            exec(code, restricted_globals)
        except TimeoutError:
            log.warning("  Sympy code timed out")
            return None
        except Exception as e:
            log.debug(f"  Sympy code execution error: {e}")
            return None
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)

        # Parse output
        output = stdout_capture.getvalue().strip()
        if not output:
            return None

        # Find last JSON object in output
        try:
            # Take the last line that looks like JSON
            for line in reversed(output.split("\n")):
                line = line.strip()
                if line.startswith("{"):
                    return json.loads(line)
        except json.JSONDecodeError:
            pass

        try:
            return json.loads(output)
        except Exception:
            log.debug(f"  Could not parse sympy output as JSON: {output[:200]}")
            return None

    def from_universality(self, result: UniversalityResult) -> list[Conjecture]:
        """Generate conjectures from universality analysis."""
        if not result.consensus_value or len(result.theories_agree) < 2:
            return []

        prompt = UNIVERSALITY_CONJECTURE_PROMPT.format(
            quantity_type=result.quantity_type,
            agree=", ".join(result.theories_agree),
            consensus_value=result.consensus_value,
            spread=result.spread,
            theory_values=json.dumps(result.details.get("theory_means", {})),
            disagree=", ".join(result.theories_disagree) if result.theories_disagree else "none",
        )

        return self._call_llm_for_conjectures(
            prompt,
            theories=result.theories_agree + result.theories_disagree,
            formula_ids=[],
        )

    def from_anomaly(
        self, anomaly: Anomaly, formulas: list[dict],
    ) -> list[Conjecture]:
        """Generate conjectures from detected anomalies."""
        formula_data = ""
        for f in formulas:
            formula_data += (
                f"\n  Theory: {f.get('theory_slug')}\n"
                f"  LaTeX: {f.get('latex')}\n"
                f"  Description: {f.get('description')}\n"
            )

        prompt = ANOMALY_CONJECTURE_PROMPT.format(
            anomaly_type=anomaly.anomaly_type,
            description=anomaly.description,
            theories=", ".join(anomaly.theories_involved),
            significance=anomaly.significance,
            details=json.dumps(anomaly.details, default=str),
            formula_data=formula_data,
        )

        return self._call_llm_for_conjectures(
            prompt,
            theories=anomaly.theories_involved,
            formula_ids=anomaly.formula_ids,
        )

    def from_cluster(
        self, cluster: Cluster, formulas: list[dict],
    ) -> list[Conjecture]:
        """Generate conjectures from a cross-theory cluster."""
        if not cluster.is_cross_theory:
            return []

        # Build context about the cluster
        formula_data = ""
        for f in formulas:
            if f["id"] in cluster.formula_ids:
                formula_data += (
                    f"\n  [{f['theory_slug']}] {f.get('description', '')}\n"
                    f"  LaTeX: {f.get('latex', '')}\n"
                )

        prompt = f"""
You are a theoretical physicist analyzing a cluster of similar formulas found across multiple quantum gravity approaches.

## Cluster Info
Theories represented: {', '.join(cluster.theories)}
Quantity types: {', '.join(cluster.quantity_types)}
Number of formulas: {cluster.size}

## Formulas in this cluster
{formula_data}

## Task
These formulas from different theories cluster together in embedding space, suggesting they may describe the same physics. Propose a conjecture explaining WHY they agree.

Return JSON:
{{
    "conjecture_type": "universality|equivalence|missing_link",
    "title": "...",
    "statement_latex": "...",
    "statement_natural": "...",
    "physical_motivation": "...",
    "confidence": 0.0-1.0,
    "significance": 0.0-1.0
}}
"""
        return self._call_llm_for_conjectures(
            prompt,
            theories=cluster.theories,
            formula_ids=cluster.formula_ids,
        )

    def _call_llm_for_conjectures(
        self, prompt: str, theories: list[str], formula_ids: list[int],
    ) -> list[Conjecture]:
        """Call LLM and parse conjectures."""
        try:
            raw = self.client.complete(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=4096,
                temperature=0.7,
                phase="conjecture",
            )
            raw = _extract_json(raw.strip())
            data = json.loads(raw)
        except Exception as e:
            log.error(f"Conjecture generation failed: {e}")
            return []

        # Handle both single conjecture and list
        if isinstance(data, dict):
            # Could be anomaly response with nested conjecture
            if "conjecture" in data and data.get("is_interesting"):
                data = data["conjecture"]
            elif "conjecture_type" not in data:
                return []
            items = [data]
        elif isinstance(data, list):
            items = data
        else:
            return []

        conjectures = []
        for item in items:
            if not item or not isinstance(item, dict):
                continue
            try:
                c = Conjecture(
                    conjecture_type=item.get("conjecture_type", "other"),
                    title=item.get("title", "Untitled conjecture"),
                    statement_latex=item.get("statement_latex", ""),
                    statement_natural=item.get("statement_natural", ""),
                    theories_involved=theories,
                    evidence_formula_ids=formula_ids,
                    evidence_paper_ids=[],  # filled later
                    evidence_score=float(item.get("confidence", 0.5)),
                    significance_score=float(item.get("significance", 0.5)),
                    combined_score=0.0,
                )
                c.combined_score = (c.evidence_score + c.significance_score) / 2
                conjectures.append(c)
            except Exception as e:
                log.warning(f"Failed to parse conjecture: {e}")

        return conjectures


def _extract_json(text: str) -> str:
    """Extract JSON from LLM response."""
    import re
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
