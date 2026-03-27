"""
═══════════════════════════════════════════════════════════════
 PRESET SCENARIOS — Classic Game Theory Networks
═══════════════════════════════════════════════════════════════
"""

from .graph import NetworkGraph, LatencyFunction


def classic_braess() -> NetworkGraph:
    """
    Classic Braess Network (4-node diamond).

         A ──→ C ──→ B
         │     ↕     ↑
         └──→ D ──→──┘

    Without Braess edge C→D:
      Nash: 0.5 on each path, total cost = 1.5
    With Braess edge C→D (cost=0):
      Nash: all traffic on A→C→D→B, total cost = 2.0 (33% worse!)
    """
    g = NetworkGraph()

    g.add_node('A', 100, 300, 'A (Source)')
    g.add_node('C', 400, 100, 'C')
    g.add_node('D', 400, 500, 'D')
    g.add_node('B', 700, 300, 'B (Sink)')

    # Top path: A→C (congestion) then C→B (constant)
    g.add_edge('A', 'C', LatencyFunction('linear', a=1, b=0), label='L(x) = x')
    g.add_edge('C', 'B', LatencyFunction('linear', a=0, b=1), label='L(x) = 1')

    # Bottom path: A→D (constant) then D→B (congestion)
    g.add_edge('A', 'D', LatencyFunction('linear', a=0, b=1), label='L(x) = 1')
    g.add_edge('D', 'B', LatencyFunction('linear', a=1, b=0), label='L(x) = x')

    # Braess edge: C→D (zero cost shortcut!)
    g.add_edge('C', 'D', LatencyFunction('linear', a=0, b=0),
               is_braess=True, label='L(x) = 0 ⚡')

    g.source = 'A'
    g.sink = 'B'
    g.demand = 1.0
    return g


def pigou_network() -> NetworkGraph:
    """
    Pigou's Example.

      A ═══► B  (two parallel paths)
      Path 1: L(x) = x   (congests)
      Path 2: L(x) = 1   (constant)

    Nash: all traffic on path 1 (it's faster until congested)
    Optimum: split traffic for lower total cost
    """
    g = NetworkGraph()

    g.add_node('A', 150, 300, 'A (Source)')
    g.add_node('B', 650, 300, 'B (Sink)')
    g.add_node('M', 400, 150, 'M')

    # Direct path (congests)
    g.add_edge('A', 'B', LatencyFunction('linear', a=1, b=0),
               label='L(x) = x')
    # Relay path (constant)
    g.add_edge('A', 'M', LatencyFunction('linear', a=0, b=0.5),
               label='L(x) = 0.5')
    g.add_edge('M', 'B', LatencyFunction('linear', a=0, b=0.5),
               label='L(x) = 0.5')

    g.source = 'A'
    g.sink = 'B'
    g.demand = 1.0
    return g


def mesh_network() -> NetworkGraph:
    """
    6-Node Mesh Network with multiple paths and a Braess edge.

       A → E → C → B
       ↓ ↘   ↕   ↗ ↑
       F → D → ────┘
    """
    g = NetworkGraph()

    g.add_node('A', 80,  300, 'A (Source)')
    g.add_node('E', 280, 130, 'E')
    g.add_node('F', 280, 470, 'F')
    g.add_node('C', 500, 130, 'C')
    g.add_node('D', 500, 470, 'D')
    g.add_node('B', 720, 300, 'B (Sink)')

    g.add_edge('A', 'E', LatencyFunction('linear', a=1, b=0),      label='L = x')
    g.add_edge('E', 'C', LatencyFunction('linear', a=0.5, b=0.5),  label='L = 0.5x+0.5')
    g.add_edge('C', 'B', LatencyFunction('linear', a=0, b=1),      label='L = 1')

    g.add_edge('A', 'F', LatencyFunction('linear', a=0, b=1),      label='L = 1')
    g.add_edge('F', 'D', LatencyFunction('linear', a=0.5, b=0.5),  label='L = 0.5x+0.5')
    g.add_edge('D', 'B', LatencyFunction('linear', a=1, b=0),      label='L = x')

    g.add_edge('A', 'D', LatencyFunction('linear', a=0.8, b=0.2),  label='L = 0.8x+0.2')
    g.add_edge('E', 'B', LatencyFunction('linear', a=0.8, b=0.5),  label='L = 0.8x+0.5')

    # Braess edge
    g.add_edge('C', 'D', LatencyFunction('linear', a=0, b=0),
               is_braess=True, label='L = 0 ⚡')

    g.source = 'A'
    g.sink = 'B'
    g.demand = 1.0
    return g


SCENARIOS = {
    'braess': {
        'name': "Classic Braess's Paradox",
        'description': "The canonical 4-node diamond network. Adding a zero-cost "
                       "shortcut C→D worsens total latency from 1.5 to 2.0 — a 33% increase!",
        'create': classic_braess
    },
    'pigou': {
        'name': "Pigou's Example",
        'description': "The simplest demonstration of selfish routing inefficiency: "
                       "two parallel paths, one congests and one is constant.",
        'create': pigou_network
    },
    'mesh': {
        'name': "6-Node Mesh Network",
        'description': "A more complex network with multiple paths, cross links, "
                       "and a Braess edge for advanced analysis.",
        'create': mesh_network
    }
}
