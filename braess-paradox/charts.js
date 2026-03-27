/**
 * ═══════════════════════════════════════════════════════════════
 *  CHARTS — Custom Canvas Charts
 * ═══════════════════════════════════════════════════════════════
 *  - Flow comparison bar chart (Nash vs Optimum per edge)
 *  - Price of Anarchy gauge
 *  - Convergence line chart
 */

export class Charts {
    constructor() {
        this.flowCanvas = document.getElementById('flow-chart');
        this.flowCtx = this.flowCanvas ? this.flowCanvas.getContext('2d') : null;

        this.poaCanvas = document.getElementById('poa-canvas');
        this.poaCtx = this.poaCanvas ? this.poaCanvas.getContext('2d') : null;

        this.convCanvas = document.getElementById('convergence-chart');
        this.convCtx = this.convCanvas ? this.convCanvas.getContext('2d') : null;

        this._setupHiDPI(this.flowCanvas, this.flowCtx);
        this._setupHiDPI(this.poaCanvas, this.poaCtx);
        this._setupHiDPI(this.convCanvas, this.convCtx);
    }

    _setupHiDPI(canvas, ctx) {
        if (!canvas || !ctx) return;
        const dpr = window.devicePixelRatio || 1;
        const rect = canvas.getBoundingClientRect();
        canvas.width = rect.width * dpr;
        canvas.height = rect.height * dpr;
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        canvas._w = rect.width;
        canvas._h = rect.height;
    }

    /** ── Flow Comparison Bar Chart ── */
    drawFlowChart(nashFlows, optFlows, edges) {
        const ctx = this.flowCtx;
        const canvas = this.flowCanvas;
        if (!ctx || !canvas) return;

        const w = canvas._w;
        const h = canvas._h;
        ctx.clearRect(0, 0, w, h);

        const activeEdges = edges.filter(e => e.enabled);
        if (activeEdges.length === 0) return;

        const pad = { top: 20, bottom: 30, left: 10, right: 10 };
        const chartW = w - pad.left - pad.right;
        const chartH = h - pad.top - pad.bottom;

        const groupWidth = chartW / activeEdges.length;
        const barWidth = groupWidth * 0.35;
        const gap = groupWidth * 0.05;

        const maxFlow = Math.max(0.01,
            ...activeEdges.map(e => Math.max(nashFlows.get(e.id) || 0, optFlows.get(e.id) || 0))
        );

        activeEdges.forEach((edge, i) => {
            const x = pad.left + i * groupWidth;
            const nashF = nashFlows.get(edge.id) || 0;
            const optF = optFlows.get(edge.id) || 0;

            // Nash bar
            const nashH = (nashF / maxFlow) * chartH;
            const nashGrad = ctx.createLinearGradient(0, pad.top + chartH - nashH, 0, pad.top + chartH);
            nashGrad.addColorStop(0, '#f87171');
            nashGrad.addColorStop(1, 'rgba(248,113,113,0.3)');
            ctx.fillStyle = nashGrad;
            this._roundedRect(ctx,
                x + gap, pad.top + chartH - nashH,
                barWidth, nashH, 3
            );

            // Optimum bar
            const optH = (optF / maxFlow) * chartH;
            const optGrad = ctx.createLinearGradient(0, pad.top + chartH - optH, 0, pad.top + chartH);
            optGrad.addColorStop(0, '#34d399');
            optGrad.addColorStop(1, 'rgba(52,211,153,0.3)');
            ctx.fillStyle = optGrad;
            this._roundedRect(ctx,
                x + gap + barWidth + gap, pad.top + chartH - optH,
                barWidth, optH, 3
            );

            // Value labels
            ctx.font = '500 9px "JetBrains Mono", monospace';
            ctx.textAlign = 'center';
            if (nashF > 0.005) {
                ctx.fillStyle = '#f87171';
                ctx.fillText(nashF.toFixed(2), x + gap + barWidth / 2, pad.top + chartH - nashH - 4);
            }
            if (optF > 0.005) {
                ctx.fillStyle = '#34d399';
                ctx.fillText(optF.toFixed(2), x + gap * 2 + barWidth * 1.5, pad.top + chartH - optH - 4);
            }

            // Edge label
            ctx.fillStyle = '#64748b';
            ctx.font = '500 9px "JetBrains Mono", monospace';
            ctx.fillText(
                edge.from + '→' + edge.to,
                x + groupWidth / 2,
                h - 8
            );
        });

        // Legend
        ctx.font = '500 10px Inter, sans-serif';
        ctx.fillStyle = '#f87171';
        ctx.fillRect(w - 100, 6, 10, 10);
        ctx.fillText('Nash', w - 86, 14);
        ctx.fillStyle = '#34d399';
        ctx.fillRect(w - 50, 6, 10, 10);
        ctx.fillText('Opt', w - 36, 14);
    }

    _roundedRect(ctx, x, y, w, h, r) {
        if (h <= 0) return;
        ctx.beginPath();
        ctx.moveTo(x + r, y);
        ctx.lineTo(x + w - r, y);
        ctx.quadraticCurveTo(x + w, y, x + w, y + r);
        ctx.lineTo(x + w, y + h);
        ctx.lineTo(x, y + h);
        ctx.lineTo(x, y + r);
        ctx.quadraticCurveTo(x, y, x + r, y);
        ctx.closePath();
        ctx.fill();
    }

