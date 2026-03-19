import json
import os
import subprocess
import tkinter as tk
from tkinter import messagebox, ttk

from backend.phase4_showcase_pack import Phase4ShowcaseRunner
from backend.phase5_evaluator_pack import EvaluatorBundleBuilder


class JudgeModeController:
    def __init__(self, base_dir: str, db_path: str, host: str = "127.0.0.1", port: int = 8787):
        self.base_dir = base_dir
        self.db_path = db_path
        self.host = host
        self.port = int(port)
        self.bundle_root = os.path.join(base_dir, "database", "artifacts", "evaluator_bundle")
        self.builder = EvaluatorBundleBuilder(base_dir, db_path, host=host, port=port)
        self.showcase = Phase4ShowcaseRunner(base_dir, db_path, host=host, port=port)

    def find_latest_bundle_dir(self):
        if not os.path.isdir(self.bundle_root):
            return None
        candidates = []
        for name in os.listdir(self.bundle_root):
            full = os.path.join(self.bundle_root, name)
            if os.path.isdir(full) and name.startswith("bundle_"):
                candidates.append(full)
        if not candidates:
            return None
        candidates.sort(key=os.path.getmtime, reverse=True)
        return candidates[0]

    def ensure_latest_bundle(self):
        latest = self.find_latest_bundle_dir()
        if latest:
            return latest
        result = self.builder.build_bundle()
        return result["bundle_dir"]

    def latest_bundle_summary_path(self):
        latest = self.ensure_latest_bundle()
        return os.path.join(latest, "bundle_summary.json")

    def load_latest_summary(self):
        summary_path = self.latest_bundle_summary_path()
        with open(summary_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def latest_bundle_zip(self):
        latest = self.ensure_latest_bundle()
        zip_path = latest + ".zip"
        return zip_path if os.path.exists(zip_path) else ""

    def judge_snapshot(self):
        summary = self.load_latest_summary()
        stats = summary.get("stats", {})
        return {
            "bundle_dir": self.ensure_latest_bundle(),
            "bundle_zip": self.latest_bundle_zip(),
            "generated_at": summary.get("generated_at", ""),
            "api_base": summary.get("api_base", ""),
            "users": stats.get("users", 0),
            "face_events": stats.get("face_events", 0),
            "activity_events": stats.get("activity_events", 0),
            "attendance_entries": stats.get("attendance_entries", 0),
            "pending_approvals": stats.get("pending_approvals", 0),
            "db_size_mb": stats.get("db_size_mb", 0),
            "anomalies": summary.get("anomalies", []),
            "artifacts": summary.get("artifacts", {}),
        }

    def run_best_demo_path(self):
        return self.showcase.run_viva_sequence(user_limit=8)

    def _open_path(self, path: str):
        if not path or not os.path.exists(path):
            raise FileNotFoundError(path)
        if hasattr(os, "startfile"):
            os.startfile(path)
            return path
        subprocess.Popen(["xdg-open", path])
        return path

    def open_latest_bundle(self):
        return self._open_path(self.ensure_latest_bundle())

    def open_latest_zip(self):
        return self._open_path(self.latest_bundle_zip())

    def open_summary(self):
        return self._open_path(self.latest_bundle_summary_path())



def launch_judge_mode_gui(base_dir: str, db_path: str, parent=None, on_close_callback=None):
    controller = JudgeModeController(base_dir, db_path)

    if parent is None:
        win = tk.Tk()
        standalone = True
    else:
        win = tk.Toplevel(parent)
        standalone = False

    win.title("Judge Mode")
    win.geometry("1080x740")
    win.configure(bg="#111827")

    page_host = tk.Frame(win, bg="#111827")
    page_host.pack(fill="both", expand=True)
    page_canvas = tk.Canvas(page_host, bg="#111827", highlightthickness=0, bd=0)
    page_scroll = ttk.Scrollbar(page_host, orient="vertical", command=page_canvas.yview)
    page = tk.Frame(page_canvas, bg="#111827")
    page_window = page_canvas.create_window((0, 0), window=page, anchor="nw")
    page_canvas.configure(yscrollcommand=page_scroll.set)
    page_canvas.pack(side="left", fill="both", expand=True)
    page_scroll.pack(side="right", fill="y")
    page.bind("<Configure>", lambda _e: page_canvas.configure(scrollregion=page_canvas.bbox("all")))
    page_canvas.bind("<Configure>", lambda e: page_canvas.itemconfigure(page_window, width=e.width))

    tk.Label(page, text="Judge Mode", font=("Segoe UI", 24, "bold"), fg="#ffd166", bg="#111827").pack(anchor="w", padx=14, pady=(12, 4))
    tk.Label(page, text="Latest evaluator bundle, instant proof summary, and fastest demo actions", font=("Segoe UI", 11), fg="#b9d6ff", bg="#111827").pack(anchor="w", padx=14)

    status_var = tk.StringVar(value="Ready")
    metrics_var = tk.StringVar(value="Users: - | Face Events: - | Activity: - | Attendance: - | Pending: -")
    button_style = {"font": ("Segoe UI", 9, "bold"), "padx": 10, "pady": 4}
    tk.Label(page, textvariable=status_var, font=("Segoe UI", 10), fg="#7ad0ff", bg="#111827").pack(anchor="w", padx=14, pady=(6, 4))
    tk.Label(page, textvariable=metrics_var, font=("Consolas", 10, "bold"), fg="#f4f7fb", bg="#111827").pack(anchor="w", padx=14, pady=(0, 8))

    cards_row = tk.Frame(page, bg="#111827")
    cards_row.pack(fill="x", padx=14, pady=(0, 8))
    card_vars = {
        "bundle": tk.StringVar(value="-"),
        "zip": tk.StringVar(value="-"),
        "api": tk.StringVar(value="-"),
        "anomalies": tk.StringVar(value="0"),
    }
    for idx, (label, key) in enumerate(
        [
            ("Latest Bundle", "bundle"),
            ("Bundle Zip", "zip"),
            ("API Base", "api"),
            ("Anomaly Count", "anomalies"),
        ]
    ):
        card = tk.Frame(cards_row, bg="#0f172a", bd=1, relief="solid", highlightbackground="#2f4373", highlightthickness=1)
        card.grid(row=0, column=idx, sticky="nsew", padx=4)
        tk.Label(card, text=label, font=("Segoe UI", 9, "bold"), fg="#9cb3ff", bg="#0f172a").pack(anchor="w", padx=8, pady=(6, 2))
        tk.Label(card, textvariable=card_vars[key], font=("Consolas", 9), fg="#dbeafe", bg="#0f172a", wraplength=240, justify="left").pack(anchor="w", padx=8, pady=(0, 8))
    for i in range(4):
        cards_row.grid_columnconfigure(i, weight=1)

    controls = tk.LabelFrame(page, text="Actions", font=("Segoe UI", 10, "bold"), fg="#cfdcff", bg="#111827")
    controls.pack(fill="x", padx=14, pady=(0, 8))
    controls_row = tk.Frame(controls, bg="#111827")
    controls_row.pack(fill="x", padx=8, pady=8)

    output_box = tk.LabelFrame(page, text="Judge Console", font=("Segoe UI", 10, "bold"), fg="#cfdcff", bg="#111827")
    output_box.pack(fill="both", expand=True, padx=14, pady=(0, 10))
    output = tk.Text(output_box, bg="#0f172a", fg="#dbeafe", font=("Consolas", 10), height=28)
    output.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=8)
    output_scroll = ttk.Scrollbar(output_box, orient="vertical", command=output.yview)
    output_scroll.pack(side="right", fill="y", padx=(6, 8), pady=8)
    output.configure(yscrollcommand=output_scroll.set)

    def set_output(payload):
        output.delete("1.0", "end")
        output.insert("end", json.dumps(payload, ensure_ascii=False, indent=2))
        output.see("1.0")

    def refresh_summary():
        try:
            snapshot = controller.judge_snapshot()
            card_vars["bundle"].set(os.path.basename(snapshot.get("bundle_dir", "")) or "-")
            card_vars["zip"].set(os.path.basename(snapshot.get("bundle_zip", "")) or "-")
            card_vars["api"].set(snapshot.get("api_base", "-") or "-")
            card_vars["anomalies"].set(str(len(snapshot.get("anomalies", []))))
            metrics_var.set(
                f"Users: {snapshot['users']} | Face Events: {snapshot['face_events']} | Activity: {snapshot['activity_events']} | "
                f"Attendance: {snapshot['attendance_entries']} | Pending: {snapshot['pending_approvals']}"
            )
            set_output(snapshot)
            status_var.set("Latest evaluator bundle loaded")
        except Exception as e:
            status_var.set("Judge summary failed")
            output.delete("1.0", "end")
            output.insert("end", str(e))

    def build_latest():
        try:
            result = controller.builder.build_bundle()
            status_var.set("New evaluator bundle generated")
            set_output(result)
        except Exception as e:
            status_var.set("Bundle generation failed")
            messagebox.showerror("Judge Mode", str(e), parent=win)

    def open_bundle():
        try:
            controller.open_latest_bundle()
            status_var.set("Latest bundle opened")
        except Exception as e:
            status_var.set("Open bundle failed")
            messagebox.showerror("Judge Mode", str(e), parent=win)

    def open_zip():
        try:
            controller.open_latest_zip()
            status_var.set("Latest zip opened")
        except Exception as e:
            status_var.set("Open zip failed")
            messagebox.showerror("Judge Mode", str(e), parent=win)

    def open_summary():
        try:
            controller.open_summary()
            status_var.set("Bundle summary opened")
        except Exception as e:
            status_var.set("Open summary failed")
            messagebox.showerror("Judge Mode", str(e), parent=win)

    def run_demo():
        try:
            data = controller.run_best_demo_path()
            status_var.set("Live demo run completed")
            set_output(data)
        except Exception as e:
            status_var.set("Live demo failed")
            messagebox.showerror("Judge Mode", str(e), parent=win)

    tk.Button(controls_row, text="Refresh Summary", command=refresh_summary, bg="#1f6cab", fg="white", **button_style).pack(side="left", padx=4)
    tk.Button(controls_row, text="Build New Bundle", command=build_latest, bg="#0f8c62", fg="white", **button_style).pack(side="left", padx=4)
    tk.Button(controls_row, text="Open Bundle", command=open_bundle, bg="#7d6608", fg="white", **button_style).pack(side="left", padx=4)
    tk.Button(controls_row, text="Open Zip", command=open_zip, bg="#7b241c", fg="white", **button_style).pack(side="left", padx=4)
    tk.Button(controls_row, text="Open Summary", command=open_summary, bg="#512e5f", fg="white", **button_style).pack(side="left", padx=4)
    tk.Button(controls_row, text="Run Best Demo", command=run_demo, bg="#0f3460", fg="white", **button_style).pack(side="left", padx=4)

    refresh_summary()

    def on_close():
        controller.showcase.stop_services()
        win.destroy()
        if on_close_callback:
            on_close_callback()

    win.protocol("WM_DELETE_WINDOW", on_close)
    if standalone:
        win.mainloop()



def run_phase6_cli(base_dir: str, db_path: str, command: str, host: str = "127.0.0.1", port: int = 8787):
    controller = JudgeModeController(base_dir, db_path, host=host, port=port)
    if command == "judgesnapshot":
        print(json.dumps(controller.judge_snapshot(), ensure_ascii=False, indent=2))
        return
    if command == "judgedemo":
        print(json.dumps(controller.run_best_demo_path(), ensure_ascii=False, indent=2))
        return
    launch_judge_mode_gui(base_dir, db_path)
