import os
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python as mp_tasks
from mediapipe.tasks.python import vision

_MODEL_PATH = os.path.join(os.path.dirname(__file__), 'models', 'hand_landmarker.task')

SWIPE_VELOCITY_THRESHOLD = 0.025  # horizontal speed to start a swipe
SWIPE_MIN_DISTANCE = 0.08         # minimum total horizontal travel to count as swipe
SWIPE_QUIET_FRAMES = 3
PINCH_CHANGE_THRESHOLD = 0.005   # min change in inter-finger distance per frame


class GestureDetector:
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

        # Swipe state (single hand)
        self._prev_wrist = None
        self._swipe_start = None
        self._swipe_active = False
        self._quiet_count = 0

        # Zoom state (two hands)
        self._prev_index_dist = None

    def process_frame(self, frame):
        """
        Returns a gesture dict or None.
        Page: {type:'page', direction:'next'|'prev'}
        Zoom: {type:'zoom', delta:float}  positive=in, negative=out
        """
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = self.hands.detect(mp_image)

        num_hands = len(result.hand_landmarks)

        # ── Two hands: zoom via index fingertip distance ───────────────────
        if num_hands == 2:
            self._reset_swipe()
            tip_a = result.hand_landmarks[0][8]  # index tip hand A
            tip_b = result.hand_landmarks[1][8]  # index tip hand B
            dist = np.hypot(tip_a.x - tip_b.x, tip_a.y - tip_b.y)

            gesture = None
            if self._prev_index_dist is not None:
                delta = dist - self._prev_index_dist
                if abs(delta) >= PINCH_CHANGE_THRESHOLD:
                    # Fingers moving apart (delta > 0) = zoom in
                    gesture = {'type': 'zoom', 'delta': round(delta * 10, 3)}
            self._prev_index_dist = dist
            return gesture

        # Not two hands — clear zoom state
        self._prev_index_dist = None

        if num_hands == 0:
            self._reset_swipe()
            return None

        # ── One hand: horizontal swipe for page turn ───────────────────────
        wrist = result.hand_landmarks[0][0]
        wx, wy = wrist.x, wrist.y

        if self._prev_wrist is None:
            self._prev_wrist = (wx, wy)
            return None

        dx = wx - self._prev_wrist[0]
        dy = wy - self._prev_wrist[1]
        speed = abs(dx)
        is_horizontal = abs(dx) > abs(dy) * 0.8

        gesture = None

        if speed >= SWIPE_VELOCITY_THRESHOLD and is_horizontal:
            if not self._swipe_active:
                self._swipe_start = (wx, wy)
                self._swipe_active = True
            self._quiet_count = 0
        elif self._swipe_active:
            self._quiet_count += 1
            if self._quiet_count >= SWIPE_QUIET_FRAMES:
                gesture = self._finish_swipe((wx, wy))

        self._prev_wrist = (wx, wy)
        return gesture

    def _finish_swipe(self, end_pos):
        gesture = None
        if self._swipe_active and self._swipe_start and end_pos:
            dx = end_pos[0] - self._swipe_start[0]
            # Require minimum travel distance to avoid accidental triggers
            if abs(dx) >= SWIPE_MIN_DISTANCE:
                direction = 'next' if dx < 0 else 'prev'
                gesture = {'type': 'page', 'direction': direction}
        self._reset_swipe()
        return gesture

    def _reset_swipe(self):
        self._prev_wrist = None
        self._swipe_active = False
        self._swipe_start = None
        self._quiet_count = 0

    def close(self):
        self.hands.close()
