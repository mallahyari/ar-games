"""
AR RAG Backend — FastAPI server.
For now: returns a simple streamed text response per card ID.
Swap out `generate_answer()` with your real RAG pipeline later.

Run with HTTPS (required for phone camera access):
    uv run python backend.py
"""
import asyncio
import json
import subprocess
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

app = FastAPI()

# Allow requests from the phone browser (any origin for local dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load card definitions
CARDS_PATH = Path(__file__).parent / "cards.json"
with open(CARDS_PATH) as f:
    CARDS = json.load(f)

# ── Simulated answers (replace with RAG pipeline) ─────────
ANSWERS = {
    "0": "Photosynthesis is how plants make their own food using sunlight. "
         "Plants absorb carbon dioxide from the air and water from the soil. "
         "Using energy from sunlight, they convert these into glucose — a sugar "
         "that fuels the plant's growth. Oxygen is released as a byproduct, "
         "which is the air we breathe. In short: sunlight + water + CO₂ → glucose + oxygen.",

    "1": "A black hole forms when a massive star runs out of fuel and collapses "
         "under its own gravity. The core implodes so forcefully that matter becomes "
         "infinitely dense — a point called a singularity. Gravity becomes so strong "
         "that nothing, not even light, can escape past the boundary called the event horizon. "
         "From the outside, a black hole appears completely dark.",

    "2": "The internet is a global network of computers connected by cables, fiber, "
         "and wireless signals. When you visit a website, your device sends a request "
         "through your router to your internet provider, which routes it to a server "
         "anywhere in the world. That server sends back data broken into small packets "
         "that travel independently and reassemble on your device. All of this happens "
         "in milliseconds.",

    "3": "DNA is a molecule inside every cell of your body that contains the instructions "
         "for building and running you. It's shaped like a twisted ladder — the double helix. "
         "The rungs of the ladder are pairs of chemical bases that spell out genes. "
         "Genes are instructions for making proteins, which do almost everything in your body. "
         "Your DNA is 99.9% identical to every other human, but that 0.1% makes you unique.",

    "4": "Gravity is a force of attraction between objects that have mass. "
         "The more mass an object has, the stronger its gravitational pull. "
         "Earth is so massive that it pulls everything toward its center — "
         "that's why things fall when you drop them. Einstein described gravity "
         "not as a force but as a curvature of space-time caused by mass. "
         "The Moon stays in orbit because it's constantly falling toward Earth "
         "while also moving sideways fast enough to keep missing it.",
}


async def generate_answer(card_id: str):
    """
    Streams the answer word by word.
    Replace this with your RAG pipeline — yield chunks as they come from the LLM.
    """
    card = CARDS.get(card_id)
    if not card:
        yield "data: Card not found.\n\n"
        return

    answer = ANSWERS.get(card_id, "No answer available for this card.")

    # Stream word by word with a small delay to simulate LLM generation
    words = answer.split(" ")
    for i, word in enumerate(words):
        chunk = word + (" " if i < len(words) - 1 else "")
        yield f"data: {chunk}\n\n"
        await asyncio.sleep(0.05)  # 50ms per word — adjust to taste

    # Signal end of stream
    yield "data: [DONE]\n\n"


# ── Endpoints ─────────────────────────────────────────────


@app.get("/card/{card_id}")
async def get_card(card_id: str):
    """Returns card metadata (topic, emoji, color)."""
    card = CARDS.get(card_id)
    if not card:
        return {"error": "Card not found"}
    return card


@app.get("/answer/{card_id}")
async def stream_answer(card_id: str):
    """Streams the answer for a card using Server-Sent Events."""
    return StreamingResponse(
        generate_answer(card_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/health")
async def health():
    return {"status": "ok"}


# ── Run with HTTPS ─────────────────────────────────────────
if __name__ == "__main__":
    import socket
    import uvicorn

    CERT = Path(__file__).parent.parent / "_dev_cert.pem"
    KEY  = Path(__file__).parent.parent / "_dev_key.pem"

    if not CERT.exists():
        print("Generating self-signed certificate...")
        subprocess.run([
            "openssl", "req", "-x509", "-newkey", "rsa:2048",
            "-keyout", str(KEY), "-out", str(CERT),
            "-days", "365", "-nodes", "-subj", "/CN=localhost",
        ], check=True)

    try:
        local_ip = socket.gethostbyname(socket.gethostname())
    except Exception:
        local_ip = "127.0.0.1"

    print(f"\nAR RAG backend running:")
    print(f"  Local:   https://localhost:8000")
    print(f"  Network: https://{local_ip}:8000")
    print(f"\nOn your phone open: https://{local_ip}:8443/ar-rag/mobile.html")
    print("(also run https_server.py from the ar-games root for static files)\n")

    uvicorn.run(app, host="0.0.0.0", port=8000, ssl_certfile=str(CERT), ssl_keyfile=str(KEY))
