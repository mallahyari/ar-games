import asyncio
import json
import sys

import cv2
import mediapipe as mp
import websockets
from detection import GestureDetector
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

    detector = GestureDetector()

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                await asyncio.sleep(0.033)
                continue

            frame = cv2.flip(frame, 1)
            gesture = detector.process_frame(frame)

            if gesture and CLIENTS:
                print(f"Gesture: {gesture}")
                websockets.broadcast(CLIENTS, json.dumps(gesture))

            # Preview window
            preview = cv2.resize(frame, (640, 360))
            ph, pw = preview.shape[:2]

            # Draw detected landmarks
            rgb_small = cv2.cvtColor(preview, cv2.COLOR_BGR2RGB)
            mp_check = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_small)
            check_result = detector.hands.detect(mp_check)
            for lms in check_result.hand_landmarks:
                # index fingertip = landmark 8
                tip = lms[8]
                cv2.circle(preview, (int(tip.x * pw), int(tip.y * ph)), 10, (0, 255, 255), -1)
                wrist = lms[0]
                cv2.circle(preview, (int(wrist.x * pw), int(wrist.y * ph)), 6, (0, 200, 0), -1)

            label = f"{gesture['type'].upper()}: {gesture}" if gesture else "Waiting for gesture..."
            color = (0, 255, 0) if gesture else (180, 180, 180)
            cv2.putText(preview, label, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)
            cv2.putText(preview, "Swipe left/right | Both index fingers to zoom | Q to quit",
                        (10, ph - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)
            cv2.imshow("Gesture PDF — Camera (Q to quit)", preview)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

            await asyncio.sleep(0.033)
    finally:
        cap.release()
        cv2.destroyAllWindows()
        detector.close()


async def main(camera_index):
    print("Gesture PDF server starting on ws://localhost:8766")
    async with websockets.serve(handler, "localhost", 8766):
        await camera_loop(camera_index)


if __name__ == "__main__":
    camera_index = pick_camera()
    asyncio.run(main(camera_index))
