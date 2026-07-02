const stateKey = "video-progress-bar-studio";

let chapters = [{ time: "00:00:00:00", title: "开场" }];
let currentImageData = "";
let generatedVideo = false;
let previewTimer = null;
let gifOptions = [];

let videoPlayer = null;
let currentVideoFile = null;
let currentVideoName = null;

const $ = (id) => document.getElementById(id);

const defaultChapters = [
    { time: "00:00:00:00", title: "开场" },
];

let availableFonts = [];
let currentFontPath = "";
let currentFontName = "默认";
let currentFontRisky = false;

async function boot() {
    bindEvents();
    await loadGifOptions();
    await loadOutputDir();
    await loadFontOptions();
    loadState();
    updateMarkerPreview();
    renderChapters();
    checkHealth();
    schedulePreview(50);
}

function bindEvents() {
    [
        "width",
        "height",
        "fontSize",
        "fps",
        "totalDuration",
        "bgColor",
        "textColor",
        "separatorColor",
        "progressColor",
        "separatorWidth",
        "progressOpacity",
        "markerGif",
        "markerSize",
        "markerOffsetX",
        "markerOffsetY",
    ].forEach((id) => {
        $(id).addEventListener("input", () => {
            updateRangeLabels();
            updateMarkerPreview();
            saveState();
            schedulePreview();
        });
    });

    $("addChapter").addEventListener("click", addChapter);
    $("clearChapters").addEventListener("click", clearChapters);
    $("presetButton").addEventListener("click", applyPreset);
    $("generateImageBtn").addEventListener("click", () => generateImage(false));
    $("downloadImageBtn").addEventListener("click", downloadImage);
    $("generateVideoBtn").addEventListener("click", generateVideo);
    $("uploadGifBtn").addEventListener("click", () => $("gifUpload").click());
    $("gifUpload").addEventListener("change", uploadGif);
    $("deleteGifBtn").addEventListener("click", deleteSelectedGif);
    $("previewImage").addEventListener("load", updateVideoMarkerPreview);
    window.addEventListener("resize", updateVideoMarkerPreview);
    $("outputDirText").addEventListener("click", openPathModal);
    $("videoFont").addEventListener("change", onFontChange);
    $("importVideoBtn").addEventListener("click", () => $("videoInput").click());
    $("importVideoBtn2").addEventListener("click", () => $("videoInput").click());
    $("videoInput").addEventListener("change", (e) => handleVideoImport(e.target.files[0]));
    $("addChapterAtCurrentBtn").addEventListener("click", addChapterAtCurrentTime);
    $("generateProgressOnlyBtn").addEventListener("click", generateProgressOnlyVideo);
    document.addEventListener("keydown", (e) => {
        if (e.code === "Space" && !["INPUT", "TEXTAREA"].includes(e.target.tagName)) {
            e.preventDefault();
            if (videoPlayer) {
                if (videoPlayer.paused()) {
                    videoPlayer.play();
                } else {
                    videoPlayer.pause();
                }
            }
        }
    });
    updateRangeLabels();
    initResizeHandle();
    initDropZone();
}

async function loadGifOptions(selectedId = null) {
    try {
        const response = await fetch("/gif_options");
        const data = await response.json();
        gifOptions = Array.isArray(data.options) ? data.options : [];
    } catch {
        gifOptions = [{ id: "none", label: "\u4e0d\u4f7f\u7528", url: "", available: true, custom: false }];
    }

    const select = $("markerGif");
    const previousValue = selectedId || select.value;
    select.innerHTML = "";
    gifOptions.forEach((option) => {
        const item = document.createElement("option");
        item.value = option.id;
        item.textContent = option.available ? option.label : `${option.label}????`;
        item.disabled = !option.available;
        select.appendChild(item);
    });
    if (previousValue && gifOptions.some((option) => option.id === previousValue && option.available)) {
        select.value = previousValue;
    }
}

