import tkinter as tk
from tkinter import ttk, messagebox
from vic3_tool.main import create_full_je, create_je_goal_progress

# (label, template_format, [champs])
# Les accolades littérales dans le template sont doublées pour .format()
CONDITION_SPECS = [
    # --- Pays ---
    ("Pays Exist/This",         "AND = {{\n    exists = c:{v1}\n    c:{v1} ?= THIS\n}}",    ["TAG"]),
    ("Pays existe",             "exists = c:{v1}",                                          ["TAG"]),
    ("Est le pays (scope)",     "c:{v1} ?= THIS",                                           ["TAG"]),
    ("Pays n'existe pas",       "NOT = {{ exists = c:{v1} }}",                               ["TAG"]),
    # --- Variables ---
    ("A la variable",           "has_variable = {v1}",                                      ["Variable"]),
    ("N'a pas la variable",     "NOT = {{ has_variable = {v1} }}",                           ["Variable"]),
    ("Pays a la variable",      "c:{v1} = {{ has_variable = {v2} }}",                        ["TAG", "Variable"]),
    # --- Lois ---
    ("Loi active",              "has_law_or_variant = law_type:{v1}",                        ["Loi"]),
    ("Loi non active",          "NOT = {{ has_law_or_variant = law_type:{v1} }}",             ["Loi"]),
    # --- État ---
    ("Est humain",              "is_ai = no",                                                []),
    ("Est IA",                  "is_ai = yes",                                               []),
    ("En guerre",               "is_at_war = yes",                                           []),
    ("Pas en guerre",           "is_at_war = no",                                            []),
    # --- Objectif ---
    ("Objectif atteint",        "is_goal_complete = yes",                                    []),
    ("JE objectif atteint",     "scope:journal_entry = {{ is_goal_complete = yes }}",         []),
    # --- Temps ---
    ("Date >=",                 "game_date >= {v1}.1.1",                                     ["Année"]),
    ("Date <",                  "game_date < {v1}.1.1",                                      ["Année"]),
    # --- Libre ---
    ("Texte libre",             "{v1}",                                                      ["Condition"]),
]
CONDITION_NAMES = [s[0] for s in CONDITION_SPECS]
CONDITION_MAP   = {s[0]: (s[1], s[2]) for s in CONDITION_SPECS}

DLC_OPTIONS = [
    "", "has_mod_hmm_1804", "has_mod_hmm_1837", "has_mod_hmm_1861",
    "has_mod_hmm_1871", "has_mod_hmm_1890", "has_mod_hmm_1919",
]


