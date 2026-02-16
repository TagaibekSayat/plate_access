import re
import cv2
import easyocr

# ================= OCR INIT =================

reader = easyocr.Reader(['en'], gpu=False)

# ================= OCR FIX =================

COUNTRY_CODES = {
    "KZ", "RK",
    "RUS", "RU",
    "UZ",
    "CN",
    "KG",
    "BY",
    "AM"
}

DIGIT_FIX = {

}

LETTER_FIX = {

}


def fix_common_ocr(text: str) -> str:
    text = text.upper()
    fixed = ""

    for c in text:
        if c in DIGIT_FIX:
            fixed += DIGIT_FIX[c]
        else:
            fixed += c

    return fixed



def is_valid_plate(text):
    if not (5 <= len(text) <= 10):
        return False

    digits = sum(c.isdigit() for c in text)
    letters = sum(c.isalpha() for c in text)

    if digits < 2:
        return False

    if letters == 0:
        return False

    return True

# ================= ASSEMBLE =================

def assemble_plate_from_texts(texts):
    if not texts:
        return None

    parts = []

    for t in texts:
        t = re.sub(r'[^A-Z0-9]', '', t.upper())

        if len(t) >= 2:
            parts.append(t)

    if not parts:
        return None

    candidate = "".join(parts)

    # 🔥 Егер басында ел коды болса (2 әріп), бірақ кейін сан келсе — алып тастаймыз
    if len(candidate) > 6 and candidate[:2].isalpha() and candidate[2].isdigit():
        candidate = candidate[2:]

    return candidate



# ================= RECOGNIZE =================

def recognize_plate(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Контраст күшейту
    gray = cv2.equalizeHist(gray)

    # Шум азайту
    gray = cv2.GaussianBlur(gray, (5, 5), 0)

    # Threshold
    thresh = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        15,
        5
    )

    # Морфология – жіңішке сызықтарды жою
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    cleaned = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

    # Кішкентай шумдарды алып тастау
    cleaned = cv2.medianBlur(cleaned, 3)

    # EasyOCR
    results = reader.readtext(cleaned, detail=0)

    return results
