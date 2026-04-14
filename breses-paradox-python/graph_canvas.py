"""
═══════════════════════════════════════════════════════════════
 GRAPH CANVAS — Interactive Matplotlib Network Visualization
═══════════════════════════════════════════════════════════════
 Embedded in PyQt6. Supports:
 - Congestion-based color gradients (green→yellow→red)
 - Glow effects on nodes, curved edges with labels
 - INTERACTIVE BUILDER:
   • Double-click to add nodes
   • Drag from node to node to create edges
   • Right-click node to set as source/sink or delete
   • Right-click edge to edit latency or delete
"""

from __future__ import annotations
import numpy as np
import networkx as nx
import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from matplotlib.patches import FancyArrowPatch, Circle
import matplotlib.patheffects as pe
from PyQt6.QtCore import QTimer, pyqtSignal, Qt
from PyQt6.QtWidgets import QMenu, QInputDialog, QMessageBox
from PyQt6.QtGui import QAction
from typing import Optional, Dict, Tuple

from core.graph import NetworkGraph, NetworkNode, LatencyFunction


class GraphCanvas(FigureCanvasQTAgg):
    """Matplotlib canvas with interactive network graph."""

    # Signals for the main window
    graph_modified = pyqtSignal()

    # Dark palette
    BG_COLOR = '#0a0e1a'
    GRID_COLOR = '#1a2235'
    NODE_SOURCE_COLOR = '#6ee7b7'
    NODE_SINK_COLOR = '#f87171'
    NODE_DEFAULT_COLOR = '#818cf8'
    BRAESS_COLOR = '#fbbf24'
    TOLL_COLOR = '#fb923c'
    TEXT_COLOR = '#f1f5f9'
    MUTED_COLOR = '#64748b'

    def __init__(self, parent=None, width=8, height=6, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi, facecolor=self.BG_COLOR)
        self.ax = self.fig.add_axes([0.02, 0.02, 0.96, 0.96])
        super().__init__(self.fig)
        self.setParent(parent)

        self.graph: Optional[NetworkGraph] = None
        self.pos: Dict[str, tuple] = {}
        self.flows: Dict[str, float] = {}
        self.max_flow: float = 0.01

        # Interactive state
        self.edit_mode = False
        self._drag_from_node: Optional[str] = None
        self._drag_line = None
        self._node_counter = 0

        # Connect matplotlib events
        self.mpl_connect('button_press_event', self._on_click)
        self.mpl_connect('button_release_event', self._on_release)
        self.mpl_connect('motion_notify_event', self._on_motion)

        self._setup_axes()

    def _setup_axes(self):
        self.ax.set_facecolor(self.BG_COLOR)
        self.ax.set_xlim(-0.15, 1.15)
        self.ax.set_ylim(-0.15, 1.15)
        self.ax.set_aspect('equal')
        self.ax.axis('off')

    def set_edit_mode(self, enabled: bool):
        """Toggle interactive builder mode."""
        self.edit_mode = enabled

    def set_graph(self, graph: NetworkGraph):
        """Set the network graph and compute layout."""
        self.graph = graph
        self._compute_positions()
        self.flows = {e.id: e.flow for e in graph.edges.values()}
        self._node_counter = len(graph.nodes)
        self.redraw()

    def _compute_positions(self):
        """Compute normalized node positions for rendering."""
        if not self.graph:
            return
        nodes = list(self.graph.nodes.values())
        if not nodes:
            self.pos = {}
            return
        xs = [n.x for n in nodes]
        ys = [n.y for n in nodes]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        rx = max_x - min_x if max_x != min_x else 1
        ry = max_y - min_y if max_y != min_y else 1
        self.pos = {}
        for n in nodes:
            self.pos[n.id] = (
                (n.x - min_x) / rx,
                1.0 - (n.y - min_y) / ry
            )

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

        # Grid dots
        for gx in np.linspace(0, 1, 15):
            for gy in np.linspace(0, 1, 15):
                self.ax.plot(gx, gy, '.', color=self.GRID_COLOR,
                             markersize=1, alpha=0.3)

        max_flow = max(0.01, max(self.flows.values()) if self.flows else 0.01)

        # Draw edges
        for e in self.graph.edges.values():
            if not e.enabled:
                continue
            flow = self.flows.get(e.id, 0)
            self._draw_edge(e, flow, max_flow)

        # Draw nodes
        for n in self.graph.nodes.values():
            self._draw_node(n)

        # Edit mode indicator
        if self.edit_mode:
            self.ax.text(0.5, 1.08, '🛠 EDIT MODE — Double-click: Add Node  |  Drag: Connect  |  Right-click: Options',
                         fontsize=7, color='#818cf8', ha='center', va='center',
                         transform=self.ax.transAxes,
                         bbox=dict(facecolor='#1a2235', edgecolor='#818cf8',
                                   alpha=0.9, pad=4, boxstyle='round,pad=0.5'))

        self.draw_idle()

    def _draw_edge(self, edge, flow, max_flow):
        if edge.from_node not in self.pos or edge.to_node not in self.pos:
            return
        p1 = np.array(self.pos[edge.from_node])
        p2 = np.array(self.pos[edge.to_node])

        if edge.is_braess:
            color = self.BRAESS_COLOR
        elif edge.toll > 0:
            color = self.TOLL_COLOR
        else:
            ratio = min(flow / max_flow, 1.0) if max_flow > 0 else 0
            color = self._congestion_color(ratio)

        alpha = 0.4 + 0.6 * min(flow / max_flow, 1.0) if max_flow > 0 else 0.5
        lw = 1.5 + (flow / max_flow) * 5 if max_flow > 0 else 1.5

        reverse_id = f"{edge.to_node}->{edge.from_node}"
        has_reverse = reverse_id in self.graph.edges and self.graph.edges[reverse_id].enabled
        rad = 0.2 if has_reverse else 0.1

        arrow = FancyArrowPatch(
            posA=tuple(p1), posB=tuple(p2),
            arrowstyle='->', mutation_scale=15 + lw * 2,
            connectionstyle=f'arc3,rad={rad}',
            color=color, alpha=alpha, linewidth=lw, zorder=2
        )
        if flow > 0.01:
            arrow.set_path_effects([
                pe.withStroke(linewidth=lw + 3, foreground=color, alpha=0.15)
            ])
        self.ax.add_patch(arrow)

        # Edge label
        mid = (p1 + p2) / 2
        dx = p2 - p1
        normal = np.array([-dx[1], dx[0]])
        norm_len = np.linalg.norm(normal)
        if norm_len > 0:
            normal = normal / norm_len
        label_pos = mid + normal * (0.06 + rad * 0.15)

        latency_str = str(edge.latency)
        flow_str = f"f={flow:.2f}"
        toll_str = f" τ={edge.toll:.2f}" if edge.toll > 0 else ""
        label = f"{latency_str}  |  {flow_str}{toll_str}"

        lbl_color = self.TOLL_COLOR if edge.toll > 0 else (
            self.BRAESS_COLOR if edge.is_braess else self.MUTED_COLOR)
        self.ax.text(
            label_pos[0], label_pos[1], label,
            fontsize=7, color=lbl_color, ha='center', va='center',
            fontfamily='monospace', fontweight='medium',
            bbox=dict(facecolor=self.BG_COLOR, edgecolor='none',
                      alpha=0.85, pad=1.5, boxstyle='round,pad=0.3'),
            zorder=5
        )

    def _draw_node(self, node):
        if node.id not in self.pos:
            return
        x, y = self.pos[node.id]
        is_source = node.id == self.graph.source
        is_sink = node.id == self.graph.sink
        color = (self.NODE_SOURCE_COLOR if is_source
                 else self.NODE_SINK_COLOR if is_sink
                 else self.NODE_DEFAULT_COLOR)

        for r, a in [(0.055, 0.06), (0.04, 0.12), (0.03, 0.2)]:
            glow = Circle((x, y), r, facecolor=color, alpha=a,
                          edgecolor='none', zorder=8)
            self.ax.add_patch(glow)

        circle = Circle((x, y), 0.028, facecolor=self.BG_COLOR,
                         edgecolor=color, linewidth=2.5, zorder=10)
        self.ax.add_patch(circle)

        self.ax.text(x, y, node.id, fontsize=11, fontweight='bold',
                     color=self.TEXT_COLOR, ha='center', va='center',
                     zorder=11, fontfamily='sans-serif')

        if is_source or is_sink:
            sub = 'SOURCE' if is_source else 'SINK'
            self.ax.text(x, y - 0.055, sub, fontsize=6, fontweight='medium',
                         color=color, ha='center', va='center',
                         zorder=11, fontfamily='sans-serif')

    # ═══════════════════════════════════════════════
    # INTERACTIVE BUILDER
    # ═══════════════════════════════════════════════

    def _find_node_at(self, mx, my, radius=0.04) -> Optional[str]:
        """Find the node closest to matplotlib coordinates (mx, my)."""
        for nid, (nx, ny) in self.pos.items():
            if (mx - nx)**2 + (my - ny)**2 < radius**2:
                return nid
        return None

    def _find_edge_at(self, mx, my, radius=0.03) -> Optional[str]:
        """Find the edge whose midpoint is closest to (mx, my)."""
        for e in self.graph.edges.values():
            if not e.enabled:
                continue
            if e.from_node not in self.pos or e.to_node not in self.pos:
                continue
            p1 = np.array(self.pos[e.from_node])
            p2 = np.array(self.pos[e.to_node])
            mid = (p1 + p2) / 2
            if (mx - mid[0])**2 + (my - mid[1])**2 < radius**2:
                return e.id
        return None

    def _on_click(self, event):
        """Handle mouse clicks on the canvas."""
        if not self.edit_mode or not self.graph or event.inaxes != self.ax:
            return

        mx, my = event.xdata, event.ydata
        if mx is None or my is None:
            return

        # Right-click → context menu
        if event.button == 3:
            self._show_context_menu(mx, my, event)
            return

        # Left click
        if event.button == 1:
            node = self._find_node_at(mx, my)
            if event.dblclick:
                # Double-click on empty space → add node
                if node is None:
                    self._add_node_at(mx, my)
            elif node is not None:
                # Start drag from existing node
                self._drag_from_node = node

    def _on_motion(self, event):
        """Handle mouse drag for edge creation."""
        if not self.edit_mode or self._drag_from_node is None:
            return
        if event.inaxes != self.ax or event.xdata is None:
            return
        # We could draw a temp line here, but for simplicity we just wait for release.

    def _on_release(self, event):
        """Handle mouse release — create edge if dragged to another node."""
        if not self.edit_mode or self._drag_from_node is None or not self.graph:
            self._drag_from_node = None
            return

        if event.inaxes != self.ax or event.xdata is None:
            self._drag_from_node = None
            return

        target = self._find_node_at(event.xdata, event.ydata)
        if target is not None and target != self._drag_from_node:
            edge_id = f"{self._drag_from_node}->{target}"
            if edge_id not in self.graph.edges:
                self.graph.add_edge(
                    self._drag_from_node, target,
                    LatencyFunction('linear', a=1, b=0),
                    label='L(x) = x'
                )
                self.redraw()
                self.graph_modified.emit()

        self._drag_from_node = None

    def _add_node_at(self, mx, my):
        """Add a new node at display coordinates."""
        self._node_counter += 1
        name = chr(64 + self._node_counter) if self._node_counter <= 26 \
               else f"N{self._node_counter}"

        # Convert display coords back to graph coords
        nodes = list(self.graph.nodes.values())
        if nodes:
            xs = [n.x for n in nodes]
            ys = [n.y for n in nodes]
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)
            rx = max_x - min_x if max_x != min_x else 1
            ry = max_y - min_y if max_y != min_y else 1
            gx = mx * rx + min_x
            gy = (1 - my) * ry + min_y
        else:
            gx, gy = mx * 800, my * 600

        self.graph.add_node(name, gx, gy, name)
        if self.graph.source is None:
            self.graph.source = name
        elif self.graph.sink is None:
            self.graph.sink = name

        self._compute_positions()
        self.redraw()
        self.graph_modified.emit()

    def _show_context_menu(self, mx, my, event):
        """Show context menu on right-click."""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background: #1a2235; color: #f1f5f9; border: 1px solid #333; border-radius: 6px; padding: 4px; }
            QMenu::item { padding: 6px 20px; }
            QMenu::item:selected { background: #818cf8; border-radius: 4px; }
        """)

        node = self._find_node_at(mx, my)
        edge_id = self._find_edge_at(mx, my) if node is None else None

        if node:
            set_src = menu.addAction("🟢 Set as Source")
            set_sink = menu.addAction("🔴 Set as Sink")
            menu.addSeparator()
            delete_node = menu.addAction("🗑 Delete Node")

            # Map from QPoint on the widget
            pos = self.mapToGlobal(self.geometry().topLeft())
            from PyQt6.QtCore import QPoint
            action = menu.exec(self.mapToGlobal(QPoint(int(event.x), int(self.height() - event.y))))

            if action == set_src:
                self.graph.source = node
                self.redraw()
                self.graph_modified.emit()
            elif action == set_sink:
                self.graph.sink = node
                self.redraw()
                self.graph_modified.emit()
            elif action == delete_node:
                self.graph.remove_node(node)
                self._compute_positions()
                self.redraw()
                self.graph_modified.emit()

        elif edge_id:
            edge = self.graph.edges.get(edge_id)
            if not edge:
                return
            edit_lat = menu.addAction(f"📝 Edit Latency ({edge.latency})")
            toggle_braess = menu.addAction("⚡ Toggle Braess")
            menu.addSeparator()
            delete_edge = menu.addAction("🗑 Delete Edge")

            from PyQt6.QtCore import QPoint
            action = menu.exec(self.mapToGlobal(QPoint(int(event.x), int(self.height() - event.y))))

            if action == edit_lat:
                self._edit_edge_latency(edge)
            elif action == toggle_braess:
                edge.is_braess = not edge.is_braess
                self.redraw()
                self.graph_modified.emit()
            elif action == delete_edge:
                self.graph.remove_edge(edge_id)
                self.redraw()
                self.graph_modified.emit()

    def _edit_edge_latency(self, edge):
        """Pop up dialog to edit edge latency function."""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, \
            QComboBox, QDoubleSpinBox, QPushButton, QFormLayout

        dlg = QDialog(self)
        dlg.setWindowTitle(f"Edit Edge: {edge.from_node} → {edge.to_node}")
        dlg.setStyleSheet("""
            QDialog { background: #1a2235; color: #f1f5f9; }
            QLabel { color: #f1f5f9; }
            QComboBox { background: #0a0e1a; color: #f1f5f9; border: 1px solid #333; border-radius: 4px; padding: 4px; }
            QComboBox QAbstractItemView { background: #1a2235; color: #f1f5f9; }
            QDoubleSpinBox { background: #0a0e1a; color: #f1f5f9; border: 1px solid #333; border-radius: 4px; padding: 4px; }
            QPushButton { background: #818cf8; color: white; border-radius: 6px; padding: 8px 16px; font-weight: 600; }
            QPushButton:hover { background: #6366f1; }
        """)
        layout = QVBoxLayout(dlg)

        form = QFormLayout()
        combo_type = QComboBox()
        combo_type.addItems(['linear', 'polynomial', 'log', 'bpr'])
        combo_type.setCurrentText(edge.latency.type)
        form.addRow("Type:", combo_type)

        spin_a = QDoubleSpinBox()
        spin_a.setRange(-100, 100)
        spin_a.setSingleStep(0.1)
        spin_a.setValue(edge.latency.a)
        form.addRow("a:", spin_a)

        spin_b = QDoubleSpinBox()
        spin_b.setRange(-100, 100)
        spin_b.setSingleStep(0.1)
        spin_b.setValue(edge.latency.b)
        form.addRow("b:", spin_b)

        spin_c = QDoubleSpinBox()
        spin_c.setRange(-100, 100)
        spin_c.setSingleStep(0.1)
        spin_c.setValue(edge.latency.c)
        form.addRow("c:", spin_c)

        # BPR params
        lbl_bpr = QLabel("── BPR Parameters ──")
        lbl_bpr.setStyleSheet("color: #94a3b8; font-size: 10px;")
        form.addRow(lbl_bpr)

        spin_t0 = QDoubleSpinBox()
        spin_t0.setRange(0.01, 100)
        spin_t0.setSingleStep(0.1)
        spin_t0.setValue(edge.latency.t0)
        form.addRow("t₀ (free-flow):", spin_t0)

        spin_cap = QDoubleSpinBox()
        spin_cap.setRange(0.01, 100)
        spin_cap.setSingleStep(0.1)
        spin_cap.setValue(edge.latency.capacity)
        form.addRow("Capacity:", spin_cap)

        layout.addLayout(form)

        btn = QPushButton("Apply")
        btn.clicked.connect(dlg.accept)
        layout.addWidget(btn)

        if dlg.exec():
            edge.latency = LatencyFunction(
                type=combo_type.currentText(),
                a=spin_a.value(), b=spin_b.value(), c=spin_c.value(),
                t0=spin_t0.value(), capacity=spin_cap.value()
            )
            self.redraw()
            self.graph_modified.emit()

    @staticmethod
    def _congestion_color(ratio: float) -> str:
        r = min(int(ratio * 2 * 255), 255) if ratio < 0.5 else 255
        g = 255 if ratio < 0.5 else max(int((1 - (ratio - 0.5) * 2) * 255), 0)
        b = 30
        return f'#{r:02x}{g:02x}{b:02x}'

    def stop_animation(self):
        pass
