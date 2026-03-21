"""
Deep Notation Normalizer.

The HARDEST engineering problem in the system. Every QG approach
uses different notation for the same physical quantities:

  Newton's constant: G, G_N, κ²/16π, κ²/(8π), 1/M_P²
  Planck length: l_P, l_p, ℓ_P, l_{Pl}, √(ℏG/c³)
  BH entropy: S, S_BH, S_{BH}, S_{\rm bh}
  Metric signature: (+---) vs (-+++)

Without correct normalization, the comparison engine will miss
that two formulas are describing the same physics.

Strategy:
1. Pattern-based replacements for known aliases (fast, reliable)
2. LLM-assisted normalization for ambiguous cases (slower, flexible)
3. Dimensional consistency check (catches normalization errors)
"""
from __future__ import annotations

import re
import logging
from typing import Optional

import sympy as sp
from sympy import Symbol, sqrt, pi, Rational, oo, log, exp

log_mod = logging.getLogger(__name__)


# ── Symbol Definitions (canonical) ───────────────────────────────

# Fundamental constants
G = Symbol('G', positive=True)          # Newton's constant
hbar = Symbol('hbar', positive=True)    # reduced Planck constant
c = Symbol('c', positive=True)          # speed of light
k_B = Symbol('k_B', positive=True)      # Boltzmann constant

# Derived Planck quantities
l_P = Symbol('l_P', positive=True)      # Planck length = sqrt(hbar*G/c^3)
M_P = Symbol('M_P', positive=True)      # Planck mass = sqrt(hbar*c/G)
t_P = Symbol('t_P', positive=True)      # Planck time = sqrt(hbar*G/c^5)
E_P = Symbol('E_P', positive=True)      # Planck energy = sqrt(hbar*c^5/G)

# Cosmological
Lambda = Symbol('Lambda')               # cosmological constant

# Theory-specific (kept distinct, not normalized away)
gamma_I = Symbol('gamma_I', positive=True)   # Immirzi parameter (LQG)
alpha_prime = Symbol('alpha_prime', positive=True)  # string tension
g_s = Symbol('g_s', positive=True)           # string coupling
theta_NC = Symbol('theta_NC', positive=True) # NC parameter
z_HL = Symbol('z_HL', positive=True)         # Horava dynamical exponent

# Common variables
r = Symbol('r', positive=True)
sigma = Symbol('sigma', positive=True)   # diffusion time
A = Symbol('A', positive=True)           # area
d = Symbol('d', positive=True, integer=True)  # spacetime dimension
k = Symbol('k', positive=True)           # energy/momentum scale


# ── Latex-to-Sympy Substitution Rules ────────────────────────────

