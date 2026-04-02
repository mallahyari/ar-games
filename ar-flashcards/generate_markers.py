"""Generate ArUco marker images using OpenCV — guaranteed to match detection."""
import cv2
import os

DICT = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
OUT_DIR = os.path.join(os.path.dirname(__file__), 'markers')
os.makedirs(OUT_DIR, exist_ok=True)

for i in range(5):
    marker = cv2.aruco.generateImageMarker(DICT, i, 400)
    # Add white border — ArUco detection requires white space around marker
    border = 60
    img = 255 * __import__('numpy').ones((400 + border*2, 400 + border*2), dtype='uint8')
    img[border:border+400, border:border+400] = marker
    path = os.path.join(OUT_DIR, f'marker_{i}.png')
    cv2.imwrite(path, img)
    print(f"Saved {path}")

print("Done — open markers.html to view them.")
