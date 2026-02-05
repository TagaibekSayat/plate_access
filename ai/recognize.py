import re
import easyocr
import cv2

reader = easyocr.Reader(['en'], gpu=False)


def assemble_plate_from_texts(texts):
    clean = [t.replace(" ", "").upper() for t in texts]

    for t in clean:
        fixed = fix_ocr_confusions(t)

        # ҰЗЫН формат
        if re.fullmatch(r"\d{3}[A-Z]{2,3}\d{2}", fixed):
            return fixed

    # ШАРШЫ формат
    region = number = letters = None

    for t in clean:
        t = fix_ocr_confusions(t)

        if t.isdigit() and len(t) == 3:
            region = t
        elif t.isdigit() and len(t) <= 2:
            number = t.zfill(2)
        elif t.isalpha() and 2 <= len(t) <= 3:
            letters = t

    if region and letters and number:
        return f"{region}{letters}{number}"

    return None




def fix_ocr_confusions(text: str):
    """
    OCR шатастыратын символдарды түзету
    """
    # цифр болуы тиіс жердегі әріптер
    DIGIT_FIX = {

    }

    # әріп болуы тиіс жердегі цифрлар
    LETTER_FIX = {
 
    }

    text = text.upper()
    chars = list(text)

    # 🔹 соңғы 2 символ — ЦИФР
    for i in range(len(chars)-2, len(chars)):
        if chars[i] in DIGIT_FIX:
            chars[i] = DIGIT_FIX[chars[i]]

    # 🔹 ортасындағы 2–3 символ — ӘРІП
    for i in range(3, len(chars)-2):
        if chars[i] in LETTER_FIX:
            chars[i] = LETTER_FIX[chars[i]]

    return "".join(chars)


def recognize_plate(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, None, fx=1.5, fy=1.5)
    gray = cv2.GaussianBlur(gray, (3,3), 0)

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

