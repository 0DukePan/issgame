/**
 * ═══════════════════════════════════════════════════════════════
 *  SYSTEM OPTIMUM SOLVER
 * ═══════════════════════════════════════════════════════════════
 *  Finds the centralized optimal routing that minimizes
 *  total system cost: Σₑ xₑ · lₑ(xₑ)
 *
 *  Uses marginal costs in Frank-Wolfe: lₑ(x) + x·lₑ'(x)
 */

import { frankWolfe } from './equilibrium.js';

/**
 * Solve for System Optimum (centralized, socially optimal)
 * @param {Graph} graph
 * @param {object} opts
 */
export function solveSystemOptimum(graph, opts = {}) {
    return frankWolfe(graph, { ...opts, useMarginal: true });
}


/**
 * Compare Nash Equilibrium vs System Optimum
 * @param {Graph} graph
 * @returns {object} Full comparison with Price of Anarchy
 */
export function compareEquilibria(graph, opts = {}) {
    const nashGraph = graph.clone();
    const optGraph = graph.clone();

    const nash = frankWolfe(nashGraph, { ...opts, useMarginal: false, recordSteps: true });
    const opt = frankWolfe(optGraph, { ...opts, useMarginal: true, recordSteps: true });

    const priceOfAnarchy = opt.totalCost > 0
        ? nash.totalCost / opt.totalCost
        : 1;

    const efficiencyLoss = opt.totalCost > 0
        ? ((nash.totalCost - opt.totalCost) / opt.totalCost) * 100
        : 0;

    return {
        nash: {
            ...nash,
            graph: nashGraph
        },
        optimum: {
            ...opt,
            graph: optGraph
        },
        priceOfAnarchy,
        efficiencyLoss,
        nashTotalCost: nash.totalCost,
        optTotalCost: opt.totalCost,
        nashAvgLatency: nash.avgLatency,
        optAvgLatency: opt.avgLatency
    };
}
