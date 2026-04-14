# ⚡ Braess's Paradox — Selfish Routing Simulator

A professional-grade interactive desktop application for simulating and analyzing **Braess's Paradox** in transportation networks. Built with **PyQt6** and **NumPy**, it implements the full traffic assignment pipeline: Frank-Wolfe solver, Nash Equilibrium, System Optimum, BPR latency functions, and Pigouvian congestion pricing.

---

## 🖥️ Features

### Core Engine
| Feature | Description |
|---|---|
| **Frank-Wolfe Solver** | Vectorized iterative solver for Wardrop Nash Equilibrium |
| **System Optimum** | Marginal-cost-based SO computation via Beckmann minimization |
| **BPR Functions** | Bureau of Public Roads latency: `L(x) = t₀(1 + α(x/C)^β)` |
| **Pigouvian Tolls** | Auto-compute optimal congestion tolls → brings PoA to 1.0 |
| **Multi-latency Types** | Linear, Polynomial, Logarithmic, BPR |
| **Price of Anarchy** | `PoA = C(Nash) / C(Optimum)` — real-time calculation |

### Interactive GUI
- 🏗️ **Network Builder** — double-click to add nodes, drag to create edges, right-click context menus
- 📡 **3 Built-in Scenarios** — Classic Braess, Pigou Network, 6-Node Mesh
- 🚗 **Traffic Demand Slider** — real-time demand adjustment (0.1–3.0 units)
- ⚡ **Braess Toggle** — enable/disable the paradox-inducing edge live
- 🔧 **Collapsible Edge Editor** — edit latency params (a, b, c, t₀, C, α, β) per edge
- 💰 **Pigouvian Tolls** — one-click to apply/remove optimal tolls
- 📖 **Explain Mode** — reveals mathematical formulations and explanations

### Analytics & Export
- 📊 **Flow Comparison Chart** — Nash vs Optimal flow per edge
- 📈 **Frank-Wolfe Convergence Plot** — gap vs iteration (log scale)
- 📉 **Efficiency Loss Bar** — % welfare loss from selfish routing
- 📄 **PDF Report Generator** — formal academic 2-page report with charts + tables
- 💾 **JSON Save/Load** — persist and restore network configurations
- 📑 **CSV Export** — edge-by-edge flow, latency, and cost data
- 📈 **Sensitivity Analysis** — PoA vs demand sweep chart

---

## 📁 Project Structure

```
breses-paradox-python/
├── main_window.py        # PyQt6 dashboard — 3-pane layout (sidebar, canvas, metrics)
├── graph_canvas.py       # Interactive Matplotlib canvas (builder + viewer)
└── core/
    ├── graph.py          # NetworkGraph, Edge, LatencyFunction (BPR, linear, poly, log)
    ├── solver.py         # Frank-Wolfe, Nash, SO, Pigouvian tolls, sensitivity
    ├── scenarios.py      # Built-in network presets
    └── report.py         # PDF report generator (Matplotlib PdfPages)
```

---

## 🚀 Getting Started

### Prerequisites
```bash
pip install PyQt6 numpy matplotlib scipy
```

### Run
```bash
cd breses-paradox-python
python3 main_window.py
```

---

## 📐 Mathematical Background

### Wardrop Nash Equilibrium
All used routes between an OD pair have **equal and minimum travel cost**:
$$L_r(f) = \min_{s \in R} L_s(f), \quad \forall r \text{ with } f_r > 0$$

### System Optimum (Beckmann)
$$\min \sum_e \int_0^{x_e} l_e(t)\, dt$$

### BPR Latency Function
$$L_e(x) = t_0 \left(1 + \alpha \left(\frac{x}{C}\right)^\beta\right)$$

### Pigouvian Toll
$$\tau_e = x_e \cdot l_e'(x_e^*)$$
where $x_e^*$ is the System Optimum flow. Charging this toll makes selfish routing coincide with system optimum → **PoA = 1.0**.

### Price of Anarchy
$$\text{PoA} = \frac{C(\text{Nash})}{C(\text{Optimum})} \geq 1$$

---

## 🎬 Demo: Classic Braess's Paradox

| Scenario | Total Cost | PoA |
|---|---|---|
| Without shortcut (C→D disabled) | **1.500** | 1.000 |
| With shortcut (C→D enabled) | **2.000** | **1.333** |
| With Pigouvian tolls | **1.500** | **1.000** |

> Adding a zero-cost shortcut edge **increases** total network cost by 33% — because every selfish user takes it, congesting the whole network.

---

## 🛠️ Controls Quick Reference

| Action | How |
|---|---|
| Add node | Double-click canvas (Edit Mode on) |
| Add edge | Drag from node to node (Edit Mode on) |
| Edit edge latency | Right-click edge → Edit Latency |
| Delete node/edge | Right-click → Delete |
| Apply Pigouvian tolls | Click **💰 Apply Tolls** |
| Export PDF report | Click **📄 PDF Report** |
| Toggle Edge Parameters | Click **🔧 Edge Parameters ▸** |

---

## 📄 License

MIT — free to use, modify, and distribute.
