/**
 * ═══════════════════════════════════════════════════════════════
 *  STEP-BY-STEP SIMULATOR
 * ═══════════════════════════════════════════════════════════════
 *  Exposes each Frank-Wolfe iteration for animated convergence.
 */

import { frankWolfe } from './equilibrium.js';

export class Simulator {
    constructor(graph, useMarginal = false) {
        this.originalGraph = graph;
        this.graph = graph.clone();
        this.useMarginal = useMarginal;
        this.steps = [];
        this.currentStep = 0;
        this.isRunning = false;
        this.onStep = null; // callback
        this.speed = 500;   // ms between steps
        this._timer = null;
    }

    /** Run entire simulation and store all steps */
    compute() {
        this.graph = this.originalGraph.clone();
        const result = frankWolfe(this.graph, {
            useMarginal: this.useMarginal,
            recordSteps: true,
            maxIter: 100,
            tolerance: 1e-7
        });
        this.steps = result.iterations;
        this.currentStep = 0;
        return result;
    }

    /** Get step data at index */
    getStep(index) {
        if (index < 0 || index >= this.steps.length) return null;
        return this.steps[index];
    }

    /** Apply step flows to graph for visualization */
    applyStep(index) {
        const step = this.getStep(index);
        if (!step) return;
        for (const e of this.graph.activeEdges()) {
            if (step.flows[e.id] !== undefined) {
                e.flow = step.flows[e.id];
            }
        }
        this.currentStep = index;
        return step;
    }

    /** Start auto-play */
    play(callback) {
        this.onStep = callback;
        this.isRunning = true;
        this._tick();
    }

    _tick() {
        if (!this.isRunning || this.currentStep >= this.steps.length - 1) {
            this.isRunning = false;
            return;
        }
        this.currentStep++;
        this.applyStep(this.currentStep);
        if (this.onStep) this.onStep(this.steps[this.currentStep], this.currentStep);
        this._timer = setTimeout(() => this._tick(), this.speed);
    }

    /** Pause auto-play */
    pause() {
        this.isRunning = false;
        if (this._timer) clearTimeout(this._timer);
    }

    /** Step forward once */
    stepForward() {
        if (this.currentStep < this.steps.length - 1) {
            this.currentStep++;
            this.applyStep(this.currentStep);
            return this.steps[this.currentStep];
        }
        return null;
    }

    /** Step backward once */
    stepBackward() {
        if (this.currentStep > 0) {
            this.currentStep--;
            this.applyStep(this.currentStep);
            return this.steps[this.currentStep];
        }
        return null;
    }

    /** Reset to beginning */
    reset() {
        this.pause();
        this.currentStep = 0;
        this.graph = this.originalGraph.clone();
        if (this.steps.length > 0) this.applyStep(0);
    }

    get totalSteps() {
        return this.steps.length;
    }
}
