import json
import os
import subprocess
import tkinter as tk
from datetime import datetime
from tkinter import messagebox

from backend.phase6_judge_mode_pack import JudgeModeController, launch_judge_mode_gui


class DemoLaunchOrchestrator:
    def __init__(self, base_dir: str, db_path: str, host: str = "127.0.0.1", port: int = 8787):
        self.base_dir = base_dir
        self.db_path = db_path
        self.host = host
        self.port = int(port)
        self.controller = JudgeModeController(base_dir, db_path, host=host, port=port)
        self.manifest_dir = os.path.join(base_dir, "database", "artifacts", "demo_launcher")

    def prepare_demo(self):
        os.makedirs(self.manifest_dir, exist_ok=True)
        bundle_dir = self.controller.builder.build_bundle()["bundle_dir"]
        snapshot = self.controller.judge_snapshot()
        demo_run = self.controller.run_best_demo_path()
        manifest = {
            "prepared_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "api_base": snapshot.get("api_base", ""),
            "bundle_dir": bundle_dir,
            "bundle_zip": snapshot.get("bundle_zip", ""),
            "summary": os.path.join(bundle_dir, "bundle_summary.json"),
            "project_report": snapshot.get("artifacts", {}).get("project_report", ""),
            "enterprise_evidence_zip": snapshot.get("artifacts", {}).get("enterprise_evidence_zip", ""),
            "viva_report": snapshot.get("artifacts", {}).get("viva_report", ""),
            "api_docs": snapshot.get("artifacts", {}).get("api_docs", ""),
            "quick_metrics": {
                "users": snapshot.get("users", 0),
                "face_events": snapshot.get("face_events", 0),
                "activity_events": snapshot.get("activity_events", 0),
                "attendance_entries": snapshot.get("attendance_entries", 0),
                "pending_approvals": snapshot.get("pending_approvals", 0),
                "db_size_mb": snapshot.get("db_size_mb", 0),
            },
            "anomalies": snapshot.get("anomalies", []),
            "live_demo": demo_run,
            "suggested_commands": [
                "python frontend/facercognition.py phase6",
                "python frontend/facercognition.py judgesnapshot",
                "python frontend/facercognition.py judgedemo",
                "python frontend/facercognition.py evaluatorbundle",
            ],
        }
        manifest_path = os.path.join(self.manifest_dir, "latest_demo_manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
        return manifest_path, manifest

    def load_manifest(self):
        manifest_path = os.path.join(self.manifest_dir, "latest_demo_manifest.json")
        if not os.path.exists(manifest_path):
            manifest_path, _ = self.prepare_demo()
        with open(manifest_path, "r", encoding="utf-8") as f:
            return manifest_path, json.load(f)

    def _open_path(self, path: str):
        if not path or not os.path.exists(path):
            raise FileNotFoundError(path)
        if hasattr(os, "startfile"):
            os.startfile(path)
            return path
        subprocess.Popen(["xdg-open", path])
        return path

    def open_manifest(self):
        manifest_path, _ = self.load_manifest()
        return self._open_path(manifest_path)

    def open_bundle(self):
        _, manifest = self.load_manifest()
        return self._open_path(manifest.get("bundle_dir", ""))

    def open_report(self):
        _, manifest = self.load_manifest()
        return self._open_path(manifest.get("project_report", ""))



def launch_phase7_demo_launcher_gui(base_dir: str, db_path: str, parent=None, on_close_callback=None):
    orchestrator = DemoLaunchOrchestrator(base_dir, db_path)

    if parent is None:
        win = tk.Tk()
        standalone = True
    else:
        win = tk.Toplevel(parent)
        standalone = False

    win.title("Phase 7 Demo Launcher")
    win.geometry("980x700")
    win.configure(bg="#0b1320")

    page_host = tk.Frame(win, bg="#0b1320")
    page_host.pack(fill="both", expand=True)
    page_canvas = tk.Canvas(page_host, bg="#0b1320", highlightthickness=0, bd=0)
    page_scroll = tk.Scrollbar(page_host, orient="vertical", command=page_canvas.yview)
    page = tk.Frame(page_canvas, bg="#0b1320")
    page_window = page_canvas.create_window((0, 0), window=page, anchor="nw")
    page_canvas.configure(yscrollcommand=page_scroll.set)
    page_canvas.pack(side="left", fill="both", expand=True)
    page_scroll.pack(side="right", fill="y")
    page.bind("<Configure>", lambda _e: page_canvas.configure(scrollregion=page_canvas.bbox("all")))
    page_canvas.bind("<Configure>", lambda e: page_canvas.itemconfigure(page_window, width=e.width))

    tk.Label(page, text="Phase 7 Demo Launcher", font=("Segoe UI", 24, "bold"), fg="#ffb703", bg="#0b1320").pack(anchor="w", padx=14, pady=(12, 4))
    tk.Label(page, text="Prepare the full demo stack, generate manifest, and jump straight into judge mode", font=("Segoe UI", 11), fg="#b9d6ff", bg="#0b1320").pack(anchor="w", padx=14)

    status_var = tk.StringVar(value="Ready")
    tk.Label(page, textvariable=status_var, font=("Segoe UI", 10), fg="#7ad0ff", bg="#0b1320").pack(anchor="w", padx=14, pady=(6, 8))

    controls = tk.Frame(page, bg="#0b1320")
    controls.pack(fill="x", padx=14, pady=(0, 8))

    output = tk.Text(page, bg="#111b35", fg="#d7e2ff", font=("Consolas", 10), height=30)
    output.pack(fill="both", expand=True, padx=14, pady=(0, 10))

    def set_output(payload):
        output.delete("1.0", "end")
        output.insert("end", json.dumps(payload, ensure_ascii=False, indent=2))
        output.see("1.0")

    def prepare_now():
        try:
            manifest_path, manifest = orchestrator.prepare_demo()
            status_var.set(f"Demo prepared: {manifest_path}")
            set_output(manifest)
        except Exception as e:
            status_var.set("Demo preparation failed")
            messagebox.showerror("Demo Launcher", str(e), parent=win)

    def load_now():
        try:
            _, manifest = orchestrator.load_manifest()
            status_var.set("Manifest loaded")
            set_output(manifest)
        except Exception as e:
            status_var.set("Manifest load failed")
            messagebox.showerror("Demo Launcher", str(e), parent=win)

    def open_manifest():
        try:
            orchestrator.open_manifest()
            status_var.set("Manifest opened")
        except Exception as e:
            status_var.set("Open manifest failed")
            messagebox.showerror("Demo Launcher", str(e), parent=win)

    def open_bundle():
        try:
            orchestrator.open_bundle()
            status_var.set("Bundle opened")
        except Exception as e:
            status_var.set("Open bundle failed")
            messagebox.showerror("Demo Launcher", str(e), parent=win)

    def open_report():
        try:
            orchestrator.open_report()
            status_var.set("Project report opened")
        except Exception as e:
            status_var.set("Open report failed")
            messagebox.showerror("Demo Launcher", str(e), parent=win)

    def open_judge():
        launch_judge_mode_gui(base_dir, db_path, parent=win)

    tk.Button(controls, text="Prepare Demo", command=prepare_now, bg="#0f8c62", fg="white").pack(side="left", padx=4)
    tk.Button(controls, text="Load Manifest", command=load_now, bg="#1f6cab", fg="white").pack(side="left", padx=4)
    tk.Button(controls, text="Open Manifest", command=open_manifest, bg="#7d6608", fg="white").pack(side="left", padx=4)
    tk.Button(controls, text="Open Bundle", command=open_bundle, bg="#7b241c", fg="white").pack(side="left", padx=4)
    tk.Button(controls, text="Open Report", command=open_report, bg="#512e5f", fg="white").pack(side="left", padx=4)
    tk.Button(controls, text="Judge Mode", command=open_judge, bg="#0f3460", fg="white").pack(side="left", padx=4)

    load_now()

    def on_close():
        orchestrator.controller.showcase.stop_services()
        win.destroy()
        if on_close_callback:
            on_close_callback()

    win.protocol("WM_DELETE_WINDOW", on_close)
    if standalone:
        win.mainloop()



def run_phase7_cli(base_dir: str, db_path: str, command: str, host: str = "127.0.0.1", port: int = 8787):
    orchestrator = DemoLaunchOrchestrator(base_dir, db_path, host=host, port=port)
    if command == "demoprep":
        manifest_path, manifest = orchestrator.prepare_demo()
        print(json.dumps({"manifest_path": manifest_path, "manifest": manifest}, ensure_ascii=False, indent=2))
        return
    if command == "demomanifest":
        manifest_path, manifest = orchestrator.load_manifest()
        print(json.dumps({"manifest_path": manifest_path, "manifest": manifest}, ensure_ascii=False, indent=2))
        return
    launch_phase7_demo_launcher_gui(base_dir, db_path)