async function loadFontOptions() {
    try {
        const response = await fetch("/font_options");
        const data = await response.json();
        if (data.success) {
            availableFonts = data.fonts || [];
            currentFontPath = data.current.font_path || "";
            currentFontName = data.current.font_name || "默认";

            const currentFont = availableFonts.find(f => f.path === currentFontPath);
            currentFontRisky = currentFont ? currentFont.risky : false;

            renderFontOptions();
            updateFontRiskWarning();
        }
    } catch (err) {
        console.error("Failed to load font options:", err);
        availableFonts = [];
    }
}

function renderFontOptions() {
    const select = $("videoFont");
    select.innerHTML = "";

    const defaultOption = document.createElement("option");
    defaultOption.value = "";
    defaultOption.textContent = "默认字体";
    select.appendChild(defaultOption);

    availableFonts.forEach((font) => {
        const option = document.createElement("option");
        option.value = font.path;
        option.textContent = font.name + (font.risky ? " ⚠️" : "");
        select.appendChild(option);
    });

    const savedPath = currentFontPath;
    if (savedPath) {
        const matchingFont = availableFonts.find((f) => f.path === savedPath);
        if (matchingFont) {
            select.value = savedPath;
        } else {
            select.value = "";
            currentFontPath = "";
            currentFontName = "默认";
            currentFontRisky = false;
        }
    } else {
        select.value = "";
        currentFontRisky = false;
    }
}

function updateFontRiskWarning() {
    const warning = $("fontRiskWarning");
    if (currentFontRisky) {
        warning.hidden = false;
    } else {
        warning.hidden = true;
    }
}

async function onFontChange() {
    const select = $("videoFont");
    const selectedPath = select.value;

    if (!selectedPath) {
        currentFontPath = "";
        currentFontName = "默认";
        currentFontRisky = false;
    } else {
        const selectedFont = availableFonts.find((f) => f.path === selectedPath);
        if (selectedFont) {
            currentFontPath = selectedFont.path;
            currentFontName = selectedFont.name;
            currentFontRisky = selectedFont.risky || false;
        }
    }

    updateFontRiskWarning();

    try {
        await postJson("/font", {
            font_path: currentFontPath,
            font_name: currentFontName
        });
        schedulePreview(200);
    } catch (err) {
        console.error("Failed to save font setting:", err);
    }
}

function loadState() {
    const saved = localStorage.getItem(stateKey);
    if (!saved) {
        chapters = [...defaultChapters];
        $("markerGif").value = "none";
        return;
    }

    try {
        const data = JSON.parse(saved);
        Object.entries(data.settings || {}).forEach(([key, value]) => {
            if ($(key)) $(key).value = value;
        });
        chapters = Array.isArray(data.chapters) && data.chapters.length ? data.chapters : [...defaultChapters];
    } catch {
        chapters = [...defaultChapters];
    }
}

function saveState() {
    localStorage.setItem(
        stateKey,
        JSON.stringify({
            settings: collectSettings(),
            chapters,
        })
    );
}

function collectSettings() {
    return {
        width: $("width").value,
        height: $("height").value,
        fontSize: $("fontSize").value,
        fps: $("fps").value,
        totalDuration: $("totalDuration").value,
        bgColor: $("bgColor").value,
        textColor: $("textColor").value,
        separatorColor: $("separatorColor").value,
        progressColor: $("progressColor").value,
        separatorWidth: $("separatorWidth").value,
        progressOpacity: $("progressOpacity").value,
        markerGif: $("markerGif").value,
        markerSize: $("markerSize").value,
        markerOffsetX: $("markerOffsetX").value,
        markerOffsetY: $("markerOffsetY").value,
    };
}

function requestPayload() {
    const settings = collectSettings();
    const payload = {
        total_duration: settings.totalDuration,
        chapters,
        width: Number(settings.width) || 1920,
        height: Number(settings.height) || 90,
        font_size: Number(settings.fontSize) || 28,
        fps: Number(settings.fps) || 30,
        bg_color: settings.bgColor,
        text_color: settings.textColor,
        separator_color: settings.separatorColor,
        progress_color: settings.progressColor,
        separator_width: Number(settings.separatorWidth) || 8,
        progress_opacity: Number(settings.progressOpacity) || 28,
        marker_gif: settings.markerGif || "none",
        marker_size: Number(settings.markerSize) || 46,
        marker_offset_x: Number(settings.markerOffsetX) || 0,
        marker_offset_y: Number(settings.markerOffsetY) || 0,
    };
    if (currentVideoName) {
        payload.video_name = currentVideoName;
    }
    return payload;
}

