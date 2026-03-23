"""
Obstacle Cataloger.

Maps what blocks each approach to quantum gravity.
If every approach hits the SAME wall, the wall is the clue.

Key insight: a universal obstacle isn't a random difficulty —
it's a signal that everyone is making the same wrong assumption.
When every path through a forest hits the same river, maybe
you're supposed to build a boat, not find a bridge.
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

OBSTACLE_EXTRACTION_PROMPT = """\
You are analyzing a physics paper to identify obstacles, open problems, \
and limitations that the authors acknowledge or that are implied.

## Paper Info
Title: {title}
Authors: {authors}
Year: {year}
Theory: {theory_slug}
Abstract: {abstract}

## Paper Content
{content}

## Task
Extract every obstacle, limitation, open problem, or difficulty mentioned \
or implied in this paper.

Look for signals like:
- "however", "remains unclear", "open problem", "does not yet"
- "challenge", "difficulty", "limitation", "obstacle"
- "future work", "not yet resolved", "beyond the scope"
- "breaks down", "diverges", "ill-defined", "ambiguous"
- "no known method", "unresolved", "problematic"

For each obstacle, provide:
- "description": Clear 1-2 sentence description of the obstacle
- "obstacle_type": one of:
    - "mathematical": a formal/technical barrier (e.g., non-renormalizability)
    - "conceptual": a foundational or interpretive issue (e.g., problem of time)
    - "computational": too hard to compute in practice
    - "empirical": no way to test with current experiments
    - "consistency": internal contradictions or tensions
- "severity": "blocking" (stops progress entirely) | "major" (serious impediment) | "minor" (annoyance)
- "is_explicitly_stated": true if the paper directly mentions it, false if inferred
- "relevant_quote": short quote from the text if applicable, else ""
- "related_to_assumptions": list of assumptions this obstacle might stem from
- "confidence": 0.0-1.0

Return ONLY a JSON array. Extract ALL obstacles, even minor ones.
"""

UNIVERSALITY_ANALYSIS_PROMPT = """\
You are analyzing obstacles across ALL quantum gravity approaches to find \
universal patterns.

## Obstacles by Theory

{obstacles_text}

## Task
1. Group obstacles that are essentially THE SAME problem appearing in different theories.
   Example: "non-renormalizability in perturbative QG" and "UV divergences in \
graviton scattering" are the same fundamental obstacle.

2. For each universal obstacle (appearing in 3+ theories), analyze:
   - What assumption might be CAUSING this obstacle?
   - What if the obstacle is not a bug but a FEATURE — a signal that \
our framework is wrong?
   - Historical parallel: has physics seen this pattern before?

Return JSON:
{{
  "universal_obstacles": [
    {{
      "canonical_description": "the obstacle stated clearly",
      "theories_affected": ["list", "of", "theory_slugs"],
      "theory_specific_versions": {{
        "theory_slug": "how this theory encounters it"
      }},
      "possible_root_assumption": "the shared assumption that might cause this",
      "what_if_feature": "reinterpretation: what if this obstacle is telling us something?",
      "historical_parallel": "similar pattern in history of physics (if any)",
      "severity": "blocking | major | minor"
    }}
  ],
  "theory_specific_obstacles": [
    {{
      "theory_slug": "...",
      "description": "obstacle unique to this theory",
      "might_indicate": "what this tells us about this approach specifically"
    }}
  ],
  "meta_analysis": "1-2 paragraph synthesis of what the obstacle landscape tells us"
}}

