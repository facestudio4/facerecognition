import subprocess
import sys
from typing import Optional

from backend.core.paths import BASE_DIR, LEGACY_MAIN


def run_legacy(command: Optional[str] = None) -> int:
    args = [sys.executable, str(LEGACY_MAIN)]
    if command:
        args.append(command)
    completed = subprocess.run(args, cwd=str(BASE_DIR), check=False)
    return completed.returncode


def launch_gui() -> int:
    return run_legacy()


def launch_services_hub() -> int:
    return run_legacy("phase3")


def launch_showcase() -> int:
    return run_legacy("phase41")


def launch_evaluator_bundle() -> int:
    return run_legacy("phase5")


def launch_judge_mode() -> int:
    return run_legacy("phase6")


def launch_demo_launcher() -> int:
    return run_legacy("phase7")


def launch_presentation_startup() -> int:
    return run_legacy("phase8")
