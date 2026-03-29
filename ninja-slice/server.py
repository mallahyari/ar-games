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
