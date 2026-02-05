import cv2
import time
import os
import threading

from camera.capture import get_frame, cap
from ai.recognize import recognize_plate, assemble_plate_from_texts
from db.plates_repo import is_allowed, log_access
from barrier.controller import BarrierController

# ===================== INIT =====================

os.makedirs("admin/static", exist_ok=True)

latest_frame = None
processed_plate_info = ""
last_seen_time = 0

print("🚀 OCR + DB MODE started")

barrier = BarrierController(min_open_time=10)

# ===================== AI THREAD =====================

def ai_recognition_thread():
    global latest_frame, processed_plate_info, last_seen_time

    while True:
        if latest_frame is None:
            time.sleep(0.05)
            continue

        small_frame = cv2.resize(latest_frame, (480, 320))

        # 1️⃣ OCR
        texts = recognize_plate(small_frame)
        if not texts:
            time.sleep(0.1)
            continue

        # 2️⃣ НОМЕР ҚҰРАСТЫРУ (ПРОБЕЛСІЗ)
        plate = assemble_plate_from_texts(texts)

        if plate:
            last_seen_time = time.time()

            # 3️⃣ БАЗАМЕН САЛЫСТЫРУ
            if is_allowed(plate):
                barrier.open()
                log_access(plate, "GRANTED", "ALLOWED")
                processed_plate_info = f"ALLOWED: {plate}"
            else:
                log_access(plate, "DENIED", "NOT_IN_DB")
                processed_plate_info = f"DENIED: {plate}"

        else:
            if time.time() - last_seen_time > 2:
                processed_plate_info = ""

        time.sleep(0.1)


# ===================== START THREAD =====================

thread = threading.Thread(
    target=ai_recognition_thread,
    daemon=True
)
thread.start()

# ===================== MAIN LOOP =====================

try:
    while True:
        frame = get_frame()
        if frame is None:
            continue

        latest_frame = frame.copy()

        # overlay
        if processed_plate_info:
            color = (0, 255, 0) if "ALLOWED" in processed_plate_info else (0, 0, 255)
            cv2.putText(
                frame,
                processed_plate_info,
                (30, 60),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.2,
                color,
                3
            )

        web_view = cv2.resize(frame, (800, 450))
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 65]
        cv2.imwrite("admin/static/live_temp.jpg", web_view, encode_param)

        try:
            os.replace("admin/static/live_temp.jpg", "admin/static/live.jpg")
        except:
            pass

        cv2.imshow("OCR + DB LIVE", web_view)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

finally:
    print("🔌 Stopping system...")
    if cap is not None:
        cap.release()
    cv2.destroyAllWindows()
