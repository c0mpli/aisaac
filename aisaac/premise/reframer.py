"""
Premise Reframer — the creative agent.

Generates premise shifts by applying 5 historical breakthrough patterns
to contradictions, convergences, shared failures, and obstacles found
in the knowledge base.

The patterns:
  1. UNIFICATION — "What if these two things are the same?"
  2. CONTRADICTION EMBRACE — "If both sides are right, what gives?"
  3. RADICAL SUBTRACTION — "What assumption can we drop?"
  4. OBSTACLE INVERSION — "What if the obstacle IS the answer?"
  5. EQUIVALENCE — "Why does the same answer appear from different starts?"

Design principle: prompts must be SPECIFIC and BOLD.
Not "maybe gravity is different."
Instead: "Drop the assumption that the metric is the fundamental variable."
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Optional

from ..knowledge.base import KnowledgeBase
from ..pipeline.llm_client import get_client

log = logging.getLogger(__name__)


# ── Breakthrough Patterns ────────────────────────────────────────

@dataclass
class BreakthroughPattern:
    name: str
    slug: str
    question: str
    description: str
    historical_example: str


PATTERNS = [
    BreakthroughPattern(
        name="Unification",
        slug="unification",
        question="What if these two things are the same?",
        description=(
            "Two phenomena that appear unrelated turn out to be "
            "manifestations of a single deeper structure."
        ),
        historical_example=(
            "Maxwell unifying electricity and magnetism; "
            "Maldacena identifying gauge theory with gravity (AdS/CFT)."
        ),
    ),
    BreakthroughPattern(
        name="Contradiction Embrace",
        slug="contradiction_embrace",
        question="If both sides are right, what gives?",
        description=(
            "Two results seem to contradict each other, but both are "
            "well-established. The resolution forces a new concept."
        ),
        historical_example=(
            "Wave-particle duality: light is both wave and particle. "
            "Resolution required quantum mechanics."
        ),
    ),
    BreakthroughPattern(
        name="Radical Subtraction",
        slug="radical_subtraction",
        question="What assumption can we drop?",
        description=(
            "Progress is blocked because everyone assumes X. "
            "Dropping X opens entirely new territory."
        ),
        historical_example=(
            "Einstein dropping absolute simultaneity → special relativity. "
            "Shannon abstracting meaning from communication → information theory."
        ),
    ),
    BreakthroughPattern(
        name="Obstacle Inversion",
        slug="obstacle_inversion",
        question="What if the obstacle IS the answer?",
        description=(
            "A persistent technical problem is not a bug but a feature — "
            "the obstacle itself encodes new physics."
        ),
        historical_example=(
            "Dirac's negative energy solutions were 'the problem' until "
            "he realized they predicted antimatter. "
            "Perelman classified Ricci flow singularities instead of avoiding them."
        ),
    ),
    BreakthroughPattern(
        name="Equivalence",
        slug="equivalence",
        question="Why does the same answer appear from different starts?",
        description=(
            "Multiple independent approaches converge on the same result. "
            "This coincidence demands an explanation — there must be a deeper reason."
        ),
        historical_example=(
            "Spectral dimension → 2 appears in LQG, CDT, asymptotic safety, "
            "causal sets, Horava-Lifshitz. Why? "
            "Boltzmann and Gibbs arriving at the same entropy formula from "
            "different axioms → statistical mechanics is inevitable."
        ),
    ),
]

PATTERN_BY_SLUG = {p.slug: p for p in PATTERNS}


# ── Input Types ──────────────────────────────────────────────────

@dataclass
class ReframerInput:
    """Structured input for the reframer from the knowledge base."""
    problem: str
    contradictions: list[dict]
    convergences: list[dict]
    shared_assumptions: list[dict]
    obstacles: list[dict]


# ── Prompts ──────────────────────────────────────────────────────

REFRAME_SYSTEM = """\
You are a theoretical physicist with the creativity of Einstein, \
the rigor of Witten, and the audacity of Dirac. Your job is to \
propose BOLD premise shifts that could break open stalled problems \
in quantum gravity.

Rules:
- Be SPECIFIC. Not "maybe gravity is different." Instead: \
"Drop the assumption that the metric is the fundamental variable. \
Replace it with the causal structure of the conformal class."
- Be PRECISE. State exactly what assumption you are questioning \
and exactly what replaces it.
- Be BOLD. The shift should feel uncomfortable — if it's obvious, \
it's not a premise shift.
- Cite the specific physics that motivates the shift.
- For each shift, state what BREAKS if you're wrong (falsifiability).
"""

REFRAME_PROMPT = """\
## Problem
{problem}

