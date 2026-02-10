import cv2

def detect_plate_regions(frame):
    # 1. Түсті сұрға айналдыру және шуды басу
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    # bilateralFilter жиектерді сақтай отырып, шуды жақсы тазалайды
    gray = cv2.bilateralFilter(gray, 11, 17, 17)

    # 2. Жиектерді анықтау (Canny Edge Detection)
    edges = cv2.Canny(gray, 50, 200)
    
    # 3. Контурларды іздеу
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    # Ең үлкен 10 контурды ғана аламыз (нөмір кішкентай болмауы керек)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:10]

    plates = []

    for cnt in contours:
        # Контурды жақындату (approximation)
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.03 * peri, True)

        # 4. Төртбұрыш па? (Нөмір пішіні төртбұрыш болуы керек)
        if len(approx) != 4:
            continue

        x, y, w, h = cv2.boundingRect(approx)
        ratio = w / float(h) # Ені мен биіктігінің қатынасы
        area = w * h         # Ауданы

        # 5. Нөмірдің стандартты пропорцияларын тексеру (мысалы, 520мм x 112мм)
        # Қазақстандық нөмірлер үшін ені биіктігінен 2.5-5.0 есе үлкен болуы керек
        if not (2.5 < ratio < 5.0 and area > 5000):
            continue

        # 6. Нөмірді кесіп алу
        plate = frame[y:y+h, x:x+w]

        # 7. OCR-ға дайындау (Бинаризация)
        plate_gray = cv2.cvtColor(plate, cv2.COLOR_BGR2GRAY)
        # Кескінді 2 есе үлкейту (OCR жақсырақ оқуы үшін)
        plate_gray = cv2.resize(
            plate_gray, None, fx=2, fy=2,
            interpolation=cv2.INTER_CUBIC
        )

        # Otsu әдісі арқылы ақ-қара түске айналдыру
        _, plate_bin = cv2.threshold(
            plate_gray, 0, 255,
            cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )

        plates.append(plate_bin)

    return plates