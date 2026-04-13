from db.connection import get_conn


def register_subscription(plate: str, hours: int, days: int, months: int):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        UPDATE subscriptions
        SET active = false
        WHERE plate = %s AND active = true
    """, (plate,))

    cur.execute("""
        INSERT INTO subscriptions (plate, start_date, end_date, active)
        VALUES (
            %s,
            NOW(),
            NOW()
              + (%s || ' hours')::INTERVAL
              + (%s || ' days')::INTERVAL
              + (%s || ' months')::INTERVAL,
            true
        )
    """, (plate, hours, days, months))

    conn.commit()
    cur.close()
    conn.close()


def has_active_subscription(plate: str) -> bool:
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT 1
        FROM subscriptions
        WHERE plate = %s
          AND active = true
          AND end_date > NOW()
        LIMIT 1
    """, (plate,))

    ok = cur.fetchone() is not None

    cur.close()
    conn.close()

    return ok