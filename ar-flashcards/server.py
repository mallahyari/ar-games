import asyncio
import json
import sys

import cv2
from detection import detect_markers
from cameras import pick_camera
import websockets

CLIENTS: set = set()


async def handler(websocket):
    CLIENTS.add(websocket)
    print(f"Client connected: {websocket.remote_address}")
    try:
        await websocket.wait_closed()
    finally:
        CLIENTS.discard(websocket)
        print("Client disconnected")


async def camera_loop(camera_index):
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        print(f"ERROR: Could not open camera {camera_index}")
        sys.exit(1)

    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"Camera opened: {w}x{h}")

    prev_ids = set()

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                await asyncio.sleep(0.033)
                continue

            frame = cv2.flip(frame, 1)
            markers = detect_markers(frame)

            if CLIENTS:
                msg = json.dumps({'type': 'markers', 'markers': markers})
                websockets.broadcast(CLIENTS, msg)

            # Preview window
            preview = cv2.resize(frame, (640, 360))
            ph, pw = preview.shape[:2]
            for m in markers:
                pts = [[int(c[0] * pw), int(c[1] * ph)] for c in m['corners']]
                pts_np = [pts]
                cv2.polylines(preview, [__import__('numpy').array(pts_np)], True, (0, 255, 0), 2)
                cx, cy = int(m['center'][0] * pw), int(m['center'][1] * ph)
                cv2.putText(preview, f"ID:{m['id']}", (cx - 20, cy),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            label = f"{len(markers)} marker(s) detected" if markers else "No markers — hold a card up"
            cv2.putText(preview, label, (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                        0.7, (0, 255, 0) if markers else (180, 180, 180), 2)
            cv2.imshow("AR Flashcards — Camera (Q to quit)", preview)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

            await asyncio.sleep(0.033)
    finally:
        cap.release()
        cv2.destroyAllWindows()


async def main(camera_index):
    print("AR Flashcards server starting on ws://localhost:8767")
    async with websockets.serve(handler, "localhost", 8767):
        await camera_loop(camera_index)


if __name__ == "__main__":
    camera_index = pick_camera()
    asyncio.run(main(camera_index))
