"""
Paper Writer.

Generates draft paper sections from AIsaac's findings.
The paper structure:

  1. Introduction: the problem of siloed QG theories
  2. Method: AIsaac system description
  3. Validation: rediscovery of known connections
  4. Novel findings: verified new conjectures
  5. Discussion: implications for quantum gravity
  6. Conclusion

Each section is drafted by the LLM using structured data
from the knowledge base and verification results.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional


from ..pipeline.config import ANTHROPIC_MODEL, THEORIES, DATA_DIR
from ..knowledge.base import KnowledgeBase

log = logging.getLogger(__name__)


SECTION_PROMPTS = {
    "abstract": """\
Write a concise abstract (150-250 words) for a physics paper with the following results:

System: AIsaac — an AI system that reads {n_papers} quantum gravity papers across {n_theories} approaches, extracts {n_formulas} key formulas, normalizes notation, and uses multi-level comparison (structural, dimensional, numerical, limiting behavior) plus ML clustering to find cross-theory connections.

Key findings:
- Rediscovered {n_known} known cross-theory connections (validation)
- Found {n_novel} novel verified conjectures
- Top conjecture: {top_conjecture}

Write in the style of Physical Review Letters. Be precise and understated.
""",

    "introduction": """\
Write the introduction section for a paper about an AI system that finds connections between quantum gravity theories. 

Context:
- There are 8+ approaches to quantum gravity: {theory_list}
- These communities are largely siloed — string theorists rarely read LQG papers and vice versa
- Known cross-theory connections (spectral dimension → 2, BH entropy) suggest deeper unity
- Nobody has systematically compared ALL predictions across ALL approaches
- Our system reads {n_papers} papers, extracts {n_formulas} formulas, and finds connections

Structure the introduction as:
1. The quantum gravity landscape (multiple approaches, siloed communities)
2. Known hints of universality (spectral dimension, BH entropy)
3. The gap: no systematic cross-theory comparison exists
4. Our contribution: AIsaac, the first automated cross-theory connection finder
5. Summary of results

Write 4-6 paragraphs. Academic physics style. Cite approaches by their foundational references.
Do not write LaTeX citations — use [Author Year] format.
""",

    "method": """\
Write the Methods section describing the AIsaac system.

System components:
1. Paper ingestion: {n_papers} papers from arXiv across {n_theories} QG approaches
   - Tiered: {tier_breakdown}
   
2. Formula extraction: LLM reads papers, identifies key predictions/equations
   - Extracts: LaTeX, physical meaning, variables, regime, approximations
   - {n_formulas} formulas extracted total
   - Breakdown by theory: {theory_breakdown}

3. Notation normalization:
   - Standard symbols (G for Newton, l_P for Planck length, etc.)
   - Natural units (ℏ = c = 1)
   - Dimensional consistency checking

4. Multi-level comparison:
   - Structural: expression tree topology matching
   - Dimensional: same physical dimensions
   - Numerical: evaluate on random inputs, compare outputs
   - Limiting: does theory A → theory B in some limit?
   - Symmetry: same symmetry group structure
   - ML: formula embeddings + HDBSCAN clustering

5. Conjecture generation: LLM proposes connections from comparison evidence

6. Verification:
   - Algebraic (sympy identity checking)
   - Numerical (1000-point random evaluation)
   - Dimensional consistency
   - Active counterexample search
   - Literature novelty check

Write 3-5 paragraphs covering each component. Technical but accessible.
""",

    "validation": """\
Write the Validation section showing that AIsaac correctly rediscovers known cross-theory connections.

Known connections that were rediscovered:
{known_connections}

For each, explain:
1. What the connection is
2. When it was originally discovered
3. How AIsaac found it (which comparison level triggered?)
4. This validates the system works

This section is critical for credibility — it proves the system finds real connections before we claim novel ones.
""",

    "results": """\
Write the Results section presenting novel verified conjectures.

Novel conjectures (verified, not previously published):
{novel_conjectures}

For each conjecture:
1. State it precisely (include the LaTeX formula)
2. Present the evidence (which formulas from which theories match?)
3. Show the verification results (algebraic, numerical, dimensional)
4. Discuss physical significance

Order by significance. The most important conjecture gets the most space.
""",

    "discussion": """\
Write the Discussion section for the paper.

Address:
1. What do the novel connections tell us about quantum gravity?
2. Limitations of the approach (LLM extraction errors, notation ambiguity, false positives)
3. Which conjectures are most likely to be confirmed by further analysis?
4. What would full confirmation of conjecture X mean for the field?
5. Future work: scaling to more papers, other physics domains, formal proofs

System stats for context:
- Papers: {n_papers}
- Formulas: {n_formulas} 
- Conjectures generated: {n_conjectures}
- Verified novel: {n_novel}
- Disproved: {n_disproved}

