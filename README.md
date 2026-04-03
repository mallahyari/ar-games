# AR Games

A collection of augmented reality games and interactive experiences built with Python, OpenCV, MediaPipe, and browser-based rendering. Each project mixes the physical world with digital overlays — using cameras, projectors, and hand/body tracking.

All projects share a single Python virtual environment managed by [uv](https://github.com/astral-sh/uv).

---

## Projects

### 🫧 [Bubble Pop](bubble-pop/)
Digital bubbles float up a projected wall. Reach out and pop them by moving your hand near them. The camera detects your palm position in real time using MediaPipe Hands.

**Tech:** Python + MediaPipe Hands → WebSocket → Browser Canvas

**Run:**
```bash
uv run python bubble-pop/server.py
open bubble-pop/index.html
```

---

### 📄 [Gesture PDF Viewer](gesture-pdf/)
A hands-free PDF viewer controlled by gestures. Swipe left/right to turn pages. Bring both index fingers together or apart to zoom in and out. Includes an AR mode where the PDF floats in front of your live camera feed.

**Tech:** Python + MediaPipe Hands → WebSocket → Browser (PDF.js + Canvas)

**Run:**
```bash
uv run python gesture-pdf/server.py

# Standard viewer:
open gesture-pdf/index.html

# AR mode (PDF overlaid on live camera feed):
uv run python -m http.server 8080
# then open: http://localhost:8080/gesture-pdf/ar.html
```

---

### 🎙 [AR Transcribe](ar-transcribe/)
Real-time speech-to-text as an AR overlay on your phone camera feed. Words animate in one by one with a glowing effect as you speak. Captures audio from your laptop mic or system audio (YouTube, video calls, podcasts) via BlackHole.

**Tech:** Python + Deepgram Nova-3 → WebSocket → Browser Canvas

**Run:**
```bash
DEEPGRAM_API_KEY=your_key uv run python ar-transcribe/server.py
# Choose audio input device, then on your phone open:
# https://YOUR_LAPTOP_IP:8443/ar-transcribe/mobile.html
```

---

### 🤖 [AR RAG](ar-rag/)
Point your phone at a QR card and a floating AI-powered information panel appears above it. The answer streams word by word from a FastAPI backend with a tappable link for more details.

**Tech:** QR detection (jsQR) + FastAPI SSE streaming → Canvas AR overlay + DOM link overlay

**Run:**
```bash
uv run python ar-rag/backend.py
uv run python https_server.py
# On your phone open:
# https://YOUR_LAPTOP_IP:8443/ar-rag/mobile.html
```

---

### 🃏 [AR Flashcards](ar-flashcards/)
Point your phone camera at a QR code card and a flashcard appears floating above it in AR. Hold it steady for 2 seconds and the answer reveals with an animation. Works entirely in the phone browser — no special hardware needed.

**Tech:** QR detection (jsQR) in browser + Canvas AR overlay. Python generates QR marker images.

**Setup (one time):**
```bash
uv run python ar-flashcards/generate_qr_markers.py
```

**Run:**
```bash
# Start HTTPS server (required for phone camera access)
uv run python https_server.py

# On your phone browser, open:
# https://YOUR_LAPTOP_IP:8443/ar-flashcards/mobile.html

# To view/print the QR marker cards:
# https://YOUR_LAPTOP_IP:8443/ar-flashcards/markers.html
```

> First time: your browser will warn about the self-signed certificate — tap **Advanced → Proceed**.

**Customize cards:** Edit `ar-flashcards/cards.json` to add your own questions and answers:
```json
{
  "0": {
    "question": "Your question here",
    "answer": "Your answer here",
    "emoji": "🔥",
    "color": "#ff6b9d"
  }
}
```

---

## Setup

**Requirements:** Python 3.11+, [uv](https://github.com/astral-sh/uv), a webcam

```bash
git clone <repo>
cd ar-games
uv sync
```

**MediaPipe model** (required for Ninja Slice, Bubble Pop, Gesture PDF):

Download `hand_landmarker.task` from [MediaPipe Models](https://developers.google.com/mediapipe/solutions/vision/hand_landmarker) and place it at:
```
bubble-pop/models/hand_landmarker.task
```
The gesture-pdf project symlinks to this file automatically.

---

## Architecture

Most projects follow the same pattern:

```
Camera → Python (OpenCV / MediaPipe) → WebSocket → Browser (Canvas)
```

1. Python reads camera frames and detects gestures or markers
2. Detected events are broadcast over a local WebSocket
3. The browser renders the game on a fullscreen canvas
4. For wall projection: connect a projector, fullscreen the browser

AR Flashcards runs differently — entirely in the phone browser using the phone's own camera, no Python server needed during play.

---

## Dev mode

Ninja Slice and Bubble Pop support mouse-based testing without a camera:

```
open ninja-slice/index.html?dev=1
open bubble-pop/index.html?dev=1
```