def make_tt_list(parent, label_text, initial_values=None):
    """
    Widget liste de custom_tooltip avec label, entrées dynamiques et bouton +.
    Retourne un dict avec 'get' -> liste de valeurs courantes.
    """
    outer = ttk.Frame(parent)
    outer.pack(fill="x", pady=1)
    ttk.Label(outer, text=label_text, width=10).pack(side="left", anchor="nw")
    entries_frame = ttk.Frame(outer)
    entries_frame.pack(side="left", fill="x", expand=True)

    state = {"vars": []}
    cur_vals = list(initial_values) if initial_values else [""]

    def rebuild(vals=None):
        if vals is not None:
            cur_vals[:] = vals
        for w in entries_frame.winfo_children():
            w.destroy()
        state["vars"] = []
        for idx, val in enumerate(cur_vals):
            sv = tk.StringVar(value=val)
            cell = ttk.Frame(entries_frame)
            cell.pack(side="left", padx=2)
            ttk.Label(cell, text=f"TT{idx + 1}").pack(side="left")
            ttk.Entry(cell, textvariable=sv, width=14).pack(side="left", padx=2)

            def make_remove(i):
                def remove():
                    c = [v.get() for v in state["vars"]]
                    c.pop(i)
                    rebuild(c if c else [""])
                return remove

            tk.Button(cell, text="×", command=make_remove(idx),
                      fg="red", width=2).pack(side="left")
            state["vars"].append(sv)

    def add_tt():
        c = [v.get() for v in state["vars"]]
        c.append("")
        rebuild(c)

    rebuild()
    tk.Button(outer, text="+", command=add_tt, width=3).pack(side="left", padx=4)
    return {"get": lambda: [v.get() for v in state["vars"]], "rebuild": rebuild}


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
    # PANNEAU FEATURES — deux onglets
    # ============================================================

    feat_outer = ttk.LabelFrame(frame, text="Features")
    feat_outer.pack(fill="both", expand=True, padx=10, pady=4)

    feat_notebook = ttk.Notebook(feat_outer)
    feat_notebook.pack(fill="both", expand=True)

    # ── Onglet 1 : Standard ───────────────────────────────────────────────────
    tab_standard = ttk.Frame(feat_notebook)
    feat_notebook.add(tab_standard, text="Standard")

    canvas = tk.Canvas(tab_standard, borderwidth=0, highlightthickness=0)
    scrollbar = ttk.Scrollbar(tab_standard, orient="vertical", command=canvas.yview)
    scroll_frame = ttk.Frame(canvas)

    scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    # ── Onglet 2 : Goal Value + Progress Bar ──────────────────────────────────
    tab_goal = ttk.Frame(feat_notebook)
    feat_notebook.add(tab_goal, text="Goal Value + Progress Bar")

    gp_frame = ttk.Frame(tab_goal)
    gp_frame.pack(fill="x", padx=12, pady=8)

    tk.Label(gp_frame, text="Schéma : progress bar pilotée par une variable globale,\n"
             "la JE se complète quand current_value atteint goal_add_value.",
             foreground="gray", justify="left").pack(anchor="w", pady=(0, 8))

    # Variable globale (auto-générée)
    row_gv = ttk.Frame(gp_frame); row_gv.pack(fill="x", pady=3)
    tk.Label(row_gv, text="Variable globale :", width=20, anchor="w").pack(side="left")
    tk.Label(row_gv, text="(auto-générée : TAG_je_N_global_variable_progress_bar_1)",
             foreground="blue", font=("Consolas", 9)).pack(side="left", padx=4)

    # Goal value
    row_goal = ttk.Frame(gp_frame); row_goal.pack(fill="x", pady=3)
    tk.Label(row_goal, text="goal_add_value :", width=20, anchor="w").pack(side="left")
    gp_goal_value = tk.StringVar(value="6")
    tk.Entry(row_goal, textvariable=gp_goal_value, width=8).pack(side="left", padx=4)

    # Pulse
    row_pulse = ttk.Frame(gp_frame); row_pulse.pack(fill="x", pady=3)
    tk.Label(row_pulse, text="Incrément dans :", width=20, anchor="w").pack(side="left")
    gp_pulse = tk.StringVar(value="monthly")
    tk.Radiobutton(row_pulse, text="on_monthly_pulse", variable=gp_pulse, value="monthly").pack(side="left")
    tk.Radiobutton(row_pulse, text="on_yearly_pulse",  variable=gp_pulse, value="yearly").pack(side="left", padx=8)

    ttk.Separator(gp_frame, orient="horizontal").pack(fill="x", pady=8)
    tk.Label(gp_frame, text="Progress Bar", font=("", 10, "bold")).pack(anchor="w")

    # Nom affiché / desc
    row_pb1 = ttk.Frame(gp_frame); row_pb1.pack(fill="x", pady=3)
    tk.Label(row_pb1, text="Nom affiché :", width=20, anchor="w").pack(side="left")
    gp_pb_name = tk.StringVar()
    tk.Entry(row_pb1, textvariable=gp_pb_name, width=28).pack(side="left", padx=4)
    tk.Label(row_pb1, text="Desc :").pack(side="left")
    gp_pb_desc = tk.StringVar()
    tk.Entry(row_pb1, textvariable=gp_pb_desc, width=28).pack(side="left", padx=4)

    # Max value
    row_pb2 = ttk.Frame(gp_frame); row_pb2.pack(fill="x", pady=3)
    tk.Label(row_pb2, text="Max value :", width=20, anchor="w").pack(side="left")
    gp_pb_max = tk.StringVar(value="10")
    tk.Entry(row_pb2, textvariable=gp_pb_max, width=8).pack(side="left", padx=4)

    # Couleur
    row_pb3 = ttk.Frame(gp_frame); row_pb3.pack(fill="x", pady=3)
    tk.Label(row_pb3, text="Couleur :", width=20, anchor="w").pack(side="left")
    gp_pb_color = tk.StringVar(value="default_green = yes")
    for label, val in [
        ("Vert",         "default_green = yes"),
        ("Rouge",        "default_bad = yes"),
        ("Neutre",       "default = yes"),
        ("Or double",    "double_sided_gold = yes"),
        ("Rouge double", "double_sided_bad = yes"),
    ]:
        tk.Radiobutton(row_pb3, text=label, variable=gp_pb_color, value=val).pack(side="left")

    # Tooltip complete
    ttk.Separator(gp_frame, orient="horizontal").pack(fill="x", pady=6)
    row_tt = ttk.Frame(gp_frame); row_tt.pack(fill="x", pady=3)
    tk.Label(row_tt, text="Tooltip complete :", width=20, anchor="w").pack(side="left")
    gp_tt_complete = tk.StringVar(value="")
    tk.Entry(row_tt, textvariable=gp_tt_complete, width=54).pack(side="left", padx=4)
    tk.Label(gp_frame, text="(défaut auto : [GetGlobalVariable('...').GetValue|D])",
             foreground="gray", font=("", 8)).pack(anchor="w")

    # -------- initialisation features_data AVANT tout --------
    features_data = {
        "is_shown":      {"enabled": tk.BooleanVar(value=False), "rows": [], "dlc": None},
        "possible":      {"enabled": tk.BooleanVar(value=False), "rows": []},
        "complete":      {"enabled": tk.BooleanVar(value=False), "rows": []},
        "fail":          {"enabled": tk.BooleanVar(value=False), "rows": []},
        "buttons":       {"enabled": tk.BooleanVar(value=False), "num": None, "rows": []},
        "status_desc":   {"enabled": tk.BooleanVar(value=False), "rows": []},
        "progress_bars": {"enabled": tk.BooleanVar(value=False), "rows": []},
        "monthly_empty": {"enabled": tk.BooleanVar(value=False)},
        "yearly":        {"enabled": tk.BooleanVar(value=False)},
    }

    def make_feature(parent, feat_key, feat_label, build_config_fn):
        row_frame = ttk.Frame(parent)
        row_frame.pack(fill="x", padx=4, pady=2)
        config_frame = ttk.Frame(parent)
        enabled_var = features_data[feat_key]["enabled"]

        def toggle():
            if enabled_var.get():
                config_frame.pack(fill="x", padx=20, pady=2)
            else:
                config_frame.pack_forget()

        tk.Checkbutton(row_frame, text=feat_label,
                       variable=enabled_var, command=toggle,
                       anchor="w").pack(side="left")
        build_config_fn(config_frame, feat_key)

    # ============================================================
    # FEATURE : BOUTONS
    # ============================================================

    def build_buttons_config(parent, key):
        tk.Label(parent, text="Nombre de boutons :").pack(anchor="w")
        num_var = tk.IntVar(value=1)
        features_data["buttons"]["num"] = num_var
        btn_rows_frame = ttk.Frame(parent)

        def refresh_buttons(*_):
            saved = [
                {"name":          r["name"].get(),
                 "desc":          r["desc"].get(),
                 "cooldown":      r["cooldown"].get(),
                 "cooldown_unit": r["cooldown_unit"].get(),
                 "possible_tts":  r["possible_tts"]["get"](),
                 "effect_tts":    r["effect_tts"]["get"]()}
                for r in features_data["buttons"]["rows"]
            ]
            for w in btn_rows_frame.winfo_children():
                w.destroy()
            features_data["buttons"]["rows"].clear()
            for i in range(1, num_var.get() + 1):
                s = saved[i - 1] if i - 1 < len(saved) else {}
                lf = ttk.LabelFrame(btn_rows_frame, text=f"Bouton {i}")
                lf.pack(fill="x", pady=2)

                r1 = ttk.Frame(lf); r1.pack(fill="x", pady=1)
                tk.Label(r1, text="Nom").pack(side="left")
                nv = tk.StringVar(value=s.get("name", ""))
                tk.Entry(r1, textvariable=nv, width=16).pack(side="left", padx=4)
                tk.Label(r1, text="Desc").pack(side="left")
                dv = tk.StringVar(value=s.get("desc", ""))
                tk.Entry(r1, textvariable=dv, width=20).pack(side="left", padx=4)
                tk.Label(r1, text="Cooldown").pack(side="left", padx=(8, 0))
                cd = tk.StringVar(value=s.get("cooldown", ""))
                tk.Entry(r1, textvariable=cd, width=6).pack(side="left", padx=2)
                cu = tk.StringVar(value=s.get("cooldown_unit", "days"))
                tk.OptionMenu(r1, cu, "days", "months", "years").pack(side="left", padx=2)

                pos_tts = make_tt_list(lf, "possible :", s.get("possible_tts", [""]))
                eff_tts = make_tt_list(lf, "effect :",   s.get("effect_tts",   [""]))

                features_data["buttons"]["rows"].append(
                    {"name": nv, "desc": dv, "cooldown": cd, "cooldown_unit": cu,
                     "possible_tts": pos_tts, "effect_tts": eff_tts}
                )

        tk.Spinbox(parent, from_=1, to=10, textvariable=num_var,
                   width=4, command=refresh_buttons).pack(anchor="w")
        btn_rows_frame.pack(fill="x")
        refresh_buttons()

    # ============================================================
    # FEATURE : STATUS DESC
    # ============================================================

    def build_status_config(parent, key):
        # ── Sélecteur trigger ──
        trigger_mode_var = tk.StringVar(value="none")
        features_data["status_desc"]["trigger_mode"] = trigger_mode_var
        trig_f = ttk.Frame(parent)
        trig_f.pack(fill="x", pady=(0, 2))
        tk.Label(trig_f, text="Trigger :").pack(side="left")
        for lbl, val in [("Aucun", "none"), ("Nouvelle var globale", "new_var"),
                          ("Var progress bar", "pb_var"), ("Champ libre", "custom")]:
            tk.Radiobutton(trig_f, text=lbl, variable=trigger_mode_var,
                           value=val).pack(side="left", padx=2)

        var_row_f = ttk.Frame(parent)
        tk.Label(var_row_f, text="Variable :", width=10, anchor="w").pack(side="left")
        custom_var = tk.StringVar()
        features_data["status_desc"]["trigger_custom_var"] = custom_var
        trig_entry = ttk.Entry(var_row_f, textvariable=custom_var, width=46)
        trig_entry.pack(side="left", fill="x", expand=True)

        def _on_trig(*_):
            mode = trigger_mode_var.get()
            if mode == "none":
                var_row_f.pack_forget()
            else:
                var_row_f.pack(fill="x", pady=2)
                if mode == "new_var":
                    trig_entry.config(state="disabled")
                else:
                    if mode == "pb_var":
                        pb_rows = features_data["progress_bars"]["rows"]
                        if pb_rows:
                            custom_var.set(f"TAG_je_X_global_variable_progress_bar_{pb_rows[0]['pb_index']}")
                        else:
                            custom_var.set("TAG_je_X_global_variable_progress_bar_1")
                    trig_entry.config(state="normal")

        trigger_mode_var.trace_add("write", _on_trig)

        # ── Nombre de lignes ──
        tk.Label(parent, text="Nombre de status_desc (min 2) :").pack(anchor="w")
        num_var = tk.IntVar(value=2)
        status_rows_frame = ttk.Frame(parent)

        def refresh_status(*_):
            for w in status_rows_frame.winfo_children():
                w.destroy()
            features_data["status_desc"]["rows"].clear()
            n = max(2, num_var.get())
            for i in range(1, n + 1):
                row = ttk.Frame(status_rows_frame)
                row.pack(fill="x", pady=1)
                tk.Label(row, text=f"Status {i} :").pack(side="left")
                sv = tk.StringVar()
                tk.Entry(row, textvariable=sv, width=28).pack(side="left", padx=4)
                tk.Label(row, text="val=").pack(side="left")
                vv = tk.StringVar(value=str(i))
                tk.Entry(row, textvariable=vv, width=5).pack(side="left")
                features_data["status_desc"]["rows"].append({"text": sv, "value": vv})

        tk.Spinbox(parent, from_=2, to=10, textvariable=num_var,
                   width=4, command=refresh_status).pack(anchor="w")
        status_rows_frame.pack(fill="x")
        refresh_status()

    # ============================================================
    # FEATURE : PROGRESS BARS
    # ============================================================

    def build_pb_config(parent, key):
        pb_pulse_var = tk.StringVar(value="monthly")
        pulse_row = ttk.Frame(parent)
        pulse_row.pack(fill="x", pady=2)
        tk.Label(pulse_row, text="Pulse :").pack(side="left")
        tk.Radiobutton(pulse_row, text="on_monthly_pulse", variable=pb_pulse_var, value="monthly").pack(side="left")
        tk.Radiobutton(pulse_row, text="on_yearly_pulse",  variable=pb_pulse_var, value="yearly").pack(side="left", padx=8)
        features_data["progress_bars"]["pulse_var"] = pb_pulse_var

        tk.Label(parent, text="Nombre de progress bars :").pack(anchor="w")
        num_var = tk.IntVar(value=1)
        pb_rows_frame = ttk.Frame(parent)

        def refresh_pb(*_):
            for w in pb_rows_frame.winfo_children():
                w.destroy()
            features_data["progress_bars"]["rows"].clear()
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
                for label, val in [
                    ("Vert",           "default_green = yes"),
                    ("Rouge",          "default_bad = yes"),
                    ("Neutre",         "default = yes"),
                    ("Or double",      "double_sided_gold = yes"),
                    ("Rouge double",   "double_sided_bad = yes"),
                ]:
                    tk.Radiobutton(row2, text=label, variable=color_var, value=val).pack(side="left")

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

                row4 = ttk.Frame(lf)
                row4.pack(fill="x", pady=1)
                inv_var = tk.BooleanVar(value=False)
                tk.Checkbutton(row4, text="is_inverted", variable=inv_var).pack(side="left")
                sd_var = tk.BooleanVar(value=False)
                tk.Checkbutton(row4, text="second_desc", variable=sd_var).pack(side="left", padx=8)
                tk.Label(row4, text="monthly_progress (valeur) :").pack(side="left", padx=(8, 0))
                mp_val = tk.StringVar()
                tk.Entry(row4, textvariable=mp_val, width=6).pack(side="left", padx=2)
                tk.Label(row4, text="desc :").pack(side="left")
                mp_desc = tk.StringVar()
                tk.Entry(row4, textvariable=mp_desc, width=20).pack(side="left", padx=2)

                features_data["progress_bars"]["rows"].append({
                    "name": nv, "desc": dv, "color": color_var,
                    "start": sv, "min": mnv, "max": mxv,
                    "is_inverted": inv_var, "second_desc": sd_var,
                    "monthly_value": mp_val, "monthly_desc": mp_desc,
                    "pb_index": i
                })

        tk.Spinbox(parent, from_=1, to=10, textvariable=num_var,
                   width=4, command=refresh_pb).pack(anchor="w")
        pb_rows_frame.pack(fill="x")
        refresh_pb()

    # ============================================================
    # BUILDER GÉNÉRIQUE DE CONDITIONS (réutilisé par is_shown, possible, complete, fail)
    # ============================================================

    def build_condition_rows(parent, feat_key):
        rows_frame = ttk.Frame(parent)
        rows_frame.pack(fill="x")

        def add_row():
            row_data = {}
            row_frame = ttk.Frame(rows_frame)
            row_frame.pack(fill="x", pady=1)

            type_var = tk.StringVar(value=CONDITION_NAMES[0])
            v1_var   = tk.StringVar()
            v2_var   = tk.StringVar()
            not_var  = tk.BooleanVar(value=False)
            and_var  = tk.BooleanVar(value=False)
            or_var   = tk.BooleanVar(value=False)

            def toggle_and():
                if and_var.get(): or_var.set(False)

            def toggle_or():
                if or_var.get(): and_var.set(False)

            om = tk.OptionMenu(row_frame, type_var, *CONDITION_NAMES)
            om.config(width=22)
            om.pack(side="left")

            lbl1 = tk.Label(row_frame, width=8)
            ent1 = tk.Entry(row_frame, textvariable=v1_var, width=12)
            lbl2 = tk.Label(row_frame, width=8)
            ent2 = tk.Entry(row_frame, textvariable=v2_var, width=12)

            def update_fields(*_):
                _, fields = CONDITION_MAP[type_var.get()]
                if len(fields) >= 1:
                    lbl1.config(text=fields[0]); lbl1.pack(side="left")
                    ent1.pack(side="left", padx=2)
                else:
                    lbl1.pack_forget(); ent1.pack_forget()
                if len(fields) >= 2:
                    lbl2.config(text=fields[1]); lbl2.pack(side="left")
                    ent2.pack(side="left", padx=2)
                else:
                    lbl2.pack_forget(); ent2.pack_forget()

            type_var.trace_add("write", update_fields)
            update_fields()

            ttk.Separator(row_frame, orient="vertical").pack(side="left", fill="y", padx=6)
            tk.Checkbutton(row_frame, text="NOT", variable=not_var, fg="red").pack(side="left")
            tk.Checkbutton(row_frame, text="AND", variable=and_var, command=toggle_and, fg="blue").pack(side="left")
            tk.Checkbutton(row_frame, text="OR",  variable=or_var,  command=toggle_or,  fg="green").pack(side="left")

            def remove():
                row_frame.destroy()
                if row_data in features_data[feat_key]["rows"]:
                    features_data[feat_key]["rows"].remove(row_data)

            tk.Button(row_frame, text="×", command=remove, fg="red", width=2).pack(side="right")
            row_data.update({"type": type_var, "v1": v1_var, "v2": v2_var,
                             "not": not_var, "and": and_var, "or": or_var})
            features_data[feat_key]["rows"].append(row_data)

        tk.Button(parent, text="+ Ajouter condition", command=add_row).pack(anchor="w", pady=2)

    def build_is_shown_config(parent, key):
        dlc_frame = ttk.Frame(parent)
        dlc_frame.pack(fill="x", pady=(0, 4))
        tk.Label(dlc_frame, text="DLC requis :").pack(side="left")
        dlc_var = tk.StringVar(value="")
        tk.OptionMenu(dlc_frame, dlc_var, *DLC_OPTIONS).pack(side="left", padx=4)
        features_data["is_shown"]["dlc"] = dlc_var

        ttk.Separator(parent, orient="horizontal").pack(fill="x", pady=2)
        build_condition_rows(parent, "is_shown")

    def build_possible_config(parent, key):
        tk.Label(parent, text="game_date >= YEAR.1.1 est toujours inclus.",
                 foreground="gray").pack(anchor="w")
        build_condition_rows(parent, "possible")

    def build_complete_config(parent, key):
        build_condition_rows(parent, "complete")

    def build_fail_config(parent, key):
        build_condition_rows(parent, "fail")

    # ============================================================
    # FEATURES SIMPLES
    # ============================================================

    def build_empty(parent, key):
        tk.Label(parent, text="Sera généré avec accolades vides.",
                 foreground="gray").pack(anchor="w")

    # ============================================================
    # AJOUT DES FEATURES
    # ============================================================

    features_columns = ttk.Frame(scroll_frame)
    features_columns.pack(fill="x", padx=4, pady=2)

    col_left = ttk.Frame(features_columns)
    col_mid = ttk.Frame(features_columns)
    col_right = ttk.Frame(features_columns)
    col_left.pack(side="left", fill="x", expand=True, anchor="n")
    col_mid.pack(side="left", fill="x", expand=True, anchor="n", padx=12)
    col_right.pack(side="left", fill="x", expand=True, anchor="n")

    make_feature(col_left,  "is_shown",      "is_shown_when_inactive",      build_is_shown_config)
    make_feature(col_left,  "possible",      "possible (conditions supp.)", build_possible_config)
    make_feature(col_left,  "complete",      "complete",                    build_complete_config)
    make_feature(col_left,  "fail",          "fail",                        build_fail_config)

    make_feature(col_mid,   "buttons",       "Boutons",                     build_buttons_config)
    make_feature(col_mid,   "status_desc",   "Status desc",                 build_status_config)
    make_feature(col_mid,   "progress_bars", "Progress bars",               build_pb_config)

    make_feature(col_right, "monthly_empty", "on_monthly_pulse",            build_empty)
    make_feature(col_right, "yearly",        "on_yearly_pulse",             build_empty)

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

        # ── Onglet "Goal Value + Progress Bar" ───────────────────────────────
        if feat_notebook.index(feat_notebook.select()) == 1:
            goal_value  = gp_goal_value.get().strip()
            pb_name     = gp_pb_name.get().strip()
            pb_desc     = gp_pb_desc.get().strip()
            pb_max      = gp_pb_max.get().strip()
            pb_color    = gp_pb_color.get()
            pulse       = gp_pulse.get()
            tt_complete = gp_tt_complete.get().strip()

            if not goal_value or not pb_max:
                messagebox.showerror("Erreur", "Goal value et Max value sont obligatoires.")
                return
            try:
                create_je_goal_progress(
                    base_path=base_path, tag=tag, year=year, title=title, desc=desc,
                    goal_value=goal_value,
                    pb_name=pb_name, pb_desc=pb_desc,
                    pb_color=pb_color, pb_max_value=pb_max,
                    pulse=pulse, tt_complete=tt_complete,
                )
                messagebox.showinfo("Succès", "Journal Entry (Goal + Progress Bar) générée avec succès !")
            except Exception as e:
                messagebox.showerror("Erreur", f"{type(e).__name__}: {e!s}")
            return

        # ---- helpers conditions ----
        def apply_indent(cond, base):
            return "\n".join(base + line for line in cond.split("\n"))

        def collect_conditions(feat_key, base="        ", inner="            "):
            standalone, and_group, or_group = [], [], []
            for r in features_data[feat_key]["rows"]:
                tmpl, _ = CONDITION_MAP[r["type"].get()]
                try:
                    raw = tmpl.format(v1=r["v1"].get().strip(), v2=r["v2"].get().strip())
                except KeyError:
                    raw = tmpl.format(v1=r["v1"].get().strip())
                cond = f"NOT = {{ {raw} }}" if r["not"].get() else raw
                if r["and"].get():
                    and_group.append(apply_indent(cond, inner))
                elif r["or"].get():
                    or_group.append(apply_indent(cond, inner))
                else:
                    standalone.append(apply_indent(cond, base))
            if and_group:
                standalone.append(f"{base}AND = {{\n" + "\n".join(and_group) + f"\n{base}}}")
            if or_group:
                standalone.append(f"{base}OR = {{\n" + "\n".join(or_group) + f"\n{base}}}")
            return standalone

        # ---- is_shown_when_inactive ----
        is_shown_list = None
        if features_data["is_shown"]["enabled"].get():
            is_shown_list = collect_conditions("is_shown")
            dlc_var = features_data["is_shown"].get("dlc")
            if dlc_var and dlc_var.get():
                is_shown_list.insert(0, f"        {dlc_var.get()} = yes")

        # ---- possible (conditions supplémentaires) ----
        possible_cond = None
        if features_data["possible"]["enabled"].get():
            possible_cond = collect_conditions("possible")

        # ---- complete ----
        complete_cond = None
        if features_data["complete"]["enabled"].get():
            complete_cond = collect_conditions("complete")

        # ---- fail ----
        fail_cond = None
        if features_data["fail"]["enabled"].get():
            fail_cond = collect_conditions("fail")

        # ---- boutons ----
        num_buttons = 0
        buttons_data = []
        if features_data["buttons"]["enabled"].get():
            num_buttons = features_data["buttons"]["num"].get() if features_data["buttons"]["num"] else 0
            for r in features_data["buttons"]["rows"]:
                buttons_data.append({
                    "name":         r["name"].get(),
                    "desc":         r["desc"].get(),
                    "cooldown":      r["cooldown"].get().strip() or None,
                    "cooldown_unit": r["cooldown_unit"].get(),
                    "possible_tts": r["possible_tts"]["get"]() or ["Nothing"],
                    "effect_tts":   r["effect_tts"]["get"]()   or ["Nothing"],
                })

        # ---- status_desc ----
        status_desc_list = None
        status_desc_tvar = None
        status_desc_tvals = []
        if features_data["status_desc"]["enabled"].get():
            _sd_rows = features_data["status_desc"]["rows"]
            status_desc_list = [r["text"].get() for r in _sd_rows if r["text"].get().strip()]
            status_desc_tvals = [r["value"].get().strip() or str(i + 1)
                                 for i, r in enumerate(_sd_rows) if r["text"].get().strip()]
            if len(status_desc_list) < 2:
                messagebox.showerror("Erreur", "Status desc nécessite au minimum 2 entrées.")
                return
            _stm = features_data["status_desc"].get("trigger_mode")
            _smode = _stm.get() if _stm else "none"
            if _smode == "new_var":
                status_desc_tvar = f"{tag.upper()}_je_X_global_variable_1"
            elif _smode in ("pb_var", "custom"):
                _scv = features_data["status_desc"].get("trigger_custom_var")
                status_desc_tvar = _scv.get().strip() if _scv else None
            else:
                status_desc_tvar = None

        # ---- progress bars ----
        progress_bars = None
        if features_data["progress_bars"]["enabled"].get():
            progress_bars = []
            for r in features_data["progress_bars"]["rows"]:
                progress_bars.append({
                    "pb_index":      r["pb_index"],
                    "name":          r["name"].get(),
                    "desc":          r["desc"].get(),
                    "color":         r["color"].get(),
                    "start":         r["start"].get(),
                    "min":           r["min"].get(),
                    "max":           r["max"].get(),
                    "is_inverted":   r["is_inverted"].get(),
                    "second_desc":   r["second_desc"].get(),
                    "monthly_value": r["monthly_value"].get().strip() or None,
                    "monthly_desc":  r["monthly_desc"].get().strip() or None,
                })

        _pv = features_data["progress_bars"].get("pulse_var")
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
                pb_pulse=_pv.get() if _pv else "monthly",
                status_desc=status_desc_list,
                status_desc_trigger_var=status_desc_tvar,
                status_desc_trigger_vals=status_desc_tvals,
                monthly_empty=features_data["monthly_empty"]["enabled"].get(),
                yearly=features_data["yearly"]["enabled"].get(),
                is_shown=is_shown_list,
                possible_conditions=possible_cond,
                complete_conditions=complete_cond,
                fail_conditions=fail_cond,
            )
            messagebox.showinfo("Succès", "Journal Entry générée avec succès !")
        except Exception as e:
            messagebox.showerror("Erreur", f"{type(e).__name__}: {e!s}")

    tk.Button(frame, text="Générer la JE", command=on_generate,
              bg="#4CAF50", fg="white", font=("Arial", 11, "bold"),
              pady=6).pack(pady=10)

    return frame
