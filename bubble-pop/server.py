import asyncio
import json
import sys

import cv2
import websockets
from detection import HandDetector
from cameras import pick_camera

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

    detector = HandDetector()
    last_hands = []

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                await asyncio.sleep(0.033)
                continue

            frame = cv2.flip(frame, 1)
            hands = detector.process_frame(frame)

            if CLIENTS:
                # Always broadcast current hand state so browser knows when hands leave
                msg = json.dumps({'type': 'hands', 'hands': hands})
                websockets.broadcast(CLIENTS, msg)

            # Preview window
            preview = cv2.resize(frame, (640, 360))
            for h_data in hands:
                cx = int(h_data['x'] * 640)
                cy = int(h_data['y'] * 360)
                r = int(h_data['radius'] * 640)
                cv2.circle(preview, (cx, cy), max(r, 10), (0, 255, 0), 2)
                cv2.circle(preview, (cx, cy), 4, (0, 255, 0), -1)
            label = f"{len(hands)} hand(s)" if hands else "No hands"
            cv2.putText(preview, label, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                        (0, 255, 0) if hands else (0, 0, 255), 2)
            cv2.imshow("Bubble Pop — Camera Preview (Q to quit)", preview)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

            await asyncio.sleep(0.033)
    finally:
        cap.release()
        cv2.destroyAllWindows()
        detector.close()


async def main(camera_index):
    print("Bubble Pop server starting on ws://localhost:8765")
    async with websockets.serve(handler, "localhost", 8765):
        await camera_loop(camera_index)


if __name__ == "__main__":
    camera_index = pick_camera()
    asyncio.run(main(camera_index))
