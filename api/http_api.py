import os
import shutil

from backend.phase3_services_pack import run_phase3_cli

from backend.core.paths import BASE_DIR, DB_FILE
from config.settings import SETTINGS


def _resolve_db_path() -> str:
    """Resolve the SQLite path, preferring a persistent location.

    On Render the container filesystem is ephemeral, so writing the DB to the
    in-repo path means every redeploy/restart wipes all runtime data (new user
    signups, login history, recognition/activity events) back to the committed
    seed. When ``SQLITE_PATH`` points at a persistent disk (e.g. /var/data) we
    use it instead, and seed it ONCE from the committed DB so the existing API
    key, token secret and seed users carry over (a fresh empty DB would
    regenerate the API key and break the mobile app). Falls back to the in-repo
    DB for local dev or if the persistent path can't be prepared.
    """
    configured = os.environ.get("SQLITE_PATH", "").strip()
    if not configured or os.path.abspath(configured) == os.path.abspath(str(DB_FILE)):
        return str(DB_FILE)
    try:
        target_dir = os.path.dirname(configured)
        if target_dir:
            os.makedirs(target_dir, exist_ok=True)
        if not os.path.exists(configured) and os.path.exists(str(DB_FILE)):
            shutil.copyfile(str(DB_FILE), configured)
        return configured
    except Exception:
        return str(DB_FILE)


def start_api(host: str | None = None, port: int | None = None) -> None:
    run_phase3_cli(
        str(BASE_DIR),
        _resolve_db_path(),
        command="startapi",
        host=host or SETTINGS.api_host,
        port=port or SETTINGS.api_port,
    )
