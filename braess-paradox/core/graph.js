/**
 * ═══════════════════════════════════════════════════════════════
 *  GRAPH DATA MODEL — Braess's Paradox Network Optimizer
 * ═══════════════════════════════════════════════════════════════
 *  Directed graph with congestion-dependent latency functions.
 *  Supports linear (ax+b), polynomial (ax²+bx+c), and log latency.
 */

export class Edge {
  /**
   * @param {string} from  - Source node ID
   * @param {string} to    - Target node ID
   * @param {object} latency - {type:'linear'|'polynomial'|'log', a, b, c?}
   * @param {object} opts  - {isBraess, label}
   */
  constructor(from, to, latency = { type: 'linear', a: 1, b: 0 }, opts = {}) {
    this.id = `${from}->${to}`;
    this.from = from;
    this.to = to;
    this.latency = { type: 'linear', a: 1, b: 0, c: 0, ...latency };
    this.flow = 0;
    this.isBraess = opts.isBraess || false;
    this.enabled = true;
    this.label = opts.label || '';
  }

  /** Compute latency given flow x */
  cost(x = this.flow) {
    const { type, a, b, c } = this.latency;
    switch (type) {
      case 'polynomial': return a * x * x + b * x + (c || 0);
      case 'log':        return a * Math.log(1 + x) + b;
      case 'linear':
      default:           return a * x + b;
    }
  }

  /** Marginal cost for System Optimum: d/dx [x * l(x)] */
  marginalCost(x = this.flow) {
    const { type, a, b, c } = this.latency;
    switch (type) {
      case 'polynomial': return 3 * a * x * x + 2 * b * x + (c || 0);
      case 'log':        return a * Math.log(1 + x) + a * x / (1 + x) + b;
      case 'linear':
      default:           return 2 * a * x + b;
    }
  }

  /** Integral of latency ∫₀ˣ l(t)dt — for Beckmann objective */
  costIntegral(x = this.flow) {
    const { type, a, b, c } = this.latency;
    switch (type) {
      case 'polynomial': return (a * x * x * x) / 3 + (b * x * x) / 2 + (c || 0) * x;
      case 'log':        return a * ((1 + x) * Math.log(1 + x) - x) + b * x;
      case 'linear':
      default:           return (a * x * x) / 2 + b * x;
    }
  }

  /** Total cost on this edge: x * l(x) */
  totalCost(x = this.flow) {
    return x * this.cost(x);
  }

  /** Latency function as human-readable string */
  latencyString() {
    const { type, a, b, c } = this.latency;
    switch (type) {
      case 'polynomial': {
        const parts = [];
        if (a !== 0) parts.push(`${a}x²`);
        if (b !== 0) parts.push(`${b > 0 && parts.length ? '+' : ''}${b}x`);
        if (c)       parts.push(`${c > 0 && parts.length ? '+' : ''}${c}`);
        return parts.join('') || '0';
      }
      case 'log': {
        const parts = [];
        if (a !== 0) parts.push(`${a}·ln(1+x)`);
        if (b !== 0) parts.push(`${b > 0 && parts.length ? '+' : ''}${b}`);
        return parts.join('') || '0';
      }
      case 'linear':
      default: {
        const parts = [];
        if (a !== 0) parts.push(`${a}x`);
        if (b !== 0) parts.push(`${b > 0 && parts.length ? '+' : ''}${b}`);
        return parts.join('') || '0';
      }
    }
  }

  toJSON() {
    return {
      from: this.from, to: this.to,
      latency: { ...this.latency },
      isBraess: this.isBraess,
      enabled: this.enabled,
      label: this.label
    };
  }

  static fromJSON(j) {
    const e = new Edge(j.from, j.to, j.latency, { isBraess: j.isBraess, label: j.label });
    e.enabled = j.enabled !== false;
    return e;
  }
}


export class Graph {
  constructor() {
    /** @type {Map<string, {id:string, x:number, y:number, label:string}>} */
    this.nodes = new Map();
    /** @type {Map<string, Edge>} */
    this.edges = new Map();
    this.source = null;
    this.sink = null;
    this.demand = 1;
  }

