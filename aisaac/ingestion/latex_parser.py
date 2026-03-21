"""
LaTeX Parser.

Extracts equations from raw LaTeX source along with their surrounding
context (the sentences before/after the equation that explain what it represents).

This is the first stage before the LLM formula extractor. It converts
raw .tex files into structured (equation, context) pairs that the LLM
can then assess for importance.
"""
from __future__ import annotations

import re
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)


@dataclass
class RawEquation:
    """A LaTeX equation extracted with its surrounding context."""
    latex: str                    # the equation itself
    environment: str              # equation, align, gather, etc.
    label: str                    # \label{} if present
    context_before: str           # ~200 chars of text before
    context_after: str            # ~200 chars of text after
    section: str                  # which section it appears in
    page_position: int            # approximate position in document (0-1000)


# ── Equation Environments ────────────────────────────────────────

# Display math environments that contain key equations
DISPLAY_ENVS = [
    "equation", "equation*",
    "align", "align*",
    "gather", "gather*",
    "multline", "multline*",
    "eqnarray", "eqnarray*",
    "displaymath",
]

# Inline math patterns
INLINE_PATTERN = re.compile(r'(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)')
DISPLAY_DOLLAR = re.compile(r'\$\$(.+?)\$\$', re.DOTALL)
DISPLAY_BRACKET = re.compile(r'\\\[(.+?)\\\]', re.DOTALL)


