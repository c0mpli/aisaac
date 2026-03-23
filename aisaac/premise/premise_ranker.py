"""
Premise Ranker — pure computational scoring, NO LLM.

Ranks premise shifts on 6 criteria:
  1. HISTORICAL PATTERN MATCH (0-1): keyword overlap with ~15 breakthroughs
  2. CONVERGENCE SUPPORT (0-1): does the shift explain convergent results?
  3. OBSTACLE RESOLUTION (0-1): does the shift resolve known obstacles?
  4. CONSISTENCY CHECK (0-1): does it contradict empirical results? → 0
  5. NOVELTY (0-1): Semantic Scholar search for prior proposals
  6. SIMPLIFICATION (0-1): shorter description = simpler (heuristic)

Combined score = weighted sum, normalized to 0-1:
  consistency(3) + convergence(2) + obstacle_resolution(2)
  + simplification(2) + historical(1) + novelty(1)
"""
from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, field

from ..knowledge.base import KnowledgeBase

log = logging.getLogger(__name__)


# ── Weights ──────────────────────────────────────────────────────

WEIGHTS = {
    "consistency":        3.0,
    "convergence":        2.0,
    "obstacle_resolution": 2.0,
    "simplification":     2.0,
    "historical":         1.0,
    "novelty":            1.0,
}
TOTAL_WEIGHT = sum(WEIGHTS.values())  # 11.0


# ── Historical Breakthroughs ─────────────────────────────────────
# Each entry: (short label, keywords that characterize the breakthrough)

HISTORICAL_BREAKTHROUGHS: list[tuple[str, list[str]]] = [
    (
        "Einstein dropping absolute time -> special relativity",
        ["drop", "absolute", "time", "simultaneity", "relativity",
         "lorentz", "frame", "observer", "invariant"],
    ),
    (
        "Maldacena: gauge/gravity duality -> AdS/CFT",
        ["gauge", "gravity", "duality", "holographic", "ads", "cft",
         "boundary", "bulk", "correspondence", "maldacena"],
    ),
    (
        "Perelman: classify singularities instead of avoiding them",
        ["singularity", "singularities", "classify", "classification",
         "topology", "ricci", "flow", "surgery", "obstacle", "feature"],
    ),
    (
        "Shannon: abstract meaning from communication",
        ["information", "entropy", "abstract", "meaning", "communication",
         "channel", "capacity", "bit", "encoding", "drop", "semantic"],
    ),
    (
        "Boltzmann: micro to macro -> statistical mechanics",
        ["micro", "macro", "statistical", "thermodynamic", "ensemble",
         "counting", "states", "partition", "boltzmann", "emergent"],
    ),
    (
        "Dirac: relativistic QM -> antimatter prediction",
        ["negative", "energy", "antimatter", "positron", "dirac",
         "spinor", "relativistic", "obstacle", "prediction", "equation"],
    ),
    (
        "Hawking: QM + GR -> black hole radiation",
        ["hawking", "radiation", "black hole", "quantum", "semiclassical",
         "temperature", "combine", "unify", "information", "evaporation"],
    ),
    (
        "'t Hooft: gauge theories are renormalizable",
        ["renormalizab", "gauge", "non-abelian", "hooft", "renormalization",
         "yang-mills", "predictive", "ultraviolet", "finite", "divergence"],
    ),
    (
        "Wilson RG -> universality classes",
        ["renormalization group", "universality", "fixed point", "scaling",
         "critical", "wilson", "flow", "coarse", "effective", "irrelevant"],
    ),
    (
        "Witten: unifying string theories -> M-theory",
        ["unify", "unification", "string", "m-theory", "duality",
         "eleven", "dimension", "strong coupling", "witten", "membrane"],
    ),
    (
        "Einstein: gravity = geometry (general relativity)",
        ["geometry", "curvature", "metric", "geodesic", "equivalence principle",
         "spacetime", "einstein", "general relativity", "tensor"],
    ),
    (
        "Noether: symmetry -> conservation law",
        ["symmetry", "conservation", "noether", "invariance", "charge",
         "continuous", "generator", "current"],
    ),
    (
        "Bekenstein-Hawking: entropy proportional to area",
        ["entropy", "area", "horizon", "bekenstein", "proportional",
         "thermodynamic", "black hole", "holographic", "bound"],
    ),
    (
        "Verlinde: gravity as entropic force",
        ["entropic", "emergent", "thermodynamic", "temperature", "screen",
         "verlinde", "information", "holographic", "force"],
    ),
    (
        "Jacobson: Einstein equations from thermodynamics",
        ["thermodynamic", "einstein equation", "entropy", "horizon",
         "jacobson", "equilibrium", "clausius", "emergent", "derive"],
    ),
]