function renderChapters() {
    const list = $("chaptersList");
    list.innerHTML = "";

    chapters.forEach((chapter, index) => {
        const item = document.createElement("article");
        item.className = "chapter-item";
        item.innerHTML = `
            <input class="chapter-time" aria-label="章节时间" value="${escapeHtml(chapter.time)}" placeholder="0:00">
            <textarea class="chapter-title" aria-label="章节标题" rows="1" placeholder="章节标题">${escapeHtml(chapter.title)}</textarea>
            <div class="chapter-actions">
                <button type="button" title="上移" data-action="up">↑</button>
                <button type="button" title="下移" data-action="down">↓</button>
                <button type="button" title="插入" data-action="insert">+</button>
                <button type="button" title="删除" data-action="remove">×</button>
            </div>
        `;

        const timeInput = item.querySelector(".chapter-time");
        const titleInput = item.querySelector(".chapter-title");
        timeInput.addEventListener("input", () => updateChapter(index, "time", timeInput.value));
        titleInput.addEventListener("input", () => {
            titleInput.style.height = "auto";
            titleInput.style.height = `${titleInput.scrollHeight}px`;
            updateChapter(index, "title", titleInput.value);
        });

        item.querySelectorAll("button").forEach((button) => {
            button.addEventListener("click", () => handleChapterAction(index, button.dataset.action));
        });

        list.appendChild(item);
        titleInput.style.height = `${titleInput.scrollHeight}px`;
    });
}

function updateChapter(index, field, value) {
    chapters[index][field] = value;
    saveState();
    schedulePreview();
}

function handleChapterAction(index, action) {
    if (action === "remove") {
        chapters.splice(index, 1);
    }
    if (action === "insert") {
        chapters.splice(index + 1, 0, { time: chapters[index]?.time || "0:00", title: "新章节" });
    }
    if (action === "up" && index > 0) {
        [chapters[index - 1], chapters[index]] = [chapters[index], chapters[index - 1]];
    }
    if (action === "down" && index < chapters.length - 1) {
        [chapters[index + 1], chapters[index]] = [chapters[index], chapters[index + 1]];
    }
    renderChapters();
    saveState();
    schedulePreview();
}

function addChapter() {
    chapters.push({ time: "0:00", title: "新章节" });
    renderChapters();
    saveState();
    schedulePreview();
}

function clearChapters() {
    chapters = [{ time: "0:00", title: "开场" }];
    renderChapters();
    saveState();
    setStatus("已重置章节", "muted");
}

function applyPreset() {
    $("width").value = 1920;
    $("height").value = 88;
    $("fontSize").value = 28;
    $("fps").value = 30;
    $("totalDuration").value = "10:00";
    $("bgColor").value = "#f8fafc";
    $("textColor").value = "#111827";
    $("separatorColor").value = "#111827";
    $("progressColor").value = "#ef4444";
    $("separatorWidth").value = 8;
    $("progressOpacity").value = 28;
    $("markerGif").value = "none";
    $("markerSize").value = 46;
    $("markerOffsetX").value = 0;
    $("markerOffsetY").value = 0;
    chapters = [...defaultChapters];
    updateRangeLabels();
    updateMarkerPreview();
    renderChapters();
    saveState();
    schedulePreview(50);
}

function updateRangeLabels() {
    $("separatorWidthValue").textContent = `${$("separatorWidth").value}px`;
    $("progressOpacityValue").textContent = `${$("progressOpacity").value}%`;
    $("markerSizeValue").textContent = `${$("markerSize").value}px`;
    $("markerOffsetXValue").textContent = `${$("markerOffsetX").value}px`;
    $("markerOffsetYValue").textContent = `${$("markerOffsetY").value}px`;
}

