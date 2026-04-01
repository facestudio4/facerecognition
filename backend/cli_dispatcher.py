from __future__ import annotations

import argparse



def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Face Studio — Recognition, Generation, Comparison, Attendance & Analytics"
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("recognize", help="Live webcam recognition")
    sub.add_parser("generate", help="Face generation with style filters")
    sub.add_parser("retrain", help="Force retrain encodings from scratch (person folders + archive)")
    sub.add_parser("compare", help="Face comparison GUI — check if two images are the same person")
    sub.add_parser("attendance", help="Mark attendance via webcam recognition")
    sub.add_parser("reports", help="View attendance reports")
    sub.add_parser("database", help="Manage face database — browse, delete, retrain")
    sub.add_parser("analytics", help="Analytics dashboard — stats, charts, export")
    sub.add_parser("lab", help="Advanced project lab GUI")
    sub.add_parser("backup", help="Create database backup in backups folder")
    sub.add_parser("seeddemo", help="Seed large demo dataset for presentation")
    sub.add_parser("report", help="Generate HTML project report")
    sub.add_parser("benchmarkdb", help="Run database benchmark and print timings")
    sub.add_parser("enterprise", help="Open enterprise control center GUI")
    sub.add_parser("runjobs", help="Run due scheduled jobs in enterprise module")
    sub.add_parser("evidencepack", help="Generate enterprise evidence pack ZIP")
    sub.add_parser("phase3", help="Open Services Hub GUI")
    sub.add_parser("startapi", help="Start secure REST API server")
    sub.add_parser("startservices", help="Start API + backup scheduler service stack")
    sub.add_parser("showapikey", help="Print services API key")
    sub.add_parser("rotapikey", help="Rotate services API key")
    sub.add_parser("gentoken", help="Generate bearer token")
    sub.add_parser("apidocs", help="Print API docs JSON")
    sub.add_parser("demokit", help="Export demo kit files")
    sub.add_parser("phase41", help="Open live evaluator dashboard")
    sub.add_parser("vivademo", help="Run one-click viva demo flow and print results")
    sub.add_parser("vivareport", help="Export viva demo report JSON file")
    sub.add_parser("phase5", help="Open evaluator bundle GUI")
    sub.add_parser("evaluatorbundle", help="Build final evaluator bundle and print paths")
    sub.add_parser("phase6", help="Open judge mode GUI")
    sub.add_parser("judgesnapshot", help="Print latest judge-mode bundle snapshot")
    sub.add_parser("judgedemo", help="Run best live demo path and print output")
    sub.add_parser("phase7", help="Open demo launcher GUI")
    sub.add_parser("demoprep", help="Prepare full demo stack and print manifest")
    sub.add_parser("demomanifest", help="Print latest demo launcher manifest")
    sub.add_parser("phase8", help="Open presentation startup GUI")
    sub.add_parser("makepresentationkit", help="Generate presentation-day launch scripts and summary")
    sub.add_parser("presentationjudge", help="Launch judge mode directly for presentation day")
    sub.add_parser("presentationdemo", help="Launch demo launcher directly for presentation day")
    sub.add_parser("snapshot", help="Print service snapshot stats")

    ident = sub.add_parser("identify", help="Recognize faces in an image")
    ident.add_argument("--image", required=True, help="Path to image")

    return parser



