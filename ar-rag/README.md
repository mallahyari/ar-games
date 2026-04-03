# AR RAG

An augmented reality demo that streams AI-generated answers onto physical QR cards using your phone camera.

Point your phone at a QR card and a floating information panel appears above it — topic, emoji, streamed answer, and a link to read more. The answer streams word by word from a FastAPI backend, simulating a live RAG pipeline.

![AR RAG demo](../ar-rag-demo.gif)

## How It Works

1. Phone camera scans a QR code via `jsQR` in the browser
2. QR payload (e.g. `flashcard:4`) is sent to the FastAPI backend
3. Backend returns card metadata (topic, emoji, color, URL) and streams the answer via Server-Sent Events
4. Answer is rendered as a floating card overlaid on the camera feed
5. A tappable link at the bottom opens the full article

## Project Structure

```
ar-rag/
├── backend.py              # FastAPI server — card metadata + SSE streaming
├── cards.json              # Card definitions (topic, query, emoji, color, url)
├── mobile.html             # Phone AR viewer (camera + canvas + DOM overlay)
├── markers.html            # Printable QR card sheet
├── generate_qr_markers.py  # Generates QR PNG files
└── markers/                # Generated QR images (qr_0.png … qr_4.png)
```

## Setup

### Requirements

```bash
uv add fastapi uvicorn qrcode[pil]
```

### Generate QR markers

```bash
uv run python ar-rag/generate_qr_markers.py
```

### Start the backend (HTTPS required for phone camera)

```bash
uv run python ar-rag/backend.py
```

On first run it generates a self-signed certificate (`_dev_cert.pem` / `_dev_key.pem`) in the project root.

### Start the static file server (from project root)

```bash
uv run python https_server.py
```

## Usage

1. On your laptop, open `https://localhost:8443/ar-rag/markers.html` and print the cards (or display on screen)
2. On your phone, open `https://<your-laptop-ip>:8443/ar-rag/mobile.html`
3. Accept the self-signed certificate warning
4. Point your phone camera at any QR card

The AR panel appears above the card and streams the answer in real time. Tap **🔗 Read more** to open the Wikipedia article.

## Cards

Five built-in topics:

| # | Topic | Emoji |
|---|-------|-------|
| 0 | Photosynthesis | 🌱 |
| 1 | Black Holes | 🌑 |
| 2 | The Internet | 🌐 |
| 3 | DNA | 🧬 |
| 4 | Gravity | 🍎 |

To add cards, edit `cards.json` and add a matching entry in `ANSWERS` in `backend.py`. Replace `ANSWERS` with a real RAG pipeline (e.g. Claude API + document retrieval) for production use.

## Replacing with a Real RAG Pipeline

The `generate_answer()` function in `backend.py` is the only thing to swap out:

```python
async def generate_answer(card_id: str):
    # Replace this with your LLM / RAG pipeline
    # yield chunks as they arrive
    yield f"data: {chunk}\n\n"
    yield "data: [DONE]\n\n"
```

Any streaming LLM (Claude, OpenAI, local Ollama) can slot in here.
