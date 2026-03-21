"""
AIsaac Main Pipeline.

Orchestrates the full discovery loop:
  1. Ingest papers (tiered)
  2. Extract formulas (LLM)
  3. Normalize notation
  4. Compare across theories (6 levels)
  5. ML pattern detection (embed, cluster, anomaly)
  6. Generate conjectures (LLM)
  7. Verify conjectures (algebraic, numerical, dimensional, counterexample)
  8. Check novelty
  9. Output ranked conjectures + report
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress

from .config import (
    PipelineConfig, Tier, DB_PATH, DATA_DIR,
    THEORIES, QuantityType,
)
from ..knowledge.base import KnowledgeBase, Conjecture
from ..knowledge.normalizer import DeepNormalizer
from ..ingestion.crawler import ArxivCrawler
from ..ingestion.extractor import FormulaExtractor
from ..ingestion.latex_parser import LatexParser
from ..ingestion.citation_graph import CitationGraph, visualize_theory_connections
from ..ingestion.deduplicator import FormulaDeduplicator
from ..comparison.engine import ComparisonEngine
from ..ml.patterns import (
    FormulaEmbedder, CrossTheoryClusterer,
    UniversalityDetector, AnomalyDetector,
    create_embedding_plot,
)
from ..ml.semantic import SemanticEmbedder
from ..conjecture.generator import ConjectureGenerator
from ..verification.engine import VerificationEngine
from ..output.visualizations import generate_all_plots
from ..output.paper_writer import PaperWriter
from .state import PipelineState
from ..knowledge.known_connections import validate_against_known, KNOWN_CONNECTIONS

log = logging.getLogger("aisaac")
console = Console()


class AIsaacPipeline:
    """Main pipeline controller."""

    def __init__(self, config: PipelineConfig | None = None):
        self.config = config or PipelineConfig()
        self.kb = KnowledgeBase(DB_PATH)
        self.state = PipelineState()
        self.crawler = ArxivCrawler(self.kb)
        self.extractor = FormulaExtractor(self.kb)
        self.latex_parser = LatexParser()
        self.normalizer = DeepNormalizer()
        self.deduplicator = FormulaDeduplicator(self.kb)
        self.citation_graph = CitationGraph(self.kb)
        self.comparator = ComparisonEngine(self.kb)
        self.embedder = FormulaEmbedder()
        self.semantic = SemanticEmbedder()
        self.clusterer = CrossTheoryClusterer(min_cluster_size=self.config.cluster_min_size)
        self.universality = UniversalityDetector()
        self.anomaly = AnomalyDetector()
        self.conjecturer = ConjectureGenerator(self.kb)
        self.verifier = VerificationEngine(self.kb)
        self.paper_writer = PaperWriter(self.kb)

    def run(self, tier: Tier = Tier.CORE_REVIEWS):
        """Run the full pipeline with resume support."""
        console.print(Panel.fit(
            "[bold cyan]AIsaac: Quantum Gravity Theory Connection Finder[/bold cyan]\n"
            f"Tier: {tier.name} | DB: {DB_PATH}",
            border_style="cyan",
        ))

        # Show resume state if any
        next_phase = self.state.get_next_phase()
        if next_phase and next_phase != "ingest_tier1":
            console.print(f"[yellow]Resuming from: {next_phase}[/yellow]")
            console.print(self.state.summary())

        # ── Phase 1: Ingest ─────────────────────────────────────
        if not self.state.is_completed("ingest_tier1"):
            console.print("\n[bold]Phase 1: Paper Ingestion[/bold]")
            self.state.mark_started("ingest_tier1")
            try:
                self._ingest(tier)
                self.state.mark_completed("ingest_tier1", {"tier": tier.name})
            except Exception as e:
                self.state.mark_failed("ingest_tier1", str(e))
                raise

        # ── Phase 2: Extract ────────────────────────────────────
        if not self.state.is_completed("extract"):
            console.print("\n[bold]Phase 2: Formula Extraction[/bold]")
            self.state.mark_started("extract")
            try:
                self._extract()
                self.state.mark_completed("extract", {"formulas": self.kb.count_formulas()})
            except Exception as e:
                self.state.mark_failed("extract", str(e))
                raise

        # ── Phase 3: Deduplicate + Citation Graph ───────────────
        if not self.state.is_completed("deduplicate"):
            console.print("\n[bold]Phase 3: Deduplication & Citation Graph[/bold]")
            self.state.mark_started("deduplicate")
            try:
                self._deduplicate_and_graph()
                self.state.mark_completed("deduplicate")
            except Exception as e:
                self.state.mark_failed("deduplicate", str(e))
                raise

        # ── Phase 4: Compare ────────────────────────────────────
        console.print("\n[bold]Phase 4: Cross-Theory Comparison[/bold]")
        self.state.mark_started("compare")
        comparison_results = self._compare()
        self.state.mark_completed("compare", {"matches": len(comparison_results)})

        # ── Phase 5: ML Pattern Detection ───────────────────────
        console.print("\n[bold]Phase 5: ML Pattern Detection[/bold]")
        self.state.mark_started("ml_embed")
        clusters, universalities, anomalies = self._detect_patterns()
        self.state.mark_completed("ml_embed", {
            "clusters": len(clusters), "anomalies": len(anomalies),
        })

        # ── Phase 6: Conjecture Generation ──────────────────────
        console.print("\n[bold]Phase 6: Conjecture Generation[/bold]")
        self.state.mark_started("conjecture_from_comparisons")
        conjectures = self._generate_conjectures(
            comparison_results, clusters, universalities, anomalies
        )
        self.state.mark_completed("conjecture_from_comparisons", {"count": len(conjectures)})

        # ── Phase 7: Verification ──────────────────────────────
        console.print("\n[bold]Phase 7: Verification[/bold]")
        self.state.mark_started("verify")
        self._verify_conjectures(conjectures)
        self.state.mark_completed("verify")

        # ── Phase 8: Validation against known connections ───────
        console.print("\n[bold]Phase 8: Validation Against Known Connections[/bold]")
        self._validate_known()

        # ── Phase 9: Visualizations ─────────────────────────────
        console.print("\n[bold]Phase 9: Visualizations[/bold]")
        try:
            generate_all_plots(self.kb)
            console.print("  [green]All plots generated[/green]")
        except Exception as e:
            console.print(f"  [dim]Visualization error: {e}[/dim]")

        # ── Phase 10: Report + Paper Draft ──────────────────────
        console.print("\n[bold]Phase 10: Report & Paper Draft[/bold]")
        self._generate_report()
        try:
            paper_path = DATA_DIR / "paper_draft.tex"
            self.paper_writer.write_full_paper(paper_path)
            console.print(f"  [green]Paper draft: {paper_path}[/green]")
        except Exception as e:
            console.print(f"  [dim]Paper draft error: {e}[/dim]")

        # ── Final summary from LLM client ───────────────────────
        try:
            from .llm_client import get_client
            client = get_client()
            console.print(f"\n{client.cost_tracker.summary()}")
            if client.cache:
                console.print(f"  Cache: {client.cache.hits} hits, {client.cache.misses} misses")
        except Exception:
            pass

    # ── Phase Implementations ────────────────────────────────────

    def _ingest(self, tier: Tier):
        """Ingest papers based on tier. Skip if DB already has papers."""
        summary = self.kb.summary()
        existing = summary['papers']
        console.print(f"  Current DB: {existing} papers, {summary['formulas']} formulas")

        if existing > 0:
            console.print(f"  [green]Skipping ingestion — {existing} papers already in DB[/green]")
            return

        if tier.value >= Tier.CORE_REVIEWS.value:
            n = self.crawler.ingest_tier1()
            console.print(f"  [green]Tier 1: {n} review papers ingested[/green]")

        if tier.value >= Tier.HIGH_IMPACT.value:
            n = self.crawler.ingest_tier2()
            console.print(f"  [green]Tier 2: {n} high-impact papers ingested[/green]")

        if tier.value >= Tier.RECENT_FRONTIER.value:
            n = self.crawler.ingest_tier3()
            console.print(f"  [green]Tier 3: {n} recent papers ingested[/green]")

        # Always look for bridge papers
        bridges = self.crawler.find_bridge_papers()
        console.print(f"  [yellow]Found {len(bridges)} bridge papers (cite multiple approaches)[/yellow]")

        summary = self.kb.summary()
        console.print(f"  Total: {summary['papers']} papers")

    def _extract(self):
        """Extract formulas from all papers that haven't been processed."""
        from concurrent.futures import ThreadPoolExecutor, as_completed

        papers_with_formulas = set()
        for f in self.kb.get_all_formulas():
            papers_with_formulas.add(f["paper_id"])

        all_papers = self.kb.conn.execute("SELECT * FROM papers").fetchall()
        unprocessed = [dict(p) for p in all_papers if p["id"] not in papers_with_formulas]

        console.print(f"  Papers to process: {len(unprocessed)}")

        # Phase A: Download sources sequentially (arXiv rate limit)
        console.print(f"  Downloading sources...")
        paper_sources = []
        for paper in unprocessed:
            arxiv_id = paper["arxiv_id"]
            src_path = self.crawler.download_latex_source(arxiv_id)
            if not src_path:
                src_path = self.crawler.download_pdf(arxiv_id)
            paper_sources.append((paper, src_path))
        console.print(f"  Downloaded {sum(1 for _, s in paper_sources if s)} sources")

        # Phase B: Prepare content (parse LaTeX) — fast, can be sequential
        paper_contents = []
        for paper, src_path in paper_sources:
            if src_path and src_path.is_dir():
                raw_eqs = self.latex_parser.parse_file(src_path)
                if raw_eqs:
                    content = self._build_enriched_content(raw_eqs, src_path)
                else:
                    content = self.extractor._read_latex(src_path)
            elif src_path and src_path.suffix == ".pdf":
                content = self.extractor._read_pdf(src_path)
            else:
                content = f"Title: {paper['title']}\n\nAbstract: {paper['abstract']}"
            paper_contents.append((paper, content))

        # Phase C: LLM extraction (sequential to avoid rate limits)
        max_workers = 1
        console.print(f"  Extracting formulas from {len(paper_contents)} papers...")
        done_count = 0
        fail_count = 0

        def extract_one(paper_content_pair):
            paper, content = paper_content_pair
            try:
                return paper, self.extractor.extract_from_text(paper, content, normalize=True)
            except Exception as e:
                log.warning(f"  Extraction failed for {paper['arxiv_id']}: {e}")
                return paper, []

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {pool.submit(extract_one, pc): pc[0] for pc in paper_contents}
            for future in as_completed(futures):
                paper = futures[future]
                try:
                    paper_result, formulas = future.result()
                    done_count += 1
                    n = len(formulas)
                    if n > 0:
                        console.print(
                            f"  [{done_count}/{len(unprocessed)}] "
                            f"{paper_result['title'][:60]}... → {n} formulas",
                        )
                    else:
                        console.print(
                            f"  [{done_count}/{len(unprocessed)}] "
                            f"{paper_result['title'][:60]}... → 0 formulas",
                            style="dim",
                        )
                except Exception as e:
                    done_count += 1
                    fail_count += 1
                    log.warning(f"  [{done_count}/{len(unprocessed)}] Failed: {e}")

        console.print(f"  Extraction complete: {done_count} papers, {fail_count} failures")

        summary = self.kb.summary()
        console.print(f"  Total formulas: {summary['formulas']}")
        if summary.get("formulas_by_theory"):
            for theory, count in sorted(summary["formulas_by_theory"].items()):
                console.print(f"    {theory}: {count}")

    def _build_enriched_content(self, raw_eqs: list, src_path, max_equations: int = 30) -> str:
        """
        Build enriched content from LaTeX-parsed equations.
        Gives the LLM pre-identified equations with context,
        so it can focus on CLASSIFYING them rather than finding them.

        Caps at max_equations to avoid overwhelming the LLM with huge prompts.
        Prioritizes equations from results/conclusion sections and labeled equations.
        """
        # Prioritize: labeled equations and those in results/conclusion sections first
        priority_sections = {"results", "conclusion", "discussion", "prediction", "entropy", "correction", "spectral"}

        def eq_priority(eq):
            section_lower = (eq.section or "").lower()
            has_priority_section = any(s in section_lower for s in priority_sections)
            has_label = bool(eq.label)
            return (not has_priority_section, not has_label)

        sorted_eqs = sorted(raw_eqs, key=eq_priority)
        selected = sorted_eqs[:max_equations]

        parts = [f"The following {len(selected)} key equations (of {len(raw_eqs)} total) were extracted from the paper:\n"]
        for eq in selected:
            parts.append(f"--- Equation (section: {eq.section}, env: {eq.environment}) ---")
            if eq.label:
                parts.append(f"Label: {eq.label}")
            # Trim context to keep prompt size reasonable
            ctx_before = (eq.context_before or "")[-200:]
            ctx_after = (eq.context_after or "")[:200]
            parts.append(f"Context before: ...{ctx_before}")
            parts.append(f"EQUATION: {eq.latex}")
            parts.append(f"Context after: {ctx_after}...")
            parts.append("")
        return "\n".join(parts)

    def _validate_known(self):
        """
        Validate the system against known cross-theory connections.
        This is the credibility check: if we can't find known connections,
        the novel ones aren't trustworthy.
        """
        conjectures = self.kb.get_conjectures()
        result = validate_against_known(conjectures)

        found = result["found"]
        missed = result["missed"]
        recall = result["recall"]

        console.print(f"  Known connections: {len(found)}/{result['total_known']} found ({recall:.0%} recall)")

        if found:
            console.print("  [green]Found:[/green]")
            for kc in found:
                console.print(f"    ✓ {kc.title}")

        if missed:
            console.print("  [yellow]Missed:[/yellow]")
            for kc in missed:
                diff = "[easy]" if kc.difficulty == "easy" else f"[{kc.difficulty}]"
                console.print(f"    ✗ {kc.title} {diff}")

        if recall < 0.5:
            console.print(
                "\n  [bold red]WARNING: Recall < 50%. The system is missing known connections.[/bold red]\n"
                "  Novel conjectures should be treated with extra skepticism.\n"
                "  Check: notation normalization, formula extraction quality, comparison thresholds."
            )
        elif recall >= 0.8:
            console.print(
                "\n  [bold green]High recall — system validated. Novel conjectures are credible.[/bold green]"
            )

        summary = self.kb.summary()
        console.print(f"  Total formulas: {summary['formulas']}")
        if summary.get("formulas_by_theory"):
            for theory, count in sorted(summary["formulas_by_theory"].items()):
                console.print(f"    {theory}: {count}")

    def _deduplicate_and_graph(self):
        """Deduplicate formulas and build citation graph."""
        # Deduplication
        clusters = self.deduplicator.deduplicate()
        cross_theory = self.deduplicator.get_cross_theory_duplicates()
        console.print(
            f"  Dedup clusters: {len(clusters)} total, "
            f"{len(cross_theory)} cross-theory (same formula in different theories!)"
        )
        for ct in cross_theory[:5]:
            console.print(
                f"    [yellow]{ct.canonical_description[:60]}... "
                f"({', '.join(ct.theory_slugs)})[/yellow]"
            )

        # Citation graph
        self.citation_graph.build_from_kb()
        bridges = self.citation_graph.get_bridge_papers(min_score=3.0)
        console.print(f"  Citation graph: {len(self.citation_graph.nodes)} nodes")
        console.print(f"  Bridge papers (cite 2+ approaches): {len(bridges)}")
        
        try:
            visualize_theory_connections(self.citation_graph, str(DATA_DIR / "citation_flow.png"))
        except Exception as e:
            console.print(f"  [dim]Citation viz error: {e}[/dim]")

    def _compare(self) -> list:
        """Run multi-level comparison across all theories."""
        results = self.comparator.compare_all(
            min_score=self.config.comparison_threshold,
        )
        console.print(f"  Found {len(results)} cross-theory matches")

        # Show top matches
        if results:
            table = Table(title="Top Cross-Theory Matches")
            table.add_column("Theory A")
            table.add_column("Theory B")
            table.add_column("Quantity")
            table.add_column("Score", justify="right")
            table.add_column("Type")

            for r in results[:20]:
                table.add_row(
                    r.theory_a, r.theory_b,
                    r.quantity_type_a,
                    f"{r.combined_score:.3f}",
                    r.match_type,
                )
            console.print(table)

        # Also compare per quantity type
        for qt in QuantityType:
            if qt == QuantityType.OTHER:
                continue
            qr = self.comparator.compare_for_quantity(qt.value, min_score=0.3)
            if qr:
                console.print(f"  {qt.value}: {len(qr)} matches")

        return results

    def _detect_patterns(self) -> tuple[list, list, list]:
        """ML pattern detection: embed, cluster, detect universality + anomalies."""
        formulas = self.kb.get_all_formulas(
            formula_types=["prediction", "correction", "key_equation"]
        )
        console.print(f"  Embedding {len(formulas)} formulas...")

        # Structural + fingerprint embeddings
        embeddings = self.embedder.embed_all(formulas)
        console.print(f"  Structural embeddings: {len(embeddings)}")

        # Semantic embeddings (description-based)
        console.print(f"  Running semantic matching...")
        semantic_matches = self.semantic.find_cross_theory_semantic_matches(
            formulas, threshold=0.7,
        )
        console.print(f"  Semantic cross-theory matches: {len(semantic_matches)}")
        for fa, fb, sim in semantic_matches[:5]:
            console.print(
                f"    [cyan]{fa.get('theory_slug','?')}: {fa.get('description','')[:40]}...[/cyan]"
            )
            console.print(
                f"    [cyan]↔ {fb.get('theory_slug','?')}: {fb.get('description','')[:40]}... "
                f"(sim={sim:.3f})[/cyan]"
            )

        # Cluster
        clusters = self.clusterer.cluster(embeddings)
        cross_theory = [c for c in clusters if c.is_cross_theory]
        universal = [c for c in clusters if c.is_universal]
        console.print(
            f"  Clusters: {len(clusters)} total, "
            f"{len(cross_theory)} cross-theory, {len(universal)} universal"
        )

        # Universality detection per quantity
        universalities = []
        for qt in QuantityType:
            if qt == QuantityType.OTHER:
                continue
            result = self.universality.detect(self.kb, qt.value)
            if result:
                universalities.append(result)
                status = "[green]UNIVERSAL[/green]" if result.is_universal else "[yellow]partial[/yellow]"
                console.print(
                    f"  {qt.value}: {status} "
                    f"(agree: {len(result.theories_agree)}, "
                    f"disagree: {len(result.theories_disagree)})"
                )

        # Anomaly detection
        anomalies = self.anomaly.detect_from_clusters(clusters, embeddings)
        anomalies += self.anomaly.detect_from_universality(universalities)
        console.print(f"  Anomalies detected: {len(anomalies)}")

        # Visualization
        if embeddings:
            plot_path = str(DATA_DIR / "formula_space.png")
            try:
                create_embedding_plot(embeddings, clusters, plot_path)
                console.print(f"  [dim]Plot saved to {plot_path}[/dim]")
            except Exception as e:
                console.print(f"  [dim]Plot failed: {e}[/dim]")

        return clusters, universalities, anomalies

    def _generate_conjectures(
        self, comparisons, clusters, universalities, anomalies,
    ) -> list[Conjecture]:
        """Generate conjectures from all evidence sources."""
        all_conjectures = []

        # From top comparison results — pick top 3 per quantity_type for diversity
        formulas_cache = {f["id"]: f for f in self.kb.get_all_formulas()}

        from collections import defaultdict
        by_quantity = defaultdict(list)
        for r in comparisons:
            qt = r.quantity_type_a or "other"
            by_quantity[qt].append(r)

        diverse_comparisons = []
        for qt, results in by_quantity.items():
            diverse_comparisons.extend(results[:3])

        console.print(f"  Generating conjectures from {len(diverse_comparisons)} comparisons ({len(by_quantity)} quantity types)...")

        for r in diverse_comparisons:
            fa = formulas_cache.get(r.formula_a_id, {})
            fb = formulas_cache.get(r.formula_b_id, {})
            if fa and fb:
                conjs = self.conjecturer.from_comparison(r, fa, fb)
                all_conjectures.extend(conjs)

        # From cross-theory clusters
        cross_clusters = [c for c in clusters if c.is_cross_theory]
        console.print(f"  Generating conjectures from {len(cross_clusters)} cross-theory clusters...")
        for c in cross_clusters[:10]:
            cluster_formulas = [formulas_cache[fid] for fid in c.formula_ids if fid in formulas_cache]
            conjs = self.conjecturer.from_cluster(c, cluster_formulas)
            all_conjectures.extend(conjs)

        # From universality results
        console.print(f"  Generating conjectures from {len(universalities)} universality checks...")
        for u in universalities:
            conjs = self.conjecturer.from_universality(u)
            all_conjectures.extend(conjs)

        # From anomalies
        top_anomalies = [a for a in anomalies if a.significance > 0.6]
        console.print(f"  Generating conjectures from {len(top_anomalies)} significant anomalies...")
        for a in top_anomalies[:10]:
            a_formulas = [formulas_cache[fid] for fid in a.formula_ids if fid in formulas_cache]
            conjs = self.conjecturer.from_anomaly(a, a_formulas)
            all_conjectures.extend(conjs)

        # Deduplicate: keep max 3 conjectures per conjecture_type+quantity combination
        seen = defaultdict(int)
        deduped = []
        for c in all_conjectures:
            # Extract primary quantity from the conjecture
            qty = getattr(c, 'quantity_type', '') or 'other'
            key = f"{c.conjecture_type}:{qty}"
            if seen[key] < 3:
                deduped.append(c)
                seen[key] += 1
        all_conjectures = deduped

        # Store all conjectures
        for c in all_conjectures:
            cid = self.kb.insert_conjecture(c)
            c.id = cid

        console.print(f"  [green]Total conjectures generated: {len(all_conjectures)}[/green]")
        return all_conjectures

    def _verify_conjectures(self, conjectures: list[Conjecture]):
        """Verify all conjectures."""
        console.print(f"  Verifying {len(conjectures)} conjectures...")

        verified = []
        disproved = []
        known = []
        inconclusive = []

        for i, c in enumerate(conjectures):
            console.print(
                f"  [{i+1}/{len(conjectures)}] {c.title[:60]}...",
                style="dim",
            )
            result = self.verifier.verify(c)

            # Update KB
            self.kb.update_conjecture_verification(
                c.id,
                algebraic=result.algebraic,
                numerical=result.numerical,
                dimensional=result.dimensional,
                counterexample=result.counterexample_found,
                is_novel=result.is_novel,
                status=result.overall_status,
            )

            if result.overall_status == "verified":
                verified.append((c, result))
            elif result.overall_status == "disproved":
                disproved.append((c, result))
            elif result.overall_status == "known":
                known.append((c, result))
            else:
                inconclusive.append((c, result))

        console.print(f"\n  Results:")
        console.print(f"    [green]Verified: {len(verified)}[/green]")
        console.print(f"    [red]Disproved: {len(disproved)}[/red]")
        console.print(f"    [yellow]Known: {len(known)} (rediscovered)[/yellow]")
        console.print(f"    [dim]Inconclusive: {len(inconclusive)}[/dim]")

        # Show verified conjectures
        if verified:
            console.print("\n[bold green]═══ VERIFIED NOVEL CONJECTURES ═══[/bold green]")
            for c, r in verified:
                console.print(Panel(
                    f"[bold]{c.title}[/bold]\n\n"
                    f"{c.statement_natural}\n\n"
                    f"LaTeX: {c.statement_latex}\n"
                    f"Theories: {', '.join(c.theories_involved)}\n"
                    f"Evidence score: {c.evidence_score:.2f}\n"
                    f"Significance: {c.significance_score:.2f}\n"
                    f"Novelty: {r.novelty_details[:100]}",
                    border_style="green",
                ))

    def _generate_report(self):
        """Generate final report."""
        report_path = DATA_DIR / "report.md"
        summary = self.kb.summary()
        conjectures = self.kb.get_conjectures()

        verified = [c for c in conjectures if c["status"] == "verified"]
        known = [c for c in conjectures if c["status"] == "known"]

        lines = [
            "# AIsaac Report",
            f"\nGenerated: {datetime.now().isoformat()}",
            f"\n## Summary",
            f"- Papers ingested: {summary['papers']}",
            f"- Formulas extracted: {summary['formulas']}",
            f"- Claimed connections found: {summary['claimed_connections']}",
            f"- Conjectures generated: {summary['conjectures']}",
            f"- Verified novel conjectures: {len(verified)}",
            f"- Rediscovered known connections: {len(known)}",
        ]

        if summary.get("formulas_by_theory"):
            lines.append("\n## Formulas by Theory")
            for theory, count in sorted(summary["formulas_by_theory"].items()):
                lines.append(f"- {theory}: {count}")

        if verified:
            lines.append("\n## Verified Novel Conjectures")
            for i, c in enumerate(verified, 1):
                lines.append(f"\n### {i}. {c['title']}")
                lines.append(f"\n{c['statement_natural']}")
                lines.append(f"\n**LaTeX:** `{c['statement_latex']}`")
                lines.append(f"\n**Theories:** {c['theories_involved']}")
                lines.append(f"**Evidence score:** {c['evidence_score']:.2f}")
                lines.append(f"**Significance:** {c['significance_score']:.2f}")

        if known:
            lines.append("\n## Rediscovered Known Connections (System Validation)")
            for c in known:
                lines.append(f"- {c['title']} ({c['theories_involved']})")

        lines.append("\n## All Conjectures (ranked)")
        for i, c in enumerate(conjectures, 1):
            status_emoji = {
                "verified": "✓", "disproved": "✗", 
                "known": "●", "inconclusive": "?",
                "proposed": "○",
            }.get(c["status"], "?")
            lines.append(
                f"{i}. [{status_emoji}] {c['title']} "
                f"(score={c['combined_score']:.2f}, status={c['status']})"
            )

        report = "\n".join(lines)
        report_path.write_text(report)
        console.print(f"  Report saved to {report_path}")
        console.print(Panel(
            f"[bold]Pipeline complete.[/bold]\n"
            f"Papers: {summary['papers']} | Formulas: {summary['formulas']} | "
            f"Conjectures: {summary['conjectures']} | "
            f"Verified novel: {len(verified)}",
            border_style="cyan",
        ))


