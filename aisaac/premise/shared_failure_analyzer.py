"""
Shared Failure Analyzer.

Finds what ALL approaches to a problem have in common.
The shared assumptions across every failed approach are
candidates for being WRONG — this is the key insight that
drives paradigm shifts.

Historical precedent: before Einstein, every theory of
electrodynamics assumed the aether existed. The shared
assumption was the wrong one.
"""
from __future__ import annotations

import json
import logging
import re
from collections import defaultdict
from dataclasses import dataclass, field

from ..knowledge.base import KnowledgeBase
from ..pipeline.llm_client import get_client

log = logging.getLogger(__name__)


# ── Prompts ───────────────────────────────────────────────────────

FILTER_EMPIRICAL_PROMPT = """\
You are a philosopher of physics evaluating whether foundational assumptions \
are empirically verified or merely conventional.

## Shared Assumptions (found in ALL quantum gravity approaches)
{assumptions_text}

## Task
For each assumption, determine:
1. Is it **empirically verified** at the energy scales relevant to quantum gravity?
   - "verified" = direct experimental confirmation exists (e.g., "spacetime has 4 dimensions at large scales")
   - "extrapolated" = verified at low energy but assumed to hold at Planck scale (e.g., "Lorentz invariance is exact")
   - "conventional" = a mathematical/conceptual choice, not tested (e.g., "spacetime is a manifold")
   - "unverifiable" = cannot currently be tested

2. How "droppable" is it? (0.0 = bedrock, 1.0 = easily dropped)
   Consider: how many theoretical structures would break if you dropped it?

3. What specific changes would follow if this assumption is wrong?
   Be concrete — name which theories would be affected and how.

Return a JSON array:
[
  {{
    "assumption_text": "...",
    "empirical_status": "verified | extrapolated | conventional | unverifiable",
    "droppability_score": 0.0-1.0,
    "droppability_reasoning": "why this score",
    "if_dropped": "concrete description of what changes",
    "affected_theories": ["list", "of", "theory_slugs"],
    "historical_analog": "if any historical precedent exists for dropping a similar assumption"
  }}
]

Return ONLY the JSON array.
"""

COMPARE_SUCCESS_PROMPT = """\
You are analyzing WHY a partially successful approach differs from failed ones \
in quantum gravity research.

## Partially Successful Approach: {success_theory}
Its assumptions:
{success_assumptions}

## Failed Approaches and Their Assumptions
{failed_text}

## Assumptions the Successful Approach Does NOT Share
{unique_to_success}

## Assumptions the Failed Approaches Share but the Successful One Lacks
{missing_from_success}

## Task
Analyze the difference. Why might the successful approach work better?
Focus on the assumptions it DROPPED or REPLACED compared to the failed ones.

Return JSON:
{{
  "key_differentiators": [
    {{
      "assumption_dropped": "what the successful approach doesn't assume",
      "replacement": "what it assumes instead (if anything)",
      "why_it_matters": "why this might explain the partial success",
      "lesson_for_field": "what other approaches could learn from this"
    }}
  ],
  "shared_baggage": [
    "assumptions the successful approach STILL shares with failed ones — these might still be wrong"
  ],
  "recommendation": "one-paragraph synthesis"
}}

Return ONLY the JSON object.
"""


# ── Data Classes ──────────────────────────────────────────────────

@dataclass
class SharedAssumption:
    """An assumption shared across multiple theories."""
    assumption_text: str
    theories: list[str]
    empirical_status: str = "unknown"
    droppability_score: float = 0.0
    droppability_reasoning: str = ""
    if_dropped: str = ""
    affected_theories: list[str] = field(default_factory=list)
    historical_analog: str = ""


@dataclass
class FailureAnalysisResult:
    """Result of analyzing shared failures across approaches."""
    all_theories: list[str]
    shared_assumptions: list[SharedAssumption]
    droppable_candidates: list[SharedAssumption]
    empirically_verified: list[SharedAssumption]
    comparison_result: dict = field(default_factory=dict)


# ── Analyzer ──────────────────────────────────────────────────────

