import sqlite3
from contextlib import contextmanager
from pathlib import Path

from backend.core.paths import BASE_DIR, DB_FILE


def resolve_db_path() -> Path:
    return DB_FILE if DB_FILE.exists() else BASE_DIR / "facestudio.db"


@contextmanager
def get_connection():
    conn = sqlite3.connect(str(resolve_db_path()))
    try:
        yield conn
    finally:
        conn.close()


def health_check() -> bool:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        return cursor.fetchone() == (1,)
