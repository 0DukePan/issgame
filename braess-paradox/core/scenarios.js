/**
 * ═══════════════════════════════════════════════════════════════
 *  PRESET SCENARIOS
 * ═══════════════════════════════════════════════════════════════
 *  Classic network configurations for demonstrating game theory.
 */

import { Graph } from './graph.js';

/**
 * Classic Braess Network (4-node diamond)
 *
 *       A ──→ C ──→ B
 *       │     ↕     ↑
 *       └──→ D ──→──┘
 *
 * Without Braess edge C→D: Nash cost = 1.5, each path gets 0.5
 * With Braess edge C→D (cost=0): Nash cost = 2.0 (WORSE!)
 */
export function classicBraess() {
    const g = new Graph();

    g.addNode('A', 100, 300, 'A (Source)');
    g.addNode('C', 400, 100, 'C');
    g.addNode('D', 400, 500, 'D');
    g.addNode('B', 700, 300, 'B (Sink)');

    // Top path: A→C (congestion) then C→B (constant)
    g.addEdge('A', 'C', { type: 'linear', a: 1, b: 0 }, { label: 'L(x) = x' });
    g.addEdge('C', 'B', { type: 'linear', a: 0, b: 1 }, { label: 'L(x) = 1' });

    // Bottom path: A→D (constant) then D→B (congestion)
    g.addEdge('A', 'D', { type: 'linear', a: 0, b: 1 }, { label: 'L(x) = 1' });
    g.addEdge('D', 'B', { type: 'linear', a: 1, b: 0 }, { label: 'L(x) = x' });

    // Braess edge: C→D (zero cost shortcut!)
    g.addEdge('C', 'D', { type: 'linear', a: 0, b: 0 }, {
        isBraess: true,
        label: 'L(x) = 0 ⚡'
    });

    g.source = 'A';
    g.sink = 'B';
    g.demand = 1;

    return g;
}

/**
 * Pigou's Example (2-node, 2-link)
 *
 *  A ═══► B
 *  Path 1: L(x) = x
 *  Path 2: L(x) = 1
 *
 * Nash: all traffic on path 1 → cost = 1
 * Optimum: split traffic → lower total cost
 */
export function pigouNetwork() {
    const g = new Graph();

    g.addNode('A', 150, 300, 'A (Source)');
    g.addNode('B', 650, 300, 'B (Sink)');

    g.addEdge('A', 'B', { type: 'linear', a: 1, b: 0 }, { label: 'L(x) = x (fast but congests)' });

    // We need a relay node for the second path to visualize two distinct paths
    g.addNode('M', 400, 150, 'M');
    g.addEdge('A', 'M', { type: 'linear', a: 0, b: 0.5 }, { label: 'L(x) = 0.5' });
    g.addEdge('M', 'B', { type: 'linear', a: 0, b: 0.5 }, { label: 'L(x) = 0.5' });

    g.source = 'A';
    g.sink = 'B';
    g.demand = 1;

    return g;
}


/**
 * Extended Network (6-node mesh)
 * More complex scenario with multiple paths and a Braess edge
 *
 *    A → E → C → B
 *    ↓ ↘   ↕   ↗ ↑
 *    F → D → ────┘
 */
export function meshNetwork() {
    const g = new Graph();

    g.addNode('A', 80, 300, 'A (Source)');
    g.addNode('E', 280, 130, 'E');
    g.addNode('F', 280, 470, 'F');
    g.addNode('C', 500, 130, 'C');
    g.addNode('D', 500, 470, 'D');
    g.addNode('B', 720, 300, 'B (Sink)');

    // Upper path
    g.addEdge('A', 'E', { type: 'linear', a: 1, b: 0 }, { label: 'L = x' });
    g.addEdge('E', 'C', { type: 'linear', a: 0.5, b: 0.5 }, { label: 'L = 0.5x+0.5' });
    g.addEdge('C', 'B', { type: 'linear', a: 0, b: 1 }, { label: 'L = 1' });

    // Lower path
    g.addEdge('A', 'F', { type: 'linear', a: 0, b: 1 }, { label: 'L = 1' });
    g.addEdge('F', 'D', { type: 'linear', a: 0.5, b: 0.5 }, { label: 'L = 0.5x+0.5' });
    g.addEdge('D', 'B', { type: 'linear', a: 1, b: 0 }, { label: 'L = x' });

    // Cross links
    g.addEdge('A', 'D', { type: 'linear', a: 0.8, b: 0.2 }, { label: 'L = 0.8x+0.2' });
    g.addEdge('E', 'B', { type: 'linear', a: 0.8, b: 0.5 }, { label: 'L = 0.8x+0.5' });

    // Braess edge
    g.addEdge('C', 'D', { type: 'linear', a: 0, b: 0 }, {
        isBraess: true,
        label: 'L = 0 ⚡'
    });

    g.source = 'A';
    g.sink = 'B';
    g.demand = 1;

    return g;
}


/** Return all presets as a dictionary */
export const SCENARIOS = {
    braess: {
        name: "Classic Braess's Paradox",
        description: "The canonical 4-node diamond network. Adding a zero-cost shortcut C→D worsens total latency from 1.5 to 2.0 — a 33% increase!",
        create: classicBraess
    },
    pigou: {
        name: "Pigou's Example",
        description: "The simplest demonstration of selfish routing inefficiency: 2 parallel paths from A to B.",
        create: pigouNetwork
    },
    mesh: {
        name: "6-Node Mesh Network",
        description: "A more complex network with multiple paths, cross links, and a Braess edge.",
        create: meshNetwork
    }
};