Be honest about limitations. Don't overclaim.
""",
}


class PaperWriter:
    """Generate draft paper sections from AIsaac results."""

    def __init__(self, kb: KnowledgeBase):
        self.kb = kb
        from ..pipeline.llm_client import get_client
        self.client = get_client()

    def write_full_paper(self, output_path: str | Path | None = None) -> str:
        """Generate complete draft paper."""
        summary = self.kb.summary()
        conjectures = self.kb.get_conjectures()
        verified = [c for c in conjectures if c["status"] == "verified"]
        known = [c for c in conjectures if c["status"] == "known"]
        disproved = [c for c in conjectures if c["status"] == "disproved"]

        context = {
            "n_papers": summary["papers"],
            "n_formulas": summary["formulas"],
            "n_theories": len(summary.get("formulas_by_theory", {})),
            "n_conjectures": summary.get("conjectures", 0),
            "n_novel": len(verified),
            "n_known": len(known),
            "n_disproved": len(disproved),
            "theory_list": ", ".join(t.name for t in THEORIES),
            "theory_breakdown": json.dumps(summary.get("formulas_by_theory", {})),
            "tier_breakdown": "Tier 1 (reviews) + Tier 2 (high-impact) + Tier 3 (recent frontier)",
            "top_conjecture": verified[0]["title"] if verified else "none",
            "known_connections": self._format_conjectures(known),
            "novel_conjectures": self._format_conjectures(verified),
        }

        sections = {}
        for section_name, prompt_template in SECTION_PROMPTS.items():
            log.info(f"Writing section: {section_name}")
            prompt = prompt_template.format(**context)
            sections[section_name] = self._generate_section(prompt)

        # Assemble LaTeX
        paper = self._assemble_latex(sections, context)
        
        if output_path:
            output_path = Path(output_path)
            output_path.write_text(paper)
            log.info(f"Paper draft saved to {output_path}")
        
        return paper

    def write_section(self, section_name: str) -> str:
        """Generate a single section."""
        if section_name not in SECTION_PROMPTS:
            raise ValueError(f"Unknown section: {section_name}")

        summary = self.kb.summary()
        conjectures = self.kb.get_conjectures()
        verified = [c for c in conjectures if c["status"] == "verified"]
        known = [c for c in conjectures if c["status"] == "known"]
        disproved = [c for c in conjectures if c["status"] == "disproved"]

        context = {
            "n_papers": summary["papers"],
            "n_formulas": summary["formulas"],
            "n_theories": len(summary.get("formulas_by_theory", {})),
            "n_conjectures": summary.get("conjectures", 0),
            "n_novel": len(verified),
            "n_known": len(known),
            "n_disproved": len(disproved),
            "theory_list": ", ".join(t.name for t in THEORIES),
            "theory_breakdown": json.dumps(summary.get("formulas_by_theory", {})),
            "tier_breakdown": "Tier 1 + Tier 2 + Tier 3",
            "top_conjecture": verified[0]["title"] if verified else "none",
            "known_connections": self._format_conjectures(known),
            "novel_conjectures": self._format_conjectures(verified),
        }

        prompt = SECTION_PROMPTS[section_name].format(**context)
        return self._generate_section(prompt)

    def _generate_section(self, prompt: str) -> str:
        """Call LLM to generate a section."""
        try:
            return self.client.complete(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=4096,
                temperature=0.3,
                phase="paper_writing",
            ).strip()
        except Exception as e:
            log.error(f"Section generation failed: {e}")
            return f"[Section generation failed: {e}]"

    def _format_conjectures(self, conjectures: list[dict]) -> str:
        """Format conjectures for inclusion in prompts."""
        if not conjectures:
            return "None found."
        parts = []
        for i, c in enumerate(conjectures, 1):
            parts.append(
                f"{i}. {c['title']}\n"
                f"   Type: {c['conjecture_type']}\n"
                f"   Statement: {c['statement_natural']}\n"
                f"   LaTeX: {c['statement_latex']}\n"
                f"   Theories: {c['theories_involved']}\n"
                f"   Evidence score: {c['evidence_score']:.2f}\n"
                f"   Significance: {c['significance_score']:.2f}\n"
            )
        return "\n".join(parts)

    def _assemble_latex(self, sections: dict[str, str], context: dict) -> str:
        """Assemble sections into a complete LaTeX document."""
        date = datetime.now().strftime("%B %d, %Y")
        
        paper = f"""\\documentclass[twocolumn,prl,aps,superscriptaddress]{{revtex4-2}}
\\usepackage{{amsmath,amssymb,graphicx,hyperref}}

\\begin{{document}}

\\title{{AIsaac: Discovering Cross-Theory Connections in Quantum Gravity\\\\
Through Automated Literature Analysis}}

\\author{{[Author Names]}}
\\affiliation{{[Affiliations]}}

\\date{{{date}}}

\\begin{{abstract}}
{sections.get('abstract', '[Abstract]')}
\\end{{abstract}}

\\maketitle

\\section{{Introduction}}
{sections.get('introduction', '[Introduction]')}

\\section{{Method}}
{sections.get('method', '[Method]')}

\\section{{Validation: Rediscovering Known Connections}}
{sections.get('validation', '[Validation]')}

\\section{{Results: Novel Cross-Theory Connections}}
{sections.get('results', '[Results]')}

\\section{{Discussion}}
{sections.get('discussion', '[Discussion]')}

\\section{{Conclusion}}
We have presented AIsaac, an AI system that reads \\num{{{context['n_papers']}}} quantum gravity 
papers across {context['n_theories']} theoretical approaches, extracts {context['n_formulas']} 
key formulas, and systematically searches for cross-theory connections using multi-level 
comparison and ML-assisted pattern detection.

The system successfully rediscovered {context['n_known']} known cross-theory connections, 
validating its methodology, and identified {context['n_novel']} novel verified conjectures 
about previously unnoticed correspondences between quantum gravity approaches.

\\begin{{acknowledgments}}
We thank the developers of PySR, SymPy, and the arXiv for making this work possible.
This research was supported by [funding].
\\end{{acknowledgments}}

\\end{{document}}
"""
        return paper
