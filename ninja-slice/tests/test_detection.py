import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import numpy as np
import pytest
from detection import SwipeDetector


def bgr_frame(h=480, w=640, val=0):
    return np.full((h, w, 3), val, dtype=np.uint8)


def test_no_swipe_on_first_frame():
    det = SwipeDetector()
    det.set_frame_size(640, 480)
    assert det.process_frame(bgr_frame()) is None


def test_no_swipe_on_static_scene():
    det = SwipeDetector()
    det.set_frame_size(640, 480)
    frame = bgr_frame(val=50)
    det.process_frame(frame)
    assert det.process_frame(frame) is None


def test_swipe_detected_on_fast_motion():
    det = SwipeDetector(min_area=100, velocity_threshold=10)
    det.set_frame_size(640, 480)
    f1 = bgr_frame()
    f1[90:130, 90:130] = 200
    f2 = bgr_frame()
    f2[200:240, 300:340] = 200
    f3 = bgr_frame()
    f3[310:350, 450:490] = 200
    det.process_frame(f1)
    det.process_frame(f2)
    result = det.process_frame(f3)
    assert result is not None
    assert result['type'] == 'swipe'


def test_swipe_coords_normalized():
    det = SwipeDetector(min_area=100, velocity_threshold=10)
    det.set_frame_size(640, 480)
    f1 = bgr_frame()
    f1[90:130, 90:130] = 200
    f2 = bgr_frame()
    f2[200:240, 300:340] = 200
    f3 = bgr_frame()
    f3[310:350, 450:490] = 200
    det.process_frame(f1)
    det.process_frame(f2)
    result = det.process_frame(f3)
    assert result is not None
    for key in ('x1', 'y1', 'x2', 'y2'):
        assert 0.0 <= result[key] <= 1.0, f"{key}={result[key]} out of [0,1]"


def test_slow_motion_not_detected():
    det = SwipeDetector(min_area=100, velocity_threshold=100)
    det.set_frame_size(640, 480)
    f1 = bgr_frame()
    f1[90:130, 90:130] = 200
    f2 = bgr_frame()
    f2[92:132, 92:132] = 200  # tiny shift
    f3 = bgr_frame()
    f3[94:134, 94:134] = 200  # another tiny shift, still well below threshold=100
    det.process_frame(f1)
    det.process_frame(f2)
    assert det.process_frame(f3) is None
