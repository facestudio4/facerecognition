from __future__ import annotations


def launch_home_ui(app) -> None:
    """Render the desktop home page using callbacks/constants from the app module."""
    is_admin = app._current_role == "admin"

    tk = app.tk
    ttk = app.ttk
    messagebox = app.messagebox

    root = tk.Tk()
    root.title("Face Studio" + (" [ADMIN]" if is_admin else ""))
    root.geometry("580x780" if is_admin else "580x700")
    root.resizable(False, False)
    root.configure(bg="#1a1a2e")

    content_host = tk.Frame(root, bg="#1a1a2e")
    content_host.pack(fill="both", expand=True)

    content_canvas = tk.Canvas(content_host, bg="#1a1a2e", highlightthickness=0, bd=0)
    content_scroll = ttk.Scrollbar(content_host, orient="vertical", command=content_canvas.yview)
    content_canvas.configure(yscrollcommand=content_scroll.set)

    content_canvas.pack(side="left", fill="both", expand=True)
    content_scroll.pack(side="right", fill="y")

    content_root = tk.Frame(content_canvas, bg="#1a1a2e")
    content_window = content_canvas.create_window((0, 0), window=content_root, anchor="nw")

    def _sync_scroll_region(_evt=None):
        content_canvas.configure(scrollregion=content_canvas.bbox("all"))

    def _sync_content_width(evt):
        content_canvas.itemconfigure(content_window, width=evt.width)

    content_root.bind("<Configure>", _sync_scroll_region)
    content_canvas.bind("<Configure>", _sync_content_width)

    def _on_mousewheel(evt):
        if evt.delta:
            delta = -int(evt.delta / 120)
        elif getattr(evt, "num", None) == 5:
            delta = 1
        else:
            delta = -1
        content_canvas.yview_scroll(delta, "units")

    content_canvas.bind_all("<MouseWheel>", _on_mousewheel)
    content_canvas.bind_all("<Button-4>", _on_mousewheel)
    content_canvas.bind_all("<Button-5>", _on_mousewheel)

    def _unbind_scroll(_evt=None):
        content_canvas.unbind_all("<MouseWheel>")
        content_canvas.unbind_all("<Button-4>")
        content_canvas.unbind_all("<Button-5>")

    root.bind("<Destroy>", _unbind_scroll)

    tk.Label(
        content_root,
        text="🧑 Face Studio",
        font=("Segoe UI", 26, "bold"),
        fg="#e94560",
        bg="#1a1a2e",
    ).pack(pady=(20, 2))

    role_text = "🔒 Admin Mode" if is_admin else "👤 User Mode"
    role_color = "#e94560" if is_admin else "#0f3460"
    welcome_name = app._current_username if app._current_username else "Guest"
    tk.Label(
        content_root,
        text=f"{role_text}  |  Welcome, {welcome_name}",
        font=("Segoe UI", 10, "bold"),
        fg=role_color,
        bg="#1a1a2e",
    ).pack(pady=(0, 2))

    tk.Label(
        content_root,
        text="Choose a mode to get started",
        font=("Segoe UI", 11),
        fg="#a0a0b8",
        bg="#1a1a2e",
    ).pack(pady=(0, 15))

    def _hex_to_rgb(hex_color):
        h = hex_color.lstrip("#")
        return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))

    def _rgb_to_hex(rgb):
        return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"

    def _blend(c1, c2, t):
        a = _hex_to_rgb(c1)
        b = _hex_to_rgb(c2)
        return _rgb_to_hex(tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3)))

    option_cards = []

    def make_button(parent, text, subtitle, color, command):
        hover_color = _blend(color, "#ffffff", 0.14)
        shell = tk.Frame(parent, bg="#283670", bd=0, relief="flat", highlightthickness=0)
        shell.pack(fill="x", padx=16, pady=7)

        bf = tk.Frame(shell, bg=color, bd=0, relief="flat", cursor="hand2")
        bf.pack(fill="x", padx=2, pady=2)

        lt = tk.Label(bf, text=text, font=("Segoe UI", 14, "bold"), fg="#f8fbff", bg=color, cursor="hand2", anchor="w")
        lt.pack(fill="x", padx=14, pady=(10, 0))

        ls = tk.Label(bf, text=subtitle, font=("Segoe UI", 9), fg="#d6deef", bg=color, cursor="hand2", anchor="w")
        ls.pack(fill="x", padx=14, pady=(0, 10))

        state = {"token": 0, "hover": False}

        def _apply(base, border, subtitle_fg):
            shell.configure(bg=border)
            bf.configure(bg=base)
            lt.configure(bg=base)
            ls.configure(bg=base, fg=subtitle_fg)

        def _animate(to_hover):
            state["token"] += 1
            token = state["token"]
            src_base = bf.cget("bg")
            dst_base = hover_color if to_hover else color
            src_border = shell.cget("bg")
            dst_border = "#65b5ff" if to_hover else "#283670"
            src_sub = ls.cget("fg")
            dst_sub = "#f0f5ff" if to_hover else "#d6deef"

            def step(i):
                if state["token"] != token:
                    return
                t = i / 6.0
                _apply(_blend(src_base, dst_base, t), _blend(src_border, dst_border, t), _blend(src_sub, dst_sub, t))
                if i < 6:
                    root.after(16, lambda: step(i + 1))

            step(0)

        def _enter(_e=None):
            state["hover"] = True
            _animate(True)

        def _leave(_e=None):
            state["hover"] = False
            _animate(False)

        for widget in (shell, bf, lt, ls):
            widget.bind("<Button-1>", lambda e: command())
            widget.bind("<Enter>", _enter)
            widget.bind("<Leave>", _leave)

        option_cards.append((shell, color, hover_color))
        return shell

    def _open_panel(panel_fn):
        root.withdraw()
        try:
            panel_fn()
        except Exception as exc:
            messagebox.showerror("Error", str(exc), parent=root)
            root.deiconify()

    def _run_recognition_mode(title, runner):
        root.withdraw()
        loading = None
        try:
            loading = app.LoadingScreen(root, title)
            known_encodings = loading.run_task(lambda cb: app.load_and_train_with_progress(cb))
            loading.close()
            loading = None
            runner(known_encodings)
        except Exception as exc:
            messagebox.showerror("Error", str(exc), parent=root)
        finally:
            if loading is not None:
                loading.close()
            root.deiconify()

    def start_recognition():
        _run_recognition_mode(
            "Loading Face Recognition",
            lambda known_encodings: app._recognize_webcam_with_model(known_encodings),
        )

    def start_generation():
        _open_panel(lambda: app.face_generation_gui(parent=root, on_close_callback=root.deiconify))

    def start_comparison():
        _open_panel(lambda: app.face_comparison_gui(parent=root, on_close_callback=root.deiconify))

    def start_attendance():
        _run_recognition_mode(
            "Loading Attendance System",
            lambda known_encodings: app.attendance_webcam(known_encodings),
        )

    def start_user_profile():
        _open_panel(lambda: app.user_profile_gui(parent=root, on_close_callback=root.deiconify))

    def start_face_search():
        _open_panel(lambda: app.face_search_gui(parent=root, on_close_callback=root.deiconify))

    def start_face_stats():
        _open_panel(lambda: app.face_stats_gui(parent=root, on_close_callback=root.deiconify))

    def start_live_face_counter():
        _open_panel(lambda: app.live_face_counter_gui(parent=root, on_close_callback=root.deiconify))

    def start_help_about():
        _open_panel(lambda: app.help_about_gui(parent=root, on_close_callback=root.deiconify))

    def start_system_info():
        _open_panel(lambda: app.system_info_gui(parent=root, on_close_callback=root.deiconify))

    def start_database():
        _open_panel(lambda: app.face_database_gui(parent=root, on_close_callback=root.deiconify))

    def start_analytics():
        _open_panel(lambda: app.analytics_dashboard_gui(parent=root, on_close_callback=root.deiconify))

    def start_advanced_lab():
        _open_panel(
            lambda: app.launch_advanced_lab(app.BASE_DIR, app.SQL_DB_PATH, parent=root, on_close_callback=root.deiconify)
        )

    def start_enterprise_center():
        _open_panel(
            lambda: app.launch_enterprise_control_center(
                app.BASE_DIR,
                app.SQL_DB_PATH,
                parent=root,
                on_close_callback=root.deiconify,
            )
        )

    def start_phase3_hub():
        _open_panel(
            lambda: app.launch_phase3_services_gui(
                app.BASE_DIR,
                app.SQL_DB_PATH,
                parent=root,
                on_close_callback=root.deiconify,
            )
        )

    def start_phase41_showcase():
        _open_panel(
            lambda: app.launch_phase41_showcase_gui(
                app.BASE_DIR,
                app.SQL_DB_PATH,
                parent=root,
                on_close_callback=root.deiconify,
            )
        )

    def start_phase5_bundle():
        _open_panel(
            lambda: app.launch_evaluator_bundle_gui(
                app.BASE_DIR,
                app.SQL_DB_PATH,
                parent=root,
                on_close_callback=root.deiconify,
            )
        )

    def start_phase6_judge():
        _open_panel(
            lambda: app.launch_judge_mode_gui(
                app.BASE_DIR,
                app.SQL_DB_PATH,
                parent=root,
                on_close_callback=root.deiconify,
            )
        )

    def start_phase7_demo():
        _open_panel(
            lambda: app.launch_phase7_demo_launcher_gui(
                app.BASE_DIR,
                app.SQL_DB_PATH,
                parent=root,
                on_close_callback=root.deiconify,
            )
        )

    def start_phase8_presentation():
        _open_panel(
            lambda: app.launch_phase8_presentation_gui(
                app.BASE_DIR,
                app.SQL_DB_PATH,
                parent=root,
                on_close_callback=root.deiconify,
            )
        )

    make_button(content_root, "🔍  Face Recognition", "Identify people in real-time via webcam", "#184e77", start_recognition)
    make_button(content_root, "🎨  Face Generation", "Search by name — Sketch, Cartoon, Ghibli Art & more", "#5e548e", start_generation)
    make_button(content_root, "🔎  Face Comparison", "Compare two face images — check similarity", "#1f7a8c", start_comparison)

    if is_admin:
        make_button(content_root, "📋  Attendance", "Mark attendance via webcam recognition", "#2a9d8f", start_attendance)
        make_button(content_root, "🗃  Face Database", "Browse, preview, and manage registered faces", "#6d597a", start_database)
        make_button(content_root, "📊  Analytics Dashboard", "View recognition stats, charts & export logs", "#c44536", start_analytics)
        make_button(content_root, "🚀  Advanced Project Lab", "Backup, benchmark, seeding, anomaly scan, HTML report", "#2f9e88", start_advanced_lab)
        make_button(content_root, "🛡  Enterprise Control Center", "Permissions, approvals, scheduler, models, evidence pack", "#277da1", start_enterprise_center)
        make_button(content_root, "🌐  Services Hub", "Secure REST API, live stream, auto backup scheduler", "#3a86ff", start_phase3_hub)
        make_button(content_root, "📺  Live Evaluator Dashboard", "Evaluator dashboard, viva run automation, exportable demo report", "#bc4749", start_phase41_showcase)
        make_button(content_root, "📦  Evaluator Bundle", "One-click export of reports, CSVs, API docs, viva proof and enterprise evidence", "#2a9d8f", start_phase5_bundle)
        make_button(content_root, "🎯  Judge Mode", "Latest bundle summary, open artifacts, and fastest live demo path", "#355070", start_phase6_judge)
        make_button(content_root, "🚀  Demo Launcher", "Prepare full demo stack, generate manifest, open report and jump to judge mode", "#b08968", start_phase7_demo)
        make_button(content_root, "🎬  Presentation Startup", "Generate launch scripts and open the presentation flow with minimal setup", "#9c6644", start_phase8_presentation)

        def start_registry():
            _open_panel(lambda: app.user_registry_gui(parent=root, on_close_callback=root.deiconify))

        make_button(content_root, "📋  User Registry", "View registered users, login history & manage accounts", "#3a86ff", start_registry)
    else:
        tk.Label(
            content_root,
            text="Advanced User Tools",
            font=("Segoe UI", 11, "bold"),
            fg="#a0a0b8",
            bg="#1a1a2e",
        ).pack(pady=(8, 2))

        make_button(content_root, "👤  My Profile", "View account details, login history, and change password", "#2a9d8f", start_user_profile)
        make_button(content_root, "🔎  Face Search", "Find people quickly by name across registered faces", "#6d597a", start_face_search)
        make_button(content_root, "📈  Face Stats", "See recognition summaries and person-wise statistics", "#e76f51", start_face_stats)
        make_button(content_root, "🎯  Live Face Counter", "Count and track visible faces from your camera feed", "#277da1", start_live_face_counter)
        make_button(content_root, "🖥  System Info", "Check model files, storage, and runtime health details", "#9c6644", start_system_info)
        make_button(content_root, "❓  Help & About", "Open shortcuts, feature guide, and app information", "#355070", start_help_about)

    def run_entry_animation(index=0):
        if index >= len(option_cards):
            return
        shell, base_color, hover_color = option_cards[index]
        pulse = {"step": 0}

        def frame_tick():
            step = pulse["step"]
            if step <= 6:
                t = step / 6.0
                shell.configure(bg=_blend("#283670", "#65b5ff", t))
                if shell.winfo_children():
                    card = shell.winfo_children()[0]
                    c = _blend(base_color, hover_color, t)
                    card.configure(bg=c)
                    for child in card.winfo_children():
                        child.configure(bg=c)
            elif step <= 12:
                t = (step - 6) / 6.0
                shell.configure(bg=_blend("#65b5ff", "#283670", t))
                if shell.winfo_children():
                    card = shell.winfo_children()[0]
                    c = _blend(hover_color, base_color, t)
                    card.configure(bg=c)
                    for child in card.winfo_children():
                        child.configure(bg=c)
            else:
                shell.configure(bg="#283670")
                if shell.winfo_children():
                    card = shell.winfo_children()[0]
                    card.configure(bg=base_color)
                    for child in card.winfo_children():
                        if child.cget("fg") == "#f0f5ff":
                            child.configure(bg=base_color, fg="#d6deef")
                        else:
                            child.configure(bg=base_color)
                root.after(45, lambda: run_entry_animation(index + 1))
                return
            pulse["step"] += 1
            root.after(16, frame_tick)

        frame_tick()

    root.after(120, run_entry_animation)

    footer_frame = tk.Frame(root, bg="#1a1a2e")
    footer_frame.pack(side="bottom", pady=8)

    def _logout():
        root.destroy()
        app.launch_login()

    logout_btn = tk.Frame(footer_frame, bg="#333", cursor="hand2")
    logout_btn.pack(pady=(0, 3), ipadx=14, ipady=3)
    logout_lbl = tk.Label(logout_btn, text="🚪 Logout", font=("Segoe UI", 9, "bold"), fg="#ccc", bg="#333", cursor="hand2")
    logout_lbl.pack()
    for w in (logout_btn, logout_lbl):
        w.bind("<Button-1>", lambda e: _logout())

    tk.Label(footer_frame, text="Press ESC in any mode to return here", font=("Segoe UI", 9), fg="#555570", bg="#1a1a2e").pack()

    root.mainloop()
