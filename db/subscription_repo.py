from db.connection import get_conn


def register_subscription(plate: str, months: int):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO subscriptions (plate, start_date, end_date, active)
        VALUES (
            %s,
            NOW(),
            NOW() + (%s || ' months')::INTERVAL,
            true
        )
    """, (plate, months))

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

    result = cur.fetchone()

    cur.close()
    conn.close()

    return result is not None