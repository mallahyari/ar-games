import { HandLandmarker, FilesetResolver } from 'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14/vision_bundle.mjs';

// ── Canvas & context ───────────────────────────────────
const canvas = document.getElementById('ar-canvas');
const ctx = canvas.getContext('2d');

function resize() {
  canvas.width  = window.innerWidth;
  canvas.height = window.innerHeight;
}
window.addEventListener('resize', resize);
resize();

// ── State ──────────────────────────────────────────────
let pdfDoc = null;
let currentPage = 1;
let scale = 1.0;
let pdfCanvas = null;
let renderInProgress = false;
let pendingRender = false;
let flashTimer = null;
let zoomRenderTimer = null;
let pdfX = 0, pdfY = 0;
let pdfOpacity = 0.88;

const pageInfo      = document.getElementById('page-info');
const zoomInfo      = document.getElementById('zoom-info');
const gestureStatus = document.getElementById('gesture-status');
const gestureFlash  = document.getElementById('gesture-flash');
const fileInput     = document.getElementById('file-input');
const hud           = document.getElementById('hud');

// ── Hand landmark connections ──────────────────────────
const HAND_CONNECTIONS = [
  [0,1],[1,2],[2,3],[3,4],
  [0,5],[5,6],[6,7],[7,8],
  [0,9],[9,10],[10,11],[11,12],
  [0,13],[13,14],[14,15],[15,16],
  [0,17],[17,18],[18,19],[19,20],
  [5,9],[9,13],[13,17],
];

// Finger colors for a nice look
const FINGER_COLORS = ['#ff6b9d','#c44dff','#4dc8ff','#4dffb4','#ffdd4d'];
const FINGER_STARTS = [0, 1, 5, 9, 13, 17]; // wrist + 5 finger bases

function fingerColor(i) {
  if (i === 0) return '#fff';
  if (i <= 4)  return FINGER_COLORS[0];
  if (i <= 8)  return FINGER_COLORS[1];
  if (i <= 12) return FINGER_COLORS[2];
  if (i <= 16) return FINGER_COLORS[3];
  return FINGER_COLORS[4];
}

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
    console.error('Camera access denied:', e);
  }
}

// ── MediaPipe Hand Landmarker (JS, runs in browser) ────
let handLandmarker = null;
let lastVideoTime = -1;
let detectedHands = [];

async function initHandLandmarker() {
  const fileset = await FilesetResolver.forVisionTasks(
    'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.3/wasm'
  );
  handLandmarker = await HandLandmarker.createFromOptions(fileset, {
    baseOptions: {
      modelAssetPath:
        'https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task',
      delegate: 'GPU',
    },
    runningMode: 'VIDEO',
    numHands: 2,
  });
  console.log('HandLandmarker ready');
}

function detectHands() {
  if (!handLandmarker || video.readyState < 2) return;
  if (video.currentTime === lastVideoTime) return;
  lastVideoTime = video.currentTime;
  const result = handLandmarker.detectForVideo(video, performance.now());
  detectedHands = result.landmarks || [];
}

// ── Draw hand skeleton ─────────────────────────────────
function drawHands() {
  if (!detectedHands.length) return;

  const w = canvas.width;
  const h = canvas.height;

  for (const landmarks of detectedHands) {
    // Map normalized coords — mirror X to match mirrored camera
    const pts = landmarks.map(lm => ({
      x: (1 - lm.x) * w,
      y: lm.y * h,
    }));

    // Draw connections
    ctx.save();
    ctx.lineWidth = 2;
    for (const [a, b] of HAND_CONNECTIONS) {
      ctx.beginPath();
      ctx.moveTo(pts[a].x, pts[a].y);
      ctx.lineTo(pts[b].x, pts[b].y);
      ctx.strokeStyle = 'rgba(255,255,255,0.5)';
      ctx.stroke();
    }

    // Draw landmark dots
    for (let i = 0; i < pts.length; i++) {
      const isFingerTip = [4, 8, 12, 16, 20].includes(i);
      const r = isFingerTip ? 8 : 4;
      ctx.beginPath();
      ctx.arc(pts[i].x, pts[i].y, r, 0, Math.PI * 2);
      ctx.fillStyle = fingerColor(i);
      ctx.fill();
      if (isFingerTip) {
        ctx.strokeStyle = 'rgba(255,255,255,0.8)';
        ctx.lineWidth = 1.5;
        ctx.stroke();
      }
    }
    ctx.restore();
  }
}