function updateMarkerPreview() {
    const selected = gifOptions.find((option) => option.id === $("markerGif").value);
    const preview = $("markerPreview");
    if (!selected || selected.id === "none" || !selected.url) {
        preview.hidden = true;
        $("markerPreviewImage").removeAttribute("src");
        $("deleteGifBtn").hidden = true;
        updateVideoMarkerPreview();
        return;
    }
    $("markerPreviewImage").src = selected.url;
    $("markerPreviewImage").style.width = `${$("markerSize").value}px`;
    $("markerPreviewImage").style.height = `${$("markerSize").value}px`;
    $("markerPreviewText").textContent = "";
    $("deleteGifBtn").hidden = !selected.custom;
    preview.hidden = false;
    updateVideoMarkerPreview();
}

function updateVideoMarkerPreview() {
    const selected = gifOptions.find((option) => option.id === $("markerGif").value);
    const marker = $("videoMarkerPreview");
    const progressRef = $("previewProgressRef");
    const image = $("previewImage");
    const frame = $("previewFrame");
    if (frame.hidden || !image.complete || !image.clientWidth) {
        marker.hidden = true;
        progressRef.hidden = true;
        marker.removeAttribute("src");
        return;
    }

    progressRef.style.width = `${image.clientWidth * 0.5}px`;
    progressRef.style.height = `${image.clientHeight}px`;
    progressRef.style.backgroundColor = hexToRgba($("progressColor").value, Number($("progressOpacity").value) / 100);

    if (!selected || selected.id === "none" || !selected.url) {
        marker.hidden = true;
        progressRef.hidden = true;
        marker.removeAttribute("src");
        return;
    }

    progressRef.hidden = false;
    const scale = image.clientWidth / image.naturalWidth;
    const markerSize = Number($("markerSize").value) * scale;
    const offsetX = Number($("markerOffsetX").value) * scale;
    const offsetY = Number($("markerOffsetY").value) * scale;
    const x = Math.min(Math.max(0, image.clientWidth * 0.5 - markerSize / 2 + offsetX), image.clientWidth - markerSize);
    const y = image.clientHeight * 0.5 - markerSize / 2 + offsetY;

    marker.src = selected.url;
    marker.style.width = `${markerSize}px`;
    marker.style.height = `${markerSize}px`;
    marker.style.left = `${x}px`;
    marker.style.top = `${y}px`;
    marker.hidden = false;
}

function hexToRgba(hex, alpha) {
    const normalized = /^#[0-9a-f]{6}$/i.test(hex) ? hex : "#ef4444";
    const r = parseInt(normalized.slice(1, 3), 16);
    const g = parseInt(normalized.slice(3, 5), 16);
    const b = parseInt(normalized.slice(5, 7), 16);
    return `rgba(${r}, ${g}, ${b}, ${Math.max(0, Math.min(alpha, 1))})`;
}

async function uploadGif() {
    const fileInput = $("gifUpload");
    const file = fileInput.files && fileInput.files[0];
    if (!file) return;
    const formData = new FormData();
    formData.append("gif", file);
    setBusy(true, "\u5220\u9664 GIF...");
    try {
        const response = await fetch("/upload_gif", { method: "POST", body: formData });
        const result = await response.json();
        if (!result.success) throw new Error(result.message || "????");
        await loadGifOptions(result.id);
        $("markerGif").value = result.id;
        updateMarkerPreview();
        saveState();
        setStatus("GIF \u5df2\u4e0a\u4f20", "ok");
    } catch (error) {
        setStatus(error.message, "error");
    } finally {
        fileInput.value = "";
        setBusy(false);
    }
}

async function deleteSelectedGif() {
    const selectedId = $("markerGif").value;
    if (!selectedId.startsWith("custom:")) return;
    setBusy(true, "\u5220\u9664 GIF...");
    try {
        const result = await postJson("/delete_gif", { id: selectedId });
        if (!result.success) throw new Error(result.message || "????");
        await loadGifOptions("none");
        $("markerGif").value = "none";
        updateMarkerPreview();
        saveState();
        setStatus("GIF \u5df2\u5220\u9664", "ok");
    } catch (error) {
        setStatus(error.message, "error");
    } finally {
        setBusy(false);
    }
}

