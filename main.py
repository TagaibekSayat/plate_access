import os
import cv2
import time
import threading
from threading import Lock
import argparse

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
# Программаны іске қосқанда параметрлерді қабылдау (мысалы: --camera-type ENTRY)
parser = argparse.ArgumentParser(description="Parking Camera Process")
parser.add_argument("--camera-index", type=int, required=True)
parser.add_argument("--camera-type", choices=["ENTRY", "EXIT"], required=True)
parser.add_argument("--zone-id", type=int, required=True)

args = parser.parse_args()

CAMERA_INDEX = args.camera_index
CAMERA_TYPE = args.camera_type
ZONE_ID = args.zone_id

PLATE_COOLDOWN = 5  # Бір номерді қайта тану арасындағы үзіліс (секунд)

# ===================== INIT =====================

# Веб-интерфейс үшін кадр сақтайтын папканы құру
os.makedirs("admin/static", exist_ok=True)

latest_frame = None
frame_lock = Lock()  # Ағындар арасында кадрды қауіпсіз алмасу үшін

processed_plate_info = ""
last_plate = None
last_plate_time = 0

print(f"🚀 STARTED | CAMERA={CAMERA_INDEX} | TYPE={CAMERA_TYPE} | ZONE={ZONE_ID}")

barrier = BarrierController(min_open_time=10)

# ===================== AI RECOGNITION THREAD =====================

def ai_recognition_thread():
    """Нөмірді тану және логиканы өңдеу ағыны"""
    global latest_frame, processed_plate_info, last_plate, last_plate_time

    while True:
        # Кадрды негізгі ағыннан көшіріп алу
        with frame_lock:
            frame = None if latest_frame is None else latest_frame.copy()

        if frame is None:
            time.sleep(0.05)
            continue

        # Оптимизация: тану жылдамдығы үшін кадр өлшемін кішірейту
        small = cv2.resize(frame, (480, 320))
        texts = recognize_plate(small)

        if not texts:
            time.sleep(0.1)
            continue

        plate = assemble_plate_from_texts(texts)
        now = time.time()

        if not plate:
            continue

        # Cooldown тексеру: бір көлікті қайта-қайта өңдемеу үшін
        if plate == last_plate and now - last_plate_time < PLATE_COOLDOWN:
            continue

        last_plate = plate
        last_plate_time = now

        # --- КІРУ ЛОГИКАСЫ ---
        if CAMERA_TYPE == "ENTRY":
            if is_inside(plate):
                processed_plate_info = f"⚠️ ІШТЕ БАР: {plate}"
                print(f"[ENTRY] {plate} already inside")
                continue

            register_entry(plate)
            processed_plate_info = f"💰 ТӨЛЕМ КЕРЕК: {plate}"
            print(f"[ENTRY] {plate} waiting for payment")

            # Төлемді 60 секунд бойы күту
            wait_start = time.time()
            while time.time() - wait_start < 60:
                if has_valid_payment(plate):
                    barrier.open()
                    processed_plate_info = f"✅ КІРДІ: {plate}"
                    print(f"[ENTRY] {plate} payment OK → opened")
                    break
                time.sleep(1)

        # --- ШЫҒУ ЛОГИКАСЫ ---
        elif CAMERA_TYPE == "EXIT":
            if not is_inside(plate):
                barrier.open()  # Тіркелмеген көліктерді де шығару (Fail-safe)
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
                # Қандай да бір қате кетсе, шлагбаумды ашу (көлік тұрып қалмауы үшін)
                barrier.open()
                processed_plate_info = f"⚠️ FAIL-SAFE EXIT: {plate}"
                print(f"[EXIT] FAIL-SAFE for {plate}: {e}")

        time.sleep(0.2)

# AI ағынын фондық режимде іске қосу
threading.Thread(target=ai_recognition_thread, daemon=True).start()

# ===================== MAIN LOOP (DISPLAY & CAPTURE) =====================

try:
    while True:
        frame = get_frame(CAMERA_INDEX)
        if frame is None:
            continue

        # Кадрды AI ағыны көру үшін сақтау
        with frame_lock:
            latest_frame = frame.copy()

        # Экранға ақпаратты шығару (Кірді/Шықты)
        if processed_plate_info:
            ok = ("КІРДІ" in processed_plate_info or "ШЫҚТЫ" in processed_plate_info)
            color = (0, 255, 0) if ok else (0, 0, 255) # Жасыл немесе Қызыл

            cv2.putText(
                frame,
                processed_plate_info,
                (30, 60),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.1,
                color,
                3
            )

        # Веб-мониторинг үшін кадрды JPEG ретінде сақтау
        web_view = cv2.resize(frame, (800, 450))
        cv2.imwrite(
            "admin/static/live.jpg",
            web_view,
            [cv2.IMWRITE_JPEG_QUALITY, 65]
        )

        # Терезеде көрсету
        cv2.imshow(f"PARKING {CAMERA_TYPE} ZONE {ZONE_ID}", web_view)

        # 'q' басылса тоқтату
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

finally:
    print("🔌 STOPPING CAMERA PROCESS...")
    if cap:
        cap.release()
    cv2.destroyAllWindows()