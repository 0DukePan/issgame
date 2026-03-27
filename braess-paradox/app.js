/**
 * ═══════════════════════════════════════════════════════════════
 *  APP CONTROLLER — Main Application Entry Point
 * ═══════════════════════════════════════════════════════════════
 *  Wires core engine ↔ UI. Handles events, guided demo,
 *  explain mode, save/load, and export.
 */

import { Graph } from './core/graph.js';
import { solveNashEquilibrium } from './core/equilibrium.js';
import { solveSystemOptimum, compareEquilibria } from './core/optimizer.js';
import { Simulator } from './core/simulator.js';
import { SCENARIOS } from './core/scenarios.js';
import { NetworkRenderer } from './renderer.js';
import { Charts } from './charts.js';

class App {
    constructor() {
        // State
        this.graph = null;
        this.result = null;
        this.simulator = null;
        this.explainMode = false;
        this.demoRunning = false;
        this.demoStep = 0;

        // UI Modules
        this.renderer = new NetworkRenderer(document.getElementById('network-canvas'));
        this.charts = new Charts();

        // DOM References
        this.$ = {
            scenario: document.getElementById('select-scenario'),
            scenarioDesc: document.getElementById('scenario-desc'),
            demand: document.getElementById('slider-demand'),
            demandValue: document.getElementById('demand-value'),
            braessToggle: document.getElementById('toggle-braess'),
            braessStatus: document.getElementById('braess-status'),
            braessExplain: document.getElementById('braess-explain'),
            edgeList: document.getElementById('edge-list'),
            // Metrics
            nashCost: document.getElementById('metric-nash-cost'),
            optCost: document.getElementById('metric-opt-cost'),
            poaValue: document.getElementById('poa-value'),
            poaExplain: document.getElementById('poa-explain'),
            effBar: document.getElementById('efficiency-bar'),
            effPct: document.getElementById('efficiency-pct'),
            effExplain: document.getElementById('efficiency-explain-text'),
            latNash: document.getElementById('lat-nash'),
            latOpt: document.getElementById('lat-opt'),
            // Simulation
            simIter: document.getElementById('sim-iter'),
            simTotal: document.getElementById('sim-total'),
            simGap: document.getElementById('sim-gap'),
            // Buttons
            btnExplain: document.getElementById('btn-explain'),
            btnDemo: document.getElementById('btn-guided-demo'),
            btnSimReset: document.getElementById('btn-sim-reset'),
            btnSimBack: document.getElementById('btn-sim-back'),
            btnSimPlay: document.getElementById('btn-sim-play'),
            btnSimForward: document.getElementById('btn-sim-forward'),
            btnSave: document.getElementById('btn-save'),
            btnLoad: document.getElementById('btn-load'),
            btnExportCSV: document.getElementById('btn-export-csv'),
            fileInput: document.getElementById('file-input'),
            // Demo
            demoOverlay: document.getElementById('demo-overlay'),
            demoText: document.getElementById('demo-text'),
            demoNext: document.getElementById('demo-next'),
            // Math
            mathPanel: document.getElementById('panel-math'),
        };

        this._bindEvents();
        this._loadScenario('braess');
        this.renderer.start();
    }

    // ═══════════ EVENT BINDING ═══════════
    _bindEvents() {
        // Scenario
        this.$.scenario.addEventListener('change', () => {
            this._loadScenario(this.$.scenario.value);
        });

        // Demand slider
        this.$.demand.addEventListener('input', () => {
            const v = parseFloat(this.$.demand.value);
            this.$.demandValue.textContent = v.toFixed(1);
            this.graph.demand = v;
            this._solve();
        });

        // Braess toggle
        this.$.braessToggle.addEventListener('change', () => {
            const on = this.$.braessToggle.checked;
            this.$.braessStatus.textContent = on ? 'ON — Paradox Active' : 'OFF — No Shortcut';
            // Toggle all braess edges
            for (const e of this.graph.edges.values()) {
                if (e.isBraess) e.enabled = on;
            }
            this._solve();
            this._buildEdgeList();
        });

        // Explain mode
        this.$.btnExplain.addEventListener('click', () => {
            this.explainMode = !this.explainMode;
            this.$.btnExplain.classList.toggle('btn-active', this.explainMode);
            this._toggleExplain();
        });

        // Guided Demo
        this.$.btnDemo.addEventListener('click', () => this._startGuidedDemo());
        this.$.demoNext.addEventListener('click', () => this._nextDemoStep());

        // Simulation controls
        this.$.btnSimReset.addEventListener('click', () => this._simReset());
        this.$.btnSimBack.addEventListener('click', () => this._simStep(-1));
        this.$.btnSimPlay.addEventListener('click', () => this._simPlayPause());
        this.$.btnSimForward.addEventListener('click', () => this._simStep(1));

        // Save/Load/Export
        this.$.btnSave.addEventListener('click', () => this._saveConfig());
        this.$.btnLoad.addEventListener('click', () => this.$.fileInput.click());
        this.$.fileInput.addEventListener('change', (e) => this._loadConfig(e));
        this.$.btnExportCSV.addEventListener('click', () => this._exportCSV());
    }

