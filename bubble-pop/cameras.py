"""Shared camera utilities: detect available cameras and prompt user to pick one."""
import cv2


def list_cameras(max_index=8):
    """Return list of (index, width, height) for every camera that opens."""
    found = []
    for i in range(max_index):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            found.append((i, w, h))
        cap.release()
    return found


def pick_camera():
    """
    Print available cameras and prompt the user to choose one.
    Returns the chosen camera index.
    Exits with an error message if no cameras are found.
    """
    cameras = list_cameras()

    if not cameras:
        print("ERROR: No cameras found.")
        raise SystemExit(1)

    if len(cameras) == 1:
        idx, w, h = cameras[0]
        print(f"Using camera {idx} ({w}x{h})")
        return idx

    print("Available cameras:")
    for idx, w, h in cameras:
        print(f"  [{idx}] {w}x{h}")

    while True:
        raw = input(f"Choose camera [{cameras[0][0]}–{cameras[-1][0]}]: ").strip()
        if raw == "":
            return cameras[0][0]
        if raw.isdigit() and int(raw) in [c[0] for c in cameras]:
            return int(raw)
        print(f"  Invalid choice — enter one of: {[c[0] for c in cameras]}")