function schedulePreview(delay = 350) {
    clearTimeout(previewTimer);
    previewTimer = setTimeout(() => generateImage(true), delay);
}

async function generateImage(isAuto = false) {
    if (!chapters.length) return;
    setBusy(true, isAuto ? "刷新预览..." : "生成图片...");
    generatedVideo = false;

    try {
        const result = await postJson("/generate", requestPayload());
        if (!result.success) throw new Error(result.message || "生成失败");
        currentImageData = result.image;
        $("previewImage").src = result.image;
        $("previewFrame").hidden = false;
        $("placeholder").hidden = true;
        updateVideoMarkerPreview();
        $("downloadImageBtn").disabled = false;
        setStatus("图片已更新", "ok");
    } catch (error) {
        if (!isAuto) setStatus(error.message, "error");
    } finally {
        setBusy(false);
    }
}

async function generateVideo() {
    if (!chapters.length) {
        setStatus("\u8bf7\u5148\u6dfb\u52a0\u7ae0\u8282", "error");
        return;
    }

    const startedAt = Date.now();
    setBusy(true, `\u51c6\u5907\u751f\u6210\u89c6\u9891\uff1a0.00%\uff5c\u7528\u65f6 ${formatElapsed(0)}`);
    $("generateVideoBtn").disabled = true;
    $("generateProgressOnlyBtn").disabled = true;
    generatedVideo = false;

    try {
        if (currentVideoFile) {
            const formData = new FormData();
            formData.append("video", currentVideoFile);
            formData.append("config", JSON.stringify(requestPayload()));

            const response = await fetch("/generate_video_with_video", {
                method: "POST",
                body: formData
            });
            const result = await response.json();

            if (!result.success) throw new Error(result.message || "视频生成失败");
            await watchVideoProgress(result.job_id, startedAt);
        } else {
            const result = await postJson("/generate_video", requestPayload());
            if (!result.success) throw new Error(result.message || "视频生成失败");
            await watchVideoProgress(result.job_id, startedAt);
        }
    } catch (error) {
        setStatus(error.message, "error");
    } finally {
        $("generateVideoBtn").disabled = false;
        $("generateProgressOnlyBtn").disabled = false;
        setBusy(false);
    }
}

async function generateProgressOnlyVideo() {
    if (!chapters.length) {
        setStatus("\u8bf7\u5148\u6dfb\u52a0\u7ae0\u8282", "error");
        return;
    }

    const startedAt = Date.now();
    setBusy(true, `\u51c6\u5907\u751f\u6210\u8fdb\u5ea6\u6761\uff1a0.00%\uff5c\u7528\u65f6 ${formatElapsed(0)}`);
    $("generateVideoBtn").disabled = true;
    $("generateProgressOnlyBtn").disabled = true;
    generatedVideo = false;

    try {
        const result = await postJson("/generate_video", requestPayload());
        if (!result.success) throw new Error(result.message || "视频生成失败");
        await watchVideoProgress(result.job_id, startedAt);
    } catch (error) {
        setStatus(error.message, "error");
    } finally {
        $("generateVideoBtn").disabled = false;
        $("generateProgressOnlyBtn").disabled = false;
        setBusy(false);
    }
}

