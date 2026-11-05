# ============================================================
# db.py  -  MySQL er sathe connection
# Shob page e SQL ekhan theke 3 ta function diye chalabo
# ============================================================
import pymysql

# XAMPP e default: user = root, password = khali
DB_HOST = 'localhost'
DB_USER = 'root'
DB_PASSWORD = ''
DB_NAME = 'project_tracker'


def get_connection():
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor,   # row gulo dictionary hishebe pabo: row['name']
        autocommit=True,
    )


# Onek row ana:  fetch_all("SELECT * FROM projects")
def fetch_all(sql, params=()):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()
    finally:
        conn.close()


# Shudhu ekta row ana (na thakle None):  fetch_one("SELECT * FROM users WHERE id=%s", (1,))
def fetch_one(sql, params=()):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchone()
    finally:
        conn.close()


# INSERT / UPDATE / DELETE chalano. Notun row er id return kore.
def execute(sql, params=()):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.lastrowid
    finally:
        conn.close()