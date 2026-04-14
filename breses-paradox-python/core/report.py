"""
═══════════════════════════════════════════════════════════════
 PDF REPORT GENERATOR — Academic-Quality Technical Report
═══════════════════════════════════════════════════════════════
 Generates a formal 2-page PDF report from the current simulation
 using matplotlib for figures and reportlab-style layout.
"""

from __future__ import annotations
import io
import os
import datetime
from typing import Optional
import numpy as np

import matplotlib
matplotlib.use('Agg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg

from .graph import NetworkGraph
from .solver import ComparisonResult


def generate_pdf_report(graph: NetworkGraph, result: ComparisonResult,
                        output_path: str, title: str = "Braess's Paradox — Simulation Report"):
    """
    Generate a multi-page academic PDF report using Matplotlib's PdfPages.

    The report includes:
    - Title page with summary metrics
    - Network diagram with flows
    - Flow comparison chart
    - Convergence analysis
    - Mathematical formulation
    - Edge-by-edge data table
    """
    from matplotlib.backends.backend_pdf import PdfPages

    with PdfPages(output_path) as pdf:
        # ═══ PAGE 1: Title & Summary ═══
        fig = Figure(figsize=(8.5, 11), dpi=150, facecolor='white')
        ax = fig.add_axes([0, 0, 1, 1])
        ax.axis('off')

        # Title
        ax.text(0.5, 0.92, title, fontsize=18, fontweight='bold',
                ha='center', va='top', fontfamily='serif')
        ax.text(0.5, 0.88, f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}",
                fontsize=9, ha='center', va='top', color='#666')

        # Horizontal rule
        ax.axhline(y=0.86, xmin=0.1, xmax=0.9, color='#333', linewidth=0.8)

        # Summary box
        y = 0.82
        ax.text(0.1, y, "1. Simulation Summary", fontsize=13, fontweight='bold',
                fontfamily='serif')
        y -= 0.04

        summary_data = [
            ("Network Nodes", str(len(graph.nodes))),
            ("Network Edges", str(len(graph.active_edges()))),
            ("Traffic Demand", f"{graph.demand:.2f}"),
            ("Nash Equilibrium Cost", f"{result.nash.total_cost:.4f}"),
            ("System Optimum Cost", f"{result.optimum.total_cost:.4f}"),
            ("Price of Anarchy (PoA)", f"{result.price_of_anarchy:.4f}"),
            ("Efficiency Loss", f"{result.efficiency_loss:.2f}%"),
            ("Nash Avg. Latency", f"{result.nash.avg_latency:.4f}"),
            ("Optimal Avg. Latency", f"{result.optimum.avg_latency:.4f}"),
        ]
        for label, value in summary_data:
            ax.text(0.15, y, f"• {label}:", fontsize=10, fontfamily='serif')
            ax.text(0.65, y, value, fontsize=10, fontweight='bold',
                    fontfamily='monospace')
            y -= 0.028

        # Mathematical formulation
        y -= 0.03
        ax.text(0.1, y, "2. Mathematical Formulation", fontsize=13,
                fontweight='bold', fontfamily='serif')
        y -= 0.04

        formulas = [
            "Wardrop User Equilibrium (Nash):",
            "    min  Σₑ ∫₀ˣₑ lₑ(t) dt    (Beckmann Objective)",
            "",
            "System Optimum:",
            "    min  Σₑ xₑ · lₑ(xₑ)       (Total System Cost)",
            "",
            "Marginal Cost (linear lₑ(x) = aₑx + bₑ):",
            "    MCₑ(x) = 2aₑx + bₑ",
            "",
            "Price of Anarchy:",
            f"    PoA = C(Nash) / C(Opt) = {result.nash.total_cost:.4f} / {result.optimum.total_cost:.4f} = {result.price_of_anarchy:.4f}",
        ]

        for line in formulas:
            if line.startswith("    "):
                ax.text(0.18, y, line, fontsize=9, fontfamily='monospace',
                        color='#333')
            elif line:
                ax.text(0.15, y, line, fontsize=10, fontfamily='serif',
                        fontweight='bold')
            y -= 0.024

        # Edge table
        y -= 0.03
        ax.text(0.1, y, "3. Edge Flow Data", fontsize=13, fontweight='bold',
                fontfamily='serif')
        y -= 0.035

        # Table header
        cols = ['Edge', 'L(x)', 'Nash Flow', 'Opt Flow', 'Nash Cost', 'Opt Cost']
        col_x = [0.12, 0.26, 0.42, 0.55, 0.68, 0.82]
        for i, col in enumerate(cols):
            ax.text(col_x[i], y, col, fontsize=8, fontweight='bold',
                    fontfamily='monospace')
        y -= 0.005
        ax.axhline(y=y, xmin=0.1, xmax=0.95, color='#999', linewidth=0.5)
        y -= 0.02

        for e in graph.edges.values():
            if not e.enabled:
                continue
            nf = result.nash.flows.get(e.id, 0)
            of_ = result.optimum.flows.get(e.id, 0)
            row = [
                f"{e.from_node}→{e.to_node}",
                str(e.latency),
                f"{nf:.4f}",
                f"{of_:.4f}",
                f"{e.latency.cost(nf):.4f}",
                f"{e.latency.cost(of_):.4f}",
            ]
            for i, val in enumerate(row):
                ax.text(col_x[i], y, val, fontsize=7.5, fontfamily='monospace')
            y -= 0.022
            if y < 0.05:
                break

        canvas = FigureCanvasAgg(fig)
        pdf.savefig(fig)

        # ═══ PAGE 2: Charts ═══
        fig2 = Figure(figsize=(8.5, 11), dpi=150, facecolor='white')

        # Flow comparison bar chart
        ax1 = fig2.add_axes([0.1, 0.55, 0.8, 0.35])
        edges = [e for e in graph.edges.values() if e.enabled]
        labels = [f"{e.from_node}→{e.to_node}" for e in edges]
        nash_vals = [result.nash.flows.get(e.id, 0) for e in edges]
        opt_vals = [result.optimum.flows.get(e.id, 0) for e in edges]

        x_pos = np.arange(len(edges))
        w = 0.35
        ax1.bar(x_pos - w/2, nash_vals, w, color='#e74c3c', alpha=0.8,
                label='Nash Equilibrium')
        ax1.bar(x_pos + w/2, opt_vals, w, color='#2ecc71', alpha=0.8,
                label='System Optimum')
        ax1.set_xticks(x_pos)
        ax1.set_xticklabels(labels, fontsize=8, rotation=30, ha='right')
        ax1.set_ylabel('Flow', fontsize=10)
        ax1.set_title('Edge Flow Comparison: Nash vs System Optimum',
                       fontsize=12, fontweight='bold', fontfamily='serif')
        ax1.legend(fontsize=9)
        ax1.grid(True, alpha=0.3)

        # Convergence chart
        ax2 = fig2.add_axes([0.1, 0.12, 0.8, 0.3])
        if result.nash.iterations:
            iters = [it['iteration'] for it in result.nash.iterations]
            gaps = [max(it['gap'], 1e-15) for it in result.nash.iterations]
            ax2.semilogy(iters, gaps, color='#3498db', linewidth=2,
                         label='Duality Gap')
            ax2.fill_between(iters, gaps, alpha=0.1, color='#3498db')
        ax2.set_xlabel('Iteration', fontsize=10)
        ax2.set_ylabel('Convergence Gap (log)', fontsize=10)
        ax2.set_title('Frank-Wolfe Convergence',
                       fontsize=12, fontweight='bold', fontfamily='serif')
        ax2.grid(True, alpha=0.3)
        ax2.legend(fontsize=9)

        canvas2 = FigureCanvasAgg(fig2)
        pdf.savefig(fig2)

    return output_path
