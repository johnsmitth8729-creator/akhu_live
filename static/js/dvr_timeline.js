/**
 * AKHU Live DVR Subsystem - Timeline Engine (Phase 2)
 * High-performance 60 FPS Dirty Region Canvas Renderer & CCTV Interactive Timeline Engine
 */

class TimelineModel {
    constructor() {
        this.segments = []; // [{ startMs, endMs, durationSec }]
        this.bufferedRanges = []; // [{ startMs, endMs }]
        this.aiEvents = []; // Reserved Layer 2: [{ timestampMs, type, label, color }]
        this.zoomLevelsSec = [86400, 21600, 3600, 600, 60]; // 24h, 6h, 1h, 10m, 1m
        this.zoomIndex = 2; // Default: 1 hour (3600s)
        this.windowCenterMs = Date.now();
    }

    getZoomWindowSec() {
        return this.zoomLevelsSec[this.zoomIndex];
    }

    getWindowBounds() {
        const halfWinMs = (this.getZoomWindowSec() * 1000) / 2;
        return {
            startMs: this.windowCenterMs - halfWinMs,
            endMs: this.windowCenterMs + halfWinMs
        };
    }

    zoom(deltaIndex, centerMs = null) {
        const newIndex = Math.max(0, Math.min(this.zoomLevelsSec.length - 1, this.zoomIndex + deltaIndex));
        if (newIndex !== this.zoomIndex) {
            this.zoomIndex = newIndex;
            if (centerMs) this.windowCenterMs = centerMs;
            return true;
        }
        return false;
    }

    addAiEvent(eventObj) {
        this.aiEvents.push(eventObj);
    }
}

class CanvasRenderer {
    constructor(canvasEl, model, clock) {
        this.canvas = canvasEl;
        this.ctx = canvasEl.getContext('2d');
        this.model = model;
        this.clock = clock;
        this.isDirty = true;
        this.hoverX = null;
        this.hoverTimestampMs = null;

        this.animFrameId = null;
        this.startLoop();
    }

    markDirty() {
        this.isDirty = true;
    }

    startLoop() {
        const loop = () => {
            if (this.isDirty) {
                this.render();
                this.isDirty = false;
            }
            this.animFrameId = requestAnimationFrame(loop);
        };
        this.animFrameId = requestAnimationFrame(loop);
    }

    stopLoop() {
        if (this.animFrameId) {
            cancelAnimationFrame(this.animFrameId);
            this.animFrameId = null;
        }
    }

