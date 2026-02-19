import re
import cv2
import easyocr
import torch

# ================= OCR INIT =================

reader = easyocr.Reader(['en','ru'], gpu=True)
print("Cuda available:", torch.cuda.is_available())

if torch.cuda.is_available():
    print("Current device:",torch.cuda.current_device())
    print("Device name:", torch.cuda.get_device_name(0))

# ================= SAFE OCR FIX =================

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


# ================= ASSEMBLE =================

def assemble_plate_from_texts(texts):

    if not texts:
        return None

    candidate = ""

    for t in texts:
        clean = re.sub(r'[^A-Z0-9]', '', t.upper())
        candidate += clean

    if len(candidate) < 6:
        return None

    return candidate


# ================= RECOGNIZE =================

def recognize_plate(img):

    # ---- Resize (агрессивный) ----
    h, w = img.shape[:2]
    if w < 400:
        scale = 400 / w
        img = cv2.resize(
            img,
            None,
            fx=scale,
            fy=scale,
            interpolation=cv2.INTER_CUBIC
        )

    # ---- Gray ----
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # ---- CLAHE (equalizeHist орнына) ----
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
    gray = clahe.apply(gray)

    # ---- Noise removal ----
    gray = cv2.bilateralFilter(gray, 9, 75, 75)

    # ---- Light sharpen ----
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2,2))
    gray = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)

    # ---- OCR ----
    results = reader.readtext(
        gray,
        allowlist="0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ",
        detail=1,
        paragraph=False,
        decoder='beamsearch'
    )

    texts = []

    for bbox, text, conf in results:

        if conf < 0.65:   # көтердік
            continue

        text = re.sub(r'[^A-Z0-9]', '', text.upper())

        if text:
            texts.append(text)

    return texts
