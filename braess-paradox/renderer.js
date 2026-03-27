/**
 * ═══════════════════════════════════════════════════════════════
 *  NETWORK GRAPH RENDERER — Canvas-based visualization
 * ═══════════════════════════════════════════════════════════════
 *  Draws the network graph on a <canvas> element with:
 *  - Glowing nodes with labels
 *  - Curved directed edges with arrowheads
 *  - Edge thickness ∝ flow
 *  - Edge color gradient green→yellow→red by congestion
 *  - Animated particles flowing along edges
 *  - Smooth transitions when flows update
 */

export class NetworkRenderer {
    constructor(canvas) {
        this.canvas = canvas;
        this.ctx = canvas.getContext('2d');
        this.graph = null;
        this.nashFlows = null;
        this.optFlows = null;
        this.displayMode = 'nash'; // 'nash' | 'optimum' | 'both'

        // Animation
        this.particles = [];
        this.animFrame = null;
        this.time = 0;

        // Layout
        this.padding = 60;
        this.nodeRadius = 24;

        // Smooth transition
        this.targetFlows = new Map();
        this.currentFlows = new Map();
        this.transitionSpeed = 0.08;

        this._resize();
        window.addEventListener('resize', () => this._resize());
    }

    _resize() {
        const rect = this.canvas.parentElement.getBoundingClientRect();
        const dpr = window.devicePixelRatio || 1;
        this.canvas.width = rect.width * dpr;
        this.canvas.height = rect.height * dpr;
        this.canvas.style.width = rect.width + 'px';
        this.canvas.style.height = rect.height + 'px';
        this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        this.width = rect.width;
        this.height = rect.height;
    }

    setGraph(graph) {
        this.graph = graph;
        this._scalePositions();
        this.currentFlows.clear();
        this.targetFlows.clear();
        for (const e of graph.edges.values()) {
            this.currentFlows.set(e.id, 0);
            this.targetFlows.set(e.id, 0);
        }
        this._initParticles();
    }

    setFlows(flows, mode = 'nash') {
        this.displayMode = mode;
        if (mode === 'nash') this.nashFlows = flows;
        else this.optFlows = flows;

        for (const [id, f] of flows) {
            this.targetFlows.set(id, f);
        }
    }

    /** Scale node positions from scenario coords to canvas space */
    _scalePositions() {
        if (!this.graph || this.graph.nodes.size === 0) return;

        const nodes = [...this.graph.nodes.values()];
        let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
        for (const n of nodes) {
            minX = Math.min(minX, n.x); maxX = Math.max(maxX, n.x);
            minY = Math.min(minY, n.y); maxY = Math.max(maxY, n.y);
        }

        const w = this.width - this.padding * 2;
        const h = this.height - this.padding * 2;
        const rangeX = maxX - minX || 1;
        const rangeY = maxY - minY || 1;
        const scale = Math.min(w / rangeX, h / rangeY);

        const cx = this.width / 2;
        const cy = this.height / 2;
        const mx = (minX + maxX) / 2;
        const my = (minY + maxY) / 2;

        for (const n of nodes) {
            n._x = cx + (n.x - mx) * scale;
            n._y = cy + (n.y - my) * scale;
        }
    }

    _initParticles() {
        this.particles = [];
    }

    /** Get congestion-based color for a flow value */
    _congestionColor(flow, maxFlow) {
        const ratio = maxFlow > 0 ? Math.min(flow / maxFlow, 1) : 0;
        // Green (0) → Yellow (0.5) → Red (1)
        const r = ratio < 0.5 ? Math.round(ratio * 2 * 255) : 255;
        const g = ratio < 0.5 ? 255 : Math.round((1 - (ratio - 0.5) * 2) * 255);
        const b = 30;
        return `rgb(${r},${g},${b})`;
    }

    _congestionColorAlpha(flow, maxFlow, alpha) {
        const ratio = maxFlow > 0 ? Math.min(flow / maxFlow, 1) : 0;
        const r = ratio < 0.5 ? Math.round(ratio * 2 * 255) : 255;
        const g = ratio < 0.5 ? 255 : Math.round((1 - (ratio - 0.5) * 2) * 255);
        const b = 30;
        return `rgba(${r},${g},${b},${alpha})`;
    }

