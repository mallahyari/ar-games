# Ninja Slice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an AR wall game where kids swipe their arm to slice flying fruit, with camera-based motion detection in Python streaming swipe events over WebSocket to a fullscreen browser canvas game.

**Architecture:** Python (`detection.py`) processes webcam frames using frame differencing to detect fast arm swipes, normalizes swipe vectors to 0–1 coordinates, and broadcasts JSON over WebSocket (`server.py`). The browser (`collision.js` + `game.js`) owns all game state and performs line-circle collision detection on incoming swipe events, rendering on a fullscreen canvas.

**Tech Stack:** Python 3.13, opencv-python, websockets (asyncio), numpy, pytest; Vanilla JS + Canvas API (no build step); uv for dependency management.

---

## File Map

| File | Responsibility |
|---|---|
| `pyproject.toml` | Python dependencies |
| `ninja-slice/detection.py` | `SwipeDetector`: frame diff → normalized swipe vector |
| `ninja-slice/server.py` | asyncio WebSocket server + camera capture loop |
| `ninja-slice/collision.js` | Pure functions: line-circle intersection, swipe→slice indices |
| `ninja-slice/game.js` | Game state, loop, rendering, WebSocket client, dev mode |
| `ninja-slice/index.html` | Entry point, loads scripts |
| `ninja-slice/style.css` | Fullscreen canvas styles |
| `ninja-slice/tests/test_detection.py` | Unit tests for SwipeDetector |
| `ninja-slice/tests/test_collision.js` | Node.js tests for collision functions |

---

### Task 1: Project setup

**Files:**
- Modify: `pyproject.toml`
- Create: `ninja-slice/` and `ninja-slice/tests/`

- [ ] **Step 1: Add Python dependencies**

```bash
cd /Users/mehdiallahyari/projects/ar-games
uv add opencv-python websockets numpy pytest
```

Expected: packages resolved and added to `.venv`

- [ ] **Step 2: Create directories**

```bash
mkdir -p ninja-slice/tests
```

- [ ] **Step 3: Verify environment**

```bash
uv run python -c "import cv2, websockets, numpy; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "chore: add opencv, websockets, numpy, pytest"
```

---

### Task 2: SwipeDetector — tests first

**Files:**
- Create: `ninja-slice/tests/__init__.py`
- Create: `ninja-slice/tests/test_detection.py`

- [ ] **Step 1: Create `ninja-slice/tests/__init__.py`** (empty file)

- [ ] **Step 2: Write failing tests in `ninja-slice/tests/test_detection.py`**

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import numpy as np
import pytest
from detection import SwipeDetector


def bgr_frame(h=480, w=640, val=0):
    return np.full((h, w, 3), val, dtype=np.uint8)


def test_no_swipe_on_first_frame():
    det = SwipeDetector()
    det.set_frame_size(640, 480)
    assert det.process_frame(bgr_frame()) is None


def test_no_swipe_on_static_scene():
    det = SwipeDetector()
    det.set_frame_size(640, 480)
    frame = bgr_frame(val=50)
    det.process_frame(frame)
    assert det.process_frame(frame) is None


def test_swipe_detected_on_fast_motion():
    det = SwipeDetector(min_area=100, velocity_threshold=10)
    det.set_frame_size(640, 480)
    f1 = bgr_frame()
    f1[90:130, 90:130] = 200
    f2 = bgr_frame()
    f2[200:240, 300:340] = 200
    f3 = bgr_frame()
    f3[310:350, 450:490] = 200
    det.process_frame(f1)
    det.process_frame(f2)
    result = det.process_frame(f3)
    assert result is not None
    assert result['type'] == 'swipe'


def test_swipe_coords_normalized():
    det = SwipeDetector(min_area=100, velocity_threshold=10)
    det.set_frame_size(640, 480)
    f1 = bgr_frame()
    f1[90:130, 90:130] = 200
    f2 = bgr_frame()
    f2[200:240, 300:340] = 200
    f3 = bgr_frame()
    f3[310:350, 450:490] = 200
    det.process_frame(f1)
    det.process_frame(f2)
    result = det.process_frame(f3)
    assert result is not None
    for key in ('x1', 'y1', 'x2', 'y2'):
        assert 0.0 <= result[key] <= 1.0, f"{key}={result[key]} out of [0,1]"