async function watchVideoProgress(jobId, startedAt) {
    if (!jobId) throw new Error("\u6ca1\u6709\u62ff\u5230\u89c6\u9891\u4efb\u52a1 ID");
    while (true) {
        await sleep(500);
        const response = await fetch(`/video_progress/${encodeURIComponent(jobId)}`);
        const result = await response.json();
        if (!result.success) throw new Error(result.message || "\u65e0\u6cd5\u8bfb\u53d6\u89c6\u9891\u8fdb\u5ea6");

        const progress = Math.max(0, Math.min(Number(result.progress) || 0, 100));
        const elapsed = formatElapsed((Date.now() - startedAt) / 1000);
        if (result.status === "error") throw new Error(result.message || "\u89c6\u9891\u751f\u6210\u5931\u8d25");
        if (result.status === "done") {
            generatedVideo = true;
            if (window.pywebview && window.pywebview.api) {
                window.pywebview.api.reveal_in_finder();
            }
            setStatus(`\u89c6\u9891\u5df2\u751f\u6210\uff0c\u603b\u8ba1\u7528\u65f6 ${elapsed}`, "ok");
            return;
        }
        setStatus(`\u6b63\u5728\u751f\u6210\u89c6\u9891\uff1a${progress.toFixed(2)}%\uff5c\u7528\u65f6 ${elapsed}`, "muted");
    }
}

function downloadImage() {
    if (!currentImageData) return;
    const link = document.createElement("a");
    link.href = currentImageData;
    link.download = `video-progress-bar-${timestamp()}.png`;
    link.click();
}

async function checkHealth() {
    try {
        const response = await fetch("/health");
        const data = await response.json();
        $("healthDot").classList.toggle("dot--ok", Boolean(data.ffmpeg));
        $("healthText").textContent = data.ffmpeg ? "FFmpeg 可用" : "未找到 FFmpeg";
    } catch {
        $("healthText").textContent = "服务未就绪";
    }
}

async function postJson(url, payload) {
    const response = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });
    return response.json();
}

function setBusy(isBusy, message = "") {
    $("spinner").hidden = !isBusy;
    if (message) setStatus(message, "muted");
}

function setStatus(message, type = "muted") {
    $("statusText").textContent = message;
    $("statusText").dataset.type = type;
}

function timestamp() {
    return new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-");
}

function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
}

function formatElapsed(seconds) {
    if (!seconds || isNaN(seconds)) return "00:00";
    const total = Math.max(0, Math.floor(seconds));
    const hours = Math.floor(total / 3600);
    const minutes = Math.floor((total % 3600) / 60);
    const rest = String(total % 60).padStart(2, "0");
    if (hours > 0) {
        return `${hours}:${String(minutes).padStart(2, "0")}:${rest}`;
    }
    return `${minutes}:${rest}`;
}

function escapeHtml(value) {
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;");
}

let currentOutputDir = "";
let defaultOutputDir = "";

async function loadOutputDir() {
    try {
        const response = await fetch("/output_dir");
        const data = await response.json();
        if (data.success) {
            currentOutputDir = data.output_dir;
            defaultOutputDir = data.default_dir;
            updateOutputDirDisplay();
        }
    } catch (err) {
        console.error("Failed to load output dir:", err);
    }
}

function updateOutputDirDisplay() {
    const display = $("outputDirText");
    const shortPath = shortenPath(currentOutputDir, 30);
    display.textContent = `📁 ${shortPath}`;
    display.title = currentOutputDir;
}

function shortenPath(path, maxLen) {
    if (path.length <= maxLen) return path;
    const parts = path.split("/");
    if (parts.length <= 3) return path;
    return parts[0] + "/.../" + parts.slice(-2).join("/");
}

async function openPathModal() {
    try {
        if (window.pywebview && window.pywebview.api) {
            const path = await window.pywebview.api.browse_folder();
            if (path) {
                currentOutputDir = path;
                updateOutputDirDisplay();
            }
        }
    } catch (err) {
        console.error("Browse folder error:", err);
    }
}