    render() {
        const width = this.canvas.width;
        const height = this.canvas.height;
        if (!width || !height) return;

        const ctx = this.ctx;
        ctx.clearRect(0, 0, width, height);

        // 1. Background
        ctx.fillStyle = '#0f172a'; // slate-900
        ctx.fillRect(0, 0, width, height);

        const { startMs, endMs } = this.model.getWindowBounds();
        const totalWinMs = endMs - startMs;

        const msToX = (ms) => ((ms - startMs) / totalWinMs) * width;
        const xToMs = (x) => startMs + (x / width) * totalWinMs;

        // 2. Layer 1: Recording Track & Segments
        const trackY = 24;
        const trackH = 20;

        ctx.fillStyle = '#1e293b'; // slate-800 track
        ctx.fillRect(0, trackY, width, trackH);

        // Render Recording Segments
        ctx.fillStyle = 'rgba(16, 185, 129, 0.4)'; // emerald recording bar
        this.model.segments.forEach(seg => {
            const x1 = Math.max(0, msToX(seg.startMs));
            const x2 = Math.min(width, msToX(seg.endMs));
            if (x2 > x1) {
                ctx.fillRect(x1, trackY, x2 - x1, trackH);
            }
        });

        // Render Downloaded MSE Buffered Ranges
        ctx.fillStyle = 'rgba(56, 189, 248, 0.8)'; // cyan-400 buffered progress
        this.model.bufferedRanges.forEach(b => {
            const x1 = Math.max(0, msToX(b.startMs));
            const x2 = Math.min(width, msToX(b.endMs));
            if (x2 > x1) {
                ctx.fillRect(x1, trackY + trackH - 4, x2 - x1, 4);
            }
        });

        // 3. Layer 2: Reserved AI Event Markers
        this.model.aiEvents.forEach(evt => {
            const x = msToX(evt.timestampMs);
            if (x >= 0 && x <= width) {
                ctx.fillStyle = evt.color || '#f59e0b';
                ctx.beginPath();
                ctx.arc(x, trackY + trackH + 6, 4, 0, Math.PI * 2);
                ctx.fill();
            }
        });

        // 4. Time Ticks & Scale Labels (Asia/Tashkent Timezone)
        ctx.fillStyle = '#64748b';
        ctx.font = '10px sans-serif';
        ctx.textAlign = 'center';

        const windowSec = this.model.getZoomWindowSec();
        let tickIntervalSec = 300;
        if (windowSec <= 60) tickIntervalSec = 10;
        else if (windowSec <= 600) tickIntervalSec = 60;
        else if (windowSec <= 3600) tickIntervalSec = 300;
        else if (windowSec <= 21600) tickIntervalSec = 1800;
        else tickIntervalSec = 7200;

        const firstTickMs = Math.ceil(startMs / (tickIntervalSec * 1000)) * (tickIntervalSec * 1000);
        for (let t = firstTickMs; t <= endMs; t += tickIntervalSec * 1000) {
            const x = msToX(t);
            ctx.strokeStyle = 'rgba(255, 255, 255, 0.15)';
            ctx.beginPath();
            ctx.moveTo(x, 0);
            ctx.lineTo(x, trackY);
            ctx.stroke();

            const d = new Date(t);
            const timeStr = typeof formatUzbekistanTime === 'function' ? formatUzbekistanTime(d, 'time') : d.toTimeString().split(' ')[0];
            ctx.fillText(timeStr, x, 14);
        }

        // 5. Playback Head
        const currentHeadMs = this.clock.getTime();
        const headX = msToX(currentHeadMs);

        if (headX >= 0 && headX <= width) {
            ctx.strokeStyle = '#ef4444'; // red-500
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.moveTo(headX, 0);
            ctx.lineTo(headX, height);
            ctx.stroke();

            ctx.fillStyle = '#ef4444';
            ctx.beginPath();
            ctx.arc(headX, trackY, 5, 0, Math.PI * 2);
            ctx.fill();
        }

        // 6. Hover Marker Cursor (Asia/Tashkent Timezone Tooltip: YYYY-MM-DD HH:mm:ss (+05:00))
        if (this.hoverX !== null && this.hoverTimestampMs) {
            ctx.strokeStyle = 'rgba(255, 255, 255, 0.5)';
            ctx.lineWidth = 1;
            ctx.setLineDash([3, 3]);
            ctx.beginPath();
            ctx.moveTo(this.hoverX, 0);
            ctx.lineTo(this.hoverX, height);
            ctx.stroke();
            ctx.setLineDash([]);

            const hoverDate = new Date(this.hoverTimestampMs);
            const hoverStr = typeof formatUzbekistanTime === 'function' ? formatUzbekistanTime(hoverDate, 'tooltip') : hoverDate.toTimeString().split(' ')[0];

            ctx.fillStyle = 'rgba(15, 23, 42, 0.95)';
            const tooltipWidth = 145;
            const tooltipX = Math.max(5, Math.min(width - tooltipWidth - 5, this.hoverX - (tooltipWidth / 2)));
            ctx.fillRect(tooltipX, height - 18, tooltipWidth, 16);
            ctx.strokeStyle = 'rgba(56, 189, 248, 0.5)';
            ctx.strokeRect(tooltipX, height - 18, tooltipWidth, 16);

            ctx.fillStyle = '#38bdf8';
            ctx.font = '9px sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText(hoverStr, tooltipX + (tooltipWidth / 2), height - 6);
        }
    }
}

