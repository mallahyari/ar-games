import cv2
import numpy as np


class SwipeDetector:
    def __init__(self, min_area=500, velocity_threshold=30):
        self.prev_gray = None
        self.prev_centroid = None
        self.min_area = min_area
        self.velocity_threshold = velocity_threshold
        self.frame_w = 1
        self.frame_h = 1

    def set_frame_size(self, w, h):
        self.frame_w = w
        self.frame_h = h

    def process_frame(self, frame):
        """Process a BGR frame. Returns swipe dict or None."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        # On first frame, just store it and initialize centroid
        if self.prev_gray is None:
            self.prev_gray = gray
            # Try to find initial centroid from first frame
            _, thresh = cv2.threshold(gray, 25, 255, cv2.THRESH_BINARY)
            thresh = cv2.dilate(thresh, None, iterations=2)
            contours, _ = cv2.findContours(
                thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
            if contours:
                largest = max(contours, key=cv2.contourArea)
                if cv2.contourArea(largest) >= self.min_area:
                    M = cv2.moments(largest)
                    if M['m00'] != 0:
                        self.prev_centroid = (M['m10'] / M['m00'], M['m01'] / M['m00'])
            return None

        diff = cv2.absdiff(self.prev_gray, gray)
        self.prev_gray = gray

        _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
        thresh = cv2.dilate(thresh, None, iterations=2)

        contours, _ = cv2.findContours(
            thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        if not contours:
            self.prev_centroid = None
            return None

        largest = max(contours, key=cv2.contourArea)
        if cv2.contourArea(largest) < self.min_area:
            self.prev_centroid = None
            return None

        M = cv2.moments(largest)
        if M['m00'] == 0:
            self.prev_centroid = None
            return None

        cx = M['m10'] / M['m00']
        cy = M['m01'] / M['m00']

        swipe = None
        if self.prev_centroid is not None:
            dx = cx - self.prev_centroid[0]
            dy = cy - self.prev_centroid[1]
            if np.hypot(dx, dy) >= self.velocity_threshold:
                swipe = {
                    'type': 'swipe',
                    'x1': round(self.prev_centroid[0] / self.frame_w, 4),
                    'y1': round(self.prev_centroid[1] / self.frame_h, 4),
                    'x2': round(cx / self.frame_w, 4),
                    'y2': round(cy / self.frame_h, 4),
                }

        self.prev_centroid = (cx, cy)
        return swipe
