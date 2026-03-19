import os
import subprocess
import sys
from functools import partial

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
MAIN_APP_FILE = os.path.join(BASE_DIR, "facercognition.py")


def _preferred_kivy_python() -> str | None:
    candidate = os.path.join(PROJECT_ROOT, ".venv-kivy", "Scripts", "python.exe")
    if os.path.exists(candidate):
        return candidate
    return None


def _ensure_kivy_runtime() -> None:
    # If this interpreter cannot import Kivy, restart with the dedicated Kivy venv.
    if os.environ.get("FACESTUDIO_KIVY_BOOTSTRAPPED") == "1":
        return

    try:
        import importlib.util

        if importlib.util.find_spec("kivy"):
            return
    except Exception:
        pass

    preferred = _preferred_kivy_python()
    if preferred and os.path.abspath(preferred) != os.path.abspath(sys.executable):
        env = os.environ.copy()
        env["FACESTUDIO_KIVY_BOOTSTRAPPED"] = "1"
        cmd = [preferred, os.path.abspath(__file__), *sys.argv[1:]]
        subprocess.Popen(cmd, cwd=PROJECT_ROOT, env=env)
        print("Kivy runtime not found in this interpreter. Relaunched with .venv-kivy.")
        raise SystemExit(0)

    print("Kivy is not installed for this Python interpreter.")
    print("Run: .\\.venv-kivy\\Scripts\\python.exe kivy_laptop_app.py")
    raise SystemExit(1)


_ensure_kivy_runtime()

from kivy.app import App
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget


def _resolve_runner_python() -> str:
    preferred = os.path.join(PROJECT_ROOT, ".venv-1", "Scripts", "python.exe")
    if os.path.exists(preferred):
        return preferred
    return sys.executable


def _launch_command(command: str | None) -> tuple[bool, str]:
    if not os.path.exists(MAIN_APP_FILE):
        return False, "Main app file not found: facercognition.py"

    runner = _resolve_runner_python()
    args = [runner, MAIN_APP_FILE]
    if command:
        args.append(command)

    flags = 0
    if os.name == "nt":
        flags = subprocess.CREATE_NEW_CONSOLE

    try:
        subprocess.Popen(args, cwd=PROJECT_ROOT, creationflags=flags)
        return True, f"Started: {'main app' if not command else command}"
    except Exception as exc:
        return False, f"Launch error: {exc}"


