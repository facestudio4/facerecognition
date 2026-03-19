from backend.phase3_services_pack import run_phase3_cli

from backend.core.paths import BASE_DIR, DB_FILE
from config.settings import SETTINGS


def start_api(host: str | None = None, port: int | None = None) -> None:
    run_phase3_cli(
        str(BASE_DIR),
        str(DB_FILE),
        command="startapi",
        host=host or SETTINGS.api_host,
        port=port or SETTINGS.api_port,
    )
