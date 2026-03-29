"""
Debug viewer for SwipeDetector (MediaPipe Hands + gesture accumulation).
Shows camera feed with hand skeleton overlay.
- Yellow dot = wrist
- Blue trail = gesture in progress (start → current wrist)
- Red arrow + "SWIPE!" = completed gesture emitted to game
Press Q to quit.
"""
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python as mp_tasks
from mediapipe.tasks.python import vision
import os

MODEL_PATH = os.path.join(os.path.dirname(__file__), 'models', 'hand_landmarker.task')

HAND_CONNECTIONS = [
    (0,1),(1,2),(2,3),(3,4),
    (0,5),(5,6),(6,7),(7,8),
    (0,9),(9,10),(10,11),(11,12),
    (0,13),(13,14),(14,15),(15,16),
    (0,17),(17,18),(18,19),(19,20),
    (5,9),(9,13),(13,17),
]

VELOCITY_THRESHOLD = 0.04
QUIET_FRAMES = 4

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

W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
print(f"Camera: {W}x{H}  |  vel_thresh={VELOCITY_THRESHOLD}  quiet_frames={QUIET_FRAMES}  |  Q to quit")

prev_wrist = None
swipe_start = None
swipe_active = False
quiet_count = 0
swipe_flash = 0
last_swipe = None  # (p1, p2) pixels of last completed swipe

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
        pts = [(int(lm.x * W), int(lm.y * H)) for lm in landmarks]
        for a, b in HAND_CONNECTIONS:
            cv2.line(display, pts[a], pts[b], (0, 220, 0), 2)
        for pt in pts:
            cv2.circle(display, pt, 4, (0, 220, 0), -1)
        cv2.circle(display, pts[0], 10, (0, 220, 255), -1)  # wrist = cyan

        wrist = landmarks[0]
        wx, wy = wrist.x, wrist.y

        if prev_wrist is not None:
            dx = wx - prev_wrist[0]
            dy = wy - prev_wrist[1]
            speed = np.hypot(dx, dy)

            cv2.putText(display, f"speed={speed:.3f}", (10, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

            if speed >= VELOCITY_THRESHOLD:
                if not swipe_active:
                    swipe_start = prev_wrist
                    swipe_active = True
                quiet_count = 0
            elif swipe_active:
                quiet_count += 1
                if quiet_count >= QUIET_FRAMES:
                    # Gesture complete
                    p1 = (int(swipe_start[0] * W), int(swipe_start[1] * H))
                    p2 = (int(wx * W), int(wy * H))
                    last_swipe = (p1, p2)
                    swipe_flash = 25
                    print(f"SWIPE  ({swipe_start[0]:.2f},{swipe_start[1]:.2f}) → ({wx:.2f},{wy:.2f})")
                    swipe_active = False
                    swipe_start = None
                    quiet_count = 0

        # Draw in-progress gesture trail in blue
        if swipe_active and swipe_start:
            p1 = (int(swipe_start[0] * W), int(swipe_start[1] * H))
            p2 = (int(wx * W), int(wy * H))
            cv2.line(display, p1, p2, (255, 100, 0), 3)
            cv2.circle(display, p1, 8, (255, 100, 0), -1)

        prev_wrist = (wx, wy)
    else:
        if swipe_active and swipe_start and prev_wrist:
            p1 = (int(swipe_start[0] * W), int(swipe_start[1] * H))
            p2 = (int(prev_wrist[0] * W), int(prev_wrist[1] * H))
            last_swipe = (p1, p2)
            swipe_flash = 25
            print(f"SWIPE (hand lost)  ({swipe_start[0]:.2f},{swipe_start[1]:.2f}) → ({prev_wrist[0]:.2f},{prev_wrist[1]:.2f})")
        swipe_active = False
        swipe_start = None
        quiet_count = 0
        prev_wrist = None
        cv2.putText(display, "No hand", (10, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

    # Draw last completed swipe as red arrow
    if swipe_flash > 0 and last_swipe:
        cv2.arrowedLine(display, last_swipe[0], last_swipe[1], (0, 0, 255), 4, tipLength=0.15)
        cv2.putText(display, "SWIPE!", (W // 2 - 80, 80),
                    cv2.FONT_HERSHEY_SIMPLEX, 2.0, (0, 0, 255), 4)
        swipe_flash -= 1

    cv2.putText(display, f"vel={VELOCITY_THRESHOLD}  quiet={QUIET_FRAMES}",
                (10, H - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (180, 180, 180), 1)

    cv2.imshow("Ninja Slice — Detection Debug (Q to quit)", display)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
landmarker.close()
cv2.destroyAllWindows()