// ── PDF rendering (off-screen) ─────────────────────────
async function renderPage(num) {
  if (!pdfDoc) return;
  if (renderInProgress) { pendingRender = true; return; }
  renderInProgress = true;
  pendingRender = false;

  const page = await pdfDoc.getPage(num);
  const viewport = page.getViewport({ scale });

  if (!pdfCanvas) pdfCanvas = document.createElement('canvas');
  pdfCanvas.width  = viewport.width;
  pdfCanvas.height = viewport.height;

  const task = page.render({ canvasContext: pdfCanvas.getContext('2d'), viewport });
  try { await task.promise; } catch (e) {
    if (e.name !== 'RenderingCancelledException') throw e;
  }

  pageInfo.textContent = `Page ${num} / ${pdfDoc.numPages}`;
  zoomInfo.textContent = `${Math.round(scale * 100)}%`;
  renderInProgress = false;
  if (pendingRender) renderPage(currentPage);
}

async function loadPdf(data) {
  pdfDoc = await pdfjsLib.getDocument({ data }).promise;
  currentPage = 1;
  scale = 1.0;
  await renderPage(currentPage);
}

// ── AR render loop ─────────────────────────────────────
function drawFrame() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  // 1. Camera feed — mirrored
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

  // 2. PDF overlay — centered with shadow
  if (pdfCanvas) {
    const x = Math.round((canvas.width  - pdfCanvas.width)  / 2 + pdfX);
    const y = Math.round((canvas.height - pdfCanvas.height) / 2 + pdfY);
    ctx.save();
    ctx.shadowColor = 'rgba(0,0,0,0.6)';
    ctx.shadowBlur  = 32;
    ctx.shadowOffsetX = 6;
    ctx.shadowOffsetY = 6;
    ctx.globalAlpha = pdfOpacity;
    ctx.drawImage(pdfCanvas, x, y);
    ctx.restore();
  }

  // 3. Hand skeleton on top
  detectHands();
  drawHands();

  requestAnimationFrame(drawFrame);
}

// ── Gesture actions ────────────────────────────────────
const ZOOM_STEP = 0.1;
const MIN_SCALE = 0.3;
const MAX_SCALE = 3.0;

async function handlePage(direction) {
  if (!pdfDoc) return;
  if (direction === 'next' && currentPage < pdfDoc.numPages) {
    currentPage++;
    await renderPage(currentPage);
    flash('→ Next Page');
  } else if (direction === 'prev' && currentPage > 1) {
    currentPage--;
    await renderPage(currentPage);
    flash('← Previous Page');
  }
}

async function handleZoom(delta) {
  const newScale = Math.min(MAX_SCALE, Math.max(MIN_SCALE, scale + delta * ZOOM_STEP));
  if (Math.abs(newScale - scale) < 0.005) return;
  scale = newScale;
  zoomInfo.textContent = `${Math.round(scale * 100)}%`;
  flash(delta > 0 ? `🔍 Zoom In  ${Math.round(scale * 100)}%` : `🔍 Zoom Out  ${Math.round(scale * 100)}%`);
  if (zoomRenderTimer) clearTimeout(zoomRenderTimer);
  zoomRenderTimer = setTimeout(() => renderPage(currentPage), 400);
}

function flash(msg) {
  gestureFlash.textContent = msg;
  gestureFlash.classList.add('show');
  if (flashTimer) clearTimeout(flashTimer);
  flashTimer = setTimeout(() => gestureFlash.classList.remove('show'), 1000);
}

// ── WebSocket ──────────────────────────────────────────
function connectWebSocket() {
  const ws = new WebSocket('ws://localhost:8766');
  ws.onopen = () => {
    gestureStatus.textContent = '● Connected';
    gestureStatus.className = 'connected';
  };
  ws.onmessage = (e) => {
    const msg = JSON.parse(e.data);
    if (msg.type === 'page') handlePage(msg.direction);
    if (msg.type === 'zoom') handleZoom(msg.delta);
  };
  ws.onclose = () => {
    gestureStatus.textContent = '● Disconnected';
    gestureStatus.className = 'disconnected';
    setTimeout(connectWebSocket, 2000);
  };
  ws.onerror = () => ws.close();
}

// ── File loading ───────────────────────────────────────
fileInput.addEventListener('change', async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  await loadPdf(await file.arrayBuffer());
});
document.addEventListener('dragover', (e) => e.preventDefault());
document.addEventListener('drop', async (e) => {
  e.preventDefault();
  const file = e.dataTransfer.files[0];
  if (!file || !file.name.endsWith('.pdf')) return;
  await loadPdf(await file.arrayBuffer());
});

// ── Keyboard shortcuts ─────────────────────────────────
document.addEventListener('keydown', async (e) => {
  if (e.key === 'ArrowRight' || e.key === 'PageDown') await handlePage('next');
  else if (e.key === 'ArrowLeft' || e.key === 'PageUp') await handlePage('prev');
  else if (e.key === '+' || e.key === '=') await handleZoom(1);
  else if (e.key === '-') await handleZoom(-1);
  else if (e.key === 'h' || e.key === 'H') hud.classList.toggle('hidden');
});

// ── Init ───────────────────────────────────────────────
startCamera();
initHandLandmarker();
connectWebSocket();
requestAnimationFrame(drawFrame);
