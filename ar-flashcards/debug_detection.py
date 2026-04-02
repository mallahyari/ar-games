"""Debug: try to detect ArUco markers in a saved image or live camera frame."""
import cv2
import sys
import os

DICT = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
PARAMS = cv2.aruco.DetectorParameters()
DETECTOR = cv2.aruco.ArucoDetector(DICT, PARAMS)

# First test: detect in the generated marker images themselves
print("=== Testing detection on generated marker images ===")
for i in range(5):
    path = f"ar-flashcards/markers/marker_{i}.png"
    img = cv2.imread(path)
    if img is None:
        print(f"  marker_{i}.png not found")
        continue
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    corners, ids, rejected = DETECTOR.detectMarkers(gray)
    if ids is not None:
        print(f"  marker_{i}.png → detected ID(s): {ids.flatten().tolist()} ✓")
    else:
        print(f"  marker_{i}.png → NOT detected (rejected={len(rejected)})")

# Second test: live camera — save a frame and try detection
print("\n=== Testing live camera detection ===")
print("Opening camera 0... (change index if needed)")
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Cannot open camera")
    sys.exit(1)

print("Hold marker in front of camera. Press SPACE to capture, Q to quit.")
while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.flip(frame, 1)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    corners, ids, rejected = DETECTOR.detectMarkers(gray)

    display = frame.copy()
    if ids is not None:
        cv2.aruco.drawDetectedMarkers(display, corners, ids)
        print(f"DETECTED: {ids.flatten().tolist()}")
    else:
        cv2.putText(display, f"No markers (rejected candidates: {len(rejected)})",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

    cv2.imshow("Debug Detection (SPACE=save frame, Q=quit)", display)
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    elif key == ord(' '):
        path = "/tmp/debug_frame.jpg"
        cv2.imwrite(path, frame)
        print(f"Saved frame to {path}")
        print(f"  Gray stats: min={gray.min()} max={gray.max()} mean={gray.mean():.1f}")
        print(f"  Rejected candidates: {len(rejected)}")

cap.release()
cv2.destroyAllWindows()
