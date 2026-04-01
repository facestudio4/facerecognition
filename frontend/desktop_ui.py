import subprocess
import sys

from backend.core.paths import BASE_DIR, KIVY_MAIN, LEGACY_MAIN


def launch_tkinter_ui() -> int:
    completed = subprocess.run([sys.executable, str(LEGACY_MAIN)], cwd=str(BASE_DIR), check=False)
    return completed.returncode


def launch_kivy_ui() -> int:
    completed = subprocess.run([sys.executable, str(KIVY_MAIN)], cwd=str(BASE_DIR), check=False)
    return completed.returncode
