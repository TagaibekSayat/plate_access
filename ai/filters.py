import re

# Қазақстандық және жалпы нөмір стандарттарының шаблондары
PLATE_PATTERNS = [
    r"^\d{3}[A-Z]{3}\d{2}$",   # Жаңа формат: 777UUU10 (3 сан, 3 әріп, 2 сан)
    r"^[A-Z]{3}\d{3}$",        # Ескі формат немесе шетелдік: ABC123
    r"^\d{3}[A-Z]{3}$"         # Тағы бір формат: 123ABC
]

# Камера интерфейсінен келуі мүмкін қате сөздерді өткізбеу
BLACKLIST = {"IVCAM", "CAM", "CAMERA"}

def filter_plate(texts):
    candidates = []

    for text in texts:
        # Мәтінді тазалау: бос орындар мен дефистерді алып тастау
        clean = text.upper().replace(" ", "").replace("-", "")

        # Егер мәтін қара тізімде болса, оны аттап өтеміз
        if clean in BLACKLIST:
            continue

        # Әрбір шаблонмен тексеру
        for pattern in PLATE_PATTERNS:
            if re.match(pattern, clean):
                candidates.append(clean)

    # Егер бірнеше нұсқа табылса, ең ұзынын таңдаймыз (ол толық нөмір болуы ықтимал)
    if candidates:
        return max(candidates, key=len)

    return None