class SharedFailureAnalyzer:
    """Identifies shared assumptions across all QG approaches — candidates for being wrong."""

    def __init__(self, kb: KnowledgeBase):
        self.kb = kb
        self.client = get_client()

    def find_shared_assumptions(
        self,
        min_theory_fraction: float = 0.8,
    ) -> FailureAnalysisResult:
        """Find assumptions shared by most or all theories.

        Parameters
        ----------
        min_theory_fraction:
            Fraction of theories that must share an assumption for it to
            count as "shared".  1.0 = unanimous; 0.8 = 80 % of theories.

        Returns
        -------
        FailureAnalysisResult with shared assumptions ranked by droppability.
        """
        # Step 1: Get all assumptions grouped by theory
        assumptions_by_theory = self._get_assumptions_by_theory()
        all_theories = sorted(assumptions_by_theory.keys())

        if len(all_theories) < 2:
            log.warning("Fewer than 2 theories have assumptions — nothing to compare")
            return FailureAnalysisResult(
                all_theories=all_theories,
                shared_assumptions=[],
                droppable_candidates=[],
                empirically_verified=[],
            )

        log.info(
            f"Analyzing assumptions across {len(all_theories)} theories: "
            f"{', '.join(all_theories)}"
        )

        # Step 2: Compute intersection — assumptions shared across theories
        min_theories = max(2, int(len(all_theories) * min_theory_fraction))
        shared = self._compute_shared_assumptions(assumptions_by_theory, min_theories)

        if not shared:
            log.info("No shared assumptions found across theories")
            return FailureAnalysisResult(
                all_theories=all_theories,
                shared_assumptions=[],
                droppable_candidates=[],
                empirically_verified=[],
            )

        log.info(f"Found {len(shared)} assumptions shared by >= {min_theories} theories")

        # Step 3: Use LLM to filter out empirically verified ones and rank
        ranked = self._filter_and_rank(shared)

        # Step 4: Separate empirically verified from droppable candidates
        verified = [a for a in ranked if a.empirical_status == "verified"]
        droppable = [
            a for a in ranked
            if a.empirical_status != "verified" and a.droppability_score > 0.3
        ]
        droppable.sort(key=lambda a: a.droppability_score, reverse=True)

        log.info(
            f"Results: {len(verified)} verified, "
            f"{len(droppable)} droppable candidates"
        )

        # Step 5: Store top droppable candidates as obstacles
        for assumption in droppable[:10]:
            self.kb.insert_obstacle(
                theory_slug="all",
                obstacle_type="shared_assumption",
                description=assumption.assumption_text,
                paper_ids="[]",
                is_universal=1,
                what_it_might_mean=(
                    f"Droppability: {assumption.droppability_score:.2f}. "
                    f"{assumption.if_dropped}"
                ),
            )

        return FailureAnalysisResult(
            all_theories=all_theories,
            shared_assumptions=ranked,
            droppable_candidates=droppable,
            empirically_verified=verified,
        )

    def compare_with_successful(
        self,
        success_theory: str,
        success_metric: str = "partial progress",
    ) -> dict:
        """Compare a partially successful approach against failed ones.

        If some approach partially succeeded, what assumptions does it
        NOT share with the approaches that failed?

        Parameters
        ----------
        success_theory:
            The theory_slug of the partially successful approach.
        success_metric:
            Description of what "success" means here.

        Returns
        -------
        dict with key_differentiators, shared_baggage, and recommendation.
        """
        assumptions_by_theory = self._get_assumptions_by_theory()

        if success_theory not in assumptions_by_theory:
            log.error(f"Theory '{success_theory}' not found in knowledge base")
            return {"error": f"No assumptions found for {success_theory}"}

        success_texts = {
            a["assumption_text"] for a in assumptions_by_theory[success_theory]
        }
        failed_theories = {
            t: a for t, a in assumptions_by_theory.items() if t != success_theory
        }

        if not failed_theories:
            log.warning("No other theories to compare against")
            return {"error": "No other theories for comparison"}

        # Assumptions in ALL failed theories but NOT in the successful one
        failed_text_sets = {}
        for theory, assumptions in failed_theories.items():
            failed_text_sets[theory] = {a["assumption_text"] for a in assumptions}

        # Intersection of all failed theories' assumptions
        if failed_text_sets:
            common_in_failed = set.intersection(*failed_text_sets.values())
        else:
            common_in_failed = set()

        missing_from_success = common_in_failed - success_texts
        unique_to_success = success_texts - common_in_failed

        # Build the prompt
        success_assumptions_text = "\n".join(
            f"- {a['assumption_text']}" for a in assumptions_by_theory[success_theory]
        )
        failed_text = ""
        for theory, assumptions in failed_theories.items():
            failed_text += f"\n### {theory}\n"
            for a in assumptions[:15]:
                failed_text += f"- {a['assumption_text']}\n"

        prompt = COMPARE_SUCCESS_PROMPT.format(
            success_theory=success_theory,
            success_assumptions=success_assumptions_text,
            failed_text=failed_text,
            unique_to_success="\n".join(f"- {t}" for t in unique_to_success) or "(none)",
            missing_from_success="\n".join(f"- {t}" for t in missing_from_success) or "(none)",
        )

        try:
            raw = self.client.complete(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
                phase="shared_failure_comparison",
            )
            raw = _extract_json(raw)
            result = json.loads(raw)
        except Exception as e:
            log.error(f"Comparison analysis failed: {e}")
            return {"error": str(e)}

        log.info(
            f"Comparison complete: {len(result.get('key_differentiators', []))} "
            f"differentiators found"
        )
        return result

    # ── Private Helpers ───────────────────────────────────────────

    def _get_assumptions_by_theory(self) -> dict[str, list[dict]]:
        """Retrieve all assumptions from the KB, grouped by theory_slug."""
        all_assumptions = self.kb.get_assumptions()
        by_theory: dict[str, list[dict]] = defaultdict(list)
        for a in all_assumptions:
            by_theory[a["theory_slug"]].append(a)
        return dict(by_theory)

    def _compute_shared_assumptions(
        self,
        by_theory: dict[str, list[dict]],
        min_theories: int,
    ) -> list[SharedAssumption]:
        """Find assumptions that appear across multiple theories.

        Uses normalized text matching — two assumptions count as "the same"
        if their texts are semantically similar.  We do an initial pass by
        exact-lowered match, then group the remainder with the LLM.
        """
        # Build a mapping: normalized_text -> list of theories
        text_to_theories: dict[str, set[str]] = defaultdict(set)
        text_to_original: dict[str, str] = {}

        for theory, assumptions in by_theory.items():
            for a in assumptions:
                normalized = a["assumption_text"].strip().lower()
                text_to_theories[normalized].add(theory)
                # Keep the best-looking original
                if normalized not in text_to_original or len(a["assumption_text"]) > len(text_to_original[normalized]):
                    text_to_original[normalized] = a["assumption_text"]

        # Filter to those meeting the threshold
        shared = []
        for normalized, theories in text_to_theories.items():
            if len(theories) >= min_theories:
                shared.append(SharedAssumption(
                    assumption_text=text_to_original[normalized],
                    theories=sorted(theories),
                ))

        # If exact matching finds too few, try semantic grouping via LLM
        if len(shared) < 3 and len(by_theory) >= 2:
            log.info("Few exact matches — attempting semantic grouping via LLM")
            semantic_shared = self._semantic_group_assumptions(by_theory, min_theories)
            # Merge, avoiding duplicates
            existing_texts = {s.assumption_text.lower() for s in shared}
            for sa in semantic_shared:
                if sa.assumption_text.lower() not in existing_texts:
                    shared.append(sa)
                    existing_texts.add(sa.assumption_text.lower())

        return shared

    def _semantic_group_assumptions(
        self,
        by_theory: dict[str, list[dict]],
        min_theories: int,
    ) -> list[SharedAssumption]:
        """Use LLM to find semantically equivalent assumptions across theories."""
        # Build a compact representation
        theory_assumptions = ""
        for theory, assumptions in by_theory.items():
            theory_assumptions += f"\n## {theory}\n"
            for a in assumptions[:20]:
                theory_assumptions += f"- {a['assumption_text']}\n"

        prompt = (
            "You are comparing assumptions across quantum gravity theories.\n\n"
            f"{theory_assumptions}\n\n"
            "## Task\n"
            "Find assumptions that are SEMANTICALLY THE SAME across multiple theories, "
            "even if worded differently.\n"
            "For example, 'spacetime is continuous' and 'the manifold is smooth' "
            "express the same assumption.\n\n"
            "Return a JSON array of shared assumptions:\n"
            "[\n"
            '  {\n'
            '    "canonical_text": "the shared assumption stated clearly",\n'
            '    "theories": ["theory_slug_1", "theory_slug_2", ...],\n'
            '    "variants": ["how theory A states it", "how theory B states it"]\n'
            "  }\n"
            "]\n\n"
            "Only include assumptions shared by at least "
            f"{min_theories} theories. Return ONLY the JSON array."
        )

        try:
            raw = self.client.complete(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                phase="semantic_assumption_grouping",
            )
            raw = _extract_json(raw)
            groups = json.loads(raw)
        except Exception as e:
            log.error(f"Semantic grouping failed: {e}")
            return []

        if not isinstance(groups, list):
            return []

        results = []
        for g in groups:
            theories = g.get("theories", [])
            if len(theories) >= min_theories:
                results.append(SharedAssumption(
                    assumption_text=g.get("canonical_text", ""),
                    theories=sorted(theories),
                ))
        return results

    def _filter_and_rank(
        self,
        shared: list[SharedAssumption],
    ) -> list[SharedAssumption]:
        """Use LLM to classify empirical status and rank droppability."""
        assumptions_text = ""
        for i, sa in enumerate(shared, 1):
            assumptions_text += (
                f"{i}. \"{sa.assumption_text}\" "
                f"(shared by: {', '.join(sa.theories)})\n"
            )

        prompt = FILTER_EMPIRICAL_PROMPT.format(assumptions_text=assumptions_text)

        try:
            raw = self.client.complete(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                phase="shared_failure_ranking",
            )
            raw = _extract_json(raw)
            ranked_data = json.loads(raw)
        except Exception as e:
            log.error(f"Ranking failed: {e}")
            return shared  # Return unranked

        if not isinstance(ranked_data, list):
            return shared

        # Map LLM results back onto SharedAssumption objects
        by_text = {sa.assumption_text.lower(): sa for sa in shared}

        for item in ranked_data:
            text = item.get("assumption_text", "").lower()
            sa = by_text.get(text)
            if sa is None:
                # Fuzzy match: find closest
                for key, candidate in by_text.items():
                    if key in text or text in key:
                        sa = candidate
                        break
            if sa is None:
                continue

            sa.empirical_status = item.get("empirical_status", "unknown")
            sa.droppability_score = float(item.get("droppability_score", 0.0))
            sa.droppability_reasoning = item.get("droppability_reasoning", "")
            sa.if_dropped = item.get("if_dropped", "")
            sa.affected_theories = item.get("affected_theories", [])
            sa.historical_analog = item.get("historical_analog", "")

        return shared


# ── Utility ───────────────────────────────────────────────────────

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
