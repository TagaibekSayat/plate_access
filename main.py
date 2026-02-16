import os
import cv2
import time
import threading
from threading import Lock
import argparse
from collections import Counter

from ai.yolo_plate import detect_plate_regions
from camera.capture import get_frame, cap
from ai.recognize import recognize_plate, assemble_plate_from_texts

from db.parking_repo import (
    is_inside,
    register_entry,
    register_exit,
    has_valid_payment
)

from db.plates_repo import log_access
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

BUFFER_SIZE = 7
UNLOCK_DELAY = 3


# ===================== INIT =====================

os.makedirs("admin/static", exist_ok=True)

latest_frame = None
frame_lock = Lock()

processed_plate_info = ""
plate_buffer = []

locked_plate = None
plate_last_seen = 0

barrier = BarrierController(min_open_time=10)

print(f"🚀 STARTED | CAMERA={CAMERA_INDEX} | TYPE={CAMERA_TYPE} | ZONE={ZONE_ID}")


def normalize_plate(plate: str) -> str:
    return plate.replace(" ", "").replace("-", "").replace("_", "").upper().strip()
    


def similar(a, b):
    if len(a) != len(b):
        return False
    diff = sum(1 for x, y in zip(a, b) if x != y)
    return diff <= 1


def is_universal_valid(plate):
    if not (5 <= len(plate) <= 10):
        return False
    if sum(c.isdigit() for c in plate) < 2:
        return False
    if sum(c.isalpha() for c in plate) < 1:
        return False
    return True



# ===================== AI THREAD =====================

def ai_recognition_thread():
    global latest_frame, processed_plate_info
    global locked_plate, plate_last_seen, plate_buffer

    while True:

        frame = None
        with frame_lock:
            if latest_frame is not None:
                frame = latest_frame.copy()

        if frame is None:
            time.sleep(0.05)
            continue

        plates = detect_plate_regions(frame)

        if not plates:
            # Егер номер көрінбей кетсе unlock тексереміз
            if locked_plate and time.time() - plate_last_seen > UNLOCK_DELAY:
                locked_plate = None
            time.sleep(0.05)
            continue

        detected_plate = None

        for plate_img in plates:
            texts = recognize_plate(plate_img)
            if not texts:
                continue

            plate = assemble_plate_from_texts(texts)
            if plate:
                detected_plate = normalize_plate(plate)
                break

        if not detected_plate:
            continue

        if not is_universal_valid(detected_plate):
             continue

        # ===== Majority vote =====
        plate_buffer.append(detected_plate)

        if len(plate_buffer) < BUFFER_SIZE:
            continue

        plate = Counter(plate_buffer).most_common(1)[0][0]
        plate_buffer.clear()

        now = time.time()

        # ===== LOCK SYSTEM =====
        if locked_plate:

            # Егер сол номер жалғасып тұрса — тек уақыт жаңартамыз
            if similar(plate, locked_plate):
                plate_last_seen = now
                continue

            # Егер басқа номер көрінді бірақ ескі әлі кетпеді
            if now - plate_last_seen < UNLOCK_DELAY:
               continue

            # Ескі номер толық жоғалды
            locked_plate = None
            plate_buffer.clear()

        # Жаңа номерді бекітеміз
        locked_plate = plate
        plate_last_seen = now
        plate_buffer.clear()


        # ================= ENTRY =================
        if CAMERA_TYPE == "ENTRY":

            if is_inside(plate):
                processed_plate_info = f"{plate} ALREADY INSIDE"
                log_access(plate, "DENIED", "ALREADY_INSIDE")
                continue

            register_entry(plate)

            if has_valid_payment(plate):
                barrier.open()
                processed_plate_info = f"{plate} ENTRY OK"
                log_access(plate, "GRANTED", "ENTRY_OK")
            else:
                processed_plate_info = f"{plate} ENTERED - NOT PAID"
                log_access(plate, "DENIED", "NO_PAYMENT")


        # ================= EXIT =================
        elif CAMERA_TYPE == "EXIT":

            if not is_inside(plate):
                barrier.open()
                processed_plate_info = f"{plate} FREE EXIT"
                log_access(plate, "GRANTED", "NO_SESSION")
                continue

            if has_valid_payment(plate):
                register_exit(plate)
                barrier.open()
                processed_plate_info = f"{plate} EXIT OK"
                log_access(plate, "GRANTED", "EXIT_OK")
            else:
                processed_plate_info = f"{plate} PAYMENT REQUIRED"
                log_access(plate, "DENIED", "EXIT_NO_PAYMENT")

        time.sleep(0.05)


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
            ok = "OK" in processed_plate_info
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
        cv2.imwrite("admin/static/live.jpg", web_view, [cv2.IMWRITE_JPEG_QUALITY, 65])

        cv2.imshow(f"PARKING {CAMERA_TYPE} ZONE {ZONE_ID}", web_view)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

finally:
    if cap:
        cap.release()
    cv2.destroyAllWindows()