# ── Empirical Constraints (hard-coded) ───────────────────────────
# Keywords that signal contradiction with established physics.
# If a premise shift mentions VIOLATING any of these, consistency → 0.

EMPIRICAL_RED_FLAGS = [
    ["violat", "lorentz invariance", "low energy"],
    ["break", "unitarity"],
    ["violat", "energy conservation"],
    ["contradict", "equivalence principle"],
    ["negative", "entropy"],
    ["superluminal", "signal"],
    ["violat", "second law"],
    ["perpetual motion"],
]


# ── Ranker ───────────────────────────────────────────────────────

@dataclass
class RankingResult:
    shift_id: int
    historical_score: float = 0.0
    convergence_score: float = 0.0
    obstacle_score: float = 0.0
    consistency_score: float = 1.0  # default: passes
    novelty_score: float = 0.5     # default: uncertain
    simplification_score: float = 0.5
    combined_score: float = 0.0
    details: dict = field(default_factory=dict)


class PremiseRanker:
    """
    Rank premise shifts using pure computation — no LLM calls.

    Each criterion is scored 0-1 using keyword matching, text
    analysis, and (for novelty) Semantic Scholar lookups.
    """

    def __init__(self, kb: KnowledgeBase, check_novelty_online: bool = True):
        self.kb = kb
        self.check_novelty_online = check_novelty_online
        # Cache KB data once
        self._contradictions: list[dict] | None = None
        self._convergences: list[dict] | None = None
        self._obstacles: list[dict] | None = None

    def _load_kb_context(self) -> None:
        """Load KB context once for the ranking session."""
        if self._contradictions is None:
            self._contradictions = self.kb.get_contradictions()
            self._obstacles = self.kb.get_obstacles()
            conjectures = self.kb.get_conjectures()
            self._convergences = [
                c for c in conjectures
                if c.get("conjecture_type") == "universality"
                or c.get("status") == "verified"
            ]

    def rank_all(self, min_score: float = 0.0) -> list[RankingResult]:
        """
        Rank all premise shifts in the KB.

        Returns sorted list of RankingResults (highest first).
        Also updates scores in the DB.
        """
        self._load_kb_context()
        shifts = self.kb.get_premise_shifts(min_score=0.0)
        results = []
        for shift in shifts:
            result = self.rank_one(shift)
            results.append(result)

        results.sort(key=lambda r: r.combined_score, reverse=True)
        log.info(
            "Ranked %d premise shifts. Top score: %.3f",
            len(results),
            results[0].combined_score if results else 0.0,
        )
        return [r for r in results if r.combined_score >= min_score]

    def rank_one(self, shift: dict) -> RankingResult:
        """Score a single premise shift on all 6 criteria."""
        self._load_kb_context()

        shift_id = shift.get("id", 0)
        proposed = shift.get("proposed_shift", "")
        current = shift.get("current_premise", "")
        evidence_for = shift.get("evidence_for", "")
        evidence_against = shift.get("evidence_against", "")
        affected = shift.get("affected_theories", "[]")
        full_text = f"{current} {proposed} {evidence_for}".lower()

        result = RankingResult(shift_id=shift_id)

        # 1. Historical pattern match
        result.historical_score = self._score_historical(full_text)
        result.details["historical_match"] = self._best_historical_match(full_text)

        # 2. Convergence support
        result.convergence_score = self._score_convergence(full_text)

        # 3. Obstacle resolution
        result.obstacle_score = self._score_obstacle_resolution(full_text)

        # 4. Consistency check
        result.consistency_score = self._score_consistency(full_text)

        # 5. Novelty (Semantic Scholar)
        result.novelty_score = self._score_novelty(proposed)

        # 6. Simplification heuristic
        result.simplification_score = self._score_simplification(
            current, proposed,
        )

        # Combined weighted score, normalized to 0-1
        raw = (
            WEIGHTS["consistency"] * result.consistency_score
            + WEIGHTS["convergence"] * result.convergence_score
            + WEIGHTS["obstacle_resolution"] * result.obstacle_score
            + WEIGHTS["simplification"] * result.simplification_score
            + WEIGHTS["historical"] * result.historical_score
            + WEIGHTS["novelty"] * result.novelty_score
        )
        result.combined_score = raw / TOTAL_WEIGHT

        # Update DB
        self._update_score(shift_id, result.combined_score)

        log.debug(
            "Shift #%d: hist=%.2f conv=%.2f obst=%.2f cons=%.2f "
            "nov=%.2f simp=%.2f => combined=%.3f",
            shift_id,
            result.historical_score,
            result.convergence_score,
            result.obstacle_score,
            result.consistency_score,
            result.novelty_score,
            result.simplification_score,
            result.combined_score,
        )
        return result

    # ── Criterion 1: Historical Pattern Match ────────────────────

    def _score_historical(self, text: str) -> float:
        """
        Keyword overlap between premise shift text and historical
        breakthroughs. Returns best match score (0-1).
        """
        best = 0.0
        for _label, keywords in HISTORICAL_BREAKTHROUGHS:
            hits = sum(1 for kw in keywords if kw in text)
            score = min(hits / max(len(keywords) * 0.4, 1), 1.0)
            if score > best:
                best = score
        return best

    def _best_historical_match(self, text: str) -> str:
        """Return the label of the best-matching historical breakthrough."""
        best_score = 0.0
        best_label = "none"
        for label, keywords in HISTORICAL_BREAKTHROUGHS:
            hits = sum(1 for kw in keywords if kw in text)
            score = hits / max(len(keywords), 1)
            if score > best_score:
                best_score = score
                best_label = label
        return best_label

    # ── Criterion 2: Convergence Support ─────────────────────────

    def _score_convergence(self, text: str) -> float:
        """
        Does the shift explain or reference existing convergent results?
        Keyword overlap between the shift and known convergences.
        """
        if not self._convergences:
            return 0.0

        total_overlap = 0.0
        for conv in self._convergences:
            conv_text = (
                f"{conv.get('title', '')} {conv.get('statement_natural', '')}"
            ).lower()
            conv_words = set(_extract_content_words(conv_text))
            shift_words = set(_extract_content_words(text))
            if not conv_words:
                continue
            overlap = len(conv_words & shift_words) / len(conv_words)
            total_overlap = max(total_overlap, overlap)

        return min(total_overlap, 1.0)

    # ── Criterion 3: Obstacle Resolution ─────────────────────────

    def _score_obstacle_resolution(self, text: str) -> float:
        """
        Does the shift address known obstacles?
        Keyword overlap between shift text and obstacle descriptions.
        """
        if not self._obstacles:
            return 0.0

        total_overlap = 0.0
        for obst in self._obstacles:
            obst_text = (
                f"{obst.get('obstacle_type', '')} {obst.get('description', '')}"
            ).lower()
            obst_words = set(_extract_content_words(obst_text))
            shift_words = set(_extract_content_words(text))
            if not obst_words:
                continue
            overlap = len(obst_words & shift_words) / len(obst_words)
            total_overlap = max(total_overlap, overlap)

        return min(total_overlap, 1.0)

    # ── Criterion 4: Consistency Check ───────────────────────────

    def _score_consistency(self, text: str) -> float:
        """
        Check if the shift would violate well-established empirical
        results. Returns 0 if a red flag is detected, 1 otherwise.

        This is deliberately conservative: if the shift explicitly
        mentions violating a fundamental principle, it scores 0.
        Ambiguous cases score 1 (benefit of the doubt).
        """
        for flag_keywords in EMPIRICAL_RED_FLAGS:
            if all(kw in text for kw in flag_keywords):
                log.debug(
                    "Consistency red flag: shift matches %s", flag_keywords,
                )
                return 0.0
        return 1.0

    # ── Criterion 5: Novelty (Semantic Scholar) ──────────────────

    def _score_novelty(self, proposed_shift: str) -> float:
        """
        Search Semantic Scholar for papers that already propose
        this shift. More papers = less novel.
        """
        if not self.check_novelty_online:
            return 0.5  # uncertain

        # Build a compact search query from the proposed shift
        query = _build_search_query(proposed_shift)
        if not query or len(query) < 10:
            return 0.5

        papers = _search_semantic_scholar(query)
        if papers is None:
            return 0.5  # API unavailable

        if len(papers) == 0:
            return 1.0  # nobody proposed this

        highly_cited = sum(1 for p in papers if (p.get("citationCount") or 0) > 20)

        if highly_cited >= 3:
            return 0.0  # well-known idea
        if highly_cited >= 1:
            return 0.2  # somewhat known
        if len(papers) >= 5:
            return 0.3  # discussed but not famous
        if len(papers) >= 2:
            return 0.5  # a few mentions
        return 0.7  # barely discussed

    # ── Criterion 6: Simplification ──────────────────────────────

    def _score_simplification(self, current: str, proposed: str) -> float:
        """
        Heuristic: does the shift make things simpler?
        Compare description lengths. Shorter proposed = simpler.
        Also reward keywords that signal simplification.
        """
        simplification_keywords = [
            "unify", "unification", "single", "simpler", "reduce",
            "eliminate", "remove", "drop", "one", "emergent", "derive",
            "recover", "explain", "subsume",
        ]
        proposed_lower = proposed.lower()

        # Length ratio: shorter proposed relative to current = simpler
        len_current = max(len(current.split()), 1)
        len_proposed = max(len(proposed.split()), 1)
        length_score = min(len_current / len_proposed, 2.0) / 2.0

        # Keyword bonus
        keyword_hits = sum(1 for kw in simplification_keywords if kw in proposed_lower)
        keyword_score = min(keyword_hits / 3.0, 1.0)

        return 0.5 * length_score + 0.5 * keyword_score

    # ── DB Update ────────────────────────────────────────────────

    def _update_score(self, shift_id: int, score: float) -> None:
        """Update the score for a premise shift in the DB."""
        if shift_id <= 0:
            return
        try:
            self.kb.conn.execute(
                "UPDATE premise_shifts SET score = ? WHERE id = ?",
                (score, shift_id),
            )
            self.kb.conn.commit()
        except Exception as e:
            log.warning("Failed to update score for shift #%d: %s", shift_id, e)


