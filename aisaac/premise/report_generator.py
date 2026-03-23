"""
Premise Report Generator.

Generates structured reports for a given problem/question, pulling
together convergences, shared assumptions, top-ranked premise shifts,
contradictions, obstacles, and open calculations.

Output formats: rich console (via print) and markdown string.
The final narrative summary uses the LLM; everything else is
assembled from the knowledge base.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..knowledge.base import KnowledgeBase
from ..pipeline.llm_client import get_client

log = logging.getLogger(__name__)


# ── LLM Prompt for Narrative Summary ─────────────────────────────

NARRATIVE_PROMPT = """\
You are a theoretical physicist writing a concise, insightful summary \
of the current state of a problem in quantum gravity.

## Problem
{problem}

## Data

### Convergent Results
{convergences}

### Shared Assumptions
{assumptions}

### Top Premise Shifts (ranked by computational score)
{shifts}

### Key Contradictions
{contradictions}

### Key Obstacles
{obstacles}

## Task

Write a 3-5 paragraph narrative summary that:
1. States the problem clearly
2. Identifies the most interesting premise shift and WHY it's promising
3. Connects the evidence: which convergences support which shifts?
4. Names the biggest obstacle and whether any shift addresses it
5. Suggests 2-3 specific OPEN CALCULATIONS that nobody has done \
   but that could confirm or refute the top premise shift

