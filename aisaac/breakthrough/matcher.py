"""Pattern matching engine for breakthrough detection.

Given current symptoms observed in a scientific field, finds the closest
historical analog where a wrong premise was eventually identified and
corrected. Uses simple sklearn classifiers suitable for small datasets.
"""

from __future__ import annotations

import copy
import warnings

import numpy as np
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.model_selection import LeaveOneOut, cross_val_predict

from .symptoms import PremiseErrorType, PremiseShiftRecord, Symptom, SymptomType

try:
    from .dataset import build_dataset
except ImportError:
    build_dataset = None  # dataset module not yet available


# Ordered lists for deterministic feature indexing.
_SYMPTOM_TYPES = list(SymptomType)
_PREMISE_ERROR_TYPES = list(PremiseErrorType)
_NUM_SYMPTOM_TYPES = len(_SYMPTOM_TYPES)


class BreakthroughMatcher:
    """Matches current symptoms against historical paradigm-shift records."""

    def __init__(self, dataset: list[PremiseShiftRecord] | None = None):
        if dataset is not None:
            self.dataset = dataset
        elif build_dataset is not None:
            self.dataset = build_dataset()
        else:
            self.dataset = []

        self.X: np.ndarray | None = None
        self.y: np.ndarray | None = None
        self.clf: RandomForestClassifier | None = None
        self.cross_val_accuracy: float = 0.0
        self.pairwise_distances: np.ndarray | None = None

        if self.dataset:
            self._train()

    # ------------------------------------------------------------------
    # Feature engineering
    # ------------------------------------------------------------------

    @staticmethod
    def _build_feature_vector(symptoms: list[Symptom]) -> np.ndarray:
        """Convert a list of symptoms into a fixed-length feature vector.

        Layout (31 features total):
            [0:9]   binary — which SymptomType is present
            [9:18]  counts — how many of each SymptomType
            [18:27] floats — max confidence per SymptomType
            [27]    total unique theories involved
            [28]    total unique affected quantities
            [29]    total symptom count
            [30]    average confidence
        """
        binary = np.zeros(_NUM_SYMPTOM_TYPES, dtype=np.float64)
        counts = np.zeros(_NUM_SYMPTOM_TYPES, dtype=np.float64)
        max_conf = np.zeros(_NUM_SYMPTOM_TYPES, dtype=np.float64)

        theories: set[str] = set()
        quantities: set[str] = set()
        total_conf = 0.0

        for s in symptoms:
            idx = _SYMPTOM_TYPES.index(s.symptom_type)
            binary[idx] = 1.0
            counts[idx] += 1.0
            max_conf[idx] = max(max_conf[idx], s.confidence)
            theories.update(s.theories_involved)
            if s.affected_quantity:
                quantities.add(s.affected_quantity)
            total_conf += s.confidence

        n = len(symptoms)
        avg_conf = total_conf / n if n > 0 else 0.0

        return np.concatenate([
            binary,
            counts,
            max_conf,
            np.array([
                float(len(theories)),
                float(len(quantities)),
                float(n),
                avg_conf,
            ]),
        ])

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def _train(self) -> None:
        """Build feature matrix, train classifier, compute distances."""
        records = [r for r in self.dataset if r.symptoms_before]
        if not records:
            return

        self.X = np.array([
            self._build_feature_vector(r.symptoms_before) for r in records
        ])
        self.y = np.array([
            _PREMISE_ERROR_TYPES.index(r.premise_error_type) for r in records
        ])

        # Keep only the records that made it into X (those with symptoms).
        self._indexed_records = records

        n_classes = len(set(self.y))
        n_samples = len(self.y)

        # Train primary classifier.
        self.clf = RandomForestClassifier(
            n_estimators=200,
            max_depth=None,
            min_samples_leaf=1,
            random_state=42,
            class_weight="balanced",
        )
        self.clf.fit(self.X, self.y)

        # Leave-one-out cross-validation (honest accuracy on tiny dataset).
        if n_samples >= 2 and n_classes >= 2:
            loo = LeaveOneOut()
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                preds = cross_val_predict(
                    RandomForestClassifier(
                        n_estimators=200,
                        max_depth=None,
                        min_samples_leaf=1,
                        random_state=42,
                        class_weight="balanced",
                    ),
                    self.X,
                    self.y,
                    cv=loo,
                )
            self.cross_val_accuracy = float(np.mean(preds == self.y))
        else:
            self.cross_val_accuracy = 0.0

        # Pairwise cosine distances for nearest-neighbour lookup.
        if n_samples >= 2:
            sim = cosine_similarity(self.X)
            self.pairwise_distances = 1.0 - sim
        else:
            self.pairwise_distances = np.zeros((n_samples, n_samples))

    # ------------------------------------------------------------------
    # Matching
    # ------------------------------------------------------------------

    def find_closest_historical(
        self,
        current_symptoms: list[Symptom],
        top_k: int = 3,
    ) -> list[tuple[PremiseShiftRecord, float, dict]]:
        """Return the *top_k* most similar historical records.

        Returns
        -------
        list of (record, similarity_score, overlap_details)
            overlap_details has keys:
                matching_types   — SymptomType names present in both
                only_in_current  — SymptomType names only in the query
                only_in_history  — SymptomType names only in the record
        """
        if not current_symptoms or self.X is None or len(self.X) == 0:
            return []

        vec = self._build_feature_vector(current_symptoms).reshape(1, -1)
        sims = cosine_similarity(vec, self.X)[0]

        current_types = {s.symptom_type.name for s in current_symptoms}

        ranked = np.argsort(-sims)
        results: list[tuple[PremiseShiftRecord, float, dict]] = []
        for idx in ranked[:top_k]:
            rec = self._indexed_records[idx]
            hist_types = {s.symptom_type.name for s in rec.symptoms_before}
            overlap = {
                "matching_types": sorted(current_types & hist_types),
                "only_in_current": sorted(current_types - hist_types),
                "only_in_history": sorted(hist_types - current_types),
            }
            results.append((rec, float(sims[idx]), overlap))

        return results

    # ------------------------------------------------------------------
    # Prediction
    # ------------------------------------------------------------------

    def predict_premise_error(self, current_symptoms: list[Symptom]) -> dict:
        """Classify the most likely premise error type.

        Returns a dict with predicted_type, probability, all_probabilities,
        cross_val_accuracy, and a short reasoning string.
        """
        empty_result = {
            "predicted_type": None,
            "probability": 0.0,
            "all_probabilities": {},
            "cross_val_accuracy": self.cross_val_accuracy,
            "reasoning": "Insufficient data for prediction.",
        }

        if not current_symptoms or self.clf is None:
            return empty_result

        vec = self._build_feature_vector(current_symptoms).reshape(1, -1)
        proba = self.clf.predict_proba(vec)[0]
        classes = self.clf.classes_

        all_probs = {
            _PREMISE_ERROR_TYPES[c].name: float(p)
            for c, p in zip(classes, proba)
        }

        best_idx = int(np.argmax(proba))
        best_class = classes[best_idx]
        best_type = _PREMISE_ERROR_TYPES[best_class]
        best_prob = float(proba[best_idx])

        present = sorted({s.symptom_type.name for s in current_symptoms})
        reasoning = (
            f"Based on symptoms [{', '.join(present)}], the pattern most "
            f"closely resembles historical cases of {best_type.name} "
            f"(probability {best_prob:.2f}). "
            f"LOO cross-val accuracy on training set: "
            f"{self.cross_val_accuracy:.2f}."
        )

        return {
            "predicted_type": best_type,
            "probability": best_prob,
            "all_probabilities": all_probs,
            "cross_val_accuracy": self.cross_val_accuracy,
            "reasoning": reasoning,
        }

    # ------------------------------------------------------------------
    # Suggestion generation (template-based, no LLM)
    # ------------------------------------------------------------------

    _TEMPLATES: dict[str, str] = {
        "UNNECESSARY_ASSUMPTION": (
            "Historical fix removed an assumed entity ({old}). "
            "Consider whether a similar unnecessary assumption exists "
            "in the current framework."
        ),
        "MISIDENTIFIED_FUNDAMENTAL": (
            "Historical fix showed that {old} was actually derived. "
            "Consider which quantities currently treated as fundamental "
            "might be emergent."
        ),
        "FALSE_DICHOTOMY": (
            "Historical fix unified two concepts ({old} -> {new}). "
            "Look for an underlying unity behind the current apparent "
            "dichotomy."
        ),
        "WRONG_LEVEL_OF_DESCRIPTION": (
            "Historical fix moved to a different level of description "
            "({old} -> {new}). The current symptoms may require a "
            "similar shift in abstraction level."
        ),
        "INVERTED_CAUSATION": (
            "Historical fix inverted the causal direction ({old} -> "
            "{new}). Check whether cause and effect are swapped in "
            "the current problem."
        ),
        "IMPLICIT_BACKGROUND": (
            "Historical fix made a fixed background dynamical "
            "({old} -> {new}). Look for structures currently treated "
            "as fixed that should be dynamical."
        ),
        "CONTINUITY_ASSUMPTION": (
            "Historical fix changed a continuity assumption "
            "({old} -> {new}). Consider whether a quantity assumed "
            "continuous might be discrete, or vice versa."
        ),
    }

    def suggest_shifts(self, current_symptoms: list[Symptom]) -> list[dict]:
        """Suggest premise shifts based on historical analogs.

        Returns a list of dicts, each with:
            historical_analog, historical_fix, translated_suggestion, confidence
        """
        matches = self.find_closest_historical(current_symptoms, top_k=3)
        if not matches:
            return []

        suggestions: list[dict] = []
        for record, sim, _overlap in matches:
            template = self._TEMPLATES.get(
                record.premise_error_type.name,
                "Historical fix: {old} -> {new}. Consider whether a "
                "similar shift applies to the current problem.",
            )
            translated = template.format(
                old=record.old_premise,
                new=record.new_premise,
            )
            suggestions.append({
                "historical_analog": (
                    f"{record.field} ({record.year}, {record.person})"
                ),
                "historical_fix": (
                    f"{record.old_premise} -> {record.new_premise}"
                ),
                "translated_suggestion": translated,
                "confidence": round(sim, 4),
            })

        return suggestions
