import bcrypt

from db.connection import get_conn


def get_user_by_username(username: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, username, password_hash FROM users WHERE username = %s LIMIT 1",
        (username,),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row


def verify_user(username: str, password: str):
    row = get_user_by_username(username)
    if not row:
        return None

    user_id, db_username, password_hash = row
    if bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8")):
        return {"id": user_id, "username": db_username}
    return None
