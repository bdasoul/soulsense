(function () {
  "use strict";

  /* ── DOM refs ── */
  const dot        = document.getElementById("status-dot");
  const statusLbl  = document.getElementById("status-label");
  const rssiLbl    = document.getElementById("rssi-label");
  const meterBar   = document.getElementById("meter-bar");
  const meterVal   = document.getElementById("meter-value");
  const canvas     = document.getElementById("waterfall");
  const ctx        = canvas.getContext("2d");
  const windowIn   = document.getElementById("window-size");
  const windowVal  = document.getElementById("window-size-val");
  const smoothIn   = document.getElementById("smoothing");
  const smoothVal  = document.getElementById("smoothing-val");

  /* ── Waterfall state ── */
  const COL_W = 2;           // pixels per time-column
  let wfCols   = 0;          // how many columns drawn so far

  function resizeCanvas() {
    const rect = canvas.getBoundingClientRect();
    canvas.width  = Math.floor(rect.width);
    canvas.height = canvas.offsetHeight || 200;
    wfCols = 0;
  }

  window.addEventListener("resize", resizeCanvas);
  resizeCanvas();

  /* ── Heatmap colour map (black → blue → cyan → white) ── */
  function ampToColor(norm) {
    // norm: 0..1
    if (norm < 0.33) {
      const t = norm / 0.33;
      const r = 0, g = Math.round(t * 80), b = Math.round(t * 200);
      return `rgb(${r},${g},${b})`;
    } else if (norm < 0.66) {
      const t = (norm - 0.33) / 0.33;
      const r = Math.round(t * 0), g = Math.round(80 + t * 175), b = 200;
      return `rgb(${r},${g},${b})`;
    } else {
      const t = (norm - 0.66) / 0.34;
      const r = Math.round(t * 255), g = 255, b = Math.round(200 + t * 55);
      return `rgb(${r},${g},${b})`;
    }
  }

  function drawWaterfallColumn(amplitudes) {
    const W = canvas.width;
    const H = canvas.height;

    // Scroll existing content left by COL_W
    if (wfCols > 0) {
      const img = ctx.getImageData(COL_W, 0, W - COL_W, H);
      ctx.putImageData(img, 0, 0);
    }

    // Draw new column on the right edge
    const x = W - COL_W;
    const n = amplitudes.length;
    const maxAmp = Math.max(...amplitudes, 1);

    for (let i = 0; i < n; i++) {
      const y     = Math.floor((i / n) * H);
      const yNext = Math.floor(((i + 1) / n) * H);
      ctx.fillStyle = ampToColor(amplitudes[i] / maxAmp);
      ctx.fillRect(x, y, COL_W, Math.max(1, yNext - y));
    }

    wfCols++;
  }

  /* ── Motion meter ── */
  function updateMeter(motion) {
    const pct = (motion * 100).toFixed(0);
    meterBar.style.width = pct + "%";
    meterVal.textContent = motion.toFixed(2);
  }

  /* ── Status ── */
  function setStatus(connected) {
    dot.className = "dot " + (connected ? "connected" : "disconnected");
    statusLbl.textContent = connected ? "Live" : "Disconnected";
  }

  /* ── Params ── */
  let paramTimer = null;
  function sendParams(ws) {
    clearTimeout(paramTimer);
    paramTimer = setTimeout(() => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
          type: "params",
          window_size: parseInt(windowIn.value, 10),
          smoothing: parseInt(smoothIn.value, 10) / 100,
        }));
      }
    }, 200);
  }

  /* ── WebSocket ── */
  let ws = null;
  let reconnectDelay = 1000;

  function connect() {
    const proto = location.protocol === "https:" ? "wss" : "ws";
    ws = new WebSocket(`${proto}://${location.host}/ws`);

    ws.onopen = () => { reconnectDelay = 1000; };

    ws.onmessage = (e) => {
      let msg;
      try { msg = JSON.parse(e.data); } catch { return; }

      if (msg.type === "status") {
        setStatus(msg.connected);
      } else if (msg.type === "csi") {
        updateMeter(msg.motion);
        rssiLbl.textContent = `RSSI ${msg.rssi} dBm`;
        if (msg.amplitudes && msg.amplitudes.length) {
          drawWaterfallColumn(msg.amplitudes);
        }
      }
    };

    ws.onclose = () => {
      setStatus(false);
      setTimeout(connect, reconnectDelay);
      reconnectDelay = Math.min(reconnectDelay * 1.5, 10000);
    };

    ws.onerror = () => ws.close();
  }

  /* ── Slider bindings ── */
  windowIn.addEventListener("input", () => {
    windowVal.textContent = windowIn.value;
    sendParams(ws);
  });

  smoothIn.addEventListener("input", () => {
    smoothVal.textContent = (parseInt(smoothIn.value, 10) / 100).toFixed(2);
    sendParams(ws);
  });

  connect();
})();
