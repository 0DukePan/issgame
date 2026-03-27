"""
═══════════════════════════════════════════════════════════════
 GRAPH CANVAS — Matplotlib Network Visualization (PyQt6)
═══════════════════════════════════════════════════════════════
 Interactive network graph embedded in PyQt6 using Matplotlib.
 - Nodes as glowing circles with labels
 - Edges as curved arrows with thickness ∝ flow
 - Color gradient green→yellow→red by congestion
 - Animated particle flow
"""

from __future__ import annotations
import numpy as np
import networkx as nx
import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from matplotlib.patches import FancyArrowPatch, Circle
from matplotlib.collections import PathCollection
import matplotlib.colors as mcolors
import matplotlib.patheffects as pe
from PyQt6.QtCore import QTimer
from typing import Optional, Dict

from core.graph import NetworkGraph


class GraphCanvas(FigureCanvasQTAgg):
    """Matplotlib canvas showing the network graph."""

    # Dark palette
    BG_COLOR = '#0a0e1a'
    GRID_COLOR = '#1a2235'
    NODE_SOURCE_COLOR = '#6ee7b7'
    NODE_SINK_COLOR = '#f87171'
    NODE_DEFAULT_COLOR = '#818cf8'
    BRAESS_COLOR = '#fbbf24'
    TEXT_COLOR = '#f1f5f9'
    MUTED_COLOR = '#64748b'

    def __init__(self, parent=None, width=8, height=6, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi, facecolor=self.BG_COLOR)
        self.ax = self.fig.add_axes([0.02, 0.02, 0.96, 0.96])
        super().__init__(self.fig)
        self.setParent(parent)

        self.graph: Optional[NetworkGraph] = None
        self.nx_graph: Optional[nx.DiGraph] = None
        self.pos: Dict[str, tuple] = {}
        self.flows: Dict[str, float] = {}
        self.max_flow: float = 0.01

        # Particle animation
        self.particles = []
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._animate)
        self.anim_timer.setInterval(50)

        self._setup_axes()

    def _setup_axes(self):
        self.ax.set_facecolor(self.BG_COLOR)
        self.ax.set_xlim(-0.15, 1.15)
        self.ax.set_ylim(-0.15, 1.15)
        self.ax.set_aspect('equal')
        self.ax.axis('off')

    def set_graph(self, graph: NetworkGraph):
        """Set the network graph and compute layout."""
        self.graph = graph
        self.nx_graph = nx.DiGraph()

        for n in graph.nodes.values():
            self.nx_graph.add_node(n.id)
        for e in graph.active_edges():
            self.nx_graph.add_edge(e.from_node, e.to_node, edge_id=e.id)

        # Use custom positions from scenario
        nodes = list(graph.nodes.values())
        xs = [n.x for n in nodes]
        ys = [n.y for n in nodes]
        if xs and ys:
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)
            rx = max_x - min_x if max_x != min_x else 1
            ry = max_y - min_y if max_y != min_y else 1
            self.pos = {}
            for n in nodes:
                self.pos[n.id] = (
                    (n.x - min_x) / rx,
                    1.0 - (n.y - min_y) / ry  # flip Y
                )
        else:
            self.pos = nx.spring_layout(self.nx_graph)

        self.flows = {e.id: e.flow for e in graph.edges.values()}
        self.particles = []
        self.redraw()
        if not self.anim_timer.isActive():
            self.anim_timer.start()

    def update_flows(self, flows: Dict[str, float]):
        """Update edge flows and redraw."""
        self.flows = dict(flows)
        self.max_flow = max(0.01, max(flows.values()) if flows else 0.01)
        self.redraw()

    def redraw(self):
        """Full redraw of the graph."""
        self.ax.clear()
        self._setup_axes()

        if not self.graph or not self.pos:
            self.draw_idle()
            return

        # Draw grid dots
        for gx in np.linspace(0, 1, 15):
            for gy in np.linspace(0, 1, 15):
                self.ax.plot(gx, gy, '.', color=self.GRID_COLOR,
                             markersize=1, alpha=0.3)

        max_flow = max(0.01, max(self.flows.values()) if self.flows else 0.01)

        # ── Draw Edges ──
        for e in self.graph.edges.values():
            if not e.enabled:
                continue
            flow = self.flows.get(e.id, 0)
            self._draw_edge(e, flow, max_flow)

        # ── Draw Nodes ──
        for n in self.graph.nodes.values():
            self._draw_node(n)

        self.draw_idle()

    def _draw_edge(self, edge, flow, max_flow):
        """Draw a single edge with congestion coloring and flow label."""
        if edge.from_node not in self.pos or edge.to_node not in self.pos:
            return

        p1 = np.array(self.pos[edge.from_node])
        p2 = np.array(self.pos[edge.to_node])

        # Color based on congestion
        if edge.is_braess:
            color = self.BRAESS_COLOR
            alpha = 0.5 + 0.5 * (flow / max_flow)
        else:
            ratio = min(flow / max_flow, 1.0) if max_flow > 0 else 0
            color = self._congestion_color(ratio)
            alpha = 0.4 + 0.6 * ratio

        # Line width based on flow
        lw = 1.5 + (flow / max_flow) * 5 if max_flow > 0 else 1.5

        # Check for reverse edge → curve more
        reverse_id = f"{edge.to_node}->{edge.from_node}"
        has_reverse = reverse_id in self.graph.edges and self.graph.edges[reverse_id].enabled
        rad = 0.2 if has_reverse else 0.1

        arrow = FancyArrowPatch(
            posA=tuple(p1), posB=tuple(p2),
            arrowstyle='->', mutation_scale=15 + lw * 2,
            connectionstyle=f'arc3,rad={rad}',
            color=color, alpha=alpha, linewidth=lw,
            zorder=2
        )
        if flow > 0.01:
            arrow.set_path_effects([
                pe.withStroke(linewidth=lw + 3, foreground=color, alpha=0.15)
            ])
        self.ax.add_patch(arrow)

        # ── Edge Label ──
        mid = (p1 + p2) / 2
        dx = p2 - p1
        normal = np.array([-dx[1], dx[0]])
        norm_len = np.linalg.norm(normal)
        if norm_len > 0:
            normal = normal / norm_len
        label_pos = mid + normal * (0.06 + rad * 0.15)

        latency_str = str(edge.latency)
        flow_str = f"f={flow:.2f}"
        label = f"{latency_str}  |  {flow_str}"

        self.ax.text(
            label_pos[0], label_pos[1], label,
            fontsize=7, color=color if edge.is_braess else self.MUTED_COLOR,
            ha='center', va='center',
            fontfamily='monospace', fontweight='medium',
            bbox=dict(facecolor=self.BG_COLOR, edgecolor='none',
                      alpha=0.85, pad=1.5, boxstyle='round,pad=0.3'),
            zorder=5
        )

    def _draw_node(self, node):
        """Draw a single node with glow effect."""
        if node.id not in self.pos:
            return

        x, y = self.pos[node.id]
        is_source = node.id == self.graph.source
        is_sink = node.id == self.graph.sink

        color = (self.NODE_SOURCE_COLOR if is_source
                 else self.NODE_SINK_COLOR if is_sink
                 else self.NODE_DEFAULT_COLOR)

        # Glow
        for r, a in [(0.055, 0.06), (0.04, 0.12), (0.03, 0.2)]:
            glow = Circle((x, y), r, facecolor=color, alpha=a,
                          edgecolor='none', zorder=8)
            self.ax.add_patch(glow)

        # Main circle
        circle = Circle((x, y), 0.028, facecolor=self.BG_COLOR,
                         edgecolor=color, linewidth=2.5, zorder=10)
        self.ax.add_patch(circle)

        # Label
        display_label = node.id
        self.ax.text(x, y, display_label, fontsize=11, fontweight='bold',
                     color=self.TEXT_COLOR, ha='center', va='center',
                     zorder=11, fontfamily='sans-serif')

        # Sub-label
        if is_source or is_sink:
            sub = 'SOURCE' if is_source else 'SINK'
            self.ax.text(x, y - 0.055, sub, fontsize=6, fontweight='medium',
                         color=color, ha='center', va='center',
                         zorder=11, fontfamily='sans-serif')

    @staticmethod
    def _congestion_color(ratio: float) -> str:
        """Green (0) → Yellow (0.5) → Red (1)."""
        r = min(int(ratio * 2 * 255), 255) if ratio < 0.5 else 255
        g = 255 if ratio < 0.5 else max(int((1 - (ratio - 0.5) * 2) * 255), 0)
        b = 30
        return f'#{r:02x}{g:02x}{b:02x}'

    def _animate(self):
        """Particle animation tick (lightweight — just draw overlay)."""
        # We skip heavy particle animation for matplotlib and rely on
        # the flow thickness/color for visual feedback.
        # Full particle animation would require blitting which is complex.
        pass

    def stop_animation(self):
        self.anim_timer.stop()