  addNode(id, x = 0, y = 0, label = '') {
    this.nodes.set(id, { id, x, y, label: label || id });
    return this;
  }

  addEdge(from, to, latency, opts) {
    const e = new Edge(from, to, latency, opts);
    this.edges.set(e.id, e);
    return e;
  }

  removeEdge(id) {
    this.edges.delete(id);
  }

  getEdge(from, to) {
    return this.edges.get(`${from}->${to}`);
  }

  /** Get all enabled edges */
  activeEdges() {
    return [...this.edges.values()].filter(e => e.enabled);
  }

  /** Adjacency list for active edges */
  adjacency() {
    const adj = {};
    for (const n of this.nodes.keys()) adj[n] = [];
    for (const e of this.activeEdges()) {
      adj[e.from].push(e);
    }
    return adj;
  }

  /** Enumerate all simple paths from source to sink (DFS) */
  enumeratePaths(src = this.source, dst = this.sink) {
    const adj = this.adjacency();
    const paths = [];
    const visited = new Set();

    const dfs = (node, path) => {
      if (node === dst) { paths.push([...path]); return; }
      visited.add(node);
      for (const e of (adj[node] || [])) {
        if (!visited.has(e.to)) {
          path.push(e);
          dfs(e.to, path);
          path.pop();
        }
      }
      visited.delete(node);
    };

    dfs(src, []);
    return paths;
  }

  /** Shortest path using Dijkstra with a custom cost function */
  shortestPath(costFn, src = this.source, dst = this.sink) {
    const dist = {};
    const prev = {};
    const visited = new Set();
    const adj = this.adjacency();

    for (const n of this.nodes.keys()) dist[n] = Infinity;
    dist[src] = 0;

    while (true) {
      let u = null, minD = Infinity;
      for (const n of this.nodes.keys()) {
        if (!visited.has(n) && dist[n] < minD) { u = n; minD = dist[n]; }
      }
      if (u === null || u === dst) break;
      visited.add(u);

      for (const e of (adj[u] || [])) {
        const d = dist[u] + costFn(e);
        if (d < dist[e.to]) {
          dist[e.to] = d;
          prev[e.to] = e;
        }
      }
    }

    // Reconstruct path
    if (dist[dst] === Infinity) return { path: [], cost: Infinity };
    const path = [];
    let cur = dst;
    while (prev[cur]) {
      path.unshift(prev[cur]);
      cur = prev[cur].from;
    }
    return { path, cost: dist[dst] };
  }

  /** Reset all flows to 0 */
  resetFlows() {
    for (const e of this.edges.values()) e.flow = 0;
  }

  /** Total system cost: Σ xₑ · lₑ(xₑ) */
  totalSystemCost() {
    let c = 0;
    for (const e of this.activeEdges()) c += e.totalCost();
    return c;
  }

  /** Beckmann objective: Σ ∫₀ˣₑ lₑ(t)dt */
  beckmannObjective() {
    let b = 0;
    for (const e of this.activeEdges()) b += e.costIntegral();
    return b;
  }

  /** Deep clone */
  clone() {
    const g = new Graph();
    for (const [id, n] of this.nodes) g.nodes.set(id, { ...n });
    for (const [id, e] of this.edges) {
      const ne = Edge.fromJSON(e.toJSON());
      ne.flow = e.flow;
      g.edges.set(id, ne);
    }
    g.source = this.source;
    g.sink = this.sink;
    g.demand = this.demand;
    return g;
  }

  toJSON() {
    return {
      nodes: [...this.nodes.values()],
      edges: [...this.edges.values()].map(e => e.toJSON()),
      source: this.source,
      sink: this.sink,
      demand: this.demand
    };
  }

  static fromJSON(j) {
    const g = new Graph();
    for (const n of j.nodes) g.addNode(n.id, n.x, n.y, n.label);
    for (const ej of j.edges) {
      const e = Edge.fromJSON(ej);
      g.edges.set(e.id, e);
    }
    g.source = j.source;
    g.sink = j.sink;
    g.demand = j.demand || 1;
    return g;
  }
}
