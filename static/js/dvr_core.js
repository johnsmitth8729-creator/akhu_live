/**
 * AKHU Live DVR Subsystem - Core Modular Engine (Phase 1)
 * Decoupled, event-driven modules for state, clock, caching, provider, and queue-driven MSE.
 */

// --- 1. Event Bus ---
class DVREventBus {
    constructor() {
        this.listeners = {};
    }
    on(event, callback) {
        if (!this.listeners[event]) this.listeners[event] = [];
        this.listeners[event].push(callback);
    }
    off(event, callback) {
        if (!this.listeners[event]) return;
        this.listeners[event] = this.listeners[event].filter(cb => cb !== callback);
    }
    emit(event, data) {
        if (this.listeners[event]) {
            this.listeners[event].forEach(cb => {
                try { cb(data); } catch (e) { console.error(`[DVREventBus] Error in listener for ${event}:`, e); }
            });
        }
    }
}

// --- 1.1 Unified Timezone Utility ---
function formatUzbekistanTime(date, mode = 'time') {
    let inputMs;
    if (typeof window.getTashkentServerTimeMs === 'function' && (!date || Math.abs(date - Date.now()) < 5000)) {
        inputMs = window.getTashkentServerTimeMs();
    } else {
        inputMs = (date instanceof Date) ? date.getTime() : (typeof date === 'number' ? date : new Date(date).getTime());
        if (isNaN(inputMs)) return '--:--:--';
        if (window.SERVER_TIME_OFFSET_MS) {
            inputMs += window.SERVER_TIME_OFFSET_MS;
        }
    }
    const d = new Date(inputMs);

    if (mode === 'full' || mode === 'tooltip') {
        const parts = new Intl.DateTimeFormat('en-GB', {
            timeZone: 'Asia/Tashkent',
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: false
        }).formatToParts(d);

        const p = {};
        parts.forEach(pt => { if (pt.type !== 'literal') p[pt.type] = pt.value; });
        const dateStr = `${p.year}-${p.month}-${p.day} ${p.hour}:${p.minute}:${p.second}`;
        return mode === 'tooltip' ? `${dateStr} (+05:00)` : dateStr;
    }

    return new Intl.DateTimeFormat('en-GB', {
        timeZone: 'Asia/Tashkent',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false
    }).format(d);
}

window.formatUzbekistanTime = formatUzbekistanTime;

// --- 2. Playback Clock ---
class PlaybackClock {
    constructor() {
        this.serverTimeOffsetMs = 0;
        this.baseTimestampMs = this.getCurrentTime();
        this.syncWithServer();
    }

    async syncWithServer() {
        try {
            const timeUrl = (window.DVR_CONFIG && window.DVR_CONFIG.timeUrl) ? window.DVR_CONFIG.timeUrl : '/api/dvr/time/';
            const res = await fetch(timeUrl);
            if (res.ok) {
                const data = await res.json();
                if (data.server_time_ms) {
                    this.serverTimeOffsetMs = data.server_time_ms - Date.now();
                    this.baseTimestampMs = this.getCurrentTime();
                    console.log(`[PlaybackClock] Server time synced! Offset: ${this.serverTimeOffsetMs} ms`);
                }
            }
        } catch(e) {
            console.warn("[PlaybackClock] Server time sync warning:", e);
        }
    }

    getCurrentTime() {
        return Date.now() + this.serverTimeOffsetMs;
    }

    setTime(timestampMs) {
        this.baseTimestampMs = timestampMs;
    }

    getTime() {
        return this.baseTimestampMs;
    }

    getFormattedTime(mode = 'full') {
        return formatUzbekistanTime(this.getTime(), mode);
    }
}

// --- 3. State Machine ---
const DVRState = Object.freeze({
    IDLE: 'IDLE',
    LIVE: 'LIVE',
    BUFFERING: 'BUFFERING',
    PLAYBACK: 'PLAYBACK',
    SEEKING: 'SEEKING',
    PAUSED: 'PAUSED',
    EXPORTING: 'EXPORTING',
    ERROR: 'ERROR'
});

