"""Scheduled auto-pull of enrolled faces from the cloud backend.

Runs unattended (e.g. from a Windows Scheduled Task every 10 minutes). It pulls
every person's face images from the Render backend's export endpoint and writes
them into the local ``database/faces/<name>/`` folders, creating folders as
needed. Designed to be launched with ``pythonw.exe`` so no console window
appears; all output goes to ``logs/pull_faces.log`` instead.

The API key is read from the local backend DB at runtime (or the
``FACESTUDIO_API_KEY`` env var) so no secret is stored in plaintext here.
"""

import os
import sqlite3
import sys
from datetime import datetime

# Make the project root importable so we can reuse the existing pull helpers.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from scripts.pull_faces_from_cloud import (  # noqa: E402
    normalize_base_url,
    post_json,
    write_entries,
)

DB_PATH = os.path.join(PROJECT_ROOT, "database", "facestudio.db")
DEST_DIR = os.path.join(PROJECT_ROOT, "database", "faces")
LOG_DIR = os.path.join(PROJECT_ROOT, "logs")
LOG_PATH = os.path.join(LOG_DIR, "pull_faces.log")
BASE_URL = os.environ.get(
    "FACE_STUDIO_BASE_URL", "https://facerecognition-4.onrender.com"
).strip()
MAX_LOG_LINES = 500


def _log(message: str) -> None:
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{stamp}  {message}"
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
        # Keep the log from growing without bound.
        try:
            with open(LOG_PATH, "r", encoding="utf-8") as f:
                lines = f.readlines()
            if len(lines) > MAX_LOG_LINES:
                with open(LOG_PATH, "w", encoding="utf-8") as f:
                    f.writelines(lines[-MAX_LOG_LINES:])
        except Exception:
            pass
    except Exception:
        pass


def _read_api_key() -> str:
    env_key = (os.environ.get("FACESTUDIO_API_KEY", "") or "").strip()
    if env_key:
        return env_key
    try:
        con = sqlite3.connect(DB_PATH)
        try:
            row = con.execute(
                "SELECT meta_value FROM project_meta WHERE meta_key='api_key'"
            ).fetchone()
        finally:
            con.close()
        return (row[0] if row else "").strip()
    except Exception as ex:
        _log(f"ERROR reading api_key from {DB_PATH}: {ex}")
        return ""


def main() -> int:
    api_key = _read_api_key()
    if not api_key:
        _log("ERROR: no API key available (set FACESTUDIO_API_KEY or seed the DB)")
        return 1

    try:
        base_url = normalize_base_url(BASE_URL)
        endpoint = f"{base_url}/api/admin/faces/export"
        result = post_json(endpoint, api_key, None, {"person": "", "limit": 0})
    except Exception as ex:
        _log(f"ERROR export request failed: {ex}")
        return 1

    if result.get("ok") is not True:
        _log(f"ERROR export not ok: {result}")
        return 1

    entries = (result.get("data") or {}).get("entries") or []
    try:
        imported = write_entries(entries, DEST_DIR, clear_existing=False)
    except Exception as ex:
        _log(f"ERROR writing entries: {ex}")
        return 1

    _log(f"OK pulled {imported} file(s) from {len(entries)} entry(ies) -> {DEST_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
