import re
import cv2
import easyocr

reader = easyocr.Reader(['en'], gpu=False)

# OCR шатастыратын символдарды түзету
DIGIT_FIX = {
   
}

LETTER_FIX = {

}


def fix_ocr(text: str) -> str:
    return "".join(DIGIT_FIX.get(c, c) for c in text)


# ===================== НОМЕР ҚҰРАСТЫРУ =====================

def assemble_plate_from_texts(texts):
    clean = [t.replace(" ", "").upper() for t in texts if t.upper() != "KZ"]

    # 🔹 1) ҰЗЫН номер (бір қатар)
    for t in clean:
        t = fix_ocr(t)
        if re.fullmatch(r"\d{3}[A-Z]{2,3}\d{2}", t):
            return t

    # 🔹 2) ШАРШЫ номер (екі қатар)
    top = None       # 3 сан
    region = None    # 2 сан
    letters = None   # 2–3 әріп

    for t in clean:
        t = fix_ocr(t)

        if t.isdigit() and len(t) == 3:
            top = t
        elif t.isdigit() and len(t) <= 2:
            region = t.zfill(2)
        elif t.isalpha() and 2 <= len(t) <= 3:
            letters = t

    if top and letters and region:
        return f"{top}{letters}{region}"

    return None


# ===================== OCR =====================

def recognize_plate(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, None, fx=1.6, fy=1.6)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)

    results = reader.readtext(
        gray,
        allowlist="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
        detail=0
    )

    texts = []
    for text in results:
        t = text.strip().upper()
        if t and t != "KZ":
            texts.append(t)

    return texts
