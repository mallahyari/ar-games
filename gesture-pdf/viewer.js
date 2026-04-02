// ── State ──────────────────────────────────────────────
let pdfDoc = null;
let currentPage = 1;
let scale = 1.5;
let renderInProgress = false;
let pendingRender = false;
let flashTimer = null;
let zoomRenderTimer = null;

const viewer = document.getElementById('viewer-wrap');
const dropZone = document.getElementById('drop-zone');
const pagesContainer = document.getElementById('pages-container');
const pageInfo = document.getElementById('page-info');
const zoomInfo = document.getElementById('zoom-info');
const gestureStatus = document.getElementById('gesture-status');
const gestureFlash = document.getElementById('gesture-flash');
const fileInput = document.getElementById('file-input');

// ── PDF rendering ──────────────────────────────────────
async function renderPage(num) {
  if (!pdfDoc) return;
  if (renderInProgress) { pendingRender = true; return; }
  renderInProgress = true;
  pendingRender = false;

  const page = await pdfDoc.getPage(num);
  const viewport = page.getViewport({ scale });

  let canvas = pagesContainer.querySelector('canvas');
  if (!canvas) {
    canvas = document.createElement('canvas');
    pagesContainer.appendChild(canvas);
  }

  canvas.width = viewport.width;
  canvas.height = viewport.height;

  const renderTask = page.render({ canvasContext: canvas.getContext('2d'), viewport });
  try { await renderTask.promise; } catch (e) {
    if (e.name !== 'RenderingCancelledException') throw e;
  }

  pagesContainer.classList.add('visible');
  dropZone.classList.add('hidden');
  pageInfo.textContent = `Page ${num} / ${pdfDoc.numPages}`;
  zoomInfo.textContent = `${Math.round(scale * 100)}%`;

  renderInProgress = false;
  if (pendingRender) renderPage(currentPage);
}

async function loadPdf(data) {
  pdfDoc = await pdfjsLib.getDocument({ data }).promise;
  currentPage = 1;
  scale = 1.5;
  await renderPage(currentPage);
}

// ── Gesture actions ────────────────────────────────────
const ZOOM_STEP = 0.08;
const MIN_SCALE = 0.5;
const MAX_SCALE = 4.0;

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

viewer.addEventListener('dragover', (e) => e.preventDefault());
viewer.addEventListener('drop', async (e) => {
  e.preventDefault();
  const file = e.dataTransfer.files[0];
  if (!file || !file.name.endsWith('.pdf')) return;
  await loadPdf(await file.arrayBuffer());
});

// ── Keyboard fallback ──────────────────────────────────
document.addEventListener('keydown', async (e) => {
  if (e.key === 'ArrowRight' || e.key === 'PageDown') await handlePage('next');
  else if (e.key === 'ArrowLeft' || e.key === 'PageUp') await handlePage('prev');
  else if (e.key === '+' || e.key === '=') await handleZoom(1);
  else if (e.key === '-') await handleZoom(-1);
});

// ── Init ───────────────────────────────────────────────
connectWebSocket();
