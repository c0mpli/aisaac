"""
Known Cross-Theory Connections.

These are ESTABLISHED connections between quantum gravity approaches
that AIsaac MUST rediscover to validate its methodology.

If the system misses any of these, something is broken in the
comparison/extraction pipeline.

Sources: review papers, textbooks, established results.
Each entry includes the precise mathematical statement,
which theories are involved, and the original reference.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class KnownConnection:
    title: str
    theories: list[str]
    statement: str                  # natural language
    latex: str                      # precise mathematical statement
    quantity_type: str
    discovery_year: int
    original_reference: str
    significance: str               # why this matters
    difficulty: str                 # easy | medium | hard (for the system to find)


KNOWN_CONNECTIONS: list[KnownConnection] = [

    # ═══════════════════════════════════════════════════════════
    # 1. SPECTRAL DIMENSION → 2 AT PLANCK SCALE
    # The most famous cross-theory result in QG
    # ═══════════════════════════════════════════════════════════

    KnownConnection(
        title="Spectral dimension flows to 2 at short distances (CDT)",
        theories=["cdt"],
        statement=(
            "In Causal Dynamical Triangulations, the spectral dimension "
            "measured by diffusion on the quantum geometry flows from "
            "d_s ≈ 4 at large distances to d_s ≈ 2 at short distances."
        ),
        latex=r"d_s(\sigma) \to 2 \text{ as } \sigma \to 0",
        quantity_type="spectral_dimension",
        discovery_year=2005,
        original_reference="Ambjorn, Jurkiewicz, Loll, PRL 95 (2005) 171301 [hep-th/0505113]",
        significance="First numerical evidence of dimensional reduction in QG",
        difficulty="easy",
    ),

    KnownConnection(
        title="Spectral dimension flows to 2 at short distances (Asymptotic Safety)",
        theories=["asymptotic_safety"],
        statement=(
            "In the asymptotic safety program, the running of Newton's "
            "constant near the UV fixed point implies the spectral "
            "dimension flows to d_s = 2 at the fixed point."
        ),
        latex=r"d_s = \frac{2d}{2 + d \cdot \eta_N} \to 2 \text{ at UV FP}",
        quantity_type="spectral_dimension",
        discovery_year=2009,
        original_reference="Lauscher, Reuter, JHEP 0510 (2005) 050 [hep-th/0508202]",
        significance="Independent derivation from completely different framework",
        difficulty="easy",
    ),

    KnownConnection(
        title="Spectral dimension flows to 2 at short distances (Horava-Lifshitz)",
        theories=["horava_lifshitz"],
        statement=(
            "In Horava-Lifshitz gravity with z=3, the anisotropic scaling "
            "between space and time gives exactly d_s = 2 in the UV."
        ),
        latex=r"d_s = 1 + \frac{d-1}{z} = 1 + \frac{3}{3} = 2 \text{ for } z=3, d=4",
        quantity_type="spectral_dimension",
        discovery_year=2009,
        original_reference="Horava, PRL 102 (2009) 161301 [0901.3775]",
        significance="EXACT result (not numerical), simple derivation",
        difficulty="easy",
    ),

    KnownConnection(
        title="Spectral dimension universality across 5+ approaches",
        theories=["cdt", "asymptotic_safety", "horava_lifshitz", "loop_quantum_gravity", "causal_sets"],
        statement=(
            "The spectral dimension flows to approximately 2 at the Planck "
            "scale in CDT, asymptotic safety, Horava-Lifshitz, LQG (some models), "
            "and causal sets. This is the most prominent universal prediction "
            "of quantum gravity, and its origin is not fully understood."
        ),
        latex=r"d_s(\ell_P) \approx 2 \text{ in CDT, AS, HL, LQG, CS}",
        quantity_type="spectral_dimension",
        discovery_year=2009,
        original_reference="Carlip, arXiv:1009.1136 [gr-qc] (2010) - review of universality",
        significance=(
            "THE key cross-theory result. If AIsaac can't find this, "
            "the system is fundamentally broken."
        ),
        difficulty="easy",
    ),

    # ═══════════════════════════════════════════════════════════
    # 2. BLACK HOLE ENTROPY S = A/4
    # ═══════════════════════════════════════════════════════════

    KnownConnection(
        title="Bekenstein-Hawking entropy from string theory microstate counting",
        theories=["string_theory"],
        statement=(
            "Strominger and Vafa derived S = A/4 for extremal black holes "
            "by counting string theory microstates (D-brane configurations)."
        ),
        latex=r"S = \frac{A}{4 G \hbar} = \frac{A}{4 l_P^2}",
        quantity_type="black_hole_entropy",
        discovery_year=1996,
        original_reference="Strominger, Vafa, PLB 379 (1996) 99 [hep-th/9601029]",
        significance="First microscopic derivation of BH entropy",
        difficulty="easy",
    ),

    KnownConnection(
        title="Bekenstein-Hawking entropy from LQG state counting",
        theories=["loop_quantum_gravity"],
        statement=(
            "In LQG, the number of spin network states piercing the horizon "
            "gives S = A/4 when the Immirzi parameter is fixed to "
            "gamma_I = ln(2) / (pi * sqrt(3))."
        ),
        latex=r"S = \frac{\gamma_0}{\gamma_I} \frac{A}{4 l_P^2}, \quad \gamma_0 = \frac{\ln 2}{\pi\sqrt{3}}",
        quantity_type="black_hole_entropy",
        discovery_year=1996,
        original_reference="Rovelli, PRL 77 (1996) 3288 [gr-qc/9603063]; Ashtekar et al. [gr-qc/9710007]",
        significance="Independent derivation, but requires fixing Immirzi parameter",
        difficulty="medium",
    ),

    # ═══════════════════════════════════════════════════════════
    # 3. LOGARITHMIC CORRECTIONS TO BH ENTROPY
    # Sharp discriminator between theories
    # ═══════════════════════════════════════════════════════════

    KnownConnection(
        title="Logarithmic correction to BH entropy: coefficient debate",
        theories=["loop_quantum_gravity", "string_theory", "asymptotic_safety"],
        statement=(
            "The subleading correction to BH entropy is logarithmic: "
            "S = A/4 + c * ln(A) + ... The coefficient c differs between "
            "approaches: c = -3/2 in LQG (Kaul-Majumdar), c = -1/2 in some "
            "string calculations, c depends on matter content in others."
        ),
        latex=r"S = \frac{A}{4 l_P^2} + c \ln\frac{A}{l_P^2} + O(1)",
        quantity_type="bh_entropy_log_correction",
        discovery_year=2000,
        original_reference="Kaul, Majumdar, PRL 84 (2000) 5255 [gr-qc/0002040]",
        significance=(
            "The log coefficient is a SHARP TEST. If it's universal, "
            "that constrains all theories. If it differs, it discriminates."
        ),
        difficulty="medium",
    ),

    # ═══════════════════════════════════════════════════════════
    # 4. QUANTUM CORRECTIONS TO NEWTON'S LAW
    # ═══════════════════════════════════════════════════════════

    KnownConnection(
        title="Leading quantum correction to Newton's potential (universal form)",
        theories=["string_theory", "loop_quantum_gravity", "asymptotic_safety"],
        statement=(
            "Multiple approaches predict the leading quantum correction to "
            "Newton's gravitational potential has the form "
            "V(r) = -Gm1m2/r * (1 + alpha * G/(r^2 c^3) + ...) "
            "where alpha is a numerical coefficient. The FORM is universal "
            "but alpha differs between approaches."
        ),
        latex=r"V(r) = -\frac{G m_1 m_2}{r}\left(1 + \alpha \frac{G \hbar}{r^2 c^3} + \ldots\right)",
        quantity_type="newton_correction",
        discovery_year=1994,
        original_reference="Donoghue, PRL 72 (1994) 2996 [gr-qc/9310024]; Bjerrum-Bohr et al. [hep-th/0206236]",
        significance=(
            "Universal STRUCTURE suggests deep reason. "
            "Coefficient comparison could connect theories."
        ),
        difficulty="medium",
    ),

    # ═══════════════════════════════════════════════════════════
    # 5. AdS/CFT CORRESPONDENCE
    # ═══════════════════════════════════════════════════════════

    KnownConnection(
        title="AdS/CFT: gravity in d+1 dimensions = CFT in d dimensions",
        theories=["string_theory", "emergent_gravity"],
        statement=(
            "The Anti-de Sitter/Conformal Field Theory correspondence "
            "states that quantum gravity in (d+1)-dimensional AdS space "
            "is exactly dual to a conformal field theory on the d-dimensional "
            "boundary. This is the most concrete realization of holography "
            "and emergent gravity."
        ),
        latex=r"Z_{\text{gravity}}[\text{AdS}_{d+1}] = Z_{\text{CFT}}[\partial\text{AdS}_{d+1}]",
        quantity_type="other",
        discovery_year=1997,
        original_reference="Maldacena, hep-th/9711200 (1997)",
        significance="The deepest known connection between gravity and quantum theory",
        difficulty="easy",
    ),

    # ═══════════════════════════════════════════════════════════
    # 6. RYU-TAKAYANAGI FORMULA
    # ═══════════════════════════════════════════════════════════

    KnownConnection(
        title="Ryu-Takayanagi: entanglement entropy = minimal surface area",
        theories=["string_theory", "emergent_gravity"],
        statement=(
            "The entanglement entropy of a boundary region A equals "
            "the area of the minimal surface in the bulk whose boundary "
            "is the boundary of A, divided by 4G. This connects quantum "
            "information to geometry."
        ),
        latex=r"S_{\text{EE}}(A) = \frac{\text{Area}(\gamma_A)}{4 G_N}",
        quantity_type="entanglement_entropy_area_law",
        discovery_year=2006,
        original_reference="Ryu, Takayanagi, PRL 96 (2006) 181602 [hep-th/0603001]",
        significance="Foundation of 'gravity from entanglement' program",
        difficulty="easy",
    ),

    # ═══════════════════════════════════════════════════════════
    # 7. MODIFIED DISPERSION RELATIONS
    # ═══════════════════════════════════════════════════════════

    KnownConnection(
        title="Planck-scale modified dispersion relation (multiple approaches)",
        theories=["loop_quantum_gravity", "horava_lifshitz", "noncommutative_geometry", "string_theory"],
        statement=(
            "Multiple QG approaches predict modifications to the energy-momentum "
            "dispersion relation at the Planck scale: "
            "E^2 = p^2 + m^2 + eta * p^n * l_P^(n-2) + ... "
            "The power n and sign of eta differ between approaches."
        ),
        latex=r"E^2 = p^2 c^2 + m^2 c^4 + \eta \frac{p^n l_P^{n-2}}{\hbar^{n-2}} + \ldots",
        quantity_type="dispersion_relation_modification",
        discovery_year=1998,
        original_reference="Amelino-Camelia, IJMPD 11 (2002) 35 [gr-qc/0012051]; Gambini, Pullin [gr-qc/9809038]",
        significance=(
            "Potentially TESTABLE with gamma-ray burst observations (Fermi/GLAST). "
            "If theories agree on n and eta, it's a universal prediction."
        ),
        difficulty="hard",
    ),

    # ═══════════════════════════════════════════════════════════
    # 8. AREA QUANTIZATION
    # ═══════════════════════════════════════════════════════════

    KnownConnection(
        title="Area quantization in LQG",
        theories=["loop_quantum_gravity"],
        statement=(
            "In LQG, the area operator has a discrete spectrum with "
            "minimum nonzero eigenvalue (the area gap). "
            "The area eigenvalues involve the Immirzi parameter gamma_I."
        ),
        latex=r"A = 8\pi\gamma_I l_P^2 \sum_i \sqrt{j_i(j_i+1)}",
        quantity_type="area_gap",
        discovery_year=1995,
        original_reference="Rovelli, Smolin, NPB 442 (1995) 593 [gr-qc/9411005]",
        significance="Key prediction of LQG — does any other approach predict discrete area?",
        difficulty="easy",
    ),

    # ═══════════════════════════════════════════════════════════
    # 9. RUNNING OF NEWTON'S CONSTANT
    # ═══════════════════════════════════════════════════════════

    KnownConnection(
        title="Running of Newton's constant near UV fixed point",
        theories=["asymptotic_safety"],
        statement=(
            "In asymptotic safety, Newton's constant runs with energy scale k: "
            "G(k) = G_0 / (1 + omega * G_0 * k^2) approaching the UV fixed point "
            "g* = G(k) * k^2 → const as k → infinity."
        ),
        latex=r"G(k) = \frac{G_0}{1 + \omega G_0 k^2}, \quad g_* = \lim_{k\to\infty} G(k) k^{d-2}",
        quantity_type="running_gravitational_coupling",
        discovery_year=1998,
        original_reference="Reuter, PRD 57 (1998) 971 [hep-th/9605030]",
        significance="Defines the asymptotic safety scenario — does string theory agree?",
        difficulty="medium",
    ),

    # ═══════════════════════════════════════════════════════════
    # 10. CARLIP'S DIMENSIONAL REDUCTION ARGUMENT
    # ═══════════════════════════════════════════════════════════

    KnownConnection(
        title="Carlip's argument for universal d_s → 2",
        theories=["cdt", "asymptotic_safety", "horava_lifshitz", "loop_quantum_gravity", "causal_sets"],
        statement=(
            "Carlip argued that the universal reduction to d_s = 2 "
            "might follow from a universal mechanism: near the Planck "
            "scale, local Lorentz invariance is enhanced to BMS-like "
            "symmetry, which constrains the geometry to be effectively 2D."
        ),
        latex=r"d_s \to 2 \iff \text{BMS-like symmetry enhancement at } \ell_P",
        quantity_type="spectral_dimension",
        discovery_year=2017,
        original_reference="Carlip, CQG 34 (2017) 193001 [1705.05417]",
        significance=(
            "If correct, this EXPLAINS the universality. "
            "AIsaac should find evidence for/against this mechanism."
        ),
        difficulty="hard",
    ),
]


def get_validation_targets() -> list[KnownConnection]:
    """Return all known connections the system must find."""
    return KNOWN_CONNECTIONS


def get_easy_targets() -> list[KnownConnection]:
    """Return easy connections for initial validation."""
    return [c for c in KNOWN_CONNECTIONS if c.difficulty == "easy"]


def get_hard_targets() -> list[KnownConnection]:
    """Return hard connections that would be impressive to find."""
    return [c for c in KNOWN_CONNECTIONS if c.difficulty == "hard"]


def validate_against_known(found_conjectures: list[dict]) -> dict:
    """
    Check how many known connections the system found.

    Uses multi-level matching:
    1. Theory overlap (ANY overlap, not full subset)
    2. Keyword matching on quantity type, title, and description
    3. Status == "known" from verification engine

    Returns dict with found, missed, recall.
    """
    import json as _json

    found = []
    missed = []

    for kc in KNOWN_CONNECTIONS:
        theories_set = set(kc.theories)
        qt = kc.quantity_type

        # Build keyword set from known connection
        kc_keywords = set()
        for w in qt.replace("_", " ").split():
            if len(w) > 2:
                kc_keywords.add(w.lower())
        for w in kc.title.lower().split():
            if len(w) > 3:
                kc_keywords.add(w.lower())
        if hasattr(kc, "description"):
            for w in kc.description.lower().split():
                if len(w) > 4:
                    kc_keywords.add(w.lower())

        matched = False
        for conj in found_conjectures:
            conj_theories = conj.get("theories_involved", [])
            if isinstance(conj_theories, str):
                try:
                    conj_theories = _json.loads(conj_theories)
                except Exception:
                    conj_theories = []
            conj_theories = set(conj_theories)

            # Level 1: ANY theory overlap (not full subset)
            if not (theories_set & conj_theories):
                continue

            # Level 2: keyword matching on conjecture text
            conj_text = " ".join([
                conj.get("title", ""),
                conj.get("statement_natural", ""),
                conj.get("conjecture_type", ""),
            ]).lower()

            keyword_hits = sum(1 for kw in kc_keywords if kw in conj_text)

            # Level 3: status == "known" from the novelty checker
            is_known = conj.get("status") == "known"

            # Match if: 3+ keyword hits, OR 2+ keywords + theory overlap of 2+, OR novelty checker said known
            theory_overlap = len(theories_set & conj_theories)
            if keyword_hits >= 3 or (keyword_hits >= 2 and theory_overlap >= 2) or is_known:
                matched = True
                break

        if matched:
            found.append(kc)
        else:
            missed.append(kc)

    return {
        "found": found,
        "missed": missed,
        "recall": len(found) / len(KNOWN_CONNECTIONS) if KNOWN_CONNECTIONS else 0,
        "total_known": len(KNOWN_CONNECTIONS),
    }
