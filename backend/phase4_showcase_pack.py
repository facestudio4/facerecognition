import json
import os
import queue
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
import tkinter as tk
from tkinter import messagebox, ttk

from backend.phase3_services_pack import Phase3ServiceHub


class Phase4ShowcaseRunner:
    def __init__(self, base_dir: str, db_path: str, host: str = "127.0.0.1", port: int = 8787):
        self.base_dir = base_dir
        self.db_path = db_path
        self.host = host
        self.port = int(port)
        self.hub = Phase3ServiceHub(base_dir, db_path, host=host, port=port)

    def base_url(self):
        return f"http://{self.host}:{self.port}"

    def ensure_services_started(self):
        self.hub.start_api_server()
        return self.base_url()

    def stop_services(self):
        self.hub.stop_all_services()

    def _http_get(self, path: str, headers=None, timeout: float = 8.0):
        if headers is None:
            headers = {}
        url = self.base_url() + path
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            payload = r.read().decode("utf-8")
        return json.loads(payload)

    def get_bearer_token(self, subject: str = "evaluator", ttl_minutes: int = 120):
        q = urllib.parse.urlencode({"subject": subject, "ttl": ttl_minutes})
        res = self._http_get(f"/api/auth/token?{q}", headers={"X-API-Key": self.hub.api_key})
        if not res.get("ok"):
            raise RuntimeError("Token issue failed")
        return res["data"]["token"]

    def run_viva_sequence(self, user_limit: int = 5):
        self.ensure_services_started()
        token = self.get_bearer_token()
        auth = {"Authorization": "Bearer " + token}
        health = self._http_get("/api/health")
        docs = self._http_get("/api/docs")
        stats = self._http_get("/api/stats", headers=auth)
        users = self._http_get(f"/api/users?limit={int(user_limit)}", headers=auth)
        activity = self._http_get("/api/activity?limit=10", headers=auth)
        return {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "base_url": self.base_url(),
            "health": health,
            "docs": docs,
            "stats": stats,
            "users": users,
            "activity": activity,
        }

    def export_viva_report(self):
        data = self.run_viva_sequence(user_limit=8)
        out_dir = os.path.join(self.base_dir, "database", "artifacts", "phase4_demo_kit")
        os.makedirs(out_dir, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(out_dir, f"viva_run_{stamp}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return path


def launch_phase41_showcase_gui(base_dir: str, db_path: str, parent=None, on_close_callback=None):
    runner = Phase4ShowcaseRunner(base_dir, db_path)
    stream_queue = queue.Queue()
    stop_stream = threading.Event()
    token_holder = {"token": ""}

    if parent is None:
        win = tk.Tk()
        standalone = True
    else:
        win = tk.Toplevel(parent)
        standalone = False

    win.title("Live Evaluator Dashboard")
    win.geometry("1080x740")
    win.configure(bg="#0b1225")

    page_host = tk.Frame(win, bg="#0b1225")
    page_host.pack(fill="both", expand=True)
    page_canvas = tk.Canvas(page_host, bg="#0b1225", highlightthickness=0, bd=0)
    page_scroll = ttk.Scrollbar(page_host, orient="vertical", command=page_canvas.yview)
    page = tk.Frame(page_canvas, bg="#0b1225")
    page_window = page_canvas.create_window((0, 0), window=page, anchor="nw")
    page_canvas.configure(yscrollcommand=page_scroll.set)
    page_canvas.pack(side="left", fill="both", expand=True)
    page_scroll.pack(side="right", fill="y")
    page.bind("<Configure>", lambda _e: page_canvas.configure(scrollregion=page_canvas.bbox("all")))
    page_canvas.bind("<Configure>", lambda e: page_canvas.itemconfigure(page_window, width=e.width))

    title = tk.Label(page, text="Live Evaluator Dashboard", font=("Segoe UI", 24, "bold"), fg="#f8b400", bg="#0b1225")
    title.pack(anchor="w", padx=14, pady=(12, 4))

    status_var = tk.StringVar(value="Ready")
    stats_var = tk.StringVar(value="Users: - | Face Events: - | Activity: - | Pending Approvals: -")
    button_style = {"font": ("Segoe UI", 9, "bold"), "padx": 10, "pady": 4}

    tk.Label(page, textvariable=status_var, font=("Segoe UI", 10), fg="#7ad0ff", bg="#0b1225").pack(anchor="w", padx=14)
    tk.Label(page, textvariable=stats_var, font=("Consolas", 10, "bold"), fg="#f5f7fa", bg="#0b1225").pack(anchor="w", padx=14, pady=(4, 8))

    cards_row = tk.Frame(page, bg="#0b1225")
    cards_row.pack(fill="x", padx=14, pady=(0, 8))
    cards = {
        "users": tk.StringVar(value="0"),
        "face_events": tk.StringVar(value="0"),
        "activity_events": tk.StringVar(value="0"),
        "pending_approvals": tk.StringVar(value="0"),
    }
    for idx, (label, key) in enumerate(
        [
            ("Users", "users"),
            ("Face Events", "face_events"),
            ("Activity", "activity_events"),
            ("Pending Approvals", "pending_approvals"),
        ]
    ):
        card = tk.Frame(cards_row, bg="#111b35", bd=1, relief="solid", highlightbackground="#31427f", highlightthickness=1)
        card.grid(row=0, column=idx, sticky="nsew", padx=4)
        tk.Label(card, text=label, font=("Segoe UI", 9, "bold"), fg="#9cb3ff", bg="#111b35").pack(anchor="w", padx=8, pady=(6, 2))
        tk.Label(card, textvariable=cards[key], font=("Segoe UI", 16, "bold"), fg="#f5f7fa", bg="#111b35").pack(anchor="w", padx=8, pady=(0, 8))
    for i in range(4):
        cards_row.grid_columnconfigure(i, weight=1)

    controls = tk.LabelFrame(page, text="Actions", font=("Segoe UI", 10, "bold"), fg="#cfdcff", bg="#0b1225")
    controls.pack(fill="x", padx=14, pady=(0, 8))
    controls_row = tk.Frame(controls, bg="#0b1225")
    controls_row.pack(fill="x", padx=8, pady=8)

    output_box = tk.LabelFrame(page, text="Live Console", font=("Segoe UI", 10, "bold"), fg="#cfdcff", bg="#0b1225")
    output_box.pack(fill="both", expand=True, padx=14, pady=(0, 10))
    output = tk.Text(output_box, bg="#111b35", fg="#d7e2ff", font=("Consolas", 10), height=26)
    output.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=8)
    output_scroll = ttk.Scrollbar(output_box, orient="vertical", command=output.yview)
    output_scroll.pack(side="right", fill="y", padx=(6, 8), pady=8)
    output.configure(yscrollcommand=output_scroll.set)

    def append(msg: str):
        output.insert("end", msg + "\n")
        output.see("end")

    def start_services():
        runner.ensure_services_started()
        status_var.set(f"Services running at {runner.base_url()}")
        append("Services started")

    def stop_services_now():
        runner.stop_services()
        status_var.set("Services stopped")
        append("Services stopped")

    def issue_token():
        try:
            token_holder["token"] = runner.get_bearer_token(subject="dashboard", ttl_minutes=180)
            status_var.set("Bearer token issued")
            append("Bearer token issued")
        except Exception as e:
            status_var.set("Token issue failed")
            append("Token issue failed: " + str(e))

    def run_viva():
        try:
            data = runner.run_viva_sequence(user_limit=8)
            status_var.set("Viva demo sequence completed")
            append("Viva run completed")
            append(json.dumps({
                "health": data["health"],
                "stats": data["stats"],
                "users_count": len(data["users"].get("data", [])),
                "activity_count": len(data["activity"].get("data", [])),
            }, ensure_ascii=False))
        except Exception as e:
            status_var.set("Viva run failed")
            append("Viva run failed: " + str(e))

    def export_report():
        try:
            path = runner.export_viva_report()
            status_var.set(f"Report exported: {path}")
            append("Report exported: " + path)
        except Exception as e:
            status_var.set("Report export failed")
            append("Report export failed: " + str(e))

    def open_docs():
        try:
            docs = runner._http_get("/api/docs")
            append("API Docs")
            append(json.dumps(docs, ensure_ascii=False, indent=2))
            status_var.set("API docs loaded")
        except Exception as e:
            status_var.set("API docs failed")
            append("API docs failed: " + str(e))

    def stream_worker():
        while not stop_stream.is_set():
            try:
                if not token_holder["token"]:
                    try:
                        token_holder["token"] = runner.get_bearer_token(subject="stream", ttl_minutes=180)
                    except Exception:
                        time.sleep(1)
                        continue
                req = urllib.request.Request(
                    runner.base_url() + "/api/events/stream",
                    headers={"Authorization": "Bearer " + token_holder["token"]},
                )
                with urllib.request.urlopen(req, timeout=20) as resp:
                    while not stop_stream.is_set():
                        line = resp.readline().decode("utf-8", errors="ignore").strip()
                        if not line:
                            continue
                        if line.startswith("data:"):
                            payload_text = line[5:].strip()
                            stream_queue.put(payload_text)
            except Exception:
                time.sleep(1)

    stream_thread = threading.Thread(target=stream_worker, daemon=True)
    stream_thread.start()

    def pump_stream():
        for _ in range(20):
            if stream_queue.empty():
                break
            msg = stream_queue.get_nowait()
            append("EVENT " + msg)
        win.after(400, pump_stream)

    def poll_stats():
        try:
            if not token_holder["token"]:
                token_holder["token"] = runner.get_bearer_token(subject="poll", ttl_minutes=180)
            stats = runner._http_get("/api/stats", headers={"Authorization": "Bearer " + token_holder["token"]})
            data = stats.get("data", {}) if isinstance(stats, dict) else {}
            cards["users"].set(str(data.get("users", 0)))
            cards["face_events"].set(str(data.get("face_events", 0)))
            cards["activity_events"].set(str(data.get("activity_events", 0)))
            cards["pending_approvals"].set(str(data.get("pending_approvals", 0)))
            stats_var.set(
                f"Users: {data.get('users', 0)} | Face Events: {data.get('face_events', 0)} | "
                f"Activity: {data.get('activity_events', 0)} | Pending Approvals: {data.get('pending_approvals', 0)}"
            )
        except Exception:
            pass
        win.after(2500, poll_stats)

    tk.Button(controls_row, text="Start Services", command=start_services, bg="#0f8c62", fg="white", **button_style).pack(side="left", padx=4)
    tk.Button(controls_row, text="Issue Token", command=issue_token, bg="#2e4053", fg="white", **button_style).pack(side="left", padx=4)
    tk.Button(controls_row, text="Run Viva Demo", command=run_viva, bg="#1f6cab", fg="white", **button_style).pack(side="left", padx=4)
    tk.Button(controls_row, text="Export Viva Report", command=export_report, bg="#7b241c", fg="white", **button_style).pack(side="left", padx=4)
    tk.Button(controls_row, text="Show API Docs", command=open_docs, bg="#512e5f", fg="white", **button_style).pack(side="left", padx=4)
    tk.Button(controls_row, text="Stop Services", command=stop_services_now, bg="#b03a2e", fg="white", **button_style).pack(side="left", padx=4)

    start_services()
    issue_token()
    append("Dashboard ready")
    pump_stream()
    poll_stats()

    def on_close():
        stop_stream.set()
        runner.stop_services()
        win.destroy()
        if on_close_callback:
            on_close_callback()

    win.protocol("WM_DELETE_WINDOW", on_close)
    if standalone:
        win.mainloop()


def run_phase41_cli(base_dir: str, db_path: str, command: str, host: str = "127.0.0.1", port: int = 8787):
    runner = Phase4ShowcaseRunner(base_dir, db_path, host=host, port=port)
    if command == "vivademo":
        data = runner.run_viva_sequence(user_limit=8)
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return
    if command == "vivareport":
        print(runner.export_viva_report())
        return
    launch_phase41_showcase_gui(base_dir, db_path)
