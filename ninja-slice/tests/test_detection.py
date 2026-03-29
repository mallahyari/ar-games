import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import numpy as np
import pytest
from unittest.mock import MagicMock, patch
from mediapipe.tasks.python import vision


def make_frame(h=480, w=640):
    return np.zeros((h, w, 3), dtype=np.uint8)


def hand_result(x, y):
    """Mock HandLandmarker result with wrist at normalized (x, y)."""
    wrist = MagicMock()
    wrist.x, wrist.y = x, y
    result = MagicMock()
    result.hand_landmarks = [[wrist]]  # [hand_index][landmark_index]
    return result


def no_hand_result():
    result = MagicMock()
    result.hand_landmarks = []
    return result


@pytest.fixture
def det():
    """SwipeDetector with HandLandmarker mocked out (no model file needed)."""
    with patch.object(vision.HandLandmarker, 'create_from_options') as mock_create:
        mock_landmarker = MagicMock()
        mock_create.return_value = mock_landmarker
        from detection import SwipeDetector
        d = SwipeDetector()
        d.hands = mock_landmarker
        yield d


def test_no_swipe_when_no_hand_detected(det):
    det.hands.detect = MagicMock(return_value=no_hand_result())
    assert det.process_frame(make_frame()) is None


def test_no_swipe_on_first_hand_frame(det):
    det.hands.detect = MagicMock(return_value=hand_result(0.5, 0.5))
    assert det.process_frame(make_frame()) is None


def test_swipe_detected_on_fast_wrist_movement(det):
    det.hands.detect = MagicMock(side_effect=[
        hand_result(0.2, 0.5),
        hand_result(0.8, 0.5),  # dx=0.6, well above default threshold
    ])
    det.process_frame(make_frame())
    result = det.process_frame(make_frame())
    assert result is not None
    assert result['type'] == 'swipe'


def test_swipe_coords_normalized(det):
    det.hands.detect = MagicMock(side_effect=[
        hand_result(0.2, 0.5),
        hand_result(0.8, 0.5),
    ])
    det.process_frame(make_frame())
    result = det.process_frame(make_frame())
    assert result is not None
    for key in ('x1', 'y1', 'x2', 'y2'):
        assert 0.0 <= result[key] <= 1.0, f"{key}={result[key]} out of [0,1]"


def test_slow_wrist_movement_not_detected(det):
    det.velocity_threshold = 0.1
    det.hands.detect = MagicMock(side_effect=[
        hand_result(0.5, 0.5),
        hand_result(0.51, 0.5),  # dx=0.01, below threshold=0.1
    ])
    det.process_frame(make_frame())
    assert det.process_frame(make_frame()) is None


def test_tracking_resets_when_hand_lost(det):
    det.hands.detect = MagicMock(side_effect=[
        hand_result(0.2, 0.5),  # frame 1: hand seen, prev_wrist set
        no_hand_result(),         # frame 2: hand lost, prev_wrist cleared
        hand_result(0.8, 0.5),  # frame 3: hand back, no prev → no swipe
    ])
    det.process_frame(make_frame())
    det.process_frame(make_frame())
    assert det.process_frame(make_frame()) is None
