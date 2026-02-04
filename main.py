import cv2
import time
import os
import threading

from camera.capture import get_frame, cap 
from ai.recognize import recognize_plate
from ai.filters import filter_plate
from ai.stability import PlateStability
from db.plates_repo import is_allowed, log_access
from barrier.controller import BarrierController

os.makedirs("admin/static", exist_ok=True)

# Глобалдық айнымалылар
latest_frame = None
processed_plate_info = ""
last_seen_time = 0

print("🚀 Ultra-Fast Plate Access System started")

stability = PlateStability()
barrier = BarrierController(min_open_time=10)
CAR_LOST_TIMEOUT = 5

def ai_recognition_thread():
    """Нөмірді тануды жеке ағында (фонда) орындау"""
    global latest_frame, processed_plate_info, last_seen_time
    
    while True:
        if latest_frame is not None:
            # AI-ға арналған кадрды барынша кішірейту (жылдамдық үшін)
            small_frame = cv2.resize(latest_frame, (480, 320))
            
            texts = recognize_plate(small_frame)
            plate = filter_plate(texts)
            
            if plate:
                stable_plate = stability.update(plate)
                if stable_plate:
                    last_seen_time = time.time()
                    if is_allowed(stable_plate):
                        barrier.open()
                        log_access(stable_plate, "GRANTED", "ALLOWED")
                        processed_plate_info = f"ALLOWED: {stable_plate}"
                    else:
                        log_access(stable_plate, "DENIED", "NOT_IN_DB")
                        processed_plate_info = f"DENIED: {stable_plate}"
            else:
                # Егер 5 секунд бойы нөмір көрінбесе, жазуды өшіру
                if time.time() - last_seen_time > 2:
                    processed_plate_info = ""
        
        time.sleep(0.1)  # AI секундына 10 рет қана жұмыс істейді (CPU үнемдеу)

# AI ағынын іске қосу
thread = threading.Thread(target=ai_recognition_thread, daemon=True)
thread.start()



try:
    while True:
        frame = get_frame()
        if frame is None:
            continue

        # Соңғы кадрды AI ағынына беру
        latest_frame = frame.copy()

        # Шлагбаум логикасы
        car_present = (time.time() - last_seen_time < CAR_LOST_TIMEOUT)
        if barrier.can_close(car_present):
            barrier.close()

        # Экранға ақпаратты шығару
        if processed_plate_info:
            color = (0, 255, 0) if "ALLOWED" in processed_plate_info else (0, 0, 255)
            cv2.putText(frame, processed_plate_info, (30, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.2, color, 3)

        # Веб-панельге жылдам жазу
        web_view = cv2.resize(frame, (800, 450))
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 65]
        cv2.imwrite("admin/static/live_temp.jpg", web_view, encode_param)
        
        try:
            os.replace("admin/static/live_temp.jpg", "admin/static/live.jpg")
        except:
            pass

        # Тікелей экранда көрсету
        cv2.imshow("LIVE - NO LAG", web_view)
        
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

finally:
    print("🔌 Stopping system...")
    if 'cap' in globals() and cap is not None:
        cap.release()
    cv2.destroyAllWindows()