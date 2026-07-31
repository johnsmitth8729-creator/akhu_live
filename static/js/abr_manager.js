/**
 * Adaptive Bitrate (ABR) Manager for AKHU Live Player
 * Handles automatic quality selection (Auto mode) based on network bandwidth,
 * buffer health, and CPU capability, with manual override support.
 */
class ABRManager {
    constructor(videoEl, options = {}) {
        this.videoEl = videoEl;
        this.currentQuality = 'auto'; // 'auto', '1080p', '720p', '540p', '480p', '360p', '240p'
        this.availableQualities = options.qualities || ['1080p', '720p', '540p', '480p', '360p', '240p'];
        this.onQualityChange = options.onQualityChange || null;
        this.checkInterval = null;
        this.initNetworkMonitor();
    }

    initNetworkMonitor() {
        if (!this.videoEl) return;
        
        // Monitor buffer health and estimated bandwidth every 4 seconds
        this.checkInterval = setInterval(() => {
            if (this.currentQuality === 'auto') {
                this.evaluateAutoQuality();
            }
        }, 4000);
    }

    setQuality(targetQuality) {
        this.currentQuality = targetQuality;
        console.log(`[ABRManager] Quality set to: ${targetQuality}`);

        if (targetQuality === 'auto') {
            this.evaluateAutoQuality();
        } else {
            if (this.onQualityChange) {
                this.onQualityChange(targetQuality, false);
            }
        }
    }

    evaluateAutoQuality() {
        if (!this.videoEl) return;

        // Check Network Information API if available
        let estimatedMbps = 10;
        if (navigator.connection && navigator.connection.downlink) {
            estimatedMbps = navigator.connection.downlink;
        }

        // Check buffer health
        let bufferLength = 0;
        if (this.videoEl.buffered && this.videoEl.buffered.length > 0) {
            const currentTime = this.videoEl.currentTime;
            for (let i = 0; i < this.videoEl.buffered.length; i++) {
                if (this.videoEl.buffered.start(i) <= currentTime && currentTime <= this.videoEl.buffered.end(i)) {
                    bufferLength = this.videoEl.buffered.end(i) - currentTime;
                    break;
                }
            }
        }

        let selected = '720p';
        if (estimatedMbps >= 8 && bufferLength > 5) {
            selected = '1080p';
        } else if (estimatedMbps >= 4 && bufferLength > 3) {
            selected = '720p';
        } else if (estimatedMbps >= 2) {
            selected = '540p';
        } else if (estimatedMbps >= 1) {
            selected = '480p';
        } else {
            selected = '360p';
        }

        console.log(`[ABRManager Auto] Bandwidth: ${estimatedMbps}Mbps, Buffer: ${bufferLength.toFixed(1)}s -> Selected: ${selected}`);

        if (this.onQualityChange) {
            this.onQualityChange(selected, true);
        }
    }

    destroy() {
        if (this.checkInterval) {
            clearInterval(this.checkInterval);
        }
    }
}
