import os
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python as mp_tasks
from mediapipe.tasks.python import vision

_MODEL_PATH = os.path.join(os.path.dirname(__file__), 'models', 'hand_landmarker.task')


class SwipeDetector:
    def __init__(self, velocity_threshold=0.04, quiet_frames=4):
        """
        velocity_threshold: wrist displacement per frame (normalized 0-1) to
                            start/continue a swipe. 0.04 = 4% of frame width.
        quiet_frames:       how many consecutive slow frames before a swipe
                            gesture is considered complete and emitted.
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
        self.quiet_frames = quiet_frames

        self._prev_wrist = None
        self._swipe_start = None    # wrist position when gesture began
        self._swipe_active = False
        self._quiet_count = 0

        # kept for interface compatibility with server.py
        self.frame_w = 1
        self.frame_h = 1

    def set_frame_size(self, w, h):
        self.frame_w = w
        self.frame_h = h

    def process_frame(self, frame):
        """
        Process a BGR frame.
        Returns a swipe dict {type, x1, y1, x2, y2} when a full swipe gesture
        completes, or None otherwise.
        Swipe coords are normalized 0-1 and cover the full gesture arc
        (start position → end position), not just a single-frame delta.
        """
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = self.hands.detect(mp_image)

        if not result.hand_landmarks:
            # Hand lost mid-swipe → emit whatever we accumulated
            swipe = self._finish_swipe(self._prev_wrist)
            self._prev_wrist = None
            return swipe

        wrist = result.hand_landmarks[0][0]
        wx, wy = wrist.x, wrist.y

        if self._prev_wrist is None:
            self._prev_wrist = (wx, wy)
            return None

        dx = wx - self._prev_wrist[0]
        dy = wy - self._prev_wrist[1]
        speed = np.hypot(dx, dy)

        swipe = None

        if speed >= self.velocity_threshold:
            # Moving fast — start or continue gesture
            if not self._swipe_active:
                self._swipe_start = self._prev_wrist
                self._swipe_active = True
            self._quiet_count = 0

        elif self._swipe_active:
            # Slowing down — count quiet frames
            self._quiet_count += 1
            if self._quiet_count >= self.quiet_frames:
                swipe = self._finish_swipe((wx, wy))

        self._prev_wrist = (wx, wy)
        return swipe

    def _finish_swipe(self, end_pos):
        """Emit swipe from gesture start to end_pos, then reset state."""
        swipe = None
        if self._swipe_active and self._swipe_start and end_pos:
            swipe = {
                'type': 'swipe',
                'x1': round(self._swipe_start[0], 4),
                'y1': round(self._swipe_start[1], 4),
                'x2': round(end_pos[0], 4),
                'y2': round(end_pos[1], 4),
            }
        self._swipe_active = False
        self._swipe_start = None
        self._quiet_count = 0
        return swipe

    def close(self):
        self.hands.close()
