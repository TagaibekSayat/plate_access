import re
import cv2
import easyocr

# EasyOCR моделін іске қосу (ағылшын тілі, GPU-сыз)
reader = easyocr.Reader(['en'], gpu=False)

# OCR шатастыратын символдарды түзету (мысалы: '0' орнына 'O')
DIGIT_FIX = {
    # Бұл жерге 'O': '0', 'I': '1' сияқты түзетулерді қосуға болады
}

LETTER_FIX = {
    # Бұл жерге '0': 'O', '1': 'I' сияқты түзетулерді қосуға болады
}


def fix_ocr_by_position(text: str) -> str:
    """Нөмірдегі символдардың орнына қарай қателерін түзейді"""
    text = text.upper()
    chars = list(text)

    for i, c in enumerate(chars):
        # Соңғы 2 таңба — цифр болуы керек (Қазақстан регионы сияқты)
        if i >= len(chars) - 2:
            if c in DIGIT_FIX:
                chars[i] = DIGIT_FIX[c]
        else:
            if c in LETTER_FIX:
                chars[i] = LETTER_FIX[c]

    return "".join(chars)



def assemble_plate_from_texts(texts):
    """Танылған мәтін кесектерін біртұтас нөмірге жинайды"""
    clean = [t.replace(" ", "").upper() for t in texts if t.upper() not in ("KZ", "RK")]

    # 1️⃣ Алдымен универсал номерді тексереміз (бір жолдағы нөмір)
    for t in clean:
        fixed = fix_ocr_by_position(t)
        # 4-тен 8 таңбаға дейінгі әріп-цифрлар, міндетті түрде цифр болуы керек
        if re.fullmatch(r"[A-Z0-9]{4,8}", fixed) and re.search(r"\d", fixed):
            return fixed

    # 2️⃣ Қазақстан квадрат номері (екі қатарлы нөмірді жинау)
    top = region = letters = None

    for t in clean:
        t = fix_ocr_by_position(t)

        if t.isdigit() and len(t) == 3:
            top = t
        elif t.isdigit() and len(t) <= 2:
            region = t.zfill(2)
        elif t.isalpha() and 2 <= len(t) <= 3:
            letters = t

    if top and letters and region:
        return f"{top}{letters}{region}"

    return None


def recognize_plate(frame):
    """Кескіннен (frame) нөмірді іздеп табады"""
    # Суретті өңдеу: сұр түске айналдыру, үлкейту, бұлдырату (шуды азайту)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, None, fx=1.6, fy=1.6)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)

    # OCR арқылы мәтінді оқу
    results = reader.readtext(
        gray,
        allowlist="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", # Тек осы таңбаларды таниды
        detail=0
    )

    texts = []

    for text in results:
        t = text.strip().upper()

        # Мағынасыз символдарды сүзу
        if not re.search(r"[A-Z0-9]", t):
            continue

        # Ұзындығы бойынша сүзу
        if len(t) < 2 or len(t) > 8:
            continue

        # Артық сөздерді алып тастау
        if t in ("KZ", "RK"):
            continue

        texts.append(t)

    return texts