def main():
    """CLI entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(str(DATA_DIR / "aisaac.log")),
        ],
    )

    import argparse
    parser = argparse.ArgumentParser(
        description="AIsaac: AI That Reads All of Quantum Gravity and Finds What Humans Missed",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  aisaac --tier 1              Run full pipeline on review papers
  aisaac --tier 2              Scale up to high-impact papers
  aisaac --compare-only        Re-run comparison on existing DB
  aisaac --status              Show pipeline state and DB summary
  aisaac --investigate 3       Deep-dive into conjecture #3
  aisaac --investigate-top 5   Deep-dive into top 5 conjectures
  aisaac --validate            Check known connections recall
  aisaac --reset               Reset pipeline state (re-run from scratch)
  aisaac --conjectures         List all conjectures with status
        """,
    )
    parser.add_argument(
        "--tier", type=int, default=1, choices=[1, 2, 3, 4],
        help="Ingestion tier (1=reviews, 2=high-impact, 3=recent, 4=all)"
    )
    parser.add_argument("--compare-only", action="store_true",
        help="Skip ingestion, run comparison on existing DB")
    parser.add_argument("--status", action="store_true",
        help="Show pipeline state and database summary")
    parser.add_argument("--investigate", type=int, metavar="ID",
        help="Deep-investigate a specific conjecture by ID")
    parser.add_argument("--investigate-top", type=int, metavar="N",
        help="Deep-investigate top N conjectures")
    parser.add_argument("--validate", action="store_true",
        help="Validate against known cross-theory connections")
    parser.add_argument("--conjectures", action="store_true",
        help="List all conjectures with their status")
    parser.add_argument("--reset", action="store_true",
        help="Reset pipeline state (allows re-running from scratch)")
    parser.add_argument("--db", type=str, default=str(DB_PATH),
        help="Database path")
    args = parser.parse_args()

    config = PipelineConfig(tier=Tier(args.tier))
    pipeline = AIsaacPipeline(config)

    # ── Status ───────────────────────────────────────────────
    if args.status:
        summary = pipeline.kb.summary()
        console.print(Panel.fit(
            "[bold cyan]AIsaac Database Status[/bold cyan]",
            border_style="cyan",
        ))
        console.print(f"  Papers: {summary['papers']}")
        console.print(f"  Formulas: {summary['formulas']}")
        console.print(f"  Conjectures: {summary.get('conjectures', 0)}")
        console.print(f"  Claimed connections: {summary.get('claimed_connections', 0)}")
        if summary.get("formulas_by_theory"):
            console.print("\n  Formulas by theory:")
            for theory, count in sorted(summary["formulas_by_theory"].items()):
                console.print(f"    {theory}: {count}")
        console.print(f"\n{pipeline.state.summary()}")
        try:
            from .llm_client import detect_backend
            backend = detect_backend()
            console.print(f"\n  LLM backend: {backend}")
        except Exception as e:
            console.print(f"\n  LLM backend: [red]not available ({e})[/red]")
        return

    # ── Reset ────────────────────────────────────────────────
    if args.reset:
        pipeline.state.reset()
        console.print("[green]Pipeline state reset. Next run will start from scratch.[/green]")
        return

    # ── Validate ─────────────────────────────────────────────
    if args.validate:
        pipeline._validate_known()
        return

    # ── List conjectures ─────────────────────────────────────
    if args.conjectures:
        conjectures = pipeline.kb.get_conjectures()
        if not conjectures:
            console.print("No conjectures in database. Run the pipeline first.")
            return
        table = Table(title=f"Conjectures ({len(conjectures)} total)")
        table.add_column("ID", style="dim", width=4)
        table.add_column("Status", width=12)
        table.add_column("Score", width=6, justify="right")
        table.add_column("Type", width=14)
        table.add_column("Title", width=50)
        table.add_column("Theories", width=25)

        status_styles = {
            "verified": "bold green", "known": "cyan",
            "disproved": "red", "inconclusive": "yellow", "proposed": "dim",
        }
        for c in conjectures:
            status = c["status"]
            style = status_styles.get(status, "")
            theories = c.get("theories_involved", "")
            if isinstance(theories, str):
                try:
                    theories = ", ".join(json.loads(theories))
                except Exception:
                    pass
            table.add_row(
                str(c["id"]),
                f"[{style}]{status}[/{style}]",
                f"{c['combined_score']:.2f}",
                c.get("conjecture_type", ""),
                c.get("title", "")[:50],
                str(theories)[:25],
            )
        console.print(table)
        return

    # ── Deep investigate ─────────────────────────────────────
    if args.investigate:
        from ..conjecture.investigator import DeepInvestigator
        investigator = DeepInvestigator(pipeline.kb)
        console.print(f"[bold]Deep investigation: conjecture #{args.investigate}[/bold]")
        report = investigator.investigate(args.investigate)
        verdict = report.get("verdict", "unknown")
        colors = {"promising": "green", "plausible": "yellow", "weak": "red", "likely_wrong": "red"}
        color = colors.get(verdict, "white")
        console.print(Panel(
            f"[bold]Verdict: [{color}]{verdict}[/{color}][/bold]\n\n"
            f"Confidence: {report.get('confidence', '?')}\n\n"
            f"Analysis: {report.get('mathematical_analysis', '?')[:300]}...\n\n"
            f"Significance: {report.get('significance_if_true', '?')[:200]}...\n\n"
            f"Next steps:\n" + "\n".join(f"  {i+1}. {s}" for i, s in enumerate(report.get("next_steps", [])[:5])),
            title=f"Investigation: Conjecture #{args.investigate}",
            border_style=color,
        ))
        console.print(f"  Full report: {DATA_DIR / f'investigation_{args.investigate}.json'}")
        return

    if args.investigate_top:
        from ..conjecture.investigator import DeepInvestigator
        investigator = DeepInvestigator(pipeline.kb)
        console.print(f"[bold]Deep investigation: top {args.investigate_top} conjectures[/bold]")
        reports = investigator.investigate_top_n(args.investigate_top)
        for r in reports:
            verdict = r.get("verdict", "unknown")
            console.print(f"  [{verdict}] {r.get('title', '?')[:60]}")
        return

    # ── Compare only ─────────────────────────────────────────
    if args.compare_only:
        console.print("[bold]Running comparison on existing database...[/bold]")
        comparisons = pipeline._compare()
        clusters, universalities, anomalies = pipeline._detect_patterns()
        conjectures = pipeline._generate_conjectures(
            comparisons, clusters, universalities, anomalies
        )
        pipeline._verify_conjectures(conjectures)
        pipeline._validate_known()
        pipeline._generate_report()
        return

    # ── Full pipeline ────────────────────────────────────────
    pipeline.run(Tier(args.tier))


if __name__ == "__main__":
    main()
