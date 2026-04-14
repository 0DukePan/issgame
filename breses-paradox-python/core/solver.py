"""
═══════════════════════════════════════════════════════════════
 FRANK-WOLFE SOLVER — Wardrop Equilibrium & System Optimum
═══════════════════════════════════════════════════════════════
 Vectorized Frank-Wolfe algorithm using NumPy.
 - Nash Equilibrium: minimizes Beckmann objective Σₑ ∫₀ˣₑ lₑ(t)dt
 - System Optimum: minimizes Σₑ xₑ·lₑ(xₑ) via marginal costs
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import numpy as np
from .graph import NetworkGraph, NetworkEdge


@dataclass
class SolverResult:
    """Result of an equilibrium computation."""
    flows: Dict[str, float] = field(default_factory=dict)
    total_cost: float = 0.0
    avg_latency: float = 0.0
    iterations: List[dict] = field(default_factory=list)
    converged: bool = False
    path_flows: List[dict] = field(default_factory=list)


@dataclass
class ComparisonResult:
    """Side-by-side Nash vs System Optimum."""
    nash: SolverResult = field(default_factory=SolverResult)
    optimum: SolverResult = field(default_factory=SolverResult)
    nash_graph: Optional[NetworkGraph] = None
    opt_graph: Optional[NetworkGraph] = None
    price_of_anarchy: float = 1.0
    efficiency_loss: float = 0.0   # percentage


def frank_wolfe(graph: NetworkGraph, use_marginal: bool = False,
                max_iter: int = 200, tolerance: float = 1e-7,
                record_steps: bool = False) -> SolverResult:
    """
    Frank-Wolfe algorithm for traffic assignment.

    Parameters
    ----------
    graph : NetworkGraph
        The network (will be mutated — flows updated in place).
    use_marginal : bool
        False → Wardrop/Nash (user cost), True → System Optimum (marginal cost).
    max_iter : int
        Maximum iterations.
    tolerance : float
        Convergence gap threshold.
    record_steps : bool
        Whether to record per-iteration data for visualization.

    Returns
    -------
    SolverResult
    """
    edges = graph.active_edges()
    if not edges:
        return SolverResult()

    paths = graph.enumerate_paths()
    if not paths:
        return SolverResult()

    # Edge index mapping for vectorization
    edge_idx = {e.id: i for i, e in enumerate(edges)}
    n_edges = len(edges)

    # ── Step 0: Initialize — all-or-nothing on shortest path ──
    graph.reset_flows()
    cost_fn = (lambda e: e.latency.marginal_cost(0)) if use_marginal \
              else (lambda e: e.latency.cost(0))
    init_path, _ = graph.shortest_path(cost_fn)
    if not init_path:
        return SolverResult()

    # Flow vector
    x = np.zeros(n_edges)
    for e in init_path:
        idx = edge_idx[e.id]
        x[idx] = graph.demand
        e.flow = graph.demand

    iterations = []
    converged = False

    for k in range(1, max_iter + 1):
        # ── Step 1: Compute edge costs at current flows ──
        if use_marginal:
            costs = np.array([e.latency.marginal_cost(x[edge_idx[e.id]])
                              for e in edges])
        else:
            # Nash: user-perceived cost = latency + toll
            costs = np.array([e.latency.cost(x[edge_idx[e.id]]) + e.toll
                              for e in edges])

        # ── Step 2: Shortest path → all-or-nothing assignment ──
        def sp_cost(e):
            return costs[edge_idx[e.id]]

        sp_path, sp_cost_val = graph.shortest_path(sp_cost)
        if not sp_path:
            break

        y = np.zeros(n_edges)
        for e in sp_path:
            y[edge_idx[e.id]] = graph.demand

        # ── Step 3: Duality gap (convergence check) ──
        gap = float(np.dot(costs, x - y))

        # ── Step 4: Line search for optimal step α ∈ [0,1] ──
        alpha = _line_search(edges, edge_idx, x, y, use_marginal)

        # ── Step 5: Update: x ← x + α(y − x) ──
        x = x + alpha * (y - x)

        # Write back to graph
        for e in edges:
            e.flow = float(x[edge_idx[e.id]])

        total_cost = graph.total_system_cost()
        beckmann = graph.beckmann_objective()

        if record_steps:
            iterations.append({
                'iteration': k,
                'alpha': float(alpha),
                'gap': abs(gap),
                'total_cost': total_cost,
                'beckmann': beckmann,
                'flows': {e.id: float(x[edge_idx[e.id]]) for e in edges}
            })

        if abs(gap) < tolerance:
            converged = True
            break

    # ── Compute results ──
    total_cost = graph.total_system_cost()
    avg_latency = total_cost / graph.demand if graph.demand > 0 else 0
    flows = {e.id: float(e.flow) for e in edges}

    # Path flow decomposition
    path_flows = _compute_path_flows(graph, paths)

    return SolverResult(
        flows=flows,
        total_cost=total_cost,
        avg_latency=avg_latency,
        iterations=iterations,
        converged=converged,
        path_flows=path_flows
    )


def _line_search(edges, edge_idx, x, y, use_marginal, n_bisect=30):
    """Bisection line search for optimal step size α."""
    lo, hi = 0.0, 1.0
    for _ in range(n_bisect):
        mid = (lo + hi) / 2
        grad = 0.0
        for e in edges:
            i = edge_idx[e.id]
            x_new = x[i] + mid * (y[i] - x[i])
            c = e.latency.marginal_cost(x_new) if use_marginal \
                else e.latency.cost(x_new) + e.toll
            grad += c * (y[i] - x[i])
        if grad < 0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def _compute_path_flows(graph, paths):
    """Decompose edge flows into approximate path flows."""
    if not paths:
        return []
    results = []
    for p in paths:
        cost = sum(e.latency.cost(e.flow) for e in p)
        edge_ids = [e.id for e in p]
        results.append({
            'edges': edge_ids,
            'cost': cost,
            'flow': 0.0,
            'description': '→'.join(e.from_node for e in p) + '→' + p[-1].to_node
        })

    # At equilibrium, used paths have equal & minimal cost
    min_cost = min(r['cost'] for r in results)
    used = [r for r in results if abs(r['cost'] - min_cost) < 0.05]
    if used:
        each = graph.demand / len(used)
        for r in used:
            r['flow'] = each
    return results


# ─────────────────────────────────────────────────────────
# High-level API
# ─────────────────────────────────────────────────────────

def solve_nash(graph: NetworkGraph, **kwargs) -> SolverResult:
    """Solve for Wardrop User Equilibrium (Nash)."""
    return frank_wolfe(graph, use_marginal=False, **kwargs)


def solve_system_optimum(graph: NetworkGraph, **kwargs) -> SolverResult:
    """Solve for centralized System Optimum."""
    return frank_wolfe(graph, use_marginal=True, **kwargs)


def compare(graph: NetworkGraph, **kwargs) -> ComparisonResult:
    """Full Nash vs System Optimum comparison."""
    nash_g = graph.clone()
    opt_g = graph.clone()

    nash = solve_nash(nash_g, record_steps=True, **kwargs)
    opt = solve_system_optimum(opt_g, record_steps=True, **kwargs)

    poa = nash.total_cost / opt.total_cost if opt.total_cost > 0 else 1.0
    eff_loss = ((nash.total_cost - opt.total_cost) / opt.total_cost * 100) \
               if opt.total_cost > 0 else 0.0

    return ComparisonResult(
        nash=nash, optimum=opt,
        nash_graph=nash_g, opt_graph=opt_g,
        price_of_anarchy=poa,
        efficiency_loss=eff_loss
    )


def compute_pigouvian_tolls(graph: NetworkGraph) -> Dict[str, float]:
    """
    Compute optimal Pigouvian tolls for each edge.

    The toll τₑ = xₑ* · lₑ'(xₑ*) evaluated at the System Optimum flow xₑ*.
    This equals the marginal external cost: MC(x) - L(x).
    When these tolls are applied, the Nash Equilibrium matches the System Optimum.

    Returns dict mapping edge_id → toll value.
    """
    # First solve for System Optimum to get optimal flows
    opt_g = graph.clone()
    opt_g.clear_tolls()
    opt_result = solve_system_optimum(opt_g)

    tolls = {}
    for e in opt_g.active_edges():
        flow = opt_result.flows.get(e.id, 0.0)
        # Toll = Marginal Social Cost - Private Cost
        # τ(x) = MC(x) - L(x) = x·L'(x)
        mc = e.latency.marginal_cost(flow)
        pc = e.latency.cost(flow)
        toll = max(0, mc - pc)  # toll can't be negative
        tolls[e.id] = toll

    return tolls


def apply_pigouvian_tolls(graph: NetworkGraph) -> Dict[str, float]:
    """
    Compute and apply Pigouvian tolls to the graph edges.
    After applying, solving Nash will yield System Optimum flows.
    Returns the toll values for display.
    """
    tolls = compute_pigouvian_tolls(graph)
    for e in graph.active_edges():
        e.toll = tolls.get(e.id, 0.0)
    return tolls


def sensitivity_analysis(graph: NetworkGraph,
                          demand_range: np.ndarray = None,
                          n_points: int = 50) -> dict:
    """
    Sweep demand from 0.1 to 3.0, compute PoA at each point.
    Returns dict with arrays: demands, poa_values, nash_costs, opt_costs.
    """
    if demand_range is None:
        demand_range = np.linspace(0.1, 3.0, n_points)

    poa_values = []
    nash_costs = []
    opt_costs = []

    for d in demand_range:
        g = graph.clone()
        g.demand = float(d)
        result = compare(g)
        poa_values.append(result.price_of_anarchy)
        nash_costs.append(result.nash.total_cost)
        opt_costs.append(result.optimum.total_cost)

    return {
        'demands': demand_range,
        'poa': np.array(poa_values),
        'nash_costs': np.array(nash_costs),
        'opt_costs': np.array(opt_costs)
    }