class DVRTimelineEngine {
    constructor(canvasEl, model, clock, eventBus) {
        this.canvas = canvasEl;
        this.model = model;
        this.clock = clock;
        this.eventBus = eventBus;
        this.renderer = new CanvasRenderer(canvasEl, model, clock);

        this.isDragging = false;
        this.resizeObserver = null;

        this.initEvents();
        this.initResizeObserver();
    }

    initResizeObserver() {
        if ('ResizeObserver' in window) {
            this.resizeObserver = new ResizeObserver(() => {
                this.resizeCanvas();
            });
            this.resizeObserver.observe(this.canvas.parentElement || this.canvas);
        } else {
            window.addEventListener('resize', () => this.resizeCanvas());
        }
        this.resizeCanvas();
    }

    resizeCanvas() {
        const parent = this.canvas.parentElement || this.canvas;
        const rect = parent.getBoundingClientRect();
        this.canvas.width = rect.width || 800;
        this.canvas.height = 54;
        this.renderer.markDirty();
    }

    setRecordings(segments) {
        this.model.segments = segments.map(s => ({
            startMs: new Date(s.start).getTime(),
            endMs: new Date(s.start).getTime() + ((s.duration || 60) * 1000),
            durationSec: s.duration || 60
        }));
        if (this.model.segments.length > 0) {
            this.model.windowCenterMs = this.model.segments[this.model.segments.length - 1].endMs;
        }
        this.renderer.markDirty();
    }

    setBufferedRanges(bufferedRanges) {
        this.model.bufferedRanges = bufferedRanges;
        this.renderer.markDirty();
    }

    updateClock(ms) {
        this.clock.setTime(ms);
        if (!this.isDragging) {
            this.model.windowCenterMs = ms;
        }
        this.renderer.markDirty();
    }

    initEvents() {
        const getXMs = (e) => {
            const rect = this.canvas.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const { startMs, endMs } = this.model.getWindowBounds();
            const targetMs = startMs + (x / rect.width) * (endMs - startMs);
            return { x, targetMs };
        };

        this.canvas.addEventListener('mousemove', (e) => {
            const { x, targetMs } = getXMs(e);
            this.renderer.hoverX = x;
            this.renderer.hoverTimestampMs = targetMs;
            this.renderer.markDirty();

            if (this.isDragging) {
                this.clock.setTime(targetMs);
                this.eventBus.emit('TIMELINE_DRAG', { timestampMs: targetMs });
            }
        });

        this.canvas.addEventListener('mouseleave', () => {
            this.renderer.hoverX = null;
            this.renderer.hoverTimestampMs = null;
            this.renderer.markDirty();
        });

        this.canvas.addEventListener('mousedown', (e) => {
            this.isDragging = true;
            const { targetMs } = getXMs(e);
            this.clock.setTime(targetMs);
            this.eventBus.emit('SEEK_REQUEST', { timestampMs: targetMs });
            this.renderer.markDirty();
        });

        window.addEventListener('mouseup', () => {
            if (this.isDragging) {
                this.isDragging = false;
                this.eventBus.emit('TIMELINE_DRAG_END', { timestampMs: this.clock.getTime() });
            }
        });

        this.canvas.addEventListener('wheel', (e) => {
            e.preventDefault();
            const { targetMs } = getXMs(e);
            const deltaIndex = e.deltaY > 0 ? 1 : -1;
            if (this.model.zoom(deltaIndex, targetMs)) {
                this.eventBus.emit('TIMELINE_ZOOM', { zoomIndex: this.model.zoomIndex, windowSec: this.model.getZoomWindowSec() });
                this.renderer.markDirty();
            }
        }, { passive: false });

        this.canvas.addEventListener('dblclick', () => {
            this.eventBus.emit('LIVE_REQUEST');
        });
    }
}

window.TimelineModel = TimelineModel;
window.CanvasRenderer = CanvasRenderer;
window.DVRTimelineEngine = DVRTimelineEngine;