Be specific. Name theories, quantities, and parameters.
Do NOT hedge with "it might be interesting to..." — state what should be done.
"""


# ── Report Generator ─────────────────────────────────────────────

class PremiseReportGenerator:
    """
    Generate structured premise reports for a problem.

    Pulls data from the KB and assembles:
      1. Convergent results
      2. Shared assumptions
      3. Top-ranked premise shifts
      4. Contradictions
      5. Obstacles
      6. Open calculations (LLM-generated)

    Outputs both rich console text and markdown.
    """

    def __init__(self, kb: KnowledgeBase, use_llm_narrative: bool = True):
        self.kb = kb
        self.use_llm_narrative = use_llm_narrative
        if use_llm_narrative:
            self.client = get_client()
        else:
            self.client = None

    def generate(
        self,
        problem: str,
        top_n_shifts: int = 5,
        output_path: Optional[str | Path] = None,
    ) -> str:
        """
        Generate a full premise report as markdown.

        Args:
            problem: The physics problem/question.
            top_n_shifts: How many top-ranked shifts to include.
            output_path: If provided, write markdown to this file.

        Returns:
            The report as a markdown string.
        """
        log.info("Generating premise report for: %s", problem[:80])

        sections = self._gather_sections(problem, top_n_shifts)
        markdown = self._render_markdown(problem, sections)

        if output_path:
            path = Path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(markdown, encoding="utf-8")
            log.info("Report written to %s", path)

        return markdown

    def print_report(
        self,
        problem: str,
        top_n_shifts: int = 5,
    ) -> str:
        """
        Print a rich console report and return the markdown.
        """
        sections = self._gather_sections(problem, top_n_shifts)
        self._print_console(problem, sections)
        return self._render_markdown(problem, sections)

    # ── Data Gathering ───────────────────────────────────────────

    def _gather_sections(
        self, problem: str, top_n_shifts: int,
    ) -> dict:
        """Gather all report sections from the KB."""
        # 1. Convergences
        conjectures = self.kb.get_conjectures()
        convergences = [
            c for c in conjectures
            if c.get("conjecture_type") == "universality"
            or c.get("status") == "verified"
        ]

        # 2. Shared assumptions
        assumptions = self.kb.get_assumptions()
        assumption_groups = self._find_shared_assumptions(assumptions)

        # 3. Top premise shifts
        shifts = self.kb.get_premise_shifts(min_score=0.0)
        top_shifts = shifts[:top_n_shifts]

        # 4. Contradictions
        contradictions = self.kb.get_contradictions()

        # 5. Obstacles
        obstacles = self.kb.get_obstacles()

        # 6. Narrative summary with open calculations (LLM)
        narrative = ""
        if self.use_llm_narrative and self.client:
            narrative = self._generate_narrative(
                problem, convergences, assumption_groups,
                top_shifts, contradictions, obstacles,
            )

        return {
            "convergences": convergences,
            "assumptions": assumption_groups,
            "shifts": top_shifts,
            "contradictions": contradictions,
            "obstacles": obstacles,
            "narrative": narrative,
        }

    def _find_shared_assumptions(
        self, assumptions: list[dict],
    ) -> list[dict]:
        """Group assumptions that appear across multiple theories."""
        by_text: dict[str, list[str]] = {}
        by_text_full: dict[str, dict] = {}
        for a in assumptions:
            text = a.get("assumption_text", "").strip().lower()
            if not text:
                continue
            by_text.setdefault(text, []).append(a.get("theory_slug", "unknown"))
            if text not in by_text_full:
                by_text_full[text] = a

        shared = []
        for text, theories in by_text.items():
            unique_theories = list(set(theories))
            if len(unique_theories) >= 2:
                full = by_text_full[text]
                shared.append({
                    "assumption_text": full.get("assumption_text", text),
                    "theories": unique_theories,
                    "category": full.get("category", ""),
                    "how_fundamental": full.get("how_fundamental", ""),
                })
        # Sort by number of theories sharing the assumption
        shared.sort(key=lambda x: len(x["theories"]), reverse=True)
        return shared

    # ── Narrative (LLM) ─────────────────────────────────────────

    def _generate_narrative(
        self,
        problem: str,
        convergences: list[dict],
        assumptions: list[dict],
        shifts: list[dict],
        contradictions: list[dict],
        obstacles: list[dict],
    ) -> str:
        """Use the LLM to write a narrative summary with open calculations."""
        prompt = NARRATIVE_PROMPT.format(
            problem=problem,
            convergences=self._fmt_convergences(convergences),
            assumptions=self._fmt_assumptions(assumptions),
            shifts=self._fmt_shifts(shifts),
            contradictions=self._fmt_contradictions(contradictions),
            obstacles=self._fmt_obstacles(obstacles),
        )

        try:
            return self.client.complete(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=4096,
                temperature=0.4,
                phase="premise_report",
            ).strip()
        except Exception as e:
            log.error("Narrative generation failed: %s", e)
            return f"[Narrative generation failed: {e}]"

    # ── Markdown Rendering ───────────────────────────────────────

    def _render_markdown(self, problem: str, sections: dict) -> str:
        """Render the full report as markdown."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        lines: list[str] = []

        lines.append(f"# Premise Report: {problem}")
        lines.append(f"*Generated {now}*")
        lines.append("")

        # Narrative summary
        if sections["narrative"]:
            lines.append("## Executive Summary")
            lines.append("")
            lines.append(sections["narrative"])
            lines.append("")

        # 1. Convergent results
        lines.append("## 1. Convergent Results")
        lines.append("")
        if sections["convergences"]:
            for i, c in enumerate(sections["convergences"], 1):
                theories = c.get("theories_involved", "[]")
                if isinstance(theories, str):
                    try:
                        theories = json.loads(theories)
                    except (json.JSONDecodeError, TypeError):
                        theories = [theories]
                theory_str = ", ".join(theories) if isinstance(theories, list) else str(theories)
                lines.append(
                    f"{i}. **{c.get('title', 'Untitled')}** "
                    f"({c.get('conjecture_type', '?')})"
                )
                lines.append(f"   - Theories: {theory_str}")
                lines.append(f"   - {c.get('statement_natural', 'No description')}")
                if c.get("statement_latex"):
                    lines.append(f"   - LaTeX: `{c['statement_latex']}`")
                lines.append(
                    f"   - Evidence: {c.get('evidence_score', 0):.2f} | "
                    f"Significance: {c.get('significance_score', 0):.2f}"
                )
                lines.append("")
        else:
            lines.append("*No convergent results found yet.*")
            lines.append("")

        # 2. Shared assumptions
        lines.append("## 2. Shared Assumptions")
        lines.append("")
        if sections["assumptions"]:
            for i, a in enumerate(sections["assumptions"], 1):
                lines.append(
                    f"{i}. **\"{a['assumption_text']}\"**"
                )
                lines.append(
                    f"   - Shared by: {', '.join(a['theories'])}"
                )
                if a.get("category"):
                    lines.append(f"   - Category: {a['category']}")
                if a.get("how_fundamental"):
                    lines.append(f"   - Fundamentality: {a['how_fundamental']}")
                lines.append("")
        else:
            lines.append("*No shared assumptions identified yet.*")
            lines.append("")

        # 3. Candidate premises to question
        lines.append("## 3. Candidate Premises to Question")
        lines.append("")
        if sections["shifts"]:
            for i, s in enumerate(sections["shifts"], 1):
                lines.append(
                    f"### Shift #{i} (score: {s.get('score', 0):.3f})"
                )
                lines.append(
                    f"- **Current premise:** {s.get('current_premise', '?')}"
                )
                lines.append(
                    f"- **Proposed shift:** {s.get('proposed_shift', '?')}"
                )
                lines.append(f"- **Pattern:** {s.get('shift_type', '?')}")
                if s.get("evidence_for"):
                    lines.append(f"- **Evidence for:** {s['evidence_for']}")
                if s.get("evidence_against"):
                    lines.append(f"- **Evidence against:** {s['evidence_against']}")
                affected = s.get("affected_theories", "[]")
                if isinstance(affected, str):
                    try:
                        affected = json.loads(affected)
                    except (json.JSONDecodeError, TypeError):
                        affected = [affected]
                if affected:
                    lines.append(
                        f"- **Affected theories:** {', '.join(affected)}"
                    )
                if s.get("historical_analog"):
                    lines.append(
                        f"- **Historical analog:** {s['historical_analog']}"
                    )
                lines.append("")
        else:
            lines.append("*No premise shifts generated yet.*")
            lines.append("")

        # 4. Contradictions
        lines.append("## 4. Contradictions")
        lines.append("")
        if sections["contradictions"]:
            for i, c in enumerate(sections["contradictions"], 1):
                lines.append(
                    f"{i}. **{c.get('theory_a', '?')} vs {c.get('theory_b', '?')}** "
                    f"(severity: {c.get('severity', '?')})"
                )
                lines.append(f"   - {c.get('description', 'No description')}")
                res = c.get("resolution_candidates", "[]")
                if isinstance(res, str):
                    try:
                        res = json.loads(res)
                    except (json.JSONDecodeError, TypeError):
                        res = []
                if res:
                    lines.append(f"   - Resolution candidates: {', '.join(res)}")
                lines.append("")
        else:
            lines.append("*No contradictions recorded yet.*")
            lines.append("")

        # 5. Obstacles
        lines.append("## 5. Obstacles")
        lines.append("")
        if sections["obstacles"]:
            for i, o in enumerate(sections["obstacles"], 1):
                lines.append(
                    f"{i}. **[{o.get('theory_slug', '?')}] "
                    f"{o.get('obstacle_type', '?')}**"
                )
                lines.append(f"   - {o.get('description', 'No description')}")
                if o.get("what_it_might_mean"):
                    lines.append(
                        f"   - Significance: {o['what_it_might_mean']}"
                    )
                if o.get("is_universal"):
                    lines.append("   - *Universal across approaches*")
                lines.append("")
        else:
            lines.append("*No obstacles recorded yet.*")
            lines.append("")

        # 6. Open calculations (extracted from narrative if present)
        lines.append("## 6. Open Calculations")
        lines.append("")
        if sections["narrative"]:
            lines.append(
                "*See the Executive Summary above for specific open "
                "calculations suggested by the analysis.*"
            )
        else:
            lines.append(
                "*Run with LLM narrative enabled to generate "
                "specific open calculation suggestions.*"
            )
        lines.append("")

        lines.append("---")
        lines.append(f"*Report generated by AIsaac premise engine on {now}*")

        return "\n".join(lines)

    # ── Console Rendering ────────────────────────────────────────

    def _print_console(self, problem: str, sections: dict) -> None:
        """Print a rich console report."""
        width = 72
        sep = "=" * width
        thin = "-" * width

        print()
        print(sep)
        print(f"  PREMISE REPORT: {problem[:60]}")
        print(sep)
        print()

        # Narrative
        if sections["narrative"]:
            print("  EXECUTIVE SUMMARY")
            print(thin)
            for line in sections["narrative"].split("\n"):
                print(f"  {line}")
            print()

        # Convergences
        print(f"  CONVERGENT RESULTS ({len(sections['convergences'])})")
        print(thin)
        if sections["convergences"]:
            for i, c in enumerate(sections["convergences"], 1):
                print(f"  {i}. {c.get('title', 'Untitled')}")
                print(f"     {c.get('statement_natural', '')[:100]}")
        else:
            print("  (none)")
        print()

        # Shared assumptions
        print(f"  SHARED ASSUMPTIONS ({len(sections['assumptions'])})")
        print(thin)
        if sections["assumptions"]:
            for i, a in enumerate(sections["assumptions"][:10], 1):
                theories = ", ".join(a["theories"])
                print(f"  {i}. \"{a['assumption_text'][:60]}\"")
                print(f"     Shared by: {theories}")
        else:
            print("  (none)")
        print()

        # Top shifts
        print(f"  TOP PREMISE SHIFTS ({len(sections['shifts'])})")
        print(thin)
        if sections["shifts"]:
            for i, s in enumerate(sections["shifts"], 1):
                score = s.get("score", 0)
                print(f"  #{i} [score={score:.3f}] ({s.get('shift_type', '?')})")
                print(f"     Current: {s.get('current_premise', '?')[:70]}")
                print(f"     Shift:   {s.get('proposed_shift', '?')[:70]}")
                print()
        else:
            print("  (none)")
        print()

        # Contradictions
        print(f"  CONTRADICTIONS ({len(sections['contradictions'])})")
        print(thin)
        if sections["contradictions"]:
            for i, c in enumerate(sections["contradictions"][:5], 1):
                print(
                    f"  {i}. {c.get('theory_a', '?')} vs {c.get('theory_b', '?')}: "
                    f"{c.get('description', '')[:60]}"
                )
        else:
            print("  (none)")
        print()

        # Obstacles
        print(f"  OBSTACLES ({len(sections['obstacles'])})")
        print(thin)
        if sections["obstacles"]:
            for i, o in enumerate(sections["obstacles"][:5], 1):
                print(
                    f"  {i}. [{o.get('theory_slug', '?')}] "
                    f"{o.get('description', '')[:60]}"
                )
        else:
            print("  (none)")
        print()

        print(sep)
        print()

    # ── Formatting helpers for LLM prompt ────────────────────────

    @staticmethod
    def _fmt_convergences(convergences: list[dict]) -> str:
        if not convergences:
            return "None found."
        parts = []
        for c in convergences[:8]:
            parts.append(
                f"- {c.get('title', 'Untitled')}: "
                f"{c.get('statement_natural', '')[:200]}"
            )
        return "\n".join(parts)

    @staticmethod
    def _fmt_assumptions(assumptions: list[dict]) -> str:
        if not assumptions:
            return "None identified."
        parts = []
        for a in assumptions[:10]:
            parts.append(
                f"- \"{a['assumption_text']}\" "
                f"(shared by: {', '.join(a['theories'])})"
            )
        return "\n".join(parts)

    @staticmethod
    def _fmt_shifts(shifts: list[dict]) -> str:
        if not shifts:
            return "None generated."
        parts = []
        for i, s in enumerate(shifts, 1):
            parts.append(
                f"{i}. [score={s.get('score', 0):.3f}] "
                f"Drop: \"{s.get('current_premise', '?')}\" -> "
                f"Replace: \"{s.get('proposed_shift', '?')}\""
            )
        return "\n".join(parts)

    @staticmethod
    def _fmt_contradictions(contradictions: list[dict]) -> str:
        if not contradictions:
            return "None recorded."
        parts = []
        for c in contradictions[:8]:
            parts.append(
                f"- {c.get('theory_a', '?')} vs {c.get('theory_b', '?')}: "
                f"{c.get('description', '')}"
            )
        return "\n".join(parts)

    @staticmethod
    def _fmt_obstacles(obstacles: list[dict]) -> str:
        if not obstacles:
            return "None recorded."
        parts = []
        for o in obstacles[:8]:
            parts.append(
                f"- [{o.get('theory_slug', '?')}] {o.get('obstacle_type', '?')}: "
                f"{o.get('description', '')}"
            )
        return "\n".join(parts)