function initVideoPlayer() {
    if (!window.videojs) {
        console.error("Video.js not loaded");
        return;
    }

    if (videoPlayer) {
        return;
    }

    const videoEl = $("videoPlayer");
    videoPlayer = videojs(videoEl, {
        controls: true,
        autoplay: false,
        preload: "auto",
        fluid: true,
        responsive: true,
        playbackRates: [0.5, 1, 1.5, 2],
        controlBar: {
            children: [
                "playToggle",
                "volumePanel",
                "currentTimeDisplay",
                "timeDivider",
                "durationDisplay",
                "progressControl",
                "playbackRateMenuButton",
                "fullscreenToggle",
            ],
        },
    });

    videoPlayer.on("timeupdate", updateVideoTimeDisplay);

    videoPlayer.on("loadedmetadata", () => {
        const duration = videoPlayer.duration();
        const videoWidth = videoPlayer.videoWidth();
        const videoHeight = videoPlayer.videoHeight();

        if (duration > 0) {
            $("totalDuration").value = formatTime(duration, true);
        }

        if (videoWidth && videoHeight) {
            const progressHeight = Math.round(videoWidth / 1920 * 90);
            const fontSize = Math.round(28 * (videoWidth / 1920));
            $("width").value = videoWidth;
            $("height").value = progressHeight;
            $("fontSize").value = Math.max(12, fontSize);
        }

        schedulePreview();
    });

    videoPlayer.on("error", () => {
        setStatus("视频加载失败，请尝试其他格式", "error");
    });
}

function updateVideoTimeDisplay() {
    if (!videoPlayer) return;
    const current = videoPlayer.currentTime() || 0;
    const duration = videoPlayer.duration() || 0;
    $("videoTimeDisplay").textContent = `${formatTime(current, true)} / ${formatTime(duration, true)}`;
}

