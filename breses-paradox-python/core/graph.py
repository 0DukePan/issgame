"""
═══════════════════════════════════════════════════════════════
 GRAPH DATA MODEL — Braess's Paradox Network Optimizer
═══════════════════════════════════════════════════════════════
 Directed graph with congestion-dependent latency functions.
 Supports linear (ax+b), polynomial (ax²+bx+c), and log forms.
 Uses NumPy for vectorized computation.
"""

from __future__ import annotations
import json
import copy
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import numpy as np


@dataclass
class LatencyFunction:
    """Latency function L(x) on a network edge.

    Supports three types:
    - linear:     L(x) = a*x + b
    - polynomial: L(x) = a*x² + b*x + c
    - log:        L(x) = a*ln(1+x) + b
    """
    type: str = 'linear'
    a: float = 1.0
    b: float = 0.0
    c: float = 0.0

    def cost(self, x: float) -> float:
        """Compute latency at flow x."""
        if self.type == 'polynomial':
            return self.a * x**2 + self.b * x + self.c
        elif self.type == 'log':
            return self.a * np.log(1 + x) + self.b
        else:  # linear
            return self.a * x + self.b

    def cost_vec(self, x: np.ndarray) -> np.ndarray:
        """Vectorized cost computation."""
        if self.type == 'polynomial':
            return self.a * x**2 + self.b * x + self.c
        elif self.type == 'log':
            return self.a * np.log(1 + x) + self.b
        else:
            return self.a * x + self.b

    def marginal_cost(self, x: float) -> float:
        """Marginal cost: d/dx [x * L(x)] for System Optimum."""
        if self.type == 'polynomial':
            return 3 * self.a * x**2 + 2 * self.b * x + self.c
        elif self.type == 'log':
            return self.a * np.log(1 + x) + self.a * x / (1 + x) + self.b
        else:
            return 2 * self.a * x + self.b

    def marginal_cost_vec(self, x: np.ndarray) -> np.ndarray:
        """Vectorized marginal cost."""
        if self.type == 'polynomial':
            return 3 * self.a * x**2 + 2 * self.b * x + self.c
        elif self.type == 'log':
            return self.a * np.log(1 + x) + self.a * x / (1 + x) + self.b
        else:
            return 2 * self.a * x + self.b

    def cost_integral(self, x: float) -> float:
        """∫₀ˣ L(t) dt — for Beckmann objective."""
        if self.type == 'polynomial':
            return (self.a * x**3) / 3 + (self.b * x**2) / 2 + self.c * x
        elif self.type == 'log':
            return self.a * ((1 + x) * np.log(1 + x) - x) + self.b * x
        else:
            return (self.a * x**2) / 2 + self.b * x

    def __str__(self) -> str:
        if self.type == 'polynomial':
            parts = []
            if self.a != 0: parts.append(f"{self.a}x²")
            if self.b != 0: parts.append(f"{'+' if self.b > 0 and parts else ''}{self.b}x")
            if self.c != 0: parts.append(f"{'+' if self.c > 0 and parts else ''}{self.c}")
            return ''.join(parts) or '0'
        elif self.type == 'log':
            parts = []
            if self.a != 0: parts.append(f"{self.a}·ln(1+x)")
            if self.b != 0: parts.append(f"{'+' if self.b > 0 and parts else ''}{self.b}")
            return ''.join(parts) or '0'
        else:
            parts = []
            if self.a != 0: parts.append(f"{self.a}x")
            if self.b != 0: parts.append(f"{'+' if self.b > 0 and parts else ''}{self.b}")
            return ''.join(parts) or '0'

    def to_dict(self) -> dict:
        return {'type': self.type, 'a': self.a, 'b': self.b, 'c': self.c}

    @staticmethod
    def from_dict(d: dict) -> 'LatencyFunction':
        return LatencyFunction(
            type=d.get('type', 'linear'),
            a=d.get('a', 1.0),
            b=d.get('b', 0.0),
            c=d.get('c', 0.0)
        )


@dataclass
class NetworkEdge:
    """A directed edge in the network graph."""
    id: str
    from_node: str
    to_node: str
    latency: LatencyFunction = field(default_factory=LatencyFunction)
    flow: float = 0.0
    is_braess: bool = False
    enabled: bool = True
    label: str = ''

    def total_cost(self) -> float:
        return self.flow * self.latency.cost(self.flow)

    def to_dict(self) -> dict:
        return {
            'from': self.from_node, 'to': self.to_node,
            'latency': self.latency.to_dict(),
            'is_braess': self.is_braess,
            'enabled': self.enabled,
            'label': self.label
        }

    @staticmethod
    def from_dict(d: dict) -> 'NetworkEdge':
        e = NetworkEdge(
            id=f"{d['from']}->{d['to']}",
            from_node=d['from'], to_node=d['to'],
            latency=LatencyFunction.from_dict(d.get('latency', {})),
            is_braess=d.get('is_braess', False),
            enabled=d.get('enabled', True),
            label=d.get('label', '')
        )
        return e


