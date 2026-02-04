import re

def filter_plate(texts):
    for text in texts:
        clean = text.upper().replace(" ", "").replace("-", "")

        # Watermark пен артық сөздер
        if clean in ["IVCAM", "CAM", "CAMERA"]:
            continue

        # Қазақстан номеріне ұқсас формат
        # мысал: 777ABC02, 01KZ777
        if re.match(r"^[A-Z0-9]{6,8}$", clean):
            return clean

    return None
