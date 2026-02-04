import cv2

def detect_plate_regions(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.bilateralFilter(gray, 11, 17, 17)

    edges = cv2.Canny(gray, 50, 200)

    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    plates = []

    for cnt in contours:
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.03 * peri, True)

        if len(approx) == 4:
            x, y, w, h = cv2.boundingRect(approx)
            ratio = w / float(h)

            if 2.2 < ratio < 5.5 and w > 120 and h > 35:
                plate = frame[y:y+h, x:x+w]

                # OCR-ға дайындау
                plate_gray = cv2.cvtColor(plate, cv2.COLOR_BGR2GRAY)
                plate_gray = cv2.resize(plate_gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
                _, plate_bin = cv2.threshold(
                    plate_gray, 0, 255,
                    cv2.THRESH_BINARY + cv2.THRESH_OTSU
                )

                plates.append(plate_bin)

    return plates
