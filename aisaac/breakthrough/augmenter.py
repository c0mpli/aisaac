"""Data augmentation for the small breakthrough-detection dataset.

Because the historical dataset of paradigm shifts is necessarily tiny (~30
records), we synthesise additional training examples via time-slicing,
symptom dropout, and hardcoded negative cases.
"""

from __future__ import annotations

import copy
import random

from .symptoms import (
    PremiseErrorType,
    PremiseShiftRecord,
    Symptom,
    SymptomType,
)


class DataAugmenter:
    """Generate augmented training data from a small set of historical records."""

    # ------------------------------------------------------------------
    # Time slicing
    # ------------------------------------------------------------------

    @staticmethod
    def time_slice(
        record: PremiseShiftRecord,
        n_stages: int = 4,
    ) -> list[PremiseShiftRecord]:
        """Create earlier-in-time snapshots of a record.

        For each of the offsets [-20, -10, -5, -1] years (trimmed to
        *n_stages*), produce a copy with fewer symptoms — the idea being
        that later-discovered symptoms would not yet have been observed.
        """
        offsets = [-20, -10, -5, -1][:n_stages]
        n_symptoms = len(record.symptoms_before)
        if n_symptoms == 0:
            return []

        variants: list[PremiseShiftRecord] = []
        for i, offset in enumerate(offsets):
            r = copy.deepcopy(record)
            r.year = record.year + offset

            # Keep a fraction of symptoms proportional to how close we
            # are to the actual shift year.  Earlier = fewer symptoms.
            fraction = (i + 1) / (len(offsets) + 1)
            keep = max(1, int(n_symptoms * fraction))
            # Deterministic: keep the first *keep* symptoms (ordered by
            # their original listing, which is roughly chronological).
            r.symptoms_before = r.symptoms_before[:keep]

            # Adjust time_stuck_years: how long the field has been stuck
            # at this snapshot.
            r.time_stuck_years = max(1, record.time_stuck_years + offset)

            variants.append(r)

        return variants

    # ------------------------------------------------------------------
    # Symptom dropout
    # ------------------------------------------------------------------

    @staticmethod
    def symptom_dropout(
        record: PremiseShiftRecord,
        n_variants: int = 3,
        seed: int | None = None,
    ) -> list[PremiseShiftRecord]:
        """Create variants with 1-2 random symptoms removed.

        This teaches the matcher to recognise records even when the
        symptom picture is incomplete.
        """
        n_symptoms = len(record.symptoms_before)
        if n_symptoms <= 1:
            # Cannot meaningfully drop symptoms from 0 or 1.
            return []

        rng = random.Random(seed if seed is not None else hash(record.field))
        variants: list[PremiseShiftRecord] = []

        for _ in range(n_variants):
            r = copy.deepcopy(record)
            n_drop = rng.randint(1, min(2, n_symptoms - 1))
            indices = list(range(n_symptoms))
            drop = set(rng.sample(indices, n_drop))
            r.symptoms_before = [
                s for j, s in enumerate(r.symptoms_before) if j not in drop
            ]
            variants.append(r)

        return variants

    # ------------------------------------------------------------------
    # Negative examples
    # ------------------------------------------------------------------

    @staticmethod
    def generate_negatives() -> list[dict]:
        """Hardcoded negative examples — fields with symptoms but no breakthrough.

        Each entry contains realistic symptoms for an *unsolved* problem.
        These can be wrapped into PremiseShiftRecord objects with
        ``succeeded=False`` for training.
        """
        negatives: list[dict] = []

        # 1. Quantum gravity
        negatives.append({
            "field": "Quantum gravity",
            "year": 2025,
            "person": "unknown",
            "old_premise": "Spacetime is a smooth manifold at all scales",
            "new_premise": "unknown",
            "premise_error_type": PremiseErrorType.IMPLICIT_BACKGROUND,
            "symptoms_before": [
                Symptom(
                    symptom_type=SymptomType.FRAMEWORK_MISMATCH,
                    description="GR and QFT contradict at Planck scale",
                    evidence=["non-renormalisability of gravity"],
                    confidence=0.95,
                    affected_quantity="Planck-scale scattering amplitudes",
                    theories_involved=["general relativity", "quantum field theory"],
                ),
                Symptom(
                    symptom_type=SymptomType.PROLIFERATION_WITHOUT_SELECTION,
                    description="String theory landscape has ~10^500 vacua",
                    evidence=["landscape statistics"],
                    confidence=0.85,
                    affected_quantity="vacuum selection",
                    theories_involved=["string theory"],
                ),
                Symptom(
                    symptom_type=SymptomType.UNIVERSAL_QUANTITY,
                    description="Bekenstein-Hawking entropy is universal across approaches",
                    evidence=["black hole thermodynamics"],
                    confidence=0.90,
                    affected_quantity="black hole entropy",
                    theories_involved=["string theory", "loop quantum gravity", "general relativity"],
                ),
                Symptom(
                    symptom_type=SymptomType.UNEXPLAINED_VALUE,
                    description="Cosmological constant 120 orders of magnitude off",
                    evidence=["vacuum energy calculation"],
                    confidence=0.95,
                    affected_quantity="cosmological constant",
                    theories_involved=["quantum field theory", "general relativity"],
                ),
            ],
            "time_stuck_years": 90,
            "time_to_solve_after": 0,
            "key_insight": "unknown",
            "what_made_it_hard": "No experimental access to Planck scale",
            "trigger": "none yet",
            "succeeded": False,
        })

        # 2. Turbulence
        negatives.append({
            "field": "Turbulence",
            "year": 2025,
            "person": "unknown",
            "old_premise": "Navier-Stokes equations fully describe turbulent flow",
            "new_premise": "unknown",
            "premise_error_type": PremiseErrorType.WRONG_LEVEL_OF_DESCRIPTION,
            "symptoms_before": [
                Symptom(
                    symptom_type=SymptomType.UNEXPLAINED_VALUE,
                    description="Kolmogorov scaling exponents deviate from K41 theory",
                    evidence=["intermittency measurements"],
                    confidence=0.80,
                    affected_quantity="scaling exponents",
                    theories_involved=["Kolmogorov theory"],
                ),
                Symptom(
                    symptom_type=SymptomType.EPICYCLE_ACCUMULATION,
                    description="Closure problem requires ever more elaborate models",
                    evidence=["RANS model proliferation"],
                    confidence=0.75,
                    affected_quantity="Reynolds stress tensor",
                    theories_involved=["statistical fluid mechanics"],
                ),
            ],
            "time_stuck_years": 180,
            "time_to_solve_after": 0,
            "key_insight": "unknown",
            "what_made_it_hard": "Extreme nonlinearity, no small parameter",
            "trigger": "none yet",
            "succeeded": False,
        })

        # 3. Consciousness
        negatives.append({
            "field": "Consciousness",
            "year": 2025,
            "person": "unknown",
            "old_premise": "Consciousness arises from neural computation",
            "new_premise": "unknown",
            "premise_error_type": PremiseErrorType.WRONG_LEVEL_OF_DESCRIPTION,
            "symptoms_before": [
                Symptom(
                    symptom_type=SymptomType.FRAMEWORK_MISMATCH,
                    description="No theory bridges subjective experience and neural activity",
                    evidence=["hard problem of consciousness"],
                    confidence=0.85,
                    affected_quantity="qualia",
                    theories_involved=["IIT", "global workspace theory", "neuroscience"],
                ),
                Symptom(
                    symptom_type=SymptomType.PROLIFERATION_WITHOUT_SELECTION,
                    description="Dozens of competing theories with no decisive experiment",
                    evidence=["theory proliferation surveys"],
                    confidence=0.80,
                    affected_quantity="neural correlates of consciousness",
                    theories_involved=["IIT", "global workspace theory", "HOT"],
                ),
            ],
            "time_stuck_years": 400,
            "time_to_solve_after": 0,
            "key_insight": "unknown",
            "what_made_it_hard": "First-person data is not third-person accessible",
            "trigger": "none yet",
            "succeeded": False,
        })

        # 4. Dark matter
        negatives.append({
            "field": "Dark matter",
            "year": 2025,
            "person": "unknown",
            "old_premise": "Missing mass is a new particle",
            "new_premise": "unknown",
            "premise_error_type": PremiseErrorType.UNNECESSARY_ASSUMPTION,
            "symptoms_before": [
                Symptom(
                    symptom_type=SymptomType.NULL_RESULT,
                    description="Direct detection experiments find no WIMP signal",
                    evidence=["XENON1T", "LUX-ZEPLIN", "PandaX"],
                    confidence=0.90,
                    affected_quantity="WIMP cross-section",
                    theories_involved=["WIMP models", "supersymmetry"],
                ),
                Symptom(
                    symptom_type=SymptomType.PROLIFERATION_WITHOUT_SELECTION,
                    description="Hundreds of dark matter candidate particles proposed",
                    evidence=["model surveys"],
                    confidence=0.80,
                    affected_quantity="dark matter particle mass",
                    theories_involved=["BSM physics"],
                ),
            ],
            "time_stuck_years": 90,
            "time_to_solve_after": 0,
            "key_insight": "unknown",
            "what_made_it_hard": "Cannot directly observe; only gravitational evidence",
            "trigger": "none yet",
            "succeeded": False,
        })

        # 5. Dark energy
        negatives.append({
            "field": "Dark energy",
            "year": 2025,
            "person": "unknown",
            "old_premise": "Accelerated expansion is driven by a cosmological constant",
            "new_premise": "unknown",
            "premise_error_type": PremiseErrorType.MISIDENTIFIED_FUNDAMENTAL,
            "symptoms_before": [
                Symptom(
                    symptom_type=SymptomType.UNEXPLAINED_VALUE,
                    description="Dark energy density is unnaturally small compared to QFT prediction",
                    evidence=["cosmological constant problem"],
                    confidence=0.95,
                    affected_quantity="dark energy density",
                    theories_involved=["general relativity", "quantum field theory"],
                ),
                Symptom(
                    symptom_type=SymptomType.FRAMEWORK_MISMATCH,
                    description="QFT vacuum energy and observed expansion rate disagree by ~120 OOM",
                    evidence=["vacuum catastrophe"],
                    confidence=0.90,
                    affected_quantity="vacuum energy",
                    theories_involved=["general relativity", "quantum field theory"],
                ),
            ],
            "time_stuck_years": 27,
            "time_to_solve_after": 0,
            "key_insight": "unknown",
            "what_made_it_hard": "Only one universe to observe; limited cosmological data",
            "trigger": "none yet",
            "succeeded": False,
        })

        return negatives

    @staticmethod
    def _negative_to_record(neg: dict) -> PremiseShiftRecord:
        """Convert a negative-example dict into a PremiseShiftRecord."""
        return PremiseShiftRecord(
            field=neg["field"],
            year=neg["year"],
            person=neg["person"],
            old_premise=neg["old_premise"],
            new_premise=neg["new_premise"],
            premise_error_type=neg["premise_error_type"],
            symptoms_before=neg["symptoms_before"],
            time_stuck_years=neg["time_stuck_years"],
            time_to_solve_after=neg["time_to_solve_after"],
            key_insight=neg["key_insight"],
            what_made_it_hard=neg["what_made_it_hard"],
            trigger=neg["trigger"],
            succeeded=neg["succeeded"],
        )

    # ------------------------------------------------------------------
    # Full augmentation pipeline
    # ------------------------------------------------------------------

    def augment_all(
        self,
        dataset: list[PremiseShiftRecord],
    ) -> list[PremiseShiftRecord]:
        """Augment the dataset to 200-500 examples.

        Combines:
        - Original records
        - Time-sliced variants (4 per record)
        - Symptom-dropout variants (3 per record)
        - Hardcoded negative examples

        Returns the combined augmented dataset.
        """
        augmented: list[PremiseShiftRecord] = list(dataset)

        # Time slicing
        for record in dataset:
            augmented.extend(self.time_slice(record))

        # Symptom dropout
        for record in dataset:
            augmented.extend(self.symptom_dropout(record))

        # Negative examples
        for neg in self.generate_negatives():
            neg_record = self._negative_to_record(neg)
            augmented.append(neg_record)
            # Also augment negatives
            augmented.extend(self.time_slice(neg_record))
            augmented.extend(self.symptom_dropout(neg_record))

        return augmented
