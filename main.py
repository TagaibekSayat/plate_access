import os
import cv2
import time
import threading
from threading import Lock
import argparse
from collections import Counter
import re

from ai.yolo_plate import detect_plate_regions
from camera.capture import get_frame, cap
from ai.recognize import recognize_plate, assemble_plate_from_texts
from ai.plate_patterns import PLATE_PATTERNS

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
latest_plate_bbox = None
latest_plate_text = ""

locked_plate = None
plate_last_seen = 0

barrier = BarrierController(min_open_time=10)

print(f"🚀 STARTED | CAMERA={CAMERA_INDEX} | TYPE={CAMERA_TYPE} | ZONE={ZONE_ID}")


# ===================== NORMALIZE =====================

def normalize_plate(plate: str) -> str:
    plate = plate.replace(" ", "").replace("-", "").replace("_", "").upper().strip()

    if plate.startswith("KZ"):
        plate = plate[2:]

    for code in ["RUS", "UZ", "KG", "BY", "AM"]:
        if plate.endswith(code):
            plate = plate[:-len(code)]

    return plate

# def extract_real_plate(text: str):

#     text = text.upper()

#     patterns = [
#         r'[A-Z]\d{3}[A-Z]{2}\d{2,3}',   # RU
#         r'\d{3}[A-Z]{2,3}\d{2}',       # KZ NEW
#         r'[A-Z]\d{3}[A-Z]{2}',         # KZ OLD
#     ]

#     for pattern in patterns:
#         matches = re.findall(pattern, text)
#         if matches:
#             # Ең ұзын match аламыз
#             return max(matches, key=len)

#     return None



# ===================== SMART SYMBOL FIX =====================

REPLACE_MAP = {
    "O": "0",
    "I": "1",
    "Z": "2",
    "S": "5",
    "B": "8",
}

def smart_fix(plate):
    return "".join(REPLACE_MAP.get(c, c) for c in plate)


# ===================== KZ LOGIC =====================

def is_kz_plate_loose(plate):
    if len(plate) < 6 or len(plate) > 8:
        return False

    digits = sum(c.isdigit() for c in plate)
    letters = sum(c.isalpha() for c in plate)

    return digits >= 4 and letters >= 2


def is_kz_plate_strict(plate: str) -> bool:
    return bool(
        re.fullmatch(PLATE_PATTERNS["KZ_NEW_3L"], plate)
        or re.fullmatch(PLATE_PATTERNS["KZ_NEW_2L"], plate)
        or re.fullmatch(PLATE_PATTERNS["KZ_OLD"], plate)
    )


def _digit_like(c: str) -> str:
    return {
        "O": "0",
        "I": "1",
        "L": "1",
        "Z": "2",
        "S": "5",
        "B": "8",
    }.get(c, c)


def _letter_like(c: str) -> str:
    return {
        "0": "O",
        "1": "I",
        "2": "Z",
        "4": "A",
        "5": "S",
        "6": "G",
        "8": "B",
    }.get(c, c)


def kz_force_candidate(plate: str) -> str | None:
    # Frequent OCR split issue: thin separator inside plate is read as '1'
    # Example: 888AVA04 -> 8884V4104 or 888AVA104.
    compact = plate.replace(" ", "").replace("-", "")
    candidates = [compact]

    if len(compact) == 9:
        candidates.append(compact[:6] + compact[7:])

    for cand in candidates:
        if len(cand) == 8:
            chars = list(cand)
            for i in range(3):
                chars[i] = _digit_like(chars[i])
            for i in range(3, 6):
                chars[i] = _letter_like(chars[i])
            for i in range(6, 8):
                chars[i] = _digit_like(chars[i])
            fixed = "".join(chars)
            if is_kz_plate_strict(fixed):
                return fixed

        if len(cand) == 7:
            chars = list(cand)
            for i in range(3):
                chars[i] = _digit_like(chars[i])
            for i in range(3, 5):
                chars[i] = _letter_like(chars[i])
            for i in range(5, 7):
                chars[i] = _digit_like(chars[i])
            fixed = "".join(chars)
            if is_kz_plate_strict(fixed):
                return fixed

        if len(cand) == 6:
            chars = list(cand)
            chars[0] = _letter_like(chars[0])
            for i in range(1, 4):
                chars[i] = _digit_like(chars[i])
            for i in range(4, 6):
                chars[i] = _letter_like(chars[i])
            fixed = "".join(chars)
            if is_kz_plate_strict(fixed):
                return fixed

    return None


