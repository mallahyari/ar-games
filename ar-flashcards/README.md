# AR Flashcards

Point your phone camera at a QR code and a flashcard appears floating above it in augmented reality. Hold it steady for 2 seconds and the answer reveals.

No app install needed — runs entirely in the phone browser.

## How it works

1. QR codes are printed or displayed on screen — each one maps to a flashcard
2. You open the AR viewer on your phone browser
3. Point the camera at a QR code — the question appears as a floating card
4. Hold steady for 2 seconds — the answer reveals
5. Multiple cards can be detected simultaneously

## Quick start

**1. Generate QR markers (one time):**
```bash
uv run python generate_qr_markers.py
```

**2. Start the HTTPS server** (from the `ar-games` root):
```bash
uv run python https_server.py
```

**3. On your phone, open:**
```
https://YOUR_LAPTOP_IP:8443/ar-flashcards/mobile.html
```

**4. View or print the QR marker cards:**
```
https://YOUR_LAPTOP_IP:8443/ar-flashcards/markers.html
```

> Accept the self-signed certificate warning: tap **Advanced → Proceed**

Both devices must be on the same WiFi network.

## Customize flashcards

Edit `cards.json`:
```json
{
  "0": {
    "question": "What is the powerhouse of the cell?",
    "answer": "The Mitochondria",
    "emoji": "⚡",
    "color": "#ff6b9d"
  }
}
```

Supported IDs: 0–4. Add more by extending `cards.json` and re-running `generate_qr_markers.py`.

## Files

| File | Purpose |
|------|---------|
| `mobile.html` | AR viewer — open on phone |
| `markers.html` | QR marker cards — print or display |
| `cards.json` | Flashcard content |
| `generate_qr_markers.py` | Generates QR code images |
| `https_server.py` | Local HTTPS server (in parent folder) |
