"""
Generate barcode markers compatible with AR.js matrixCodeType: 4x4_BCH_13_9_3
These are different from OpenCV DICT_4X4_50 — AR.js uses its own BCH encoding.
We download them directly from the AR.js marker generator.
"""
import urllib.request
import os

OUT_DIR = os.path.join(os.path.dirname(__file__), 'markers')
os.makedirs(OUT_DIR, exist_ok=True)

# AR.js barcode markers (4x4_BCH_13_9_3) — download from official generator
for i in range(5):
    url = f"https://github.com/nicktindall/cyclon.p2p-rtc-server/raw/master/public/markers/pattern-{i}.patt"
    # Use the AR.js marker image generator
    img_url = f"https://ar-js-org.github.io/AR.js/data/images/barcode/barcode_{i}.png"
    out = os.path.join(OUT_DIR, f"arjs_marker_{i}.png")
    try:
        urllib.request.urlretrieve(img_url, out)
        print(f"Downloaded marker {i} → {out}")
    except Exception as e:
        print(f"Failed to download marker {i}: {e}")

print("Done.")