def dispatch_command(app, args) -> None:
    cmd = args.command

    if cmd == "recognize":
        app.recognize_webcam()
    elif cmd == "generate":
        app.face_generation_gui()
    elif cmd == "retrain":
        app.load_and_train(force_retrain=True)
        print("[DONE] Encodings recomputed and cached.")
    elif cmd == "identify":
        app.identify_image(args.image)
    elif cmd == "compare":
        app.face_comparison_gui()
    elif cmd == "attendance":
        known = app.load_and_train()
        app.attendance_webcam(known)
    elif cmd == "reports":
        app.attendance_report_gui()
    elif cmd == "database":
        app.face_database_gui()
    elif cmd == "analytics":
        app.analytics_dashboard_gui()
    elif cmd == "lab":
        app.launch_advanced_lab(app.BASE_DIR, app.SQL_DB_PATH)
    elif cmd == "backup":
        app.run_advanced_cli(app.BASE_DIR, app.SQL_DB_PATH, "backup")
    elif cmd == "seeddemo":
        app.run_advanced_cli(app.BASE_DIR, app.SQL_DB_PATH, "seeddemo")
    elif cmd == "report":
        app.run_advanced_cli(app.BASE_DIR, app.SQL_DB_PATH, "report")
    elif cmd == "benchmarkdb":
        app.run_advanced_cli(app.BASE_DIR, app.SQL_DB_PATH, "benchmark")
    elif cmd == "enterprise":
        app.launch_enterprise_control_center(app.BASE_DIR, app.SQL_DB_PATH)
    elif cmd == "runjobs":
        app.run_enterprise_cli(app.BASE_DIR, app.SQL_DB_PATH, "runjobs")
    elif cmd == "evidencepack":
        app.run_enterprise_cli(app.BASE_DIR, app.SQL_DB_PATH, "evidencepack")
    elif cmd == "phase3":
        app.launch_phase3_services_gui(app.BASE_DIR, app.SQL_DB_PATH)
    elif cmd == "startapi":
        app.run_phase3_cli(app.BASE_DIR, app.SQL_DB_PATH, "startapi")
    elif cmd == "startservices":
        app.run_phase3_cli(app.BASE_DIR, app.SQL_DB_PATH, "startservices")
    elif cmd == "showapikey":
        app.run_phase3_cli(app.BASE_DIR, app.SQL_DB_PATH, "showapikey")
    elif cmd == "rotapikey":
        app.run_phase3_cli(app.BASE_DIR, app.SQL_DB_PATH, "rotapikey")
    elif cmd == "gentoken":
        app.run_phase3_cli(app.BASE_DIR, app.SQL_DB_PATH, "gentoken")
    elif cmd == "apidocs":
        app.run_phase3_cli(app.BASE_DIR, app.SQL_DB_PATH, "apidocs")
    elif cmd == "demokit":
        app.run_phase3_cli(app.BASE_DIR, app.SQL_DB_PATH, "demokit")
    elif cmd == "phase41":
        app.launch_phase41_showcase_gui(app.BASE_DIR, app.SQL_DB_PATH)
    elif cmd == "vivademo":
        app.run_phase41_cli(app.BASE_DIR, app.SQL_DB_PATH, "vivademo")
    elif cmd == "vivareport":
        app.run_phase41_cli(app.BASE_DIR, app.SQL_DB_PATH, "vivareport")
    elif cmd == "phase5":
        app.launch_evaluator_bundle_gui(app.BASE_DIR, app.SQL_DB_PATH)
    elif cmd == "evaluatorbundle":
        app.run_phase5_cli(app.BASE_DIR, app.SQL_DB_PATH, "evaluatorbundle")
    elif cmd == "phase6":
        app.launch_judge_mode_gui(app.BASE_DIR, app.SQL_DB_PATH)
    elif cmd == "judgesnapshot":
        app.run_phase6_cli(app.BASE_DIR, app.SQL_DB_PATH, "judgesnapshot")
    elif cmd == "judgedemo":
        app.run_phase6_cli(app.BASE_DIR, app.SQL_DB_PATH, "judgedemo")
    elif cmd == "phase7":
        app.launch_phase7_demo_launcher_gui(app.BASE_DIR, app.SQL_DB_PATH)
    elif cmd == "demoprep":
        app.run_phase7_cli(app.BASE_DIR, app.SQL_DB_PATH, "demoprep")
    elif cmd == "demomanifest":
        app.run_phase7_cli(app.BASE_DIR, app.SQL_DB_PATH, "demomanifest")
    elif cmd == "phase8":
        app.launch_phase8_presentation_gui(app.BASE_DIR, app.SQL_DB_PATH)
    elif cmd == "makepresentationkit":
        app.run_phase8_cli(app.BASE_DIR, app.SQL_DB_PATH, "makepresentationkit")
    elif cmd == "presentationjudge":
        app.run_phase8_cli(app.BASE_DIR, app.SQL_DB_PATH, "presentationjudge")
    elif cmd == "presentationdemo":
        app.run_phase8_cli(app.BASE_DIR, app.SQL_DB_PATH, "presentationdemo")
    elif cmd == "snapshot":
        app.run_phase3_cli(app.BASE_DIR, app.SQL_DB_PATH, "snapshot")
    else:
        app.launch_login()



def run_from_argv(app) -> None:
    parser = build_parser()
    args = parser.parse_args()
    dispatch_command(app, args)
