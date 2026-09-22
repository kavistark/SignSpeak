/**
 * Enhanced HTML5 Canvas Skeleton Renderer for MediaPipe Pose Landmarks.
 * Features theme color schemes, glow adjustments, frame-stepping, and synchronized playback.
 */

class SkeletonPlayer {
    constructor(canvasId, videoElementId) {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas.getContext('2d');
        this.video = document.getElementById(videoElementId);

        this.timeline = [];
        this.connections = [];
        this.fps = 30.0;
        this.currentFrameIdx = 0;
        this.showGlow = true;
        this.showPoints = true;
        this.theme = 'cyberpunk'; // 'cyberpunk', 'emerald', 'sunfire', 'neonpink'

        this.onFrameUpdate = null; // Callback (frameIdx) => {}

        this.init();
    }

    init() {
        this.resize();
        window.addEventListener('resize', () => this.resize());

        // Video playback synchronization
        this.video.addEventListener('timeupdate', () => this.syncWithVideo());
        this.video.addEventListener('play', () => this.startAnimationLoop());
        this.video.addEventListener('pause', () => this.stopAnimationLoop());
        this.video.addEventListener('seeked', () => this.syncWithVideo());
    }

    resize() {
        const rect = this.canvas.parentElement.getBoundingClientRect();
        this.canvas.width = rect.width * (window.devicePixelRatio || 1) || 640;
        this.canvas.height = rect.height * (window.devicePixelRatio || 1) || 480;
        this.renderCurrentFrame();
    }

    loadKeypoints(keypointsData) {
        this.timeline = keypointsData.timeline || [];
        this.connections = keypointsData.connections || [];
        this.fps = keypointsData.fps || 30.0;
        this.currentFrameIdx = 0;
        this.renderCurrentFrame();
    }

    setTheme(themeName) {
        this.theme = themeName;
        this.renderCurrentFrame();
    }

    stepFrame(delta) {
        if (!this.timeline || this.timeline.length === 0) return;
        this.currentFrameIdx = Math.max(0, Math.min(this.timeline.length - 1, this.currentFrameIdx + delta));
        const frameTimeSec = (this.timeline[this.currentFrameIdx].time_ms || 0) / 1000;
        this.video.currentTime = frameTimeSec;
        this.renderCurrentFrame();
        if (this.onFrameUpdate) this.onFrameUpdate(this.currentFrameIdx);
    }

    syncWithVideo() {
        if (!this.timeline || this.timeline.length === 0) return;
        
        const currentTimeMs = this.video.currentTime * 1000;
        
        // Find closest frame in timeline
        let closestIdx = 0;
        let minDiff = Infinity;

        for (let i = 0; i < this.timeline.length; i++) {
            const diff = Math.abs(this.timeline[i].time_ms - currentTimeMs);
            if (diff < minDiff) {
                minDiff = diff;
                closestIdx = i;
            } else if (diff > minDiff) {
                break;
            }
        }

        this.currentFrameIdx = closestIdx;
        this.renderCurrentFrame();

        if (this.onFrameUpdate) {
            this.onFrameUpdate(this.currentFrameIdx);
        }
    }

    startAnimationLoop() {
        if (this.animId) cancelAnimationFrame(this.animId);
        const loop = () => {
            if (!this.video.paused && !this.video.ended) {
                this.syncWithVideo();
                this.animId = requestAnimationFrame(loop);
            }
        };
        this.animId = requestAnimationFrame(loop);
    }

    stopAnimationLoop() {
        if (this.animId) {
            cancelAnimationFrame(this.animId);
            this.animId = null;
        }
    }