    /** ── Price of Anarchy Gauge ── */
    drawPoAGauge(poa) {
        const ctx = this.poaCtx;
        const canvas = this.poaCanvas;
        if (!ctx || !canvas) return;

        const w = canvas._w;
        const h = canvas._h;
        ctx.clearRect(0, 0, w, h);

        const cx = w / 2;
        const cy = h - 10;
        const radius = Math.min(w, h) - 30;

        const startAngle = Math.PI;
        const endAngle = 2 * Math.PI;

        // Background arc
        ctx.beginPath();
        ctx.arc(cx, cy, radius, startAngle, endAngle);
        ctx.strokeStyle = 'rgba(148,163,184,0.1)';
        ctx.lineWidth = 16;
        ctx.lineCap = 'round';
        ctx.stroke();

        // Value arc
        const clampedPoa = Math.min(Math.max(poa, 1), 2.5);
        const fraction = (clampedPoa - 1) / 1.5; // 1.0→0, 2.5→1
        const valueAngle = startAngle + fraction * Math.PI;

        // Gradient for the arc
        const grad = ctx.createLinearGradient(cx - radius, cy, cx + radius, cy);
        grad.addColorStop(0, '#34d399');
        grad.addColorStop(0.4, '#fbbf24');
        grad.addColorStop(1, '#ef4444');

        ctx.beginPath();
        ctx.arc(cx, cy, radius, startAngle, valueAngle);
        ctx.strokeStyle = grad;
        ctx.lineWidth = 16;
        ctx.lineCap = 'round';
        ctx.stroke();

        // Tick marks
        ctx.font = '500 9px "JetBrains Mono", monospace';
        ctx.textAlign = 'center';
        ctx.fillStyle = '#64748b';
        const ticks = [1.0, 1.25, 1.5, 1.75, 2.0, 2.5];
        for (const t of ticks) {
            const frac = (t - 1) / 1.5;
            const angle = startAngle + frac * Math.PI;
            const tx = cx + (radius + 16) * Math.cos(angle);
            const ty = cy + (radius + 16) * Math.sin(angle);
            ctx.fillText(t.toFixed(t === 1 || t === 2 ? 1 : 2), tx, ty);
        }

        // Needle
        const needleAngle = startAngle + fraction * Math.PI;
        const needleLen = radius - 10;
        ctx.save();
        ctx.strokeStyle = '#f1f5f9';
        ctx.lineWidth = 2;
        ctx.shadowColor = 'rgba(241,245,249,0.4)';
        ctx.shadowBlur = 8;
        ctx.beginPath();
        ctx.moveTo(cx, cy);
        ctx.lineTo(
            cx + needleLen * Math.cos(needleAngle),
            cy + needleLen * Math.sin(needleAngle)
        );
        ctx.stroke();
        ctx.restore();

        // Center dot
        ctx.fillStyle = '#f1f5f9';
        ctx.beginPath();
        ctx.arc(cx, cy, 5, 0, Math.PI * 2);
        ctx.fill();
    }

    /** ── Convergence Line Chart ── */
    drawConvergenceChart(iterations) {
        const ctx = this.convCtx;
        const canvas = this.convCanvas;
        if (!ctx || !canvas) return;

        const w = canvas._w;
        const h = canvas._h;
        ctx.clearRect(0, 0, w, h);

        if (!iterations || iterations.length === 0) return;

        const pad = { top: 15, bottom: 20, left: 35, right: 10 };
        const chartW = w - pad.left - pad.right;
        const chartH = h - pad.top - pad.bottom;

        const gaps = iterations.map(it => it.gap > 0 ? Math.log10(it.gap) : -8);
        const minG = Math.min(...gaps, -7);
        const maxG = Math.max(...gaps, 0);
        const rangeG = maxG - minG || 1;

        // Grid lines
        ctx.strokeStyle = 'rgba(148,163,184,0.08)';
        ctx.lineWidth = 1;
        for (let i = 0; i <= 4; i++) {
            const y = pad.top + (chartH / 4) * i;
            ctx.beginPath(); ctx.moveTo(pad.left, y); ctx.lineTo(w - pad.right, y); ctx.stroke();
        }

        // Line
        ctx.beginPath();
        iterations.forEach((it, i) => {
            const x = pad.left + (i / Math.max(iterations.length - 1, 1)) * chartW;
            const y = pad.top + chartH - ((gaps[i] - minG) / rangeG) * chartH;
            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        });
        ctx.strokeStyle = '#818cf8';
        ctx.lineWidth = 2;
        ctx.stroke();

        // Fill area
        const lastX = pad.left + chartW;
        ctx.lineTo(lastX, pad.top + chartH);
        ctx.lineTo(pad.left, pad.top + chartH);
        ctx.closePath();
        const fillGrad = ctx.createLinearGradient(0, pad.top, 0, pad.top + chartH);
        fillGrad.addColorStop(0, 'rgba(129,140,248,0.2)');
        fillGrad.addColorStop(1, 'rgba(129,140,248,0)');
        ctx.fillStyle = fillGrad;
        ctx.fill();

        // Y axis label
        ctx.save();
        ctx.font = '500 8px Inter, sans-serif';
        ctx.fillStyle = '#64748b';
        ctx.textAlign = 'right';
        ctx.fillText('log(gap)', pad.left - 4, pad.top + 4);

        // X axis label
        ctx.textAlign = 'center';
        ctx.fillText('Iteration', w / 2, h - 2);
        ctx.restore();
    }
}