## Breakthrough Pattern: {pattern_name}
Core question: {pattern_question}
Description: {pattern_description}
Historical example: {pattern_example}

## Evidence from the Literature

### Contradictions
{contradictions_text}

### Convergent Results
{convergences_text}

### Shared Assumptions (across approaches)
{assumptions_text}

### Obstacles
{obstacles_text}

## Task
Apply the "{pattern_name}" pattern to this problem and evidence.

Generate 1-3 premise shifts. For EACH shift, provide:
1. CURRENT PREMISE: The assumption everyone currently makes (be specific)
2. PROPOSED SHIFT: What to replace it with (be specific and bold)
3. EVIDENCE FOR: What existing results support this shift
4. EVIDENCE AGAINST: What could disprove it
5. AFFECTED THEORIES: Which QG approaches would be impacted
6. HISTORICAL ANALOG: Which historical breakthrough does this most resemble
7. WHAT BREAKS: What established result would fail if this shift is wrong

Return a JSON array:
[
  {{
    "current_premise": "...",
    "proposed_shift": "...",
    "evidence_for": "...",
    "evidence_against": "...",
    "affected_theories": ["theory_slug_1", "theory_slug_2"],
    "historical_analog": "...",
    "what_breaks": "..."
  }}
]

Be BOLD. The best premise shifts feel wrong at first.
"""


# ── Reframer ─────────────────────────────────────────────────────

class PremiseReframer:
    """
    The creative agent. Generates premise shifts by applying
    5 historical breakthrough patterns to evidence from the KB.
    """

    def __init__(self, kb: KnowledgeBase):
        self.kb = kb
        self.client = get_client()

    def gather_inputs(self, problem: str) -> ReframerInput:
        """Gather all relevant evidence from the KB for a given problem."""
        contradictions = self.kb.get_contradictions()
        obstacles = self.kb.get_obstacles()
        assumptions = self.kb.get_assumptions()

        # Convergences: conjectures with type 'universality' or status 'verified'
        conjectures = self.kb.get_conjectures()
        convergences = [
            c for c in conjectures
            if c.get("conjecture_type") == "universality"
            or c.get("status") == "verified"
        ]

        # Shared assumptions: assumptions that appear across multiple theories
        assumption_texts: dict[str, list[str]] = {}
        for a in assumptions:
            text = a.get("assumption_text", "").strip().lower()
            if text:
                assumption_texts.setdefault(text, []).append(
                    a.get("theory_slug", "unknown")
                )
        shared = [
            {"assumption_text": text, "theories": list(set(theories))}
            for text, theories in assumption_texts.items()
            if len(set(theories)) >= 2
        ]

        return ReframerInput(
            problem=problem,
            contradictions=contradictions,
            convergences=convergences,
            shared_assumptions=shared,
            obstacles=obstacles,
        )

    def generate_shifts(
        self,
        problem: str,
        patterns: list[str] | None = None,
        max_per_pattern: int = 3,
    ) -> list[dict]:
        """
        Generate premise shifts for a problem using all (or selected) patterns.

        Args:
            problem: The physics problem/question to reframe.
            patterns: List of pattern slugs to use. None = all 5.
            max_per_pattern: Max shifts per pattern (LLM may return fewer).

        Returns:
            List of premise shift dicts (also inserted into KB).
        """
        inputs = self.gather_inputs(problem)
        selected = (
            [PATTERN_BY_SLUG[s] for s in patterns if s in PATTERN_BY_SLUG]
            if patterns
            else PATTERNS
        )

        all_shifts: list[dict] = []
        for pattern in selected:
            log.info(
                "Applying pattern '%s' to problem: %s",
                pattern.name, problem[:80],
            )
            shifts = self._apply_pattern(pattern, inputs)
            for shift in shifts[:max_per_pattern]:
                shift_id = self._store_shift(problem, pattern, shift)
                shift["id"] = shift_id
                shift["shift_type"] = pattern.slug
                shift["problem"] = problem
                all_shifts.append(shift)
            log.info(
                "  Pattern '%s' produced %d shifts", pattern.name, len(shifts),
            )

        log.info(
            "Total premise shifts generated: %d (problem: %s)",
            len(all_shifts), problem[:60],
        )
        return all_shifts

    def _apply_pattern(
        self, pattern: BreakthroughPattern, inputs: ReframerInput,
    ) -> list[dict]:
        """Apply a single breakthrough pattern and return shifts."""
        prompt = REFRAME_PROMPT.format(
            problem=inputs.problem,
            pattern_name=pattern.name,
            pattern_question=pattern.question,
            pattern_description=pattern.description,
            pattern_example=pattern.historical_example,
            contradictions_text=self._format_contradictions(inputs.contradictions),
            convergences_text=self._format_convergences(inputs.convergences),
            assumptions_text=self._format_assumptions(inputs.shared_assumptions),
            obstacles_text=self._format_obstacles(inputs.obstacles),
        )

        try:
            data = self.client.complete_json(
                messages=[{"role": "user", "content": prompt}],
                system=REFRAME_SYSTEM,
                max_tokens=4096,
                temperature=0.8,  # higher temp for creativity
                phase="premise_reframe",
            )
        except Exception as e:
            log.error("Reframe LLM call failed for pattern '%s': %s", pattern.name, e)
            return []

        if isinstance(data, dict):
            data = [data]
        if not isinstance(data, list):
            log.warning("Unexpected LLM response type: %s", type(data))
            return []

        shifts = []
        for item in data:
            if not isinstance(item, dict):
                continue
            if not item.get("current_premise") or not item.get("proposed_shift"):
                continue
            shifts.append(item)

        return shifts

    def _store_shift(
        self, problem: str, pattern: BreakthroughPattern, shift: dict,
    ) -> int:
        """Insert a premise shift into the knowledge base."""
        affected = shift.get("affected_theories", [])
        if isinstance(affected, list):
            affected_json = json.dumps(affected)
        else:
            affected_json = json.dumps([str(affected)])

        return self.kb.insert_premise_shift(
            problem=problem,
            current_premise=shift.get("current_premise", ""),
            proposed_shift=shift.get("proposed_shift", ""),
            shift_type=pattern.slug,
            evidence_for=shift.get("evidence_for", ""),
            evidence_against=shift.get("evidence_against", ""),
            affected_theories=affected_json,
            historical_analog=shift.get("historical_analog", ""),
            score=0.0,  # scored later by premise_ranker
        )

    # ── Formatting helpers ───────────────────────────────────────

    @staticmethod
    def _format_contradictions(contradictions: list[dict]) -> str:
        if not contradictions:
            return "No contradictions recorded yet."
        lines = []
        for c in contradictions[:10]:
            lines.append(
                f"- [{c.get('theory_a', '?')} vs {c.get('theory_b', '?')}] "
                f"{c.get('description', 'no description')} "
                f"(severity: {c.get('severity', 'unknown')})"
            )
        return "\n".join(lines)

    @staticmethod
    def _format_convergences(convergences: list[dict]) -> str:
        if not convergences:
            return "No convergent results recorded yet."
        lines = []
        for c in convergences[:10]:
            theories = c.get("theories_involved", "[]")
            if isinstance(theories, str):
                try:
                    theories = json.loads(theories)
                except (json.JSONDecodeError, TypeError):
                    theories = [theories]
            lines.append(
                f"- {c.get('title', 'Untitled')}: "
                f"{c.get('statement_natural', 'no description')} "
                f"(theories: {', '.join(theories) if isinstance(theories, list) else theories})"
            )
        return "\n".join(lines)

    @staticmethod
    def _format_assumptions(shared: list[dict]) -> str:
        if not shared:
            return "No shared assumptions identified yet."
        lines = []
        for a in shared[:15]:
            theories = a.get("theories", [])
            lines.append(
                f"- \"{a.get('assumption_text', '?')}\" "
                f"(shared by: {', '.join(theories)})"
            )
        return "\n".join(lines)

    @staticmethod
    def _format_obstacles(obstacles: list[dict]) -> str:
        if not obstacles:
            return "No obstacles recorded yet."
        lines = []
        for o in obstacles[:10]:
            lines.append(
                f"- [{o.get('theory_slug', '?')}] {o.get('obstacle_type', '?')}: "
                f"{o.get('description', 'no description')}"
            )
        return "\n".join(lines)