    getThemeColors() {
        switch (this.theme) {
            case 'emerald':
                return {
                    boneGradStart: '#059669',
                    boneGradEnd: '#34d399',
                    glowColor: '#10b981',
                    jointColor: '#6ee7b7',
                    limbHighlight: '#a7f3d0'
                };
            case 'sunfire':
                return {
                    boneGradStart: '#d97706',
                    boneGradEnd: '#fbbf24',
                    glowColor: '#f59e0b',
                    jointColor: '#fde047',
                    limbHighlight: '#ef4444'
                };
            case 'neonpink':
                return {
                    boneGradStart: '#be185d',
                    boneGradEnd: '#f43f5e',
                    glowColor: '#fb7185',
                    jointColor: '#fda4af',
                    limbHighlight: '#ec4899'
                };
            case 'cyberpunk':
            default:
                return {
                    boneGradStart: '#6366f1',
                    boneGradEnd: '#06b6d4',
                    glowColor: '#06b6d4',
                    jointColor: '#38bdf8',
                    limbHighlight: '#f43f5e'
                };
        }
    }

    renderCurrentFrame() {
        const w = this.canvas.width;
        const h = this.canvas.height;
        this.ctx.clearRect(0, 0, w, h);

        if (!this.timeline || this.timeline.length === 0) {
            this.drawPlaceholder(w, h);
            return;
        }

        const frameData = this.timeline[this.currentFrameIdx];
        if (!frameData || !frameData.landmarks) return;

        const landmarks = frameData.landmarks;
        const theme = this.getThemeColors();
        const dpr = window.devicePixelRatio || 1;

        // Draw bone connections
        this.ctx.save();
        this.ctx.lineWidth = Math.max(2.5, 3.5 * dpr);
        this.ctx.lineCap = 'round';
        this.ctx.lineJoin = 'round';

        for (const conn of this.connections) {
            const startIdx = conn[0];
            const endIdx = conn[1];

            if (startIdx < landmarks.length && endIdx < landmarks.length) {
                const p1 = landmarks[startIdx];
                const p2 = landmarks[endIdx];

                if (p1.v > 0.2 && p2.v > 0.2) {
                    const x1 = p1.x * w;
                    const y1 = p1.y * h;
                    const x2 = p2.x * w;
                    const y2 = p2.y * h;

                    if (this.showGlow) {
                        this.ctx.shadowColor = theme.glowColor;
                        this.ctx.shadowBlur = 10 * dpr;
                    } else {
                        this.ctx.shadowBlur = 0;
                    }

                    // Dynamic gradient for limbs
                    const grad = this.ctx.createLinearGradient(x1, y1, x2, y2);
                    grad.addColorStop(0, theme.boneGradStart);
                    grad.addColorStop(1, theme.boneGradEnd);
                    this.ctx.strokeStyle = grad;

                    this.ctx.beginPath();
                    this.ctx.moveTo(x1, y1);
                    this.ctx.lineTo(x2, y2);
                    this.ctx.stroke();
                }
            }
        }
        this.ctx.restore();

        // Draw joint points
        if (this.showPoints) {
            const radius = Math.max(3, 4.5 * dpr);
            for (let i = 0; i < landmarks.length; i++) {
                const p = landmarks[i];
                if (p.v > 0.2) {
                    const cx = p.x * w;
                    const cy = p.y * h;

                    this.ctx.save();
                    if (this.showGlow) {
                        this.ctx.shadowColor = theme.limbHighlight;
                        this.ctx.shadowBlur = 8 * dpr;
                    }
                    this.ctx.fillStyle = (i >= 11 && i <= 22) ? theme.jointColor : theme.limbHighlight;
                    this.ctx.beginPath();
                    this.ctx.arc(cx, cy, radius, 0, Math.PI * 2);
                    this.ctx.fill();
                    this.ctx.restore();
                }
            }
        }
    }

    drawPlaceholder(w, h) {
        const dpr = window.devicePixelRatio || 1;
        this.ctx.save();
        this.ctx.fillStyle = '#64748b';
        this.ctx.font = `${14 * dpr}px Outfit, sans-serif`;
        this.ctx.textAlign = 'center';
        this.ctx.fillText("Skeleton visualizer will appear after generation", w / 2, h / 2);
        this.ctx.restore();
    }
}

window.SkeletonPlayer = SkeletonPlayer;
