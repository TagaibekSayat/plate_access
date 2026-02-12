import re

BLACKLIST = {"IVCAM", "CAM", "CAMERA"}

def normalize_plate(text):
    if not text:
        return None

    # Үлкен әріпке ауыстыру
    text = text.upper()

    # Артық символдарды алып тастау (тек A-Z және 0-9 қалдырамыз)
    text = re.sub(r'[^A-Z0-9]', '', text)

    # Минималды ұзындық (тым қысқа болса қабылдамаймыз)
    if len(text) < 4:
        return None

    # Қара тізім тексеру
    if text in BLACKLIST:
        return None

    return text


def filter_plate(texts):
    candidates = []

    for text in texts:
        clean = normalize_plate(text)

        if clean:
            candidates.append(clean)

    if candidates:
        # ең ұзын вариантты аламыз
        return max(candidates, key=len)

    return None
