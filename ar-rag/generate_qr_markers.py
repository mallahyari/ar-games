"""Generate QR code markers — one per flashcard."""
import qrcode
import os

OUT_DIR = os.path.join(os.path.dirname(__file__), 'markers')
os.makedirs(OUT_DIR, exist_ok=True)

for i in range(5):
    qr = qrcode.QRCode(box_size=20, border=4, error_correction=qrcode.constants.ERROR_CORRECT_H)
    qr.add_data(f"flashcard:{i}")
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    path = os.path.join(OUT_DIR, f"qr_{i}.png")
    img.save(path)
    print(f"Saved {path}")

print("Done.")
