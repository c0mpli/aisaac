"""
Symmetry Matcher (Comparison Level 5).

Compares the SYMMETRY STRUCTURE of formulas across theories.
If two theories share the same symmetry group, their predictions
in that symmetric sector must agree (by representation theory).

This is the deepest comparison level before ML. Symmetry arguments
are the strongest proofs in physics.

Key symmetries to detect:
- Diffeomorphism invariance (all QG theories should have this in some form)
- Lorentz invariance (preserved or broken?)
- Gauge symmetries (SU(2) in LQG, conformal in string theory)
- BMS symmetry (Carlip's argument for d_s → 2)
- Duality symmetries (T-duality, S-duality in strings)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

log = logging.getLogger(__name__)


@dataclass
class SymmetryProfile:
    """Symmetry properties of a formula or theory."""
    theory_slug: str
    # Which symmetries are present
    diffeo_invariant: Optional[bool] = None       # full diffeomorphism invariance
    lorentz_invariant: Optional[bool] = None       # local Lorentz invariance
    foliation_dependent: Optional[bool] = None     # breaks time-space democracy
    gauge_group: str = ""                          # e.g., "SU(2)", "U(1)", "conformal"
    discrete_symmetry: Optional[bool] = None       # discrete spacetime structure
    has_supersymmetry: Optional[bool] = None
    has_duality: Optional[bool] = None             # T-duality, S-duality, etc.
    uv_scaling: str = ""                           # how it behaves at high energy
    # From formula extraction
    formula_symmetries_claimed: list[str] = None   # symmetries mentioned in the paper
    
    def __post_init__(self):
        if self.formula_symmetries_claimed is None:
            self.formula_symmetries_claimed = []


# Known symmetry profiles per theory
THEORY_SYMMETRIES: dict[str, SymmetryProfile] = {
    "string_theory": SymmetryProfile(
        theory_slug="string_theory",
        diffeo_invariant=True,
        lorentz_invariant=True,
        foliation_dependent=False,
        gauge_group="various (depends on compactification)",
        discrete_symmetry=False,
        has_supersymmetry=True,
        has_duality=True,
        uv_scaling="soft UV (string scale cutoff)",
    ),
    "loop_quantum_gravity": SymmetryProfile(
        theory_slug="loop_quantum_gravity",
        diffeo_invariant=True,
        lorentz_invariant=True,  # debated at Planck scale
        foliation_dependent=False,  # background independent
        gauge_group="SU(2)",
        discrete_symmetry=True,  # discrete area/volume spectra
        has_supersymmetry=False,
        has_duality=False,
        uv_scaling="discrete (natural cutoff from area gap)",
    ),
    "cdt": SymmetryProfile(
        theory_slug="cdt",
        diffeo_invariant=False,  # only foliation-preserving
        lorentz_invariant=False,  # broken by preferred foliation
        foliation_dependent=True,
        gauge_group="",
        discrete_symmetry=True,  # simplicial
        has_supersymmetry=False,
        has_duality=False,
        uv_scaling="discrete (lattice cutoff)",
    ),
    "asymptotic_safety": SymmetryProfile(
        theory_slug="asymptotic_safety",
        diffeo_invariant=True,
        lorentz_invariant=True,
        foliation_dependent=False,
        gauge_group="",
        discrete_symmetry=False,
        has_supersymmetry=False,
        has_duality=False,
        uv_scaling="power-law (UV fixed point)",
    ),
    "causal_sets": SymmetryProfile(
        theory_slug="causal_sets",
        diffeo_invariant=False,  # replaced by order invariance
        lorentz_invariant=True,   # maintained despite discreteness!
        foliation_dependent=False,
        gauge_group="",
        discrete_symmetry=True,
        has_supersymmetry=False,
        has_duality=False,
        uv_scaling="discrete (fundamental discreteness)",
    ),
    "horava_lifshitz": SymmetryProfile(
        theory_slug="horava_lifshitz",
        diffeo_invariant=False,  # only foliation-preserving
        lorentz_invariant=False,  # explicitly broken (z ≠ 1)
        foliation_dependent=True,
        gauge_group="",
        discrete_symmetry=False,
        has_supersymmetry=False,
        has_duality=False,
        uv_scaling="power-law (z=3 in UV)",
    ),
    "noncommutative_geometry": SymmetryProfile(
        theory_slug="noncommutative_geometry",
        diffeo_invariant=False,  # twisted diffeomorphisms
        lorentz_invariant=False,  # broken by θ (direction-dependent)
        foliation_dependent=False,
        gauge_group="Hopf algebra",
        discrete_symmetry=False,
        has_supersymmetry=False,
        has_duality=True,  # Seiberg-Witten map
        uv_scaling="modified (noncommutative scale)",
    ),
    "emergent_gravity": SymmetryProfile(
        theory_slug="emergent_gravity",
        diffeo_invariant=True,  # emerges
        lorentz_invariant=True,  # emerges
        foliation_dependent=False,
        gauge_group="entanglement structure",
        discrete_symmetry=False,  # depends on microscopic theory
        has_supersymmetry=None,  # depends on microscopic theory
        has_duality=True,  # ER=EPR
        uv_scaling="depends on microscopic theory",
    ),
}


class SymmetryMatcher:
    """
    Compare symmetry structures between theories/formulas.
    
    Key insight: if two theories share a symmetry, their predictions
    in the symmetric sector MUST agree (or one is wrong).
    
    Conversely, if they BREAK different symmetries, their predictions
    should DIFFER — and the difference tells us which symmetry breaking
    matters physically.
    """

    def compare_theories(self, theory_a: str, theory_b: str) -> tuple[float, dict]:
        """
        Compare symmetry profiles of two theories.
        Returns (similarity_score, details).
        """
        prof_a = THEORY_SYMMETRIES.get(theory_a)
        prof_b = THEORY_SYMMETRIES.get(theory_b)
        
        if not prof_a or not prof_b:
            return 0.0, {"error": "unknown theory"}

        matches = 0
        total = 0
        details = {}

        # Compare each symmetry property
        checks = [
            ("diffeo_invariant", prof_a.diffeo_invariant, prof_b.diffeo_invariant),
            ("lorentz_invariant", prof_a.lorentz_invariant, prof_b.lorentz_invariant),
            ("foliation_dependent", prof_a.foliation_dependent, prof_b.foliation_dependent),
            ("discrete_symmetry", prof_a.discrete_symmetry, prof_b.discrete_symmetry),
            ("has_supersymmetry", prof_a.has_supersymmetry, prof_b.has_supersymmetry),
            ("has_duality", prof_a.has_duality, prof_b.has_duality),
        ]

        for name, va, vb in checks:
            if va is not None and vb is not None:
                total += 1
                if va == vb:
                    matches += 1
                    details[name] = "agree"
                else:
                    details[name] = f"disagree ({va} vs {vb})"
            else:
                details[name] = "unknown"

        score = matches / max(total, 1)
        details["matches"] = matches
        details["total_checked"] = total

        return score, details

    def find_symmetry_implications(
        self, theory_a: str, theory_b: str,
    ) -> list[dict]:
        """
        Find implications of symmetry (dis)agreement between theories.
        
        If theories share a symmetry → predictions in that sector should agree.
        If they break different symmetries → specific predictions should differ.
        
        Returns list of implications with their significance.
        """
        prof_a = THEORY_SYMMETRIES.get(theory_a)
        prof_b = THEORY_SYMMETRIES.get(theory_b)
        
        if not prof_a or not prof_b:
            return []

        implications = []

        # Lorentz invariance
        if prof_a.lorentz_invariant and not prof_b.lorentz_invariant:
            implications.append({
                "symmetry": "Lorentz invariance",
                "status": f"{theory_a} preserves, {theory_b} breaks",
                "implication": (
                    f"Dispersion relation modifications should DIFFER: "
                    f"{theory_b} predicts direction-dependent corrections, "
                    f"{theory_a} does not."
                ),
                "testable": True,
                "significance": 0.9,
            })

        # Both preserve Lorentz
        if prof_a.lorentz_invariant and prof_b.lorentz_invariant:
            implications.append({
                "symmetry": "Lorentz invariance",
                "status": "both preserve",
                "implication": (
                    "Both theories predict Lorentz-invariant corrections. "
                    "Their dispersion relation modifications should be isotropic "
                    "and should agree on the leading correction if the symmetry "
                    "constrains the form."
                ),
                "testable": True,
                "significance": 0.7,
            })

        # Discreteness
        if prof_a.discrete_symmetry and prof_b.discrete_symmetry:
            implications.append({
                "symmetry": "discrete spacetime",
                "status": "both discrete",
                "implication": (
                    "Both predict discrete spacetime structure. "
                    "Minimum area/length predictions should be compared — "
                    "if they agree, it constrains the discreteness scale."
                ),
                "testable": True,
                "significance": 0.8,
            })

        # Foliation dependence
        if prof_a.foliation_dependent and prof_b.foliation_dependent:
            implications.append({
                "symmetry": "foliation structure",
                "status": "both foliation-dependent",
                "implication": (
                    "Both break full diffeomorphism invariance to "
                    "foliation-preserving diffeomorphisms. Their UV behavior "
                    "should be compared — CDT and Horava-Lifshitz might agree "
                    "on foliation-dependent predictions."
                ),
                "testable": True,
                "significance": 0.8,
            })

        # One has duality, other doesn't
        if prof_a.has_duality and not prof_b.has_duality:
            implications.append({
                "symmetry": "duality",
                "status": f"{theory_a} has duality, {theory_b} doesn't",
                "implication": (
                    f"Duality in {theory_a} might map to a hidden symmetry "
                    f"in {theory_b} that hasn't been discovered yet."
                ),
                "testable": False,
                "significance": 0.6,
            })

        return implications

    def find_all_symmetry_matches(self) -> list[tuple[str, str, float, dict]]:
        """
        Compare all theory pairs and return symmetry analysis.
        """
        theories = list(THEORY_SYMMETRIES.keys())
        results = []
        
        for i, ta in enumerate(theories):
            for tb in theories[i+1:]:
                score, details = self.compare_theories(ta, tb)
                implications = self.find_symmetry_implications(ta, tb)
                details["implications"] = implications
                results.append((ta, tb, score, details))

        results.sort(key=lambda x: x[2], reverse=True)
        return results
