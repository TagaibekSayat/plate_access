import os
import sys

# МАҢЫЗДЫ: Мұны ең басына, cv2 импортталмай тұрып қою керек!
os.environ["OPENCV_LOG_LEVEL"] = "OFF"
os.environ["OPENCV_VIDEOIO_PRIORITY_MSMF"] = "0"

import cv2
import time

cap = None

def init_camera():
    global cap
    try:
        if cap is not None:
            cap.release()
            cap = None
    except:
        pass

    target_index = 1 
    # Біз тек өзіміздің хабарламаны шығарамыз, ал OpenCV қателері OFF болды
    print(f"🔍 iVCam ізделуде (Индекс {target_index})...")
    
    try:
        # CAP_DSHOW қолдану арқылы obsensor және ffmpeg қателерін азайтамыз
        new_cap = cv2.VideoCapture(target_index, cv2.CAP_DSHOW)
        
        if new_cap.isOpened():
            time.sleep(0.5)
            ret, frame = new_cap.read()
            
            if ret and frame is not None:
                print(f"✅ iVCam қосылды!")
                new_cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                new_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                return new_cap
            else:
                new_cap.release()
    except Exception:
        pass # Қатені үнсіз өткізу
    
    return None

def get_frame():
    global cap
    try:
        if cap is None or not cap.isOpened():
            cap = init_camera()
            if cap is None:
                time.sleep(2)
                return None

        ret, frame = cap.read()
        
        if not ret or frame is None:
            print("⚠️ iVCam-мен байланыс үзілді...")
            if cap:
                try: cap.release()
                except: pass
            cap = None
            return None

        return frame

    except Exception:
        # Кез келген оқу қатесі кезінде терминалды толтырмаймыз
        cap = None
        return None