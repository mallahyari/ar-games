import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import numpy as np
import pytest
from unittest.mock import MagicMock, patch
from mediapipe.tasks.python import vision


def make_frame(h=480, w=640):
    return np.zeros((h, w, 3), dtype=np.uint8)


def hand_result(x, y):
    wrist = MagicMock()
    wrist.x, wrist.y = x, y
    result = MagicMock()
    result.hand_landmarks = [[wrist]]
    return result


def no_hand():
    result = MagicMock()
    result.hand_landmarks = []
    return result


@pytest.fixture
def det():
    with patch.object(vision.HandLandmarker, 'create_from_options') as mock_create:
        mock_landmarker = MagicMock()
        mock_create.return_value = mock_landmarker
        from detection import SwipeDetector
        d = SwipeDetector(velocity_threshold=0.05, quiet_frames=2)
        d.hands = mock_landmarker
        yield d


def feed(det, results):
    """Feed a list of mock results into det, return list of non-None outputs."""
    outputs = []
    for r in results:
        det.hands.detect = MagicMock(return_value=r)
        out = det.process_frame(make_frame())
        if out is not None:
            outputs.append(out)
    return outputs


def test_no_swipe_when_no_hand(det):
    swipes = feed(det, [no_hand(), no_hand()])
    assert swipes == []


def test_no_swipe_on_first_hand_frame(det):
    swipes = feed(det, [hand_result(0.5, 0.5)])
    assert swipes == []


def test_swipe_emitted_after_gesture_completes(det):
    # fast move then 2 quiet frames → swipe emitted
    swipes = feed(det, [
        hand_result(0.2, 0.5),   # prev set
        hand_result(0.7, 0.5),   # fast: gesture starts
        hand_result(0.71, 0.5),  # slow: quiet 1
        hand_result(0.72, 0.5),  # slow: quiet 2 → emit
    ])
    assert len(swipes) == 1
    assert swipes[0]['type'] == 'swipe'


def test_swipe_covers_full_arc(det):
    # x1 should be gesture start, x2 should be near gesture end
    swipes = feed(det, [
        hand_result(0.1, 0.5),   # prev
        hand_result(0.6, 0.5),   # fast: start at x≈0.1
        hand_result(0.9, 0.5),   # still fast
        hand_result(0.91, 0.5),  # quiet 1
        hand_result(0.92, 0.5),  # quiet 2 → emit
    ])
    assert len(swipes) == 1
    s = swipes[0]
    assert s['x1'] < 0.3, f"start should be near left, got {s['x1']}"
    assert s['x2'] > 0.8, f"end should be near right, got {s['x2']}"


def test_swipe_coords_in_range(det):
    swipes = feed(det, [
        hand_result(0.2, 0.3),
        hand_result(0.8, 0.7),
        hand_result(0.81, 0.71),
        hand_result(0.82, 0.72),
    ])
    assert len(swipes) == 1
    for key in ('x1', 'y1', 'x2', 'y2'):
        assert 0.0 <= swipes[0][key] <= 1.0


def test_slow_movement_not_detected(det):
    swipes = feed(det, [
        hand_result(0.5, 0.5),
        hand_result(0.51, 0.5),  # dx=0.01, below threshold
        hand_result(0.52, 0.5),
        hand_result(0.53, 0.5),
    ])
    assert swipes == []


def test_hand_loss_mid_swipe_emits(det):
    # If hand disappears during a swipe, emit what we have
    swipes = feed(det, [
        hand_result(0.2, 0.5),
        hand_result(0.7, 0.5),  # fast: gesture starts
        no_hand(),               # lost → emit immediately
    ])
    assert len(swipes) == 1


def test_tracking_resets_after_hand_loss(det):
    # After hand loss, first reappearance does not immediately swipe
    swipes = feed(det, [
        hand_result(0.2, 0.5),
        hand_result(0.7, 0.5),  # fast
        no_hand(),               # lost → emits swipe #1
        hand_result(0.1, 0.5),  # reappears — prev_wrist reset, no swipe yet
    ])
    assert len(swipes) == 1   # only the one from before the loss
