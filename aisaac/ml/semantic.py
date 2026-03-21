"""
Semantic Formula Embedder.

Embeds formulas by their PHYSICAL MEANING, not just their mathematical structure.
Two formulas about the same physics should have similar embeddings even if
the math looks completely different.

Uses sentence-transformers to embed natural language descriptions of formulas.
Combined with structural and fingerprint embeddings from patterns.py for
maximum detection power.
"""
from __future__ import annotations

import logging
from typing import Optional

import numpy as np

log = logging.getLogger(__name__)


class SemanticEmbedder:
    """
    Embed formula descriptions using sentence-transformers.
    
    The insight: formulas from different theories about the same
    physical quantity should have similar description embeddings
    even when the math looks completely different.
    
    Example:
    - LQG: "Area spectrum eigenvalue with Immirzi parameter"
    - String theory: "Minimum area from string tension"
    These describe related physics → similar embeddings.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = None

    @property
    def model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self.model_name)
                log.info(f"Loaded sentence-transformer: {self.model_name}")
            except ImportError:
                log.warning("sentence-transformers not installed, semantic embedding disabled")
                return None
        return self._model

    def embed_formula(self, formula: dict) -> Optional[np.ndarray]:
        """
        Embed a single formula by its physical description.
        
        Constructs a rich text representation combining:
        - The description
        - The quantity type
        - The theory
        - The regime of validity
        - The approximations used
        """
        if self.model is None:
            return None

        # Build rich text description
        parts = []
        
        desc = formula.get("description", "")
        if desc:
            parts.append(desc)
        
        qt = formula.get("quantity_type", "")
        if qt and qt != "other":
            parts.append(f"This formula predicts the {qt.replace('_', ' ')}.")
        
        theory = formula.get("theory_slug", "")
        if theory:
            parts.append(f"Derived in the {theory.replace('_', ' ')} approach.")
        
        regime = formula.get("regime", "")
        if regime:
            parts.append(f"Valid in the {regime} regime.")
        
        approx = formula.get("approximations", "")
        if approx:
            parts.append(f"Approximations: {approx}.")

        text = " ".join(parts)
        if not text.strip():
            return None

        try:
            embedding = self.model.encode(text, normalize_embeddings=True)
            return np.array(embedding, dtype=np.float32)
        except Exception as e:
            log.warning(f"Semantic embedding failed: {e}")
            return None

    def embed_batch(self, formulas: list[dict]) -> list[Optional[np.ndarray]]:
        """Embed multiple formulas efficiently."""
        if self.model is None:
            return [None] * len(formulas)

        texts = []
        for f in formulas:
            parts = []
            desc = f.get("description", "")
            if desc:
                parts.append(desc)
            qt = f.get("quantity_type", "")
            if qt and qt != "other":
                parts.append(f"Predicts {qt.replace('_', ' ')}.")
            theory = f.get("theory_slug", "")
            if theory:
                parts.append(f"From {theory.replace('_', ' ')}.")
            regime = f.get("regime", "")
            if regime:
                parts.append(f"Regime: {regime}.")
            texts.append(" ".join(parts) if parts else "unknown formula")

        try:
            embeddings = self.model.encode(texts, normalize_embeddings=True, batch_size=32)
            return [np.array(e, dtype=np.float32) for e in embeddings]
        except Exception as e:
            log.warning(f"Batch semantic embedding failed: {e}")
            return [None] * len(formulas)

    def find_similar(
        self, 
        query_formula: dict, 
        corpus_formulas: list[dict],
        top_k: int = 10,
    ) -> list[tuple[dict, float]]:
        """
        Find the most semantically similar formulas to a query formula.
        
        Returns list of (formula, similarity_score) pairs.
        """
        if self.model is None:
            return []

        query_emb = self.embed_formula(query_formula)
        if query_emb is None:
            return []

        corpus_embs = self.embed_batch(corpus_formulas)
        
        results = []
        for formula, emb in zip(corpus_formulas, corpus_embs):
            if emb is not None:
                sim = float(np.dot(query_emb, emb))  # cosine sim (already normalized)
                results.append((formula, sim))
        
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def find_cross_theory_semantic_matches(
        self, formulas: list[dict], threshold: float = 0.7,
    ) -> list[tuple[dict, dict, float]]:
        """
        Find pairs of formulas from different theories that are
        semantically very similar (likely describing the same physics).
        """
        if self.model is None:
            return []

        embeddings = self.embed_batch(formulas)
        
        matches = []
        for i, (fa, ea) in enumerate(zip(formulas, embeddings)):
            if ea is None:
                continue
            for j in range(i + 1, len(formulas)):
                fb, eb = formulas[j], embeddings[j]
                if eb is None:
                    continue
                if fa.get("theory_slug") == fb.get("theory_slug"):
                    continue  # only cross-theory
                
                sim = float(np.dot(ea, eb))
                if sim >= threshold:
                    matches.append((fa, fb, sim))

        matches.sort(key=lambda x: x[2], reverse=True)
        log.info(f"Found {len(matches)} cross-theory semantic matches (threshold={threshold})")
        return matches
