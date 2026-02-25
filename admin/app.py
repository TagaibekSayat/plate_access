import os
import time
import cv2
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from db.connection import get_conn
from barrier.controller import BarrierController
from db.parking_repo import register_payment
from db.user_repo import verify_user

app = FastAPI(title="Plate Access Control")
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET", "change-this-secret"),
    same_site="lax",
    https_only=False,
)

# ===================== STATIC & TEMPLATES =====================

app.mount("/static", StaticFiles(directory="admin/static"), name="static")
templates = Jinja2Templates(directory="admin/templates")

barrier = BarrierController()


def is_admin_authenticated(request: Request) -> bool:
    return bool(request.session.get("user_id"))


def redirect_login():
    return RedirectResponse("/login", status_code=303)


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if is_admin_authenticated(request):
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "error": ""}
    )


@app.post("/login", response_class=HTMLResponse)
async def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...)
):
    user = verify_user(username, password)
    if not user:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Неверный логин или пароль"},
            status_code=401
        )

    request.session["user_id"] = user["id"]
    request.session["username"] = user["username"]
    return RedirectResponse("/", status_code=303)


@app.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)

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
                time.sleep(0.01)
                continue
        else:
            time.sleep(0.1)
        
        
        time.sleep(0.04)

@app.get("/video_feed")
def video_feed(request: Request):
    if not is_admin_authenticated(request):
        return redirect_login()
    return StreamingResponse(
        get_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

# ===================== DASHBOARD =====================

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    if not is_admin_authenticated(request):
        return redirect_login()
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
    if not is_admin_authenticated(request):
        return redirect_login()
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
async def add_plate(request: Request, plate: str = Form(...)):
    if not is_admin_authenticated(request):
        return redirect_login()
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
async def remove_plate(request: Request, plate: str = Form(...)):
    if not is_admin_authenticated(request):
        return redirect_login()
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("DELETE FROM allowed_plates WHERE plate = %s", (plate,))

    conn.commit()
    cur.close()
    conn.close()

    return RedirectResponse("/plates", status_code=303)

# ===================== LOGS =====================

def fetch_logs_data(
    plate: str = "",
    status: str = "ALL",
    log_date: str = "",
    page: int = 1,
    use_date: int = 0
):
    conn = get_conn()
    cur = conn.cursor()

    page = max(1, page)
    per_page = 20

    filters = []
    params = []

    if plate.strip():
        normalized_plate = (
            plate.strip()
            .upper()
            .replace(" ", "")
            .replace("-", "")
        )
        filters.append("REPLACE(REPLACE(UPPER(plate), ' ', ''), '-', '') LIKE %s")
        params.append(f"%{normalized_plate}%")

    if status in ("GRANTED", "DENIED"):
        filters.append("status = %s")
        params.append(status)

    if use_date and log_date:
        filters.append("DATE(created_at) = %s")
        params.append(log_date)

    where_sql = f"WHERE {' AND '.join(filters)}" if filters else ""

    cur.execute(
        f"""
        SELECT COUNT(*)
        FROM access_logs
        {where_sql}
        """,
        params
    )
    total_count = cur.fetchone()[0] or 0
    total_pages = max(1, (total_count + per_page - 1) // per_page)
    if page > total_pages:
        page = total_pages
    offset = (page - 1) * per_page
    max_visible_pages = 10
    window_start = ((page - 1) // max_visible_pages) * max_visible_pages + 1
    window_end = min(total_pages, window_start + max_visible_pages - 1)
    visible_pages = list(range(window_start, window_end + 1))

    cur.execute("""
        SELECT
            plate,
            status,
            reason,
            created_at
        FROM access_logs
        """ + where_sql + """
        ORDER BY created_at DESC
        LIMIT %s OFFSET %s
    """, params + [per_page, offset])

    logs = cur.fetchall()

    cur.execute(
        f"""
        SELECT
            COUNT(*) AS total,
            COALESCE(SUM(CASE WHEN status = 'GRANTED' THEN 1 ELSE 0 END), 0) AS granted,
            COALESCE(SUM(CASE WHEN status = 'DENIED' THEN 1 ELSE 0 END), 0) AS denied
        FROM access_logs
        {where_sql}
        """,
        params
    )
    stats_row = cur.fetchone() or (0, 0, 0)
    today_count, granted_count, denied_count = stats_row

    cur.close()
    conn.close()

    logs_json = []
    for row in logs:
        plate_val, status_val, reason_val, created_at_val = row
        logs_json.append({
            "plate": plate_val,
            "status": status_val,
            "reason": reason_val or "—",
            "created_at": created_at_val.strftime("%Y-%m-%d %H:%M") if created_at_val else "—",
        })

    return {
        "logs": logs,
        "logs_json": logs_json,
        "today_count": today_count,
        "granted_count": granted_count,
        "denied_count": denied_count,
        "selected_date": log_date,
        "filter_plate": plate,
        "filter_status": status,
        "use_date": use_date,
        "current_page": page,
        "total_pages": total_pages,
        "total_count": total_count,
        "visible_pages": visible_pages,
        "per_page": per_page,
    }

@app.get("/logs", response_class=HTMLResponse)
async def logs_page(
    request: Request,
    plate: str = "",
    status: str = "ALL",
    log_date: str = "",
    page: int = 1,
    use_date: int = 0
):
    if not is_admin_authenticated(request):
        return redirect_login()
    payload = fetch_logs_data(
        plate=plate,
        status=status,
        log_date=log_date,
        page=page,
        use_date=use_date
    )

    return templates.TemplateResponse(
        "logs.html",
        {
            "request": request,
            **payload
        }
    )


@app.get("/api/logs")
async def logs_api(
    request: Request,
    plate: str = "",
    status: str = "ALL",
    log_date: str = "",
    page: int = 1,
    use_date: int = 0
):
    if not is_admin_authenticated(request):
        return JSONResponse({"detail": "Unauthorized"}, status_code=401)
    payload = fetch_logs_data(
        plate=plate,
        status=status,
        log_date=log_date,
        page=page,
        use_date=use_date
    )
    return JSONResponse({
        "logs": payload["logs_json"],
        "today_count": payload["today_count"],
        "granted_count": payload["granted_count"],
        "denied_count": payload["denied_count"],
        "selected_date": payload["selected_date"],
        "filter_plate": payload["filter_plate"],
        "filter_status": payload["filter_status"],
        "use_date": payload["use_date"],
        "current_page": payload["current_page"],
        "total_pages": payload["total_pages"],
        "total_count": payload["total_count"],
        "visible_pages": payload["visible_pages"],
        "per_page": payload["per_page"],
    })

# ===================== BARRIER CONTROL =====================

@app.post("/barrier/open")
async def open_barrier(request: Request):
    if not is_admin_authenticated(request):
        return redirect_login()
    barrier.open(manual=True)
    return RedirectResponse("/", status_code=303)


@app.post("/barrier/close")
async def close_barrier(request: Request):
    if not is_admin_authenticated(request):
        return redirect_login()
    barrier.close()
    return RedirectResponse("/", status_code=303)

# ===================== HEALTH CHECK =====================

@app.get("/status")
async def get_status():
    return {
        "status": "online",
        "barrier": barrier.status()
    }
@app.get("/client", response_class=HTMLResponse)
async def client_page(request: Request):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT ps.plate, ps.entry_time
        FROM access_logs al
        JOIN parking_sessions ps
          ON ps.plate = al.plate
        WHERE ps.status = 'INSIDE'
        ORDER BY al.created_at DESC
        LIMIT 1
    """)
    session = cur.fetchone()

    cur.close()
    conn.close()

    return templates.TemplateResponse(
        "client.html",
        {
            "request": request,
            "session": session
        }
    )

@app.post("/client/pay")
async def client_pay(
    plate: str = Form(...),
    hours: int = Form(0),
    days: int = Form(0)
):
    clean_plate = plate.upper().strip()
    total_hours = max(0, hours) + (max(0, days) * 24)
    if total_hours <= 0:
        total_hours = 1

    register_payment(clean_plate, total_hours)

    return RedirectResponse("/client", status_code=303)




