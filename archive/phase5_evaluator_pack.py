import json
import os
import shutil
import zipfile
from datetime import datetime
import tkinter as tk
from tkinter import messagebox

from advanced_project_pack import AdvancedProjectPack
from phase2_enterprise_pack import EnterpriseControlCenter
from phase4_showcase_pack import Phase4ShowcaseRunner


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
        out_dir = os.path.join(self.base_dir, "evaluator_bundle", f"bundle_{stamp}")
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
    win.geometry("900x620")
    win.configure(bg="#101826")

    tk.Label(win, text="Evaluator Bundle", font=("Segoe UI", 24, "bold"), fg="#ffb703", bg="#101826").pack(anchor="w", padx=14, pady=(12, 4))
    tk.Label(win, text="One-click evidence export for evaluator review and presentation", font=("Segoe UI", 11), fg="#bcd3ff", bg="#101826").pack(anchor="w", padx=14)

    status_var = tk.StringVar(value="Ready")
    tk.Label(win, textvariable=status_var, font=("Segoe UI", 10), fg="#7ad0ff", bg="#101826").pack(anchor="w", padx=14, pady=(6, 10))

    output = tk.Text(win, bg="#0e1628", fg="#e4ecff", font=("Consolas", 10), height=26)
    output.pack(fill="both", expand=True, padx=14, pady=(0, 12))

    def append(text: str):
        output.insert("end", text + "\n")
        output.see("end")

    def build_now():
        try:
            result = builder.build_bundle()
            status_var.set("Evaluator bundle generated")
            output.delete("1.0", "end")
            append(json.dumps(result, ensure_ascii=False, indent=2))
        except Exception as e:
            status_var.set("Bundle generation failed")
            append(str(e))
            messagebox.showerror("Bundle Error", str(e), parent=win)

    controls = tk.Frame(win, bg="#101826")
    controls.pack(fill="x", padx=14, pady=(0, 10))

    tk.Button(controls, text="Build Evaluator Bundle", command=build_now, bg="#0f8c62", fg="white").pack(side="left", padx=4)
    tk.Button(controls, text="Close", command=win.destroy, bg="#b03a2e", fg="white").pack(side="left", padx=4)

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
