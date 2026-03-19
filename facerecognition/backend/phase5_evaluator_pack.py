import json
import os
import shutil
import zipfile
from datetime import datetime
import tkinter as tk
from tkinter import messagebox, ttk

from backend.advanced_project_pack import AdvancedProjectPack
from backend.phase2_enterprise_pack import EnterpriseControlCenter
from backend.phase4_showcase_pack import Phase4ShowcaseRunner


class EvaluatorBundleBuilder:
    def __init__(self, base_dir: str, db_path: str, host: str = "127.0.0.1", port: int = 8787):
        self.base_dir = base_dir
        self.db_path = db_path
        self.host = host
        self.port = int(port)
        self.advanced = AdvancedProjectPack(base_dir, db_path)
        self.enterprise = EnterpriseControlCenter(base_dir, db_path)
        self.showcase = Phase4ShowcaseRunner(base_dir, db_path, host=host, port=port)

    def build_bundle(self):
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_dir = os.path.join(self.base_dir, "database", "artifacts", "evaluator_bundle", f"bundle_{stamp}")
        os.makedirs(out_dir, exist_ok=True)

        csv_dir = os.path.join(out_dir, "csv_exports")
        reports_dir = os.path.join(out_dir, "reports")
        api_dir = os.path.join(out_dir, "api")
        evidence_dir = os.path.join(out_dir, "evidence")
        os.makedirs(csv_dir, exist_ok=True)
        os.makedirs(reports_dir, exist_ok=True)
        os.makedirs(api_dir, exist_ok=True)
        os.makedirs(evidence_dir, exist_ok=True)

        try:
            csv_exports = self.advanced.export_all_csv(csv_dir)
            html_report = self.advanced.generate_presentation_report(os.path.join(reports_dir, "project_report.html"))
            evidence_zip = self.enterprise.generate_evidence_pack(os.path.join(evidence_dir, "enterprise_evidence.zip"))
            viva_report = self.showcase.export_viva_report()
            api_docs_path = os.path.join(api_dir, "api_docs.json")
            with open(api_docs_path, "w", encoding="utf-8") as f:
                json.dump(self.showcase.hub.get_api_docs(), f, ensure_ascii=False, indent=2)

            copied_viva = os.path.join(api_dir, os.path.basename(viva_report))
            shutil.copy2(viva_report, copied_viva)

            stats = self.showcase.hub.get_stats()
            anomalies = self.advanced.anomaly_scan()
            summary = {
                "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "base_dir": self.base_dir,
                "db_path": self.db_path,
                "api_base": self.showcase.base_url(),
                "stats": stats,
                "anomalies": anomalies,
                "artifacts": {
                    "csv_exports": csv_exports,
                    "project_report": html_report,
                    "enterprise_evidence_zip": evidence_zip,
                    "viva_report": copied_viva,
                    "api_docs": api_docs_path,
                },
            }
        finally:
            self.showcase.stop_services()
        summary_path = os.path.join(out_dir, "bundle_summary.json")
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

        readme_path = os.path.join(out_dir, "README.txt")
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(
                "Face Studio Evaluator Bundle\n"
                "===========================\n\n"
                f"Generated: {summary['generated_at']}\n"
                f"API Base: {summary['api_base']}\n\n"
                "Contents\n"
                "- bundle_summary.json: overall metrics and artifact map\n"
                "- reports/project_report.html: presentation-ready project report\n"
                "- api/api_docs.json: API contract and auth documentation\n"
                "- api/viva_run_*.json: one-click viva proof output\n"
                "- evidence/enterprise_evidence.zip: enterprise governance evidence\n"
                "- csv_exports/: exported user, face, activity, attendance data\n"
            )

        zip_path = out_dir + ".zip"
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
            for root, _, files in os.walk(out_dir):
                for name in files:
                    full = os.path.join(root, name)
                    rel = os.path.relpath(full, out_dir)
                    z.write(full, rel)

        return {
            "bundle_dir": out_dir,
            "bundle_zip": zip_path,
            "summary": summary_path,
            "readme": readme_path,
        }


