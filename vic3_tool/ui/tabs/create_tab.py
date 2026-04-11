import tkinter as tk
from tkinter import ttk, messagebox
from vic3_tool.main import create_full_je


def build_create_tab(notebook, path_var, tag_var):
    frame = ttk.Frame(notebook)
    frame.columnconfigure(1, weight=1)

    # ============================================================
    # CHAMPS DE BASE
    # ============================================================

    base = ttk.LabelFrame(frame, text="Journal Entry — Infos de base")
    base.pack(fill="x", padx=10, pady=8)
    base.columnconfigure(1, weight=1)

    tk.Label(base, text="Année").grid(row=0, column=0, sticky="w", padx=6, pady=3)
    year_var = tk.StringVar()
    tk.Entry(base, textvariable=year_var, width=10).grid(row=0, column=1, sticky="w", padx=6)

    tk.Label(base, text="Titre").grid(row=1, column=0, sticky="w", padx=6, pady=3)
    title_var = tk.StringVar()
    tk.Entry(base, textvariable=title_var, width=40).grid(row=1, column=1, sticky="w", padx=6)

    tk.Label(base, text="Description").grid(row=2, column=0, sticky="nw", padx=6, pady=3)
    desc_text = tk.Text(base, height=3, width=40)
    desc_text.grid(row=2, column=1, sticky="w", padx=6, pady=3)

    # ============================================================
    # PANNEAU FEATURES
    # ============================================================

    feat_outer = ttk.LabelFrame(frame, text="Features")
    feat_outer.pack(fill="both", expand=True, padx=10, pady=4)

    canvas = tk.Canvas(feat_outer, borderwidth=0, highlightthickness=0)
    scrollbar = ttk.Scrollbar(feat_outer, orient="vertical", command=canvas.yview)
    scroll_frame = ttk.Frame(canvas)

    scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    # -------- état global des features --------

    features_data = {}  # stocke les widgets de chaque feature

    def make_feature(parent, feat_key, feat_label, build_config_fn):
        """Crée une ligne feature : [checkbox Oui/Non] + zone config dépliable."""
        row_frame = ttk.Frame(parent)
        row_frame.pack(fill="x", padx=4, pady=2)

        enabled_var = tk.BooleanVar(value=False)
        config_frame = ttk.Frame(parent)

        def toggle():
            if enabled_var.get():
                config_frame.pack(fill="x", padx=20, pady=2)
            else:
                config_frame.pack_forget()

        chk = tk.Checkbutton(row_frame, text=feat_label,
                             variable=enabled_var, command=toggle,
                             anchor="w")
        chk.pack(side="left")

        build_config_fn(config_frame, feat_key)
        features_data[feat_key] = {"enabled": enabled_var}

    # ============================================================
    # FEATURE : BOUTONS
    # ============================================================

    buttons_rows = []

    def build_buttons_config(parent, key):
        tk.Label(parent, text="Nombre de boutons :").pack(anchor="w")

        num_var = tk.IntVar(value=1)
        btn_rows_frame = ttk.Frame(parent)

        def refresh_buttons(*_):
            for w in btn_rows_frame.winfo_children():
                w.destroy()
            buttons_rows.clear()
            for i in range(1, num_var.get() + 1):
                row = ttk.Frame(btn_rows_frame)
                row.pack(fill="x", pady=1)
                tk.Label(row, text=f"Bouton {i} — Nom").pack(side="left")
                nv = tk.StringVar()
                tk.Entry(row, textvariable=nv, width=16).pack(side="left", padx=4)
                tk.Label(row, text="Desc").pack(side="left")
                dv = tk.StringVar()
                tk.Entry(row, textvariable=dv, width=20).pack(side="left", padx=4)
                tk.Label(row, text="TT1").pack(side="left")
                t1 = tk.StringVar()
                tk.Entry(row, textvariable=t1, width=12).pack(side="left", padx=2)
                tk.Label(row, text="TT2").pack(side="left")
                t2 = tk.StringVar()
                tk.Entry(row, textvariable=t2, width=12).pack(side="left", padx=2)
                buttons_rows.append({"name": nv, "desc": dv, "tt1": t1, "tt2": t2})

        spin = tk.Spinbox(parent, from_=1, to=10, textvariable=num_var,
                          width=4, command=refresh_buttons)
        spin.pack(anchor="w")
        btn_rows_frame.pack(fill="x")
        refresh_buttons()
        features_data["buttons"]["num"] = num_var
        features_data["buttons"]["rows"] = buttons_rows

    # ============================================================
    # FEATURE : STATUS DESC
    # ============================================================

    status_rows = []

    def build_status_config(parent, key):
        tk.Label(parent, text="Nombre de status_desc (min 2) :").pack(anchor="w")

        num_var = tk.IntVar(value=2)
        status_rows_frame = ttk.Frame(parent)

        def refresh_status(*_):
            for w in status_rows_frame.winfo_children():
                w.destroy()
            status_rows.clear()
            n = max(2, num_var.get())
            for i in range(1, n + 1):
                row = ttk.Frame(status_rows_frame)
                row.pack(fill="x", pady=1)
                tk.Label(row, text=f"Status desc {i} — Texte :").pack(side="left")
                sv = tk.StringVar()
                tk.Entry(row, textvariable=sv, width=36).pack(side="left", padx=4)
                status_rows.append(sv)

        spin = tk.Spinbox(parent, from_=2, to=10, textvariable=num_var,
                          width=4, command=refresh_status)
        spin.pack(anchor="w")
        status_rows_frame.pack(fill="x")
        refresh_status()
        features_data["status_desc"]["rows"] = status_rows

    # ============================================================
    # FEATURE : PROGRESS BARS
    # ============================================================

    pb_rows = []

    def build_pb_config(parent, key):
        tk.Label(parent, text="Nombre de progress bars :").pack(anchor="w")

        num_var = tk.IntVar(value=1)
        pb_rows_frame = ttk.Frame(parent)

        def refresh_pb(*_):
            for w in pb_rows_frame.winfo_children():
                w.destroy()
            pb_rows.clear()
            for i in range(1, num_var.get() + 1):
                lf = ttk.LabelFrame(pb_rows_frame, text=f"Progress Bar {i}")
                lf.pack(fill="x", pady=3)

                row1 = ttk.Frame(lf)
                row1.pack(fill="x", pady=1)
                tk.Label(row1, text="Nom affiché :").pack(side="left")
                nv = tk.StringVar()
                tk.Entry(row1, textvariable=nv, width=20).pack(side="left", padx=4)
                tk.Label(row1, text="Description :").pack(side="left")
                dv = tk.StringVar()
                tk.Entry(row1, textvariable=dv, width=24).pack(side="left", padx=4)

                row2 = ttk.Frame(lf)
                row2.pack(fill="x", pady=1)
                color_var = tk.StringVar(value="default_green = yes")
                tk.Radiobutton(row2, text="Vert (default_green)",
                               variable=color_var, value="default_green = yes").pack(side="left")
                tk.Radiobutton(row2, text="Rouge (default_bad)",
                               variable=color_var, value="default_bad = yes").pack(side="left")

                row3 = ttk.Frame(lf)
                row3.pack(fill="x", pady=1)
                tk.Label(row3, text="Start :").pack(side="left")
                sv = tk.StringVar(value="0")
                tk.Entry(row3, textvariable=sv, width=6).pack(side="left", padx=2)
                tk.Label(row3, text="Min :").pack(side="left")
                mnv = tk.StringVar(value="0")
                tk.Entry(row3, textvariable=mnv, width=6).pack(side="left", padx=2)
                tk.Label(row3, text="Max :").pack(side="left")
                mxv = tk.StringVar(value="100")
                tk.Entry(row3, textvariable=mxv, width=6).pack(side="left", padx=2)

                pb_rows.append({
                    "name": nv, "desc": dv, "color": color_var,
                    "start": sv, "min": mnv, "max": mxv,
                    "pb_index": i
                })

        spin = tk.Spinbox(parent, from_=1, to=10, textvariable=num_var,
                          width=4, command=refresh_pb)
        spin.pack(anchor="w")
        pb_rows_frame.pack(fill="x")
        refresh_pb()
        features_data["progress_bars"]["rows"] = pb_rows

    # ============================================================
    # FEATURES SIMPLES (accolades vides)
    # ============================================================

    def build_empty(parent, key):
        tk.Label(parent, text="Sera généré avec accolades vides.",
                 foreground="gray").pack(anchor="w")

    # ============================================================
    # AJOUT DES FEATURES AU PANNEAU
    # ============================================================

    # Important : initialiser features_data AVANT make_feature pour les features
    # qui accèdent à features_data["x"] dans leur build_config_fn

    features_data["buttons"] = {"enabled": None}
    features_data["status_desc"] = {"enabled": None}
    features_data["progress_bars"] = {"enabled": None}
    features_data["monthly_empty"] = {"enabled": None}
    features_data["yearly"] = {"enabled": None}
    features_data["modifiers"] = {"enabled": None}

    make_feature(scroll_frame, "buttons",       "Boutons",             build_buttons_config)
    make_feature(scroll_frame, "status_desc",   "Status desc",         build_status_config)
    make_feature(scroll_frame, "progress_bars", "Progress bars",       build_pb_config)
    make_feature(scroll_frame, "monthly_empty", "on_monthly_pulse (vide)", build_empty)
    make_feature(scroll_frame, "yearly",        "on_yearly_pulse (vide)",  build_empty)
    make_feature(scroll_frame, "modifiers",     "modifiers_while_active (vide)", build_empty)

    # ============================================================
    # BOUTON GÉNÉRER
    # ============================================================

    def on_generate():
        base_path = path_var.get().strip()
        tag = tag_var.get().strip()
        year = year_var.get().strip()
        title = title_var.get().strip()
        desc = desc_text.get("1.0", "end").strip()

        if not base_path or not tag or not year or not title:
            messagebox.showerror("Erreur", "Dossier, TAG, Année et Titre sont obligatoires.")
            return

        # ---- boutons ----
        num_buttons = 0
        buttons_data = []
        if features_data["buttons"]["enabled"].get():
            num_buttons = features_data["buttons"].get("num", tk.IntVar(value=0)).get()
            rows = features_data["buttons"].get("rows", [])
            for r in rows:
                buttons_data.append({
                    "name": r["name"].get(),
                    "desc": r["desc"].get(),
                    "tt1": r["tt1"].get() or "Nothing",
                    "tt2": r["tt2"].get() or "Nothing",
                })

        # ---- status_desc ----
        status_desc_list = None
        if features_data["status_desc"]["enabled"].get():
            rows = features_data["status_desc"].get("rows", [])
            status_desc_list = [r.get() for r in rows if r.get().strip()]
            if len(status_desc_list) < 2:
                messagebox.showerror("Erreur", "Status desc nécessite au minimum 2 entrées.")
                return

        # ---- progress bars ----
        progress_bars = None
        if features_data["progress_bars"]["enabled"].get():
            rows = features_data["progress_bars"].get("rows", [])
            progress_bars = []
            for r in rows:
                i = r["pb_index"]
                # la clé sera construite après avoir le JE index — on passe un placeholder
                # reconstruit dans main.py avec le vrai index JE
                progress_bars.append({
                    "pb_index": i,
                    "name": r["name"].get(),
                    "desc": r["desc"].get(),
                    "color": r["color"].get(),
                    "start": r["start"].get(),
                    "min": r["min"].get(),
                    "max": r["max"].get(),
                })

        try:
            create_full_je(
                base_path=base_path,
                tag=tag,
                year=year,
                title=title,
                desc=desc,
                num_buttons=num_buttons,
                buttons_data=buttons_data,
                progress_bars=progress_bars,
                status_desc=status_desc_list,
                monthly_empty=features_data["monthly_empty"]["enabled"].get(),
                yearly=features_data["yearly"]["enabled"].get(),
                modifiers=features_data["modifiers"]["enabled"].get(),
            )
            messagebox.showinfo("Succès", "Journal Entry générée avec succès !")
        except Exception as e:
            messagebox.showerror("Erreur", str(e))

    tk.Button(frame, text="Générer la JE", command=on_generate,
              bg="#4CAF50", fg="white", font=("Arial", 11, "bold"),
              pady=6).pack(pady=10)

    return frame
