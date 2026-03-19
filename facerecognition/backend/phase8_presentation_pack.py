import json
import os
import sys
import tkinter as tk
from tkinter import messagebox

from backend.phase6_judge_mode_pack import launch_judge_mode_gui
from backend.phase7_demo_launcher_pack import DemoLaunchOrchestrator, launch_phase7_demo_launcher_gui


class PresentationStartupPack:
    def __init__(self, base_dir: str, db_path: str):
        self.base_dir = base_dir
        self.db_path = db_path
        self.script_dir = os.path.join(base_dir, "scripts", "presentation_day")
        self.python_executable = os.path.abspath(sys.executable)
        self.main_script = os.path.join(base_dir, "frontend", "facercognition.py")
        self.orchestrator = DemoLaunchOrchestrator(base_dir, db_path)

    def create_startup_scripts(self):
        os.makedirs(self.script_dir, exist_ok=True)
        commands = {
            "start_judge_mode.bat": f'@echo off\r\ncd /d "{self.base_dir}"\r\n"{self.python_executable}" "{self.main_script}" phase6\r\n',
            "start_demo_launcher.bat": f'@echo off\r\ncd /d "{self.base_dir}"\r\n"{self.python_executable}" "{self.main_script}" phase7\r\n',
            "prepare_demo_stack.bat": f'@echo off\r\ncd /d "{self.base_dir}"\r\n"{self.python_executable}" "{self.main_script}" demoprep\r\npause\r\n',
            "start_judge_mode.ps1": f'Set-Location "{self.base_dir}"\n& "{self.python_executable}" "{self.main_script}" phase6\n',
            "start_demo_launcher.ps1": f'Set-Location "{self.base_dir}"\n& "{self.python_executable}" "{self.main_script}" phase7\n',
            "prepare_demo_stack.ps1": f'Set-Location "{self.base_dir}"\n& "{self.python_executable}" "{self.main_script}" demoprep\n',
        }
        created = {}
        for name, content in commands.items():
            path = os.path.join(self.script_dir, name)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            created[name] = path
        manifest_path, manifest = self.orchestrator.prepare_demo()
        summary = {
            "script_dir": self.script_dir,
            "python_executable": self.python_executable,
            "main_script": self.main_script,
            "scripts": created,
            "latest_demo_manifest": manifest_path,
            "latest_bundle": manifest.get("bundle_dir", ""),
        }
        summary_path = os.path.join(self.script_dir, "presentation_startup_summary.json")
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        return summary_path, summary



def launch_phase8_presentation_gui(base_dir: str, db_path: str, parent=None, on_close_callback=None):
    pack = PresentationStartupPack(base_dir, db_path)

    if parent is None:
        win = tk.Tk()
        standalone = True
    else:
        win = tk.Toplevel(parent)
        standalone = False

    win.title("Presentation Startup")
    win.geometry("920x660")
    win.configure(bg="#0f172a")

    page_host = tk.Frame(win, bg="#0f172a")
    page_host.pack(fill="both", expand=True)
    page_canvas = tk.Canvas(page_host, bg="#0f172a", highlightthickness=0, bd=0)
    page_scroll = tk.Scrollbar(page_host, orient="vertical", command=page_canvas.yview)
    page = tk.Frame(page_canvas, bg="#0f172a")
    page_window = page_canvas.create_window((0, 0), window=page, anchor="nw")
    page_canvas.configure(yscrollcommand=page_scroll.set)
    page_canvas.pack(side="left", fill="both", expand=True)
    page_scroll.pack(side="right", fill="y")
    page.bind("<Configure>", lambda _e: page_canvas.configure(scrollregion=page_canvas.bbox("all")))
    page_canvas.bind("<Configure>", lambda e: page_canvas.itemconfigure(page_window, width=e.width))

    tk.Label(page, text="Presentation Startup", font=("Segoe UI", 24, "bold"), fg="#f59e0b", bg="#0f172a").pack(anchor="w", padx=14, pady=(12, 4))
    tk.Label(page, text="Generate launch scripts and jump straight into the presentation workflow", font=("Segoe UI", 11), fg="#c7d2fe", bg="#0f172a").pack(anchor="w", padx=14)

    status_var = tk.StringVar(value="Ready")
    tk.Label(page, textvariable=status_var, font=("Segoe UI", 10), fg="#7dd3fc", bg="#0f172a").pack(anchor="w", padx=14, pady=(6, 8))

    controls = tk.Frame(page, bg="#0f172a")
    controls.pack(fill="x", padx=14, pady=(0, 8))

    output = tk.Text(page, bg="#111827", fg="#e5e7eb", font=("Consolas", 10), height=28)
    output.pack(fill="both", expand=True, padx=14, pady=(0, 10))

    def set_output(payload):
        output.delete("1.0", "end")
        output.insert("end", json.dumps(payload, ensure_ascii=False, indent=2))
        output.see("1.0")

    def create_scripts():
        try:
            _, summary = pack.create_startup_scripts()
            status_var.set("Presentation scripts generated")
            set_output(summary)
        except Exception as e:
            status_var.set("Script generation failed")
            messagebox.showerror("Presentation Startup", str(e), parent=win)

    def open_judge():
        launch_judge_mode_gui(base_dir, db_path, parent=win)

    def open_demo_launcher():
        launch_phase7_demo_launcher_gui(base_dir, db_path, parent=win)

    tk.Button(controls, text="Generate Scripts", command=create_scripts, bg="#0f8c62", fg="white").pack(side="left", padx=4)
    tk.Button(controls, text="Judge Mode", command=open_judge, bg="#1f6cab", fg="white").pack(side="left", padx=4)
    tk.Button(controls, text="Demo Launcher", command=open_demo_launcher, bg="#7d6608", fg="white").pack(side="left", padx=4)

    create_scripts()

    def on_close():
        pack.orchestrator.controller.showcase.stop_services()
        win.destroy()
        if on_close_callback:
            on_close_callback()

    win.protocol("WM_DELETE_WINDOW", on_close)
    if standalone:
        win.mainloop()



def run_phase8_cli(base_dir: str, db_path: str, command: str):
    pack = PresentationStartupPack(base_dir, db_path)
    if command == "makepresentationkit":
        summary_path, summary = pack.create_startup_scripts()
        print(json.dumps({"summary_path": summary_path, "summary": summary}, ensure_ascii=False, indent=2))
        return
    if command == "presentationjudge":
        launch_judge_mode_gui(base_dir, db_path)
        return
    if command == "presentationdemo":
        launch_phase7_demo_launcher_gui(base_dir, db_path)
        return
    launch_phase8_presentation_gui(base_dir, db_path)
