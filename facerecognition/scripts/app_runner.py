import argparse
import os
import sys


def _prefer_standard_python() -> None:
    """Relaunch with python.exe when running under free-threaded pythonX.Yt.exe."""
    exe_name = os.path.basename(sys.executable).lower()
    if not exe_name.endswith("t.exe"):
        return

    standard_python = os.path.join(os.path.dirname(sys.executable), "python.exe")
    if os.path.exists(standard_python):
        os.execv(standard_python, [standard_python, *sys.argv])


_prefer_standard_python()

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from api.http_api import start_api
from backend.services.legacy_services import (
    launch_demo_launcher,
    launch_evaluator_bundle,
    launch_gui,
    launch_judge_mode,
    launch_presentation_startup,
    launch_services_hub,
    launch_showcase,
)
from config.settings import SETTINGS
from frontend.desktop_ui import launch_kivy_ui, launch_tkinter_ui


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="FaceRecognitionStudio unified runner")
    parser.add_argument(
        "mode",
        nargs="?",
        default="gui",
        choices=[
            "gui",
            "tk",
            "kivy",
            "api",
            "services",
            "showcase",
            "bundle",
            "judge",
            "demo",
            "presentation",
        ],
        help="What to run",
    )
    parser.add_argument("--host", default=SETTINGS.api_host)
    parser.add_argument("--port", type=int, default=SETTINGS.api_port)
    return parser


def main() -> int:
    args = build_parser().parse_args()

    if args.mode in {"gui", "tk"}:
        return launch_tkinter_ui()
    if args.mode == "kivy":
        return launch_kivy_ui()
    if args.mode == "api":
        start_api(args.host, args.port)
        return 0
    if args.mode == "services":
        return launch_services_hub()
    if args.mode == "showcase":
        return launch_showcase()
    if args.mode == "bundle":
        return launch_evaluator_bundle()
    if args.mode == "judge":
        return launch_judge_mode()
    if args.mode == "demo":
        return launch_demo_launcher()
    if args.mode == "presentation":
        return launch_presentation_startup()

    return launch_gui()


if __name__ == "__main__":
    raise SystemExit(main())
