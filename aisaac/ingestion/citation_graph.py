"""
Citation Graph Builder.

Builds a citation network between papers to:
1. Identify the most influential papers per approach
2. Find BRIDGE PAPERS that cite multiple approaches (highest priority)
3. Trace how ideas flow between theory communities
4. Weight papers by their cross-theory influence score

Bridge papers are the most likely to contain or hint at
cross-theory connections, so they get priority in extraction.
"""
from __future__ import annotations

import json
import logging
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

import networkx as nx
import numpy as np

from ..knowledge.base import KnowledgeBase

log = logging.getLogger(__name__)


@dataclass
class CitationNode:
    arxiv_id: str
    title: str
    theory_tags: list[str]
    year: int
    cited_by: list[str] = field(default_factory=list)   # papers that cite this
    cites: list[str] = field(default_factory=list)       # papers this cites
    cross_theory_score: float = 0.0                       # how cross-theory is this paper
    pagerank: float = 0.0


class CitationGraph:
    """
    Build and analyze the citation network of QG papers.
    """

    def __init__(self, kb: KnowledgeBase):
        self.kb = kb
        self.graph = nx.DiGraph()
        self.nodes: dict[str, CitationNode] = {}

    def build_from_kb(self):
        """Build graph from papers in the knowledge base."""
        papers = self.kb.conn.execute("SELECT * FROM papers").fetchall()
        
        for p in papers:
            p = dict(p)
            aid = p["arxiv_id"]
            tags = json.loads(p["theory_tags"]) if isinstance(p["theory_tags"], str) else p["theory_tags"]
            
            self.nodes[aid] = CitationNode(
                arxiv_id=aid,
                title=p["title"],
                theory_tags=tags,
                year=p["year"],
            )
            self.graph.add_node(aid, **{
                "title": p["title"],
                "theory_tags": tags,
                "year": p["year"],
            })

    def add_citations_from_latex(self, arxiv_id: str, latex_text: str):
        """
        Extract citation references from LaTeX source and add edges.
        Looks for \\cite{...} commands and matches to known papers.
        """
        # Extract all cite keys
        cite_pattern = re.compile(r'\\cite[tp]?\{([^}]+)\}')
        cite_keys = set()
        for m in cite_pattern.finditer(latex_text):
            keys = m.group(1).split(",")
            for k in keys:
                cite_keys.add(k.strip())

        if arxiv_id not in self.nodes:
            return

        # Try to match cite keys to known papers (by partial arXiv ID match)
        for key in cite_keys:
            for known_id in self.nodes:
                if key in known_id or known_id.split("/")[-1] in key:
                    self.graph.add_edge(arxiv_id, known_id)
                    self.nodes[arxiv_id].cites.append(known_id)
                    self.nodes[known_id].cited_by.append(arxiv_id)

    def compute_cross_theory_scores(self):
        """
        Score each paper by how cross-theory it is.
        
        High score = paper cites or is cited by papers from multiple approaches.
        These are the bridge papers we care most about.
        """
        for aid, node in self.nodes.items():
            # Theories this paper directly touches
            own_theories = set(node.theory_tags)
            
            # Theories of papers it cites
            cited_theories = set()
            for cited_id in node.cites:
                if cited_id in self.nodes:
                    cited_theories.update(self.nodes[cited_id].theory_tags)
            
            # Theories of papers that cite it
            citing_theories = set()
            for citing_id in node.cited_by:
                if citing_id in self.nodes:
                    citing_theories.update(self.nodes[citing_id].theory_tags)
            
            # Combined unique theories
            all_theories = own_theories | cited_theories | citing_theories
            all_theories.discard("unclassified")
            
            # Score: number of distinct theories involved
            # Weighted: direct tags count 3x, cited 2x, citing 1x
            score = (
                3 * len(own_theories - {"unclassified"}) +
                2 * len(cited_theories - own_theories - {"unclassified"}) +
                1 * len(citing_theories - own_theories - cited_theories - {"unclassified"})
            )
            node.cross_theory_score = score

    def compute_pagerank(self):
        """Compute PageRank to find most influential papers."""
        if len(self.graph.nodes) == 0:
            return
        try:
            pr = nx.pagerank(self.graph, alpha=0.85)
            for aid, score in pr.items():
                if aid in self.nodes:
                    self.nodes[aid].pagerank = score
        except Exception as e:
            log.warning(f"PageRank computation failed: {e}")

    def get_bridge_papers(self, min_score: float = 3.0, top_n: int = 50) -> list[CitationNode]:
        """Get top bridge papers ranked by cross-theory score."""
        self.compute_cross_theory_scores()
        bridges = [n for n in self.nodes.values() if n.cross_theory_score >= min_score]
        bridges.sort(key=lambda n: n.cross_theory_score, reverse=True)
        return bridges[:top_n]

    def get_most_influential(self, theory: str | None = None, top_n: int = 20) -> list[CitationNode]:
        """Get most influential papers by PageRank, optionally filtered by theory."""
        self.compute_pagerank()
        nodes = list(self.nodes.values())
        if theory:
            nodes = [n for n in nodes if theory in n.theory_tags]
        nodes.sort(key=lambda n: n.pagerank, reverse=True)
        return nodes[:top_n]

    def get_theory_flow(self) -> dict[tuple[str, str], int]:
        """
        Count cross-theory citations: how many papers from theory A cite theory B?
        Returns dict of (theory_a, theory_b) → count.
        """
        flow = defaultdict(int)
        for aid, node in self.nodes.items():
            for cited_id in node.cites:
                if cited_id in self.nodes:
                    cited_node = self.nodes[cited_id]
                    for ta in node.theory_tags:
                        for tb in cited_node.theory_tags:
                            if ta != tb and ta != "unclassified" and tb != "unclassified":
                                flow[(ta, tb)] += 1
        return dict(flow)

    def export_for_visualization(self, output_path: str = "citation_graph.json"):
        """Export graph data for visualization."""
        data = {
            "nodes": [
                {
                    "id": aid,
                    "title": node.title[:80],
                    "theories": node.theory_tags,
                    "year": node.year,
                    "cross_theory_score": node.cross_theory_score,
                    "pagerank": node.pagerank,
                }
                for aid, node in self.nodes.items()
            ],
            "edges": [
                {"source": u, "target": v}
                for u, v in self.graph.edges()
            ],
            "theory_flow": {
                f"{a}->{b}": count
                for (a, b), count in self.get_theory_flow().items()
            },
        }
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)
        log.info(f"Citation graph exported to {output_path}")