    // ═══════════ SCENARIO LOADING ═══════════
    _loadScenario(key) {
        const scenario = SCENARIOS[key];
        if (!scenario) return;

        this.graph = scenario.create();
        this.$.scenarioDesc.textContent = scenario.description;
        this.$.demand.value = this.graph.demand;
        this.$.demandValue.textContent = this.graph.demand.toFixed(1);

        // Check for braess edges
        let hasBraess = false;
        for (const e of this.graph.edges.values()) {
            if (e.isBraess) { hasBraess = true; break; }
        }
        document.getElementById('panel-braess').style.display = hasBraess ? '' : 'none';
        if (hasBraess) {
            this.$.braessToggle.checked = true;
            this.$.braessStatus.textContent = 'ON — Paradox Active';
        }

        this.renderer.setGraph(this.graph);
        this._buildEdgeList();
        this._solve();
        this._initSimulator();
    }

    // ═══════════ SOLVER ═══════════
    _solve() {
        if (!this.graph) return;

        // Clone for both solvers
        const nashGraph = this.graph.clone();
        const optGraph = this.graph.clone();

        const nash = solveNashEquilibrium(nashGraph, { recordSteps: true });
        const opt = solveSystemOptimum(optGraph, { recordSteps: true });

        const nashCost = nash.totalCost;
        const optCost = opt.totalCost;
        const poa = optCost > 0 ? nashCost / optCost : 1;
        const effLoss = optCost > 0 ? ((nashCost - optCost) / optCost) * 100 : 0;

        this.result = { nash, opt, poa, effLoss };

        // Update graph with Nash flows for display
        for (const e of this.graph.activeEdges()) {
            const f = nash.flows.get(e.id);
            if (f !== undefined) e.flow = f;
        }

        // Feed renderer
        this.renderer.setFlows(nash.flows, 'nash');

        // Update metrics
        this.$.nashCost.textContent = nashCost.toFixed(3);
        this.$.optCost.textContent = optCost.toFixed(3);
        this.$.poaValue.textContent = poa.toFixed(3);
        this.$.latNash.textContent = nash.avgLatency.toFixed(3);
        this.$.latOpt.textContent = opt.avgLatency.toFixed(3);

        // Efficiency bar
        const clampedEff = Math.min(Math.max(effLoss, 0), 100);
        this.$.effBar.style.width = clampedEff + '%';
        this.$.effPct.textContent = effLoss.toFixed(1) + '%';

        // Charts
        this.charts.drawPoAGauge(poa);
        this.charts.drawFlowChart(nash.flows, opt.flows, [...this.graph.edges.values()]);
        this.charts.drawConvergenceChart(nash.iterations);

        // Update edge list flows
        this._updateEdgeFlows();
    }

    // ═══════════ EDGE LIST ═══════════
    _buildEdgeList() {
        const container = this.$.edgeList;
        container.innerHTML = '';

        for (const e of this.graph.edges.values()) {
            if (!e.enabled) continue;

            const div = document.createElement('div');
            div.className = 'edge-item';
            div.innerHTML = `
        <div>
          <span class="edge-name">${e.from} → ${e.to}</span>
          <span class="edge-latency" data-edge-latency="${e.id}">${e.latencyString()}</span>
        </div>
        <div style="display:flex; gap:4px; align-items:center;">
          <label style="font-size:0.7rem; color:#64748b;">a=</label>
          <input class="edge-param-input" data-edge="${e.id}" data-param="a" type="number" step="0.1" value="${e.latency.a}">
        </div>
        <div style="display:flex; gap:4px; align-items:center;">
          <label style="font-size:0.7rem; color:#64748b;">b=</label>
          <input class="edge-param-input" data-edge="${e.id}" data-param="b" type="number" step="0.1" value="${e.latency.b}">
        </div>
      `;
            container.appendChild(div);
        }

        // Bind inputs
        container.querySelectorAll('.edge-param-input').forEach(input => {
            input.addEventListener('change', () => {
                const edgeId = input.dataset.edge;
                const param = input.dataset.param;
                const edge = this.graph.edges.get(edgeId);
                if (!edge) return;
                edge.latency[param] = parseFloat(input.value) || 0;
                // Update label
                const lbl = container.querySelector(`[data-edge-latency="${edgeId}"]`);
                if (lbl) lbl.textContent = edge.latencyString();
                this._solve();
            });
        });
    }

