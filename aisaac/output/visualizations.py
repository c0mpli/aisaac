"""
Theory Connection Visualizations.

Creates publication-quality visualizations of:
1. Cross-theory connection graph (which theories are connected)
2. Formula embedding space (2D UMAP of all formulas)
3. Universality heatmap (which quantities are universal)
4. Conjecture evidence network
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from collections import defaultdict

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import networkx as nx

from ..knowledge.base import KnowledgeBase
from ..pipeline.config import THEORIES, DATA_DIR

log = logging.getLogger(__name__)

THEORY_COLORS = {
    "string_theory": "#e41a1c",
    "loop_quantum_gravity": "#377eb8",
    "cdt": "#4daf4a",
    "asymptotic_safety": "#984ea3",
    "causal_sets": "#ff7f00",
    "horava_lifshitz": "#c4a600",
    "noncommutative_geometry": "#a65628",
    "emergent_gravity": "#f781bf",
}

THEORY_SHORT = {
    "string_theory": "String",
    "loop_quantum_gravity": "LQG",
    "cdt": "CDT",
    "asymptotic_safety": "AS",
    "causal_sets": "CS",
    "horava_lifshitz": "HL",
    "noncommutative_geometry": "NCG",
    "emergent_gravity": "EG",
}


def plot_connection_graph(
    kb: KnowledgeBase,
    output_path: str | None = None,
):
    """
    Create a theory-level connection graph.
    
    Nodes = QG theories (sized by number of formulas)
    Edges = verified connections between theories (width = number of connections)
    """
    if output_path is None:
        output_path = str(DATA_DIR / "theory_connections.png")

    # Count formulas per theory
    formula_counts = {}
    for f in kb.get_all_formulas():
        slug = f["theory_slug"]
        formula_counts[slug] = formula_counts.get(slug, 0) + 1

    # Count connections per theory pair
    conjectures = kb.get_conjectures()
    pair_counts = defaultdict(int)
    pair_types = defaultdict(list)
    
    for c in conjectures:
        if c["status"] in ("verified", "known"):
            theories = json.loads(c["theories_involved"]) if isinstance(c["theories_involved"], str) else c["theories_involved"]
            for i, ta in enumerate(theories):
                for tb in theories[i+1:]:
                    pair = tuple(sorted([ta, tb]))
                    pair_counts[pair] += 1
                    pair_types[pair].append(c["conjecture_type"])

    # Build networkx graph
    G = nx.Graph()
    for slug in THEORY_COLORS:
        if slug in formula_counts:
            G.add_node(slug, size=formula_counts[slug])

    for (ta, tb), count in pair_counts.items():
        if ta in G.nodes and tb in G.nodes:
            G.add_edge(ta, tb, weight=count)

    if len(G.nodes) == 0:
        log.warning("No nodes to plot")
        return

    # Layout
    pos = nx.spring_layout(G, k=3, seed=42, iterations=100)

    fig, ax = plt.subplots(1, 1, figsize=(14, 10))
    fig.patch.set_facecolor("white")

    # Draw edges
    if G.edges():
        max_weight = max(d["weight"] for _, _, d in G.edges(data=True))
        for u, v, d in G.edges(data=True):
            width = 1 + 6 * d["weight"] / max(max_weight, 1)
            x = [pos[u][0], pos[v][0]]
            y = [pos[u][1], pos[v][1]]
            ax.plot(x, y, color="#999999", linewidth=width, alpha=0.6, zorder=1)
            # Label with count
            mx, my = (pos[u][0] + pos[v][0]) / 2, (pos[u][1] + pos[v][1]) / 2
            ax.annotate(
                str(d["weight"]), (mx, my),
                fontsize=8, ha="center", va="center",
                bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.8),
                zorder=3,
            )

    # Draw nodes
    for node in G.nodes():
        x, y = pos[node]
        size = 200 + 20 * formula_counts.get(node, 0)
        color = THEORY_COLORS.get(node, "#999999")
        ax.scatter(x, y, s=size, c=color, zorder=5, edgecolors="black", linewidths=1.5)
        label = THEORY_SHORT.get(node, node[:8])
        n_formulas = formula_counts.get(node, 0)
        ax.annotate(
            f"{label}\n({n_formulas})",
            (x, y), fontsize=9, ha="center", va="center",
            fontweight="bold", zorder=6,
        )

    # Legend
    legend_patches = [
        mpatches.Patch(color=c, label=THEORY_SHORT[s])
        for s, c in THEORY_COLORS.items()
        if s in G.nodes
    ]
    ax.legend(handles=legend_patches, loc="upper left", fontsize=8)

    ax.set_title(
        "Quantum Gravity Cross-Theory Connections\n"
        "(node size ∝ formulas, edge width ∝ verified connections)",
        fontsize=13,
    )
    ax.axis("off")
    plt.tight_layout()
    plt.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close()
    log.info(f"Connection graph saved to {output_path}")


def plot_universality_heatmap(
    kb: KnowledgeBase,
    output_path: str | None = None,
):
    """
    Heatmap: rows = theories, columns = comparable quantities.
    Cell color = prediction value (normalized).
    Shows at a glance which theories agree on which quantities.
    """
    if output_path is None:
        output_path = str(DATA_DIR / "universality_heatmap.png")

    quantities = [
        "spectral_dimension", "newton_correction", "black_hole_entropy",
        "bh_entropy_log_correction", "dispersion_relation_modification",
        "graviton_propagator_modification",
    ]
    theory_slugs = [t.slug for t in THEORIES]

    # Build matrix: rows=theories, cols=quantities
    # Value: 1 if prediction exists, 0 if not
    # (For actual values, we'd need numerical predictions)
    matrix = np.zeros((len(theory_slugs), len(quantities)))
    
    for j, qt in enumerate(quantities):
        formulas = kb.get_predictions_for_quantity(qt)
        for f in formulas:
            slug = f.get("theory_slug", "")
            if slug in theory_slugs:
                i = theory_slugs.index(slug)
                matrix[i, j] = 1.0

    fig, ax = plt.subplots(1, 1, figsize=(12, 6))
    
    im = ax.imshow(matrix, cmap="YlOrRd", aspect="auto", vmin=0, vmax=1)
    
    ax.set_xticks(range(len(quantities)))
    ax.set_xticklabels([q.replace("_", "\n") for q in quantities], fontsize=8, rotation=45, ha="right")
    ax.set_yticks(range(len(theory_slugs)))
    ax.set_yticklabels([THEORY_SHORT.get(s, s) for s in theory_slugs], fontsize=9)

    # Add text annotations
    for i in range(len(theory_slugs)):
        for j in range(len(quantities)):
            text = "✓" if matrix[i, j] > 0 else ""
            ax.text(j, i, text, ha="center", va="center", fontsize=12)

    ax.set_title("Quantum Gravity Predictions Coverage\n(which theories predict which quantities)", fontsize=12)
    plt.colorbar(im, ax=ax, label="Has prediction", shrink=0.8)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    log.info(f"Universality heatmap saved to {output_path}")


def plot_conjecture_network(
    kb: KnowledgeBase,
    output_path: str | None = None,
):
    """
    Network visualization of conjectures.
    
    Nodes = theories + conjectures
    Edges = which theories are connected by each conjecture
    Color-coded by conjecture status (verified/known/inconclusive)
    """
    if output_path is None:
        output_path = str(DATA_DIR / "conjecture_network.png")

    conjectures = kb.get_conjectures()
    if not conjectures:
        return

    G = nx.Graph()

    # Add theory nodes
    for slug, color in THEORY_COLORS.items():
        G.add_node(slug, node_type="theory", color=color)

    # Add conjecture nodes and edges
    status_colors = {
        "verified": "#00aa00",
        "known": "#0066cc",
        "inconclusive": "#999999",
        "disproved": "#cc0000",
        "proposed": "#cccccc",
    }

    for c in conjectures:
        cid = f"C{c['id']}"
        status = c["status"]
        color = status_colors.get(status, "#cccccc")
        G.add_node(cid, node_type="conjecture", color=color, label=c["title"][:30])

        theories = json.loads(c["theories_involved"]) if isinstance(c["theories_involved"], str) else c["theories_involved"]
        for t in theories:
            if t in G.nodes:
                G.add_edge(cid, t)

    if len(G.nodes) < 2:
        return

    pos = nx.spring_layout(G, k=2, seed=42)

    fig, ax = plt.subplots(1, 1, figsize=(16, 12))

    # Draw edges
    nx.draw_networkx_edges(G, pos, alpha=0.3, ax=ax)

    # Draw theory nodes
    theory_nodes = [n for n in G.nodes if G.nodes[n].get("node_type") == "theory"]
    theory_colors_list = [G.nodes[n].get("color", "#999") for n in theory_nodes]
    nx.draw_networkx_nodes(
        G, pos, nodelist=theory_nodes,
        node_color=theory_colors_list, node_size=500,
        edgecolors="black", linewidths=2, ax=ax,
    )
    labels = {n: THEORY_SHORT.get(n, n[:6]) for n in theory_nodes}
    nx.draw_networkx_labels(G, pos, labels, font_size=8, font_weight="bold", ax=ax)

    # Draw conjecture nodes
    conj_nodes = [n for n in G.nodes if G.nodes[n].get("node_type") == "conjecture"]
    conj_colors = [G.nodes[n].get("color", "#ccc") for n in conj_nodes]
    nx.draw_networkx_nodes(
        G, pos, nodelist=conj_nodes,
        node_color=conj_colors, node_size=100,
        node_shape="s", edgecolors="black", linewidths=0.5, ax=ax,
    )

    # Legend
    legend_patches = [
        mpatches.Patch(color=c, label=s.capitalize())
        for s, c in status_colors.items()
    ]
    ax.legend(handles=legend_patches, title="Conjecture Status", loc="upper left")

    ax.set_title("Conjecture Network\n(theories connected by verified/proposed conjectures)", fontsize=13)
    ax.axis("off")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    log.info(f"Conjecture network saved to {output_path}")


def generate_all_plots(kb: KnowledgeBase):
    """Generate all visualizations."""
    plot_connection_graph(kb)
    plot_universality_heatmap(kb)
    plot_conjecture_network(kb)
    log.info("All visualizations generated")
