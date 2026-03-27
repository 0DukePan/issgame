/**
 * ═══════════════════════════════════════════════════════════════
 *  WARDROP EQUILIBRIUM SOLVER — Frank-Wolfe Algorithm
 * ═══════════════════════════════════════════════════════════════
 *  Finds the User Equilibrium (Nash / Wardrop) by minimizing
 *  the Beckmann objective: Σₑ ∫₀ˣₑ lₑ(t) dt
 *
 *  At equilibrium, all used paths have equal and minimal cost.
 */

import { Graph } from './graph.js';

/**
 * Frank-Wolfe algorithm for Wardrop User Equilibrium
 * @param {Graph} graph
 * @param {object} opts - {maxIter, tolerance, useMarginal}
 * @returns {{flows: Map<string,number>, totalCost: number, iterations: Array}}
 */
export function frankWolfe(graph, opts = {}) {
    const {
        maxIter = 200,
        tolerance = 1e-6,
        useMarginal = false,   // true → System Optimum
        recordSteps = false
    } = opts;

    const edges = graph.activeEdges();
    const paths = graph.enumeratePaths();

    if (paths.length === 0) {
        return { flows: new Map(), totalCost: 0, iterations: [], avgLatency: 0, converged: false };
    }

    // Initialize: all-or-nothing on shortest path (using free-flow costs)
    graph.resetFlows();
    const costFn = useMarginal
        ? (e) => e.marginalCost(0)
        : (e) => e.cost(0);

    const { path: initPath } = graph.shortestPath(costFn);
    if (initPath.length === 0) {
        return { flows: new Map(), totalCost: 0, iterations: [], avgLatency: 0, converged: false };
    }
    for (const e of initPath) e.flow = graph.demand;

    const iterations = [];
    let converged = false;

    for (let k = 1; k <= maxIter; k++) {
        // Step 1: Find shortest path under current costs → direction
        const edgeCostFn = useMarginal
            ? (e) => e.marginalCost(e.flow)
            : (e) => e.cost(e.flow);

        const { path: spPath, cost: spCost } = graph.shortestPath(edgeCostFn);
        if (spPath.length === 0) break;

        // All-or-nothing assignment along shortest path
        const yFlows = new Map();
        for (const e of edges) yFlows.set(e.id, 0);
        for (const e of spPath) yFlows.set(e.id, graph.demand);

        // Step 2: Compute duality gap (convergence check)
        let gap = 0;
        for (const e of edges) {
            const c = useMarginal ? e.marginalCost(e.flow) : e.cost(e.flow);
            gap += c * (e.flow - yFlows.get(e.id));
        }

        // Step 3: Line search for optimal step size α ∈ [0, 1]
        // Minimize Σₑ ∫₀^{xₑ + α(yₑ - xₑ)} lₑ(t) dt
        const alpha = lineSearch(edges, yFlows, useMarginal);

        // Step 4: Update flows: xₑ ← xₑ + α(yₑ - xₑ)
        for (const e of edges) {
            const y = yFlows.get(e.id);
            e.flow = e.flow + alpha * (y - e.flow);
        }

        const totalCost = graph.totalSystemCost();
        const beckmann = graph.beckmannObjective();

        if (recordSteps) {
            iterations.push({
                iteration: k,
                alpha,
                gap: Math.abs(gap),
                totalCost,
                beckmann,
                flows: Object.fromEntries(edges.map(e => [e.id, e.flow])),
                shortestPathCost: spCost
            });
        }

        if (Math.abs(gap) < tolerance) {
            converged = true;
            break;
        }
    }

    // Compute path flows for display
    const pathFlows = computePathFlows(graph, paths);

    const totalCost = graph.totalSystemCost();
    const avgLatency = graph.demand > 0 ? totalCost / graph.demand : 0;

    return {
        flows: new Map(edges.map(e => [e.id, e.flow])),
        pathFlows,
        totalCost,
        avgLatency,
        iterations,
        converged
    };
}


/**
 * Bisection line search for optimal step size
 */
function lineSearch(edges, yFlows, useMarginal) {
    let lo = 0, hi = 1;

    for (let i = 0; i < 30; i++) {
        const mid = (lo + hi) / 2;
        let grad = 0;

        for (const e of edges) {
            const y = yFlows.get(e.id);
            const xNew = e.flow + mid * (y - e.flow);
            const c = useMarginal ? e.marginalCost(xNew) : e.cost(xNew);
            grad += c * (y - e.flow);
        }

        if (grad < 0) lo = mid;
        else hi = mid;
    }

    return (lo + hi) / 2;
}


/**
 * Decompose edge flows into path flows
 * Uses proportional assignment based on path costs
 */
function computePathFlows(graph, paths) {
    if (paths.length === 0) return [];

    // Compute path costs
    const pathInfos = paths.map(p => {
        const cost = p.reduce((s, e) => s + e.cost(), 0);
        const edgeIds = p.map(e => e.id);
        return { edges: edgeIds, cost, flow: 0 };
    });

    // At equilibrium, all used paths have equal cost (min cost)
    const minCost = Math.min(...pathInfos.map(p => p.cost));
    const usedPaths = pathInfos.filter(p => Math.abs(p.cost - minCost) < 0.01);

    if (usedPaths.length > 0) {
        const flowEach = graph.demand / usedPaths.length;
        for (const p of usedPaths) p.flow = flowEach;
    }

    return pathInfos;
}


/**
 * Solve for Wardrop User Equilibrium (Nash)
 */
export function solveNashEquilibrium(graph, opts = {}) {
    return frankWolfe(graph, { ...opts, useMarginal: false });
}
