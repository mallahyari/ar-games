"""
Debug viewer for SwipeDetector (MediaPipe Hands).
Shows camera feed with hand skeleton overlay.
Green skeleton = hand detected. Red arrow = swipe fired.
Press Q to quit.
"""
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python as mp_tasks
from mediapipe.tasks.python import vision
import os

MODEL_PATH = os.path.join(os.path.dirname(__file__), 'models', 'hand_landmarker.task')

# Hand connections for drawing skeleton
HAND_CONNECTIONS = [
    (0,1),(1,2),(2,3),(3,4),        # thumb
    (0,5),(5,6),(6,7),(7,8),        # index
    (0,9),(9,10),(10,11),(11,12),   # middle
    (0,13),(13,14),(14,15),(15,16), # ring
    (0,17),(17,18),(18,19),(19,20), # pinky
    (5,9),(9,13),(13,17),           # palm
]

options = vision.HandLandmarkerOptions(
    base_options=mp_tasks.BaseOptions(model_asset_path=MODEL_PATH),
    running_mode=vision.RunningMode.IMAGE,
    num_hands=1,
    min_hand_detection_confidence=0.7,
    min_hand_presence_confidence=0.5,
    min_tracking_confidence=0.5,
)
landmarker = vision.HandLandmarker.create_from_options(options)

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("ERROR: Cannot open camera")
    exit(1)

w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
print(f"Camera: {w}x{h}  |  velocity_threshold=0.05  |  Press Q to quit")

prev_wrist = None
swipe_flash = 0
VELOCITY_THRESHOLD = 0.05

while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.flip(frame, 1)
    display = frame.copy()
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    result = landmarker.detect(mp_image)

    if result.hand_landmarks:
        landmarks = result.hand_landmarks[0]

        # Draw skeleton
        pts = [(int(lm.x * w), int(lm.y * h)) for lm in landmarks]
        for a, b in HAND_CONNECTIONS:
            cv2.line(display, pts[a], pts[b], (0, 255, 0), 2)
        for pt in pts:
            cv2.circle(display, pt, 4, (0, 255, 0), -1)

        # Highlight wrist (landmark 0)
        cv2.circle(display, pts[0], 10, (255, 255, 0), -1)

        wrist = landmarks[0]
        wx, wy = wrist.x, wrist.y

        if prev_wrist is not None:
            dx = wx - prev_wrist[0]
            dy = wy - prev_wrist[1]
            speed = np.hypot(dx, dy)

            # Show current speed
            cv2.putText(display, f"speed={speed:.3f}", (10, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

            if speed >= VELOCITY_THRESHOLD:
                swipe_flash = 15
                p1 = (int(prev_wrist[0] * w), int(prev_wrist[1] * h))
                p2 = (int(wx * w), int(wy * h))
                cv2.arrowedLine(display, p1, p2, (0, 0, 255), 3, tipLength=0.3)
                print(f"SWIPE  speed={speed:.3f}  "
                      f"({prev_wrist[0]:.2f},{prev_wrist[1]:.2f}) → ({wx:.2f},{wy:.2f})")

        prev_wrist = (wx, wy)
    else:
        prev_wrist = None
        cv2.putText(display, "No hand detected", (10, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

    if swipe_flash > 0:
        cv2.putText(display, "SWIPE!", (w // 2 - 80, 80),
                    cv2.FONT_HERSHEY_SIMPLEX, 2.0, (0, 0, 255), 4)
        swipe_flash -= 1

    cv2.putText(display, f"vel_thresh={VELOCITY_THRESHOLD}",
                (10, h - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1)

    cv2.imshow("Ninja Slice — Detection Debug (Q to quit)", display)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
landmarker.close()
cv2.destroyAllWindows()