function formatTime(seconds, includeFrames = false) {
    if (!seconds || isNaN(seconds)) return "00:00";
    const total = Math.max(0, Math.floor(seconds));
    const hours = Math.floor(total / 3600);
    const minutes = Math.floor((total % 3600) / 60);
    const secs = total % 60;
    let result;
    result = `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
    if (includeFrames) {
        const fps = parseInt($("fps")?.value) || 30;
        const frame = Math.round((seconds - total) * fps);
        result += `:${String(frame).padStart(2, "0")}`;
    }
    return result;
}

function parseTimeToSecondsWithFrames(timeStr, fps = 30) {
    if (!timeStr) return 0;
    const parts = String(timeStr).split(":").map(p => parseFloat(p) || 0);
    if (parts.length === 1) return parts[0];
    if (parts.length === 2) return parts[0] * 60 + parts[1];
    if (parts.length === 3) return parts[0] * 3600 + parts[1] * 60 + parts[2];
    if (parts.length >= 4) {
        const frames = parts[3] || 0;
        return parts[0] * 3600 + parts[1] * 60 + parts[2] + frames / fps;
    }
    return 0;
}

async function handleVideoImport(file) {
    if (!file) return;

    const validTypes = ["video/mp4", "video/webm", "video/quicktime", "video/x-msvideo"];
    const validExtensions = [".mp4", ".webm", ".mov", ".avi"];
    const hasValidType = validTypes.includes(file.type);
    const hasValidExt = validExtensions.some((ext) => file.name.toLowerCase().endsWith(ext));

    if (!hasValidType && !hasValidExt) {
        setStatus("不支持的视频格式，请使用 MP4、WebM、MOV 或 AVI", "error");
        $("videoInput").value = "";
        return;
    }

    const maxSize = 500 * 1024 * 1024;
    if (file.size > maxSize) {
        setStatus("视频文件过大，请使用 500MB 以下的文件", "error");
        $("videoInput").value = "";
        return;
    }

    currentVideoFile = file;
    currentVideoName = file.name.replace(/\.[^.]+$/, "");
    const url = URL.createObjectURL(file);

    if (!videoPlayer) {
        initVideoPlayer();
    }

    setBusy(true, "加载视频...");
    try {
        videoPlayer.src({ src: url, type: file.type || "video/mp4" });
        videoPlayer.load();

        $("videoContainer").hidden = false;
        $("videoPlaceholder").hidden = true;

        const formData = new FormData();
        formData.append("video", file);

        try {
            const response = await fetch("/video_info", {
                method: "POST",
                body: formData
            });
            const data = await response.json();
            if (data.success) {
                $("fps").value = Math.min(60, Math.max(1, data.fps || 30));
            }
        } catch (err) {
            console.error("获取视频信息失败:", err);
        }

        $("generateProgressOnlyBtn").hidden = false;
        setStatus("视频已导入，拖动播放轴到指定位置后点击添加章节", "ok");
    } catch (err) {
        console.error("Video import error:", err);
        setStatus("视频加载失败: " + err.message, "error");
    } finally {
        setBusy(false);
    }
}

function addChapterAtCurrentTime() {
    if (!videoPlayer) {
        setStatus("请先导入视频", "error");
        return;
    }

    const currentTime = videoPlayer.currentTime();
    if (!currentTime || currentTime <= 0) {
        setStatus("视频尚未开始播放", "error");
        return;
    }

    const formattedTime = formatTime(currentTime, true);
    chapters.push({
        time: formattedTime,
        title: "新章节",
    });

    sortChaptersByTime();
    renderChapters();
    saveState();
    schedulePreview();

    setStatus(`已添加章节：${formattedTime}`, "ok");
}

function sortChaptersByTime() {
    chapters.sort((a, b) => {
        return parseTimeToSecondsWithFrames(a.time) - parseTimeToSecondsWithFrames(b.time);
    });
}

function parseTimeToSeconds(timeStr) {
    if (!timeStr) return 0;
    const parts = String(timeStr)
        .split(":")
        .map((p) => parseFloat(p) || 0);
    if (parts.length === 1) return parts[0];
    if (parts.length === 2) return parts[0] * 60 + parts[1];
    if (parts.length >= 3) return parts[0] * 3600 + parts[1] * 60 + parts[2];
    return 0;
}

function initResizeHandle() {
    const handle = document.querySelector(".resize-handle");
    const previewArea = document.querySelector(".preview-area");
    const imagePreview = document.querySelector(".preview--image");
    const videoPreview = document.querySelector(".preview--video");

    if (!handle || !previewArea || !imagePreview || !videoPreview) return;

    let isResizing = false;
    let startY = 0;
    let startHeight = 0;

    handle.addEventListener("mousedown", (e) => {
        isResizing = true;
        startY = e.clientY;
        startHeight = imagePreview.offsetHeight;
        document.body.style.cursor = "row-resize";
        document.body.style.userSelect = "none";
    });

    document.addEventListener("mousemove", (e) => {
        if (!isResizing) return;
        const delta = startY - e.clientY;
        const newHeight = Math.max(60, Math.min(600, startHeight + delta));
        imagePreview.style.flex = "none";
        imagePreview.style.height = newHeight + "px";
    });

    document.addEventListener("mouseup", () => {
        if (isResizing) {
            isResizing = false;
            document.body.style.cursor = "";
            document.body.style.userSelect = "";
        }
    });
}

function initDropZone() {
    const dropZone = document.getElementById("dropZone");
    if (!dropZone) return;

    dropZone.addEventListener("dragover", (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropZone.classList.add("dragover");
    });

    dropZone.addEventListener("dragleave", (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropZone.classList.remove("dragover");
    });

    dropZone.addEventListener("drop", (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropZone.classList.remove("dragover");

        const files = e.dataTransfer.files;
        if (files.length > 0) {
            const file = files[0];
            if (file.type.startsWith("video/")) {
                handleVideoImport(file);
            } else {
                setStatus("请拖拽视频文件", "error");
            }
        }
    });

    const videoPlaceholder = document.getElementById("videoPlaceholder");
    if (videoPlaceholder) {
        videoPlaceholder.addEventListener("dragover", (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropZone.classList.add("dragover");
        });

        videoPlaceholder.addEventListener("dragleave", (e) => {
            e.preventDefault();
            e.stopPropagation();
            if (!videoPlaceholder.contains(e.relatedTarget)) {
                dropZone.classList.remove("dragover");
            }
        });

        videoPlaceholder.addEventListener("drop", (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropZone.classList.remove("dragover");

            const files = e.dataTransfer.files;
            if (files.length > 0) {
                const file = files[0];
                if (file.type.startsWith("video/")) {
                    handleVideoImport(file);
                } else {
                    setStatus("请拖拽视频文件", "error");
                }
            }
        });
    }
}

document.addEventListener("DOMContentLoaded", boot);