class DVRStateMachine {
    constructor(eventBus) {
        this.eventBus = eventBus;
        this.currentState = DVRState.IDLE;
    }
    setState(newState, payload = {}) {
        if (this.currentState === newState) return;
        const oldState = this.currentState;
        this.currentState = newState;
        console.log(`[DVRStateMachine] ${oldState} -> ${newState}`, payload);
        if (this.eventBus) {
            this.eventBus.emit('STATE_CHANGED', { oldState, newState, payload });
        }
    }
    getState() {
        return this.currentState;
    }
}

// --- 4. Provider Abstraction ---
class PlaybackProvider {
    async list(streamId) { throw new Error('Not implemented'); }
    getStreamUrl(streamId, startIso, durationSec, format) { throw new Error('Not implemented'); }
}

class MediaMTXProvider extends PlaybackProvider {
    async list(streamId) {
        const listUrl = (window.DVR_CONFIG && window.DVR_CONFIG.listUrlTemplate)
            ? window.DVR_CONFIG.listUrlTemplate.replace('STREAM_ID_PLACEHOLDER', encodeURIComponent(streamId))
            : `/api/dvr/${encodeURIComponent(streamId)}/list/`;
        const res = await fetch(listUrl);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return await res.json();
    }
    getStreamUrl(streamId, startIso, durationSec, format = 'fmp4') {
        let baseUrl = (window.DVR_CONFIG && window.DVR_CONFIG.getUrlTemplate)
            ? window.DVR_CONFIG.getUrlTemplate.replace('STREAM_ID_PLACEHOLDER', encodeURIComponent(streamId))
            : `/api/dvr/${encodeURIComponent(streamId)}/get/`;
            
        return `${baseUrl}?start=${encodeURIComponent(startIso)}&duration=${Math.ceil(durationSec)}&format=${format}`;
    }
}

// --- 5. LRU Cache (256 MB / 20 Segments Max) ---
class DVRCache {
    constructor(maxSizeMB = 256, maxSegments = 20) {
        this.maxSizeBytes = maxSizeMB * 1024 * 1024;
        this.maxSegments = maxSegments;
        this.cache = new Map();
        this.currentSizeBytes = 0;
    }
    get(key) {
        if (!this.cache.has(key)) return null;
        const item = this.cache.get(key);
        this.cache.delete(key);
        this.cache.set(key, item);
        return item;
    }
    put(key, buffer) {
        if (this.cache.has(key)) {
            this.currentSizeBytes -= this.cache.get(key).byteLength;
            this.cache.delete(key);
        }
        while ((this.currentSizeBytes + buffer.byteLength > this.maxSizeBytes || this.cache.size >= this.maxSegments) && this.cache.size > 0) {
            const oldestKey = this.cache.keys().next().value;
            const oldestBuf = this.cache.get(oldestKey);
            this.currentSizeBytes -= oldestBuf.byteLength;
            this.cache.delete(oldestKey);
            console.log(`[DVRCache] Evicted LRU segment: ${oldestKey}`);
        }
        this.cache.set(key, buffer);
        this.currentSizeBytes += buffer.byteLength;
    }
    clear() {
        this.cache.clear();
        this.currentSizeBytes = 0;
    }
}

// --- 6. Queue-Driven DVRMediaSource ---
class DVRMediaSource {
    constructor(videoEl, eventBus) {
        this.videoEl = videoEl;
        this.eventBus = eventBus;
        this.mediaSource = null;
        this.sourceBuffer = null;
        this.abortController = null;
    }

    stop() {
        if (this.abortController) {
            this.abortController.abort();
            this.abortController = null;
        }
        if (this.sourceBuffer) {
            try {
                if (this.sourceBuffer.updating) this.sourceBuffer.abort();
            } catch (e) {}
            this.sourceBuffer = null;
        }
        if (this.mediaSource) {
            try {
                if (this.mediaSource.readyState === 'open') this.mediaSource.endOfStream();
            } catch (e) {}
            this.mediaSource = null;
        }
        if (this.videoEl) {
            this.videoEl.pause();
            if (this.videoEl.src && this.videoEl.src.startsWith('blob:')) {
                URL.revokeObjectURL(this.videoEl.src);
            }
            this.videoEl.removeAttribute('src');
            this.videoEl.load();
        }
    }

