/**
 * MaxTube Pro Studio - Reactive Frontend Controller
 * Handles URL inspection, real-time SSE progress streaming, format configuration, and batch processing.
 */

document.addEventListener("DOMContentLoaded", () => {
    // DOM Elements - Mode Switcher
    const tabSingleMode = document.getElementById("tabSingleMode");
    const tabBatchMode = document.getElementById("tabBatchMode");
    const singleInputSection = document.getElementById("singleInputSection");
    const batchInputSection = document.getElementById("batchInputSection");
    const btnClearBatch = document.getElementById("btnClearBatch");

    // DOM Elements - Inputs
    const urlInput = document.getElementById("urlInput");
    const batchUrlsInput = document.getElementById("batchUrlsInput");
    const btnPaste = document.getElementById("btnPaste");
    const btnInspect = document.getElementById("btnInspect");

    // DOM Elements - Media Preview
    const mediaPreviewCard = document.getElementById("mediaPreviewCard");
    const previewThumb = document.getElementById("previewThumb");
    const previewDuration = document.getElementById("previewDuration");
    const previewPlatform = document.getElementById("previewPlatform");
    const previewTitle = document.getElementById("previewTitle");
    const previewUploader = document.getElementById("previewUploader");
    const previewViews = document.getElementById("previewViews");
    const previewResolutions = document.getElementById("previewResolutions");
    const playlistAccordionWrapper = document.getElementById("playlistAccordionWrapper");
    const playlistItemCount = document.getElementById("playlistItemCount");
    const playlistItemsList = document.getElementById("playlistItemsList");

    // DOM Elements - Format Options
    const modeVideoRadio = document.getElementById("modeVideo");
    const modeAudioRadio = document.getElementById("modeAudio");
    const videoOptionsPanel = document.getElementById("videoOptionsPanel");
    const audioOptionsPanel = document.getElementById("audioOptionsPanel");
    const resolutionSelect = document.getElementById("resolutionSelect");
    const audioFormatSelect = document.getElementById("audioFormatSelect");
    const audioBitrateSelect = document.getElementById("audioBitrateSelect");
    const bitrateContainer = document.getElementById("bitrateContainer");

    // DOM Elements - Action & Progress
    const btnStartDownload = document.getElementById("btnStartDownload");
    const btnDownloadText = document.getElementById("btnDownloadText");
    const progressPanel = document.getElementById("progressPanel");
    const jobStatusDot = document.getElementById("jobStatusDot");
    const jobStatusStep = document.getElementById("jobStatusStep");
    const jobPercentBadge = document.getElementById("jobPercentBadge");
    const jobProgressBar = document.getElementById("jobProgressBar");
    const jobSpeedVal = document.getElementById("jobSpeedVal");
    const jobSizeVal = document.getElementById("jobSizeVal");
    const jobEtaVal = document.getElementById("jobEtaVal");
    const downloadReadyBox = document.getElementById("downloadReadyBox");
    const directDownloadLink = document.getElementById("directDownloadLink");
    const downloadReadyBtnText = document.getElementById("downloadReadyBtnText");
    const jobErrorBox = document.getElementById("jobErrorBox");
    const jobErrorMessage = document.getElementById("jobErrorMessage");

    // DOM Elements - Settings & Updater
    const btnCheckUpdate = document.getElementById("btnCheckUpdate");
    const updateStatusAlert = document.getElementById("updateStatusAlert");
    const statsFileCount = document.getElementById("statsFileCount");
    const statsDiskUsage = document.getElementById("statsDiskUsage");
    const btnPurgeCache = document.getElementById("btnPurgeCache");

    // State Variables
    let currentMode = "single"; // "single" or "batch"
    let activeEventSource = null;
    let isInspecting = false;
    let lastInspectedUrl = "";

    // Mode Switching
    tabSingleMode.addEventListener("click", () => {
        currentMode = "single";
        tabSingleMode.classList.add("active");
        tabBatchMode.classList.remove("active");
        singleInputSection.classList.remove("d-none");
        batchInputSection.classList.add("d-none");
        btnDownloadText.textContent = "START DOWNLOAD";
    });

    tabBatchMode.addEventListener("click", () => {
        currentMode = "batch";
        tabBatchMode.classList.add("active");
        tabSingleMode.classList.remove("active");
        batchInputSection.classList.remove("d-none");
        singleInputSection.classList.add("d-none");
        mediaPreviewCard.classList.add("d-none");
        btnDownloadText.textContent = "QUEUE BATCH DOWNLOAD (ZIP)";
    });

    if (btnClearBatch) {
        btnClearBatch.addEventListener("click", () => {
            batchUrlsInput.value = "";
        });
    }

    // Paste Action
    if (btnPaste) {
        btnPaste.addEventListener("click", async () => {
            try {
                const text = await navigator.clipboard.readText();
                if (text && text.trim()) {
                    urlInput.value = text.trim();
                    inspectMedia(text.trim());
                }
            } catch (err) {
                console.warn("Clipboard access denied or unavailable:", err);
            }
        });
    }

    // Format Panel Toggle (Video vs Audio)
    modeVideoRadio.addEventListener("change", () => {
        if (modeVideoRadio.checked) {
            videoOptionsPanel.classList.remove("d-none");
            audioOptionsPanel.classList.add("d-none");
        }
    });

    modeAudioRadio.addEventListener("change", () => {
        if (modeAudioRadio.checked) {
            audioOptionsPanel.classList.remove("d-none");
            videoOptionsPanel.classList.add("d-none");
        }
    });

    // Audio Format Change (Hide bitrate if lossless)
    audioFormatSelect.addEventListener("change", () => {
        const val = audioFormatSelect.value;
        if (val === "wav" || val === "flac") {
            bitrateContainer.classList.add("opacity-50", "pointer-events-none");
            audioBitrateSelect.disabled = true;
        } else {
            bitrateContainer.classList.remove("opacity-50", "pointer-events-none");
            audioBitrateSelect.disabled = false;
        }
    });

    // Inspect Media Trigger
    btnInspect.addEventListener("click", () => {
        const url = urlInput.value.trim();
        if (url) {
            inspectMedia(url);
        }
    });

    urlInput.addEventListener("blur", () => {
        const url = urlInput.value.trim();
        if (url && url !== lastInspectedUrl) {
            inspectMedia(url);
        }
    });

    urlInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
            e.preventDefault();
            const url = urlInput.value.trim();
            if (url) {
                inspectMedia(url);
            }
        }
    });

    async function inspectMedia(url) {
        if (isInspecting || !url.startsWith("http")) return;
        isInspecting = true;
        lastInspectedUrl = url;

        const spinner = btnInspect.querySelector(".inspect-spinner");
        const inspectText = btnInspect.querySelector(".inspect-text");
        spinner.classList.remove("d-none");
        inspectText.classList.add("d-none");

        try {
            const resp = await fetch("/api/inspect", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ url: url })
            });

            const data = await resp.json();
            if (data.success) {
                renderPreview(data);
            } else {
                mediaPreviewCard.classList.add("d-none");
            }
        } catch (err) {
            console.error("Inspect error:", err);
            mediaPreviewCard.classList.add("d-none");
        } finally {
            isInspecting = false;
            spinner.classList.add("d-none");
            inspectText.classList.remove("d-none");
        }
    }

    function renderPreview(data) {
        mediaPreviewCard.classList.remove("d-none");
        previewThumb.src = data.thumbnail || "https://placehold.co/600x340/121826/4facfe?text=+Preview";
        previewPlatform.textContent = data.platform || "Video";
        previewTitle.textContent = data.title || "Untitled";
        previewUploader.innerHTML = `<i class="fa-solid fa-circle-user me-1"></i> ${data.uploader || "Unknown"}`;

        if (data.is_playlist) {
            previewDuration.textContent = `${data.item_count} items`;
            previewViews.innerHTML = `<i class="fa-solid fa-list text-info me-1"></i> Playlist Collection`;
            previewResolutions.innerHTML = `<i class="fa-solid fa-layer-group text-warning me-1"></i> Batch ZIP Mode`;
            
            playlistAccordionWrapper.classList.remove("d-none");
            playlistItemCount.textContent = `Playlist Tracks (${data.item_count || (data.entries ? data.entries.length : 0)})`;

            let itemsHtml = "";
            (data.entries || []).forEach((item) => {
                itemsHtml += `
                    <div class="playlist-item-row">
                        <span class="text-truncate me-2">#${item.index} ${item.title}</span>
                        <span class="text-muted font-monospace">${item.duration || ""}</span>
                    </div>
                `;
            });
            playlistItemsList.innerHTML = itemsHtml;
        } else {
            previewDuration.textContent = data.duration_str || "--:--";
            previewViews.innerHTML = `<i class="fa-solid fa-eye text-primary me-1"></i> ${(data.views || 0).toLocaleString()} views`;
            
            const highestRes = (data.available_resolutions && data.available_resolutions.length > 0)
                ? `${data.available_resolutions[0]}p Max`
                : "Best Available";
            previewResolutions.innerHTML = `<i class="fa-solid fa-film text-info me-1"></i> ${highestRes}`;
            
            playlistAccordionWrapper.classList.add("d-none");
        }
    }

    // Start Download Execution
    btnStartDownload.addEventListener("click", async () => {
        let urlsToDownload = [];

        if (currentMode === "single") {
            const singleUrl = urlInput.value.trim();
            if (!singleUrl) {
                alert("Please enter a media link first.");
                urlInput.focus();
                return;
            }
            urlsToDownload = [singleUrl];
        } else {
            const batchText = batchUrlsInput.value.trim();
            if (!batchText) {
                alert("Please paste at least one URL in the batch area.");
                batchUrlsInput.focus();
                return;
            }
            urlsToDownload = batchText.split("\n").map(u => u.trim()).filter(u => u.startsWith("http"));
            if (urlsToDownload.length === 0) {
                alert("No valid URLs found. Make sure URLs start with http:// or https://");
                return;
            }
        }

        const downloadMode = modeVideoRadio.checked ? "video" : "audio";
        const resolution = resolutionSelect.value;
        const audioFormat = audioFormatSelect.value;
        const audioBitrate = audioBitrateSelect.value;

        // Reset and show progress panel
        resetProgressUI();
        progressPanel.classList.remove("d-none");
        setButtonLoading(true);

        try {
            const resp = await fetch("/api/download/start", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    urls: urlsToDownload,
                    mode: downloadMode,
                    resolution: resolution,
                    audio_format: audioFormat,
                    audio_bitrate: audioBitrate
                })
            });

            const data = await resp.json();
            if (data.success && data.job_id) {
                listenToProgressSSE(data.job_id);
            } else {
                showError(data.error || "Failed to start download job.");
                setButtonLoading(false);
            }
        } catch (err) {
            showError("Network error: Could not reach download server.");
            setButtonLoading(false);
        }
    });

    function listenToProgressSSE(jobId) {
        if (activeEventSource) {
            activeEventSource.close();
        }

        activeEventSource = new EventSource(`/api/progress/${jobId}`);

        activeEventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                updateProgressUI(data);

                if (data.status === "completed") {
                    handleDownloadCompleted(data, jobId);
                    activeEventSource.close();
                    setButtonLoading(false);
                } else if (data.status === "error") {
                    showError(data.error_message || "Download encountered an error.");
                    activeEventSource.close();
                    setButtonLoading(false);
                }
            } catch (e) {
                console.error("Error parsing progress SSE payload:", e);
            }
        };

        activeEventSource.onerror = () => {
            console.warn("SSE connection interrupted. Falling back to status polling...");
            activeEventSource.close();
            startPollingFallback(jobId);
        };
    }

    function startPollingFallback(jobId) {
        const interval = setInterval(async () => {
            try {
                const res = await fetch(`/api/job/${jobId}`);
                const data = await res.json();
                updateProgressUI(data);

                if (data.status === "completed") {
                    handleDownloadCompleted(data, jobId);
                    clearInterval(interval);
                    setButtonLoading(false);
                } else if (data.status === "error") {
                    showError(data.error_message || "Download failed.");
                    clearInterval(interval);
                    setButtonLoading(false);
                }
            } catch (e) {
                clearInterval(interval);
                showError("Lost connection to server.");
                setButtonLoading(false);
            }
        }, 1500);
    }

    function updateProgressUI(data) {
        const pct = Math.min(Math.max(data.percent || 0, 0), 100);
        jobProgressBar.style.width = `${pct}%`;
        jobPercentBadge.textContent = `${pct.toFixed(1)}%`;

        if (data.step_message) {
            jobStatusStep.textContent = data.step_message;
        }

        jobSpeedVal.textContent = data.speed_str || "-- KB/s";
        jobSizeVal.textContent = (data.downloaded_str && data.total_str)
            ? `${data.downloaded_str} / ${data.total_str}`
            : "-- / --";
        jobEtaVal.textContent = data.eta_str || "--:--";
    }

    function handleDownloadCompleted(data, jobId) {
        jobProgressBar.style.width = "100%";
        jobPercentBadge.textContent = "100%";
        jobStatusStep.textContent = data.is_zip 
            ? `Batch Archive Ready (${data.completed_items || 'All'} items)`
            : "Transcoding complete. Ready to save!";
        
        jobStatusDot.classList.remove("pulse");
        jobStatusDot.style.backgroundColor = "var(--accent-green)";

        // Configure Save File button
        const downloadUrl = `/api/download/file/${jobId}`;
        directDownloadLink.href = downloadUrl;
        
        if (data.final_filename) {
            downloadReadyBtnText.textContent = `SAVE "${data.final_filename}"`;
        } else {
            downloadReadyBtnText.textContent = data.is_zip ? "SAVE BATCH ZIP ARCHIVE" : "SAVE FILE TO DISK";
        }

        downloadReadyBox.classList.remove("d-none");

        // Trigger immediate browser download
        const autoDownloadAnchor = document.createElement("a");
        autoDownloadAnchor.href = downloadUrl;
        autoDownloadAnchor.setAttribute("download", data.final_filename || "download");
        document.body.appendChild(autoDownloadAnchor);
        autoDownloadAnchor.click();
        document.body.removeChild(autoDownloadAnchor);
    }

    function resetProgressUI() {
        jobProgressBar.style.width = "0%";
        jobPercentBadge.textContent = "0%";
        jobStatusStep.textContent = "Initializing stream...";
        jobStatusDot.classList.add("pulse");
        jobStatusDot.style.backgroundColor = "var(--accent-cyan)";
        jobSpeedVal.textContent = "-- KB/s";
        jobSizeVal.textContent = "0 B / 0 B";
        jobEtaVal.textContent = "--:--";
        downloadReadyBox.classList.add("d-none");
        jobErrorBox.classList.add("d-none");
    }

    function showError(msg) {
        jobErrorBox.classList.remove("d-none");
        jobErrorMessage.textContent = msg;
        jobStatusStep.textContent = "Error during process";
        jobStatusDot.style.backgroundColor = "#ef4444";
        jobStatusDot.classList.remove("pulse");
    }

    function setButtonLoading(loading) {
        const spinner = btnStartDownload.querySelector(".btn-spinner");
        const content = btnStartDownload.querySelector(".btn-content");
        if (loading) {
            btnStartDownload.disabled = true;
            spinner.classList.remove("d-none");
            content.classList.add("opacity-50");
        } else {
            btnStartDownload.disabled = false;
            spinner.classList.add("d-none");
            content.classList.remove("opacity-50");
        }
    }

    // Settings Modal & Diagnostics
    const settingsModal = document.getElementById("settingsModal");
    if (settingsModal) {
        settingsModal.addEventListener("show.bs.modal", loadSystemStats);
    }

    async function loadSystemStats() {
        try {
            const resp = await fetch("/api/system/stats");
            const data = await resp.json();
            statsFileCount.textContent = `${data.temp_files_count || 0} items`;
            statsDiskUsage.textContent = `${data.temp_size_mb || 0} MB`;
        } catch (e) {
            console.error("Failed to load storage stats:", e);
        }
    }

    if (btnPurgeCache) {
        btnPurgeCache.addEventListener("click", async () => {
            btnPurgeCache.disabled = true;
            btnPurgeCache.textContent = "Purging...";
            try {
                await fetch("/api/system/clean", { method: "POST" });
                await loadSystemStats();
            } finally {
                btnPurgeCache.disabled = false;
                btnPurgeCache.innerHTML = `<i class="fa-solid fa-trash-can me-1"></i> Force Clear Server Cache`;
            }
        });
    }

    if (btnCheckUpdate) {
        btnCheckUpdate.addEventListener("click", async () => {
            btnCheckUpdate.disabled = true;
            btnCheckUpdate.innerHTML = `<span class="spinner-border spinner-border-sm me-1"></span> Checking...`;
            updateStatusAlert.classList.add("d-none");

            try {
                const resp = await fetch("/api/updater/check");
                const data = await resp.json();
                updateStatusAlert.classList.remove("d-none");

                if (data.update_available) {
                    updateStatusAlert.className = "alert alert-warning py-2 small mb-0";
                    updateStatusAlert.innerHTML = `
                        <strong>Update Available!</strong> Latest: v${data.latest_version} (Current: v${data.current_version}).
                        <button class="btn btn-sm btn-warning w-100 mt-2" id="btnApplyUpdate">
                            <i class="fa-solid fa-download me-1"></i> Upgrade yt-dlp Now
                        </button>
                    `;
                    document.getElementById("btnApplyUpdate").addEventListener("click", applyEngineUpdate);
                } else {
                    updateStatusAlert.className = "alert alert-success py-2 small mb-0";
                    updateStatusAlert.innerHTML = `<strong>Up to Date!</strong> yt-dlp engine is on latest release (v${data.current_version}).`;
                }
            } catch (e) {
                updateStatusAlert.className = "alert alert-danger py-2 small mb-0";
                updateStatusAlert.textContent = "Failed to connect to PyPI updates registry.";
                updateStatusAlert.classList.remove("d-none");
            } finally {
                btnCheckUpdate.disabled = false;
                btnCheckUpdate.innerHTML = `<i class="fa-solid fa-arrows-rotate me-1"></i> Check Update`;
            }
        });
    }

    async function applyEngineUpdate() {
        const btn = document.getElementById("btnApplyUpdate");
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = `<span class="spinner-border spinner-border-sm me-1"></span> Upgrading yt-dlp via pip...`;
        }
        try {
            const resp = await fetch("/api/updater/upgrade", { method: "POST" });
            const data = await resp.json();
            if (data.success) {
                updateStatusAlert.className = "alert alert-info py-2 small mb-0";
                updateStatusAlert.innerHTML = `<strong>Upgrade in progress!</strong> The background updater is installing the latest yt-dlp. Refresh in a moment.`;
            }
        } catch (e) {
            console.error("Upgrade trigger failed:", e);
        }
    }
});