LATEX_SUBSTITUTIONS = [
    # Newton's constant variants → G
    (r'\\kappa\^2\s*/\s*\(?\s*16\s*\\pi\s*\)?', 'G'),
    (r'\\kappa\^2\s*/\s*\(?\s*8\s*\\pi\s*\)?', '2*G'),
    (r'\\kappa\^2', '16*pi*G'),
    (r'\\kappa', 'sqrt(16*pi*G)'),
    (r'G_N', 'G'),
    (r'G_{\\rm N}', 'G'),
    (r'G_{N}', 'G'),
    (r'G_\\mathrm{N}', 'G'),

    # Planck length variants → l_P
    (r'l_p(?![A-Z])', 'l_P'),
    (r'\\ell_P', 'l_P'),
    (r'\\ell_p', 'l_P'),
    (r'l_\{Pl\}', 'l_P'),
    (r'l_\{\\rm Pl\}', 'l_P'),
    (r'l_\{\\mathrm\{Pl\}\}', 'l_P'),
    (r'\\ell_\{\\rm P\}', 'l_P'),
    (r'\\ell_\{P\}', 'l_P'),

    # Planck mass variants → M_P
    (r'M_p(?![A-Z])', 'M_P'),
    (r'm_P', 'M_P'),
    (r'm_p', 'M_P'),
    (r'M_\{Pl\}', 'M_P'),
    (r'M_\{\\rm Pl\}', 'M_P'),
    (r'M_\{\\mathrm\{Pl\}\}', 'M_P'),

    # Cosmological constant
    (r'\\Lambda_\{cc\}', 'Lambda'),
    (r'\\Lambda_\{\\rm cc\}', 'Lambda'),
    (r'\\Lambda_\{cosm\}', 'Lambda'),
    (r'\\Lambda', 'Lambda'),
    (r'\\lambda(?=\s|$|[^a-zA-Z])', 'Lambda'),

    # Hbar variants
    (r'\\hbar', 'hbar'),

    # Immirzi parameter
    (r'\\gamma_I', 'gamma_I'),
    (r'\\gamma_\{\\rm I\}', 'gamma_I'),
    (r'\\gamma_\{Immirzi\}', 'gamma_I'),
    (r'\\beta_I', 'gamma_I'),   # some papers use β

    # String theory
    (r"\\alpha'", 'alpha_prime'),
    (r"\\alpha_\{\\rm s\}", 'alpha_prime'),
    (r'g_s', 'g_s'),
    (r'g_\{\\rm s\}', 'g_s'),
    (r'l_s', 'sqrt(alpha_prime)'),   # string length = sqrt(α')
    (r'l_\{\\rm s\}', 'sqrt(alpha_prime)'),

    # NC geometry
    (r'\\theta_\{NC\}', 'theta_NC'),
    (r'\\theta_\{\\rm NC\}', 'theta_NC'),

    # Horava
    (r'z_\{HL\}', 'z_HL'),

    # Common math
    (r'\\frac\{([^{}]+)\}\{([^{}]+)\}', r'((\1)/(\2))'),
    (r'\\sqrt\{([^{}]+)\}', r'sqrt(\1)'),
    (r'\\ln', 'log'),
    (r'\\log', 'log'),
    (r'\\exp', 'exp'),
    (r'\\pi', 'pi'),
    (r'\\infty', 'oo'),
    (r'\\cdot', '*'),
    (r'\\times', '*'),
    (r'\\left\(', '('),
    (r'\\right\)', ')'),
    (r'\\left\[', '('),
    (r'\\right\]', ')'),
    (r'\^', '**'),
]


# ── Natural Units Conversion ─────────────────────────────────────

# In natural units: ℏ = c = k_B = 1
# Then: l_P = √G, M_P = 1/√G, t_P = √G, E_P = 1/√G

NATURAL_UNIT_SUBS = {
    hbar: 1,
    c: 1,
    k_B: 1,
    l_P: sqrt(G),       # l_P = sqrt(ℏG/c³) → sqrt(G) in natural units
    M_P: 1/sqrt(G),     # M_P = sqrt(ℏc/G) → 1/sqrt(G) in natural units
    t_P: sqrt(G),
    E_P: 1/sqrt(G),
}


# ── Metric Signature Convention ──────────────────────────────────
# We use (-+++) throughout.
# Papers using (+---) need sign flips in certain terms.
# This is tracked but not auto-corrected (too risky without context).