    async loadStream(mediaUrl, computedLocalSeek) {
        this.stop();

        const candidateMimes = [
            'video/mp4; codecs="avc1.42E01E,opus"',
            'video/mp4; codecs="avc1.42E01E, opus"',
            'video/mp4; codecs="avc1.42E01E"',
            'video/mp4'
        ];

        let selectedMime = null;
        if ('MediaSource' in window && typeof MediaSource.isTypeSupported === 'function') {
            for (const candidate of candidateMimes) {
                if (MediaSource.isTypeSupported(candidate)) {
                    selectedMime = candidate;
                    break;
                }
            }
        }

        if (!selectedMime) {
            this.setupDirectPlayback(mediaUrl, computedLocalSeek);
            return;
        }

        this.mediaSource = new MediaSource();
        
        // Step 4 & 2: HTMLVideoElement Event & Property Tracing
        const videoEvts = ['loadedmetadata', 'loadeddata', 'canplay', 'canplaythrough', 'play', 'playing', 'waiting', 'stalled', 'ended', 'error'];
        const vHandler = (evt) => {
            const err = this.videoEl ? this.videoEl.error : null;
            console.log(`[DVR-MSE-DEBUG Step 4 VideoEvent: ${evt.type}] readyState=${this.videoEl.readyState}, networkState=${this.videoEl.networkState}, currentTime=${this.videoEl.currentTime.toFixed(2)}, duration=${this.videoEl.duration}, paused=${this.videoEl.paused}, error=${err ? err.code : 'none'}`);
        };
        videoEvts.forEach(eName => this.videoEl.addEventListener(eName, vHandler));

        this.mediaSource.addEventListener('sourceopen', async () => {
            console.log("[DVR-MSE-DEBUG Step 3 MSE] sourceopen fired, readyState=", this.mediaSource.readyState);
            try {
                this.sourceBuffer = this.mediaSource.addSourceBuffer(selectedMime);
                // Set sequence mode so MediaSource aligns timestamps to start at 0.0s
                this.sourceBuffer.mode = 'sequence';
                console.log("[DVR-MSE-DEBUG Step 3 MSE] SourceBuffer created with mode='sequence'");

                this.sourceBuffer.addEventListener('update', () => console.log("[DVR-MSE-DEBUG Step 3 MSE] SourceBuffer update"));
                this.sourceBuffer.addEventListener('error', (e) => console.error("[DVR-MSE-DEBUG Step 3 MSE] SourceBuffer error:", e));

                this.abortController = new AbortController();
                
                // Step 1: Network Trace
                console.log(`[DVR-MSE-DEBUG Step 1 Network] Fetching GET URL: ${mediaUrl}`);
                const response = await fetch(mediaUrl, { signal: this.abortController.signal });
                const contentType = response.headers.get('content-type') || 'unknown';
                console.log(`[DVR-MSE-DEBUG Step 1 Network] Response: Status=${response.status}, Content-Type=${contentType}`);
                
                if (!response.ok) throw new Error(`HTTP ${response.status}`);

                const reader = response.body.getReader();
                let totalBytes = 0;
                let chunkCount = 0;
                const queue = [];
                let streamFinished = false;
                let initialSeekDone = false;

                const pump = () => {
                    if (!this.sourceBuffer) return;
                    if (this.videoEl && this.videoEl.error) return;
                    if (this.sourceBuffer.updating) return;

                    // Step 5: Check MSE Queue & SourceBuffer Status
                    if (queue.length > 0) {
                        const chunk = queue.shift();
                        chunkCount++;
                        try {
                            // Step 6: Check appendBuffer
                            this.sourceBuffer.appendBuffer(chunk);
                            let bufInfo = "none";
                            if (this.sourceBuffer.buffered && this.sourceBuffer.buffered.length > 0) {
                                bufInfo = `[${this.sourceBuffer.buffered.start(0).toFixed(2)}s - ${this.sourceBuffer.buffered.end(0).toFixed(2)}s]`;
                            }
                            console.log(`[DVR-MSE-DEBUG Step 6 Chunk #${chunkCount}] size=${chunk.byteLength} bytes, remainingQueue=${queue.length}, updating=${this.sourceBuffer.updating}, buffered=${bufInfo}`);
                        } catch (appErr) {
                            console.error("[DVR-MSE-DEBUG Step 6 ERROR] appendBuffer error:", appErr);
                        }
                    } else if (streamFinished) {
                        if (this.mediaSource && this.mediaSource.readyState === 'open' && !this.sourceBuffer.updating) {
                            try {
                                // Step 7: Check endOfStream
                                console.log("[DVR-MSE-DEBUG Step 7] Stream finished. Calling mediaSource.endOfStream()");
                                this.mediaSource.endOfStream();
                                console.log(`[DVR-MSE-DEBUG Step 7] endOfStream successful! mediaSource.readyState=${this.mediaSource.readyState}`);
                            } catch (eosErr) {
                                console.error("[DVR-MSE-DEBUG Step 7 ERROR] endOfStream failed:", eosErr);
                            }
                        }
                    }

                    if (!initialSeekDone && computedLocalSeek >= 0 && this.sourceBuffer && !this.sourceBuffer.updating) {
                        if (this.sourceBuffer.buffered && this.sourceBuffer.buffered.length > 0) {
                            const bufEnd = this.sourceBuffer.buffered.end(0);
                            const seekTarget = Math.min(computedLocalSeek, bufEnd - 0.2);
                            if (seekTarget >= 0) {
                                try {
                                    this.videoEl.currentTime = seekTarget;
                                    initialSeekDone = true;
                                    console.log(`[DVR-MSE-DEBUG Step 6 Seek] video.currentTime set to ${seekTarget.toFixed(2)}s (bufEnd=${bufEnd.toFixed(2)}s)`);
                                } catch (sErr) {
                                    console.warn("[DVR-MSE-DEBUG Step 6 Seek Warning]", sErr);
                                }
                            }
                        }
                    }

                    if (this.videoEl && this.videoEl.paused && !this.videoEl.error && (this.sourceBuffer && this.sourceBuffer.buffered && this.sourceBuffer.buffered.length > 0)) {
                        console.log("[DVR-MSE-DEBUG Step 8 Trigger Play] Invoking videoEl.play()");
                        this.videoEl.play().then(() => {
                            console.log("[DVR-MSE-DEBUG Step 8 Video Playing] video.play() SUCCESS! currentTime=", this.videoEl.currentTime.toFixed(2));
                        }).catch(pErr => {
                            console.warn("[DVR-MSE-DEBUG Step 8 Play Autoplay Warning]", pErr);
                        });
                    }
                };

                this.sourceBuffer.addEventListener('updateend', () => {
                    console.log("[DVR-MSE-DEBUG Step 3 MSE] SourceBuffer updateend event fired");
                    pump();
                });

                const enqueue = (chunk) => {
                    queue.push(chunk);
                    pump();
                };

                while (true) {
                    if (this.videoEl && this.videoEl.error) break;
                    const { done, value } = await reader.read();
                    if (done) {
                        streamFinished = true;
                        console.log(`[DVR-MSE-DEBUG Step 1 Network] Stream read complete! Total Bytes Transferred: ${totalBytes} bytes`);
                        pump();
                        break;
                    }
                    totalBytes += value.byteLength;
                    enqueue(value);
                }
            } catch (e) {
                console.error("[DVR-MSE-DEBUG ERROR] loadStream exception:", e);
                this.setupDirectPlayback(mediaUrl, computedLocalSeek);
            }
        });

        this.videoEl.src = URL.createObjectURL(this.mediaSource);
    }

    setupDirectPlayback(mediaUrl, seekOffset) {
        this.stop();
        this.videoEl.src = mediaUrl;
        this.videoEl.load();
        if (seekOffset > 0) {
            const onMeta = () => {
                this.videoEl.currentTime = seekOffset;
                this.videoEl.removeEventListener('loadedmetadata', onMeta);
            };
            this.videoEl.addEventListener('loadedmetadata', onMeta);
        }
        this.videoEl.play().catch(e => {});
    }
}

// Attach modules to global window for integration
window.DVREventBus = DVREventBus;
window.PlaybackClock = PlaybackClock;
window.DVRState = DVRState;
window.DVRStateMachine = DVRStateMachine;
window.PlaybackProvider = PlaybackProvider;
window.MediaMTXProvider = MediaMTXProvider;
window.DVRCache = DVRCache;
window.DVRMediaSource = DVRMediaSource;