    _updateEdgeFlows() {
        // Could update display flow values on edge items if desired
    }

    // ═══════════ EXPLAIN MODE ═══════════
    _toggleExplain() {
        const show = this.explainMode;
        this.$.braessExplain.classList.toggle('hidden', !show);
        this.$.poaExplain.classList.toggle('hidden', !show);
        this.$.mathPanel.classList.toggle('hidden', !show);
        this.$.effExplain.style.display = show ? '' : 'none';
    }

    // ═══════════ GUIDED DEMO ═══════════
    _startGuidedDemo() {
        this.demoRunning = true;
        this.demoStep = 0;

        // Force Classic Braess scenario
        this.$.scenario.value = 'braess';
        this._loadScenario('braess');

        // Start with Braess edge OFF
        this.$.braessToggle.checked = false;
        this.$.braessToggle.dispatchEvent(new Event('change'));

        // Enable explain mode
        if (!this.explainMode) {
            this.explainMode = true;
            this.$.btnExplain.classList.add('btn-active');
            this._toggleExplain();
        }

        this._showDemoStep();
    }

    get _demoSteps() {
        const r = this.result;
        const nashCost = r ? r.nash.totalCost.toFixed(3) : '?';
        const optCost = r ? r.opt.totalCost.toFixed(3) : '?';

        return [
            {
                text: `🎬 <strong>Welcome to the Guided Demo!</strong><br><br>This demo will walk you through <em>Braess's Paradox</em> — where adding a new road to a network makes traffic <strong>worse</strong> for everyone.`,
                action: null
            },
            {
                text: `📡 <strong>Step 1: The Network (No Shortcut)</strong><br><br>We have 4 nodes: Source A → Sink B. Two paths exist:<br>• Top: A→C→B<br>• Bottom: A→D→B<br><br>Currently the <strong>zero-cost shortcut C→D is OFF</strong>.`,
                action: null
            },
            {
                text: `⚖️ <strong>Step 2: Nash Equilibrium Result</strong><br><br>Selfish users split evenly: <strong>0.5 on each path</strong>.<br>• Total System Cost = <strong>${nashCost}</strong><br>• Each user experiences latency = <strong>1.5</strong><br><br>This is actually efficient! Nash = Optimum here.`,
                action: null
            },
            {
                text: `⚡ <strong>Step 3: Adding the Shortcut!</strong><br><br>Now we add a <strong>zero-cost edge C→D</strong>. Logic says: "a free shortcut — things should get better, right?"<br><br>Click <strong>Next</strong> to find out...`,
                action: () => {
                    this.$.braessToggle.checked = true;
                    this.$.braessToggle.dispatchEvent(new Event('change'));
                }
            },
            {
                text: `😳 <strong>Step 4: BRAESS'S PARADOX!</strong><br><br>Total System Cost jumped to <strong>${this.result ? this.result.nash.totalCost.toFixed(3) : '2.000'}</strong>!<br><br>Adding a free shortcut made things <strong>33% worse</strong>.<br>Every selfish user rushes to use the shortcut (A→C→D→B), creating massive congestion on edges A→C and D→B.`,
                action: null
            },
            {
                text: `🧠 <strong>Step 5: Why does this happen?</strong><br><br>Each user thinks: "C→D is free, I should use it!"<br>But when <em>everyone</em> thinks this way, edges with <code>L(x)=x</code> get overloaded.<br><br>Self-interest ≠ collective good.<br>This is the <strong>Price of Anarchy</strong>.`,
                action: null
            },
            {
                text: `🏁 <strong>Demo Complete!</strong><br><br>You've just witnessed one of game theory's most famous results.<br><br>Feel free to experiment: change traffic demand, adjust latency functions, and explore other scenarios!`,
                action: null
            }
        ];
    }

    _showDemoStep() {
        const steps = this._demoSteps;
        if (this.demoStep >= steps.length) {
            this._endDemo();
            return;
        }
        const step = steps[this.demoStep];
        this.$.demoOverlay.classList.remove('hidden');
        this.$.demoText.innerHTML = step.text;
        this.$.demoNext.textContent = this.demoStep === steps.length - 1 ? 'Finish ✓' : 'Next →';
    }

    _nextDemoStep() {
        const steps = this._demoSteps;
        // Execute action of NEXT step (if it has one)
        this.demoStep++;
        if (this.demoStep < steps.length) {
            const step = steps[this.demoStep];
            if (step.action) step.action();
            // Small delay for visuals to update
            setTimeout(() => this._showDemoStep(), 100);
        } else {
            this._endDemo();
        }
    }

    _endDemo() {
        this.demoRunning = false;
        this.$.demoOverlay.classList.add('hidden');
    }