class LatexParser:
    """Parse LaTeX source to extract equations with context."""

    def __init__(self, context_chars: int = 300):
        self.context_chars = context_chars

    def parse_file(self, filepath: Path) -> list[RawEquation]:
        """Parse a .tex file or directory of .tex files."""
        filepath = Path(filepath)
        
        if filepath.is_dir():
            # Find main tex file
            tex_files = list(filepath.glob("*.tex"))
            if not tex_files:
                return []
            main = self._find_main_file(tex_files)
            text = main.read_text(errors="replace")
            # Resolve \input{} and \include{} commands
            text = self._resolve_includes(text, filepath)
        elif filepath.suffix == ".tex":
            text = filepath.read_text(errors="replace")
        else:
            return []

        return self.parse_text(text)

    def parse_text(self, text: str) -> list[RawEquation]:
        """Parse LaTeX text and extract all equations."""
        # Strip comments
        text = self._strip_comments(text)
        
        # Extract document body if \begin{document} exists
        doc_match = re.search(r'\\begin\{document\}(.+?)\\end\{document\}', text, re.DOTALL)
        if doc_match:
            text = doc_match.group(1)

        equations = []
        total_len = len(text)

        # Build section map for context
        sections = self._extract_sections(text)

        # 1. Display environments
        for env in DISPLAY_ENVS:
            pattern = re.compile(
                rf'\\begin\{{{env}\}}(.*?)\\end\{{{env}\}}',
                re.DOTALL,
            )
            for m in pattern.finditer(text):
                eq_text = m.group(1).strip()
                if not eq_text or len(eq_text) < 3:
                    continue
                
                start = m.start()
                end = m.end()
                
                # Extract label
                label_match = re.search(r'\\label\{([^}]+)\}', eq_text)
                label = label_match.group(1) if label_match else ""
                
                # Clean equation (remove labels, tags)
                eq_clean = re.sub(r'\\label\{[^}]+\}', '', eq_text)
                eq_clean = re.sub(r'\\tag\{[^}]+\}', '', eq_clean)
                eq_clean = eq_clean.strip()
                
                if not eq_clean:
                    continue

                equations.append(RawEquation(
                    latex=eq_clean,
                    environment=env,
                    label=label,
                    context_before=self._get_context(text, start, before=True),
                    context_after=self._get_context(text, end, before=False),
                    section=self._find_section(sections, start),
                    page_position=int(1000 * start / max(total_len, 1)),
                ))

        # 2. \[ ... \] display math
        for m in DISPLAY_BRACKET.finditer(text):
            eq_text = m.group(1).strip()
            if eq_text and len(eq_text) > 3:
                equations.append(RawEquation(
                    latex=eq_text,
                    environment="displaymath",
                    label="",
                    context_before=self._get_context(text, m.start(), before=True),
                    context_after=self._get_context(text, m.end(), before=False),
                    section=self._find_section(sections, m.start()),
                    page_position=int(1000 * m.start() / max(total_len, 1)),
                ))

        # 3. $$ ... $$ display math
        for m in DISPLAY_DOLLAR.finditer(text):
            eq_text = m.group(1).strip()
            if eq_text and len(eq_text) > 3:
                equations.append(RawEquation(
                    latex=eq_text,
                    environment="displaymath",
                    label="",
                    context_before=self._get_context(text, m.start(), before=True),
                    context_after=self._get_context(text, m.end(), before=False),
                    section=self._find_section(sections, m.start()),
                    page_position=int(1000 * m.start() / max(total_len, 1)),
                ))

        # Deduplicate by content
        seen = set()
        unique = []
        for eq in equations:
            key = eq.latex.strip()
            if key not in seen:
                seen.add(key)
                unique.append(eq)

        log.info(f"Extracted {len(unique)} unique equations from LaTeX source")
        return unique

    def _strip_comments(self, text: str) -> str:
        """Remove LaTeX comments (% to end of line)."""
        lines = []
        for line in text.split("\n"):
            # Find % that isn't \%
            idx = 0
            while idx < len(line):
                if line[idx] == "%" and (idx == 0 or line[idx - 1] != "\\"):
                    line = line[:idx]
                    break
                idx += 1
            lines.append(line)
        return "\n".join(lines)

    def _resolve_includes(self, text: str, base_dir: Path) -> str:
        r"""Resolve \input{} and \include{} commands."""
        def replacer(m):
            filename = m.group(1)
            if not filename.endswith(".tex"):
                filename += ".tex"
            fpath = base_dir / filename
            if fpath.exists():
                return fpath.read_text(errors="replace")
            return m.group(0)  # keep original if file not found

        text = re.sub(r'\\input\{([^}]+)\}', replacer, text)
        text = re.sub(r'\\include\{([^}]+)\}', replacer, text)
        return text

    def _find_main_file(self, tex_files: list[Path]) -> Path:
        """Find the main .tex file in a directory."""
        for f in tex_files:
            text = f.read_text(errors="replace")
            if r"\begin{document}" in text:
                return f
        # Fallback: largest file
        return max(tex_files, key=lambda f: f.stat().st_size)

    def _extract_sections(self, text: str) -> list[tuple[int, str]]:
        """Extract section headings with their positions."""
        sections = []
        for m in re.finditer(r'\\(?:section|subsection|subsubsection)\{([^}]+)\}', text):
            sections.append((m.start(), m.group(1)))
        return sections

    def _find_section(self, sections: list[tuple[int, str]], pos: int) -> str:
        """Find which section a position falls in."""
        current = "preamble"
        for sec_pos, sec_name in sections:
            if sec_pos > pos:
                break
            current = sec_name
        return current

    def _get_context(self, text: str, pos: int, before: bool) -> str:
        """Get surrounding text context."""
        if before:
            start = max(0, pos - self.context_chars)
            ctx = text[start:pos]
        else:
            end = min(len(text), pos + self.context_chars)
            ctx = text[pos:end]
        
        # Clean LaTeX commands for readability
        ctx = re.sub(r'\\[a-zA-Z]+\{', ' ', ctx)
        ctx = ctx.replace('{', '').replace('}', '')
        ctx = re.sub(r'\s+', ' ', ctx).strip()
        return ctx


def extract_equations_with_context(filepath: str | Path) -> list[dict]:
    """
    Convenience function: extract all equations from a LaTeX file
    and return as list of dicts ready for LLM processing.
    """
    parser = LatexParser()
    raw_eqs = parser.parse_file(Path(filepath))
    
    return [
        {
            "latex": eq.latex,
            "environment": eq.environment,
            "label": eq.label,
            "context_before": eq.context_before,
            "context_after": eq.context_after,
            "section": eq.section,
            "position": eq.page_position,
        }
        for eq in raw_eqs
    ]
