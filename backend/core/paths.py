from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
DB_FILE = BASE_DIR / "database" / "facestudio.db"
LEGACY_MAIN = BASE_DIR / "frontend" / "facercognition.py"
KIVY_MAIN = BASE_DIR / "frontend" / "kivy_laptop_app.py"
