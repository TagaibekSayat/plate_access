import os
import cv2
import time
import threading
from threading import Lock
import argparse
from collections import Counter
from ai.yolo_plate import detect_plate_regions


# Жобаның ішкі модульдерінен импорттау
from camera.capture import get_frame, cap
from ai.recognize import recognize_plate, assemble_plate_from_texts
from db.parking_repo import (
    is_inside,
    register_entry,
    register_exit,
    has_valid_payment
)
from barrier.controller import BarrierController

# ===================== ARGUMENTS =====================
parser = argparse.ArgumentParser(description="Parking Camera Process")
parser.add_argument("--camera-index", type=int, required=True)
parser.add_argument("--camera-type", choices=["ENTRY", "EXIT"], required=True)
parser.add_argument("--zone-id", type=int, required=True)

args = parser.parse_args()

CAMERA_INDEX = args.camera_index
CAMERA_TYPE = args.camera_type
ZONE_ID = args.zone_id

PLATE_COOLDOWN = 5

# ===================== INIT =====================

os.makedirs("admin/static", exist_ok=True)

latest_frame = None
frame_lock = Lock()

processed_plate_info = ""
last_plate = None
last_plate_time = 0

# 🔥 Majority Vote буфері
plate_buffer = []
BUFFER_SIZE = 5

print(f"🚀 STARTED | CAMERA={CAMERA_INDEX} | TYPE={CAMERA_TYPE} | ZONE={ZONE_ID}")

barrier = BarrierController(min_open_time=10)

# ===================== AI RECOGNITION THREAD =====================

def ai_recognition_thread():
    global latest_frame, processed_plate_info, last_plate, last_plate_time, plate_buffer

    while True:
        with frame_lock:
            frame = None if latest_frame is None else latest_frame.copy()

        if frame is None:
            time.sleep(0.05)
            continue

        # 🔥 YOLO арқылы номер аймағын табу
        plates = detect_plate_regions(frame)

        if not plates:
            time.sleep(0.1)
            continue

        detected_plate = None

        # Әр табылған plate-ті OCR жасау
        for plate_img in plates:
            texts = recognize_plate(plate_img)

            if not texts:
                continue

            plate = assemble_plate_from_texts(texts)

            if plate:
                detected_plate = plate
                break

        if not detected_plate:
            continue

        # 🔥 Majority Vote
        plate_buffer.append(detected_plate)

        if len(plate_buffer) < BUFFER_SIZE:
            continue

        plate = Counter(plate_buffer).most_common(1)[0][0]
        plate_buffer.clear()

        now = time.time()

        # Cooldown тексеру
        if plate == last_plate and now - last_plate_time < PLATE_COOLDOWN:
            continue

        last_plate = plate
        last_plate_time = now

        # ================= ENTRY =================
        if CAMERA_TYPE == "ENTRY":

            if is_inside(plate):
                processed_plate_info = f"⚠️ ІШТЕ БАР: {plate}"
                print(f"[ENTRY] {plate} already inside")
                continue

            if has_valid_payment(plate):
                register_entry(plate)
                barrier.open()
                processed_plate_info = f"✅ КІРДІ: {plate}"
                print(f"[ENTRY] {plate} payment OK → opened")
            else:
                processed_plate_info = f"💰 ТӨЛЕМ КЕРЕК: {plate}"
                print(f"[ENTRY] {plate} payment required")

        # ================= EXIT =================
        elif CAMERA_TYPE == "EXIT":

            if not is_inside(plate):
                barrier.open()
                processed_plate_info = f"🚪 ШЫҒУ: {plate}"
                print(f"[EXIT] {plate} no session → opened")
                continue

            try:
                if has_valid_payment(plate):
                    barrier.open()
                    register_exit(plate)
                    processed_plate_info = f"🚪 ШЫҚТЫ: {plate}"
                    print(f"[EXIT] {plate} exit allowed")
                else:
                    processed_plate_info = f"⛔ ТӨЛЕМ ЖОҚ: {plate}"
                    print(f"[EXIT] {plate} payment required")
            except Exception as e:
                barrier.open()
                processed_plate_info = f"⚠️ FAIL-SAFE EXIT: {plate}"
                print(f"[EXIT] FAIL-SAFE for {plate}: {e}")

        time.sleep(0.1)



threading.Thread(target=ai_recognition_thread, daemon=True).start()

# ===================== MAIN LOOP =====================

try:
    while True:
        frame = get_frame(CAMERA_INDEX)
        if frame is None:
            continue

        with frame_lock:
            latest_frame = frame.copy()

        if processed_plate_info:
            ok = ("КІРДІ" in processed_plate_info or "ШЫҚТЫ" in processed_plate_info)
            color = (0, 255, 0) if ok else (0, 0, 255)

            cv2.putText(
                frame,
                processed_plate_info,
                (30, 60),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.1,
                color,
                3
            )

        web_view = cv2.resize(frame, (800, 450))
        cv2.imwrite(
            "admin/static/live.jpg",
            web_view,
            [cv2.IMWRITE_JPEG_QUALITY, 65]
        )

        cv2.imshow(f"PARKING {CAMERA_TYPE} ZONE {ZONE_ID}", web_view)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

finally:
    print("🔌 STOPPING CAMERA PROCESS...")
    if cap:
        cap.release()
    cv2.destroyAllWindows()
