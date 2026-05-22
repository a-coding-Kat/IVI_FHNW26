/* ------------------------------------------------------------------ *
 * Eye-tracking orchestration for the metabolite dashboard.
 *
 * Loads the WebGazer library at runtime (from CDN — the local
 * webgazer.js in assets/ is a stub), then exposes window.gazeTracker
 * with start / calibrate / stop methods that the Dash buttons call
 * via clientside callbacks.
 *
 * Gaze samples are buffered for ~2 seconds and then pushed in a
 * single batch into the dcc.Store with id="gaze-batch-store" using
 * Dash 2.17's set_props clientside API. The Python side then appends
 * the batch to usability_gaze_log.csv.
 *
 * Why batched: WebGazer fires at ~30 Hz. Sending one HTTP request per
 * sample would freeze the UI inside 10 seconds. Batched flushes keep
 * the callback rate to ~0.5 Hz.
 * ------------------------------------------------------------------ */

(function () {
    const FLUSH_INTERVAL_MS = 2000;
    const CDN_SOURCES = [
        "https://webgazer.cs.brown.edu/webgazer.js",
        "https://cdn.jsdelivr.net/npm/webgazer@3.3.0/dist/webgazer.min.js",
    ];

    const GAZE_BUFFER = [];
    let sessionActive = false;
    let sessionStartedAt = null;
    let calibrationOpen = false;
    let webgazerLoaded = false;

    // --------------------------------------------------------- //
    //  Dynamic CDN loader for WebGazer
    // --------------------------------------------------------- //
    function injectScript(src) {
        return new Promise((resolve, reject) => {
            const s = document.createElement("script");
            s.src = src;
            s.async = true;
            s.onload = () => resolve(src);
            s.onerror = () => reject(new Error("failed: " + src));
            document.head.appendChild(s);
        });
    }

    async function loadWebGazer() {
        if (window.webgazer) { webgazerLoaded = true; return; }
        for (const src of CDN_SOURCES) {
            try {
                await injectScript(src);
                if (window.webgazer) {
                    webgazerLoaded = true;
                    console.log("[gaze] WebGazer loaded from", src);
                    return;
                }
            } catch (e) {
                console.warn("[gaze]", e.message);
            }
        }
        throw new Error("WebGazer could not be loaded from any CDN");
    }

    // --------------------------------------------------------- //
    //  Bridge to Dash: push batched samples into gaze-batch-store
    // --------------------------------------------------------- //
    function pushBatchToDash(batch) {
        if (window.dash_clientside && window.dash_clientside.set_props) {
            // Dash 2.17+ supported API for clientside prop updates.
            window.dash_clientside.set_props("gaze-batch-store",
                                              { data: batch });
        } else {
            // Fallback: stash on window for manual download.
            window._gazeBatches = window._gazeBatches || [];
            window._gazeBatches.push(batch);
        }
    }

    function flushBuffer() {
        if (!GAZE_BUFFER.length) return;
        const batch = {
            samples: GAZE_BUFFER.splice(0),
            flushed_at: Date.now(),
            session_started_at: sessionStartedAt,
        };
        pushBatchToDash(batch);
    }
    // Periodic flush loop, always running once tracking.js is loaded.
    setInterval(flushBuffer, FLUSH_INTERVAL_MS);

    // --------------------------------------------------------- //
    //  Active-tab detection for context-tagging each sample
    // --------------------------------------------------------- //
    function currentTabLabel() {
        const el = document.querySelector(".dash-tabs .tab--selected");
        return el ? el.innerText.trim() : "Unknown";
    }

    // --------------------------------------------------------- //
    //  Gaze callback (called by WebGazer at ~30 Hz)
    // --------------------------------------------------------- //
    function onGaze(data, elapsedTime) {
        if (!sessionActive || data == null || calibrationOpen) return;
        GAZE_BUFFER.push({
            t: Math.round(elapsedTime),
            x: Math.round(data.x),
            y: Math.round(data.y),
            tab: currentTabLabel(),
        });
    }

    // --------------------------------------------------------- //
    //  Calibration overlay
    //
    //  9-point grid; participant clicks each point 5 times while
    //  looking at it. WebGazer's recordScreenPosition seeds the
    //  ridge regression with click-located samples. Without this
    //  step the predictions are off by 200-400 px.
    // --------------------------------------------------------- //
    function buildCalibrationOverlay(onDone) {
        calibrationOpen = true;

        const overlay = document.createElement("div");
        overlay.id = "gaze-calibration-overlay";
        Object.assign(overlay.style, {
            position: "fixed", inset: "0",
            background: "rgba(15,23,42,0.45)",
            zIndex: "99998",
        });

        const note = document.createElement("div");
        note.setAttribute("data-static", "true");
        note.textContent = "Calibration — click each yellow dot 5 times while looking at it.";
        Object.assign(note.style, {
            position: "absolute", top: "16px", left: "50%",
            transform: "translateX(-50%)",
            background: "rgba(15,23,42,0.92)", color: "#fff",
            padding: "10px 16px", borderRadius: "8px",
            fontFamily: "Inter, system-ui, sans-serif", fontSize: "13px",
        });
        overlay.appendChild(note);

        const positions = [];
        for (const py of [0.08, 0.5, 0.92])
            for (const px of [0.08, 0.5, 0.92])
                positions.push([px, py]);

        let remaining = positions.length;

        positions.forEach(([px, py]) => {
            const dot = document.createElement("div");
            let clicks = 0;
            Object.assign(dot.style, {
                position: "absolute",
                left:  `calc(${px * 100}% - 22px)`,
                top:   `calc(${py * 100}% - 22px)`,
                width: "44px", height: "44px",
                borderRadius: "50%",
                background: "#f59e0b",
                color: "#0f172a", fontWeight: "700",
                fontFamily: "Inter, sans-serif", fontSize: "14px",
                boxShadow: "0 0 18px rgba(245,158,11,0.7)",
                cursor: "pointer",
                display: "flex", alignItems: "center", justifyContent: "center",
            });
            dot.textContent = "5";

            dot.addEventListener("click", () => {
                clicks++;
                dot.textContent = String(5 - clicks);
                if (window.webgazer && window.webgazer.recordScreenPosition) {
                    const r = dot.getBoundingClientRect();
                    window.webgazer.recordScreenPosition(
                        r.left + r.width / 2,
                        r.top + r.height / 2,
                        "click"
                    );
                }
                if (clicks >= 5) {
                    dot.remove();
                    remaining--;
                    if (remaining <= 0) {
                        overlay.remove();
                        calibrationOpen = false;
                        if (onDone) onDone();
                    }
                }
            });
            overlay.appendChild(dot);
        });

        document.body.appendChild(overlay);
    }

    // --------------------------------------------------------- //
    //  Public control surface (called by Dash clientside callbacks)
    // --------------------------------------------------------- //
    window.gazeTracker = {
        async start() {
            try {
                await loadWebGazer();
            } catch (e) {
                console.error("[gaze]", e);
                alert("Could not load WebGazer (offline?). Check the console.");
                return "error";
            }
            // Configure regression + tracker (idempotent — safe to call again).
            window.webgazer.setRegression("ridge").setTracker("TFFacemesh");
            window.webgazer.setGazeListener(onGaze);
            if (!window.webgazer.isReady || !window.webgazer.isReady()) {
                await window.webgazer.begin();
            }
            window.webgazer.showVideoPreview(true)
                            .showPredictionPoints(true);
            sessionActive = true;
            sessionStartedAt = Date.now();
            console.log("[gaze] tracker started");
            return "active";
        },

        calibrate() {
            if (!window.webgazer) {
                alert("Start the tracker first.");
                return;
            }
            // Pause sample push so calibration clicks don't end up in the log.
            sessionActive = false;
            buildCalibrationOverlay(() => {
                sessionActive = true;
                console.log("[gaze] calibration complete");
            });
        },

        async stop() {
            sessionActive = false;
            flushBuffer();
            if (window.webgazer) {
                try { window.webgazer.end(); } catch (e) {}
            }
            console.log("[gaze] tracker stopped");
        },
    };

    console.debug("[gaze] tracking.js ready — call window.gazeTracker.{start,calibrate,stop}");
})();
