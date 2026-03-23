"""Generates the final breakthrough analysis report.

Combines symptom detection, historical pattern matching, and ML-based
premise error prediction into a structured report that identifies which
assumptions in quantum gravity are most likely wrong and what to try instead.
"""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .symptoms import Symptom, SymptomType, PremiseErrorType
from .detector import SymptomDetector
from .matcher import BreakthroughMatcher
from .dataset import build_dataset
from ..knowledge.base import KnowledgeBase
from ..pipeline.config import DATA_DIR

log = logging.getLogger(__name__)
console = Console()


class BreakthroughReport:
    """Full breakthrough analysis report combining all detection modules."""

    def __init__(self, kb: KnowledgeBase):
        self.kb = kb
        self.detector = SymptomDetector(kb)
        self.matcher = BreakthroughMatcher()
        self._report: dict | None = None

    def generate(self) -> dict:
        """Detect symptoms, match against history, build structured report."""
        # 1. Detect symptoms in the current field
        symptoms = self.detector.detect_all()

        # 2. Match against historical breakthroughs
        matches = self.matcher.find_closest_historical(symptoms, top_k=5)
        prediction = self.matcher.predict_premise_error(symptoms)
        cv_accuracy = getattr(self.matcher, 'cv_accuracy_', 0.0)

        # 3. Get convergence constraints (what any premise shift must reproduce)
        try:
            from ..premise.convergence_analyzer import ConvergenceAnalyzer
            ca = ConvergenceAnalyzer(self.kb)
            convergences = ca.analyze_all()
            constraints = [c for c in convergences if c.is_premise_independent]
        except Exception:
            constraints = []

        # 4. Get premise engine results if available
        try:
            premise_shifts = self.kb.get_premise_shifts(min_score=0.0)
            premise_shifts.sort(key=lambda s: s.get("score", 0), reverse=True)
        except Exception:
            premise_shifts = []

        # Convert match tuples to dicts for consistent access downstream
        match_dicts = []
        for item in matches[:5]:
            if isinstance(item, tuple) and len(item) == 3:
                record, sim, details = item
                match_dicts.append({
                    "field": record.field,
                    "year": record.year,
                    "person": record.person,
                    "old_premise": record.old_premise,
                    "new_premise": record.new_premise,
                    "key_insight": record.key_insight,
                    "what_made_it_hard": record.what_made_it_hard,
                    "trigger": record.trigger,
                    "premise_error_type": record.premise_error_type.value if hasattr(record.premise_error_type, 'value') else str(record.premise_error_type),
                    "symptoms_before": record.symptoms_before,
                    "similarity": sim,
                    "details": details,
                    "matching_symptoms": details.get("matching_symptoms", []) if isinstance(details, dict) else [],
                    "missing_symptoms": details.get("missing_symptoms", []) if isinstance(details, dict) else [],
                })
            elif isinstance(item, dict):
                match_dicts.append(item)

        self._report = {
            "generated": datetime.now().isoformat(),
            "symptoms": symptoms,
            "historical_matches": match_dicts,
            "prediction": prediction,
            "cv_accuracy": cv_accuracy,
            "constraints": constraints,
            "premise_shifts": premise_shifts,
            "dataset_size": len(self.matcher.dataset),
        }
        return self._report

    def print_report(self):
        """Print full report to console using rich formatting."""
        if self._report is None:
            self.generate()
        report = self._report

        console.print(Panel.fit(
            "[bold cyan]BREAKTHROUGH PATTERN ANALYSIS[/bold cyan]\n"
            f"Generated: {report['generated']}\n"
            f"Historical dataset: {report['dataset_size']} paradigm shifts",
            border_style="cyan",
        ))

        # ── Section 1: DETECTED SYMPTOMS ─────────────────────────
        console.print("\n[bold]1. DETECTED SYMPTOMS[/bold]")
        symptoms: list[Symptom] = report["symptoms"]
        if symptoms:
            # Group by type, show top 2 per type (most confident)
            from collections import defaultdict
            by_type = defaultdict(list)
            for s in symptoms:
                by_type[s.symptom_type].append(s)

            table = Table(title=f"Symptoms Detected in Quantum Gravity ({len(symptoms)} total, showing top per type)")
            table.add_column("Type", width=28)
            table.add_column("Conf", justify="right", width=5)
            table.add_column("Count", justify="right", width=5)
            table.add_column("Description", width=50)
            table.add_column("Theories", width=25)

            for st in sorted(by_type.keys(), key=lambda x: max(s.confidence for s in by_type[x]), reverse=True):
                group = sorted(by_type[st], key=lambda s: s.confidence, reverse=True)
                for s in group[:2]:  # top 2 per type
                    conf_color = "green" if s.confidence > 0.7 else "yellow" if s.confidence > 0.4 else "dim"
                    count_str = str(len(group)) if s == group[0] else ""
                    table.add_row(
                        s.symptom_type.name if s == group[0] else "",
                        f"[{conf_color}]{s.confidence:.2f}[/{conf_color}]",
                        count_str,
                        s.description[:50],
                        ", ".join(s.theories_involved[:3]),
                    )
            console.print(table)
        else:
            console.print("  [dim]No symptoms detected.[/dim]")

        # ── Section 2: SYMPTOM PROFILE COMPARISON ────────────────
        console.print("\n[bold]2. SYMPTOM PROFILE COMPARISON[/bold]")
        matches = report["historical_matches"]
        # matches are now dicts with 'field', 'year', 'symptoms_before', etc.
        if symptoms and matches:
            current_types = {s.symptom_type for s in symptoms}

            table = Table(title="Current Field vs Historical Matches")
            table.add_column("Symptom", width=30)
            table.add_column("Current QG", justify="center", width=12)
            for m in matches[:3]:
                label = f"{m.get('field', '?')[:12]} ({m.get('year', '?')})"
                table.add_column(label, justify="center", width=15)

            # Collect all symptom types
            all_types = set(current_types)
            for m in matches[:3]:
                for ms in m.get("symptoms_before", []):
                    if isinstance(ms, Symptom):
                        all_types.add(ms.symptom_type)

            for st in sorted(all_types, key=lambda x: x.name):
                row = [st.name]
                if st in current_types:
                    row.append("[green]YES[/green]")
                else:
                    row.append("[red]---[/red]")
                for m in matches[:3]:
                    match_types = set()
                    for ms in m.get("symptoms_before", []):
                        if isinstance(ms, Symptom):
                            match_types.add(ms.symptom_type)
                    if st in match_types:
                        row.append("[green]YES[/green]")
                    else:
                        row.append("[red]---[/red]")
                table.add_row(*row)
            console.print(table)
        else:
            console.print("  [dim]Insufficient data for comparison.[/dim]")

        # ── Section 3: PREDICTED PREMISE ERROR TYPE ──────────────
        console.print("\n[bold]3. PREDICTED PREMISE ERROR TYPE[/bold]")
        prediction = report["prediction"]
        cv_accuracy = report["cv_accuracy"]
        if prediction:
            top_predictions = prediction.get("top_predictions", [])
            best = top_predictions[0] if top_predictions else None

            if best:
                console.print(Panel(
                    f"[bold]Primary prediction: {best['error_type']}[/bold]\n"
                    f"Probability: {best['probability']:.1%}\n\n"
                    f"Cross-validation accuracy: {cv_accuracy:.1%} "
                    f"({'reliable' if cv_accuracy > 0.6 else 'use with caution'})\n\n"
                    f"[bold]Top 3 most likely error types:[/bold]",
                    border_style="yellow",
                ))

                table = Table()
                table.add_column("Rank", width=6)
                table.add_column("Premise Error Type", width=35)
                table.add_column("Probability", justify="right", width=12)

                for i, pred in enumerate(top_predictions[:3], 1):
                    table.add_row(
                        str(i),
                        pred["error_type"],
                        f"{pred['probability']:.1%}",
                    )
                console.print(table)
        else:
            console.print("  [dim]No prediction available.[/dim]")

        # ── Section 4: HISTORICAL ANALOGS ────────────────────────
        console.print("\n[bold]4. HISTORICAL ANALOGS[/bold]")
        for i, m in enumerate(matches[:3], 1):
            console.print(Panel(
                f"[bold]{m.get('field', '?')} ({m.get('year', '?')}) — {m.get('person', '?')}[/bold]\n\n"
                f"[red]Wrong premise:[/red] {m.get('old_premise', '?')}\n"
                f"[green]The fix:[/green] {m.get('new_premise', '?')}\n\n"
                f"Key insight: {m.get('key_insight', '?')}\n\n"
                f"Similarity score: {m.get('similarity', 0):.2f}\n"
                f"Matching symptoms: {', '.join(m.get('matching_symptoms', []))}\n"
                f"Missing symptoms: {', '.join(m.get('missing_symptoms', []))}",
                title=f"Analog #{i}",
                border_style="blue",
            ))

        # ── Section 5: CONSTRAINTS ───────────────────────────────
        console.print("\n[bold]5. CONSTRAINTS (any premise shift MUST reproduce)[/bold]")
        constraints = report["constraints"]
        if constraints:
            table = Table(title="Premise-Independent Results")
            table.add_column("Quantity", width=25)
            table.add_column("Theories Agree", width=35)
            table.add_column("Strength", width=10)

            for c in constraints:
                strength_color = {"strong": "green", "moderate": "yellow", "weak": "dim"}.get(c.strength, "")
                table.add_row(
                    c.quantity_type,
                    ", ".join(c.theories_agree),
                    f"[{strength_color}]{c.strength}[/{strength_color}]",
                )
            console.print(table)
        else:
            console.print("  [dim]No convergence constraints found. Run: aisaac --premises[/dim]")

        # ── Section 6: CANDIDATE PREMISES TO QUESTION ────────────
        console.print("\n[bold]6. CANDIDATE PREMISES TO QUESTION[/bold]")
        candidates = self._build_candidate_premises(report)
        if candidates:
            for i, c in enumerate(candidates[:10], 1):
                source_color = {
                    "ml_prediction": "yellow",
                    "historical_analog": "blue",
                    "premise_engine": "green",
                }.get(c["source"], "dim")

                console.print(Panel(
                    f"[bold]{c['premise_to_drop']}[/bold]\n\n"
                    f"How to test: {c['how_to_test']}\n"
                    f"Resembles: {c['historical_resemblance']}\n"
                    f"Source: [{source_color}]{c['source']}[/{source_color}]",
                    title=f"Candidate #{i}",
                    border_style=source_color,
                ))
        else:
            console.print("  [dim]No candidate premises identified.[/dim]")

        # ── Section 7: META-ANALYSIS ─────────────────────────────
        console.print("\n[bold]7. META-ANALYSIS[/bold]")
        self._print_meta_analysis(report)

    def _build_candidate_premises(self, report: dict) -> list[dict]:
        """Combine candidates from ML prediction, historical analogs, and premise engine."""
        candidates = []

        # From ML prediction
        prediction = report.get("prediction", {})
        top_predictions = prediction.get("top_predictions", [])
        for pred in top_predictions[:2]:
            candidates.append({
                "premise_to_drop": f"Premise error type: {pred['error_type']}",
                "how_to_test": pred.get("test_suggestion", "Derive consequences of dropping this assumption"),
                "historical_resemblance": pred.get("historical_example", "See historical analogs above"),
                "source": "ml_prediction",
            })

        # From historical analogs
        for m in report.get("historical_matches", [])[:3]:
            old_premise = m.get("old_premise", "")
            qg_translation = m.get("qg_translation", "")
            if qg_translation:
                candidates.append({
                    "premise_to_drop": qg_translation,
                    "how_to_test": f"Follow the pattern from {m.get('field', '?')}: {m.get('new_premise', '?')}",
                    "historical_resemblance": f"{m.get('field', '?')} ({m.get('year', '?')}): dropped '{old_premise}'",
                    "source": "historical_analog",
                })

        # From premise engine
        for s in report.get("premise_shifts", [])[:5]:
            if s.get("score", 0) > 0.3:
                candidates.append({
                    "premise_to_drop": s.get("proposed_shift", ""),
                    "how_to_test": s.get("how_to_test", "See premise report for details"),
                    "historical_resemblance": s.get("historical_analog", "None identified"),
                    "source": "premise_engine",
                })

        # Deduplicate by rough similarity of premise_to_drop
        seen = set()
        deduped = []
        for c in candidates:
            key = c["premise_to_drop"][:50].lower()
            if key not in seen:
                seen.add(key)
                deduped.append(c)

        return deduped

    def _print_meta_analysis(self, report: dict):
        """Print honest assessment of confidence and limitations."""
        symptoms = report["symptoms"]
        matches = report["historical_matches"]
        cv_accuracy = report["cv_accuracy"]
        prediction = report["prediction"]

        # Confidence assessment
        n_symptoms = len(symptoms)
        high_conf_symptoms = [s for s in symptoms if s.confidence > 0.7]
        top_similarity = matches[0].get("similarity", 0) if matches else 0

        lines = []

        # What we're sure about
        lines.append("[bold]What the model is relatively confident about:[/bold]")
        if high_conf_symptoms:
            lines.append(f"  - {len(high_conf_symptoms)} high-confidence symptoms detected")
            for s in high_conf_symptoms[:3]:
                lines.append(f"    * {s.symptom_type.name}: {s.description[:60]}")
        if top_similarity > 0.7:
            lines.append(f"  - Strong historical match (similarity {top_similarity:.2f})")
        if not high_conf_symptoms and top_similarity <= 0.7:
            lines.append("  - [dim]No high-confidence findings[/dim]")

        lines.append("")

        # What we're uncertain about
        lines.append("[bold]What the model is uncertain about:[/bold]")
        if cv_accuracy < 0.6:
            lines.append(f"  - ML prediction accuracy is low ({cv_accuracy:.1%}) — treat with skepticism")
        if n_symptoms < 3:
            lines.append(f"  - Only {n_symptoms} symptoms detected — may be missing data")
        if top_similarity < 0.5:
            lines.append(f"  - No strong historical analog found — this might be genuinely unprecedented")
        low_conf = [s for s in symptoms if s.confidence < 0.4]
        if low_conf:
            lines.append(f"  - {len(low_conf)} symptoms have low confidence and may be noise")

        lines.append("")

        # What might be missing
        lines.append("[bold]Potential missing symptoms:[/bold]")
        detected_types = {s.symptom_type for s in symptoms}
        all_types = set(SymptomType)
        missing = all_types - detected_types
        if missing:
            for st in sorted(missing, key=lambda x: x.name):
                lines.append(f"  - {st.name}: not detected (could be absent or undetectable from current data)")
        else:
            lines.append("  - All symptom types checked")

        lines.append("")

        # Honest limitations
        lines.append("[bold]Honest limitations:[/bold]")
        lines.append("  - Historical analogy is suggestive, not predictive — physics is not obligated to repeat")
        lines.append("  - The ML model is trained on a small dataset of historical paradigm shifts (~20-30 cases)")
        lines.append("  - Symptom detection depends on what has been published and extracted — unpublished insights are invisible")
        lines.append("  - Quantum gravity may require a type of premise shift not seen in any previous revolution")
        lines.append("  - This analysis identifies WHAT might be wrong, not WHAT is right — the creative leap is still human")

        console.print(Panel(
            "\n".join(lines),
            title="Meta-Analysis",
            border_style="dim",
        ))

    def save_markdown(self, path: Path):
        """Save full report as markdown."""
        if self._report is None:
            self.generate()
        report = self._report
        path = Path(path)

        lines = [
            "# Breakthrough Pattern Analysis Report",
            f"\nGenerated: {report['generated']}",
            f"Historical dataset: {report['dataset_size']} paradigm shifts",
        ]

        # Section 1: Symptoms (top 2 per type)
        lines.append("\n## 1. Detected Symptoms")
        symptoms: list[Symptom] = report["symptoms"]
        if symptoms:
            from collections import defaultdict as _dd
            _by_type = _dd(list)
            for s in symptoms:
                _by_type[s.symptom_type].append(s)

            lines.append(f"\n{len(symptoms)} total symptoms detected across {len(_by_type)} types.\n")
            lines.append("| Type | Count | Confidence | Description | Theories |")
            lines.append("|------|-------|-----------|-------------|----------|")
            for st in sorted(_by_type.keys(), key=lambda x: max(s.confidence for s in _by_type[x]), reverse=True):
                group = sorted(_by_type[st], key=lambda s: s.confidence, reverse=True)
                for j, s in enumerate(group[:2]):
                    theories = ", ".join(s.theories_involved[:3])
                    count = str(len(group)) if j == 0 else ""
                    lines.append(f"| {s.symptom_type.name if j == 0 else ''} | {count} | {s.confidence:.2f} | {s.description[:80]} | {theories} |")
        else:
            lines.append("\nNo symptoms detected.")

        # Section 2: Symptom Profile Comparison
        lines.append("\n## 2. Symptom Profile Comparison")
        matches = report["historical_matches"]
        if symptoms and matches:
            current_types = {s.symptom_type for s in symptoms}
            header_fields = ["Current QG"] + [m.get("field", "?")[:20] for m in matches[:3]]
            lines.append(f"\n| Symptom | {' | '.join(header_fields)} |")
            lines.append(f"|---------|{'|'.join(['------' for _ in header_fields])}|")

            all_types = set(current_types)
            for m in matches[:3]:
                for ms in m.get("symptoms_before", []):
                    if isinstance(ms, Symptom):
                        all_types.add(ms.symptom_type)

            for st in sorted(all_types, key=lambda x: x.name):
                row = [st.name]
                row.append("YES" if st in current_types else "---")
                for m in matches[:3]:
                    match_types = set()
                    for ms in m.get("symptoms_before", []):
                        if isinstance(ms, Symptom):
                            match_types.add(ms.symptom_type)
                    row.append("YES" if st in match_types else "---")
                lines.append(f"| {' | '.join(row)} |")

        # Section 3: Predicted Premise Error Type
        lines.append("\n## 3. Predicted Premise Error Type")
        prediction = report["prediction"]
        cv_accuracy = report["cv_accuracy"]
        if prediction:
            top_predictions = prediction.get("top_predictions", [])
            if top_predictions:
                best = top_predictions[0]
                lines.append(f"\n**Primary prediction:** {best['error_type']} ({best['probability']:.1%})")
                lines.append(f"\n**Cross-validation accuracy:** {cv_accuracy:.1%}")
                lines.append("\n| Rank | Error Type | Probability |")
                lines.append("|------|-----------|-------------|")
                for i, pred in enumerate(top_predictions[:3], 1):
                    lines.append(f"| {i} | {pred['error_type']} | {pred['probability']:.1%} |")

        # Section 4: Historical Analogs
        lines.append("\n## 4. Historical Analogs")
        for i, m in enumerate(matches[:3], 1):
            lines.append(f"\n### Analog #{i}: {m.get('field', '?')} ({m.get('year', '?')})")
            lines.append(f"\n- **Person:** {m.get('person', '?')}")
            lines.append(f"- **Wrong premise:** {m.get('old_premise', '?')}")
            lines.append(f"- **The fix:** {m.get('new_premise', '?')}")
            lines.append(f"- **Similarity score:** {m.get('similarity', 0):.2f}")
            qg = m.get("qg_translation", "")
            if qg:
                lines.append(f"- **If the analog holds for QG:** {qg}")

        # Section 5: Constraints
        lines.append("\n## 5. Constraints")
        lines.append("\nResults any premise shift MUST reproduce:")
        constraints = report["constraints"]
        if constraints:
            for c in constraints:
                lines.append(f"- **{c.quantity_type}** ({c.strength}): {', '.join(c.theories_agree)}")
        else:
            lines.append("\nNo convergence constraints found.")

        # Section 6: Candidate Premises
        lines.append("\n## 6. Candidate Premises to Question")
        candidates = self._build_candidate_premises(report)
        if candidates:
            for i, c in enumerate(candidates[:10], 1):
                lines.append(f"\n### Candidate #{i}")
                lines.append(f"- **What to drop:** {c['premise_to_drop']}")
                lines.append(f"- **How to test:** {c['how_to_test']}")
                lines.append(f"- **Resembles:** {c['historical_resemblance']}")
                lines.append(f"- **Source:** {c['source']}")

        # Section 7: Meta-Analysis
        lines.append("\n## 7. Meta-Analysis")
        symptoms = report["symptoms"]
        high_conf = [s for s in symptoms if s.confidence > 0.7]
        top_sim = matches[0].get("similarity", 0) if matches else 0

        lines.append("\n### Confidence Assessment")
        if high_conf:
            lines.append(f"- {len(high_conf)} high-confidence symptoms detected")
        if top_sim > 0.7:
            lines.append(f"- Strong historical match (similarity {top_sim:.2f})")

        lines.append("\n### Uncertainties")
        if cv_accuracy < 0.6:
            lines.append(f"- ML prediction accuracy is low ({cv_accuracy:.1%})")
        if len(symptoms) < 3:
            lines.append(f"- Only {len(symptoms)} symptoms detected")
        if top_sim < 0.5:
            lines.append("- No strong historical analog found")

        lines.append("\n### Missing Symptoms")
        detected = {s.symptom_type for s in symptoms}
        for st in sorted(set(SymptomType) - detected, key=lambda x: x.name):
            lines.append(f"- {st.name}: not detected")

        lines.append("\n### Honest Limitations")
        lines.append("- Historical analogy is suggestive, not predictive")
        lines.append("- ML model trained on small dataset (~20-30 historical cases)")
        lines.append("- Symptom detection depends on published and extracted literature")
        lines.append("- Quantum gravity may require unprecedented type of premise shift")
        lines.append("- This identifies WHAT might be wrong, not WHAT is right")

        path.write_text("\n".join(lines))
        console.print(f"  [green]Report saved to {path}[/green]")
