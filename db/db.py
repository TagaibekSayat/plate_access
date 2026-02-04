import os
import psycopg2

def get_conn():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        port=os.getenv("DB_PORT")
    )

def is_allowed(plate):
    plate = plate.upper().strip() # Нөмірді үлкен әріпке айналдыру және артық пробелдерді алып тастау
    conn = get_conn()
    # ... қалған код
def is_allowed(plate):
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
