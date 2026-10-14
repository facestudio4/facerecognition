import os
import shutil
import sqlite3
import tempfile
from contextlib import contextmanager
from pathlib import Path

from backend.core.paths import BASE_DIR, DB_FILE


def resolve_db_path() -> Path:
    return DB_FILE if DB_FILE.exists() else BASE_DIR / "facestudio.db"


@contextmanager
def get_connection():
    db_p = resolve_db_path()
    try:
        conn = sqlite3.connect(str(db_p))
        conn.execute("SELECT 1")
    except sqlite3.OperationalError:
        safe_dir = Path(tempfile.gettempdir()) / "facestudio_runtime"
        safe_dir.mkdir(parents=True, exist_ok=True)
        safe_db = safe_dir / db_p.name
        if db_p.exists() and (not safe_db.exists() or db_p.stat().st_mtime > safe_db.stat().st_mtime):
            try:
                shutil.copy2(str(db_p), str(safe_db))
            except Exception:
                pass
        conn = sqlite3.connect(str(safe_db))
    try:
        yield conn
    finally:
        conn.close()


def health_check() -> bool:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        return cursor.fetchone() == (1,)
