import os
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python as mp_tasks
from mediapipe.tasks.python import vision

_MODEL_PATH = os.path.join(os.path.dirname(__file__), 'models', 'hand_landmarker.task')


class SwipeDetector:
    def __init__(self, velocity_threshold=0.05):
        """
        velocity_threshold: minimum wrist displacement per frame in normalized
        coords (0-1) to register as a swipe. At 30fps, 0.05 means the wrist
        must travel 5% of the frame width per frame — a fast deliberate swipe.
        """
        options = vision.HandLandmarkerOptions(
            base_options=mp_tasks.BaseOptions(model_asset_path=_MODEL_PATH),
            running_mode=vision.RunningMode.IMAGE,
            num_hands=1,
            min_hand_detection_confidence=0.7,
            min_hand_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self.hands = vision.HandLandmarker.create_from_options(options)
        self.velocity_threshold = velocity_threshold
        self.prev_wrist = None
        # kept for interface compatibility with server.py
        self.frame_w = 1
        self.frame_h = 1

    def set_frame_size(self, w, h):
        self.frame_w = w
        self.frame_h = h

    def process_frame(self, frame):
        """Process a BGR frame. Returns swipe dict or None."""
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = self.hands.detect(mp_image)

        if not result.hand_landmarks:
            self.prev_wrist = None
            return None

        # Landmark 0 is the wrist; coords are already normalized 0-1
        wrist = result.hand_landmarks[0][0]
        wx, wy = wrist.x, wrist.y

        swipe = None
        if self.prev_wrist is not None:
            dx = wx - self.prev_wrist[0]
            dy = wy - self.prev_wrist[1]
            if np.hypot(dx, dy) >= self.velocity_threshold:
                swipe = {
                    'type': 'swipe',
                    'x1': round(self.prev_wrist[0], 4),
                    'y1': round(self.prev_wrist[1], 4),
                    'x2': round(wx, 4),
                    'y2': round(wy, 4),
                }

        self.prev_wrist = (wx, wy)
        return swipe

    def close(self):
        self.hands.close()