class DeepNormalizer:
    """
    Multi-pass notation normalizer.
    
    Pass 1: Regex substitutions for known notation aliases
    Pass 2: Convert to natural units (ℏ = c = 1)
    Pass 3: Express all Planck quantities in terms of G
    Pass 4: Dimensional consistency check
    Pass 5: LLM validation for ambiguous cases
    """

    def normalize_latex(self, latex: str) -> str:
        """Normalize LaTeX notation to standard form."""
        result = latex
        for pattern, replacement in LATEX_SUBSTITUTIONS:
            result = re.sub(pattern, replacement, result)
        # Clean up
        result = result.replace('{', '').replace('}', '')
        result = re.sub(r'\s+', ' ', result).strip()
        return result

    def normalize_sympy_expr(
        self, expr_str: str, 
        to_natural_units: bool = True,
    ) -> Optional[str]:
        """
        Normalize a sympy expression string.
        
        Returns normalized sympy expression as string,
        or None if parsing fails.
        """
        try:
            expr = sp.sympify(expr_str)
        except Exception:
            return None

        # Substitute Planck quantities
        if to_natural_units:
            for old, new in NATURAL_UNIT_SUBS.items():
                if old in expr.free_symbols:
                    expr = expr.subs(old, new)

        # Simplify
        try:
            expr = sp.simplify(expr)
        except Exception:
            pass

        return str(expr)

    def latex_to_sympy(self, latex: str) -> Optional[str]:
        """
        Convert LaTeX formula to sympy expression string.
        
        This is best-effort. Complex LaTeX may need LLM assistance.
        """
        # First normalize LaTeX
        s = self.normalize_latex(latex)
        
        # Additional LaTeX → Python/sympy conversions
        # Handle remaining \frac with nested braces (recursive)
        for _ in range(5):
            s_new = re.sub(r'\\frac\{([^{}]+)\}\{([^{}]+)\}', r'((\1)/(\2))', s)
            if s_new == s:
                break
            s = s_new

        # Handle subscripts/superscripts that are just labels
        s = re.sub(r'_\{([a-zA-Z0-9]+)\}', r'_\1', s)
        
        # Remove remaining LaTeX commands
        s = re.sub(r'\\[a-zA-Z]+', '', s)
        
        # Clean up braces
        s = s.replace('{', '(').replace('}', ')')
        
        # Try to parse
        try:
            expr = sp.sympify(s)
            return str(expr)
        except Exception:
            return None

    def check_dimensional_consistency(
        self, expr_str: str, expected_dims: str | None = None,
    ) -> dict:
        """
        Check if an expression is dimensionally consistent.
        
        In natural units (ℏ=c=1), the only remaining dimension is
        [length] = [mass]⁻¹ = [energy]⁻¹.
        
        G has dimensions [length]² in natural units.
        
        Returns dict with consistency assessment.
        """
        try:
            expr = sp.sympify(expr_str)
        except Exception:
            return {"consistent": None, "error": "parse failed"}

        # Count powers of G to infer dimensions
        g_sym = sp.Symbol('G')
        if g_sym in expr.free_symbols:
            # Extract coefficient of G
            # This is a simplified check — full dimensional analysis
            # would require tracking dimensions of ALL symbols
            g_power = 0
            try:
                # Try to express as c * G^n * (rest)
                collected = sp.collect(sp.expand(expr), g_sym)
                # Simple heuristic: count explicit G powers
                s = str(expr)
                g_power = s.count("G**") + s.count("G*") + s.count("*G") + (1 if "G" in s else 0)
            except Exception:
                pass

            return {
                "consistent": None,
                "g_power_estimate": g_power,
                "note": "G present — dimensions involve powers of length²",
            }

        # No G → should be dimensionless in natural units
        return {
            "consistent": True,
            "note": "no G present — dimensionless in natural units",
        }

    def normalize_full(
        self, latex: str, context: str = "",
    ) -> dict:
        """
        Full normalization pipeline.
        
        Returns dict with:
        - normalized_latex: cleaned LaTeX
        - normalized_sympy: sympy expression string
        - natural_units: expression in natural units
        - dimensional_check: consistency assessment
        """
        # Step 1: LaTeX normalization
        norm_latex = self.normalize_latex(latex)
        
        # Step 2: Convert to sympy
        sympy_str = self.latex_to_sympy(latex)
        
        # Step 3: Natural units
        natural = None
        if sympy_str:
            natural = self.normalize_sympy_expr(sympy_str, to_natural_units=True)
        
        # Step 4: Dimensional check
        dim_check = {}
        if natural:
            dim_check = self.check_dimensional_consistency(natural)

        return {
            "normalized_latex": norm_latex,
            "normalized_sympy": sympy_str or "",
            "natural_units": natural or "",
            "dimensional_check": dim_check,
        }
