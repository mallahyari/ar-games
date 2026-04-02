// ── Canvas ─────────────────────────────────────────────
const canvas = document.getElementById('ar-canvas');
const ctx = canvas.getContext('2d');
const hud = document.getElementById('hud');
const statusEl = document.getElementById('status');

function resize() {
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;
}
window.addEventListener('resize', resize);
resize();

// ── Camera feed ────────────────────────────────────────
const video = document.createElement('video');
video.autoplay = true;
video.playsInline = true;

async function startCamera() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: 'user' },
      audio: false,
    });
    video.srcObject = stream;
    await new Promise(r => video.onloadedmetadata = r);
    video.play();
  } catch (e) {
    console.error('Camera error:', e);
  }
}

// ── Cards data ─────────────────────────────────────────
let cards = {};
async function loadCards() {
  const res = await fetch('cards.json');
  cards = await res.json();
}

// ── Marker state ───────────────────────────────────────
// Track each marker: { corners, center, firstSeen, flipped }
const markerState = {};

// ── Card rendering ─────────────────────────────────────
function drawCard(marker) {
  const card = cards[String(marker.id)];
  if (!card) return;

  const w = canvas.width;
  const h = canvas.height;

  // Corners in pixel space (already mirrored via camera)
  const corners = marker.corners.map(([nx, ny]) => [nx * w, ny * h]);
  const cx = marker.center[0] * w;
  const cy = marker.center[1] * h;

  // Estimate card size from marker
  const markerW = Math.hypot(corners[1][0] - corners[0][0], corners[1][1] - corners[0][1]);
  const cardW = markerW * 3.5;
  const cardH = cardW * 0.65;

  // State
  const state = markerState[marker.id];
  const age = Date.now() - state.firstSeen;
  const showAnswer = age > 2000; // show answer after 2 seconds

  // Card background
  const x = cx - cardW / 2;
  const y = cy - cardH / 2 - markerW * 0.8;

  ctx.save();

  // Shadow
  ctx.shadowColor = 'rgba(0,0,0,0.5)';
  ctx.shadowBlur = 20;

  // Card body
  const radius = 16;
  ctx.beginPath();
  roundRect(ctx, x, y, cardW, cardH, radius);
  ctx.fillStyle = showAnswer ? card.color : '#1a1a2e';
  ctx.globalAlpha = 0.92;
  ctx.fill();
  ctx.shadowBlur = 0;

  // Border
  ctx.strokeStyle = card.color;
  ctx.lineWidth = 3;
  ctx.stroke();

  ctx.globalAlpha = 1;

  // Emoji
  const emoji = card.emoji || '❓';
  ctx.font = `${cardW * 0.15}px serif`;
  ctx.textAlign = 'center';
  ctx.fillStyle = '#fff';
  ctx.fillText(emoji, cx, y + cardH * 0.28);

  // Text
  const text = showAnswer ? card.answer : card.question;
  ctx.font = `bold ${Math.max(12, cardW * 0.075)}px -apple-system, sans-serif`;
  ctx.fillStyle = '#fff';
  wrapText(ctx, text, cx, y + cardH * 0.52, cardW * 0.85, cardW * 0.09);

  // Timer bar at bottom (counts down to answer reveal)
  if (!showAnswer) {
    const progress = Math.min(age / 2000, 1);
    ctx.fillStyle = 'rgba(255,255,255,0.15)';
    roundRect(ctx, x + 12, y + cardH - 20, cardW - 24, 10, 5);
    ctx.fill();
    ctx.fillStyle = card.color;
    roundRect(ctx, x + 12, y + cardH - 20, (cardW - 24) * progress, 10, 5);
    ctx.fill();
  } else {
    ctx.font = `${Math.max(10, cardW * 0.06)}px -apple-system, sans-serif`;
    ctx.fillStyle = 'rgba(255,255,255,0.6)';
    ctx.fillText('Answer ✓', cx, y + cardH - 8);
  }

  // Outline the detected marker
  ctx.beginPath();
  ctx.moveTo(corners[0][0], corners[0][1]);
  for (let i = 1; i < corners.length; i++) ctx.lineTo(corners[i][0], corners[i][1]);
  ctx.closePath();
  ctx.strokeStyle = card.color;
  ctx.lineWidth = 2;
  ctx.globalAlpha = 0.7;
  ctx.stroke();

  ctx.restore();
}

function roundRect(ctx, x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.lineTo(x + w - r, y);
  ctx.quadraticCurveTo(x + w, y, x + w, y + r);
  ctx.lineTo(x + w, y + h - r);
  ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
  ctx.lineTo(x + r, y + h);
  ctx.quadraticCurveTo(x, y + h, x, y + h - r);
  ctx.lineTo(x, y + r);
  ctx.quadraticCurveTo(x, y, x + r, y);
  ctx.closePath();
}

function wrapText(ctx, text, cx, y, maxWidth, lineHeight) {
  const words = text.split(' ');
  let line = '';
  let lines = [];
  for (const word of words) {
    const test = line + (line ? ' ' : '') + word;
    if (ctx.measureText(test).width > maxWidth && line) {
      lines.push(line);
      line = word;
    } else {
      line = test;
    }
  }
  if (line) lines.push(line);
  const startY = y - ((lines.length - 1) * lineHeight) / 2;
  lines.forEach((l, i) => ctx.fillText(l, cx, startY + i * lineHeight));
}

// ── Render loop ────────────────────────────────────────
let activeMarkers = [];

function drawFrame() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  // 1. Mirrored camera feed
  if (video.readyState >= 2) {
    ctx.save();
    ctx.translate(canvas.width, 0);
    ctx.scale(-1, 1);
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    ctx.restore();
  } else {
    ctx.fillStyle = '#111';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
  }

  // 2. Draw cards for each detected marker
  for (const marker of activeMarkers) {
    // Init state if new
    if (!markerState[marker.id]) {
      markerState[marker.id] = { firstSeen: Date.now() };
    }
    // Mirror marker X coords to match mirrored camera
    const mirrored = {
      ...marker,
      center: [1 - marker.center[0], marker.center[1]],
      corners: marker.corners.map(([x, y]) => [1 - x, y]),
    };
    drawCard(mirrored);
  }

  requestAnimationFrame(drawFrame);
}

// ── WebSocket ──────────────────────────────────────────
function connectWebSocket() {
  const ws = new WebSocket('ws://localhost:8767');

  ws.onopen = () => {
    statusEl.textContent = '● Connected';
    statusEl.className = 'connected';
  };

  ws.onmessage = (e) => {
    const msg = JSON.parse(e.data);
    if (msg.type === 'markers') {
      activeMarkers = msg.markers;
      // Reset firstSeen for markers that disappeared and came back
      const activeIds = new Set(activeMarkers.map(m => m.id));
      for (const id of Object.keys(markerState)) {
        if (!activeIds.has(Number(id))) delete markerState[id];
      }
    }
  };

  ws.onclose = () => {
    statusEl.textContent = '● Disconnected';
    statusEl.className = 'disconnected';
    setTimeout(connectWebSocket, 2000);
  };

  ws.onerror = () => ws.close();
}

// ── Keyboard ───────────────────────────────────────────
document.addEventListener('keydown', (e) => {
  if (e.key === 'h' || e.key === 'H') hud.classList.toggle('hidden');
});

// ── Init ───────────────────────────────────────────────
loadCards();
startCamera();
connectWebSocket();
requestAnimationFrame(drawFrame);