def test_slow_motion_not_detected():
    det = SwipeDetector(min_area=100, velocity_threshold=100)
    det.set_frame_size(640, 480)
    f1 = bgr_frame()
    f1[90:130, 90:130] = 200
    f2 = bgr_frame()
    f2[92:132, 92:132] = 200  # tiny shift
    f3 = bgr_frame()
    f3[94:134, 94:134] = 200  # another tiny shift, still well below threshold=100
    det.process_frame(f1)
    det.process_frame(f2)
    assert det.process_frame(f3) is None
```

- [ ] **Step 3: Run — expect failure**

```bash
uv run pytest ninja-slice/tests/test_detection.py -v
```

Expected: `ModuleNotFoundError: No module named 'detection'`

---

### Task 3: Implement SwipeDetector

**Files:**
- Create: `ninja-slice/detection.py`

- [ ] **Step 1: Create `ninja-slice/detection.py`**

```python
import cv2
import numpy as np


class SwipeDetector:
    def __init__(self, min_area=500, velocity_threshold=30):
        self.prev_gray = None
        self.prev_centroid = None
        self.min_area = min_area
        self.velocity_threshold = velocity_threshold
        self.frame_w = 1
        self.frame_h = 1

    def set_frame_size(self, w, h):
        self.frame_w = w
        self.frame_h = h

    def process_frame(self, frame):
        """Process a BGR frame. Returns swipe dict or None."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        if self.prev_gray is None:
            self.prev_gray = gray
            return None

        diff = cv2.absdiff(self.prev_gray, gray)
        self.prev_gray = gray

        _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
        thresh = cv2.dilate(thresh, None, iterations=2)

        contours, _ = cv2.findContours(
            thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        if not contours:
            self.prev_centroid = None
            return None

        largest = max(contours, key=cv2.contourArea)
        if cv2.contourArea(largest) < self.min_area:
            self.prev_centroid = None
            return None

        M = cv2.moments(largest)
        if M['m00'] == 0:
            self.prev_centroid = None
            return None

        cx = M['m10'] / M['m00']
        cy = M['m01'] / M['m00']

        swipe = None
        if self.prev_centroid is not None:
            dx = cx - self.prev_centroid[0]
            dy = cy - self.prev_centroid[1]
            if np.hypot(dx, dy) >= self.velocity_threshold:
                swipe = {
                    'type': 'swipe',
                    'x1': round(self.prev_centroid[0] / self.frame_w, 4),
                    'y1': round(self.prev_centroid[1] / self.frame_h, 4),
                    'x2': round(cx / self.frame_w, 4),
                    'y2': round(cy / self.frame_h, 4),
                }

        self.prev_centroid = (cx, cy)
        return swipe
```

- [ ] **Step 2: Run tests — expect pass**

```bash
uv run pytest ninja-slice/tests/test_detection.py -v
```

Expected:
```
test_no_swipe_on_first_frame PASSED
test_no_swipe_on_static_scene PASSED
test_swipe_detected_on_fast_motion PASSED
test_swipe_coords_normalized PASSED
test_slow_motion_not_detected PASSED
5 passed
```

- [ ] **Step 3: Commit**

```bash
git add ninja-slice/detection.py ninja-slice/tests/
git commit -m "feat: add SwipeDetector with frame differencing motion detection"
```

---

### Task 4: WebSocket server

**Files:**
- Create: `ninja-slice/server.py`

- [ ] **Step 1: Create `ninja-slice/server.py`**

```python
import asyncio
import json
import sys

import cv2
import websockets
from detection import SwipeDetector

CLIENTS: set = set()


async def handler(websocket):
    CLIENTS.add(websocket)
    print(f"Client connected: {websocket.remote_address}")
    try:
        await websocket.wait_closed()
    finally:
        CLIENTS.discard(websocket)
        print("Client disconnected")


async def camera_loop():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("ERROR: Could not open camera (device 0)")
        sys.exit(1)

    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"Camera opened: {w}x{h}")

    detector = SwipeDetector()
    detector.set_frame_size(w, h)

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                await asyncio.sleep(0.033)
                continue

            swipe = detector.process_frame(frame)
            if swipe and CLIENTS:
                websockets.broadcast(CLIENTS, json.dumps(swipe))

            await asyncio.sleep(0.033)  # ~30 fps
    finally:
        cap.release()


async def main():
    print("Ninja Slice server starting on ws://localhost:8765")
    async with websockets.serve(handler, "localhost", 8765):
        await camera_loop()


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: Verify syntax (no camera needed)**

```bash
cd ninja-slice && uv run python -c "import server" 2>&1; cd ..
```

Expected: no output (clean import)

- [ ] **Step 3: Commit**

```bash
git add ninja-slice/server.py
git commit -m "feat: add WebSocket server with camera capture loop"
```

---

### Task 5: Collision module — tests first

**Files:**
- Create: `ninja-slice/tests/test_collision.js`

- [ ] **Step 1: Write `ninja-slice/tests/test_collision.js`**

```javascript
const { lineCircleIntersects, checkSwipeSlices } = require('../collision.js');

let passed = 0, failed = 0;
function assert(condition, msg) {
    if (condition) { console.log(`  PASS: ${msg}`); passed++; }
    else { console.error(`  FAIL: ${msg}`); failed++; }
}

console.log('lineCircleIntersects:');
assert(lineCircleIntersects(0, 0, 100, 0, 50, 0, 10),   'line through center hits');
assert(lineCircleIntersects(0, 0, 100, 0, 50, 5, 10),   'line grazes circle hits');
assert(!lineCircleIntersects(0, 0, 100, 0, 50, 20, 10), 'line above circle misses');
assert(!lineCircleIntersects(0, 0, 10, 0, 50, 0, 10),   'segment ends before circle misses');
assert(lineCircleIntersects(0, 0, 200, 0, 50, 0, 10),   'circle mid-segment hits');
assert(!lineCircleIntersects(0, 0, 0, 0, 50, 50, 10),   'zero-length segment misses');

console.log('\ncheckSwipeSlices:');
const objects = [
    { x: 500, y: 240, radius: 40, sliced: false },
    { x: 100, y: 240, radius: 40, sliced: false },
    { x: 500, y: 240, radius: 40, sliced: true  },
];
const swipe = { x1: 0.45, y1: 0.5, x2: 0.55, y2: 0.5 };
const result = checkSwipeSlices(swipe, 1000, 480, objects);
assert(result.includes(0),  'slices object in path');
assert(!result.includes(1), 'does not slice object outside path');
assert(!result.includes(2), 'does not re-slice already-sliced object');

if (failed > 0) { console.error(`\n${passed} passed, ${failed} failed`); process.exit(1); }
else console.log(`\n${passed} passed, 0 failed`);
```

- [ ] **Step 2: Run — expect failure**

```bash
node ninja-slice/tests/test_collision.js
```

Expected: `Error: Cannot find module '../collision.js'`

---

### Task 6: Implement collision module

**Files:**
- Create: `ninja-slice/collision.js`

- [ ] **Step 1: Create `ninja-slice/collision.js`**

```javascript
function lineCircleIntersects(x1, y1, x2, y2, cx, cy, r) {
    const dx = x2 - x1, dy = y2 - y1;
    const fx = x1 - cx, fy = y1 - cy;
    const a = dx * dx + dy * dy;
    if (a === 0) return false;
    const b = 2 * (fx * dx + fy * dy);
    const c = fx * fx + fy * fy - r * r;
    const disc = b * b - 4 * a * c;
    if (disc < 0) return false;
    const sqrtD = Math.sqrt(disc);
    const t1 = (-b - sqrtD) / (2 * a);
    const t2 = (-b + sqrtD) / (2 * a);
    return (t1 >= 0 && t1 <= 1) || (t2 >= 0 && t2 <= 1);
}

function checkSwipeSlices(swipe, cw, ch, objects) {
    const sx1 = swipe.x1 * cw, sy1 = swipe.y1 * ch;
    const sx2 = swipe.x2 * cw, sy2 = swipe.y2 * ch;
    const result = [];
    for (let i = 0; i < objects.length; i++) {
        const obj = objects[i];
        if (obj.sliced) continue;
        if (lineCircleIntersects(sx1, sy1, sx2, sy2, obj.x, obj.y, obj.radius)) {
            result.push(i);
        }
    }
    return result;
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = { lineCircleIntersects, checkSwipeSlices };
}
```

- [ ] **Step 2: Run tests — expect pass**

```bash
node ninja-slice/tests/test_collision.js
```

Expected: `9 passed, 0 failed`

- [ ] **Step 3: Commit**

```bash
git add ninja-slice/collision.js ninja-slice/tests/test_collision.js
git commit -m "feat: add collision detection with line-circle intersection"
```

---

### Task 7: HTML, CSS, and game engine

**Files:**
- Create: `ninja-slice/style.css`
- Create: `ninja-slice/index.html`
- Create: `ninja-slice/game.js`

- [ ] **Step 1: Create `ninja-slice/style.css`**

```css
*, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }
body { background: #000; overflow: hidden; width: 100vw; height: 100vh; }
#game { display: block; cursor: crosshair; }
```

- [ ] **Step 2: Create `ninja-slice/index.html`**

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ninja Slice</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <canvas id="game"></canvas>
    <script src="collision.js"></script>
    <script src="game.js"></script>
</body>
</html>
```

- [ ] **Step 3: Create `ninja-slice/game.js`**

```javascript
const WS_URL = 'ws://localhost:8765';
const RECONNECT_DELAY = 2000;

const FRUIT_CONFIG = {
    apple:      { emoji: '🍎', color: '#e74c3c' },
    watermelon: { emoji: '🍉', color: '#27ae60' },
    orange:     { emoji: '🍊', color: '#e67e22' },
    bomb:       { emoji: '💣', color: '#2c3e50' },
};
const SPAWN_TYPES = ['apple', 'watermelon', 'orange', 'orange', 'apple', 'bomb'];

let canvas, ctx;
let state = {};

function initState() {
    state = {
        objects: [], score: 0, lives: 3,
        maxObjects: 3, speed: 3, spawnInterval: 2000,
        lastSpawnTime: 0, difficultyTimer: 0,
        gameOver: false, running: false,
        ws: null, wsConnected: false,
        trails: [],
        devMode: new URLSearchParams(window.location.search).has('dev'),
        mouseStart: null, lastTime: null,
    };
}

function spawnObject() {
    const type = SPAWN_TYPES[Math.floor(Math.random() * SPAWN_TYPES.length)];
    const edge = Math.floor(Math.random() * 4);
    const r = 40;
    let x, y;
    switch (edge) {
        case 0: x = Math.random() * canvas.width;  y = -r; break;
        case 1: x = canvas.width + r;               y = Math.random() * canvas.height; break;
        case 2: x = Math.random() * canvas.width;  y = canvas.height + r; break;
        default: x = -r;                            y = Math.random() * canvas.height;
    }
    const targetX = canvas.width  * (0.2 + Math.random() * 0.6);
    const targetY = canvas.height * (0.2 + Math.random() * 0.6);
    const angle  = Math.atan2(targetY - y, targetX - x);
    const spread = (Math.random() - 0.5) * 0.8;
    return {
        id: Date.now() + Math.random(),
        x, y,
        vx: Math.cos(angle + spread) * state.speed,
        vy: Math.sin(angle + spread) * state.speed,
        radius: r, type, sliced: false, sliceEffect: null,
    };
}

function applySwipe(swipe) {
    if (state.gameOver) return;
    state.trails.push({
        x1: swipe.x1 * canvas.width,  y1: swipe.y1 * canvas.height,
        x2: swipe.x2 * canvas.width,  y2: swipe.y2 * canvas.height,
        alpha: 1.0,
    });
    const indices = checkSwipeSlices(swipe, canvas.width, canvas.height, state.objects);
    if (!indices.length) return;
    const combo = indices.length >= 2;
    for (const i of indices) {
        const obj = state.objects[i];
        obj.sliced = true;
        obj.sliceEffect = { alpha: 1.0, offsetX: 0, offsetY: 0 };
        if (obj.type === 'bomb') {
            state.lives = Math.max(0, state.lives - 1);
            if (state.lives === 0) triggerGameOver();
        } else {
            state.score += combo ? 3 : 1;
        }
    }
}

function update(dt) {
    if (state.gameOver) return;

    state.difficultyTimer += dt;
    if (state.difficultyTimer >= 15000) {
        state.difficultyTimer = 0;
        state.maxObjects    = Math.min(state.maxObjects + 1, 10);
        state.speed         = Math.min(state.speed * 1.05, 10);
        state.spawnInterval = Math.max(state.spawnInterval * 0.95, 800);
    }

    const activeCount = state.objects.filter(o => !o.sliced).length;
    const now = performance.now();
    if (activeCount < state.maxObjects && now - state.lastSpawnTime > state.spawnInterval) {
        state.objects.push(spawnObject());
        state.lastSpawnTime = now;
    }

    const margin = 80;
    for (let i = state.objects.length - 1; i >= 0; i--) {
        const obj = state.objects[i];
        if (obj.sliced) {
            obj.sliceEffect.alpha    -= 0.04;
            obj.sliceEffect.offsetX  += obj.vx * 0.5;
            obj.sliceEffect.offsetY  += obj.vy * 0.5;
            if (obj.sliceEffect.alpha <= 0) state.objects.splice(i, 1);
            continue;
        }
        obj.x += obj.vx;
        obj.y += obj.vy;
        const off = obj.x < -margin || obj.x > canvas.width + margin ||
                    obj.y < -margin || obj.y > canvas.height + margin;
        if (off) {
            state.objects.splice(i, 1);
            if (obj.type !== 'bomb') {
                state.lives = Math.max(0, state.lives - 1);
                if (state.lives === 0) triggerGameOver();
            }
        }
    }

    for (let i = state.trails.length - 1; i >= 0; i--) {
        state.trails[i].alpha -= 0.05;
        if (state.trails[i].alpha <= 0) state.trails.splice(i, 1);
    }
}

function render() {
    ctx.fillStyle = '#0a0a0a';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    for (const obj of state.objects) {
        obj.sliced ? drawSliced(obj) : drawObject(obj);
    }

    for (const t of state.trails) {
        ctx.save();
        ctx.strokeStyle = `rgba(255,255,200,${t.alpha})`;
        ctx.lineWidth = 4; ctx.lineCap = 'round';
        ctx.beginPath(); ctx.moveTo(t.x1, t.y1); ctx.lineTo(t.x2, t.y2);
        ctx.stroke(); ctx.restore();
    }

    drawHUD();
    if (state.gameOver) drawGameOver();
    if (!state.wsConnected && !state.devMode) drawReconnecting();
}

function drawObject(obj) {
    const cfg = FRUIT_CONFIG[obj.type];
    ctx.save();
    ctx.beginPath();
    ctx.arc(obj.x, obj.y, obj.radius, 0, Math.PI * 2);
    ctx.fillStyle = cfg.color; ctx.fill();
    ctx.font = `${obj.radius}px serif`;
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.fillText(cfg.emoji, obj.x, obj.y);
    ctx.restore();
}

function drawSliced(obj) {
    const cfg = FRUIT_CONFIG[obj.type];
    const eff = obj.sliceEffect;
    ctx.save();
    ctx.globalAlpha = Math.max(0, eff.alpha);
    for (let half = 0; half < 2; half++) {
        const dx = eff.offsetX + (half === 0 ? -15 : 15) * (1 - eff.alpha);
        const dy = eff.offsetY + 10 * (1 - eff.alpha);
        ctx.save();
        ctx.beginPath();
        ctx.arc(obj.x + dx, obj.y + dy, obj.radius, half * Math.PI, (half + 1) * Math.PI);
        ctx.closePath();
        ctx.fillStyle = cfg.color; ctx.fill();
        ctx.restore();
    }
    ctx.restore();
}

function drawHUD() {
    ctx.save();
    ctx.fillStyle = '#fff'; ctx.font = 'bold 36px monospace';
    ctx.textAlign = 'left';  ctx.textBaseline = 'top';
    ctx.fillText(`Score: ${state.score}`, 20, 20);
    ctx.textAlign = 'right';
    ctx.fillText('❤️'.repeat(state.lives), canvas.width - 20, 20);
    ctx.restore();
}

function drawGameOver() {
    ctx.save();
    ctx.fillStyle = 'rgba(0,0,0,0.75)';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = '#fff'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.font = 'bold 80px monospace';
    ctx.fillText('GAME OVER', canvas.width / 2, canvas.height / 2 - 70);
    ctx.font = 'bold 48px monospace';
    ctx.fillText(`Score: ${state.score}`, canvas.width / 2, canvas.height / 2 + 10);
    ctx.font = '28px monospace'; ctx.fillStyle = '#aaa';
    ctx.fillText('Click to restart', canvas.width / 2, canvas.height / 2 + 80);
    ctx.restore();
}

function drawReconnecting() {
    ctx.save();
    ctx.fillStyle = 'rgba(0,0,0,0.6)'; ctx.fillRect(0, 0, canvas.width, 56);
    ctx.fillStyle = '#f39c12'; ctx.font = '22px monospace';
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.fillText('Connecting to camera server...', canvas.width / 2, 28);
    ctx.restore();
}

function gameLoop(timestamp) {
    if (state.lastTime === null) state.lastTime = timestamp;
    update(timestamp - state.lastTime);
    state.lastTime = timestamp;
    render();
    requestAnimationFrame(gameLoop);
}

function triggerGameOver() {
    state.gameOver = true;
    state.running  = false;
}

function startGame() {
    initState();
    state.running = true;
    connectWebSocket();
    if (state.devMode) setupDevMode();
    requestAnimationFrame(gameLoop);
}

function restartGame() {
    if (state.ws) { state.ws.onclose = null; state.ws.close(); }
    startGame();
}

function connectWebSocket() {
    if (state.devMode) return;
    let ws;
    try { ws = new WebSocket(WS_URL); }
    catch (e) { setTimeout(connectWebSocket, RECONNECT_DELAY); return; }
    state.ws = ws;
    ws.onopen    = () => { state.wsConnected = true; };
    ws.onmessage = (e) => {
        try { const msg = JSON.parse(e.data); if (msg.type === 'swipe') applySwipe(msg); }
        catch (_) {}
    };
    ws.onclose = () => { state.wsConnected = false; setTimeout(connectWebSocket, RECONNECT_DELAY); };
    ws.onerror = () => ws.close();
}

function setupDevMode() {
    state.wsConnected = true;
    canvas.addEventListener('mousedown', (e) => {
        const r = canvas.getBoundingClientRect();
        state.mouseStart = {
            x: (e.clientX - r.left) / canvas.width,
            y: (e.clientY - r.top)  / canvas.height,
        };
    });
    canvas.addEventListener('mouseup', (e) => {
        if (!state.mouseStart) return;
        const r = canvas.getBoundingClientRect();
        applySwipe({
            type: 'swipe',
            x1: state.mouseStart.x, y1: state.mouseStart.y,
            x2: (e.clientX - r.left) / canvas.width,
            y2: (e.clientY - r.top)  / canvas.height,
        });
        state.mouseStart = null;
    });
}

window.addEventListener('DOMContentLoaded', () => {
    canvas = document.getElementById('game');
    ctx    = canvas.getContext('2d');

    function resize() { canvas.width = window.innerWidth; canvas.height = window.innerHeight; }
    resize();
    window.addEventListener('resize', resize);
    canvas.addEventListener('click', () => { if (state.gameOver) restartGame(); });
    startGame();
});
```

- [ ] **Step 4: Smoke test in browser**

Open `ninja-slice/index.html?dev=1` in a browser. Verify:
- Dark fullscreen canvas
- Fruit emoji fly from random edges
- Mouse click-drag slices objects
- Score increments on hits; +3 for slicing 2+ in one drag
- Lives decrease when fruit exits screen
- Slicing a bomb (💣) loses a life
- Game over overlay appears at 0 lives; click restarts
- After 15 seconds, objects get faster and more spawn

- [ ] **Step 5: Commit**

```bash
git add ninja-slice/index.html ninja-slice/style.css ninja-slice/game.js
git commit -m "feat: add game engine with rendering, spawning, difficulty, dev mode"
```

---

### Task 8: Full integration test

**Files:** (none new)

- [ ] **Step 1: Run Python tests**

```bash
uv run pytest ninja-slice/tests/test_detection.py -v
```

Expected: `5 passed`

- [ ] **Step 2: Run JS tests**

```bash
node ninja-slice/tests/test_collision.js
```

Expected: `9 passed, 0 failed`

- [ ] **Step 3: End-to-end with camera (optional)**

```bash
# Terminal 1
cd ninja-slice && uv run python server.py

# Terminal 2
open ninja-slice/index.html
```

Verify server prints `Camera opened: WxH` and swipes triggered by arm motion register in-game.

- [ ] **Step 4: Final commit**

```bash
git add .
git commit -m "feat: complete Ninja Slice AR game v1"
```