    /** Main render loop */
    start() {
        const loop = () => {
            this.time += 0.016;
            this._updateTransitions();
            this._draw();
            this.animFrame = requestAnimationFrame(loop);
        };
        loop();
    }

    stop() {
        if (this.animFrame) cancelAnimationFrame(this.animFrame);
    }

    _updateTransitions() {
        for (const [id, target] of this.targetFlows) {
            const current = this.currentFlows.get(id) || 0;
            const diff = target - current;
            this.currentFlows.set(id, current + diff * this.transitionSpeed);
        }
    }

    _draw() {
        const ctx = this.ctx;
        const w = this.width;
        const h = this.height;

        // Clear
        ctx.clearRect(0, 0, w, h);

        // Background grid
        this._drawGrid(ctx, w, h);

        if (!this.graph) return;

        const maxFlow = Math.max(0.01, ...this.currentFlows.values());

        // Draw edges
        for (const e of this.graph.edges.values()) {
            if (!e.enabled) continue;
            const fromNode = this.graph.nodes.get(e.from);
            const toNode = this.graph.nodes.get(e.to);
            if (!fromNode || !toNode) continue;

            const flow = this.currentFlows.get(e.id) || 0;
            this._drawEdge(ctx, fromNode, toNode, e, flow, maxFlow);
        }

        // Draw particles
        this._drawParticles(ctx);

        // Draw nodes
        for (const n of this.graph.nodes.values()) {
            this._drawNode(ctx, n);
        }
    }

    _drawGrid(ctx, w, h) {
        ctx.strokeStyle = 'rgba(148,163,184,0.04)';
        ctx.lineWidth = 1;
        const step = 40;
        for (let x = 0; x < w; x += step) {
            ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke();
        }
        for (let y = 0; y < h; y += step) {
            ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke();
        }
    }

    _drawEdge(ctx, from, to, edge, flow, maxFlow) {
        const x1 = from._x, y1 = from._y;
        const x2 = to._x, y2 = to._y;

        // Compute a curve control point (slight offset for aesthetics)
        const mx = (x1 + x2) / 2;
        const my = (y1 + y2) / 2;
        const dx = x2 - x1, dy = y2 - y1;
        const len = Math.sqrt(dx * dx + dy * dy);
        const nx = -dy / len, ny = dx / len;

        // Check if there's a reverse edge → curve more
        const reverseId = `${edge.to}->${edge.from}`;
        const hasReverse = this.graph.edges.has(reverseId);
        const curveAmount = hasReverse ? 30 : 15;

        const cpx = mx + nx * curveAmount;
        const cpy = my + ny * curveAmount;

        // Line width based on flow
        const baseWidth = 2;
        const flowWidth = baseWidth + flow / maxFlow * 8;

        // Color
        const color = edge.isBraess
            ? `rgba(251,191,36,${0.4 + flow / maxFlow * 0.6})`
            : this._congestionColor(flow, maxFlow);

        // Glow
        ctx.save();
        ctx.shadowColor = edge.isBraess ? 'rgba(251,191,36,0.3)' : this._congestionColorAlpha(flow, maxFlow, 0.3);
        ctx.shadowBlur = flow > 0 ? 12 : 0;

        // Draw curve
        ctx.beginPath();
        ctx.moveTo(x1, y1);
        ctx.quadraticCurveTo(cpx, cpy, x2, y2);
        ctx.strokeStyle = color;
        ctx.lineWidth = flowWidth;
        ctx.lineCap = 'round';
        ctx.stroke();
        ctx.restore();

        // Arrowhead
        this._drawArrowhead(ctx, cpx, cpy, x2, y2, color, flowWidth);

        // Edge label (latency function + flow)
        this._drawEdgeLabel(ctx, cpx, cpy, edge, flow);

        // Spawn particles
        if (flow > 0.01) {
            const particleRate = Math.ceil(flow / maxFlow * 3);
            if (Math.random() < particleRate * 0.05) {
                this.particles.push({
                    x: x1, y: y1,
                    x1, y1, cpx, cpy, x2, y2,
                    t: 0,
                    speed: 0.008 + Math.random() * 0.008,
                    color,
                    size: 2 + flow / maxFlow * 3,
                    isBraess: edge.isBraess
                });
            }
        }
    }

