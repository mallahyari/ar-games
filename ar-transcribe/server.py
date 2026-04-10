"""
AR Transcribe — FastAPI server.

New architecture:
- laptop.html  captures tab audio via getDisplayMedia() and streams PCM to /ws/audio
- server.py    forwards audio to Deepgram, translates with Gemini, broadcasts to /ws/display
- mobile.html  connects to /ws/display and shows live transcript/translation as AR overlay

Run:
    DEEPGRAM_API_KEY=your_key GEMINI_API_KEY=your_key uv run python ar-transcribe/server.py
"""
import asyncio
import json
import os
import socket
import subprocess
from contextlib import asynccontextmanager
from pathlib import Path

import websockets
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from google import genai
import uvicorn

SAMPLE_RATE = 16000   # browser resamples to this before sending
DEEPGRAM_URL = (
    "wss://api.deepgram.com/v1/listen"
    "?model=nova-3"
    "&language=en-US"
    "&encoding=linear16"
    f"&sample_rate={SAMPLE_RATE}"
    "&channels=1"
    "&smart_format=true"
    "&interim_results=false"
    "&endpointing=300"
)

GEMINI_MODEL = "gemini-3.1-flash-lite-preview"
TARGET_LANG = "Persian (Farsi)"

# Phones waiting for transcript/translation
display_clients: set[WebSocket] = set()
gemini_client: genai.Client | None = None


async def translate(text: str) -> str:
    try:
        response = await asyncio.to_thread(
            gemini_client.models.generate_content,
            model=GEMINI_MODEL,
            contents=(
                f"Translate the following to {TARGET_LANG}. "
                f"Return only the translation, no explanation:\n\n{text}"
            ),
        )
        return response.text.strip()
    except Exception as e:
        print(f"[translate error] {e}", flush=True)
        return text


async def broadcast(payload: dict) -> None:
    """Send JSON payload to all display clients (phones)."""
    global display_clients
    message = json.dumps(payload)
    dead: set[WebSocket] = set()
    for ws in list(display_clients):
        try:
            await ws.send_text(message)
        except Exception:
            dead.add(ws)
    display_clients -= dead


@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.websocket("/ws/audio")
async def audio_endpoint(websocket: WebSocket):
    """
    Receives raw PCM audio chunks from laptop.html,
    streams them to Deepgram, translates results, broadcasts to phones.
    """
    await websocket.accept()
    api_key = os.environ["DEEPGRAM_API_KEY"]
    headers = {"Authorization": f"Token {api_key}"}

    print("[audio] Laptop connected, opening Deepgram stream...", flush=True)

    try:
        async with websockets.connect(DEEPGRAM_URL, additional_headers=headers) as dg_ws:
            print("[audio] Deepgram connected.", flush=True)

            async def receive_from_laptop():
                """Forward audio chunks from browser to Deepgram."""
                try:
                    while True:
                        data = await websocket.receive_bytes()
                        await dg_ws.send(data)
                except WebSocketDisconnect:
                    print("[audio] Laptop disconnected.", flush=True)
                    await dg_ws.close()

            async def receive_from_deepgram():
                """Receive transcripts from Deepgram, translate, broadcast."""
                async for msg in dg_ws:
                    data = json.loads(msg)
                    if data.get("type") == "Results":
                        alts = data.get("channel", {}).get("alternatives", [])
                        if alts and data.get("is_final"):
                            transcript = alts[0].get("transcript", "").strip()
                            if transcript:
                                print(f"[transcript] {transcript}", flush=True)
                                # Broadcast transcript immediately
                                await broadcast({"type": "transcript", "text": transcript})
                                # Translate and broadcast
                                translated = await translate(transcript)
                                print(f"[translated] {translated}", flush=True)
                                await broadcast({"type": "translation", "text": translated})

            await asyncio.gather(receive_from_laptop(), receive_from_deepgram())

    except Exception as e:
        print(f"[audio] Error: {e}", flush=True)


@app.websocket("/ws/display")
async def display_endpoint(websocket: WebSocket):
    """Phone connects here to receive transcript/translation."""
    await websocket.accept()
    display_clients.add(websocket)
    print(f"[display] Phone connected. Total: {len(display_clients)}", flush=True)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        display_clients.discard(websocket)
        print(f"[display] Phone disconnected. Total: {len(display_clients)}", flush=True)


@app.get("/health")
async def health():
    return {"status": "ok", "display_clients": len(display_clients)}


app.mount(
    "/ar-transcribe",
    StaticFiles(directory=str(Path(__file__).parent), html=True),
    name="static",
)


if __name__ == "__main__":
    CERT = Path(__file__).parent.parent / "_dev_cert.pem"
    KEY = Path(__file__).parent.parent / "_dev_key.pem"

    if not CERT.exists():
        print("Generating self-signed certificate...")
        subprocess.run(
            [
                "openssl", "req", "-x509", "-newkey", "rsa:2048",
                "-keyout", str(KEY), "-out", str(CERT),
                "-days", "365", "-nodes", "-subj", "/CN=localhost",
            ],
            check=True,
        )

    for key in ("DEEPGRAM_API_KEY", "GEMINI_API_KEY"):
        if key not in os.environ:
            print(f"ERROR: {key} environment variable not set.")
            raise SystemExit(1)

    gemini_client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    try:
        local_ip = socket.gethostbyname(socket.gethostname())
    except Exception:
        local_ip = "127.0.0.1"

    print(f"\nAR Transcribe:")
    print(f"  Laptop page : https://{local_ip}:8443/ar-transcribe/laptop.html")
    print(f"  Phone page  : https://{local_ip}:8443/ar-transcribe/mobile.html\n")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8443,
        ssl_certfile=str(CERT),
        ssl_keyfile=str(KEY),
    )
