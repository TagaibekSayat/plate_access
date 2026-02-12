# import cv2

# def detect_plate_regions(frame):
#     plates = []

#     gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
#     gray = cv2.bilateralFilter(gray, 11, 17, 17)

#     edged = cv2.Canny(gray, 50, 150)

#     contours, _ = cv2.findContours(
#         edged.copy(),
#         cv2.RETR_EXTERNAL,   # тек сыртқы контур
#         cv2.CHAIN_APPROX_SIMPLE
#     )

#     for cnt in contours:
#         area = cv2.contourArea(cnt)

#         # тым кішкентай немесе тым үлкендерді алып тастау
#         if area < 2000 or area > 50000:
#             continue

#         x, y, w, h = cv2.boundingRect(cnt)

#         aspect_ratio = w / float(h)

#         # Нақты номер пропорциясы
#         if 2.5 <= aspect_ratio <= 5.5:

#             # Минималды өлшем
#             if w > 120 and h > 30:

#                 # ROI-ны аздап кеңейтеміз
#                 pad = 5
#                 x1 = max(0, x - pad)
#                 y1 = max(0, y - pad)
#                 x2 = min(frame.shape[1], x + w + pad)
#                 y2 = min(frame.shape[0], y + h + pad)

#                 plate = frame[y1:y2, x1:x2]
#                 plates.append(plate)

#     return plates
