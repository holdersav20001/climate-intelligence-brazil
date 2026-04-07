# api/app/db.py
"""
PostgreSQL connection pool for FastAPI.
Reads CLIMATE_DATABASE_URL which already sets search_path=climate.
"""
import os
import psycopg2
import psycopg2.pool
from contextlib import contextmanager

DATABASE_URL = os.environ.get(
    "CLIMATE_DATABASE_URL",
    "postgresql://climate_intel:password@postgres:5432/climate_intel?options=-csearch_path%3Dclimate"
)

_pool: psycopg2.pool.ThreadedConnectionPool | None = None


def get_pool() -> psycopg2.pool.ThreadedConnectionPool:
    global _pool
    if _pool is None:
        _pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=2,
            maxconn=10,
            dsn=DATABASE_URL,
        )
    return _pool


@contextmanager
def get_conn():
    pool = get_pool()
    conn = pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)


def query(sql: str, params: tuple = ()) -> list[dict]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            cols = [desc[0] for desc in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]


def execute(sql: str, params: tuple = ()) -> int:
    """Returns rowcount."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.rowcount
