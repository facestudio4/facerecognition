import csv
import json
import os
import random
import sqlite3
import statistics
import string
import time
import tkinter as tk
from datetime import datetime, timedelta
from tkinter import filedialog, messagebox, ttk


class AutoClosingConnection(sqlite3.Connection):
    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            return super().__exit__(exc_type, exc_val, exc_tb)
        finally:
            self.close()


class AdvancedProjectPack:
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
                CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY,
                    password TEXT,
                    email TEXT,
                    phone TEXT,
                    role TEXT,
                    created TEXT,
                    logins_json TEXT,
                    verified_email INTEGER,
                    data_json TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS face_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    distance REAL,
                    event_time TEXT,
                    payload_json TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS activity_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_time TEXT,
                    username TEXT,
                    role TEXT,
                    action TEXT,
                    detail TEXT,
                    payload_json TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS attendance_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    payload_json TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS app_settings (
                    setting_key TEXT PRIMARY KEY,
                    value_json TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS project_meta (
                    meta_key TEXT PRIMARY KEY,
                    meta_value TEXT
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_face_time ON face_events(event_time)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_face_name ON face_events(name)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_activity_time ON activity_events(event_time)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_activity_user ON activity_events(username)")
            conn.commit()

    def database_stats(self):
        with self._connect() as conn:
            users = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
            faces = conn.execute("SELECT COUNT(*) AS c FROM face_events").fetchone()["c"]
            activity = conn.execute("SELECT COUNT(*) AS c FROM activity_events").fetchone()["c"]
            attendance = conn.execute("SELECT COUNT(*) AS c FROM attendance_entries").fetchone()["c"]
            admins = conn.execute("SELECT COUNT(*) AS c FROM users WHERE lower(role)='admin'").fetchone()["c"]
            distinct_people = conn.execute("SELECT COUNT(DISTINCT name) AS c FROM face_events").fetchone()["c"]
            avg_score_row = conn.execute("SELECT AVG(distance) AS a FROM face_events").fetchone()
            avg_score = float(avg_score_row["a"] or 0.0)
        db_size = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
        return {
            "users": users,
            "admins": admins,
            "face_events": faces,
            "activity_events": activity,
            "attendance_entries": attendance,
            "distinct_people": distinct_people,
            "avg_similarity": round(avg_score, 4),
            "db_size_mb": round(db_size / (1024 * 1024), 3),
        }

    def integrity_check(self):
        with self._connect() as conn:
            quick = conn.execute("PRAGMA quick_check").fetchone()[0]
            full = conn.execute("PRAGMA integrity_check").fetchone()[0]
            fk = conn.execute("PRAGMA foreign_key_check").fetchall()
        return {
            "quick_check": quick,
            "integrity_check": full,
            "foreign_key_violations": len(fk),
            "ok": quick == "ok" and full == "ok" and len(fk) == 0,
        }

    def optimize_database(self):
        with self._connect() as conn:
            conn.execute("ANALYZE")
            conn.execute("PRAGMA optimize")
            conn.execute("VACUUM")
            conn.commit()

    def backup_database(self, out_dir: str):
        os.makedirs(out_dir, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = os.path.join(out_dir, f"facestudio_backup_{stamp}.db")
        with self._connect() as source:
            with sqlite3.connect(out_path, factory=AutoClosingConnection) as dest:
                source.backup(dest)
        return out_path

    def restore_database(self, backup_path: str):
        if not os.path.exists(backup_path):
            raise FileNotFoundError("Backup file not found")
        with sqlite3.connect(backup_path, factory=AutoClosingConnection) as source:
            with sqlite3.connect(self.db_path, factory=AutoClosingConnection) as dest:
                source.backup(dest)
        self._ensure_schema()

    def _random_name(self):
        names = [
            "Aarav", "Vihaan", "Aditya", "Ishaan", "Arjun", "Kabir", "Reyansh", "Atharv", "Dhruv", "Kiaan",
            "Anaya", "Myra", "Diya", "Aadhya", "Pari", "Sara", "Kiara", "Riya", "Ira", "Avni",
        ]
        return random.choice(names) + str(random.randint(10, 999))

    def _random_email(self, username: str):
        domains = ["gmail.com", "outlook.com", "icloud.com", "student.edu", "example.org"]
        return f"{username.lower()}@{random.choice(domains)}"

    def _random_phone(self):
        return "+91" + "".join(random.choice(string.digits) for _ in range(10))

    def seed_demo_data(self, users=80, face_events=12000, activity_events=7000, attendance_entries=900):
        with self._connect() as conn:
            existing = conn.execute("SELECT username FROM users").fetchall()
            existing_names = {row["username"] for row in existing}

            new_users = []
            for _ in range(users):
                username = self._random_name()
                while username in existing_names:
                    username = self._random_name()
                existing_names.add(username)
                created = (datetime.now() - timedelta(days=random.randint(1, 600))).strftime("%Y-%m-%d %H:%M:%S")
                role = "admin" if random.random() < 0.04 else "user"
                logins = [
                    (datetime.now() - timedelta(days=random.randint(0, 120), minutes=random.randint(0, 1440))).strftime("%Y-%m-%d %H:%M:%S")
                    for _ in range(random.randint(1, 18))
                ]
                payload = {
                    "department": random.choice(["CSE", "ECE", "ME", "CE", "BBA", "MCA"]),
                    "year": random.choice([1, 2, 3, 4]),
                    "status": random.choice(["active", "active", "active", "inactive"]),
                }
                new_users.append(
                    (
                        username,
                        "seeded_hash_" + hashlib_like(username),
                        self._random_email(username),
                        self._random_phone(),
                        role,
                        created,
                        json.dumps(logins, ensure_ascii=False),
                        1,
                        json.dumps(payload, ensure_ascii=False),
                    )
                )

            conn.executemany(
                """
                INSERT INTO users(username, password, email, phone, role, created, logins_json, verified_email, data_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(username) DO UPDATE SET
                    email=excluded.email,
                    phone=excluded.phone,
                    role=excluded.role,
                    created=excluded.created,
                    logins_json=excluded.logins_json,
                    verified_email=excluded.verified_email,
                    data_json=excluded.data_json
                """,
                new_users,
            )

            known_names = [row["username"] for row in conn.execute("SELECT username FROM users").fetchall()]

            fe_rows = []
            now = datetime.now()
            for _ in range(face_events):
                name = random.choice(known_names + ["Unknown"] * 2)
                score = random.uniform(0.25, 0.98)
                ts = (now - timedelta(days=random.randint(0, 90), seconds=random.randint(0, 86400))).strftime("%Y-%m-%d %H:%M:%S")
                payload = {"name": name, "distance": round(score, 4), "time": ts}
                fe_rows.append((name, score, ts, json.dumps(payload, ensure_ascii=False)))

            conn.executemany(
                "INSERT INTO face_events(name, distance, event_time, payload_json) VALUES (?, ?, ?, ?)",
                fe_rows,
            )

            actions = [
                "Login", "Logout", "Generate Face", "Compare Faces", "Attendance Marked",
                "Settings Changed", "Password Changed", "Export CSV", "Model Retrain",
            ]
            ac_rows = []
            for _ in range(activity_events):
                uname = random.choice(known_names)
                role_row = conn.execute("SELECT role FROM users WHERE username=?", (uname,)).fetchone()
                role = role_row["role"] if role_row else "user"
                action = random.choice(actions)
                detail = random.choice([
                    "From desktop client", "Batch execution", "From analytics panel", "User initiated",
                    "Automated schedule", "Manual trigger",
                ])
                ts = (now - timedelta(days=random.randint(0, 120), seconds=random.randint(0, 86400))).strftime("%Y-%m-%d %H:%M:%S")
                payload = {"time": ts, "user": uname, "role": role, "action": action, "detail": detail}
                ac_rows.append((ts, uname, role, action, detail, json.dumps(payload, ensure_ascii=False)))

            conn.executemany(
                "INSERT INTO activity_events(event_time, username, role, action, detail, payload_json) VALUES (?, ?, ?, ?, ?, ?)",
                ac_rows,
            )

            at_rows = []
            for _ in range(attendance_entries):
                marked = random.sample(known_names, k=min(len(known_names), random.randint(1, 12)))
                entry = {
                    "date": (now - timedelta(days=random.randint(0, 120))).strftime("%Y-%m-%d"),
                    "time_start": f"{random.randint(8, 11):02d}:{random.randint(0, 59):02d}:{random.randint(0, 59):02d}",
                    "present": marked,
                    "count": len(marked),
                }
                at_rows.append((json.dumps(entry, ensure_ascii=False),))

            conn.executemany("INSERT INTO attendance_entries(payload_json) VALUES (?)", at_rows)
            conn.commit()

        return {
            "users_seeded": len(new_users),
            "face_events_seeded": len(fe_rows),
            "activity_events_seeded": len(ac_rows),
            "attendance_seeded": len(at_rows),
        }

    def query_benchmark(self, rounds=80):
        durations = {}

        def run(name, fn):
            start = time.perf_counter()
            for _ in range(rounds):
                fn()
            end = time.perf_counter()
            durations[name] = round((end - start) * 1000 / rounds, 4)

        with self._connect() as conn:
            run("count_users", lambda: conn.execute("SELECT COUNT(*) FROM users").fetchone())
            run("lookup_email", lambda: conn.execute("SELECT username FROM users WHERE email IS NOT NULL LIMIT 1").fetchone())
            run("latest_face_events", lambda: conn.execute("SELECT id, name, distance FROM face_events ORDER BY id DESC LIMIT 50").fetchall())
            run("latest_activity", lambda: conn.execute("SELECT id, action, username FROM activity_events ORDER BY id DESC LIMIT 50").fetchall())
            run("top_people", lambda: conn.execute("SELECT name, COUNT(*) c FROM face_events GROUP BY name ORDER BY c DESC LIMIT 10").fetchall())
        return durations

    def anomaly_scan(self):
        issues = []
        with self._connect() as conn:
            dup_email = conn.execute(
                "SELECT email, COUNT(*) c FROM users WHERE email IS NOT NULL AND email!='' GROUP BY lower(email) HAVING c > 1"
            ).fetchall()
            dup_phone = conn.execute(
                "SELECT phone, COUNT(*) c FROM users WHERE phone IS NOT NULL AND phone!='' GROUP BY phone HAVING c > 1"
            ).fetchall()
            bad_scores = conn.execute(
                "SELECT COUNT(*) c FROM face_events WHERE distance < 0 OR distance > 1"
            ).fetchone()["c"]
            empty_actions = conn.execute(
                "SELECT COUNT(*) c FROM activity_events WHERE action IS NULL OR action=''"
            ).fetchone()["c"]

        if dup_email:
            issues.append(f"Duplicate emails: {len(dup_email)} groups")
        if dup_phone:
            issues.append(f"Duplicate phones: {len(dup_phone)} groups")
        if bad_scores:
            issues.append(f"Invalid similarity scores: {bad_scores}")
        if empty_actions:
            issues.append(f"Activity rows with empty action: {empty_actions}")
        if not issues:
            issues.append("No anomalies found")
        return issues

    def export_all_csv(self, out_dir: str):
        os.makedirs(out_dir, exist_ok=True)
        out = {}
        with self._connect() as conn:
            users_path = os.path.join(out_dir, "users_export.csv")
            with open(users_path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["username", "email", "phone", "role", "created", "verified_email"])
                for row in conn.execute("SELECT username, email, phone, role, created, verified_email FROM users ORDER BY username"):
                    w.writerow([row["username"], row["email"], row["phone"], row["role"], row["created"], row["verified_email"]])
            out["users"] = users_path

            face_path = os.path.join(out_dir, "face_events_export.csv")
            with open(face_path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["id", "name", "distance", "event_time"])
                for row in conn.execute("SELECT id, name, distance, event_time FROM face_events ORDER BY id"):
                    w.writerow([row["id"], row["name"], row["distance"], row["event_time"]])
            out["face_events"] = face_path

            activity_path = os.path.join(out_dir, "activity_events_export.csv")
            with open(activity_path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["id", "event_time", "username", "role", "action", "detail"])
                for row in conn.execute("SELECT id, event_time, username, role, action, detail FROM activity_events ORDER BY id"):
                    w.writerow([row["id"], row["event_time"], row["username"], row["role"], row["action"], row["detail"]])
            out["activity_events"] = activity_path

            attendance_path = os.path.join(out_dir, "attendance_export.csv")
            with open(attendance_path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["id", "payload_json"])
                for row in conn.execute("SELECT id, payload_json FROM attendance_entries ORDER BY id"):
                    w.writerow([row["id"], row["payload_json"]])
            out["attendance"] = attendance_path
        return out

    def generate_presentation_report(self, out_file: str):
        stats = self.database_stats()
        anomalies = self.anomaly_scan()
        benchmark = self.query_benchmark(rounds=50)
        with self._connect() as conn:
            top_people = conn.execute(
                "SELECT name, COUNT(*) c, AVG(distance) a FROM face_events GROUP BY name ORDER BY c DESC LIMIT 12"
            ).fetchall()
            top_actions = conn.execute(
                "SELECT action, COUNT(*) c FROM activity_events GROUP BY action ORDER BY c DESC LIMIT 12"
            ).fetchall()

        html = [
            "<html><head><meta charset='utf-8'><title>Face Studio Project Report</title>",
            "<style>body{font-family:Segoe UI,Arial;background:#0f1226;color:#f5f7ff;padding:24px}"
            "h1{color:#ff5b7f}h2{color:#7ad0ff}.card{background:#171c3a;padding:16px;border-radius:12px;margin:10px 0}"
            "table{width:100%;border-collapse:collapse}th,td{border:1px solid #2f376d;padding:8px;text-align:left}"
            "th{background:#222a5a} .grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}</style></head><body>",
            "<h1>Face Studio Mid-Term Project Report</h1>",
            f"<div class='card'><b>Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>",
            "<h2>Database Metrics</h2>",
            "<div class='grid'>",
        ]
        for k, v in stats.items():
            html.append(f"<div class='card'><b>{k.replace('_', ' ').title()}</b><br>{v}</div>")
        html.append("</div>")

        html.append("<h2>Query Benchmark (ms average)</h2><div class='card'><table><tr><th>Query</th><th>Time</th></tr>")
        for k, v in benchmark.items():
            html.append(f"<tr><td>{k}</td><td>{v}</td></tr>")
        html.append("</table></div>")

        html.append("<h2>Top Recognized People</h2><div class='card'><table><tr><th>Name</th><th>Events</th><th>Avg Similarity</th></tr>")
        for row in top_people:
            html.append(f"<tr><td>{row['name']}</td><td>{row['c']}</td><td>{round(float(row['a'] or 0),4)}</td></tr>")
        html.append("</table></div>")

        html.append("<h2>Top Activities</h2><div class='card'><table><tr><th>Action</th><th>Count</th></tr>")
        for row in top_actions:
            html.append(f"<tr><td>{row['action']}</td><td>{row['c']}</td></tr>")
        html.append("</table></div>")

        html.append("<h2>Anomaly Scan</h2><div class='card'><ul>")
        for a in anomalies:
            html.append(f"<li>{a}</li>")
        html.append("</ul></div>")

        html.append("</body></html>")
        os.makedirs(os.path.dirname(out_file) or self.base_dir, exist_ok=True)
        with open(out_file, "w", encoding="utf-8") as f:
            f.write("\n".join(html))
        return out_file


def hashlib_like(value: str):
    n = sum((i + 1) * ord(ch) for i, ch in enumerate(value))
    chars = "0123456789abcdef"
    out = []
    for i in range(64):
        out.append(chars[(n + i * 11 + (i % 7) * 3) % 16])
    return "".join(out)


def launch_advanced_lab(base_dir: str, db_path: str, parent=None, on_close_callback=None):
    pack = AdvancedProjectPack(base_dir, db_path)
    if parent is None:
        win = tk.Tk()
        standalone = True
    else:
        win = tk.Toplevel(parent)
        standalone = False

    win.title("Face Studio Advanced Project Lab")
    win.geometry("1120x760")
    win.configure(bg="#11152b")

    top = tk.Frame(win, bg="#11152b")
    top.pack(fill="x", padx=14, pady=10)
    tk.Label(top, text="Face Studio Advanced Project Lab", font=("Segoe UI", 22, "bold"), fg="#ff5b7f", bg="#11152b").pack(anchor="w")
    tk.Label(top, text="Mid-term presentation toolkit", font=("Segoe UI", 11), fg="#9cb3ff", bg="#11152b").pack(anchor="w")

    notebook = ttk.Notebook(win)
    notebook.pack(fill="both", expand=True, padx=12, pady=10)

    tab_overview = tk.Frame(notebook, bg="#171c3a")
    tab_data = tk.Frame(notebook, bg="#171c3a")
    tab_perf = tk.Frame(notebook, bg="#171c3a")
    tab_report = tk.Frame(notebook, bg="#171c3a")

    notebook.add(tab_overview, text="Overview")
    notebook.add(tab_data, text="Data Ops")
    notebook.add(tab_perf, text="Performance")
    notebook.add(tab_report, text="Reports")

    overview_scroll = tk.Canvas(tab_overview, bg="#171c3a", highlightthickness=0)
    overview_scroll.pack(fill="both", expand=True, padx=14, pady=14)
    overview_content = tk.Frame(overview_scroll, bg="#171c3a")
    overview_window = overview_scroll.create_window((0, 0), window=overview_content, anchor="nw")
    overview_bar = ttk.Scrollbar(tab_overview, orient="vertical", command=overview_scroll.yview)
    overview_bar.pack(side="right", fill="y", padx=(0, 14), pady=14)
    overview_scroll.configure(yscrollcommand=overview_bar.set)

    def _resize_overview(e):
        overview_scroll.configure(scrollregion=overview_scroll.bbox("all"))
        overview_scroll.itemconfigure(overview_window, width=e.width)

    overview_scroll.bind("<Configure>", _resize_overview)

    card_grid = tk.Frame(overview_content, bg="#171c3a")
    card_grid.pack(fill="x")

    card_vars = {
        "users": tk.StringVar(value="0"),
        "admins": tk.StringVar(value="0"),
        "face_events": tk.StringVar(value="0"),
        "activity_events": tk.StringVar(value="0"),
        "attendance_entries": tk.StringVar(value="0"),
        "distinct_people": tk.StringVar(value="0"),
        "avg_similarity": tk.StringVar(value="0"),
        "db_size_mb": tk.StringVar(value="0"),
    }
    card_titles = [
        ("Users", "users"),
        ("Admins", "admins"),
        ("Face Events", "face_events"),
        ("Activity Events", "activity_events"),
        ("Attendance", "attendance_entries"),
        ("Distinct People", "distinct_people"),
        ("Avg Similarity", "avg_similarity"),
        ("DB Size (MB)", "db_size_mb"),
    ]

    for idx, (title, key) in enumerate(card_titles):
        r = idx // 4
        c = idx % 4
        card = tk.Frame(card_grid, bg="#101735", bd=1, relief="solid", highlightbackground="#29356f", highlightthickness=1)
        card.grid(row=r, column=c, sticky="nsew", padx=6, pady=6)
        tk.Label(card, text=title, font=("Segoe UI", 9, "bold"), fg="#9cb3ff", bg="#101735").pack(anchor="w", padx=10, pady=(8, 2))
        tk.Label(card, textvariable=card_vars[key], font=("Segoe UI", 18, "bold"), fg="#f3f7ff", bg="#101735").pack(anchor="w", padx=10, pady=(0, 8))
    for c in range(4):
        card_grid.grid_columnconfigure(c, weight=1)

    integrity_box = tk.LabelFrame(overview_content, text="Integrity Snapshot", font=("Segoe UI", 10, "bold"), fg="#cddcff", bg="#171c3a")
    integrity_box.pack(fill="x", pady=(10, 0))
    integrity_lines_var = tk.StringVar(value="Loading integrity checks...")
    tk.Label(
        integrity_box,
        textvariable=integrity_lines_var,
        justify="left",
        anchor="w",
        font=("Consolas", 10),
        fg="#d7e2ff",
        bg="#171c3a",
    ).pack(fill="x", padx=10, pady=8)

    anomaly_box = tk.LabelFrame(overview_content, text="Anomaly Scan", font=("Segoe UI", 10, "bold"), fg="#cddcff", bg="#171c3a")
    anomaly_box.pack(fill="x", pady=(10, 0))
    anomaly_text = tk.Text(anomaly_box, bg="#0f1430", fg="#d7e2ff", font=("Consolas", 10), height=6, bd=0, highlightthickness=0)
    anomaly_text.pack(fill="x", padx=10, pady=8)

    insights_row = tk.Frame(overview_content, bg="#171c3a")
    insights_row.pack(fill="both", expand=True, pady=(10, 0))
    top_people_box = tk.LabelFrame(insights_row, text="Top Recognized People", font=("Segoe UI", 10, "bold"), fg="#cddcff", bg="#171c3a")
    top_people_box.pack(side="left", fill="both", expand=True, padx=(0, 6))
    top_action_box = tk.LabelFrame(insights_row, text="Top Actions", font=("Segoe UI", 10, "bold"), fg="#cddcff", bg="#171c3a")
    top_action_box.pack(side="left", fill="both", expand=True, padx=(6, 0))

    top_people_tree = ttk.Treeview(top_people_box, columns=("name", "events", "avg"), show="headings", height=8)
    top_people_tree.heading("name", text="Name")
    top_people_tree.heading("events", text="Events")
    top_people_tree.heading("avg", text="Avg Similarity")
    top_people_tree.column("name", width=170, anchor="w")
    top_people_tree.column("events", width=90, anchor="center")
    top_people_tree.column("avg", width=120, anchor="center")
    top_people_tree.pack(fill="both", expand=True, padx=8, pady=8)

    top_actions_tree = ttk.Treeview(top_action_box, columns=("action", "count"), show="headings", height=8)
    top_actions_tree.heading("action", text="Action")
    top_actions_tree.heading("count", text="Count")
    top_actions_tree.column("action", width=220, anchor="w")
    top_actions_tree.column("count", width=90, anchor="center")
    top_actions_tree.pack(fill="both", expand=True, padx=8, pady=8)

    status_var = tk.StringVar(value="Ready")
    tk.Label(win, textvariable=status_var, font=("Segoe UI", 10), fg="#7ad0ff", bg="#11152b").pack(anchor="w", padx=14, pady=(0, 8))

    def refresh_overview():
        stats = pack.database_stats()
        integrity = pack.integrity_check()
        anomalies = pack.anomaly_scan()
        for k, v in stats.items():
            if k in card_vars:
                card_vars[k].set(str(v))

        integrity_lines_var.set(
            "\n".join(
                [
                    f"Quick Check: {integrity.get('quick_check', 'n/a')}",
                    f"Integrity Check: {integrity.get('integrity_check', 'n/a')}",
                    f"Foreign Key Violations: {integrity.get('foreign_key_violations', 0)}",
                    f"Overall Status: {'PASS' if integrity.get('ok') else 'ATTENTION NEEDED'}",
                ]
            )
        )

        anomaly_text.configure(state="normal")
        anomaly_text.delete("1.0", "end")
        for item in anomalies:
            anomaly_text.insert("end", f"- {item}\n")
        anomaly_text.configure(state="disabled")

        for item in top_people_tree.get_children():
            top_people_tree.delete(item)
        for item in top_actions_tree.get_children():
            top_actions_tree.delete(item)

        with pack._connect() as conn:
            top_people = conn.execute(
                "SELECT COALESCE(name, 'Unknown') AS name, COUNT(*) AS c, AVG(distance) AS a FROM face_events "
                "GROUP BY COALESCE(name, 'Unknown') ORDER BY c DESC LIMIT 10"
            ).fetchall()
            top_actions = conn.execute(
                "SELECT COALESCE(action, 'Unknown') AS action, COUNT(*) AS c FROM activity_events "
                "GROUP BY COALESCE(action, 'Unknown') ORDER BY c DESC LIMIT 10"
            ).fetchall()

        for row in top_people:
            top_people_tree.insert("", "end", values=(row["name"], row["c"], round(float(row["a"] or 0.0), 4)))
        for row in top_actions:
            top_actions_tree.insert("", "end", values=(row["action"], row["c"]))

    overview_toolbar = tk.Frame(tab_overview, bg="#171c3a")
    overview_toolbar.place(relx=1.0, x=-28, y=20, anchor="ne")
    refresh_btn = tk.Frame(overview_toolbar, bg="#3050d3", cursor="hand2")
    refresh_btn.pack()
    refresh_lbl = tk.Label(refresh_btn, text="Refresh Dashboard", font=("Segoe UI", 9, "bold"), fg="white", bg="#3050d3", cursor="hand2")
    refresh_lbl.pack(ipadx=10, ipady=4)
    for w in (refresh_btn, refresh_lbl):
        w.bind("<Button-1>", lambda e: refresh_overview())

    left_data = tk.Frame(tab_data, bg="#171c3a")
    left_data.pack(side="left", fill="y", padx=12, pady=12)
    right_data = tk.Frame(tab_data, bg="#171c3a")
    right_data.pack(side="left", fill="y", padx=0, pady=12)
    preview_data = tk.Frame(tab_data, bg="#171c3a")
    preview_data.pack(side="left", fill="both", expand=True, padx=12, pady=12)

    def action_button(parent_widget, text, color, cmd):
        f = tk.Frame(parent_widget, bg=color, cursor="hand2")
        f.pack(fill="x", pady=8)
        l = tk.Label(f, text=text, font=("Segoe UI", 10, "bold"), fg="white", bg=color, cursor="hand2")
        l.pack(ipady=8)
        for w in (f, l):
            w.bind("<Button-1>", lambda e: cmd())

    def do_backup():
        out = filedialog.askdirectory(
            title="Select backup folder",
            initialdir=os.path.join(base_dir, "database", "artifacts", "backups"),
        )
        if not out:
            return
        path = pack.backup_database(out)
        status_var.set(f"Backup created: {path}")
        messagebox.showinfo("Backup", path, parent=win)

    def do_restore():
        path = filedialog.askopenfilename(title="Select backup database", filetypes=[("SQLite", "*.db")])
        if not path:
            return
        if messagebox.askyesno("Restore", "This will overwrite current database. Continue?", parent=win):
            pack.restore_database(path)
            refresh_overview()
            status_var.set("Database restored")

    def do_optimize():
        pack.optimize_database()
        refresh_overview()
        status_var.set("Optimization complete")

    def do_seed():
        result = pack.seed_demo_data(users=120, face_events=15000, activity_events=9000, attendance_entries=1200)
        refresh_overview()
        refresh_preview()
        status_var.set(f"Seeding complete: {result}")
        messagebox.showinfo("Seed Complete", json.dumps(result, indent=2), parent=win)

    def do_export_all():
        out = filedialog.askdirectory(
            title="Select export folder",
            initialdir=os.path.join(base_dir, "database", "artifacts", "exports"),
        )
        if not out:
            return
        paths = pack.export_all_csv(out)
        status_var.set("CSV export complete")
        messagebox.showinfo("Export Complete", json.dumps(paths, indent=2), parent=win)

    tk.Label(left_data, text="Maintenance", font=("Segoe UI", 11, "bold"), fg="#d7e2ff", bg="#171c3a").pack(anchor="w", pady=(0, 4))
    action_button(left_data, "Create Backup", "#0f8c62", do_backup)
    action_button(left_data, "Restore Backup", "#3258d6", do_restore)
    action_button(left_data, "Optimize Database", "#7a3cb0", do_optimize)

    tk.Label(right_data, text="Data Generation / Export", font=("Segoe UI", 11, "bold"), fg="#d7e2ff", bg="#171c3a").pack(anchor="w", pady=(0, 4))
    action_button(right_data, "Seed Demo Data", "#b03a2e", do_seed)
    action_button(right_data, "Export All CSV", "#1f6cab", do_export_all)

    preview_header = tk.LabelFrame(preview_data, text="Data Preview", font=("Segoe UI", 10, "bold"), fg="#cddcff", bg="#171c3a")
    preview_header.pack(fill="both", expand=True)
    controls = tk.Frame(preview_header, bg="#171c3a")
    controls.pack(fill="x", padx=8, pady=8)

    tk.Label(controls, text="Table", fg="#d7e2ff", bg="#171c3a", font=("Segoe UI", 9, "bold")).pack(side="left")
    table_var = tk.StringVar(value="users")
    table_combo = ttk.Combobox(
        controls,
        textvariable=table_var,
        state="readonly",
        width=18,
        values=["users", "face_events", "activity_events", "attendance_entries"],
    )
    table_combo.pack(side="left", padx=(6, 10))

    tk.Label(controls, text="Search", fg="#d7e2ff", bg="#171c3a", font=("Segoe UI", 9, "bold")).pack(side="left")
    search_var = tk.StringVar()
    search_entry = tk.Entry(controls, textvariable=search_var, width=26, bg="#0f1430", fg="#f4f7ff", insertbackground="#f4f7ff", relief="flat")
    search_entry.pack(side="left", padx=(6, 8))

    preview_count_var = tk.StringVar(value="0 rows")
    tk.Label(controls, textvariable=preview_count_var, fg="#9cb3ff", bg="#171c3a", font=("Segoe UI", 9)).pack(side="right")

    preview_tree = ttk.Treeview(preview_header, columns=("c1", "c2", "c3", "c4", "c5"), show="headings", height=13)
    preview_tree.pack(fill="both", expand=True, padx=8, pady=(0, 8))
    preview_scroll = ttk.Scrollbar(preview_header, orient="vertical", command=preview_tree.yview)
    preview_scroll.place(relx=1.0, rely=0.17, relheight=0.8, anchor="ne")
    preview_tree.configure(yscrollcommand=preview_scroll.set)

    def refresh_preview():
        dataset = table_var.get()
        query = search_var.get().strip().lower()

        if dataset == "users":
            headings = ["Username", "Email", "Role", "Created", "Logins"]
            sql = "SELECT username, email, role, created, logins_json FROM users ORDER BY created DESC LIMIT 300"
        elif dataset == "face_events":
            headings = ["ID", "Name", "Similarity", "Time", "Payload"]
            sql = "SELECT id, name, distance, event_time, payload_json FROM face_events ORDER BY id DESC LIMIT 300"
        elif dataset == "activity_events":
            headings = ["ID", "Time", "Username", "Action", "Detail"]
            sql = "SELECT id, event_time, username, action, detail FROM activity_events ORDER BY id DESC LIMIT 300"
        else:
            headings = ["ID", "Date", "Start", "Count", "Present (sample)"]
            sql = "SELECT id, payload_json FROM attendance_entries ORDER BY id DESC LIMIT 300"

        preview_tree.configure(columns=tuple(f"c{i + 1}" for i in range(len(headings))))
        for i, h in enumerate(headings, start=1):
            col = f"c{i}"
            preview_tree.heading(col, text=h)
            if h in ("Payload", "Present (sample)", "Detail"):
                preview_tree.column(col, width=230, anchor="w")
            elif h in ("ID", "Logins", "Count"):
                preview_tree.column(col, width=90, anchor="center")
            else:
                preview_tree.column(col, width=150, anchor="w")

        for item in preview_tree.get_children():
            preview_tree.delete(item)

        shown = 0
        with pack._connect() as conn:
            rows = conn.execute(sql).fetchall()
        for row in rows:
            if dataset == "attendance_entries":
                payload = {}
                try:
                    payload = json.loads(row["payload_json"] or "{}")
                except Exception:
                    payload = {}
                present = payload.get("present") if isinstance(payload.get("present"), list) else []
                values = (
                    row["id"],
                    payload.get("date", ""),
                    payload.get("time_start", ""),
                    payload.get("count", 0),
                    ", ".join(str(x) for x in present[:4]),
                )
            elif dataset == "users":
                login_count = 0
                try:
                    data = json.loads(row["logins_json"] or "[]")
                    if isinstance(data, list):
                        login_count = len(data)
                except Exception:
                    login_count = 0
                values = (row["username"], row["email"], row["role"], row["created"], login_count)
            else:
                values = tuple(row)

            if query:
                joined = " ".join(str(v).lower() for v in values)
                if query not in joined:
                    continue
            preview_tree.insert("", "end", values=values)
            shown += 1
        preview_count_var.set(f"{shown} rows shown")

    refresh_preview_btn = tk.Frame(controls, bg="#3050d3", cursor="hand2")
    refresh_preview_btn.pack(side="left", padx=(4, 0))
    refresh_preview_lbl = tk.Label(refresh_preview_btn, text="Refresh", fg="white", bg="#3050d3", font=("Segoe UI", 9, "bold"), cursor="hand2")
    refresh_preview_lbl.pack(ipadx=8, ipady=3)
    for w in (refresh_preview_btn, refresh_preview_lbl):
        w.bind("<Button-1>", lambda e: refresh_preview())

    table_combo.bind("<<ComboboxSelected>>", lambda e: refresh_preview())
    search_var.trace_add("write", lambda *_: refresh_preview())

    perf_box = tk.Text(tab_perf, bg="#0f1430", fg="#d7e2ff", font=("Consolas", 10), height=28)
    perf_box.pack(fill="both", expand=True, padx=14, pady=14)

    def run_benchmark():
        bench = pack.query_benchmark(rounds=120)
        perf_box.delete("1.0", "end")
        perf_box.insert("end", "Benchmark Results (ms avg)\n")
        perf_box.insert("end", "==============================\n")
        for k, v in bench.items():
            perf_box.insert("end", f"{k}: {v}\n")
        perf_box.insert("end", "\nAnomaly Scan\n")
        perf_box.insert("end", "==============================\n")
        for row in pack.anomaly_scan():
            perf_box.insert("end", f"{row}\n")
        status_var.set("Benchmark complete")

    perf_tools = tk.Frame(tab_perf, bg="#171c3a")
    perf_tools.place(relx=1.0, x=-20, y=20, anchor="ne")
    bench_btn = tk.Frame(perf_tools, bg="#3258d6", cursor="hand2")
    bench_btn.pack()
    bench_lbl = tk.Label(bench_btn, text="Run Benchmark", font=("Segoe UI", 9, "bold"), fg="white", bg="#3258d6", cursor="hand2")
    bench_lbl.pack(ipadx=10, ipady=4)
    for w in (bench_btn, bench_lbl):
        w.bind("<Button-1>", lambda e: run_benchmark())

    report_box = tk.Text(tab_report, bg="#0f1430", fg="#d7e2ff", font=("Consolas", 10), height=28)
    report_box.pack(fill="both", expand=True, padx=14, pady=14)

    def do_report():
        out = filedialog.asksaveasfilename(
            title="Save presentation report",
            defaultextension=".html",
            filetypes=[("HTML", "*.html")],
            initialfile="face_studio_project_report.html",
        )
        if not out:
            return
        path = pack.generate_presentation_report(out)
        report_box.delete("1.0", "end")
        report_box.insert("end", f"Report generated:\n{path}\n\n")
        report_box.insert("end", "Open this file in browser for your presentation.\n")
        status_var.set("Report generated")

    report_tools = tk.Frame(tab_report, bg="#171c3a")
    report_tools.place(relx=1.0, x=-20, y=20, anchor="ne")
    report_btn = tk.Frame(report_tools, bg="#0f8c62", cursor="hand2")
    report_btn.pack()
    report_lbl = tk.Label(report_btn, text="Generate HTML Report", font=("Segoe UI", 9, "bold"), fg="white", bg="#0f8c62", cursor="hand2")
    report_lbl.pack(ipadx=10, ipady=4)
    for w in (report_btn, report_lbl):
        w.bind("<Button-1>", lambda e: do_report())

    refresh_overview()
    refresh_preview()

    def on_close():
        win.destroy()
        if on_close_callback:
            on_close_callback()

    win.protocol("WM_DELETE_WINDOW", on_close)
    if standalone:
        win.mainloop()


def run_advanced_cli(base_dir: str, db_path: str, command: str):
    pack = AdvancedProjectPack(base_dir, db_path)
    if command == "backup":
        out = os.path.join(base_dir, "database", "artifacts", "backups")
        path = pack.backup_database(out)
        print(path)
        return
    if command == "seeddemo":
        print(json.dumps(pack.seed_demo_data(), indent=2))
        return
    if command == "report":
        out = os.path.join(base_dir, "docs", "face_studio_project_report.html")
        print(pack.generate_presentation_report(out))
        return
    if command == "benchmark":
        print(json.dumps(pack.query_benchmark(rounds=120), indent=2))
        return
    print(json.dumps(pack.database_stats(), indent=2))
