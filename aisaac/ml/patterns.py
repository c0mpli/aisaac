"""
ML Pattern Detection Layer.

Classical ML for finding patterns that pairwise comparison misses:
- Formula embedding (structural + semantic + fingerprint)
- Cross-theory clustering (HDBSCAN)
- Universality detection (same prediction across all theories)
- Anomaly detection (unexpected agreements/disagreements)

This layer FINDS candidates. Verification proves/disproves them.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
from scipy.spatial.distance import cosine, pdist, squareform
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA

from ..knowledge.base import KnowledgeBase

log = logging.getLogger(__name__)


# ── Formula Embedding ────────────────────────────────────────────

@dataclass 
class FormulaEmbedding:
    formula_id: int
    theory_slug: str
    quantity_type: str
    structural_vec: np.ndarray      # from expression tree
    fingerprint_vec: np.ndarray     # from numerical evaluation
    feature_vec: np.ndarray         # hand-engineered features
    combined_vec: np.ndarray = field(default_factory=lambda: np.array([]))


class FormulaEmbedder:
    """
    Multiple embedding strategies combined:
    
    1. STRUCTURAL: expression tree features
    2. FINGERPRINT: numerical behavior on random inputs  
    3. FEATURE: hand-engineered physics features
    
    (Semantic embedding via sentence-transformers added when scaling up)
    """

    # Operators/functions we track in structural embedding
    OPS = ["Add", "Mul", "Pow", "exp", "log", "sqrt", "sin", "cos", "Rational"]
    STRUCT_DIM = len(OPS) + 5  # ops + depth + n_symbols + n_terms + n_constants + total_nodes

    FINGER_DIM = 50    # number of test points for fingerprint
    FEATURE_DIM = 20   # hand-engineered features

    def __init__(self):
        self.scaler = StandardScaler()
        self._fitted = False

    def embed_formula(self, formula: dict) -> Optional[FormulaEmbedding]:
        """Create multi-strategy embedding for a single formula."""
        expr_str = formula.get("normalized_sympy") or formula.get("sympy_expr", "")
        
        struct = self._structural_embed(expr_str)
        finger = self._fingerprint_embed(expr_str)
        feat = self._feature_embed(formula, expr_str)

        if struct is None:
            struct = np.zeros(self.STRUCT_DIM)
        if finger is None:
            finger = np.zeros(self.FINGER_DIM)
        if feat is None:
            feat = np.zeros(self.FEATURE_DIM)

        return FormulaEmbedding(
            formula_id=formula["id"],
            theory_slug=formula["theory_slug"],
            quantity_type=formula["quantity_type"],
            structural_vec=struct,
            fingerprint_vec=finger,
            feature_vec=feat,
            combined_vec=np.concatenate([struct, finger, feat]),
        )

    def embed_all(self, formulas: list[dict]) -> list[FormulaEmbedding]:
        """Embed all formulas and normalize."""
        embeddings = []
        for f in formulas:
            e = self.embed_formula(f)
            if e is not None:
                embeddings.append(e)

        if embeddings:
            # Normalize combined vectors
            vecs = np.array([e.combined_vec for e in embeddings])
            if len(vecs) > 1:
                vecs = self.scaler.fit_transform(vecs)
                self._fitted = True
                for i, e in enumerate(embeddings):
                    e.combined_vec = vecs[i]

        return embeddings

    def _structural_embed(self, expr_str: str) -> Optional[np.ndarray]:
        """Count operators, depth, symbols in expression tree."""
        if not expr_str:
            return None
        try:
            import sympy as sp
            expr = sp.sympify(expr_str)
            if expr is None or not isinstance(expr, sp.Basic):
                return None
        except Exception:
            return None

        vec = np.zeros(self.STRUCT_DIM)

        try:
            # Count each operator type
            tree_str = sp.srepr(expr)
            for i, op in enumerate(self.OPS):
                vec[i] = tree_str.count(op)

            # Additional features
            vec[len(self.OPS)] = self._tree_depth(expr)
            vec[len(self.OPS) + 1] = len(expr.free_symbols) if hasattr(expr, 'free_symbols') else 0
            vec[len(self.OPS) + 2] = len(expr.as_ordered_terms()) if hasattr(expr, 'as_ordered_terms') else 1
            # Count numerical constants
            atoms = expr.atoms() if hasattr(expr, 'atoms') else set()
            vec[len(self.OPS) + 3] = sum(1 for a in atoms if hasattr(a, 'is_number') and a.is_number)
            vec[len(self.OPS) + 4] = self._count_nodes(expr)
        except Exception:
            pass

        return vec

    def _fingerprint_embed(self, expr_str: str) -> Optional[np.ndarray]:
        """Evaluate formula on fixed random inputs to create numerical fingerprint."""
        if not expr_str:
            return None
        try:
            import sympy as sp
            expr = sp.sympify(expr_str)
            if expr is None or not isinstance(expr, sp.Basic):
                return None
        except Exception:
            return None

        symbols = sorted(expr.free_symbols, key=str) if hasattr(expr, 'free_symbols') else []
        if not symbols:
            # Constant expression
            try:
                val = float(expr.evalf())
                return np.full(self.FINGER_DIM, val)
            except Exception:
                return None

        # Fixed random points (seeded for reproducibility)
        rng = np.random.default_rng(12345)
        # Use positive values, log-uniform distribution (physics-friendly)
        test_points = np.exp(rng.uniform(-2, 2, (self.FINGER_DIM, len(symbols))))

        fingerprint = np.zeros(self.FINGER_DIM)
        for i in range(self.FINGER_DIM):
            subs = {s: float(test_points[i, j]) for j, s in enumerate(symbols)}
            try:
                val = complex(expr.subs(subs))
                fingerprint[i] = val.real if not np.isnan(val.real) and not np.isinf(val.real) else 0.0
            except Exception:
                fingerprint[i] = 0.0

        # Normalize to prevent scale issues
        norm = np.linalg.norm(fingerprint)
        if norm > 0:
            fingerprint /= norm

        return fingerprint

    def _feature_embed(self, formula: dict, expr_str: str) -> Optional[np.ndarray]:
        """Hand-engineered physics features."""
        vec = np.zeros(self.FEATURE_DIM)

        # Theory one-hot (8 theories)
        theory_map = {
            "string_theory": 0, "loop_quantum_gravity": 1, "cdt": 2,
            "asymptotic_safety": 3, "causal_sets": 4, "horava_lifshitz": 5,
            "noncommutative_geometry": 6, "emergent_gravity": 7,
        }
        idx = theory_map.get(formula.get("theory_slug", ""), -1)
        if 0 <= idx < 8:
            vec[idx] = 1.0

        # Quantity type features
        qt_map = {
            "spectral_dimension": 8, "newton_correction": 9,
            "black_hole_entropy": 10, "bh_entropy_log_correction": 11,
            "dispersion_relation_modification": 12,
            "graviton_propagator_modification": 13,
        }
        idx = qt_map.get(formula.get("quantity_type", ""), -1)
        if 0 <= idx < self.FEATURE_DIM:
            vec[idx] = 1.0

        # Expression complexity features (remaining slots)
        if expr_str:
            vec[14] = len(expr_str)                    # expression length
            vec[15] = expr_str.count("**")             # number of powers
            vec[16] = expr_str.count("log") + expr_str.count("ln")
            vec[17] = expr_str.count("exp")
            vec[18] = expr_str.count("pi")
            vec[19] = formula.get("confidence", 0.5)

        return vec

    def _tree_depth(self, expr, depth: int = 0) -> int:
        if depth > 50:
            return depth
        try:
            args = expr.args
            if not args or not isinstance(args, (list, tuple)):
                return 0
            return 1 + max(self._tree_depth(a, depth + 1) for a in args)
        except (TypeError, AttributeError):
            return 0

    def _count_nodes(self, expr, depth: int = 0) -> int:
        if depth > 50:
            return 1
        try:
            args = expr.args
            if not args or not isinstance(args, (list, tuple)):
                return 1
            return 1 + sum(self._count_nodes(a, depth + 1) for a in args)
        except (TypeError, AttributeError):
            return 1


# ── Cross-Theory Clustering ─────────────────────────────────────

@dataclass
class Cluster:
    cluster_id: int
    formula_ids: list[int]
    theories: list[str]
    quantity_types: list[str]
    centroid: np.ndarray
    is_cross_theory: bool           # involves 2+ theories
    is_universal: bool              # involves all/most theories
    size: int = 0


class CrossTheoryClusterer:
    """
    Cluster formulas from all theories and find cross-theory clusters.
    
    Key insight: if formulas from DIFFERENT theories cluster together,
    they might describe the same physics in different languages.
    """

    def __init__(self, min_cluster_size: int = 3):
        self.min_cluster_size = min_cluster_size

    def cluster(
        self, embeddings: list[FormulaEmbedding], 
        n_theories_total: int = 8,
    ) -> list[Cluster]:
        """Cluster formula embeddings and identify cross-theory clusters."""
        if len(embeddings) < self.min_cluster_size:
            return []

        vecs = np.array([e.combined_vec for e in embeddings])

        # Use HDBSCAN for density-based clustering (handles varying density)
        try:
            import hdbscan
            clusterer = hdbscan.HDBSCAN(
                min_cluster_size=self.min_cluster_size,
                min_samples=2,
                metric="euclidean",
            )
            labels = clusterer.fit_predict(vecs)
        except ImportError:
            # Fallback to sklearn AgglomerativeClustering
            from sklearn.cluster import AgglomerativeClustering
            n_clusters = max(2, len(embeddings) // 5)
            clusterer = AgglomerativeClustering(n_clusters=n_clusters)
            labels = clusterer.fit_predict(vecs)

        clusters = []
        unique_labels = set(labels)
        unique_labels.discard(-1)  # remove noise label

        for label in sorted(unique_labels):
            members = [e for e, l in zip(embeddings, labels) if l == label]
            theories = list(set(e.theory_slug for e in members))
            qtypes = list(set(e.quantity_type for e in members))
            centroid = np.mean([e.combined_vec for e in members], axis=0)

            c = Cluster(
                cluster_id=int(label),
                formula_ids=[e.formula_id for e in members],
                theories=theories,
                quantity_types=qtypes,
                centroid=centroid,
                is_cross_theory=len(theories) >= 2,
                is_universal=len(theories) >= max(3, n_theories_total // 2),
                size=len(members),
            )
            clusters.append(c)

        # Sort: universal first, then cross-theory, then single-theory
        clusters.sort(key=lambda c: (c.is_universal, c.is_cross_theory, c.size), reverse=True)

        n_cross = sum(1 for c in clusters if c.is_cross_theory)
        n_universal = sum(1 for c in clusters if c.is_universal)
        log.info(
            f"Found {len(clusters)} clusters: "
            f"{n_universal} universal, {n_cross} cross-theory"
        )
        return clusters


# ── Universality Detector ────────────────────────────────────────

@dataclass
class UniversalityResult:
    quantity_type: str
    theories_agree: list[str]
    theories_disagree: list[str]
    consensus_value: Optional[float]    # if all agree on a number
    spread: float                        # how much they vary
    is_universal: bool
    details: dict = field(default_factory=dict)


class UniversalityDetector:
    """
    For each comparable quantity, check if all theories give the same answer.
    
    Known universalities (validation):
    - Spectral dimension → 2 at Planck scale
    - BH entropy → A/4 (leading term)
    
    Looking for UNKNOWN universalities.
    """

    def detect(
        self, kb: KnowledgeBase, quantity_type: str,
        tolerance: float = 0.1,
    ) -> Optional[UniversalityResult]:
        """
        Check if predictions for a quantity are universal across theories.
        """
        predictions = kb.get_predictions_for_quantity(quantity_type)
        if len(predictions) < 2:
            return None

        # Group by theory
        by_theory: dict[str, list[dict]] = {}
        for p in predictions:
            slug = p["theory_slug"]
            by_theory.setdefault(slug, []).append(p)

        # Extract numerical values where available
        values_by_theory: dict[str, list[float]] = {}
        for slug, preds in by_theory.items():
            vals = []
            for p in preds:
                # Try to extract numerical value from sympy expression
                try:
                    import sympy as sp
                    expr = sp.sympify(p.get("normalized_sympy") or p.get("sympy_expr", ""))
                    # If it's a pure number
                    if expr.is_number:
                        vals.append(float(expr.evalf()))
                except Exception:
                    pass
            if vals:
                values_by_theory[slug] = vals

        if len(values_by_theory) < 2:
            # Not enough numerical values for comparison
            return UniversalityResult(
                quantity_type=quantity_type,
                theories_agree=list(by_theory.keys()),
                theories_disagree=[],
                consensus_value=None,
                spread=float("inf"),
                is_universal=False,
                details={"reason": "insufficient numerical data"},
            )

        # Compute consensus
        all_values = []
        theory_means = {}
        for slug, vals in values_by_theory.items():
            mean = np.mean(vals)
            theory_means[slug] = mean
            all_values.extend(vals)

        global_mean = np.mean(all_values)
        global_std = np.std(all_values) if len(all_values) > 1 else 0

        # Check which theories agree with consensus
        agree = []
        disagree = []
        for slug, mean in theory_means.items():
            if abs(mean - global_mean) / max(abs(global_mean), 1e-30) < tolerance:
                agree.append(slug)
            else:
                disagree.append(slug)

        spread = global_std / max(abs(global_mean), 1e-30)
        is_universal = len(disagree) == 0 and len(agree) >= 3

        return UniversalityResult(
            quantity_type=quantity_type,
            theories_agree=agree,
            theories_disagree=disagree,
            consensus_value=global_mean,
            spread=spread,
            is_universal=is_universal,
            details={
                "theory_means": theory_means,
                "global_mean": global_mean,
                "global_std": global_std,
                "n_theories": len(values_by_theory),
                "tolerance": tolerance,
            },
        )


# ── Anomaly Detector ────────────────────────────────────────────

@dataclass
class Anomaly:
    anomaly_type: str           # unexpected_agreement | unexpected_disagreement | near_miss | missing | sign_flip
    description: str
    theories_involved: list[str]
    formula_ids: list[int]
    significance: float          # 0-1
    details: dict = field(default_factory=dict)


class AnomalyDetector:
    """
    Find things that DON'T match expected patterns.
    Often the most interesting findings.
    """

    def detect_from_clusters(
        self, clusters: list[Cluster], embeddings: list[FormulaEmbedding],
    ) -> list[Anomaly]:
        """Find anomalies in clustering results."""
        anomalies = []

        # Build lookup
        emb_by_id = {e.formula_id: e for e in embeddings}
        emb_by_theory: dict[str, list[FormulaEmbedding]] = {}
        for e in embeddings:
            emb_by_theory.setdefault(e.theory_slug, []).append(e)

        # 1. UNEXPECTED AGREEMENT: cross-theory clusters between
        #    theories with very different foundations
        distant_pairs = [
            ("string_theory", "loop_quantum_gravity"),
            ("causal_sets", "noncommutative_geometry"),
            ("cdt", "emergent_gravity"),
        ]
        for c in clusters:
            if c.is_cross_theory:
                for t1, t2 in distant_pairs:
                    if t1 in c.theories and t2 in c.theories:
                        anomalies.append(Anomaly(
                            anomaly_type="unexpected_agreement",
                            description=f"Formulas from {t1} and {t2} cluster together "
                                        f"(cluster {c.cluster_id}, {c.size} members)",
                            theories_involved=[t1, t2],
                            formula_ids=c.formula_ids,
                            significance=0.8,
                            details={"cluster_id": c.cluster_id, "all_theories": c.theories},
                        ))

        # 2. NEAR-MISS: formulas close in embedding space but from different theories
        for i, e1 in enumerate(embeddings):
            for e2 in embeddings[i+1:]:
                if e1.theory_slug == e2.theory_slug:
                    continue
                dist = cosine(e1.combined_vec, e2.combined_vec)
                if 0.05 < dist < 0.15:  # very close but not identical
                    anomalies.append(Anomaly(
                        anomaly_type="near_miss",
                        description=f"Near-miss between {e1.theory_slug} and {e2.theory_slug} "
                                    f"(distance={dist:.3f})",
                        theories_involved=[e1.theory_slug, e2.theory_slug],
                        formula_ids=[e1.formula_id, e2.formula_id],
                        significance=1.0 - dist,
                        details={"cosine_distance": dist},
                    ))

        # 3. OUTLIER: formula that doesn't cluster with anything
        # (could be a unique prediction of one theory)
        all_clustered = set()
        for c in clusters:
            all_clustered.update(c.formula_ids)
        
        unclustered = [e for e in embeddings if e.formula_id not in all_clustered]
        for e in unclustered:
            if e.quantity_type != "other":
                anomalies.append(Anomaly(
                    anomaly_type="missing",
                    description=f"Formula from {e.theory_slug} for {e.quantity_type} "
                                f"doesn't match any other theory",
                    theories_involved=[e.theory_slug],
                    formula_ids=[e.formula_id],
                    significance=0.5,
                    details={"quantity_type": e.quantity_type},
                ))

        anomalies.sort(key=lambda a: a.significance, reverse=True)
        log.info(f"Found {len(anomalies)} anomalies")
        return anomalies

    def detect_from_universality(
        self, results: list[UniversalityResult],
    ) -> list[Anomaly]:
        """Find anomalies in universality analysis."""
        anomalies = []
        for r in results:
            if r.theories_disagree and r.theories_agree:
                # Most theories agree, some don't → interesting
                anomalies.append(Anomaly(
                    anomaly_type="unexpected_disagreement",
                    description=f"{r.quantity_type}: {len(r.theories_agree)} theories agree "
                                f"(value ≈ {r.consensus_value:.4f}), but "
                                f"{', '.join(r.theories_disagree)} disagree",
                    theories_involved=r.theories_agree + r.theories_disagree,
                    formula_ids=[],
                    significance=len(r.theories_agree) / (len(r.theories_agree) + len(r.theories_disagree)),
                    details=r.details,
                ))
        return anomalies


# ── Visualization ────────────────────────────────────────────────

def create_embedding_plot(
    embeddings: list[FormulaEmbedding],
    clusters: list[Cluster],
    output_path: str = "formula_space.png",
):
    """Create 2D visualization of formula embedding space."""
    import matplotlib.pyplot as plt

    vecs = np.array([e.combined_vec for e in embeddings])
    theories = [e.theory_slug for e in embeddings]

    # Reduce to 2D
    if vecs.shape[1] > 2:
        pca = PCA(n_components=2)
        vecs_2d = pca.fit_transform(vecs)
    else:
        vecs_2d = vecs

    theory_colors = {
        "string_theory": "#e41a1c",
        "loop_quantum_gravity": "#377eb8",
        "cdt": "#4daf4a",
        "asymptotic_safety": "#984ea3",
        "causal_sets": "#ff7f00",
        "horava_lifshitz": "#ffff33",
        "noncommutative_geometry": "#a65628",
        "emergent_gravity": "#f781bf",
    }

    fig, ax = plt.subplots(1, 1, figsize=(12, 8))

    for theory, color in theory_colors.items():
        mask = [t == theory for t in theories]
        if any(mask):
            pts = vecs_2d[mask]
            ax.scatter(pts[:, 0], pts[:, 1], c=color, label=theory, alpha=0.7, s=30)

    # Highlight cross-theory clusters
    cluster_map = {}
    for c in clusters:
        for fid in c.formula_ids:
            cluster_map[fid] = c

    for i, e in enumerate(embeddings):
        if e.formula_id in cluster_map:
            c = cluster_map[e.formula_id]
            if c.is_cross_theory:
                ax.scatter(
                    vecs_2d[i, 0], vecs_2d[i, 1],
                    edgecolors="black", facecolors="none",
                    s=100, linewidths=2,
                )

    ax.set_title("Formula Embedding Space (cross-theory clusters circled)")
    ax.legend(loc="best", fontsize=8)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()
    log.info(f"Embedding plot saved to {output_path}")
