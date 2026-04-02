import cv2
import numpy as np


# Use the 4x4 ArUco dictionary (50 unique markers, simple and robust)
ARUCO_DICT = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
ARUCO_PARAMS = cv2.aruco.DetectorParameters()
DETECTOR = cv2.aruco.ArucoDetector(ARUCO_DICT, ARUCO_PARAMS)


def detect_markers(frame):
    """
    Detect ArUco markers in a BGR frame.
    Returns list of dicts:
      { id, corners: [[x,y], ...4 corners], center: [x, y] }
    Coordinates are normalized 0-1.
    """
    h, w = frame.shape[:2]
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    corners, ids, _ = DETECTOR.detectMarkers(gray)

    result = []
    if ids is None:
        return result

    for marker_corners, marker_id in zip(corners, ids.flatten()):
        pts = marker_corners[0]  # shape (4, 2) in pixel coords
        norm_corners = [[round(float(x) / w, 4), round(float(y) / h, 4)]
                        for x, y in pts]
        cx = round(float(pts[:, 0].mean()) / w, 4)
        cy = round(float(pts[:, 1].mean()) / h, 4)
        result.append({
            'id': int(marker_id),
            'corners': norm_corners,
            'center': [cx, cy],
        })

    return result
