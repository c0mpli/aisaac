"""
AIsaac Configuration.

All theory definitions, comparable quantities, search queries,
normalization rules, and pipeline settings.
"""
from __future__ import annotations
import os
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum


# ── Paths ─────────────────────────────────────────────────────────
DATA_DIR = Path(os.environ.get("AISAAC_DATA", "./data"))
DB_PATH = DATA_DIR / "aisaac.db"
PAPERS_DIR = DATA_DIR / "papers"
CACHE_DIR = DATA_DIR / "cache"

for d in [DATA_DIR, PAPERS_DIR, CACHE_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ── LLM ──────────────────────────────────────────────────────────
ANTHROPIC_MODEL = "claude-sonnet-4-20250514"
ANTHROPIC_MAX_TOKENS = 8192

# ── Ingestion Tiers ──────────────────────────────────────────────

class Tier(Enum):
    CORE_REVIEWS = 1        # ~200 papers, key reviews + foundational
    HIGH_IMPACT = 2         # ~2000 most-cited per approach
    RECENT_FRONTIER = 3     # ~10K papers, 2020-2026
    FULL_CORPUS = 4         # everything else


# ── Theory Registry ──────────────────────────────────────────────

@dataclass
class TheoryDef:
    name: str
    slug: str
    key_object: str
    arxiv_categories: list[str]
    search_queries: list[str]
    key_reviews_arxiv_ids: list[str]   # manually curated Tier-1 seeds
    key_parameters: list[str]
    key_symmetries: list[str]
    estimated_papers: int


THEORIES: list[TheoryDef] = [
    TheoryDef(
        name="String Theory",
        slug="string_theory",
        key_object="Polyakov action, worldsheet, strings/branes",
        arxiv_categories=["hep-th"],
        search_queries=[
            "quantum gravity string theory",
            "string theory graviton scattering",
            "string theory black hole entropy microscopic",
            "string compactification quantum gravity",
            "AdS/CFT correspondence gravity",
        ],
        key_reviews_arxiv_ids=[
            "hep-th/9905111",   # MAGOO (Aharony et al, AdS/CFT review)
            "hep-th/0108200",   # Polchinski TASI lectures
            "0709.3555",        # Becker-Becker-Schwarz review lectures
            "1501.00007",       # Natsuume AdS/CFT textbook
            "hep-th/9601029",   # Strominger-Vafa BH entropy from D-branes
            "hep-th/9711053",   # Maldacena BH in string theory
            "gr-qc/9310024",    # Donoghue Newton correction from gravitons
            "hep-th/0206236",   # Bjerrum-Bohr et al Newton corrections
            "hep-th/0603001",   # Ryu-Takayanagi original
            "hep-th/0605073",   # Ryu-Takayanagi proof
            "hep-th/9809038",   # Amelino-Camelia modified dispersion
        ],
        key_parameters=["α' (string tension)", "g_s (string coupling)", "l_s (string length)"],
        key_symmetries=["conformal", "T-duality", "S-duality", "supersymmetry"],
        estimated_papers=30000,
    ),
    TheoryDef(
        name="Loop Quantum Gravity",
        slug="loop_quantum_gravity",
        key_object="Ashtekar connection, spin networks, spin foams",
        arxiv_categories=["gr-qc", "hep-th"],
        search_queries=[
            "loop quantum gravity",
            "spin foam models quantum gravity",
            "loop quantum gravity black hole entropy",
            "loop quantum gravity spectral dimension",
            "Ashtekar variables quantum gravity",
        ],
        key_reviews_arxiv_ids=[
            "gr-qc/0404018",   # Rovelli review
            "gr-qc/0306083",   # Thiemann review
            "1012.4707",       # Rovelli-Vidotto Covariant LQG
            "1607.05129",      # Dona-Speziale intro to spin foams
            "gr-qc/9411005",   # Rovelli-Smolin area spectrum
            "gr-qc/9412137",   # Ashtekar et al area eigenvalues
            "gr-qc/0002040",   # Kaul-Majumdar log correction to BH entropy
            "gr-qc/0405036",   # Meissner log correction
            "gr-qc/0407117",   # Corichi et al area gap
            "0811.1396",       # Modesto spectral dimension in LQG
            "1205.0971",       # Engle et al BH entropy in spin foams
        ],
        key_parameters=["γ (Immirzi parameter)", "l_P (Planck length)"],
        key_symmetries=["diffeomorphism invariance", "SU(2) gauge"],
        estimated_papers=5000,
    ),
    TheoryDef(
        name="Causal Dynamical Triangulations",
        slug="cdt",
        key_object="simplicial path integral with causality",
        arxiv_categories=["hep-th", "gr-qc"],
        search_queries=[
            "causal dynamical triangulations",
            "CDT quantum gravity spectral dimension",
            "dynamical triangulations phase diagram",
        ],
        key_reviews_arxiv_ids=[
            "1905.02782",      # Loll 2019 review
            "hep-th/0105267",  # Ambjorn-Jurkiewicz-Loll early review
            "1203.3591",       # Ambjorn et al review
            "hep-th/0505113",  # Ambjorn et al spectral dimension in CDT
            "1404.3851",       # CDT spectral dimension detailed
        ],
        key_parameters=["κ₀ (inverse Newton)", "κ₄ (cosmological)", "Δ (asymmetry)"],
        key_symmetries=["foliation-preserving diffeomorphisms"],
        estimated_papers=500,
    ),
    TheoryDef(
        name="Asymptotic Safety",
        slug="asymptotic_safety",
        key_object="functional RG for gravity, UV fixed point",
        arxiv_categories=["hep-th", "gr-qc"],
        search_queries=[
            "asymptotic safety quantum gravity",
            "functional renormalization group gravity",
            "gravitational UV fixed point",
            "asymptotic safety spectral dimension",
        ],
        key_reviews_arxiv_ids=[
            "1202.2274",       # Reuter-Saueressig review
            "0709.3851",       # Percacci review
            "1204.3541",       # Codello et al review
            "hep-th/9605030",  # Reuter original asymptotic safety
            "hep-th/0012232",  # Reuter running G
            "hep-th/0207143",  # Lauscher-Reuter UV fixed point
            "hep-th/0508202",  # Lauscher-Reuter spectral dimension
            "1402.6334",       # Falls et al BH entropy from AS
        ],
        key_parameters=["G(k) (running Newton)", "Λ(k) (running cosmological)", "g* (UV fixed point)"],
        key_symmetries=["diffeomorphism invariance"],
        estimated_papers=2000,
    ),
    TheoryDef(
        name="Causal Sets",
        slug="causal_sets",
        key_object="partially ordered set (causet)",
        arxiv_categories=["gr-qc", "hep-th"],
        search_queries=[
            "causal set quantum gravity",
            "causal set spectral dimension",
            "causal set cosmological constant",
            "Sorkin causal set",
        ],
        key_reviews_arxiv_ids=[
            "gr-qc/0309009",  # Sorkin review
            "1903.11544",     # Surya review
            "hep-th/0409024", # Bombelli et al entanglement entropy on causal sets
            "1507.01950",     # Dowker spectral dimension of causal sets
        ],
        key_parameters=["ρ (sprinkling density)", "l_P"],
        key_symmetries=["Lorentz invariance"],
        estimated_papers=800,
    ),
    TheoryDef(
        name="Hořava-Lifshitz Gravity",
        slug="horava_lifshitz",
        key_object="anisotropic scaling z=3 in UV",
        arxiv_categories=["hep-th", "gr-qc"],
        search_queries=[
            "Horava-Lifshitz gravity",
            "Horava gravity anisotropic scaling",
            "Horava-Lifshitz spectral dimension",
        ],
        key_reviews_arxiv_ids=[
            "0901.3775",      # Horava original
            "1007.5199",      # Mukohyama review
            "1605.03541",     # Sotiriou spectral dimension in HL
            "0905.2579",      # Calcagni spectral dimension HL
            "0909.3525",      # HL BH entropy
        ],
        key_parameters=["z (dynamical critical exponent)", "λ (coupling)"],
        key_symmetries=["foliation-preserving diffeomorphisms"],
        estimated_papers=1500,
    ),
    TheoryDef(
        name="Noncommutative Geometry",
        slug="noncommutative_geometry",
        key_object="spectral triple, [x^μ, x^ν] ≠ 0",
        arxiv_categories=["hep-th", "math-ph", "gr-qc"],
        search_queries=[
            "noncommutative geometry gravity",
            "noncommutative spacetime quantum gravity",
            "spectral triple gravity Connes",
        ],
        key_reviews_arxiv_ids=[
            "hep-th/0510059", # Szabo review
            "0901.0577",      # Connes-Marcolli overview
            "hep-th/0012051", # Amelino-Camelia et al NC dispersion relation
            "hep-th/0112090", # Douglas-Nekrasov NC field theory review
            "hep-th/0505072", # Rivelles NC corrections to gravity
        ],
        key_parameters=["θ (noncommutativity parameter)"],
        key_symmetries=["twisted diffeomorphisms", "Hopf algebra"],
        estimated_papers=2000,
    ),
    TheoryDef(
        name="Emergent Gravity / Holographic",
        slug="emergent_gravity",
        key_object="gravity from entanglement / thermodynamics",
        arxiv_categories=["hep-th", "gr-qc", "quant-ph"],
        search_queries=[
            "emergent gravity entanglement",
            "gravity from entanglement entropy",
            "ER=EPR",
            "Ryu-Takayanagi formula",
            "Verlinde entropic gravity",
            "Van Raamsdonk building spacetime entanglement",
        ],
        key_reviews_arxiv_ids=[
            "1001.0785",      # Verlinde entropic gravity
            "1005.3035",      # Van Raamsdonk
            "0905.1317",      # Ryu-Takayanagi review
            "1009.1136",      # Carlip spontaneous dimensional reduction review
            "hep-th/0305117", # Bousso holographic entropy bound
            "1304.4926",      # Maldacena-Susskind ER=EPR
        ],
        key_parameters=["S_EE (entanglement entropy)", "Ryu-Takayanagi surface"],
        key_symmetries=["entanglement structure"],
        estimated_papers=3000,
    ),
]

THEORY_BY_SLUG = {t.slug: t for t in THEORIES}


# ── Comparable Quantities ────────────────────────────────────────

class QuantityType(Enum):
    SPECTRAL_DIMENSION = "spectral_dimension"
    NEWTON_CORRECTION = "newton_correction"
    BH_ENTROPY = "black_hole_entropy"
    BH_ENTROPY_LOG_CORRECTION = "bh_entropy_log_correction"
    AREA_GAP = "area_gap"
    COSMOLOGICAL_CONSTANT = "cosmological_constant"
    GRAVITON_PROPAGATOR = "graviton_propagator_modification"
    ENTANGLEMENT_AREA_LAW = "entanglement_entropy_area_law"
    DISPERSION_RELATION = "dispersion_relation_modification"
    HEAT_KERNEL = "heat_kernel_coefficient"
    RUNNING_COUPLING = "running_gravitational_coupling"
    OTHER = "other"


# ── Normalization Constants ──────────────────────────────────────
# Standard symbols everything gets translated to

STANDARD_SYMBOLS = {
    "newton_constant": "G",
    "planck_length": "l_P",
    "planck_mass": "M_P",
    "cosmological_constant": "Lambda",
    "speed_of_light": "c",
    "hbar": "hbar",
    "boltzmann": "k_B",
    "spacetime_dim": "d",
    "spatial_dim": "d-1",
    # theory-specific (kept distinct)
    "immirzi": "gamma_I",
    "string_tension": "alpha_prime",
    "string_coupling": "g_s",
    "nc_parameter": "theta_NC",
    "horava_z": "z_HL",
}

# Common aliases → standard symbol
NOTATION_ALIASES = {
    # Newton's constant
    "G_N": "G", "G_n": "G", "kappa^2/16pi": "G",
    # Planck length
    "l_p": "l_P", "ell_P": "l_P", "l_{Pl}": "l_P", "l_{\\rm Pl}": "l_P",
    # Planck mass
    "M_p": "M_P", "m_P": "M_P", "M_{Pl}": "M_P",
    # Cosmological
    "\\Lambda": "Lambda", "lambda": "Lambda",
    # Immirzi
    "\\gamma": "gamma_I", "beta_I": "gamma_I",
}


# ── Formula Type Classification ──────────────────────────────────

class FormulaType(Enum):
    PREDICTION = "prediction"          # quantitative prediction
    KEY_EQUATION = "key_equation"      # defining equation of approach
    CORRECTION = "correction"          # correction to known result
    MAPPING = "mapping"                # explicit map to other theory
    DEFINITION = "definition"          # notation/definition (skip)
    INTERMEDIATE = "intermediate"      # derivation step (skip)


# ── Conjecture Templates ────────────────────────────────────────

class ConjectureType(Enum):
    EQUIVALENCE = "equivalence"        # X in A = Y in B under mapping
    UNIVERSALITY = "universality"      # same value across N theories
    LIMIT = "limit"                    # A → B in some limit
    CORRECTION = "correction"          # universal correction form
    DUALITY = "duality"                # strong ↔ weak coupling map
    MISSING_LINK = "missing_link"      # same result, different mechanism
    NEAR_MISS = "near_miss"            # almost equal — interesting discrepancy
    SIGN_FLIP = "sign_flip"            # same magnitude, opposite sign


# ── Pipeline Settings ────────────────────────────────────────────

@dataclass
class PipelineConfig:
    tier: Tier = Tier.CORE_REVIEWS
    max_papers_per_query: int = 100
    extraction_batch_size: int = 10
    comparison_threshold: float = 0.3   # minimum similarity to flag
    cluster_min_size: int = 3
    conjecture_min_evidence: int = 2    # min formulas supporting a conjecture
    verify_algebraic: bool = True
    verify_numerical: bool = True
    verify_dimensional: bool = True
    search_counterexamples: bool = True
    check_novelty: bool = True
    llm_temperature: float = 0.2        # low temp for extraction, higher for conjecture
    llm_conjecture_temperature: float = 0.7