class KivyLaptopLauncher(App):
    def build(self):
        Window.size = (1080, 760)
        Window.clearcolor = (0.07, 0.08, 0.13, 1)

        root = BoxLayout(orientation="vertical", padding=dp(18), spacing=dp(12))

        hero = BoxLayout(orientation="vertical", size_hint=(1, None), height=dp(104), padding=dp(12), spacing=dp(4))
        hero.canvas.before.clear()
        with hero.canvas.before:
            from kivy.graphics import Color, RoundedRectangle

            Color(0.12, 0.18, 0.33, 1)
            self._hero_bg = RoundedRectangle(radius=[18], pos=hero.pos, size=hero.size)

        hero.bind(pos=self._update_hero_bg, size=self._update_hero_bg)

        title = Label(
            text="Face Studio Launcher",
            color=(0.98, 0.98, 0.99, 1),
            font_size="30sp",
            bold=True,
            size_hint=(1, None),
            height=dp(40),
            halign="left",
            valign="middle",
        )
        title.bind(size=lambda inst, _: setattr(inst, "text_size", inst.size))

        subtitle = Label(
            text="Organized desktop interface for all project flows",
            color=(0.74, 0.82, 0.98, 1),
            font_size="15sp",
            size_hint=(1, None),
            height=dp(28),
            halign="left",
            valign="middle",
        )
        subtitle.bind(size=lambda inst, _: setattr(inst, "text_size", inst.size))

        hero.add_widget(title)
        hero.add_widget(subtitle)
        root.add_widget(hero)

        self.status_label = Label(
            text="Ready",
            color=(0.55, 0.88, 0.95, 1),
            font_size="14sp",
            size_hint=(1, None),
            height=dp(28),
            halign="left",
            valign="middle",
        )
        self.status_label.bind(size=lambda inst, _: setattr(inst, "text_size", inst.size))
        root.add_widget(self.status_label)

        scroller = ScrollView(size_hint=(1, 1), bar_width=dp(8), scroll_type=["bars", "content"])
        content = BoxLayout(orientation="vertical", spacing=dp(10), size_hint=(1, None), padding=(0, 0, 0, dp(16)))
        content.bind(minimum_height=content.setter("height"))

        sections = [
            (
                "Core",
                [
                    ("Open Main Login", "Launch full app home/login", None),
                    ("Face Recognition", "Live webcam recognition", "recognize"),
                    ("Face Generation", "Apply visual styles", "generate"),
                    ("Face Comparison", "Compare two face images", "compare"),
                ],
            ),
            (
                "Data and Admin",
                [
                    ("Attendance", "Webcam attendance mode", "attendance"),
                    ("Attendance Reports", "Session report viewer", "reports"),
                    ("Face Database", "Manage registered faces", "database"),
                    ("Analytics", "Stats and export center", "analytics"),
                    ("Advanced Lab", "Backup, benchmark, report", "lab"),
                    ("Enterprise Center", "Permissions and evidence", "enterprise"),
                ],
            ),
            (
                "Services and Presentation",
                [
                    ("Services Hub", "REST API and scheduler", "phase3"),
                    ("Live Dashboard", "Evaluator live view", "phase41"),
                    ("Evaluator Bundle", "Build full submission pack", "phase5"),
                    ("Judge Mode", "Open latest bundle review", "phase6"),
                    ("Demo Launcher", "Prepare demo stack", "phase7"),
                    ("Presentation Startup", "Presentation day tools", "phase8"),
                ],
            ),
        ]

        for section_title, items in sections:
            content.add_widget(self._make_section_title(section_title))
            for btn_text, subtitle_text, cmd in items:
                content.add_widget(self._make_action_button(btn_text, subtitle_text, cmd))

        scroller.add_widget(content)
        root.add_widget(scroller)

        footer = Label(
            text="Tip: This launcher uses .venv-1 for facercognition.py so your current app setup keeps working.",
            color=(0.65, 0.7, 0.82, 1),
            font_size="12sp",
            size_hint=(1, None),
            height=dp(26),
            halign="left",
            valign="middle",
        )
        footer.bind(size=lambda inst, _: setattr(inst, "text_size", inst.size))
        root.add_widget(footer)

        return root

    def _update_hero_bg(self, widget, _value):
        self._hero_bg.pos = widget.pos
        self._hero_bg.size = widget.size

    def _make_section_title(self, title: str) -> Widget:
        bar = BoxLayout(orientation="horizontal", size_hint=(1, None), height=dp(34), padding=(dp(6), 0))
        lbl = Label(
            text=title,
            color=(0.5, 0.86, 1.0, 1),
            bold=True,
            font_size="16sp",
            halign="left",
            valign="middle",
        )
        lbl.bind(size=lambda inst, _: setattr(inst, "text_size", inst.size))
        bar.add_widget(lbl)
        return bar

    def _make_action_button(self, title: str, subtitle: str, command: str | None) -> Button:
        btn = Button(
            text=f"[b]{title}[/b]\n[size=13sp]{subtitle}[/size]",
            markup=True,
            size_hint=(1, None),
            height=dp(78),
            background_normal="",
            background_down="",
            background_color=(0.16, 0.22, 0.4, 1),
            color=(0.96, 0.97, 1, 1),
            halign="left",
            valign="middle",
            padding=(dp(16), dp(8)),
        )
        btn.bind(size=lambda inst, _: setattr(inst, "text_size", (inst.width - dp(24), None)))
        btn.bind(on_release=partial(self._on_action, command))
        return btn

    def _on_action(self, command: str | None, _button):
        ok, msg = _launch_command(command)
        self.status_label.text = msg
        self.status_label.color = (0.55, 0.88, 0.95, 1) if ok else (1, 0.5, 0.5, 1)


if __name__ == "__main__":
    KivyLaptopLauncher().run()
