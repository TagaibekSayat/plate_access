from db.connection import get_conn


def is_inside(plate: str) -> bool:
    """Көлік қазір тұрақ ішінде ме, жоқ па — соны тексереді"""
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT 1
        FROM parking_sessions
        WHERE plate = %s AND status = 'INSIDE'
        LIMIT 1
    """, (plate,))

    result = cur.fetchone()

    cur.close()
    conn.close()

    return result is not None

def has_valid_payment(plate: str) -> bool:
    """Көліктің ағымдағы уақытқа дейін жарамды төлемі бар-жоғын тексереді"""
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT 1
        FROM parking_sessions
        WHERE plate = %s
          AND status = 'INSIDE'
          AND paid_until IS NOT NULL
          AND paid_until > NOW()
        LIMIT 1
    """, (plate,))

    ok = cur.fetchone() is not None
    cur.close()
    conn.close()

    return ok


def register_entry(plate: str):
    """Көлік кірген кезде жаңа сессия ашады"""
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO parking_sessions (
            plate,
            entry_time,
            status,
            paid,
            paid_until
        )
        VALUES (%s, NOW(), 'INSIDE', false, NULL)
    """, (plate,))

    conn.commit()
    cur.close()
    conn.close()



def get_active_session(plate: str):
    """Көліктің қазіргі белсенді сессиясын (ID және төлем мерзімі) алады"""
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, paid_until
        FROM parking_sessions
        WHERE plate = %s AND status = 'INSIDE'
        LIMIT 1
    """, (plate,))

    row = cur.fetchone()
    cur.close()
    conn.close()

    return row

def register_payment(plate: str, hours: int):
    """Белгілі бір сағатқа төлем жасалғанын тіркейді"""
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        UPDATE parking_sessions
        SET
            paid_until = NOW() + (%s || ' hours')::INTERVAL,
            paid = true
        WHERE plate = %s AND status = 'INSIDE'
    """, (hours, plate))

    conn.commit()
    cur.close()
    conn.close()


def register_exit(plate: str):
    """Көлік шыққан кезде сессияны жабады және тұрған уақытын есептейді"""
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        UPDATE parking_sessions
        SET
            exit_time = NOW(),
            duration_seconds = EXTRACT(EPOCH FROM (NOW() - entry_time)),
            status = 'EXITED'
        WHERE plate = %s
          AND status = 'INSIDE'
    """, (plate,))

    conn.commit()
    cur.close()
    conn.close()