@dataclass
class NetworkNode:
    """A node in the network graph."""
    id: str
    x: float = 0.0
    y: float = 0.0
    label: str = ''

    def to_dict(self) -> dict:
        return {'id': self.id, 'x': self.x, 'y': self.y, 'label': self.label}

    @staticmethod
    def from_dict(d: dict) -> 'NetworkNode':
        return NetworkNode(id=d['id'], x=d.get('x', 0), y=d.get('y', 0),
                           label=d.get('label', d['id']))


class NetworkGraph:
    """Directed graph with congestion-dependent latency functions."""

    def __init__(self):
        self.nodes: Dict[str, NetworkNode] = {}
        self.edges: Dict[str, NetworkEdge] = {}
        self.source: Optional[str] = None
        self.sink: Optional[str] = None
        self.demand: float = 1.0

    def add_node(self, id: str, x: float = 0, y: float = 0,
                 label: str = '') -> NetworkNode:
        node = NetworkNode(id=id, x=x, y=y, label=label or id)
        self.nodes[id] = node
        return node

    def add_edge(self, from_node: str, to_node: str,
                 latency: Optional[LatencyFunction] = None,
                 is_braess: bool = False,
                 label: str = '') -> NetworkEdge:
        if latency is None:
            latency = LatencyFunction()
        edge_id = f"{from_node}->{to_node}"
        edge = NetworkEdge(
            id=edge_id, from_node=from_node, to_node=to_node,
            latency=latency, is_braess=is_braess, label=label
        )
        self.edges[edge_id] = edge
        return edge

    def remove_edge(self, edge_id: str):
        self.edges.pop(edge_id, None)

    def get_edge(self, from_node: str, to_node: str) -> Optional[NetworkEdge]:
        return self.edges.get(f"{from_node}->{to_node}")

    def active_edges(self) -> List[NetworkEdge]:
        return [e for e in self.edges.values() if e.enabled]

    def adjacency(self) -> Dict[str, List[NetworkEdge]]:
        adj: Dict[str, List[NetworkEdge]] = {n: [] for n in self.nodes}
        for e in self.active_edges():
            adj[e.from_node].append(e)
        return adj

    def enumerate_paths(self, src: Optional[str] = None,
                        dst: Optional[str] = None) -> List[List[NetworkEdge]]:
        """Enumerate all simple paths from source to sink (DFS)."""
        src = src or self.source
        dst = dst or self.sink
        if not src or not dst:
            return []

        adj = self.adjacency()
        paths: List[List[NetworkEdge]] = []
        visited = set()

        def dfs(node: str, path: List[NetworkEdge]):
            if node == dst:
                paths.append(list(path))
                return
            visited.add(node)
            for e in adj.get(node, []):
                if e.to_node not in visited:
                    path.append(e)
                    dfs(e.to_node, path)
                    path.pop()
            visited.discard(node)

        dfs(src, [])
        return paths

    def shortest_path(self, cost_fn, src: Optional[str] = None,
                      dst: Optional[str] = None) -> Tuple[List[NetworkEdge], float]:
        """Dijkstra shortest path with custom cost function."""
        src = src or self.source
        dst = dst or self.sink
        if not src or not dst:
            return [], float('inf')

        adj = self.adjacency()
        dist = {n: float('inf') for n in self.nodes}
        prev = {}
        visited = set()
        dist[src] = 0

        while True:
            u, min_d = None, float('inf')
            for n in self.nodes:
                if n not in visited and dist[n] < min_d:
                    u, min_d = n, dist[n]
            if u is None or u == dst:
                break
            visited.add(u)
            for e in adj.get(u, []):
                d = dist[u] + cost_fn(e)
                if d < dist[e.to_node]:
                    dist[e.to_node] = d
                    prev[e.to_node] = e

        if dist[dst] == float('inf'):
            return [], float('inf')

        path = []
        cur = dst
        while cur in prev:
            path.insert(0, prev[cur])
            cur = prev[cur].from_node
        return path, dist[dst]

    def reset_flows(self):
        for e in self.edges.values():
            e.flow = 0.0

    def total_system_cost(self) -> float:
        return sum(e.total_cost() for e in self.active_edges())

    def beckmann_objective(self) -> float:
        return sum(e.latency.cost_integral(e.flow) for e in self.active_edges())

    def clone(self) -> 'NetworkGraph':
        return copy.deepcopy(self)

    def to_dict(self) -> dict:
        return {
            'nodes': [n.to_dict() for n in self.nodes.values()],
            'edges': [e.to_dict() for e in self.edges.values()],
            'source': self.source, 'sink': self.sink,
            'demand': self.demand
        }

    @staticmethod
    def from_dict(d: dict) -> 'NetworkGraph':
        g = NetworkGraph()
        for nd in d.get('nodes', []):
            n = NetworkNode.from_dict(nd)
            g.nodes[n.id] = n
        for ed in d.get('edges', []):
            e = NetworkEdge.from_dict(ed)
            g.edges[e.id] = e
        g.source = d.get('source')
        g.sink = d.get('sink')
        g.demand = d.get('demand', 1.0)
        return g

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    @staticmethod
    def from_json(s: str) -> 'NetworkGraph':
        return NetworkGraph.from_dict(json.loads(s))
