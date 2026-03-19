import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AppSettings:
    app_name: str = os.getenv("APP_NAME", "FaceRecognitionStudio")
    environment: str = os.getenv("APP_ENV", "dev")
    api_host: str = os.getenv("API_HOST", "127.0.0.1")
    api_port: int = int(os.getenv("API_PORT", "8787"))
    sqlite_path: str = os.getenv("SQLITE_PATH", "facestudio.db")


SETTINGS = AppSettings()