    // ═══════════ SIMULATION ═══════════
    _initSimulator() {
        this.simulator = new Simulator(this.graph, false);
        this.simulator.compute();
        this.$.simTotal.textContent = this.simulator.totalSteps;
        this.$.simIter.textContent = '0';
        this.$.simGap.textContent = '—';
    }

    _simReset() {
        if (!this.simulator) return;
        this.simulator.reset();
        this.$.simIter.textContent = '0';
        this.$.simGap.textContent = '—';
        this.$.btnSimPlay.textContent = '▶';
        this.charts.drawConvergenceChart(this.simulator.steps.slice(0, 1));
        // Reset flows on renderer
        this.renderer.setFlows(new Map([...this.graph.edges.values()].map(e => [e.id, 0])));
    }

    _simStep(dir) {
        if (!this.simulator) return;
        const step = dir > 0 ? this.simulator.stepForward() : this.simulator.stepBackward();
        if (step) {
            this._updateSimUI(step, this.simulator.currentStep);
            // Update renderer with step flows
            const flowMap = new Map(Object.entries(step.flows));
            this.renderer.setFlows(flowMap);
            this.charts.drawConvergenceChart(this.simulator.steps.slice(0, this.simulator.currentStep + 1));
        }
    }

    _simPlayPause() {
        if (!this.simulator) return;

        if (this.simulator.isRunning) {
            this.simulator.pause();
            this.$.btnSimPlay.textContent = '▶';
        } else {
            if (this.simulator.currentStep >= this.simulator.totalSteps - 1) {
                this.simulator.reset();
                this.simulator.compute();
            }
            this.$.btnSimPlay.textContent = '⏸';
            this.simulator.play((step, idx) => {
                this._updateSimUI(step, idx);
                const flowMap = new Map(Object.entries(step.flows));
                this.renderer.setFlows(flowMap);
                this.charts.drawConvergenceChart(this.simulator.steps.slice(0, idx + 1));

                if (idx >= this.simulator.totalSteps - 1) {
                    this.$.btnSimPlay.textContent = '▶';
                }
            });
        }
    }

    _updateSimUI(step, idx) {
        this.$.simIter.textContent = idx;
        this.$.simGap.textContent = step.gap.toExponential(2);
    }

    // ═══════════ SAVE / LOAD / EXPORT ═══════════
    _saveConfig() {
        const data = JSON.stringify(this.graph.toJSON(), null, 2);
        const blob = new Blob([data], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `braess-network-${Date.now()}.json`;
        a.click();
        URL.revokeObjectURL(url);
    }

    _loadConfig(event) {
        const file = event.target.files[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = (e) => {
            try {
                const json = JSON.parse(e.target.result);
                this.graph = Graph.fromJSON(json);
                this.renderer.setGraph(this.graph);
                this._buildEdgeList();
                this._solve();
                this._initSimulator();
                this.$.demand.value = this.graph.demand;
                this.$.demandValue.textContent = this.graph.demand.toFixed(1);
            } catch (err) {
                console.error('Failed to load config:', err);
            }
        };
        reader.readAsText(file);
        // Reset file input
        event.target.value = '';
    }

    _exportCSV() {
        if (!this.result) return;

        const lines = ['Edge,From,To,Latency Function,Nash Flow,Optimal Flow,Nash Latency,Optimal Latency'];

        for (const e of this.graph.edges.values()) {
            if (!e.enabled) continue;
            const nf = this.result.nash.flows.get(e.id) || 0;
            const of_ = this.result.opt.flows.get(e.id) || 0;
            const nl = e.cost(nf);
            const ol = e.cost(of_);
            lines.push(`${e.id},${e.from},${e.to},"${e.latencyString()}",${nf.toFixed(4)},${of_.toFixed(4)},${nl.toFixed(4)},${ol.toFixed(4)}`);
        }

        lines.push('');
        lines.push('Metric,Nash,Optimal');
        lines.push(`Total Cost,${this.result.nash.totalCost.toFixed(4)},${this.result.opt.totalCost.toFixed(4)}`);
        lines.push(`Avg Latency,${this.result.nash.avgLatency.toFixed(4)},${this.result.opt.avgLatency.toFixed(4)}`);
        lines.push(`Price of Anarchy,${this.result.poa.toFixed(4)},—`);
        lines.push(`Efficiency Loss,${this.result.effLoss.toFixed(2)}%,—`);

        const blob = new Blob([lines.join('\n')], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `braess-results-${Date.now()}.csv`;
        a.click();
        URL.revokeObjectURL(url);
    }
}

// ═══════════ BOOT ═══════════
window.addEventListener('DOMContentLoaded', () => {
    window.app = new App();
});
