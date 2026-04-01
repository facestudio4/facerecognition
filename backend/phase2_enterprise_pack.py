import csv
import io
import json
import os
import sqlite3
import tkinter as tk
import zipfile
from datetime import datetime, timedelta
from tkinter import filedialog, messagebox, ttk


class AutoClosingConnection(sqlite3.Connection):
    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            return super().__exit__(exc_type, exc_val, exc_tb)
        finally:
            self.close()


class EnterpriseControlCenter:
    def __init__(self, base_dir: str, db_path: str):
        self.base_dir = base_dir
        self.db_path = db_path
        self._ensure_schema()

    def _connect(self):
        conn = sqlite3.connect(self.db_path, factory=AutoClosingConnection)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _ensure_schema(self):
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS role_permissions (
                    role TEXT NOT NULL,
                    action_key TEXT NOT NULL,
                    allowed INTEGER NOT NULL,
                    updated_at TEXT,
                    PRIMARY KEY(role, action_key)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS approval_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    requested_by TEXT,
                    requested_at TEXT,
                    reviewed_by TEXT,
                    reviewed_at TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS scheduled_jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_name TEXT UNIQUE NOT NULL,
                    interval_minutes INTEGER NOT NULL,
                    enabled INTEGER NOT NULL,
                    last_run TEXT,
                    next_run TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS model_registry (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_name TEXT NOT NULL,
                    model_version TEXT NOT NULL,
                    metrics_json TEXT,
                    created_at TEXT,
                    active INTEGER NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_approval_status ON approval_requests(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_enabled_next ON scheduled_jobs(enabled, next_run)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_model_active ON model_registry(active)")
            self._seed_defaults(conn)
            conn.commit()

    def _seed_defaults(self, conn):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        defaults = {
            "admin": {
                "manage_users": 1,
                "manage_permissions": 1,
                "approve_requests": 1,
                "run_scheduler": 1,
                "manage_models": 1,
                "export_evidence": 1,
            },
            "user": {
                "manage_users": 0,
                "manage_permissions": 0,
                "approve_requests": 0,
                "run_scheduler": 0,
                "manage_models": 0,
                "export_evidence": 0,
            },
        }
        for role, actions in defaults.items():
            for action_key, allowed in actions.items():
                conn.execute(
                    """
                    INSERT OR IGNORE INTO role_permissions(role, action_key, allowed, updated_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (role, action_key, allowed, now),
                )

        jobs = [
            ("nightly_backup", 1440, 1),
            ("daily_integrity_check", 1440, 1),
            ("weekly_report_build", 10080, 1),
            ("hourly_anomaly_scan", 60, 1),
        ]
        for name, interval, enabled in jobs:
            row = conn.execute("SELECT id FROM scheduled_jobs WHERE job_name=?", (name,)).fetchone()
            if row:
                continue
            next_run = (datetime.now() + timedelta(minutes=interval)).strftime("%Y-%m-%d %H:%M:%S")
            conn.execute(
                """
                INSERT INTO scheduled_jobs(job_name, interval_minutes, enabled, last_run, next_run)
                VALUES (?, ?, ?, ?, ?)
                """,
                (name, interval, enabled, None, next_run),
            )

        model_row = conn.execute("SELECT id FROM model_registry WHERE active=1 LIMIT 1").fetchone()
        if not model_row:
            conn.execute(
                """
                INSERT INTO model_registry(model_name, model_version, metrics_json, created_at, active)
                VALUES (?, ?, ?, ?, 1)
                """,
                (
                    "Face Studio Core",
                    "v2.0",
                    json.dumps({"threshold": 0.363, "avg_latency_ms": 82.4}, ensure_ascii=False),
                    now,
                ),
            )

    def get_permissions(self):
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT role, action_key, allowed, updated_at FROM role_permissions ORDER BY role, action_key"
            ).fetchall()
        out = {}
        for row in rows:
            role = row["role"]
            out.setdefault(role, {})
            out[role][row["action_key"]] = {
                "allowed": bool(row["allowed"]),
                "updated_at": row["updated_at"],
            }
        return out

    def set_permission(self, role: str, action_key: str, allowed: bool):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO role_permissions(role, action_key, allowed, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(role, action_key) DO UPDATE SET
                    allowed=excluded.allowed,
                    updated_at=excluded.updated_at
                """,
                (role, action_key, 1 if allowed else 0, now),
            )
            conn.commit()

    def submit_request(self, request_type: str, payload: dict, requested_by: str):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO approval_requests(request_type, payload_json, status, requested_by, requested_at, reviewed_by, reviewed_at)
                VALUES (?, ?, 'pending', ?, ?, NULL, NULL)
                """,
                (request_type, json.dumps(payload, ensure_ascii=False), requested_by, now),
            )
            conn.commit()

    def list_requests(self, status: str | None = None):
        with self._connect() as conn:
            if status:
                rows = conn.execute(
                    """
                    SELECT id, request_type, payload_json, status, requested_by, requested_at, reviewed_by, reviewed_at
                    FROM approval_requests
                    WHERE status=?
                    ORDER BY id DESC
                    """,
                    (status,),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT id, request_type, payload_json, status, requested_by, requested_at, reviewed_by, reviewed_at
                    FROM approval_requests
                    ORDER BY id DESC
                    """
                ).fetchall()
        out = []
        for r in rows:
            payload = {}
            try:
                payload = json.loads(r["payload_json"])
            except (json.JSONDecodeError, TypeError):
                payload = {"raw": r["payload_json"]}
            out.append(
                {
                    "id": r["id"],
                    "request_type": r["request_type"],
                    "payload": payload,
                    "status": r["status"],
                    "requested_by": r["requested_by"],
                    "requested_at": r["requested_at"],
                    "reviewed_by": r["reviewed_by"],
                    "reviewed_at": r["reviewed_at"],
                }
            )
        return out

    def review_request(self, request_id: int, approved: bool, reviewer: str):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_status = "approved" if approved else "rejected"
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE approval_requests
                SET status=?, reviewed_by=?, reviewed_at=?
                WHERE id=?
                """,
                (new_status, reviewer, now, request_id),
            )
            conn.commit()

    def list_jobs(self):
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, job_name, interval_minutes, enabled, last_run, next_run FROM scheduled_jobs ORDER BY id"
            ).fetchall()
        return [dict(r) for r in rows]

    def toggle_job(self, job_id: int, enabled: bool):
        with self._connect() as conn:
            conn.execute("UPDATE scheduled_jobs SET enabled=? WHERE id=?", (1 if enabled else 0, job_id))
            conn.commit()

    def run_due_jobs(self):
        now = datetime.now()
        now_s = now.strftime("%Y-%m-%d %H:%M:%S")
        executed = []
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, job_name, interval_minutes, enabled, last_run, next_run
                FROM scheduled_jobs
                WHERE enabled=1 AND (next_run IS NULL OR next_run<=?)
                ORDER BY id
                """,
                (now_s,),
            ).fetchall()
            for r in rows:
                nxt = (now + timedelta(minutes=int(r["interval_minutes"]))).strftime("%Y-%m-%d %H:%M:%S")
                conn.execute(
                    "UPDATE scheduled_jobs SET last_run=?, next_run=? WHERE id=?",
                    (now_s, nxt, r["id"]),
                )
                payload = {
                    "time": now_s,
                    "user": "scheduler",
                    "role": "system",
                    "action": "Scheduled Job",
                    "detail": f"Executed {r['job_name']}",
                }
                conn.execute(
                    """
                    INSERT INTO activity_events(event_time, username, role, action, detail, payload_json)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (now_s, "scheduler", "system", "Scheduled Job", f"Executed {r['job_name']}", json.dumps(payload, ensure_ascii=False)),
                )
                executed.append(r["job_name"])
            conn.commit()
        return executed

    def register_model(self, model_name: str, model_version: str, metrics: dict, activate: bool):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._connect() as conn:
            if activate:
                conn.execute("UPDATE model_registry SET active=0")
            conn.execute(
                """
                INSERT INTO model_registry(model_name, model_version, metrics_json, created_at, active)
                VALUES (?, ?, ?, ?, ?)
                """,
                (model_name, model_version, json.dumps(metrics, ensure_ascii=False), now, 1 if activate else 0),
            )
            conn.commit()

    def list_models(self):
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, model_name, model_version, metrics_json, created_at, active FROM model_registry ORDER BY id DESC"
            ).fetchall()
        out = []
        for r in rows:
            metrics = {}
            try:
                metrics = json.loads(r["metrics_json"] or "{}")
            except (json.JSONDecodeError, TypeError):
                metrics = {}
            out.append(
                {
                    "id": r["id"],
                    "model_name": r["model_name"],
                    "model_version": r["model_version"],
                    "metrics": metrics,
                    "created_at": r["created_at"],
                    "active": bool(r["active"]),
                }
            )
        return out

    def generate_evidence_pack(self, out_zip_path: str):
        os.makedirs(os.path.dirname(out_zip_path) or self.base_dir, exist_ok=True)
        with self._connect() as conn:
            users = conn.execute("SELECT username, email, phone, role, created FROM users ORDER BY username").fetchall()
            face_events = conn.execute("SELECT id, name, distance, event_time FROM face_events ORDER BY id").fetchall()
            activity = conn.execute("SELECT id, event_time, username, role, action, detail FROM activity_events ORDER BY id").fetchall()
            approvals = conn.execute("SELECT id, request_type, status, requested_by, requested_at, reviewed_by, reviewed_at FROM approval_requests ORDER BY id").fetchall()
            jobs = conn.execute("SELECT id, job_name, interval_minutes, enabled, last_run, next_run FROM scheduled_jobs ORDER BY id").fetchall()
            models = conn.execute("SELECT id, model_name, model_version, created_at, active FROM model_registry ORDER BY id").fetchall()

        stats = {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "users": len(users),
            "face_events": len(face_events),
            "activity_events": len(activity),
            "approval_requests": len(approvals),
            "scheduled_jobs": len(jobs),
            "models": len(models),
        }

        def to_csv(rows, headers):
            buf = io.StringIO()
            w = csv.writer(buf)
            w.writerow(headers)
            for r in rows:
                w.writerow([r[h] for h in headers])
            return buf.getvalue().encode("utf-8")

        with zipfile.ZipFile(out_zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
            z.writestr("summary.json", json.dumps(stats, indent=2, ensure_ascii=False).encode("utf-8"))
            z.writestr("users.csv", to_csv(users, ["username", "email", "phone", "role", "created"]))
            z.writestr("face_events.csv", to_csv(face_events, ["id", "name", "distance", "event_time"]))
            z.writestr("activity_events.csv", to_csv(activity, ["id", "event_time", "username", "role", "action", "detail"]))
            z.writestr("approval_requests.csv", to_csv(approvals, ["id", "request_type", "status", "requested_by", "requested_at", "reviewed_by", "reviewed_at"]))
            z.writestr("scheduled_jobs.csv", to_csv(jobs, ["id", "job_name", "interval_minutes", "enabled", "last_run", "next_run"]))
            z.writestr("model_registry.csv", to_csv(models, ["id", "model_name", "model_version", "created_at", "active"]))

        return out_zip_path



def launch_enterprise_control_center(base_dir: str, db_path: str, parent=None, on_close_callback=None):
    ecc = EnterpriseControlCenter(base_dir, db_path)
    if parent is None:
        win = tk.Tk()
        standalone = True
    else:
        win = tk.Toplevel(parent)
        standalone = False

    win.title("Face Studio Enterprise Control Center")
    win.geometry("1140x760")
    win.configure(bg="#0f1430")

    tk.Label(win, text="Enterprise Control Center", font=("Segoe UI", 24, "bold"), fg="#ff6f91", bg="#0f1430").pack(anchor="w", padx=14, pady=(12, 2))
    tk.Label(win, text="Permissions, approvals, scheduler, model registry, evidence pack", font=("Segoe UI", 11), fg="#90b7ff", bg="#0f1430").pack(anchor="w", padx=14, pady=(0, 8))

    status_var = tk.StringVar(value="Ready")
    button_style = {"font": ("Segoe UI", 9, "bold"), "padx": 10, "pady": 4}

    cards_frame = tk.Frame(win, bg="#0f1430")
    cards_frame.pack(fill="x", padx=12, pady=(2, 8))
    metric_vars = {
        "permissions": tk.StringVar(value="0"),
        "pending": tk.StringVar(value="0"),
        "jobs": tk.StringVar(value="0"),
        "active_models": tk.StringVar(value="0"),
    }
    metric_defs = [
        ("Permission Rules", "permissions"),
        ("Pending Approvals", "pending"),
        ("Scheduled Jobs", "jobs"),
        ("Active Models", "active_models"),
    ]
    for idx, (label, key) in enumerate(metric_defs):
        card = tk.Frame(cards_frame, bg="#121a44", bd=1, relief="solid", highlightbackground="#32428e", highlightthickness=1)
        card.grid(row=0, column=idx, sticky="nsew", padx=5)
        tk.Label(card, text=label, font=("Segoe UI", 9, "bold"), fg="#9cb3ff", bg="#121a44").pack(anchor="w", padx=8, pady=(6, 2))
        tk.Label(card, textvariable=metric_vars[key], font=("Segoe UI", 16, "bold"), fg="#f3f7ff", bg="#121a44").pack(anchor="w", padx=8, pady=(0, 8))
    for idx in range(4):
        cards_frame.grid_columnconfigure(idx, weight=1)

    notebook = ttk.Notebook(win)
    notebook.pack(fill="both", expand=True, padx=12, pady=8)

    tab_perm = tk.Frame(notebook, bg="#151b45")
    tab_approval = tk.Frame(notebook, bg="#151b45")
    tab_jobs = tk.Frame(notebook, bg="#151b45")
    tab_models = tk.Frame(notebook, bg="#151b45")
    tab_evidence = tk.Frame(notebook, bg="#151b45")

    notebook.add(tab_perm, text="Permissions")
    notebook.add(tab_approval, text="Approvals")
    notebook.add(tab_jobs, text="Scheduler")
    notebook.add(tab_models, text="Models")
    notebook.add(tab_evidence, text="Evidence")

    perm_box = tk.Frame(tab_perm, bg="#151b45")
    perm_box.pack(fill="both", expand=True, padx=10, pady=10)
    perm_tree = ttk.Treeview(perm_box, columns=("Role", "Action", "Allowed", "Updated"), show="headings", height=22)
    for col in ("Role", "Action", "Allowed", "Updated"):
        perm_tree.heading(col, text=col)
        perm_tree.column(col, width=220 if col == "Action" else 160, anchor="center")
    perm_tree.pack(side="left", fill="both", expand=True)
    perm_scroll = ttk.Scrollbar(perm_box, orient="vertical", command=perm_tree.yview)
    perm_scroll.pack(side="right", fill="y")
    perm_tree.configure(yscrollcommand=perm_scroll.set)

    def refresh_permissions():
        for i in perm_tree.get_children():
            perm_tree.delete(i)
        data = ecc.get_permissions()
        total = 0
        for role, actions in data.items():
            for action, meta in actions.items():
                perm_tree.insert("", "end", values=(role, action, "Yes" if meta["allowed"] else "No", meta["updated_at"]))
                total += 1
        metric_vars["permissions"].set(str(total))

    perm_controls = tk.Frame(tab_perm, bg="#151b45")
    perm_controls.pack(fill="x", padx=10, pady=(0, 10))

    role_var = tk.StringVar(value="user")
    action_var = tk.StringVar(value="export_evidence")
    allow_var = tk.BooleanVar(value=True)

    tk.Label(perm_controls, text="Role", bg="#151b45", fg="#d3e2ff").pack(side="left", padx=5)
    ttk.Combobox(perm_controls, textvariable=role_var, values=["admin", "user"], width=10).pack(side="left", padx=5)
    tk.Label(perm_controls, text="Action", bg="#151b45", fg="#d3e2ff").pack(side="left", padx=5)
    ttk.Combobox(
        perm_controls,
        textvariable=action_var,
        values=["manage_users", "manage_permissions", "approve_requests", "run_scheduler", "manage_models", "export_evidence"],
        width=20,
    ).pack(side="left", padx=5)
    tk.Checkbutton(perm_controls, text="Allowed", variable=allow_var, bg="#151b45", fg="#d3e2ff", selectcolor="#151b45").pack(side="left", padx=8)

    def apply_permission():
        ecc.set_permission(role_var.get().strip(), action_var.get().strip(), allow_var.get())
        refresh_permissions()
        status_var.set("Permission updated")

    tk.Button(perm_controls, text="Apply", command=apply_permission, bg="#3050d3", fg="white", **button_style).pack(side="left", padx=8)

    approval_box = tk.Frame(tab_approval, bg="#151b45")
    approval_box.pack(fill="both", expand=True, padx=10, pady=10)
    approval_tree = ttk.Treeview(approval_box, columns=("ID", "Type", "Status", "By", "Requested", "ReviewedBy"), show="headings", height=22)
    for col in ("ID", "Type", "Status", "By", "Requested", "ReviewedBy"):
        approval_tree.heading(col, text=col)
        approval_tree.column(col, width=150 if col != "Type" else 220, anchor="center")
    approval_tree.pack(side="left", fill="both", expand=True)
    approval_scroll = ttk.Scrollbar(approval_box, orient="vertical", command=approval_tree.yview)
    approval_scroll.pack(side="right", fill="y")
    approval_tree.configure(yscrollcommand=approval_scroll.set)

    req_type_var = tk.StringVar(value="delete_user")
    req_payload_var = tk.StringVar(value='{"target":"demo_user"}')
    req_by_var = tk.StringVar(value="admin")

    approval_controls = tk.Frame(tab_approval, bg="#151b45")
    approval_controls.pack(fill="x", padx=10, pady=(0, 10))
    tk.Label(approval_controls, text="Type", bg="#151b45", fg="#d3e2ff").pack(side="left", padx=4)
    ttk.Combobox(approval_controls, textvariable=req_type_var, values=["delete_user", "reset_password", "data_export", "model_activate"], width=14).pack(side="left", padx=4)
    tk.Label(approval_controls, text="Payload JSON", bg="#151b45", fg="#d3e2ff").pack(side="left", padx=4)
    tk.Entry(approval_controls, textvariable=req_payload_var, width=44).pack(side="left", padx=4)
    tk.Label(approval_controls, text="By", bg="#151b45", fg="#d3e2ff").pack(side="left", padx=4)
    tk.Entry(approval_controls, textvariable=req_by_var, width=12).pack(side="left", padx=4)

    def submit_req():
        try:
            payload = json.loads(req_payload_var.get().strip() or "{}")
        except json.JSONDecodeError:
            messagebox.showerror("Invalid", "Payload must be valid JSON", parent=win)
            return
        ecc.submit_request(req_type_var.get().strip(), payload, req_by_var.get().strip())
        refresh_approvals()
        status_var.set("Approval request submitted")

    def refresh_approvals():
        for i in approval_tree.get_children():
            approval_tree.delete(i)
        rows = ecc.list_requests()
        pending = 0
        for r in rows:
            approval_tree.insert("", "end", values=(r["id"], r["request_type"], r["status"], r["requested_by"], r["requested_at"], r["reviewed_by"] or ""))
            if (r.get("status") or "").lower() == "pending":
                pending += 1
        metric_vars["pending"].set(str(pending))

    def review_selected(approved: bool):
        selected = approval_tree.selection()
        if not selected:
            return
        item = approval_tree.item(selected[0])["values"]
        rid = int(item[0])
        ecc.review_request(rid, approved, "admin")
        refresh_approvals()
        status_var.set("Request reviewed")

    tk.Button(approval_controls, text="Submit", command=submit_req, bg="#3050d3", fg="white", **button_style).pack(side="left", padx=6)
    tk.Button(approval_controls, text="Approve Selected", command=lambda: review_selected(True), bg="#0f8c62", fg="white", **button_style).pack(side="left", padx=6)
    tk.Button(approval_controls, text="Reject Selected", command=lambda: review_selected(False), bg="#b03a2e", fg="white", **button_style).pack(side="left", padx=6)

    jobs_box = tk.Frame(tab_jobs, bg="#151b45")
    jobs_box.pack(fill="both", expand=True, padx=10, pady=10)
    jobs_tree = ttk.Treeview(jobs_box, columns=("ID", "Job", "IntervalMin", "Enabled", "LastRun", "NextRun"), show="headings", height=22)
    for col in ("ID", "Job", "IntervalMin", "Enabled", "LastRun", "NextRun"):
        jobs_tree.heading(col, text=col)
        jobs_tree.column(col, width=160 if col in ("Job", "LastRun", "NextRun") else 110, anchor="center")
    jobs_tree.pack(side="left", fill="both", expand=True)
    jobs_scroll = ttk.Scrollbar(jobs_box, orient="vertical", command=jobs_tree.yview)
    jobs_scroll.pack(side="right", fill="y")
    jobs_tree.configure(yscrollcommand=jobs_scroll.set)

    jobs_controls = tk.Frame(tab_jobs, bg="#151b45")
    jobs_controls.pack(fill="x", padx=10, pady=(0, 10))

    def refresh_jobs():
        for i in jobs_tree.get_children():
            jobs_tree.delete(i)
        count = 0
        for j in ecc.list_jobs():
            jobs_tree.insert("", "end", values=(j["id"], j["job_name"], j["interval_minutes"], "Yes" if j["enabled"] else "No", j["last_run"] or "", j["next_run"] or ""))
            count += 1
        metric_vars["jobs"].set(str(count))

    def toggle_selected_job():
        selected = jobs_tree.selection()
        if not selected:
            return
        vals = jobs_tree.item(selected[0])["values"]
        job_id = int(vals[0])
        enabled_now = vals[3] == "Yes"
        ecc.toggle_job(job_id, not enabled_now)
        refresh_jobs()
        status_var.set("Job toggled")

    def run_due():
        jobs = ecc.run_due_jobs()
        refresh_jobs()
        status_var.set("Executed jobs: " + (", ".join(jobs) if jobs else "none"))

    tk.Button(jobs_controls, text="Toggle Selected", command=toggle_selected_job, bg="#3258d6", fg="white", **button_style).pack(side="left", padx=6)
    tk.Button(jobs_controls, text="Run Due Jobs", command=run_due, bg="#0f8c62", fg="white", **button_style).pack(side="left", padx=6)

    models_box = tk.Frame(tab_models, bg="#151b45")
    models_box.pack(fill="both", expand=True, padx=10, pady=10)
    models_tree = ttk.Treeview(models_box, columns=("ID", "Name", "Version", "Created", "Active"), show="headings", height=20)
    for col in ("ID", "Name", "Version", "Created", "Active"):
        models_tree.heading(col, text=col)
        models_tree.column(col, width=180 if col in ("Name", "Created") else 120, anchor="center")
    models_tree.pack(side="left", fill="both", expand=True)
    models_scroll = ttk.Scrollbar(models_box, orient="vertical", command=models_tree.yview)
    models_scroll.pack(side="right", fill="y")
    models_tree.configure(yscrollcommand=models_scroll.set)

    model_controls = tk.Frame(tab_models, bg="#151b45")
    model_controls.pack(fill="x", padx=10, pady=(0, 10))

    model_name_var = tk.StringVar(value="Face Studio Core")
    model_version_var = tk.StringVar(value="v2.1")
    model_metrics_var = tk.StringVar(value='{"threshold":0.36,"avg_latency_ms":79.2}')
    model_active_var = tk.BooleanVar(value=True)

    tk.Entry(model_controls, textvariable=model_name_var, width=26).pack(side="left", padx=5)
    tk.Entry(model_controls, textvariable=model_version_var, width=12).pack(side="left", padx=5)
    tk.Entry(model_controls, textvariable=model_metrics_var, width=36).pack(side="left", padx=5)
    tk.Checkbutton(model_controls, text="Set Active", variable=model_active_var, bg="#151b45", fg="#d3e2ff", selectcolor="#151b45").pack(side="left", padx=5)

    def refresh_models():
        for i in models_tree.get_children():
            models_tree.delete(i)
        active = 0
        for m in ecc.list_models():
            models_tree.insert("", "end", values=(m["id"], m["model_name"], m["model_version"], m["created_at"], "Yes" if m["active"] else "No"))
            if m["active"]:
                active += 1
        metric_vars["active_models"].set(str(active))

    def add_model():
        try:
            metrics = json.loads(model_metrics_var.get().strip() or "{}")
        except json.JSONDecodeError:
            messagebox.showerror("Invalid", "Metrics must be valid JSON", parent=win)
            return
        ecc.register_model(model_name_var.get().strip(), model_version_var.get().strip(), metrics, model_active_var.get())
        refresh_models()
        status_var.set("Model registered")

    tk.Button(model_controls, text="Register Model", command=add_model, bg="#3050d3", fg="white", **button_style).pack(side="left", padx=6)

    evidence_panel = tk.Frame(tab_evidence, bg="#151b45")
    evidence_panel.pack(fill="both", expand=True, padx=12, pady=12)

    ev_text = tk.Text(evidence_panel, bg="#0f1430", fg="#d7e2ff", font=("Consolas", 10), height=26)
    ev_text.pack(side="left", fill="both", expand=True)
    ev_scroll = ttk.Scrollbar(evidence_panel, orient="vertical", command=ev_text.yview)
    ev_scroll.pack(side="right", fill="y")
    ev_text.configure(yscrollcommand=ev_scroll.set)

    def build_evidence():
        out = filedialog.asksaveasfilename(
            title="Save Evidence Pack",
            defaultextension=".zip",
            filetypes=[("ZIP", "*.zip")],
            initialfile="face_studio_evidence_pack.zip",
        )
        if not out:
            return
        path = ecc.generate_evidence_pack(out)
        ev_text.delete("1.0", "end")
        ev_text.insert("end", f"Evidence pack created:\n{path}\n")
        status_var.set("Evidence pack generated")

    tk.Button(evidence_panel, text="Generate Evidence Pack", command=build_evidence, bg="#0f8c62", fg="white", **button_style).pack(anchor="w", pady=(0, 10))

    refresh_permissions()
    refresh_approvals()
    refresh_jobs()
    refresh_models()

    tk.Label(win, textvariable=status_var, font=("Segoe UI", 10), fg="#7ad0ff", bg="#0f1430").pack(anchor="w", padx=14, pady=(0, 10))

    def on_close():
        win.destroy()
        if on_close_callback:
            on_close_callback()

    win.protocol("WM_DELETE_WINDOW", on_close)
    if standalone:
        win.mainloop()



def run_enterprise_cli(base_dir: str, db_path: str, command: str):
    ecc = EnterpriseControlCenter(base_dir, db_path)
    if command == "runjobs":
        out = ecc.run_due_jobs()
        print(json.dumps({"executed_jobs": out}, indent=2))
        return
    if command == "evidencepack":
        path = os.path.join(base_dir, "face_studio_evidence_pack.zip")
        print(ecc.generate_evidence_pack(path))
        return
    print(json.dumps({
        "permissions": ecc.get_permissions(),
        "jobs": ecc.list_jobs(),
        "models": ecc.list_models(),
        "pending_requests": ecc.list_requests("pending"),
    }, indent=2))