Return ONLY the JSON object.
"""


# ── Data Classes ──────────────────────────────────────────────────

@dataclass
class Obstacle:
    """A single obstacle extracted from a paper."""
    theory_slug: str
    description: str
    obstacle_type: str
    severity: str = "major"
    is_explicitly_stated: bool = True
    relevant_quote: str = ""
    related_to_assumptions: list[str] = field(default_factory=list)
    confidence: float = 0.5
    paper_ids: list[int] = field(default_factory=list)


@dataclass
class UniversalObstacle:
    """An obstacle shared across multiple theories."""
    canonical_description: str
    theories_affected: list[str]
    theory_specific_versions: dict[str, str]
    possible_root_assumption: str
    what_if_feature: str
    historical_parallel: str
    severity: str


@dataclass
class ObstacleCatalog:
    """Full catalog of obstacles across all theories."""
    obstacles_by_theory: dict[str, list[Obstacle]]
    universal_obstacles: list[UniversalObstacle]
    theory_specific_obstacles: list[dict]
    meta_analysis: str


# ── Cataloger ─────────────────────────────────────────────────────

class ObstacleCataloger:
    """Extracts and catalogs obstacles across all QG approaches."""

    def __init__(self, kb: KnowledgeBase):
        self.kb = kb
        self.client = get_client()

    def extract_from_paper(self, paper: dict, content: str = "") -> list[Obstacle]:
        """Extract obstacles from a single paper.

        Parameters
        ----------
        paper:
            Paper dict from the knowledge base (must include ``id``).
        content:
            Full text or abstract of the paper.  When empty, falls back
            to title + abstract from the paper dict itself.

        Returns
        -------
        List of extracted :class:`Obstacle` objects (also stored in the KB).
        """
        title = paper.get("title", "")
        theory_tags = paper.get("theory_tags", [])
        if isinstance(theory_tags, str):
            theory_tags = json.loads(theory_tags)
        theory_slug = theory_tags[0] if theory_tags else "unknown"
        paper_id = paper.get("id", 0)

        if not content:
            content = f"Title: {title}\n\nAbstract: {paper.get('abstract', '')}"

        # Truncate content to fit context window
        max_chars = 60_000
        if len(content) > max_chars:
            third = max_chars // 3
            content = content[:third] + "\n\n[...truncated...]\n\n" + content[-third:]

        prompt = OBSTACLE_EXTRACTION_PROMPT.format(
            title=title,
            authors=paper.get("authors", ""),
            year=paper.get("year", ""),
            theory_slug=theory_slug,
            abstract=paper.get("abstract", ""),
            content=content,
        )

        try:
            raw = self.client.complete(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                phase="obstacle_extraction",
            )
            raw = _extract_json(raw.strip())
            obstacles_data = json.loads(raw)
        except Exception as e:
            log.error(f"Obstacle extraction failed for '{title}': {e}")
            return []

        if not isinstance(obstacles_data, list):
            return []

        results = []
        for od in obstacles_data:
            try:
                description = od.get("description", "")
                if not description:
                    continue

                obstacle = Obstacle(
                    theory_slug=theory_slug,
                    description=description,
                    obstacle_type=od.get("obstacle_type", "conceptual"),
                    severity=od.get("severity", "major"),
                    is_explicitly_stated=od.get("is_explicitly_stated", True),
                    relevant_quote=od.get("relevant_quote", ""),
                    related_to_assumptions=od.get("related_to_assumptions", []),
                    confidence=float(od.get("confidence", 0.5)),
                    paper_ids=[paper_id],
                )

                self.kb.insert_obstacle(
                    theory_slug=theory_slug,
                    obstacle_type=obstacle.obstacle_type,
                    description=obstacle.description,
                    paper_ids=json.dumps([paper_id]),
                    is_universal=0,
                    what_it_might_mean="",
                )

                results.append(obstacle)
            except Exception as e:
                log.warning(f"Failed to store obstacle: {e}")
                continue

        log.info(f"Extracted {len(results)} obstacles from '{title}'")
        return results

    def extract_all_unprocessed(self) -> int:
        """Extract obstacles from all papers not yet processed.

        Returns
        -------
        Total number of obstacles extracted.
        """
        # Identify papers already processed by checking existing obstacles
        existing = self.kb.get_obstacles()
        processed_paper_ids: set[int] = set()
        for obs in existing:
            pids = obs.get("paper_ids", "[]")
            if isinstance(pids, str):
                pids = json.loads(pids)
            processed_paper_ids.update(pids)

        all_papers = self.kb.conn.execute("SELECT * FROM papers").fetchall()
        unprocessed = [dict(p) for p in all_papers if p["id"] not in processed_paper_ids]

        log.info(f"Extracting obstacles from {len(unprocessed)} papers...")
        total = 0

        for i, paper in enumerate(unprocessed):
            log.info(f"  [{i + 1}/{len(unprocessed)}] {paper['title'][:60]}...")
            results = self.extract_from_paper(paper)
            total += len(results)

        # Mark universal obstacles via simple heuristic before LLM analysis
        self._mark_universal()

        log.info(f"Total obstacles extracted: {total}")
        return total

    def analyze_universality(self) -> ObstacleCatalog:
        """Analyze all obstacles for universal patterns.

        Groups obstacles by theory, asks the LLM to find universal
        obstacles (same wall across different approaches), and returns
        a full catalog.

        Returns
        -------
        :class:`ObstacleCatalog` with universal and theory-specific obstacles.
        """
        # Load all obstacles from the KB
        all_obstacles = self.kb.get_obstacles()
        if not all_obstacles:
            log.warning("No obstacles in knowledge base — run extraction first")
            return ObstacleCatalog(
                obstacles_by_theory={},
                universal_obstacles=[],
                theory_specific_obstacles=[],
                meta_analysis="No obstacles cataloged yet.",
            )

        # Group by theory
        by_theory: dict[str, list[dict]] = defaultdict(list)
        for obs in all_obstacles:
            by_theory[obs["theory_slug"]].append(obs)

        log.info(
            f"Analyzing {len(all_obstacles)} obstacles across "
            f"{len(by_theory)} theories"
        )

        # Build text for the LLM
        obstacles_text = ""
        for theory, obs_list in sorted(by_theory.items()):
            obstacles_text += f"\n## {theory} ({len(obs_list)} obstacles)\n"
            for obs in obs_list[:20]:
                obstacles_text += (
                    f"- [{obs.get('obstacle_type', '?')}] "
                    f"{obs['description']}\n"
                )

        prompt = UNIVERSALITY_ANALYSIS_PROMPT.format(obstacles_text=obstacles_text)

        try:
            raw = self.client.complete(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
                phase="obstacle_universality",
            )
            raw = _extract_json(raw.strip())
            analysis = json.loads(raw)
        except Exception as e:
            log.error(f"Universality analysis failed: {e}")
            return ObstacleCatalog(
                obstacles_by_theory=self._to_obstacle_dict(by_theory),
                universal_obstacles=[],
                theory_specific_obstacles=[],
                meta_analysis=f"Analysis failed: {e}",
            )

        # Parse universal obstacles
        universal = []
        for uo in analysis.get("universal_obstacles", []):
            universal_obs = UniversalObstacle(
                canonical_description=uo.get("canonical_description", ""),
                theories_affected=uo.get("theories_affected", []),
                theory_specific_versions=uo.get("theory_specific_versions", {}),
                possible_root_assumption=uo.get("possible_root_assumption", ""),
                what_if_feature=uo.get("what_if_feature", ""),
                historical_parallel=uo.get("historical_parallel", ""),
                severity=uo.get("severity", "major"),
            )
            universal.append(universal_obs)

            # Store universal obstacles in the KB
            self.kb.insert_obstacle(
                theory_slug="all",
                obstacle_type="universal",
                description=universal_obs.canonical_description,
                paper_ids="[]",
                is_universal=1,
                what_it_might_mean=(
                    f"Root assumption: {universal_obs.possible_root_assumption}. "
                    f"What if feature: {universal_obs.what_if_feature}"
                ),
            )

        theory_specific = analysis.get("theory_specific_obstacles", [])
        meta = analysis.get("meta_analysis", "")

        log.info(
            f"Found {len(universal)} universal obstacles, "
            f"{len(theory_specific)} theory-specific obstacles"
        )

        return ObstacleCatalog(
            obstacles_by_theory=self._to_obstacle_dict(by_theory),
            universal_obstacles=universal,
            theory_specific_obstacles=theory_specific,
            meta_analysis=meta,
        )

    # ── Private Helpers ───────────────────────────────────────────

    def _mark_universal(self):
        """Mark obstacles that appear across 3+ theories as universal.

        This is a fast heuristic pass that groups by obstacle_type.
        The full semantic analysis is done by :meth:`analyze_universality`.
        """
        obstacles = self.kb.get_obstacles()
        by_type: dict[str, set[str]] = defaultdict(set)
        for o in obstacles:
            by_type[o["obstacle_type"]].add(o["theory_slug"])

        for obs_type, theories in by_type.items():
            if len(theories) >= 3:
                self.kb.conn.execute(
                    "UPDATE obstacles SET is_universal = 1 WHERE obstacle_type = ?",
                    (obs_type,),
                )
        self.kb.conn.commit()

    def _to_obstacle_dict(
        self,
        by_theory: dict[str, list[dict]],
    ) -> dict[str, list[Obstacle]]:
        """Convert raw KB rows into Obstacle dataclass instances."""
        result: dict[str, list[Obstacle]] = {}
        for theory, obs_list in by_theory.items():
            result[theory] = []
            for obs in obs_list:
                paper_ids_raw = obs.get("paper_ids", "[]")
                if isinstance(paper_ids_raw, str):
                    paper_ids_raw = json.loads(paper_ids_raw)

                result[theory].append(Obstacle(
                    theory_slug=theory,
                    description=obs["description"],
                    obstacle_type=obs.get("obstacle_type", "conceptual"),
                    paper_ids=paper_ids_raw,
                ))
        return result


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
