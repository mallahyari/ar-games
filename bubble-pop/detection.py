import os
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python as mp_tasks
from mediapipe.tasks.python import vision

_MODEL_PATH = os.path.join(os.path.dirname(__file__), 'models', 'hand_landmarker.task')


class HandDetector:
    def __init__(self):
        options = vision.HandLandmarkerOptions(
            base_options=mp_tasks.BaseOptions(model_asset_path=_MODEL_PATH),
            running_mode=vision.RunningMode.IMAGE,
            num_hands=2,
            min_hand_detection_confidence=0.6,
            min_hand_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self.hands = vision.HandLandmarker.create_from_options(options)

    def process_frame(self, frame):
        """
        Process a BGR frame.
        Returns a list of hand dicts [{type, x, y, radius}, ...] — one per detected hand.
        x, y are normalized palm center (0-1).
        radius is a normalized estimate of hand size.
        Returns empty list when no hands detected.
        """
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = self.hands.detect(mp_image)

        hands = []
        for landmarks in result.hand_landmarks:
            # Palm center: average of wrist (0) + 4 MCP joints (5,9,13,17)
            palm_indices = [0, 5, 9, 13, 17]
            px = sum(landmarks[i].x for i in palm_indices) / len(palm_indices)
            py = sum(landmarks[i].y for i in palm_indices) / len(palm_indices)

            # Hand radius: distance from wrist to middle finger MCP (landmark 9)
            wrist = landmarks[0]
            mcp = landmarks[9]
            radius = np.hypot(mcp.x - wrist.x, mcp.y - wrist.y)

            hands.append({
                'type': 'hand',
                'x': round(px, 4),
                'y': round(py, 4),
                'radius': round(radius, 4),
            })

        return hands

    def close(self):
        self.hands.close()