# ── Utility Functions ────────────────────────────────────────────

_STOP_WORDS = frozenset({
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "can", "shall", "to", "of", "in", "for",
    "on", "with", "at", "by", "from", "as", "into", "through", "during",
    "before", "after", "above", "below", "between", "out", "off", "over",
    "under", "again", "further", "then", "once", "here", "there", "when",
    "where", "why", "how", "all", "each", "every", "both", "few", "more",
    "most", "other", "some", "such", "no", "nor", "not", "only", "own",
    "same", "so", "than", "too", "very", "and", "but", "or", "if", "that",
    "this", "these", "those", "it", "its", "what", "which", "who", "whom",
})


def _extract_content_words(text: str) -> list[str]:
    """Extract meaningful words (no stop words, no short tokens)."""
    words = re.findall(r"[a-z][a-z_-]{2,}", text.lower())
    return [w for w in words if w not in _STOP_WORDS]


def _build_search_query(text: str, max_words: int = 8) -> str:
    """Build a compact search query from premise shift text."""
    words = _extract_content_words(text)
    # Prioritize longer, more specific words
    words.sort(key=len, reverse=True)
    selected = words[:max_words]
    return " ".join(selected)


def _search_semantic_scholar(
    query: str, limit: int = 10,
) -> list[dict] | None:
    """Search Semantic Scholar. Returns None on API failure."""
    try:
        import requests
    except ImportError:
        log.warning("requests not installed; skipping Semantic Scholar check")
        return None

    api_url = "https://api.semanticscholar.org/graph/v1/paper/search"
    try:
        resp = requests.get(
            api_url,
            params={
                "query": query,
                "limit": limit,
                "fields": "title,year,citationCount",
            },
            timeout=10,
        )
        if resp.status_code == 429:
            log.debug("Semantic Scholar rate limited; waiting 5s")
            time.sleep(5)
            resp = requests.get(
                api_url,
                params={
                    "query": query,
                    "limit": limit,
                    "fields": "title,year,citationCount",
                },
                timeout=10,
            )
        if resp.status_code != 200:
            log.debug("Semantic Scholar returned %d", resp.status_code)
            return None
        return resp.json().get("data", [])
    except Exception as e:
        log.debug("Semantic Scholar search failed: %s", e)
        return None