def launch_evaluator_bundle_gui(base_dir: str, db_path: str, parent=None, on_close_callback=None):
    builder = EvaluatorBundleBuilder(base_dir, db_path)

    if parent is None:
        win = tk.Tk()
        standalone = True
    else:
        win = tk.Toplevel(parent)
        standalone = False

    win.title("Evaluator Bundle")
    win.geometry("1020x700")
    win.configure(bg="#101826")

    page_host = tk.Frame(win, bg="#101826")
    page_host.pack(fill="both", expand=True)
    page_canvas = tk.Canvas(page_host, bg="#101826", highlightthickness=0, bd=0)
    page_scroll = ttk.Scrollbar(page_host, orient="vertical", command=page_canvas.yview)
    page = tk.Frame(page_canvas, bg="#101826")
    page_window = page_canvas.create_window((0, 0), window=page, anchor="nw")
    page_canvas.configure(yscrollcommand=page_scroll.set)
    page_canvas.pack(side="left", fill="both", expand=True)
    page_scroll.pack(side="right", fill="y")
    page.bind("<Configure>", lambda _e: page_canvas.configure(scrollregion=page_canvas.bbox("all")))
    page_canvas.bind("<Configure>", lambda e: page_canvas.itemconfigure(page_window, width=e.width))

    tk.Label(page, text="Evaluator Bundle", font=("Segoe UI", 24, "bold"), fg="#ffb703", bg="#101826").pack(anchor="w", padx=14, pady=(12, 4))
    tk.Label(page, text="One-click evidence export for evaluator review and presentation", font=("Segoe UI", 11), fg="#bcd3ff", bg="#101826").pack(anchor="w", padx=14)

    status_var = tk.StringVar(value="Ready")
    button_style = {"font": ("Segoe UI", 9, "bold"), "padx": 10, "pady": 4}
    tk.Label(page, textvariable=status_var, font=("Segoe UI", 10), fg="#7ad0ff", bg="#101826").pack(anchor="w", padx=14, pady=(6, 10))

    cards_row = tk.Frame(page, bg="#101826")
    cards_row.pack(fill="x", padx=14, pady=(0, 8))
    card_vars = {
        "bundle_dir": tk.StringVar(value="-"),
        "bundle_zip": tk.StringVar(value="-"),
        "summary": tk.StringVar(value="-"),
    }
    for idx, (label, key) in enumerate(
        [
            ("Bundle Dir", "bundle_dir"),
            ("Bundle Zip", "bundle_zip"),
            ("Summary", "summary"),
        ]
    ):
        card = tk.Frame(cards_row, bg="#0e1628", bd=1, relief="solid", highlightbackground="#31427f", highlightthickness=1)
        card.grid(row=0, column=idx, sticky="nsew", padx=4)
        tk.Label(card, text=label, font=("Segoe UI", 9, "bold"), fg="#9cb3ff", bg="#0e1628").pack(anchor="w", padx=8, pady=(6, 2))
        tk.Label(card, textvariable=card_vars[key], font=("Consolas", 9), fg="#e4ecff", bg="#0e1628", wraplength=300, justify="left").pack(anchor="w", padx=8, pady=(0, 8))
    for i in range(3):
        cards_row.grid_columnconfigure(i, weight=1)

    output_box = tk.LabelFrame(page, text="Bundle Console", font=("Segoe UI", 10, "bold"), fg="#cfdcff", bg="#101826")
    output_box.pack(fill="both", expand=True, padx=14, pady=(0, 12))
    output = tk.Text(output_box, bg="#0e1628", fg="#e4ecff", font=("Consolas", 10), height=26)
    output.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=8)
    output_scroll = ttk.Scrollbar(output_box, orient="vertical", command=output.yview)
    output_scroll.pack(side="right", fill="y", padx=(6, 8), pady=8)
    output.configure(yscrollcommand=output_scroll.set)

    def append(text: str):
        output.insert("end", text + "\n")
        output.see("end")

    def build_now():
        try:
            result = builder.build_bundle()
            status_var.set("Evaluator bundle generated")
            card_vars["bundle_dir"].set(os.path.basename(result.get("bundle_dir", "")) or "-")
            card_vars["bundle_zip"].set(os.path.basename(result.get("bundle_zip", "")) or "-")
            card_vars["summary"].set(os.path.basename(result.get("summary", "")) or "-")
            output.delete("1.0", "end")
            append(json.dumps(result, ensure_ascii=False, indent=2))
        except Exception as e:
            status_var.set("Bundle generation failed")
            append(str(e))
            messagebox.showerror("Bundle Error", str(e), parent=win)

    controls = tk.LabelFrame(page, text="Actions", font=("Segoe UI", 10, "bold"), fg="#cfdcff", bg="#101826")
    controls.pack(fill="x", padx=14, pady=(0, 10))
    controls_row = tk.Frame(controls, bg="#101826")
    controls_row.pack(fill="x", padx=8, pady=8)

    tk.Button(controls_row, text="Build Evaluator Bundle", command=build_now, bg="#0f8c62", fg="white", **button_style).pack(side="left", padx=4)
    tk.Button(controls_row, text="Close", command=win.destroy, bg="#b03a2e", fg="white", **button_style).pack(side="left", padx=4)

    build_now()

    def on_close():
        win.destroy()
        if on_close_callback:
            on_close_callback()

    win.protocol("WM_DELETE_WINDOW", on_close)
    if standalone:
        win.mainloop()


def run_phase5_cli(base_dir: str, db_path: str, command: str, host: str = "127.0.0.1", port: int = 8787):
    builder = EvaluatorBundleBuilder(base_dir, db_path, host=host, port=port)
    if command == "evaluatorbundle":
        print(json.dumps(builder.build_bundle(), ensure_ascii=False, indent=2))
        return
    launch_evaluator_bundle_gui(base_dir, db_path)