def visualize_theory_connections(
    graph: CitationGraph, output_path: str = "theory_connections.png",
):
    """
    Create a high-level visualization of how QG theories cite each other.
    Nodes = theories, edge width = number of cross-citations.
    """
    import matplotlib.pyplot as plt

    flow = graph.get_theory_flow()
    if not flow:
        log.warning("No cross-theory citations to visualize")
        return

    theory_colors = {
        "string_theory": "#e41a1c",
        "loop_quantum_gravity": "#377eb8",
        "cdt": "#4daf4a",
        "asymptotic_safety": "#984ea3",
        "causal_sets": "#ff7f00",
        "horava_lifshitz": "#c4a600",
        "noncommutative_geometry": "#a65628",
        "emergent_gravity": "#f781bf",
    }

    G = nx.DiGraph()
    for (ta, tb), count in flow.items():
        if ta in theory_colors and tb in theory_colors:
            G.add_edge(ta, tb, weight=count)

    if len(G.nodes) == 0:
        return

    fig, ax = plt.subplots(1, 1, figsize=(14, 10))
    pos = nx.spring_layout(G, k=2, seed=42)
    
    # Draw edges with width proportional to citation count
    max_weight = max(d["weight"] for _, _, d in G.edges(data=True)) or 1
    for u, v, d in G.edges(data=True):
        width = 1 + 5 * d["weight"] / max_weight
        ax.annotate(
            "", xy=pos[v], xytext=pos[u],
            arrowprops=dict(
                arrowstyle="->", lw=width,
                color="gray", alpha=0.5,
                connectionstyle="arc3,rad=0.1",
            ),
        )

    # Draw nodes
    for theory in G.nodes:
        x, y = pos[theory]
        color = theory_colors.get(theory, "#999999")
        n_papers = sum(1 for n in graph.nodes.values() if theory in n.theory_tags)
        size = max(300, n_papers * 5)
        ax.scatter(x, y, s=size, c=color, zorder=5, edgecolors="black", linewidths=1)
        label = theory.replace("_", "\n")
        ax.annotate(label, (x, y), fontsize=8, ha="center", va="center", fontweight="bold")

    ax.set_title("Quantum Gravity Theory Citation Network", fontsize=14)
    ax.axis("off")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    log.info(f"Theory connection plot saved to {output_path}")
