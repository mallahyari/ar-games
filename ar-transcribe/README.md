# AR Transcribe

Real-time speech-to-text as an augmented reality overlay on your phone. Point your phone camera at anything — a speaker, a screen, a room — and see live transcription floating over the camera feed with animated word-by-word reveal and a blue glow effect.

Audio is captured on the laptop, transcribed by Deepgram Nova-3, and streamed to the phone over WebSocket.

## Architecture

```mermaid
flowchart LR
    subgraph Laptop
        A[Audio Input\nMic / BlackHole] -->|PCM 16-bit| B[sounddevice]
        B -->|audio chunks| C[FastAPI Server\nport 8443]
        C <-->|WebSocket streaming| D[Deepgram Nova-3\napi.deepgram.com]
        D -->|final transcript| C
    end

    subgraph Phone Browser
        E[Camera Feed\ncanvas]
        F[WebSocket Client\nwss://laptop:8443/ws]
        G[AR Overlay\nword reveal + glow]
        F -->|transcript text| G
        E --- G
    end

    C -->|transcript text| F
    C -->|serves mobile.html| Phone Browser
```

## How It Works

1. `server.py` opens a selected audio input device via `sounddevice`
2. 100ms PCM chunks are streamed to Deepgram's live WebSocket API
3. Deepgram returns final transcripts (Nova-3 model, ~300ms latency)
4. The server forwards each sentence to all connected phone browsers via WebSocket
5. `mobile.html` renders the camera feed on a canvas and animates each word into view with a glowing effect

## Project Structure

```
ar-transcribe/
├── server.py       # FastAPI server — audio capture, Deepgram, WebSocket broadcast
└── mobile.html     # Phone AR viewer — camera feed + transcript overlay
```

## Setup

### Requirements

```bash
uv add fastapi uvicorn websockets sounddevice numpy
```

You need a [Deepgram](https://deepgram.com) API key. The free tier includes 200 hours/month.

### Run

```bash
DEEPGRAM_API_KEY=your_key uv run python ar-transcribe/server.py
```

On startup it lists all available audio input devices and lets you pick one:

```
Available audio input devices:
  0) [0] MacBook Pro Microphone
  1) [2] BlackHole 2ch
  2) [3] MirrorMeister Audio

Press Enter to use default, or enter a number:
```

Then on your phone open:

```
https://<your-laptop-ip>:8443/ar-transcribe/mobile.html
```

> The server also serves the static file — no separate static server needed.

## Audio Input Options

| Source | How |
|--------|-----|
| **Laptop mic** | Default — pick `MacBook Pro Microphone` |
| **Room / speaker nearby** | Same — point laptop toward the sound |
| **System audio (YouTube, video calls)** | Install BlackHole (see below), pick `BlackHole 2ch` |
| **iPhone mic** | Shows as `Mehdi's iPhone Microphone` via Continuity Camera — requires iPhone to be active as webcam |

### Capturing System Audio with BlackHole

To transcribe audio playing on the laptop screen (YouTube, podcasts, video calls):

1. Install BlackHole: `brew install blackhole-2ch`
2. Open **Audio MIDI Setup** → `+` → **Create Multi-Output Device**
3. Check **BlackHole 2ch** + **MacBook Pro Speakers** (so you still hear audio)
4. **System Settings → Sound → Output** → select **Multi-Output Device**
5. **System Settings → Sound → Input** → select **BlackHole 2ch**
6. Restart the server and pick **BlackHole 2ch**

## Phone UI

- **Green dot** — connected to server
- **🎙 icon** — pulsing when live
- Words animate in one by one (70ms apart) with a slide-up effect
- Current sentence glows in blue and pulses
- Last 3 sentences visible, older ones fade out

## Certificate

The server auto-generates a self-signed TLS certificate (`_dev_cert.pem`) on first run, required for `getUserMedia` (camera access) over HTTPS. Accept the browser warning once on both laptop and phone.

## Use Cases

- **Accessibility** — live captions for deaf/hard-of-hearing in real conversations
- **Lectures / talks** — AR captions floating over the speaker
- **Video transcription** — transcribe YouTube, Netflix, video calls in real time
- **Language learning** — see words as they're spoken
- **Add translation** — pipe transcripts through an LLM to show translated text instead
