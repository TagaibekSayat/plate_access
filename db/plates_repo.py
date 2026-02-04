from db.connection import get_conn

def is_allowed(plate: str) -> bool:
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