def kz_position_fix(plate):

    if len(plate) < 6:
        return plate

    chars = list(plate)

    # 1-3 цифр
    for i in range(min(3, len(chars))):
        if chars[i] in ["O", "I"]:
            chars[i] = REPLACE_MAP.get(chars[i], chars[i])

    # 4-6 әріп
    for i in range(3, min(6, len(chars))):
        if chars[i] == "0":
            chars[i] = "O"
        if chars[i] == "1":
            chars[i] = "I"

    # регион цифр
    if len(chars) >= 8:
        for i in range(6, 8):
            if chars[i] in ["O", "I"]:
                chars[i] = REPLACE_MAP.get(chars[i], chars[i])

    return "".join(chars)


def is_universal_valid(plate):
    if not (5 <= len(plate) <= 10):
        return False
    if sum(c.isdigit() for c in plate) < 2:
        return False
    if sum(c.isalpha() for c in plate) < 1:
        return False
    return True


# ===================== SIMILAR CHECK =====================

SIMILAR_GROUPS = [
    set("0O"),
    set("1I"),
    set("2Z"),
    set("4A"),
    set("5S"),
    set("6G"),
    set("8B"),
]

def is_visually_similar(a, b):
    if a == b:
        return True
    for group in SIMILAR_GROUPS:
        if a in group and b in group:
            return True
    return False


def similar(a, b):
    if len(a) != len(b):
        return False

    diff = 0
    for x, y in zip(a, b):
        if not is_visually_similar(x, y):
            diff += 1

    return diff <= 1


# ===================== AI THREAD =====================

def ai_recognition_thread():
    global latest_frame, processed_plate_info
    global locked_plate, plate_last_seen, plate_buffer
    global latest_plate_bbox, latest_plate_text

    while True:

        frame = None
        with frame_lock:
            if latest_frame is not None:
                frame = latest_frame.copy()

        if frame is None:
            time.sleep(0.03)
            continue

        detections = detect_plate_regions(frame, return_boxes=True)

        if not detections:
            if locked_plate and time.time() - plate_last_seen > UNLOCK_DELAY:
                locked_plate = None
                latest_plate_bbox = None
                latest_plate_text = ""
            time.sleep(0.03)
            continue

        detected_plate = None
        detected_bbox = None

        for plate_img, bbox in detections:

            # 🔥 OCR алдында upscale
            plate_img = cv2.resize(
                plate_img,
                None,
                fx=2,
                fy=2,
                interpolation=cv2.INTER_CUBIC
            )

            texts = recognize_plate(plate_img)
            if not texts:
                continue

            plate = assemble_plate_from_texts(texts)
            if not plate:
                continue

            plate = normalize_plate(plate)
            plate = smart_fix(plate)
            plate = kz_position_fix(plate)

            kz_forced = kz_force_candidate(plate)
            if kz_forced:
                plate = kz_forced
                detected_plate = plate
                detected_bbox = bbox
                break

            if is_kz_plate_loose(plate):
                detected_plate = plate
                detected_bbox = bbox
                break

            if is_universal_valid(plate):
                detected_plate = plate
                detected_bbox = bbox
                break

        if not detected_plate:
            continue

        plate_buffer.append(detected_plate)

        if len(plate_buffer) < BUFFER_SIZE:
            continue

        plate = Counter(plate_buffer).most_common(1)[0][0]
        plate_buffer.clear()

        now = time.time()

        if locked_plate:
            if similar(plate, locked_plate):
                plate_last_seen = now
                continue

            if now - plate_last_seen < UNLOCK_DELAY:
                continue

            locked_plate = None

        locked_plate = plate
        plate_last_seen = now
        latest_plate_bbox = detected_bbox
        latest_plate_text = plate


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

        time.sleep(0.03)


threading.Thread(target=ai_recognition_thread, daemon=True).start()


# ===================== MAIN LOOP =====================

try:
    while True:

        frame = get_frame(CAMERA_INDEX)
        if frame is None:
            continue

        with frame_lock:
            latest_frame = frame.copy()

        if latest_plate_bbox:
            x1, y1, x2, y2 = latest_plate_bbox
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
            if latest_plate_text:
                cv2.putText(
                    frame,
                    latest_plate_text,
                    (x1, max(25, y1 - 10)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.85,
                    (46, 204, 113),
                    2,
                    cv2.LINE_AA
                )

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

        h, w = frame.shape[:2]
        target_w = min(w, 1280)
        target_h = int(h * (target_w / w))
        web_view = cv2.resize(frame, (target_w, target_h), interpolation=cv2.INTER_AREA)
        cv2.imwrite("admin/static/live.jpg", web_view, [cv2.IMWRITE_JPEG_QUALITY, 90])

        cv2.imshow(f"PARKING {CAMERA_TYPE} ZONE {ZONE_ID}", web_view)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

finally:
    if cap:
        cap.release()
    cv2.destroyAllWindows()
