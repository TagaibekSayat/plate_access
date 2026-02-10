import os
import time
import cv2
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from db.connection import get_conn
from barrier.controller import BarrierController
from db.parking_repo import register_payment

app = FastAPI(title="Plate Access Control")

# ===================== STATIC & TEMPLATES =====================

app.mount("/static", StaticFiles(directory="admin/static"), name="static")
templates = Jinja2Templates(directory="admin/templates")

barrier = BarrierController()

# ===================== LIVE VIDEO =====================

def get_frames():
    frame_path = "admin/static/live.jpg"

    while True:
        if os.path.exists(frame_path):
            try:
                # Файлды тек оқу режимінде ашу (rb)
                with open(frame_path, "rb") as f:
                    frame_bytes = f.read()
                
                if not frame_bytes: # Егер файл бос болса (жазылып жатқан сәт)
                    time.sleep(0.01)
                    continue

                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" +
                    frame_bytes +
                    b"\r\n"
                )
            except Exception:
                # Кез келген қате болса (мысалы, файл басқа процесспен жабық болса)
                time.sleep(0.01)
                continue
        else:
            time.sleep(0.1)
        
        # FPS-ті бақылау (шамамен 25-30 кадр/сек)
        time.sleep(0.04)

@app.get("/video_feed")
def video_feed():
    return StreamingResponse(
        get_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

# ===================== DASHBOARD =====================

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    try:
        conn = get_conn()
        cur = conn.cursor()

        cur.execute("""
            SELECT plate, status, created_at
            FROM access_logs
            ORDER BY created_at DESC
            LIMIT 20
        """)
        logs = cur.fetchall()

        cur.close()
        conn.close()
    except Exception as e:
        print("DB ERROR:", e)
        logs = []

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "logs": logs,
            "barrier_status": barrier.status(),
            "barrier_is_open": barrier.is_opened
        }
    )

# ===================== PLATES =====================

@app.get("/plates", response_class=HTMLResponse)
async def plates_page(request: Request):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT plate FROM allowed_plates ORDER BY plate")
    plates = [row[0] for row in cur.fetchall()]

    cur.close()
    conn.close()

    return templates.TemplateResponse(
        "plates.html",
        {
            "request": request,
            "plates": plates
        }
    )


@app.post("/add-plate")
async def add_plate(plate: str = Form(...)):
    clean_plate = plate.upper().replace(" ", "").strip()
    if not clean_plate:
        return RedirectResponse("/plates", status_code=303)

    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO allowed_plates (plate) VALUES (%s) ON CONFLICT DO NOTHING",
        (clean_plate,)
    )

    conn.commit()
    cur.close()
    conn.close()

    return RedirectResponse("/plates", status_code=303)


@app.post("/remove-plate")
async def remove_plate(plate: str = Form(...)):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("DELETE FROM allowed_plates WHERE plate = %s", (plate,))

    conn.commit()
    cur.close()
    conn.close()

    return RedirectResponse("/plates", status_code=303)

# ===================== LOGS =====================
# ❗ АТЫ СОЛ ҚАЛПЫ (/logs), ТЕК ДЕРЕККӨЗ ДҰРЫСТАЛДЫ

@app.get("/logs", response_class=HTMLResponse)
async def logs_page(request: Request):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            plate,
            status,
            entry_time,
            exit_time,
            duration_seconds,
            paid_until
        FROM parking_sessions
        ORDER BY COALESCE(exit_time, entry_time) DESC
        LIMIT 500
    """)

    logs = cur.fetchall()

    cur.close()
    conn.close()

    return templates.TemplateResponse(
        "logs.html",
        {
            "request": request,
            "logs": logs
        }
    )

# ===================== BARRIER CONTROL =====================

@app.post("/barrier/open")
async def open_barrier():
    barrier.open(manual=True)
    return RedirectResponse("/", status_code=303)


@app.post("/barrier/close")
async def close_barrier():
    barrier.close()
    return RedirectResponse("/", status_code=303)

# ===================== HEALTH CHECK =====================

@app.get("/status")
async def get_status():
    return {
        "status": "online",
        "barrier": barrier.status()
    }




