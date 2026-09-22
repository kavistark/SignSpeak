/**
 * Main Web Application Logic for ISL Studio (v2.0).
 */

document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const sentenceInput = document.getElementById('sentence-input');
    const previewGrammarBtn = document.getElementById('preview-grammar-btn');
    const generateBtn = document.getElementById('generate-btn');
    const grammarPanel = document.getElementById('grammar-panel');
    const glossesContainer = document.getElementById('glosses-container');
    const charCount = document.getElementById('char-count');
    const clearInputBtn = document.getElementById('clear-input-btn');
    const voiceInputBtn = document.getElementById('voice-input-btn');
    const voiceBtnText = document.getElementById('voice-btn-text');

    // Progress Elements
    const progressSection = document.getElementById('progress-section');
    const progressHeading = document.getElementById('progress-heading');
    const progressStatusText = document.getElementById('progress-status-text');
    const progressPercent = document.getElementById('progress-percent');
    const progressBarFill = document.getElementById('progress-bar-fill');
    const terminalLogs = document.getElementById('terminal-logs');

    // Visualizer Elements
    const visualizerSection = document.getElementById('visualizer-section');
    const visualizerContainer = document.getElementById('visualizer-container');
    const videoElem = document.getElementById('isl-video');
    const videoSource = document.getElementById('video-source');
    const activeWordBadge = document.getElementById('active-word-badge');
    const videoInfoBadge = document.getElementById('video-info-badge');
    const skeletonFrameBadge = document.getElementById('skeleton-frame-badge');
    const playPauseBtn = document.getElementById('play-pause-btn');
    const playIcon = document.getElementById('play-icon');
    const pauseIcon = document.getElementById('pause-icon');
    const stepBackBtn = document.getElementById('step-back-btn');
    const stepFwdBtn = document.getElementById('step-fwd-btn');
    const videoSeek = document.getElementById('video-seek');
    const timeDisplay = document.getElementById('time-display');
    const playbackSpeedSelect = document.getElementById('playback-speed');
    const loopToggleBtn = document.getElementById('loop-toggle-btn');
    const wordTimelineStrip = document.getElementById('word-timeline-strip');
    const btnFullscreen = document.getElementById('btn-fullscreen');
    const skeletonThemeSelect = document.getElementById('skeleton-theme');

    // Toggles
    const toggleGlow = document.getElementById('toggle-glow');
    const togglePoints = document.getElementById('toggle-points');

    // Export buttons
    const downloadVideoBtn = document.getElementById('download-video-btn');
    const downloadNpzBtn = document.getElementById('download-npz-btn');
    const downloadCsvBtn = document.getElementById('download-csv-btn');
    const downloadJsonBtn = document.getElementById('download-json-btn');

    // History
    const historySection = document.getElementById('history-section');
    const historyList = document.getElementById('history-list');
    const clearHistoryBtn = document.getElementById('clear-history-btn');

    // Dictionary Modal
    const openDictBtn = document.getElementById('open-dict-btn');
    const closeDictBtn = document.getElementById('close-dict-btn');
    const dictModal = document.getElementById('dict-modal');
    const dictSearchInput = document.getElementById('dict-search-input');
    const dictGrid = document.getElementById('dict-grid');
    const dictCount = document.getElementById('dict-count');
    const tabAllCount = document.getElementById('tab-all-count');

    // Status chip
    const systemStatusChip = document.getElementById('system-status-chip');

    // State
    let currentJobResult = null;
    let vocabularyItems = [];
    let isRecording = false;
    let recognition = null;
    let isLooping = false;
    let skeletonPlayer = new SkeletonPlayer('skeleton-canvas', 'isl-video');

    skeletonPlayer.onFrameUpdate = (frameIdx) => {
        skeletonFrameBadge.textContent = `Frame ${frameIdx}`;
    };

    // -------------------------------------------------------------
    // System Diagnostics & Load
    // -------------------------------------------------------------
    async function checkDiagnostics() {
        try {
            const res = await fetch('/api/diagnostics');
            const data = await res.json();
            if (data.ffmpeg && data.ffmpeg.available) {
                systemStatusChip.innerHTML = `<span class="status-dot"></span><span class="status-text">Engine Ready (${data.dataset.count} Signs)</span>`;
            } else {
                systemStatusChip.innerHTML = `<span class="status-dot" style="background:#f43f5e;box-shadow:0 0 8px #f43f5e"></span><span class="status-text">FFmpeg Missing</span>`;
            }
        } catch (e) {
            systemStatusChip.innerHTML = `<span class="status-dot" style="background:#f59e0b"></span><span class="status-text">Connecting...</span>`;
        }
    }
    checkDiagnostics();

    // -------------------------------------------------------------
    // Character Counter & Input Clear
    // -------------------------------------------------------------
    function updateInputState() {
        const len = sentenceInput.value.length;
        charCount.textContent = `${len} character${len === 1 ? '' : 's'}`;
        clearInputBtn.style.display = len > 0 ? 'flex' : 'none';
    }

    sentenceInput.addEventListener('input', updateInputState);

    clearInputBtn.addEventListener('click', () => {
        sentenceInput.value = '';
        updateInputState();
        grammarPanel.style.display = 'none';
        sentenceInput.focus();
    });

    // -------------------------------------------------------------
    // Voice / Speech Input (Web Speech API)
    // -------------------------------------------------------------
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
        recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.lang = 'en-US';
        recognition.interimResults = false;

        recognition.onstart = () => {
            isRecording = true;
            voiceInputBtn.classList.add('recording');
            voiceBtnText.textContent = 'Listening...';
        };

        recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            sentenceInput.value = transcript;
            updateInputState();
            triggerQuickPreview();
        };

        recognition.onerror = (e) => {
            console.warn("Speech recognition error:", e);
            stopRecording();
        };

        recognition.onend = () => {
            stopRecording();
        };

        function stopRecording() {
            isRecording = false;
            voiceInputBtn.classList.remove('recording');
            voiceBtnText.textContent = 'Voice Input';
        }

        voiceInputBtn.addEventListener('click', () => {
            if (isRecording) {
                recognition.stop();
                stopRecording();
            } else {
                try {
                    recognition.start();
                } catch (e) {
                    console.warn("Failed to start speech recognition:", e);
                }
            }
        });
    } else {
        voiceInputBtn.style.display = 'none';
    }

    // -------------------------------------------------------------
    // Vocabulary Loading & Modal
    // -------------------------------------------------------------
    async function loadVocabulary() {
        try {
            const res = await fetch('/api/vocabulary');
            const data = await res.json();
            vocabularyItems = data.items || [];
            dictCount.textContent = data.total || 228;
            tabAllCount.textContent = data.total || 228;
            renderDictGrid();
        } catch (e) {
            console.error("Failed to load vocabulary:", e);
        }
    }
    loadVocabulary();

    function renderDictGrid() {
        const query = (dictSearchInput.value || '').trim().toLowerCase();
        dictGrid.innerHTML = '';

        const filtered = vocabularyItems.filter(item => {
            return item.word.toLowerCase().includes(query) || (item.yt_name && item.yt_name.toLowerCase().includes(query));
        });

        if (filtered.length === 0) {
            dictGrid.innerHTML = `<div style="grid-column: 1/-1; text-align:center; padding: 20px; color: var(--text-muted)">No signs found matching "${query}"</div>`;
            return;
        }

        filtered.forEach(item => {
            const card = document.createElement('div');
            card.className = 'dict-item-card';
            card.innerHTML = `
                <span class="dict-item-word">${item.word}</span>
                <span class="dict-item-time">${item.start} - ${item.end}</span>
            `;
            card.addEventListener('click', () => {
                const current = sentenceInput.value.trim();
                sentenceInput.value = current ? `${current} ${item.word}` : item.word;
                updateInputState();
                dictModal.style.display = 'none';
                sentenceInput.focus();
                triggerQuickPreview();
            });
            dictGrid.appendChild(card);
        });
    }

    openDictBtn.addEventListener('click', () => {
        dictModal.style.display = 'flex';
        dictSearchInput.focus();
    });

    closeDictBtn.addEventListener('click', () => {
        dictModal.style.display = 'none';
    });

    dictModal.addEventListener('click', (e) => {
        if (e.target === dictModal) dictModal.style.display = 'none';
    });

    dictSearchInput.addEventListener('input', renderDictGrid);

    // -------------------------------------------------------------
    // Example Chips & Category Tabs
    // -------------------------------------------------------------
    document.querySelectorAll('.cat-pill').forEach(pill => {
        pill.addEventListener('click', () => {
            document.querySelectorAll('.cat-pill').forEach(p => p.classList.remove('active'));
            pill.classList.add('active');
            const cat = pill.dataset.cat;
            document.querySelectorAll('.example-chips .chip-btn').forEach(btn => {
                if (cat === 'all' || btn.dataset.cat === cat) {
                    btn.style.display = 'inline-block';
                } else {
                    btn.style.display = 'none';
                }
            });
        });
    });

    document.querySelectorAll('.chip-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            sentenceInput.value = btn.dataset.text;
            updateInputState();
            triggerQuickPreview();
        });
    });

    // -------------------------------------------------------------
    // Quick Grammar Preview
    // -------------------------------------------------------------
    async function triggerQuickPreview() {
        const text = sentenceInput.value.trim();
        if (!text) {
            grammarPanel.style.display = 'none';
            return;
        }

        try {
            previewGrammarBtn.disabled = true;
            const res = await fetch('/api/translate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text })
            });
            const data = await res.json();
            if (data.words) {
                grammarPanel.style.display = 'block';
                glossesContainer.innerHTML = '';
                data.words.forEach(w => {
                    const card = document.createElement('div');
                    card.className = `gloss-card in-vocab`;
                    card.innerHTML = `
                        <span class="gloss-word">${w.word}</span>
                        <span class="gloss-tag">${w.in_vocab ? 'Vocabulary' : 'Resolved'}</span>
                    `;
                    glossesContainer.appendChild(card);
                });
            }
        } catch (e) {
            console.error("Preview error:", e);
        } finally {
            previewGrammarBtn.disabled = false;
        }
    }

    previewGrammarBtn.addEventListener('click', triggerQuickPreview);

    // -------------------------------------------------------------
    // Generation Pipeline with Live SSE Stream
    // -------------------------------------------------------------
    function appendTerminalLog(message) {
        const line = document.createElement('div');
        line.className = 'terminal-line';
        const now = new Date();
        const timeStr = `${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`;
        line.innerHTML = `<span class="term-time">[${timeStr}]</span> ${message}`;
        terminalLogs.appendChild(line);
        terminalLogs.scrollTop = terminalLogs.scrollHeight;
    }

    generateBtn.addEventListener('click', async () => {
        const text = sentenceInput.value.trim();
        if (!text) {
            alert("Please enter a sentence to translate.");
            return;
        }

        generateBtn.disabled = true;
        progressSection.style.display = 'block';
        visualizerSection.style.display = 'none';
        terminalLogs.innerHTML = '';
        progressBarFill.style.width = '0%';
        progressPercent.textContent = '0%';
        progressStatusText.textContent = 'Starting pipeline...';
        appendTerminalLog(`Initiating job for: "${text}"`);

        try {
            const startRes = await fetch('/api/process', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text })
            });
            const startData = await startRes.json();

            if (startData.error) {
                alert(`Error: ${startData.error}`);
                generateBtn.disabled = false;
                return;
            }

            const jobId = startData.job_id;
            appendTerminalLog(`Job registered with ID: ${jobId}`);

            // Connect to Server-Sent Events
            const eventSource = new EventSource(`/api/stream/${jobId}`);

            eventSource.onmessage = (e) => {
                try {
                    const event = JSON.parse(e.data);
                    if (event.message) {
                        appendTerminalLog(event.message);
                        progressStatusText.textContent = event.message;
                    }
                    if (event.progress !== undefined) {
                        progressBarFill.style.width = `${event.progress}%`;
                        progressPercent.textContent = `${event.progress}%`;
                    }

                    if (event.status === 'completed') {
                        eventSource.close();
                        onJobComplete(jobId, text);
                    } else if (event.status === 'failed') {
                        eventSource.close();
                        progressStatusText.textContent = `Pipeline failed: ${event.error || 'Unknown error'}`;
                        generateBtn.disabled = false;
                    }
                } catch (err) {
                    console.error("SSE parse error:", err);
                }
            };

            eventSource.onerror = (err) => {
                eventSource.close();
                checkJobResultPolling(jobId, text);
            };

        } catch (err) {
            alert(`Failed to start job: ${err}`);
            generateBtn.disabled = false;
        }
    });

    async function checkJobResultPolling(jobId, originalText) {
        try {
            const res = await fetch(`/api/result/${jobId}`);
            const data = await res.json();
            if (data.status === 'completed') {
                onJobComplete(jobId, originalText);
            } else if (data.status === 'failed') {
                progressStatusText.textContent = `Pipeline failed: ${data.error}`;
                generateBtn.disabled = false;
            } else {
                setTimeout(() => checkJobResultPolling(jobId, originalText), 1500);
            }
        } catch (e) {
            generateBtn.disabled = false;
        }
    }

    async function onJobComplete(jobId, originalText) {
        generateBtn.disabled = false;
        progressSection.style.display = 'none';
        visualizerSection.style.display = 'flex';

        try {
            const res = await fetch(`/api/result/${jobId}`);
            const data = await res.json();
            const result = data.result;
            currentJobResult = result;

            // Load Video
            videoSource.src = `${result.video_url}?t=${Date.now()}`;
            videoElem.load();
            videoInfoBadge.textContent = `${result.fps.toFixed(0)} FPS • ${result.total_frames} Frames`;

            // Load Keypoints
            const kpRes = await fetch(result.json_url);
            const kpData = await kpRes.json();
            skeletonPlayer.loadKeypoints(kpData);

            // Populate Export Links
            downloadVideoBtn.href = result.video_url;
            downloadNpzBtn.href = result.npz_url;
            downloadCsvBtn.href = result.csv_url;
            downloadJsonBtn.href = result.json_url;

            // Populate Word Timeline Strip
            wordTimelineStrip.innerHTML = '';
            result.word_durations.forEach(wd => {
                const chip = document.createElement('button');
                chip.className = 'timeline-chip';
                chip.textContent = wd.word;
                chip.title = `Seek to ${wd.word} (${(wd.start_ms/1000).toFixed(1)}s)`;
                chip.addEventListener('click', () => {
                    videoElem.currentTime = wd.start_ms / 1000;
                    videoElem.play();
                });
                wordTimelineStrip.appendChild(chip);
            });

            // Save to History
            saveToHistory(originalText, result);

            // Smooth scroll to visualizer
            visualizerSection.scrollIntoView({ behavior: 'smooth' });

        } catch (e) {
            console.error("Failed loading job result:", e);
        }
    }

    // -------------------------------------------------------------
    // Video Controls & Subtitles
    // -------------------------------------------------------------
    function updateActiveWordSubtitle() {
        if (!currentJobResult || !currentJobResult.word_durations) return;
        const currentMs = videoElem.currentTime * 1000;

        let activeWord = null;
        const chips = wordTimelineStrip.querySelectorAll('.timeline-chip');

        currentJobResult.word_durations.forEach((wd, idx) => {
            if (currentMs >= wd.start_ms && currentMs <= wd.end_ms) {
                activeWord = wd.word;
                if (chips[idx]) chips[idx].classList.add('active');
            } else {
                if (chips[idx]) chips[idx].classList.remove('active');
            }
        });

        if (activeWord) {
            activeWordBadge.textContent = activeWord;
            activeWordBadge.style.opacity = '1';
        } else {
            activeWordBadge.style.opacity = '0.7';
        }
    }

    videoElem.addEventListener('timeupdate', () => {
        updateActiveWordSubtitle();
        if (videoElem.duration) {
            videoSeek.value = (videoElem.currentTime / videoElem.duration) * 100;
            const curMin = String(Math.floor(videoElem.currentTime / 60)).padStart(2, '0');
            const curSec = String(Math.floor(videoElem.currentTime % 60)).padStart(2, '0');
            const durMin = String(Math.floor(videoElem.duration / 60)).padStart(2, '0');
            const durSec = String(Math.floor(videoElem.duration % 60)).padStart(2, '0');
            timeDisplay.textContent = `${curMin}:${curSec} / ${durMin}:${durSec}`;
        }
    });

    videoElem.addEventListener('ended', () => {
        if (isLooping) {
            videoElem.currentTime = 0;
            videoElem.play();
        }
    });

    playPauseBtn.addEventListener('click', () => {
        if (videoElem.paused || videoElem.ended) {
            videoElem.play();
            playIcon.style.display = 'none';
            pauseIcon.style.display = 'block';
        } else {
            videoElem.pause();
            playIcon.style.display = 'block';
            pauseIcon.style.display = 'none';
        }
    });

    // Spacebar to Play/Pause
    window.addEventListener('keydown', (e) => {
        if (e.code === 'Space' && document.activeElement !== sentenceInput && document.activeElement !== dictSearchInput) {
            e.preventDefault();
            playPauseBtn.click();
        }
    });

    videoElem.addEventListener('play', () => {
        playIcon.style.display = 'none';
        pauseIcon.style.display = 'block';
    });

    videoElem.addEventListener('pause', () => {
        playIcon.style.display = 'block';
        pauseIcon.style.display = 'none';
    });

    videoSeek.addEventListener('input', () => {
        if (videoElem.duration) {
            videoElem.currentTime = (videoSeek.value / 100) * videoElem.duration;
        }
    });

    // Playback Speed
    playbackSpeedSelect.addEventListener('change', (e) => {
        videoElem.playbackRate = parseFloat(e.target.value);
    });

    // Loop toggle
    loopToggleBtn.addEventListener('click', () => {
        isLooping = !isLooping;
        loopToggleBtn.classList.toggle('active', isLooping);
        loopToggleBtn.style.color = isLooping ? 'var(--accent-indigo)' : 'var(--text-primary)';
    });

    // Frame Stepping
    stepBackBtn.addEventListener('click', () => {
        videoElem.pause();
        skeletonPlayer.stepFrame(-1);
    });

    stepFwdBtn.addEventListener('click', () => {
        videoElem.pause();
        skeletonPlayer.stepFrame(1);
    });

    // Skeleton Theme Selection
    skeletonThemeSelect.addEventListener('change', (e) => {
        skeletonPlayer.setTheme(e.target.value);
    });

    // Toggle Glow / Points
    toggleGlow.addEventListener('change', (e) => {
        skeletonPlayer.showGlow = e.target.checked;
        skeletonPlayer.renderCurrentFrame();
    });

    togglePoints.addEventListener('change', (e) => {
        skeletonPlayer.showPoints = e.target.checked;
        skeletonPlayer.renderCurrentFrame();
    });

    // Fullscreen Mode
    btnFullscreen.addEventListener('click', () => {
        if (!document.fullscreenElement) {
            visualizerContainer.requestFullscreen().catch(err => console.warn(err));
        } else {
            document.exitFullscreen();
        }
    });

    // -------------------------------------------------------------
    // History Management
    // -------------------------------------------------------------
    function loadHistory() {
        const history = JSON.parse(localStorage.getItem('isl_history') || '[]');
        if (history.length > 0) {
            historySection.style.display = 'block';
            historyList.innerHTML = '';
            history.forEach(item => {
                const row = document.createElement('div');
                row.className = 'history-item';
                row.innerHTML = `
                    <div>
                        <div class="history-text">"${item.text}"</div>
                        <div class="history-isl">ISL: ${item.isl_text}</div>
                    </div>
                    <button class="btn btn-secondary btn-sm">Load</button>
                `;
                row.querySelector('button').addEventListener('click', () => {
                    sentenceInput.value = item.text;
                    updateInputState();
                    triggerQuickPreview();
                    sentenceInput.scrollIntoView({ behavior: 'smooth' });
                });
                historyList.appendChild(row);
            });
        } else {
            historySection.style.display = 'none';
        }
    }

    function saveToHistory(text, result) {
        let history = JSON.parse(localStorage.getItem('isl_history') || '[]');
        history = history.filter(h => h.text.toLowerCase() !== text.toLowerCase());
        history.unshift({
            text,
            isl_text: result.isl_text,
            timestamp: Date.now()
        });
        if (history.length > 6) history.pop();
        localStorage.setItem('isl_history', JSON.stringify(history));
        loadHistory();
    }

    clearHistoryBtn.addEventListener('click', () => {
        localStorage.removeItem('isl_history');
        loadHistory();
    });

    loadHistory();
});
