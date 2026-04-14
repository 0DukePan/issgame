"""
═══════════════════════════════════════════════════════════════
 MAIN WINDOW — PyQt6 Dashboard for Braess's Paradox
═══════════════════════════════════════════════════════════════
"""
import sys, json, csv, io, os
import numpy as np
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QLabel, QComboBox, QSlider, QCheckBox, QPushButton,
    QGroupBox, QFormLayout, QDoubleSpinBox, QScrollArea, QFileDialog,
    QMessageBox, QProgressBar, QTextEdit, QFrame
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor, QPalette, QIcon

import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from core.graph import NetworkGraph, LatencyFunction
from core.solver import solve_nash, solve_system_optimum, compare, sensitivity_analysis, apply_pigouvian_tolls
from core.scenarios import SCENARIOS
from core.report import generate_pdf_report
from graph_canvas import GraphCanvas

# ───────────────── Dark Stylesheet ─────────────────
DARK_STYLE = """
QMainWindow, QWidget { background-color: #0a0e1a; color: #f1f5f9; }
QGroupBox {
    background-color: #1a2235; border: 1px solid rgba(148,163,184,0.12);
    border-radius: 10px; margin-top: 14px; padding: 16px 12px 12px 12px;
    font-weight: 600; font-size: 12px; color: #94a3b8;
}
QGroupBox::title { subcontrol-origin: margin; left: 14px; padding: 0 6px; color: #94a3b8; }
QComboBox {
    background: #111827; border: 1px solid rgba(148,163,184,0.15);
    border-radius: 6px; padding: 6px 10px; color: #f1f5f9; min-height: 28px;
}
QComboBox:hover { border-color: #818cf8; }
QComboBox::drop-down { border: none; width: 24px; }
QComboBox QAbstractItemView { background: #1a2235; color: #f1f5f9; selection-background-color: #818cf8; }
QSlider::groove:horizontal { height: 6px; background: #111827; border-radius: 3px; }
QSlider::handle:horizontal { width: 18px; height: 18px; margin: -6px 0; background: #818cf8; border-radius: 9px; }
QSlider::handle:horizontal:hover { background: #6366f1; }
QPushButton {
    background: #1a2235; border: 1px solid rgba(148,163,184,0.15);
    border-radius: 8px; padding: 8px 16px; color: #f1f5f9;
    font-weight: 500; font-size: 12px;
}
QPushButton:hover { border-color: #818cf8; background: #1e2a42; }
QPushButton:pressed { background: #111827; }
QPushButton#accentBtn {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #818cf8,stop:1 #6366f1);
    border: 1px solid #818cf8; color: white;
}
QPushButton#accentBtn:hover { background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #6366f1,stop:1 #4f46e5); }
QPushButton#braessBtn {
    background: rgba(251,191,36,0.15); border: 1px solid rgba(251,191,36,0.3); color: #fbbf24;
}
QPushButton#warnBtn { background: rgba(248,113,113,0.15); border: 1px solid rgba(248,113,113,0.3); color: #f87171; }
QLabel { color: #f1f5f9; }
QLabel#muted { color: #64748b; font-size: 11px; }
QLabel#metricNash { color: #f87171; font-family: monospace; font-size: 18px; font-weight: 700; }
QLabel#metricOpt { color: #34d399; font-family: monospace; font-size: 18px; font-weight: 700; }
QLabel#poa { color: #fbbf24; font-family: monospace; font-size: 22px; font-weight: 800; }
QLabel#sectionTitle { color: #94a3b8; font-weight: 600; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; }
QDoubleSpinBox {
    background: #0a0e1a; border: 1px solid rgba(148,163,184,0.15);
    border-radius: 4px; padding: 3px 6px; color: #f1f5f9; font-family: monospace;
}
QDoubleSpinBox:focus { border-color: #818cf8; }
QProgressBar {
    background: #111827; border: 1px solid rgba(148,163,184,0.1); border-radius: 10px;
    height: 22px; text-align: center; color: #f1f5f9; font-size: 11px; font-weight: 600;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #34d399,stop:0.5 #fbbf24,stop:1 #f87171);
    border-radius: 10px;
}
QScrollArea { border: none; background: transparent; }
QCheckBox { color: #f1f5f9; spacing: 8px; }
QCheckBox::indicator { width: 18px; height: 18px; border-radius: 4px; border: 1px solid #64748b; background: #111827; }
QCheckBox::indicator:checked { background: #818cf8; border-color: #818cf8; }
QTextEdit { background: #111827; border: 1px solid rgba(148,163,184,0.1); border-radius: 8px; color: #94a3b8; font-size: 11px; padding: 8px; }
QFrame#separator { background: rgba(148,163,184,0.1); max-height: 1px; }
"""


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Braess's Paradox — Selfish Routing Simulator")
        self.setMinimumSize(960, 600)
        self.resize(1440, 860)
        self.setStyleSheet(DARK_STYLE)

        self.graph: NetworkGraph = None
        self.result = None
        self.explain_mode = False
        self.tolls_active = False

        self._build_ui()
        self._bind_events()
        self._load_scenario('braess')

    # ═══════════════════════════════════════════════
    # UI CONSTRUCTION
    # ═══════════════════════════════════════════════
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

        # ── LEFT SIDEBAR ──
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setMinimumWidth(240)
        left_scroll.setMaximumWidth(320)
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(10)

        # Header
        hdr = QLabel("⚡ Braess's Paradox")
        hdr.setStyleSheet("font-size:18px; font-weight:800; color:#818cf8; padding:4px 0;")
        left_layout.addWidget(hdr)
        sub = QLabel("Selfish Routing & Network Optimization")
        sub.setObjectName("muted")
        left_layout.addWidget(sub)

        # Buttons row
        btn_row = QHBoxLayout()
        self.btn_explain = QPushButton("📖 Explain")
        self.btn_demo = QPushButton("▶ Guided Demo")
        self.btn_demo.setObjectName("accentBtn")
        btn_row.addWidget(self.btn_explain)
        btn_row.addWidget(self.btn_demo)
        left_layout.addLayout(btn_row)

        # Edit Mode + Tolls row
        btn_row2 = QHBoxLayout()
        self.btn_edit_mode = QPushButton("🛠 Edit Mode")
        self.btn_tolls = QPushButton("💰 Apply Tolls")
        self.btn_tolls.setObjectName("braessBtn")
        btn_row2.addWidget(self.btn_edit_mode)
        btn_row2.addWidget(self.btn_tolls)
        left_layout.addLayout(btn_row2)

        # Scenario
        grp_scenario = QGroupBox("📡 Network Scenario")
        sl = QVBoxLayout(grp_scenario)
        self.combo_scenario = QComboBox()
        for key, s in SCENARIOS.items():
            self.combo_scenario.addItem(s['name'], key)
        sl.addWidget(self.combo_scenario)
        self.lbl_scenario_desc = QLabel()
        self.lbl_scenario_desc.setObjectName("muted")
        self.lbl_scenario_desc.setWordWrap(True)
        sl.addWidget(self.lbl_scenario_desc)
        left_layout.addWidget(grp_scenario)

        # Demand
        grp_demand = QGroupBox("🚗 Traffic Demand")
        dl = QVBoxLayout(grp_demand)
        dl.setSpacing(4)
        slider_row = QHBoxLayout()
        self.slider_demand = QSlider(Qt.Orientation.Horizontal)
        self.slider_demand.setRange(1, 30)
        self.slider_demand.setValue(10)
        self.slider_demand.setTickInterval(5)
        slider_row.addWidget(self.slider_demand)
        self.lbl_demand = QLabel("1.0")
        self.lbl_demand.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.lbl_demand.setStyleSheet(
            "font-family:monospace; color:#818cf8; font-weight:700;"
            "font-size:13px; min-width:38px; max-width:38px;"
        )
        slider_row.addWidget(self.lbl_demand)
        dl.addLayout(slider_row)
        lbl_range = QLabel("Range: 0.1 — 3.0 units")
        lbl_range.setObjectName("muted")
        dl.addWidget(lbl_range)
        left_layout.addWidget(grp_demand)

        # Braess Toggle
        self.grp_braess = QGroupBox("⚡ Braess Edge (C → D)")
        bl = QVBoxLayout(self.grp_braess)
        bl.setSpacing(6)
        # Inline row: checkbox + status badge
        braess_top = QHBoxLayout()
        self.chk_braess = QCheckBox("Enable shortcut edge")
        self.chk_braess.setChecked(True)
        braess_top.addWidget(self.chk_braess)
        braess_top.addStretch()
        self.lbl_braess_status = QLabel("ON")
        self.lbl_braess_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_braess_status.setFixedWidth(36)
        self.lbl_braess_status.setStyleSheet(
            "color:#0a0e1a; background:#fbbf24; font-weight:700;"
            "font-size:10px; border-radius:4px; padding:2px 4px;"
        )
        braess_top.addWidget(self.lbl_braess_status)
        bl.addLayout(braess_top)
        # Status description line
        self.lbl_braess_explain = QLabel(
            "⚠️ Braess's Paradox: Adding this zero-cost shortcut INCREASES total "
            "network latency because every selfish user rushes to use it."
        )
        self.lbl_braess_explain.setWordWrap(True)
        self.lbl_braess_explain.setObjectName("muted")
        self.lbl_braess_explain.setVisible(False)
        bl.addWidget(self.lbl_braess_explain)
        self.grp_braess.setStyleSheet(
            self.grp_braess.styleSheet() +
            "QGroupBox{border-color:rgba(251,191,36,0.35);}"
        )
        left_layout.addWidget(self.grp_braess)

        # Edge Parameters — COLLAPSIBLE (this was causing the overload)
        self.btn_toggle_edges = QPushButton("🔧 Edge Parameters ▸")
        self.btn_toggle_edges.setStyleSheet(
            "QPushButton{text-align:left; padding:8px 14px; font-size:12px; font-weight:600;"
            "color:#94a3b8; background:#1a2235; border:1px solid rgba(148,163,184,0.12); border-radius:10px;}"
            "QPushButton:hover{border-color:#818cf8;}"
        )
        left_layout.addWidget(self.btn_toggle_edges)
        self.grp_edges = QFrame()
        self.grp_edges.setStyleSheet(
            "QFrame{background:#1a2235; border:1px solid rgba(148,163,184,0.12);"
            "border-radius:10px; padding:8px; margin-top:2px;}"
        )
        self.edge_layout = QFormLayout(self.grp_edges)
        self.edge_layout.setContentsMargins(8, 8, 8, 8)
        self.edge_layout.setSpacing(6)
        self.grp_edges.setVisible(False)  # COLLAPSED by default
        left_layout.addWidget(self.grp_edges)
        self.btn_toggle_edges.clicked.connect(self._toggle_edge_panel)

        # Save/Load/Export
        grp_io = QGroupBox("💾 Save & Export")
        io_layout = QVBoxLayout(grp_io)
        row1 = QHBoxLayout()
        self.btn_save = QPushButton("Save JSON")
        self.btn_load = QPushButton("Load JSON")
        row1.addWidget(self.btn_save)
        row1.addWidget(self.btn_load)
        io_layout.addLayout(row1)
        row2 = QHBoxLayout()
        self.btn_csv = QPushButton("Export CSV")
        self.btn_sensitivity = QPushButton("📈 Sensitivity")
        self.btn_sensitivity.setObjectName("accentBtn")
        row2.addWidget(self.btn_csv)
        row2.addWidget(self.btn_sensitivity)
        io_layout.addLayout(row2)
        row3 = QHBoxLayout()
        self.btn_pdf = QPushButton("📄 PDF Report")
        self.btn_pdf.setObjectName("accentBtn")
        row3.addWidget(self.btn_pdf)
        io_layout.addLayout(row3)
        left_layout.addWidget(grp_io)

        left_layout.addStretch()
        left_scroll.setWidget(left_widget)
        splitter.addWidget(left_scroll)

        # ── CENTER — GRAPH CANVAS ──
        self.graph_canvas = GraphCanvas()
        splitter.addWidget(self.graph_canvas)

        # ── RIGHT PANEL — METRICS ──
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setMinimumWidth(240)
        right_scroll.setMaximumWidth(340)
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(8, 8, 8, 8)
        right_layout.setSpacing(4)

        # Nash vs Opt cards — side by side
        cards = QHBoxLayout()
        nash_card = QFrame()
        nash_card.setStyleSheet("QFrame{background:rgba(248,113,113,0.08);border:1px solid rgba(248,113,113,0.2);border-radius:10px;padding:10px;}")
        nc_l = QVBoxLayout(nash_card)
        nc_l.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nc_l.addWidget(self._make_label("NASH EQUILIBRIUM", "sectionTitle", align=Qt.AlignmentFlag.AlignCenter))
        self.lbl_nash_cost = QLabel("—")
        self.lbl_nash_cost.setObjectName("metricNash")
        self.lbl_nash_cost.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nc_l.addWidget(self.lbl_nash_cost)
        nc_l.addWidget(self._make_label("Total System Cost", "muted", align=Qt.AlignmentFlag.AlignCenter))
        cards.addWidget(nash_card)

        opt_card = QFrame()
        opt_card.setStyleSheet("QFrame{background:rgba(52,211,153,0.08);border:1px solid rgba(52,211,153,0.2);border-radius:10px;padding:10px;}")
        oc_l = QVBoxLayout(opt_card)
        oc_l.setAlignment(Qt.AlignmentFlag.AlignCenter)
        oc_l.addWidget(self._make_label("SYSTEM OPTIMUM", "sectionTitle", align=Qt.AlignmentFlag.AlignCenter))
        self.lbl_opt_cost = QLabel("—")
        self.lbl_opt_cost.setObjectName("metricOpt")
        self.lbl_opt_cost.setAlignment(Qt.AlignmentFlag.AlignCenter)
        oc_l.addWidget(self.lbl_opt_cost)
        oc_l.addWidget(self._make_label("Total System Cost", "muted", align=Qt.AlignmentFlag.AlignCenter))
        cards.addWidget(opt_card)
        right_layout.addLayout(cards)

        # Price of Anarchy
        grp_poa = QGroupBox("🔥 Price of Anarchy")
        poa_l = QVBoxLayout(grp_poa)
        self.lbl_poa = QLabel("1.000")
        self.lbl_poa.setObjectName("poa")
        self.lbl_poa.setAlignment(Qt.AlignmentFlag.AlignCenter)
        poa_l.addWidget(self.lbl_poa)
        poa_l.addWidget(self._make_label("PoA = Nash Cost / Optimal Cost", "muted", align=Qt.AlignmentFlag.AlignCenter))
        self.lbl_poa_explain = QLabel(
            "📊 Price of Anarchy measures how much worse selfish routing is vs optimal. "
            "PoA = 1 means no loss; PoA > 1 means selfishness hurts everyone."
        )
        self.lbl_poa_explain.setWordWrap(True)
        self.lbl_poa_explain.setObjectName("muted")
        self.lbl_poa_explain.setVisible(False)
        poa_l.addWidget(self.lbl_poa_explain)
        right_layout.addWidget(grp_poa)

        # Efficiency Loss bar
        grp_eff = QGroupBox("📉 Efficiency Loss")
        eff_l = QVBoxLayout(grp_eff)
        self.efficiency_bar = QProgressBar()
        self.efficiency_bar.setRange(0, 100)
        self.efficiency_bar.setValue(0)
        self.efficiency_bar.setFormat("%p% wasted by selfishness")
        eff_l.addWidget(self.efficiency_bar)
        right_layout.addWidget(grp_eff)

        # Average Latency
        grp_lat = QGroupBox("⏱ Average Latency")
        lat_l = QHBoxLayout(grp_lat)
        self.lbl_lat_nash = self._make_metric_label("—", "#f87171")
        self.lbl_lat_opt = self._make_metric_label("—", "#34d399")
        lnash = QVBoxLayout()
        lnash.addWidget(self._make_label("Nash", "muted", align=Qt.AlignmentFlag.AlignCenter))
        lnash.addWidget(self.lbl_lat_nash)
        lopt = QVBoxLayout()
        lopt.addWidget(self._make_label("Optimal", "muted", align=Qt.AlignmentFlag.AlignCenter))
        lopt.addWidget(self.lbl_lat_opt)
        lat_l.addLayout(lnash)
        lat_l.addLayout(lopt)
        right_layout.addWidget(grp_lat)

        # Flow comparison chart
        grp_flow = QGroupBox("📊 Flow Comparison")
        fl = QVBoxLayout(grp_flow)
        self.flow_fig = Figure(figsize=(3, 2), dpi=100, facecolor='#1a2235')
        self.flow_canvas = FigureCanvasQTAgg(self.flow_fig)
        self.flow_ax = self.flow_fig.add_subplot(111)
        fl.addWidget(self.flow_canvas)
        right_layout.addWidget(grp_flow)

        # Convergence chart
        grp_conv = QGroupBox("📈 Convergence (log gap)")
        cl = QVBoxLayout(grp_conv)
        self.conv_fig = Figure(figsize=(3, 1.5), dpi=100, facecolor='#1a2235')
        self.conv_canvas = FigureCanvasQTAgg(self.conv_fig)
        self.conv_ax = self.conv_fig.add_subplot(111)
        cl.addWidget(self.conv_canvas)
        right_layout.addWidget(grp_conv)

        # Math panel (explain mode)
        self.grp_math = QGroupBox("🧠 Mathematical Foundation")
        ml = QVBoxLayout(self.grp_math)
        math_text = QTextEdit()
        math_text.setReadOnly(True)
        math_text.setMaximumHeight(200)
        math_text.setHtml(
            "<p><b>Wardrop Equilibrium:</b> All used paths have equal and minimal cost.</p>"
            "<p><b>Beckmann Objective:</b><br><code>min Σₑ ∫₀ˣₑ lₑ(t) dt</code></p>"
            "<p><b>System Optimum:</b><br><code>min Σₑ xₑ · lₑ(xₑ)</code></p>"
            "<p><b>Marginal Cost (linear):</b><br><code>MC(x) = 2ax + b</code></p>"
            "<p><b>Price of Anarchy:</b><br><code>PoA = C(Nash) / C(Optimum) ≥ 1</code></p>"
        )
        ml.addWidget(math_text)
        self.grp_math.setVisible(False)
        right_layout.addWidget(self.grp_math)

        right_layout.addStretch()
        right_scroll.setWidget(right_widget)
        splitter.addWidget(right_scroll)

        splitter.setStretchFactor(0, 0)  # left sidebar: fixed
        splitter.setStretchFactor(1, 1)  # center canvas: stretches
        splitter.setStretchFactor(2, 0)  # right panel: fixed
        splitter.setSizes([280, 580, 300])

    # ═══════════════════════════════════════════════
    # EVENTS
    # ═══════════════════════════════════════════════
    def _bind_events(self):
        self.combo_scenario.currentIndexChanged.connect(self._on_scenario_change)
        self.slider_demand.valueChanged.connect(self._on_demand_change)
        self.chk_braess.toggled.connect(self._on_braess_toggle)
        self.btn_explain.clicked.connect(self._toggle_explain)
        self.btn_demo.clicked.connect(self._run_guided_demo)
        self.btn_edit_mode.clicked.connect(self._toggle_edit_mode)
        self.btn_tolls.clicked.connect(self._toggle_tolls)
        self.btn_save.clicked.connect(self._save_config)
        self.btn_load.clicked.connect(self._load_config)
        self.btn_csv.clicked.connect(self._export_csv)
        self.btn_sensitivity.clicked.connect(self._run_sensitivity)
        self.btn_pdf.clicked.connect(self._export_pdf)
        self.graph_canvas.graph_modified.connect(self._on_graph_modified)

    def _on_scenario_change(self):
        key = self.combo_scenario.currentData()
        if key:
            self._load_scenario(key)

    def _on_demand_change(self, val):
        d = val / 10.0
        self.lbl_demand.setText(f"{d:.1f}")
        if self.graph:
            self.graph.demand = d
            self._solve()

    def _on_braess_toggle(self, checked):
        if checked:
            self.lbl_braess_status.setText("ON")
            self.lbl_braess_status.setStyleSheet(
                "color:#0a0e1a; background:#fbbf24; font-weight:700;"
                "font-size:10px; border-radius:4px; padding:2px 4px;"
            )
        else:
            self.lbl_braess_status.setText("OFF")
            self.lbl_braess_status.setStyleSheet(
                "color:#64748b; background:rgba(100,116,139,0.15); font-weight:700;"
                "font-size:10px; border-radius:4px; padding:2px 4px;"
            )
        if self.graph:
            for e in self.graph.edges.values():
                if e.is_braess:
                    e.enabled = checked
            self._build_edge_list()
            self._solve()

    def _toggle_explain(self):
        self.explain_mode = not self.explain_mode
        self.lbl_braess_explain.setVisible(self.explain_mode)
        self.lbl_poa_explain.setVisible(self.explain_mode)
        self.grp_math.setVisible(self.explain_mode)
        style = "QPushButton{background:rgba(129,140,248,0.2);border-color:#818cf8;}" if self.explain_mode else ""
        self.btn_explain.setStyleSheet(style)

    def _toggle_edge_panel(self):
        """Toggle visibility of the edge parameters panel."""
        visible = not self.grp_edges.isVisible()
        self.grp_edges.setVisible(visible)
        self.btn_toggle_edges.setText("🔧 Edge Parameters ▾" if visible else "🔧 Edge Parameters ▸")

    # ═══════════════════════════════════════════════
    # SCENARIO & SOLVER
    # ═══════════════════════════════════════════════
    def _load_scenario(self, key):
        scenario = SCENARIOS.get(key)
        if not scenario:
            return
        self.graph = scenario['create']()
        self.lbl_scenario_desc.setText(scenario['description'])
        self.slider_demand.setValue(int(self.graph.demand * 10))
        self.lbl_demand.setText(f"{self.graph.demand:.1f}")

        has_braess = any(e.is_braess for e in self.graph.edges.values())
        self.grp_braess.setVisible(has_braess)
        if has_braess:
            self.chk_braess.setChecked(True)

        self.graph_canvas.set_graph(self.graph)
        self._build_edge_list()
        self._solve()

    def _solve(self):
        if not self.graph:
            return
        result = compare(self.graph)
        self.result = result

        # Update canvas with Nash flows
        self.graph_canvas.update_flows(result.nash.flows)

        # Update metrics
        self.lbl_nash_cost.setText(f"{result.nash.total_cost:.3f}")
        self.lbl_opt_cost.setText(f"{result.optimum.total_cost:.3f}")
        self.lbl_poa.setText(f"{result.price_of_anarchy:.3f}")
        self.lbl_lat_nash.setText(f"{result.nash.avg_latency:.3f}")
        self.lbl_lat_opt.setText(f"{result.optimum.avg_latency:.3f}")

        eff = min(max(result.efficiency_loss, 0), 100)
        self.efficiency_bar.setValue(int(eff))

        # Color PoA by severity
        if result.price_of_anarchy > 1.2:
            self.lbl_poa.setStyleSheet("color:#f87171; font-family:monospace; font-size:28px; font-weight:800;")
        elif result.price_of_anarchy > 1.05:
            self.lbl_poa.setStyleSheet("color:#fbbf24; font-family:monospace; font-size:28px; font-weight:800;")
        else:
            self.lbl_poa.setStyleSheet("color:#34d399; font-family:monospace; font-size:28px; font-weight:800;")

        self._draw_flow_chart(result)
        self._draw_convergence_chart(result.nash.iterations)

    # ═══════════════════════════════════════════════
    # EDGE LIST
    # ═══════════════════════════════════════════════
    def _build_edge_list(self):
        while self.edge_layout.count():
            item = self.edge_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for e in self.graph.edges.values():
            if not e.enabled:
                continue
            row = QHBoxLayout()
            lbl = QLabel(f"{e.from_node}→{e.to_node}")
            lbl.setStyleSheet("font-family:monospace; font-weight:600; min-width:50px;")
            row.addWidget(lbl)

            spin_a = QDoubleSpinBox()
            spin_a.setPrefix("a=")
            spin_a.setRange(-10, 10)
            spin_a.setSingleStep(0.1)
            spin_a.setValue(e.latency.a)
            spin_a.setFixedWidth(75)
            spin_a.valueChanged.connect(lambda v, edge=e: self._on_edge_param(edge, 'a', v))
            row.addWidget(spin_a)

            spin_b = QDoubleSpinBox()
            spin_b.setPrefix("b=")
            spin_b.setRange(-10, 10)
            spin_b.setSingleStep(0.1)
            spin_b.setValue(e.latency.b)
            spin_b.setFixedWidth(75)
            spin_b.valueChanged.connect(lambda v, edge=e: self._on_edge_param(edge, 'b', v))
            row.addWidget(spin_b)

            wrapper = QWidget()
            wrapper.setLayout(row)
            self.edge_layout.addRow(wrapper)

    def _on_edge_param(self, edge, param, value):
        setattr(edge.latency, param, value)
        self._solve()

    # ═══════════════════════════════════════════════
    # CHARTS
    # ═══════════════════════════════════════════════
    def _draw_flow_chart(self, result):
        ax = self.flow_ax
        ax.clear()
        ax.set_facecolor('#1a2235')

        edges = [e for e in self.graph.edges.values() if e.enabled]
        if not edges:
            self.flow_canvas.draw_idle()
            return

        labels = [f"{e.from_node}→{e.to_node}" for e in edges]
        nash_vals = [result.nash.flows.get(e.id, 0) for e in edges]
        opt_vals = [result.optimum.flows.get(e.id, 0) for e in edges]

        x = np.arange(len(edges))
        w = 0.35
        ax.bar(x - w/2, nash_vals, w, color='#f87171', alpha=0.8, label='Nash', zorder=3)
        ax.bar(x + w/2, opt_vals, w, color='#34d399', alpha=0.8, label='Optimal', zorder=3)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=7, color='#64748b', rotation=30, ha='right')
        ax.tick_params(colors='#64748b', labelsize=7)
        ax.legend(fontsize=7, facecolor='#1a2235', edgecolor='#64748b', labelcolor='#f1f5f9')
        ax.spines[:].set_color('#64748b')
        ax.spines[:].set_linewidth(0.5)
        self.flow_fig.tight_layout()
        self.flow_canvas.draw_idle()

    def _draw_convergence_chart(self, iterations):
        ax = self.conv_ax
        ax.clear()
        ax.set_facecolor('#1a2235')

        if not iterations:
            self.conv_canvas.draw_idle()
            return

        iters = [it['iteration'] for it in iterations]
        gaps = [max(it['gap'], 1e-15) for it in iterations]

        ax.semilogy(iters, gaps, color='#818cf8', linewidth=1.5, zorder=3)
        ax.fill_between(iters, gaps, alpha=0.1, color='#818cf8')
        ax.set_xlabel('Iteration', fontsize=7, color='#64748b')
        ax.set_ylabel('Gap', fontsize=7, color='#64748b')
        ax.tick_params(colors='#64748b', labelsize=6)
        ax.spines[:].set_color('#64748b')
        ax.spines[:].set_linewidth(0.5)
        ax.grid(True, alpha=0.1, color='#94a3b8')
        self.conv_fig.tight_layout()
        self.conv_canvas.draw_idle()

    # ═══════════════════════════════════════════════
    # GUIDED DEMO
    # ═══════════════════════════════════════════════
    def _run_guided_demo(self):
        self.combo_scenario.setCurrentIndex(0)  # Classic Braess
        self._load_scenario('braess')

        steps = [
            ("🎬 Welcome!\n\nThis demo walks you through Braess's Paradox — "
             "where adding a new shortcut makes traffic WORSE for everyone."),
            ("📡 Step 1: The Network\n\nWe have 4 nodes: A→B. Two paths exist:\n"
             "• Top: A→C→B\n• Bottom: A→D→B\n\nThe zero-cost shortcut C→D is now OFF."),
            None,  # Action: turn off braess
            ("⚖️ Step 2: Nash Equilibrium\n\nSelfish users split evenly: 0.5 on each path.\n"
             f"Total Cost = {self.result.nash.total_cost:.3f}\nThis is efficient!"),
            ("⚡ Step 3: Adding the Shortcut!\n\nNow adding a zero-cost edge C→D.\n"
             "A free shortcut — things should get better, right?"),
            None,  # Action: turn on braess
            ("😳 BRAESS'S PARADOX!\n\n"
             f"Total Cost jumped to {self.result.nash.total_cost:.3f}!\n\n"
             "Adding a free shortcut made things 33% WORSE.\n"
             "Every selfish user rushes A→C→D→B, overloading congested edges."),
            ("🧠 Why?\n\nEach user thinks: 'C→D is free, I should use it!'\n"
             "But when EVERYONE thinks this, edges with L(x)=x get overloaded.\n\n"
             "Self-interest ≠ collective good.\nThis is the Price of Anarchy."),
            ("🏁 Demo Complete!\n\nFeel free to experiment with parameters, "
             "try different scenarios, and run sensitivity analysis!")
        ]

        # First: turn off braess
        self.chk_braess.setChecked(False)
        QTimer.singleShot(500, lambda: self._demo_step(steps, 0))

    def _demo_step(self, steps, idx):
        if idx >= len(steps):
            return
        step = steps[idx]
        if step is None:
            # Action step
            if idx == 2:
                self.chk_braess.setChecked(False)
            elif idx == 5:
                self.chk_braess.setChecked(True)
            QTimer.singleShot(800, lambda: self._demo_step(steps, idx + 1))
            return

        # Update step text for action results
        if idx == 6:
            step = (f"😳 BRAESS'S PARADOX!\n\n"
                    f"Total Cost jumped to {self.result.nash.total_cost:.3f}!\n\n"
                    "Adding a free shortcut made things 33% WORSE.\n"
                    "Every selfish user rushes A→C→D→B, overloading congested edges.")

        reply = QMessageBox.information(
            self, f"Guided Demo — Step {idx+1}/{len(steps)}",
            step,
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel
        )
        if reply == QMessageBox.StandardButton.Ok:
            QTimer.singleShot(300, lambda: self._demo_step(steps, idx + 1))

    # ═══════════════════════════════════════════════
    # SENSITIVITY ANALYSIS
    # ═══════════════════════════════════════════════
    def _run_sensitivity(self):
        if not self.graph:
            return
        result = sensitivity_analysis(self.graph, n_points=40)

        fig = Figure(figsize=(7, 5), dpi=100, facecolor='#0a0e1a')
        ax1 = fig.add_subplot(211)
        ax1.set_facecolor('#1a2235')
        ax1.plot(result['demands'], result['nash_costs'], color='#f87171', linewidth=2, label='Nash Cost')
        ax1.plot(result['demands'], result['opt_costs'], color='#34d399', linewidth=2, label='Optimal Cost')
        ax1.fill_between(result['demands'], result['opt_costs'], result['nash_costs'], alpha=0.1, color='#f87171')
        ax1.set_ylabel('Total System Cost', color='#94a3b8', fontsize=9)
        ax1.legend(fontsize=8, facecolor='#1a2235', edgecolor='#64748b', labelcolor='#f1f5f9')
        ax1.tick_params(colors='#64748b')
        ax1.grid(True, alpha=0.1)

        ax2 = fig.add_subplot(212)
        ax2.set_facecolor('#1a2235')
        ax2.plot(result['demands'], result['poa'], color='#fbbf24', linewidth=2.5)
        ax2.axhline(y=1.0, color='#34d399', linestyle='--', alpha=0.5, label='Perfect (PoA=1)')
        ax2.set_xlabel('Traffic Demand', color='#94a3b8', fontsize=9)
        ax2.set_ylabel('Price of Anarchy', color='#94a3b8', fontsize=9)
        ax2.legend(fontsize=8, facecolor='#1a2235', edgecolor='#64748b', labelcolor='#f1f5f9')
        ax2.tick_params(colors='#64748b')
        ax2.grid(True, alpha=0.1)

        fig.suptitle('Sensitivity Analysis: PoA vs Demand', color='#f1f5f9', fontsize=12, fontweight='bold')
        fig.tight_layout()

        canvas = FigureCanvasQTAgg(fig)
        canvas.setWindowTitle("Sensitivity Analysis")
        canvas.resize(700, 500)
        canvas.show()
        self._sensitivity_window = canvas  # prevent garbage collection

    # ═══════════════════════════════════════════════
    # SAVE / LOAD / EXPORT
    # ═══════════════════════════════════════════════
    def _save_config(self):
        if not self.graph:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save Network", "", "JSON Files (*.json)")
        if path:
            with open(path, 'w') as f:
                f.write(self.graph.to_json())

    def _load_config(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load Network", "", "JSON Files (*.json)")
        if not path:
            return
        try:
            with open(path) as f:
                self.graph = NetworkGraph.from_json(f.read())
            self.graph_canvas.set_graph(self.graph)
            self.slider_demand.setValue(int(self.graph.demand * 10))
            self._build_edge_list()
            self._solve()
        except Exception as ex:
            QMessageBox.critical(self, "Error", f"Failed to load: {ex}")

    def _export_csv(self):
        if not self.graph or not self.result:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export CSV", "", "CSV Files (*.csv)")
        if not path:
            return
        with open(path, 'w', newline='') as f:
            w = csv.writer(f)
            w.writerow(['Edge', 'From', 'To', 'Latency', 'Nash Flow', 'Opt Flow', 'Nash Latency', 'Opt Latency'])
            for e in self.graph.edges.values():
                if not e.enabled:
                    continue
                nf = self.result.nash.flows.get(e.id, 0)
                of_ = self.result.optimum.flows.get(e.id, 0)
                w.writerow([e.id, e.from_node, e.to_node, str(e.latency),
                            f"{nf:.4f}", f"{of_:.4f}",
                            f"{e.latency.cost(nf):.4f}", f"{e.latency.cost(of_):.4f}"])
            w.writerow([])
            w.writerow(['Metric', 'Nash', 'Optimal'])
            w.writerow(['Total Cost', f"{self.result.nash.total_cost:.4f}", f"{self.result.optimum.total_cost:.4f}"])
            w.writerow(['Avg Latency', f"{self.result.nash.avg_latency:.4f}", f"{self.result.optimum.avg_latency:.4f}"])
            w.writerow(['Price of Anarchy', f"{self.result.price_of_anarchy:.4f}", '—'])
            w.writerow(['Efficiency Loss', f"{self.result.efficiency_loss:.2f}%", '—'])

    def _export_pdf(self):
        """Generate a formal PDF report of the current simulation."""
        if not self.graph or not self.result:
            QMessageBox.warning(self, "No Data", "Run a simulation first.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save PDF Report", "braess_report.pdf", "PDF Files (*.pdf)")
        if not path:
            return
        try:
            generate_pdf_report(self.graph, self.result, path)
            QMessageBox.information(self, "PDF Exported",
                                   f"Report saved to:\n{path}")
        except Exception as ex:
            QMessageBox.critical(self, "Export Error", f"Failed: {ex}")

    def _toggle_edit_mode(self):
        """Toggle interactive network builder mode."""
        editing = not self.graph_canvas.edit_mode
        self.graph_canvas.set_edit_mode(editing)
        if editing:
            self.btn_edit_mode.setStyleSheet(
                "QPushButton{background:rgba(129,140,248,0.25);border-color:#818cf8;color:#818cf8;}"
            )
        else:
            self.btn_edit_mode.setStyleSheet("")
        self.graph_canvas.redraw()

    def _toggle_tolls(self):
        """Apply or remove Pigouvian congestion tolls."""
        if not self.graph:
            return
        self.tolls_active = not self.tolls_active
        if self.tolls_active:
            tolls = apply_pigouvian_tolls(self.graph)
            self.btn_tolls.setText("💰 Remove Tolls")
            self.btn_tolls.setStyleSheet(
                "QPushButton{background:rgba(251,191,36,0.3);border-color:#fbbf24;color:#fbbf24;}"
            )
            # Show toll info
            toll_info = "\n".join(f"  {eid}: τ={t:.4f}" for eid, t in tolls.items() if t > 0.001)
            QMessageBox.information(self, "💰 Pigouvian Tolls Applied",
                f"Optimal congestion tolls computed from System Optimum:\n\n"
                f"{toll_info}\n\n"
                f"Nash Equilibrium should now match System Optimum (PoA ≈ 1.0).")
        else:
            self.graph.clear_tolls()
            self.btn_tolls.setText("💰 Apply Tolls")
            self.btn_tolls.setStyleSheet("")
        self._solve()

    def _on_graph_modified(self):
        """Called when the interactive canvas modifies the graph."""
        self._build_edge_list()
        if self.graph and self.graph.source and self.graph.sink:
            self._solve()

    # ═══════════════════════════════════════════════
    # HELPERS
    # ═══════════════════════════════════════════════
    @staticmethod
    def _make_label(text, obj_name="", align=None):
        lbl = QLabel(text)
        if obj_name:
            lbl.setObjectName(obj_name)
        if align:
            lbl.setAlignment(align)
        return lbl

    @staticmethod
    def _make_metric_label(text, color):
        lbl = QLabel(text)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet(f"color:{color}; font-family:monospace; font-size:16px; font-weight:700;")
        return lbl


# ═══════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════
def main():
    app = QApplication(sys.argv)
    app.setFont(QFont("Inter", 10))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
