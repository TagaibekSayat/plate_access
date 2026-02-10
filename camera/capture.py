import os
import time
import cv2

# OpenCV-дің артық логтарын өшіру
os.environ["OPENCV_LOG_LEVEL"] = "OFF"
os.environ["OPENCV_VIDEOIO_PRIORITY_MSMF"] = "0"

cap = None

def init_camera(camera_index=1):
    """Камераны инициализациялау және баптау"""
    global cap
    
    # Егер ескі байланыс болса, оны жабу
    if cap is not None:
        try:
            cap.release()
        except:
            pass
        cap = None

    print(f"📷 Camera ізделуде (index={camera_index})...")

    try:
        # CAP_DSHOW Windows-та камераны жылдам іске қосу үшін керек
        new_cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)

        if new_cap.isOpened():
            # Камераның сенсоры дайындалуы үшін қысқа үзіліс
            time.sleep(0.6)
            ret, frame = new_cap.read()

            if ret and frame is not None:
                # Камера параметрлерін орнату
                new_cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                new_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                # Буферде ескі кадрлар тұрып қалмауы үшін (өте маңызды!)
                new_cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                
                print(f"✅ Camera {camera_index} сәтті қосылды")
                return new_cap
            else:
                new_cap.release()
    except Exception as e:
        print(f"❌ Camera error: {e}")

    return None


def get_frame(camera_index=1):
    """Кадрды алу. Егер камера өшіп қалса, қайта қосылуға тырысады"""
    global cap
    
    try:
        # 1. Егер cap нысаны жоқ болса немесе ашылмаса, қайта қосу
        if cap is None or not cap.isOpened():
            cap = init_camera(camera_index)
            if cap is None:
                return None

        # 2. Кадрды оқу
        ret, frame = cap.read()

        # 3. Егер кадр алынбаса (байланыс үзілсе)
        if not ret or frame is None:
            print(f"⚠️ Camera (index={camera_index}) байланысы үзілді, қайта қосылуда...")
            if cap is not None:
                cap.release()
            cap = None
            return None

        return frame

    except Exception as e:
        print(f"🚨 get_frame ішінде күтілмеген қате: {e}")
        cap = None
        return None

# Ресурстарды тазалау үшін функция (бағдарлама жабылғанда керек)
def release_camera():
    global cap
    if cap is not None:
        cap.release()
        cap = None
        print("🔌 Camera ресурстары босатылды.")