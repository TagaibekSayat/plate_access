import easyocr
import cv2

reader = easyocr.Reader(['en'], gpu=False)

BLOCKED_WORDS = {
    "IVCAM", "CAM", "CAMERA", "IPCAM",
    "HTTP", "HTTPS", "WWW"
}

def recognize_plate(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, None, fx=1.5, fy=1.5)
    gray = cv2.GaussianBlur(gray, (5,5), 0)

    results = reader.readtext(
        gray,
        allowlist="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
        detail=0
    )

    texts = []
    for text in results:
        t = text.replace(" ", "").upper()

        # ❌ watermark-тарды өткізбеу
        if t in BLOCKED_WORDS:
            continue

        # номерге ұқсас ұзындық
        if 5 <= len(t) <= 8:
            texts.append(t)

    return texts
