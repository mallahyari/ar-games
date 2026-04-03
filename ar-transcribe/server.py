"""
AR Transcribe — FastAPI server.
Captures laptop mic audio, streams to Deepgram for real-time transcription,
and forwards transcript words to connected phone browsers via WebSocket.

Run:
    DEEPGRAM_API_KEY=your_key uv run python ar-transcribe/server.py
"""
import asyncio
import json
import os
import socket
import subprocess
from contextlib import asynccontextmanager
from pathlib import Path

import numpy as np
import sounddevice as sd
import websockets
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from google import genai
import uvicorn

SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK_SIZE = 1600   # 100 ms at 16 kHz

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

clients: set[WebSocket] = set()
selected_device: int | None = None  # set at startup
gemini_client: genai.Client | None = None


async def translate(text: str) -> str:
    """Translate text to Persian using Gemini Flash."""
    try:
        response = await asyncio.to_thread(
            gemini_client.models.generate_content,
            model=GEMINI_MODEL,
            contents=f"Translate the following to {TARGET_LANG}. Return only the translation, no explanation:\n\n{text}",
        )
        return response.text.strip()
    except Exception as e:
        print(f"[translate error] {e}", flush=True)
        return text  # fall back to original if translation fails


def pick_device() -> int | None:
    """Print available input devices and let user choose one."""
    devices = sd.query_devices()
    inputs = [(i, d) for i, d in enumerate(devices) if d["max_input_channels"] > 0]

    print("\nAvailable audio input devices:")
    for i, (idx, d) in enumerate(inputs):
        print(f"  {i}) [{idx}] {d['name']}")

    print(f"\nPress Enter to use default, or enter a number (0-{len(inputs)-1}): ", end="", flush=True)
    choice = input().strip()
    if not choice:
        print("Using default input device.", flush=True)
        return None
    try:
        chosen = inputs[int(choice)]
        print(f"Using: {chosen[1]['name']}", flush=True)
        return chosen[0]
    except (ValueError, IndexError):
        print("Invalid choice, using default.", flush=True)
        return None


async def broadcast(text: str) -> None:
    global clients
    dead: set[WebSocket] = set()
    for ws in list(clients):
        try:
            await ws.send_text(text)
        except Exception:
            dead.add(ws)
    clients -= dead


async def run_transcription() -> None:
    """Capture mic audio and stream to Deepgram via raw WebSocket."""
    loop = asyncio.get_event_loop()
    api_key = os.environ["DEEPGRAM_API_KEY"]
    headers = {"Authorization": f"Token {api_key}"}

    # Use device's native sample rate to avoid resampling issues
    dev_info = sd.query_devices(selected_device, "input")
    actual_rate = int(dev_info["default_samplerate"])
    print(f"Device: {dev_info['name']} @ {actual_rate} Hz", flush=True)

    dg_url = (
        "wss://api.deepgram.com/v1/listen"
        "?model=nova-3"
        "&language=en-US"
        "&encoding=linear16"
        f"&sample_rate={actual_rate}"
        "&channels=1"
        "&smart_format=true"
        "&interim_results=false"
        "&endpointing=300"
    )
    chunk_size = actual_rate // 10  # 100 ms

    while True:
        try:
            print("Connecting to Deepgram...", flush=True)
            async with websockets.connect(dg_url, additional_headers=headers) as ws:
                print("Connected. Listening to microphone...", flush=True)

                audio_queue: asyncio.Queue[bytes] = asyncio.Queue()

                def audio_callback(indata, frames, time_info, status):
                    pcm = (indata[:, 0] * 32767).astype(np.int16)
                    loop.call_soon_threadsafe(audio_queue.put_nowait, pcm.tobytes())

                async def send_audio():
                    while True:
                        chunk = await audio_queue.get()
                        await ws.send(chunk)

                async def receive():
                    async for msg in ws:
                        data = json.loads(msg)
                        if data.get("type") == "Results":
                            alts = data.get("channel", {}).get("alternatives", [])
                            if alts and data.get("is_final"):
                                text = alts[0].get("transcript", "").strip()
                                if text:
                                    print(f"[transcript] {text}", flush=True)
                                    translated = await translate(text)
                                    print(f"[translated] {translated}", flush=True)
                                    await broadcast(translated)

                with sd.InputStream(
                    device=selected_device,
                    samplerate=actual_rate,
                    channels=1,
                    dtype="float32",
                    blocksize=chunk_size,
                    callback=audio_callback,
                ):
                    await asyncio.gather(send_audio(), receive())

        except Exception as e:
            print(f"Deepgram error: {e}. Reconnecting in 3s...", flush=True)
            await asyncio.sleep(3)


@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(run_transcription())
    yield


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await websocket.accept()
    clients.add(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        clients.discard(websocket)


@app.get("/health")
async def health():
    return {"status": "ok"}


# Serve ar-transcribe static files at /ar-transcribe/
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

    try:
        local_ip = socket.gethostbyname(socket.gethostname())
    except Exception:
        local_ip = "127.0.0.1"

    print(f"\nAR Transcribe — single server on port 8443:")
    print(f"  https://{local_ip}:8443/ar-transcribe/mobile.html\n")

    if "DEEPGRAM_API_KEY" not in os.environ:
        print("ERROR: DEEPGRAM_API_KEY environment variable not set.")
        raise SystemExit(1)
    if "GEMINI_API_KEY" not in os.environ:
        print("ERROR: GEMINI_API_KEY environment variable not set.")
        raise SystemExit(1)

    gemini_client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    print(f"Translation: English → {TARGET_LANG} via Gemini Flash", flush=True)

    selected_device = pick_device()

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8443,
        ssl_certfile=str(CERT),
        ssl_keyfile=str(KEY),
    )
