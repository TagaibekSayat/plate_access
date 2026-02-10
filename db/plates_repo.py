from db.connection import get_conn

def normalize_plate(plate: str) -> str:
    """
    БАРЛЫҚ жерден келген номерді
    БАЗА ФОРМАТЫНА келтіреміз
    """
    return plate.replace(" ", "").upper()


def is_allowed(plate: str) -> bool:
    plate = normalize_plate(plate)

    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        "SELECT 1 FROM allowed_plates WHERE plate = %s",
        (plate,)
    )

    result = cur.fetchone()

    cur.close()
    conn.close()

    return result is not None


def log_access(plate: str, status: str, reason: str):
    plate = normalize_plate(plate)

    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO access_logs (plate, status, reason)
        VALUES (%s, %s, %s)
        """,
        (plate, status, reason)
    )

    conn.commit()
    cur.close()
    conn.close()
