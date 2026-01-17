from dotenv import load_dotenv
import os
from mysql.connector import pooling

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_DATABASE"),
}

_pool = None

def get_pool():
    global _pool
    if _pool is None:
        # PythonAnywhere free: max_user_connections ist klein -> Pool klein halten
        _pool = pooling.MySQLConnectionPool(
            pool_name="pool",
            pool_size=2,   # <= wichtig (statt 5)
            **DB_CONFIG
        )
    return _pool

def get_conn():
    return get_pool().get_connection()

def db_read(sql, params=None, single=False):
    conn = get_conn()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, params or ())
        return cur.fetchone() if single else cur.fetchall()
    finally:
        if cur:
            cur.close()
        conn.close()

def db_write(sql, params=None):
    conn = get_conn()
    cur = None
    try:
        cur = conn.cursor()
        cur.execute(sql, params or ())
        conn.commit()
    finally:
        if cur:
            cur.close()
        conn.close()