    _drawArrowhead(ctx, cpx, cpy, x2, y2, color, lineWidth) {
        const angle = Math.atan2(y2 - cpy, x2 - cpx);
        const arrowLen = 10 + lineWidth;
        const arrowAngle = 0.4;

        // Pull back from node center
        const pullback = this.nodeRadius + 4;
        const tipX = x2 - Math.cos(angle) * pullback;
        const tipY = y2 - Math.sin(angle) * pullback;

        ctx.save();
        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.moveTo(tipX, tipY);
        ctx.lineTo(
            tipX - arrowLen * Math.cos(angle - arrowAngle),
            tipY - arrowLen * Math.sin(angle - arrowAngle)
        );
        ctx.lineTo(
            tipX - arrowLen * Math.cos(angle + arrowAngle),
            tipY - arrowLen * Math.sin(angle + arrowAngle)
        );
        ctx.closePath();
        ctx.fill();
        ctx.restore();
    }

    _drawEdgeLabel(ctx, cx, cy, edge, flow) {
        ctx.save();
        ctx.font = '500 11px "JetBrains Mono", monospace';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';

        // Background
        const label = edge.latencyString();
        const flowText = `f=${flow.toFixed(2)}`;
        const fullText = `${label}  │  ${flowText}`;
        const metrics = ctx.measureText(fullText);
        const tw = metrics.width + 12;
        const th = 18;

        ctx.fillStyle = 'rgba(10,14,26,0.85)';
        ctx.beginPath();
        ctx.roundRect(cx - tw / 2, cy - th / 2 - 12, tw, th, 4);
        ctx.fill();

        // Text
        ctx.fillStyle = edge.isBraess ? '#fbbf24' : '#94a3b8';
        ctx.fillText(fullText, cx, cy - 12);
        ctx.restore();
    }

    _drawParticles(ctx) {
        const alive = [];
        for (const p of this.particles) {
            p.t += p.speed;
            if (p.t > 1) continue;

            // Quadratic Bezier interpolation
            const t = p.t;
            const mt = 1 - t;
            p.x = mt * mt * p.x1 + 2 * mt * t * p.cpx + t * t * p.x2;
            p.y = mt * mt * p.y1 + 2 * mt * t * p.cpy + t * t * p.y2;

            ctx.save();
            ctx.shadowColor = p.isBraess ? 'rgba(251,191,36,0.6)' : p.color;
            ctx.shadowBlur = 8;
            ctx.fillStyle = p.isBraess ? '#fbbf24' : '#ffffff';
            ctx.globalAlpha = 1 - t * 0.5;
            ctx.beginPath();
            ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
            ctx.fill();
            ctx.restore();

            alive.push(p);
        }
        this.particles = alive;
        // Cap particles
        if (this.particles.length > 200) {
            this.particles = this.particles.slice(-200);
        }
    }

    _drawNode(ctx, node) {
        const x = node._x, y = node._y;
        const r = this.nodeRadius;

        // Determine node color
        const isSource = node.id === this.graph.source;
        const isSink = node.id === this.graph.sink;
        const baseColor = isSource ? '#6ee7b7' : isSink ? '#f87171' : '#818cf8';
        const glowColor = isSource ? 'rgba(110,231,183,0.3)' : isSink ? 'rgba(248,113,113,0.3)' : 'rgba(129,140,248,0.3)';

        // Outer glow
        ctx.save();
        ctx.shadowColor = glowColor;
        ctx.shadowBlur = 20 + Math.sin(this.time * 2 + x) * 5;

        // Circle fill
        const grad = ctx.createRadialGradient(x, y, 0, x, y, r);
        grad.addColorStop(0, baseColor);
        grad.addColorStop(1, 'rgba(26,34,53,0.9)');
        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.arc(x, y, r, 0, Math.PI * 2);
        ctx.fill();

        // Border
        ctx.strokeStyle = baseColor;
        ctx.lineWidth = 2;
        ctx.stroke();
        ctx.restore();

        // Label
        ctx.save();
        ctx.font = '700 14px Inter, sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillStyle = '#ffffff';
        ctx.fillText(node.label.replace(' (Source)', '').replace(' (Sink)', ''), x, y);

        // Sub-label (source/sink)
        if (isSource || isSink) {
            ctx.font = '500 9px Inter, sans-serif';
            ctx.fillStyle = baseColor;
            ctx.fillText(isSource ? 'SOURCE' : 'SINK', x, y + r + 14);
        }
        ctx.restore();
    }
}
