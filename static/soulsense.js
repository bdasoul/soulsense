(function () {
  "use strict";

  const WAVE_HISTORY = 300;

  /* ── State ── */
  let motion       = 0;
  let motionTarget = 0;
  let energy       = 0;
  let spread       = 0;
  let velocity     = 0;
  const waveData   = new Float32Array(WAVE_HISTORY);
  let waveHead     = 0;

  /* ── DOM ── */
  const ringMain   = document.getElementById("ring-main");
  const ringGlow   = document.getElementById("ring-glow");
  const ringFill   = document.getElementById("ring-fill");
  const ringValue  = document.getElementById("ring-value");
  const ticksG     = document.getElementById("ticks");
  const dot        = document.getElementById("status-dot");
  const statusTxt  = document.getElementById("status-text");
  const rssiTxt    = document.getElementById("rssi-text");
  const bgCanvas   = document.getElementById("bg");
  const waveCanvas = document.getElementById("wave");
  const bgCtx      = bgCanvas.getContext("2d");
  const waveCtx    = waveCanvas.getContext("2d");

  /* Secondary metric bars */
  const energyBar  = document.getElementById("energy-bar");
  const spreadBar  = document.getElementById("spread-bar");
  const velocityBar= document.getElementById("velocity-bar");
  const energyVal  = document.getElementById("energy-val");
  const spreadVal  = document.getElementById("spread-val");
  const velocityVal= document.getElementById("velocity-val");

  /* ── Build tick marks ── */
  (function buildTicks() {
    const N = 48;
    for (let i = 0; i < N; i++) {
      const angle = (i / N) * Math.PI * 2 - Math.PI / 2;
      const r0 = 150, r1 = 158;
      const x0 = 200 + Math.cos(angle) * r0;
      const y0 = 200 + Math.sin(angle) * r0;
      const x1 = 200 + Math.cos(angle) * r1;
      const y1 = 200 + Math.sin(angle) * r1;
      const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
      line.setAttribute("x1", x0); line.setAttribute("y1", y0);
      line.setAttribute("x2", x1); line.setAttribute("y2", y1);
      line.setAttribute("class", "tick");
      ticksG.appendChild(line);
    }
  })();

  /* ── Resize ── */
  function resize() {
    bgCanvas.width  = window.innerWidth;
    bgCanvas.height = window.innerHeight;
    waveCanvas.width  = window.innerWidth;
    waveCanvas.height = waveCanvas.offsetHeight || 100;
  }
  window.addEventListener("resize", resize);
  resize();

  /* ── Background particles ── */
  const PARTICLES = 60;
  const particles = Array.from({ length: PARTICLES }, () => ({
    x: Math.random(), y: Math.random(),
    vx: (Math.random() - 0.5) * 0.0003,
    vy: (Math.random() - 0.5) * 0.0003,
    r: Math.random() * 1.5 + 0.5,
    a: Math.random() * 0.3 + 0.05,
  }));

  function drawBg() {
    const W = bgCanvas.width, H = bgCanvas.height;
    bgCtx.clearRect(0, 0, W, H);
    const cx = W / 2, cy = H / 2;
    const grad = bgCtx.createRadialGradient(cx, cy, 0, cx, cy, Math.max(W, H) * 0.6);
    grad.addColorStop(0, `rgba(76,29,149,${0.12 + motion * 0.18})`);
    grad.addColorStop(0.5, `rgba(59,7,100,${0.06 + motion * 0.1})`);
    grad.addColorStop(1, "rgba(6,6,15,0)");
    bgCtx.fillStyle = grad;
    bgCtx.fillRect(0, 0, W, H);
    for (const p of particles) {
      p.x += p.vx * (1 + motion * 3);
      p.y += p.vy * (1 + motion * 3);
      if (p.x < 0) p.x = 1; if (p.x > 1) p.x = 0;
      if (p.y < 0) p.y = 1; if (p.y > 1) p.y = 0;
      const pulse = 0.5 + motion * 0.5;
      bgCtx.beginPath();
      bgCtx.arc(p.x * W, p.y * H, p.r * pulse, 0, Math.PI * 2);
      bgCtx.fillStyle = `rgba(255,214,0,${p.a * pulse})`;
      bgCtx.fill();
    }
  }

  /* ── Ring ── */
  function drawRing() {
    motion += (motionTarget - motion) * 0.12;
    const scale    = 1 + motion * 0.08;
    const glowR    = 160 + motion * 20;
    const mainR    = 140 + motion * 8;
    const fillR    = mainR - 2;
    const opacity  = 0.4 + motion * 0.6;

    ringMain.setAttribute("r", mainR);
    ringMain.setAttribute("stroke-opacity", opacity);
    ringGlow.setAttribute("r", glowR);
    ringGlow.setAttribute("stroke-opacity", 0.08 + motion * 0.25);
    ringFill.setAttribute("r", fillR);
    ringFill.setAttribute("fill-opacity", 0.04 + motion * 0.14);
    document.getElementById("ring-svg").style.transform = `scale(${scale})`;
    ringValue.textContent = motion.toFixed(2);
    ringValue.setAttribute("fill-opacity", 0.5 + motion * 0.5);

    const activeTicks = Math.round(motion * 48);
    ticksG.querySelectorAll("line").forEach((t, i) => {
      t.setAttribute("opacity", i < activeTicks ? (0.6 + motion * 0.4) : 0.15);
    });
  }

  /* ── Secondary metric bars ── */
  function ease(current, target) {
    return current + (target - current) * 0.1;
  }

  let eEnergy = 0, eSpread = 0, eVelocity = 0;

  function drawMetrics() {
    eEnergy   = ease(eEnergy, energy);
    eSpread   = ease(eSpread, spread);
    eVelocity = ease(eVelocity, velocity);

    energyBar.style.width   = (eEnergy   * 100).toFixed(1) + "%";
    spreadBar.style.width   = (eSpread   * 100).toFixed(1) + "%";
    velocityBar.style.width = (eVelocity * 100).toFixed(1) + "%";

    energyVal.textContent   = eEnergy.toFixed(2);
    spreadVal.textContent   = eSpread.toFixed(2);
    velocityVal.textContent = eVelocity.toFixed(2);
  }

  /* ── Waveform ── */
  function drawWave() {
    const W = waveCanvas.width, H = waveCanvas.height;
    waveCtx.clearRect(0, 0, W, H);
    const mid = H * 0.5, amp = H * 0.42;
    waveCtx.beginPath();
    for (let i = 0; i < WAVE_HISTORY; i++) {
      const idx = (waveHead + i) % WAVE_HISTORY;
      const x = (i / (WAVE_HISTORY - 1)) * W;
      const y = mid - waveData[idx] * amp;
      i === 0 ? waveCtx.moveTo(x, y) : waveCtx.lineTo(x, y);
    }
    const grad = waveCtx.createLinearGradient(0, 0, W, 0);
    grad.addColorStop(0, "rgba(255,214,0,0)");
    grad.addColorStop(0.4, "rgba(255,214,0,0.3)");
    grad.addColorStop(1, "rgba(255,214,0,0.9)");
    waveCtx.strokeStyle = grad;
    waveCtx.lineWidth = 1.5;
    waveCtx.stroke();
    waveCtx.lineTo(W, H); waveCtx.lineTo(0, H); waveCtx.closePath();
    const fillGrad = waveCtx.createLinearGradient(0, 0, 0, H);
    fillGrad.addColorStop(0, "rgba(255,214,0,0.08)");
    fillGrad.addColorStop(1, "rgba(255,214,0,0)");
    waveCtx.fillStyle = fillGrad;
    waveCtx.fill();
  }

  /* ── Status ── */
  function setStatus(isLive) {
    dot.className = "dot" + (isLive ? " live" : "");
    statusTxt.textContent = isLive ? "Live" : "Disconnected";
  }

  /* ── Render loop ── */
  function frame() {
    drawBg();
    drawRing();
    drawMetrics();
    drawWave();
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);

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
        motionTarget = msg.motion;
        energy       = msg.energy   ?? 0;
        spread       = msg.spread   ?? 0;
        velocity     = msg.velocity ?? 0;
        rssiTxt.textContent = `${msg.rssi} dBm`;
        waveData[waveHead] = msg.motion;
        waveHead = (waveHead + 1) % WAVE_HISTORY;
      }
    };
    ws.onclose = () => {
      setStatus(false);
      setTimeout(connect, reconnectDelay);
      reconnectDelay = Math.min(reconnectDelay * 1.5, 10000);
    };
    ws.onerror = () => ws.close();
  }

  connect();
})();
