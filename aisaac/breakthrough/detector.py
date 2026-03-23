"""
Breakthrough Symptom Detector.

Detects breakthrough-preceding symptoms in the CURRENT state of quantum
gravity using AIsaac's existing database.  No LLM calls -- pure data
analysis against the knowledge base.

Each detector method queries the SQLite database directly, builds
Symptom objects with real evidence, and sets confidence based on data
quality (more theories agreeing -> higher confidence).
"""
from __future__ import annotations

import json
import logging
from collections import defaultdict

from ..knowledge.base import KnowledgeBase
from .symptoms import Symptom, SymptomType

log = logging.getLogger(__name__)


class SymptomDetector:
    """Detect pre-breakthrough symptoms from the knowledge base."""

    def __init__(self, kb: KnowledgeBase):
        self.kb = kb

    # ── Public API ───────────────────────────────────────────────

    def detect_all(self) -> list[Symptom]:
        """Run every detector and return the combined symptom list."""
        detectors = [
            self.detect_epicycle_accumulation,
            self.detect_unexplained_coincidence,
            self.detect_structured_obstacle,
            self.detect_universal_quantity,
            self.detect_unexplained_value,
            self.detect_framework_mismatch,
            self.detect_proliferation,
            self.detect_dual_description,
            self.detect_null_result,
        ]
        symptoms: list[Symptom] = []
        for detector in detectors:
            try:
                symptoms.extend(detector())
            except Exception as exc:
                log.error("Detector %s failed: %s", detector.__name__, exc)
        log.info("Detected %d total symptoms", len(symptoms))
        return symptoms

    # ── 1. Epicycle Accumulation ─────────────────────────────────

    def detect_epicycle_accumulation(self) -> list[Symptom]:
        """Detect theories that accumulate complexity without structure.

        A theory that generates many formulas but few distinct measurable
        prediction types is adding epicycles -- complexity that doesn't
        resolve into testable claims.
        """
        conn = self.kb.conn
        symptoms: list[Symptom] = []

        # Total formulas per theory
        rows_total = conn.execute(
            "SELECT theory_slug, COUNT(*) AS cnt "
            "FROM formulas GROUP BY theory_slug"
        ).fetchall()
        total_by_theory = {r["theory_slug"]: r["cnt"] for r in rows_total}

        # Distinct non-'other' quantity types with predictions per theory
        rows_pred = conn.execute(
            "SELECT theory_slug, COUNT(DISTINCT quantity_type) AS n_qt "
            "FROM formulas WHERE quantity_type != 'other' "
            "GROUP BY theory_slug"
        ).fetchall()
        pred_types_by_theory = {r["theory_slug"]: r["n_qt"] for r in rows_pred}

        # Count 'other'-classified formulas per theory (complexity w/o structure)
        rows_other = conn.execute(
            "SELECT theory_slug, COUNT(*) AS cnt "
            "FROM formulas WHERE quantity_type = 'other' "
            "GROUP BY theory_slug"
        ).fetchall()
        other_by_theory = {r["theory_slug"]: r["cnt"] for r in rows_other}

        for theory, total in total_by_theory.items():
            n_pred_types = pred_types_by_theory.get(theory, 0)
            n_other = other_by_theory.get(theory, 0)

            # Heuristic: if total formulas outnumber distinct prediction
            # types by a wide margin, the theory is accumulating epicycles.
            if total < 3:
                continue  # too little data to judge

            ratio = total / max(n_pred_types, 1)
            other_fraction = n_other / total if total else 0.0

            if ratio > 5 or (other_fraction > 0.6 and total >= 5):
                confidence = min(0.9, 0.4 + 0.1 * ratio)
                evidence = [
                    f"{theory}: {total} formulas but only "
                    f"{n_pred_types} distinct measurable quantity types",
                ]
                if n_other:
                    evidence.append(
                        f"{n_other}/{total} formulas classified as 'other' "
                        f"(complexity without structure)"
                    )
                symptoms.append(Symptom(
                    symptom_type=SymptomType.EPICYCLE_ACCUMULATION,
                    description=(
                        f"Theory '{theory}' has {total} formulas but only "
                        f"{n_pred_types} distinct prediction types -- "
                        f"growing complexity without proportional predictive power"
                    ),
                    evidence=evidence,
                    confidence=confidence,
                    affected_quantity="multiple",
                    theories_involved=[theory],
                ))

        return symptoms

    # ── 2. Unexplained Coincidence ───────────────────────────────

    def detect_unexplained_coincidence(self) -> list[Symptom]:
        """Detect quantities where 3+ independent theories agree.

        When theories built on different premises converge on the same
        value, that agreement demands an explanation the current
        frameworks cannot supply.
        """
        conn = self.kb.conn
        symptoms: list[Symptom] = []

        # Quantities predicted by 3+ distinct theories
        rows = conn.execute(
            "SELECT quantity_type, COUNT(DISTINCT theory_slug) AS n_theories "
            "FROM formulas "
            "WHERE quantity_type != 'other' "
            "GROUP BY quantity_type "
            "HAVING n_theories >= 3"
        ).fetchall()

        if not rows:
            return symptoms

        # Check whether the assumptions table is populated
        assumption_count = conn.execute(
            "SELECT COUNT(*) FROM assumptions"
        ).fetchone()[0]
        has_assumptions = assumption_count > 0

        for row in rows:
            qt = row["quantity_type"]
            n = row["n_theories"]

            # Gather the specific theories
            theory_rows = conn.execute(
                "SELECT DISTINCT theory_slug FROM formulas "
                "WHERE quantity_type = ?",
                (qt,),
            ).fetchall()
            theories = [r["theory_slug"] for r in theory_rows]

            evidence = [
                f"{n} independent theories predict '{qt}': "
                + ", ".join(theories)
            ]

            # If assumptions are available, check premise overlap
            shared_premises: list[str] = []
            if has_assumptions:
                # Assumptions shared by ALL agreeing theories
                for theory in theories:
                    t_assumptions = conn.execute(
                        "SELECT DISTINCT assumption_text FROM assumptions "
                        "WHERE theory_slug = ?",
                        (theory,),
                    ).fetchall()
                    t_set = {a["assumption_text"] for a in t_assumptions}
                    if not shared_premises:
                        shared_premises = list(t_set)
                    else:
                        shared_premises = [
                            a for a in shared_premises if a in t_set
                        ]
                if shared_premises:
                    evidence.append(
                        f"Shared premises across agreeing theories: "
                        f"{len(shared_premises)}"
                    )
                else:
                    evidence.append(
                        "No shared premises detected -- agreement appears "
                        "genuinely independent"
                    )

            confidence = min(0.95, 0.5 + 0.1 * n)
            symptoms.append(Symptom(
                symptom_type=SymptomType.UNEXPLAINED_COINCIDENCE,
                description=(
                    f"Quantity '{qt}' is predicted by {n} independent "
                    f"theories with no known derivation linking them"
                ),
                evidence=evidence,
                confidence=confidence,
                affected_quantity=qt,
                theories_involved=theories,
            ))

        return symptoms

    # ── 3. Structured Obstacle ───────────────────────────────────

    def detect_structured_obstacle(self) -> list[Symptom]:
        """Detect patterned obstacles from the obstacles table.

        If obstacles cluster neatly into a small number of categories
        (mathematical, conceptual, computational, ...) the difficulty
        is structured -- hinting at a shared root cause.
        """
        conn = self.kb.conn
        symptoms: list[Symptom] = []

        rows = conn.execute(
            "SELECT theory_slug, obstacle_type, COUNT(*) AS cnt "
            "FROM obstacles "
            "GROUP BY theory_slug, obstacle_type "
            "ORDER BY theory_slug, cnt DESC"
        ).fetchall()

        if not rows:
            return symptoms

        # Aggregate: obstacle types per theory, and type distribution
        by_theory: dict[str, dict[str, int]] = defaultdict(dict)
        type_across_theories: dict[str, set[str]] = defaultdict(set)
        for r in rows:
            by_theory[r["theory_slug"]][r["obstacle_type"]] = r["cnt"]
            type_across_theories[r["obstacle_type"]].add(r["theory_slug"])

        # Flag obstacle types that span 3+ theories
        for obs_type, theories in type_across_theories.items():
            if len(theories) >= 3:
                theory_list = sorted(theories)
                evidence = [
                    f"Obstacle type '{obs_type}' appears in {len(theories)} "
                    f"theories: {', '.join(theory_list)}"
                ]
                for t in theory_list:
                    cnt = by_theory[t].get(obs_type, 0)
                    evidence.append(f"  {t}: {cnt} '{obs_type}' obstacles")

                confidence = min(0.9, 0.4 + 0.1 * len(theories))
                symptoms.append(Symptom(
                    symptom_type=SymptomType.STRUCTURED_OBSTACLE,
                    description=(
                        f"Obstacle type '{obs_type}' is systematic across "
                        f"{len(theories)} theories -- the difficulty has "
                        f"structure, suggesting a shared wrong assumption"
                    ),
                    evidence=evidence,
                    confidence=confidence,
                    affected_quantity=obs_type,
                    theories_involved=theory_list,
                ))

        # Also flag individual theories with highly structured obstacles
        for theory, type_counts in by_theory.items():
            total = sum(type_counts.values())
            n_types = len(type_counts)
            if total >= 3 and n_types <= 3:
                evidence = [
                    f"{theory}: {total} obstacles fall into only "
                    f"{n_types} categories: "
                    + ", ".join(
                        f"{t} ({c})" for t, c in sorted(
                            type_counts.items(), key=lambda x: -x[1]
                        )
                    )
                ]
                symptoms.append(Symptom(
                    symptom_type=SymptomType.STRUCTURED_OBSTACLE,
                    description=(
                        f"Theory '{theory}' has {total} obstacles in only "
                        f"{n_types} categories -- highly structured difficulty"
                    ),
                    evidence=evidence,
                    confidence=0.6,
                    affected_quantity="multiple",
                    theories_involved=[theory],
                ))

        return symptoms

    # ── 4. Universal Quantity ────────────────────────────────────

    def detect_universal_quantity(self) -> list[Symptom]:
        """Detect quantities predicted by 4+ theories.

        A quantity that appears across nearly all approaches is
        quasi-universal and likely reflects deep physics, not the
        assumptions of any single framework.
        """
        conn = self.kb.conn
        symptoms: list[Symptom] = []

        rows = conn.execute(
            "SELECT quantity_type, COUNT(DISTINCT theory_slug) AS n "
            "FROM formulas "
            "WHERE quantity_type != 'other' "
            "GROUP BY quantity_type "
            "HAVING n >= 3"
        ).fetchall()

        for row in rows:
            qt = row["quantity_type"]
            n = row["n"]

            theory_rows = conn.execute(
                "SELECT DISTINCT theory_slug FROM formulas "
                "WHERE quantity_type = ?",
                (qt,),
            ).fetchall()
            theories = [r["theory_slug"] for r in theory_rows]

            # Only flag as "universal" if 4+ theories, otherwise moderate
            if n >= 4:
                label = "universal"
                confidence = min(0.95, 0.5 + 0.1 * n)
            else:
                label = "widely predicted"
                confidence = min(0.8, 0.4 + 0.1 * n)

            evidence = [
                f"'{qt}' predicted by {n} theories: {', '.join(theories)}"
            ]

            # Count total formulas for this quantity
            total_row = conn.execute(
                "SELECT COUNT(*) AS cnt FROM formulas "
                "WHERE quantity_type = ?",
                (qt,),
            ).fetchone()
            evidence.append(
                f"Total of {total_row['cnt']} formulas for this quantity"
            )

            symptoms.append(Symptom(
                symptom_type=SymptomType.UNIVERSAL_QUANTITY,
                description=(
                    f"Quantity '{qt}' is {label} -- predicted by {n} "
                    f"independent theories"
                ),
                evidence=evidence,
                confidence=confidence,
                affected_quantity=qt,
                theories_involved=theories,
            ))

        return symptoms

    # ── 5. Unexplained Value ────────────────────────────────────

    def detect_unexplained_value(self) -> list[Symptom]:
        """Detect recurring numerical values that are computed but not explained.

        Specific numbers (d_s=2, log coefficient -3/2, BH entropy = A/4G)
        that appear across theories demand explanation at a deeper level.
        """
        conn = self.kb.conn
        symptoms: list[Symptom] = []

        # Known unexplained values in quantum gravity
        WATCHED_VALUES = [
            {
                "label": "spectral dimension -> 2",
                "quantity_types": ["spectral_dimension"],
                "description_pattern": "%2%",
                "explanation": (
                    "The spectral dimension flows to 2 in the UV across "
                    "CDT, Asymptotic Safety, Horava-Lifshitz, LQG, and "
                    "Causal Sets -- the value 2 is computed but never "
                    "derived from a unifying principle"
                ),
            },
            {
                "label": "BH entropy log correction -3/2",
                "quantity_types": [
                    "bh_entropy_log_correction",
                    "black_hole_entropy",
                ],
                "description_pattern": "%-3/2%",
                "explanation": (
                    "The logarithmic correction to black hole entropy has "
                    "coefficient -3/2 in multiple independent calculations"
                ),
            },
            {
                "label": "BH entropy = A/4G",
                "quantity_types": ["black_hole_entropy"],
                "description_pattern": "%A/4%",
                "explanation": (
                    "The Bekenstein-Hawking area law S = A/4G is reproduced "
                    "by string theory, LQG, and induced gravity approaches "
                    "but the factor 1/4 has no universal derivation"
                ),
            },
        ]

        for val in WATCHED_VALUES:
            theories_found: set[str] = set()
            evidence: list[str] = []

            for qt in val["quantity_types"]:
                # Search formulas matching this quantity type
                rows = conn.execute(
                    "SELECT DISTINCT theory_slug, description, latex "
                    "FROM formulas WHERE quantity_type = ?",
                    (qt,),
                ).fetchall()
                for r in rows:
                    theories_found.add(r["theory_slug"])

                # Also search descriptions for the value pattern
                pattern_rows = conn.execute(
                    "SELECT DISTINCT theory_slug, description "
                    "FROM formulas "
                    "WHERE description LIKE ? "
                    "AND quantity_type != 'other'",
                    (val["description_pattern"],),
                ).fetchall()
                for r in pattern_rows:
                    theories_found.add(r["theory_slug"])

            if not theories_found:
                continue

            theories = sorted(theories_found)
            evidence.append(val["explanation"])
            evidence.append(f"Found in theories: {', '.join(theories)}")

            confidence = min(0.9, 0.4 + 0.15 * len(theories))
            symptoms.append(Symptom(
                symptom_type=SymptomType.UNEXPLAINED_VALUE,
                description=(
                    f"Value '{val['label']}' is computed by "
                    f"{len(theories)} theories but has no unifying "
                    f"derivation"
                ),
                evidence=evidence,
                confidence=confidence,
                affected_quantity=val["quantity_types"][0],
                theories_involved=theories,
            ))

        return symptoms

    # ── 6. Framework Mismatch ────────────────────────────────────

    def detect_framework_mismatch(self) -> list[Symptom]:
        """Detect fundamental contradictions between successful frameworks.

        The GR vs QFT mismatch is the defining symptom of quantum gravity
        and is always present.  Additional contradictions are pulled from
        the contradictions table.
        """
        conn = self.kb.conn
        symptoms: list[Symptom] = []

        # The GR / QFT mismatch is always present -- it IS quantum gravity
        symptoms.append(Symptom(
            symptom_type=SymptomType.FRAMEWORK_MISMATCH,
            description=(
                "General Relativity and Quantum Field Theory give "
                "contradictory answers in the Planck regime -- the "
                "defining framework mismatch of quantum gravity"
            ),
            evidence=[
                "GR: spacetime is a smooth dynamical manifold",
                "QFT: fields propagate on a fixed background spacetime",
                "Both are spectacularly confirmed in their regimes",
                "Non-renormalizability of perturbative quantum gravity",
            ],
            confidence=1.0,
            affected_quantity="spacetime_structure",
            theories_involved=["GR", "QFT"],
        ))

        # Pull contradictions from DB — ONE symptom per theory pair (not per contradiction)
        rows = conn.execute("SELECT * FROM contradictions").fetchall()

        pair_contradictions = defaultdict(list)
        for r in rows:
            pair = tuple(sorted([r["theory_a"], r["theory_b"]]))
            pair_contradictions[pair].append(r)

        for (ta, tb), contras in pair_contradictions.items():
            # Pick the most severe contradiction as the description
            severities = [c["severity"] for c in contras]
            max_severity = "fundamental" if "fundamental" in severities else \
                           "major" if "major" in severities else "moderate"
            best = next((c for c in contras if c["severity"] == max_severity), contras[0])

            evidence = [f"{len(contras)} contradictions found between {ta} and {tb}"]
            evidence.append(best["description"][:150])

            confidence = 0.9 if max_severity == "fundamental" else 0.7 if max_severity == "major" else 0.5

            symptoms.append(Symptom(
                symptom_type=SymptomType.FRAMEWORK_MISMATCH,
                description=f"{ta} vs {tb}: {len(contras)} contradictions ({max_severity})",
                evidence=evidence,
                confidence=confidence,
                affected_quantity="framework_consistency",
                theories_involved=[ta, tb],
            ))

        log.info("Found %d theory-pair contradictions from %d individual entries",
                 len(pair_contradictions), len(rows))

        return symptoms

    # ── 7. Proliferation Without Selection ───────────────────────

    def detect_proliferation(self) -> list[Symptom]:
        """Detect proliferation of theories with no distinguishing experiments.

        When the number of competing theories far exceeds the number of
        experiments that can discriminate between them, something is
        wrong with the question being asked.
        """
        conn = self.kb.conn
        symptoms: list[Symptom] = []

        # Count distinct theories in the database
        rows = conn.execute(
            "SELECT DISTINCT theory_slug FROM formulas"
        ).fetchall()
        theories = [r["theory_slug"] for r in rows]
        n_theories = len(theories)

        if n_theories < 2:
            return symptoms

        # Distinguishing experiments: in quantum gravity, effectively 0
        # at accessible energies.  This is a hard fact about the field.
        n_distinguishing_experiments = 0

        ratio = n_theories / max(n_distinguishing_experiments, 0.1)

        evidence = [
            f"{n_theories} distinct theories in the database: "
            + ", ".join(theories),
            f"Distinguishing experiments at accessible energies: "
            f"{n_distinguishing_experiments}",
            f"Theory/experiment ratio: {ratio:.0f}",
            "No current or planned experiment can discriminate between "
            "the major quantum gravity approaches",
        ]

        confidence = min(0.95, 0.5 + 0.05 * n_theories)
        symptoms.append(Symptom(
            symptom_type=SymptomType.PROLIFERATION_WITHOUT_SELECTION,
            description=(
                f"{n_theories} quantum gravity theories compete with "
                f"essentially zero distinguishing experiments -- "
                f"proliferation without empirical selection"
            ),
            evidence=evidence,
            confidence=confidence,
            affected_quantity="theory_count",
            theories_involved=theories,
        ))

        return symptoms

    # ── 8. Dual Description ──────────────────────────────────────

    def detect_dual_description(self) -> list[Symptom]:
        """Detect high-scoring cross-theory formula matches.

        When two theories with completely different formalisms produce
        the same formula for the same quantity, this duality signals
        that neither formalism is fundamental.
        """
        conn = self.kb.conn
        symptoms: list[Symptom] = []

        # Look for claimed connections of type 'agrees' or 'maps_to'
        conn_rows = conn.execute(
            "SELECT * FROM claimed_connections "
            "WHERE connection_type IN ('agrees', 'maps_to')"
        ).fetchall()

        for _cr in conn_rows:
            cr = dict(_cr)
            evidence = [cr["description"]] if cr["description"] else []
            evidence.append(
                f"Connection type: {cr['connection_type']} "
                f"between {cr['theory_a']} and {cr['theory_b']}"
            )

            # If formula IDs are available, pull their details
            for fid_key in ("formula_a_id", "formula_b_id"):
                try:
                    fid = cr[fid_key]
                except (IndexError, KeyError):
                    fid = None
                if fid:
                    f_row = conn.execute(
                        "SELECT theory_slug, quantity_type, description "
                        "FROM formulas WHERE id = ?",
                        (fid,),
                    ).fetchone()
                    if f_row:
                        evidence.append(
                            f"  {f_row['theory_slug']} "
                            f"({f_row['quantity_type']}): "
                            f"{f_row['description'][:80]}"
                        )

            symptoms.append(Symptom(
                symptom_type=SymptomType.DUAL_DESCRIPTION,
                description=(
                    f"Dual description: {cr['theory_a']} and "
                    f"{cr['theory_b']} produce equivalent results "
                    f"from different formalisms"
                ),
                evidence=evidence,
                confidence=0.75,
                affected_quantity=cr["connection_type"] if "connection_type" in cr.keys() else "mapping",
                theories_involved=[cr["theory_a"], cr["theory_b"]],
            ))

        # Also check conjectures that link theories
        conj_rows = conn.execute(
            "SELECT * FROM conjectures "
            "WHERE conjecture_type IN ('duality', 'equivalence', 'mapping') "
            "AND status != 'disproved'"
        ).fetchall()

        for _cj in conj_rows:
            cj = dict(_cj)
            theories_raw = cj.get("theories_involved", "[]")
            try:
                theories = json.loads(theories_raw) if isinstance(theories_raw, str) else theories_raw
            except (json.JSONDecodeError, TypeError):
                theories = []

            if len(theories) < 2:
                continue

            evidence = [cj.get("statement_natural", "")]
            if cj.get("algebraic_verified"):
                evidence.append("Algebraically verified")
            if cj.get("numerical_verified"):
                evidence.append("Numerically verified")

            confidence = min(
                0.95,
                0.5 + 0.15 * (
                    int(bool(cj.get("algebraic_verified")))
                    + int(bool(cj.get("numerical_verified")))
                    + int(bool(cj.get("dimensional_verified")))
                ),
            )

            symptoms.append(Symptom(
                symptom_type=SymptomType.DUAL_DESCRIPTION,
                description=(
                    f"Conjecture '{cj.get('title', '?')}': possible duality "
                    f"between {', '.join(theories)}"
                ),
                evidence=evidence,
                confidence=confidence,
                affected_quantity=cj.get("conjecture_type", "duality"),
                theories_involved=theories,
            ))

        return symptoms

    # ── 9. Null Result ───────────────────────────────────────────

    def detect_null_result(self) -> list[Symptom]:
        """Report known null results constraining quantum gravity.

        These are experimental results where a predicted or expected
        signal was NOT found.  Each null result eliminates parts of the
        QG parameter space and collectively they tighten the constraint
        on viable theories.
        """
        # These are established experimental facts, not database-derived.
        # We hard-code them because they are foundational context for any
        # QG symptom analysis.
        NULL_RESULTS = [
            {
                "description": (
                    "No proton decay detected (Super-Kamiokande): "
                    "constrains GUT-scale physics adjacent to several "
                    "QG approaches"
                ),
                "affected_quantity": "proton_lifetime",
                "theories": ["string_theory", "loop_quantum_gravity"],
                "confidence": 0.95,
            },
            {
                "description": (
                    "No Lorentz invariance violation detected "
                    "(Fermi GBM/LAT): photons of vastly different "
                    "energies arrive simultaneously from gamma-ray bursts, "
                    "constraining LQG and NCG dispersion modifications"
                ),
                "affected_quantity": "lorentz_violation",
                "theories": ["loop_quantum_gravity", "noncommutative_geometry"],
                "confidence": 0.95,
            },
            {
                "description": (
                    "No large extra dimensions detected (LHC): "
                    "rules out TeV-scale extra dimensions predicted "
                    "by some string phenomenology models"
                ),
                "affected_quantity": "extra_dimensions",
                "theories": ["string_theory"],
                "confidence": 0.90,
            },
            {
                "description": (
                    "No supersymmetric partners detected (LHC at 13 TeV): "
                    "minimal SUSY scenarios increasingly constrained, "
                    "challenging a foundational ingredient of string theory"
                ),
                "affected_quantity": "supersymmetry",
                "theories": ["string_theory"],
                "confidence": 0.90,
            },
        ]

        symptoms: list[Symptom] = []
        for nr in NULL_RESULTS:
            symptoms.append(Symptom(
                symptom_type=SymptomType.NULL_RESULT,
                description=nr["description"],
                evidence=[
                    nr["description"],
                    "Null result: the expected effect was not observed",
                ],
                confidence=nr["confidence"],
                affected_quantity=nr["affected_quantity"],
                theories_involved=nr["theories"],
            ))

        return symptoms
