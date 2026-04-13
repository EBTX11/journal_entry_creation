import tkinter as tk
from tkinter import ttk, messagebox
import os
import re

from vic3_tool.generators.je_generator import generate_je_block, generate_je_goal_progress_block
from vic3_tool.generators.button_generator import generate_buttons
from vic3_tool.generators.localization_generator import generate_localization
from vic3_tool.generators.progress_bar_generator import generate_progress_bar
from vic3_tool.models.journal_entry import JournalEntry
from vic3_tool.utils.file_manager import read_file
from vic3_tool.utils.formatter import format_text
from vic3_tool.ui.tabs.create_tab import (
    CONDITION_SPECS, CONDITION_NAMES, CONDITION_MAP, DLC_OPTIONS, make_tt_list,
    apply_indent, collect_conditions,
)

# ================================================================
# UTILITAIRES DE PARSING
# ================================================================

def find_block_range(content, key):
    m = re.search(rf"{re.escape(key)}\s*=\s*\{{", content)
    if not m:
        return None
    start = m.start()
    i = m.end() - 1
    depth = 0
    while i < len(content):
        if content[i] == '{':
            depth += 1
        elif content[i] == '}':
            depth -= 1
            if depth == 0:
                return (start, i + 1)
        i += 1
    return None


def extract_named_block(content, name):
    m = re.search(rf"\b{re.escape(name)}\s*=\s*\{{", content)
    if not m:
        return None
    start = m.end() - 1
    depth = 0
    i = start
    while i < len(content):
        if content[i] == '{':
            depth += 1
        elif content[i] == '}':
            depth -= 1
            if depth == 0:
                return content[start + 1:i]
        i += 1
    return None


def match_to_condition(line):
    line = line.strip()
    base = {"type": "Texte libre", "v1": line, "v2": "",
            "not": False, "and": False, "or": False}

    W = r"[\w:]+"   # mot + deux-points (pour law_type:xxx etc.)
    S = r"\S+"      # tout sauf espace

    patterns = [
        # (type_name,             regex,                                    g_v1, g_v2)
        ("Pays existe",           rf"exists\s*=\s*c:({W})",                    1, None),
        ("Est le pays (scope)",   rf"c:({W})\s*\?=\s*THIS",                    1, None),
        ("Pays n'existe pas",     rf"NOT\s*=\s*\{{\s*exists\s*=\s*c:({W})\s*\}}", 1, None),
        ("A la variable",         rf"has_variable\s*=\s*({S})",                1, None),
        ("N'a pas la variable",   rf"NOT\s*=\s*\{{\s*has_variable\s*=\s*({S})\s*\}}", 1, None),
        ("Pays a la variable",    rf"c:({W})\s*=\s*\{{\s*has_variable\s*=\s*({S})\s*\}}", 1, 2),
        ("Loi active",            rf"has_law_or_variant\s*=\s*law_type:({S})", 1, None),
        ("Loi non active",        rf"NOT\s*=\s*\{{\s*has_law_or_variant\s*=\s*law_type:({S})\s*\}}", 1, None),
        ("Est humain",            r"is_ai\s*=\s*no",                           None, None),
        ("Est IA",                r"is_ai\s*=\s*yes",                          None, None),
        ("En guerre",             r"is_at_war\s*=\s*yes",                      None, None),
        ("Pas en guerre",         r"is_at_war\s*=\s*no",                       None, None),
        ("Objectif atteint",      r"is_goal_complete\s*=\s*yes",               None, None),
        ("JE objectif atteint",   r"scope:journal_entry\s*=\s*\{\s*is_goal_complete\s*=\s*yes\s*\}", None, None),
        ("Date >=",               r"game_date\s*>=\s*(\d+)(?:\.\d+\.\d+)?",   1, None),
        ("Date <",                r"game_date\s*<\s*(\d+)(?:\.\d+\.\d+)?",    1, None),
    ]

    for type_name, pattern, g1, g2 in patterns:
        m = re.fullmatch(pattern, line)
        if m:
            v1 = m.group(g1) if g1 else ""
            v2 = m.group(g2) if g2 else ""
            return {**base, "type": type_name, "v1": v1, "v2": v2}

    return base


def parse_condition_rows(block_text):
    if not block_text or not block_text.strip():
        return []
    rows = []
    lines = [l.strip() for l in block_text.split('\n') if l.strip()]
    idx = 0
    while idx < len(lines):
        line = lines[idx]
        if line == '}':
            idx += 1
            continue

        # AND = { ... }
        if re.match(r'^AND\s*=\s*\{', line):
            inner, depth = [], 1
            idx += 1
            while idx < len(lines) and depth > 0:
                depth += lines[idx].count('{') - lines[idx].count('}')
                if depth > 0:
                    inner.append(lines[idx])
                idx += 1
            # Pays Exist/This shortcut
            clean = [l for l in inner if l.strip() and l.strip() != '}']
            if len(clean) == 2:
                m1 = re.match(r'exists\s*=\s*c:(\w+)', clean[0])
                m2 = re.match(r'c:(\w+)\s*\?=\s*THIS', clean[1])
                if m1 and m2 and m1.group(1) == m2.group(1):
                    rows.append({"type": "Pays Exist/This", "v1": m1.group(1),
                                 "v2": "", "not": False, "and": False, "or": False})
                    continue
            for il in clean:
                r = match_to_condition(il)
                r["and"] = True
                rows.append(r)
            continue

        # OR = { ... }
        if re.match(r'^OR\s*=\s*\{', line):
            inner, depth = [], 1
            idx += 1
            while idx < len(lines) and depth > 0:
                depth += lines[idx].count('{') - lines[idx].count('}')
                if depth > 0:
                    inner.append(lines[idx])
                idx += 1
            for r in parse_condition_rows('\n'.join(inner)):
                r["or"] = True
                rows.append(r)
            continue

        # NOT = { single }
        m = re.match(r'^NOT\s*=\s*\{([^{}]+)\}', line)
        if m:
            r = match_to_condition(m.group(1).strip())
            r["not"] = True
            rows.append(r)
            idx += 1
            continue

        rows.append(match_to_condition(line))
        idx += 1
    return rows


def parse_je_data(je_path, loc_path, btn_path, pb_path, key):
    data = {
        "year": "1836", "title": "", "desc": "",
        "is_shown_dlc": "",
        "is_shown_rows": [], "possible_rows": [],
        "complete_rows": [], "fail_rows": [],
        "buttons": [], "progress_bars": [], "status_desc": [],
        "status_desc_trigger_var": "", "status_desc_trigger_values": [],
        "monthly_empty": False, "yearly": False,
        "goal_mode": False,
        "goal_global_var": "",
        "goal_value": "",
        "goal_pulse": "monthly",
        "goal_pb_name": "",
        "goal_pb_desc": "",
        "goal_pb_color": "default_green = yes",
        "goal_pb_max": "10",
        "goal_tt_complete": "",
    }
    je_content  = read_file(je_path)
    loc_content = read_file(loc_path)
    btn_content = read_file(btn_path)
    pb_content  = read_file(pb_path)

    br = find_block_range(je_content, key)
    if not br:
        return data
    block = je_content[br[0]:br[1]]
    safe  = re.escape(key)

    # Year
    m = re.search(r'game_date\s*>=\s*(\d+)', block)
    if m:
        data["year"] = m.group(1)

    # Title / Desc
    m = re.search(rf'^\s*{safe}:0\s+"(.*?)"', loc_content, re.MULTILINE)
    if m:
        data["title"] = m.group(1)
    m = re.search(rf'^\s*{safe}_reason:0\s+"(.*?)"', loc_content, re.MULTILINE)
    if m:
        data["desc"] = m.group(1).replace("\\n\\n", "\n\n")

    # is_shown_when_inactive
    is_shown_txt = extract_named_block(block, "is_shown_when_inactive")
    if is_shown_txt:
        dlc_m = re.search(r'(has_mod_hmm_\d+)\s*=\s*yes', is_shown_txt)
        if dlc_m:
            data["is_shown_dlc"] = dlc_m.group(1)
            is_shown_txt = is_shown_txt.replace(dlc_m.group(0), "").strip()
        data["is_shown_rows"] = parse_condition_rows(is_shown_txt)

    # possible (extra)
    possible_txt = extract_named_block(block, "possible")
    if possible_txt:
        clean = re.sub(r'game_date\s*[<>]=?\s*\d+\.\d+\.\d+', "", possible_txt).strip()
        data["possible_rows"] = parse_condition_rows(clean)

    # complete / fail
    complete_txt = extract_named_block(block, "complete")
    if complete_txt:
        data["complete_rows"] = parse_condition_rows(complete_txt)

    fail_txt = extract_named_block(block, "fail")
    if fail_txt is not None:
        data["fail_rows"] = parse_condition_rows(fail_txt)

    # Goal Value + Progress Bar mode
    m = re.search(r'current_value\s*=\s*\{\s*value\s*=\s*global_var:(\S+)', block)
    if m:
        data["goal_mode"] = True
        data["goal_global_var"] = m.group(1)
    m = re.search(r'goal_add_value\s*=\s*\{\s*value\s*=\s*(\S+)', block)
    if m:
        data["goal_value"] = m.group(1)
    if re.search(r'on_yearly_pulse\s*=\s*\{', block):
        data["goal_pulse"] = "yearly"
    m = re.search(rf'^\s*{safe}_tt_complete_1:0\s+"(.*?)"', loc_content, re.MULTILINE)
    if m:
        data["goal_tt_complete"] = m.group(1)

    # Flags
    data["monthly_empty"] = bool(re.search(r'on_monthly_pulse', block))
    data["yearly"]        = bool(re.search(r'on_yearly_pulse', block))

    # Buttons
    btn_keys = re.findall(rf'scripted_button\s*=\s*({re.escape(key)}_button_\d+)', block)
    for bk in btn_keys:
        sb = re.escape(bk)
        bd = {
            "name": "", "desc": "", "cooldown": "", "cooldown_unit": "days",
            "possible_tts": [], "effect_tts": [],
            "possible_modified": False, "possible_raw": None,
            "possible_existing_tt_count": 0,
            "visible_modified":  False, "visible_raw":  None,
            "effect_modified":   False, "effect_raw":   None,
            "effect_existing_tt_count": 0,
            "ai_chance_modified": False, "ai_chance_raw": None,
        }

        # Nom / Desc
        for field, pattern in [
            ("name", rf'^\s*{sb}:0\s+"(.*?)"'),
            ("desc", rf'^\s*{sb}_desc:0\s+"(.*?)"'),
        ]:
            mm = re.search(pattern, loc_content, re.MULTILINE)
            if mm:
                bd[field] = mm.group(1)

        # possible TTs — nouveau format _tt_possible_N
        j = 1
        while True:
            mm = re.search(rf'^\s*{sb}_tt_possible_{j}:0\s+"(.*?)"', loc_content, re.MULTILINE)
            if not mm:
                break
            bd["possible_tts"].append(mm.group(1))
            j += 1
        # Rétrocompat : ancien format _tt_1
        if not bd["possible_tts"]:
            mm = re.search(rf'^\s*{sb}_tt_1:0\s+"(.*?)"', loc_content, re.MULTILINE)
            if mm:
                bd["possible_tts"] = [mm.group(1)]

        # effect TTs — nouveau format _tt_effect_N
        j = 1
        while True:
            mm = re.search(rf'^\s*{sb}_tt_effect_{j}:0\s+"(.*?)"', loc_content, re.MULTILINE)
            if not mm:
                break
            bd["effect_tts"].append(mm.group(1))
            j += 1
        # Rétrocompat : ancien format _tt_2
        if not bd["effect_tts"]:
            mm = re.search(rf'^\s*{sb}_tt_2:0\s+"(.*?)"', loc_content, re.MULTILINE)
            if mm:
                bd["effect_tts"] = [mm.group(1)]

        if btn_content:
            bb = extract_named_block(btn_content, bk)
            if bb:
                # Cooldown
                cd = re.search(r'cooldown\s*=\s*\{\s*(days|months|years)\s*=\s*(\d+)', bb)
                if cd:
                    bd["cooldown_unit"] = cd.group(1)
                    bd["cooldown"]      = cd.group(2)

                # Détection de modification manuelle dans le bloc possible
                possible_raw = extract_named_block(bb, "possible")
                if possible_raw is not None:
                    # Supprime les custom_tooltip standards (nouveau et ancien format)
                    cleaned = re.sub(
                        rf'custom_tooltip\s*=\s*\{{\s*text\s*=\s*{re.escape(bk)}_tt_possible_\d+\s*\}}',
                        '', possible_raw
                    )
                    cleaned = re.sub(
                        rf'custom_tooltip\s*=\s*\{{\s*text\s*=\s*{re.escape(bk)}_tt_1\s*\}}',
                        '', cleaned
                    )
                    if cleaned.strip():
                        bd["possible_modified"] = True
                        bd["possible_raw"] = possible_raw

                    # Compter les TT STANDARDS déjà présents dans possible_raw
                    # (nouveau format _tt_possible_N + ancien _tt_1/_tt_2)
                    raw_count = len(re.findall(
                        rf'{re.escape(bk)}_tt_possible_\d+', possible_raw
                    ))
                    if raw_count == 0:
                        raw_count = len(re.findall(
                            rf'{re.escape(bk)}_tt_\d+\b', possible_raw
                        ))
                    bd["possible_existing_tt_count"] = raw_count

                # Détection de modification manuelle dans le bloc visible
                visible_raw = extract_named_block(bb, "visible")
                if visible_raw is not None and visible_raw.strip():
                    bd["visible_modified"] = True
                    bd["visible_raw"] = visible_raw

                # Détection de modification manuelle dans le bloc effect
                effect_raw = extract_named_block(bb, "effect")
                if effect_raw is not None:
                    raw_count = len(re.findall(
                        rf'{re.escape(bk)}_tt_effect_\d+', effect_raw
                    ))
                    if raw_count == 0:
                        raw_count = len(re.findall(
                            rf'{re.escape(bk)}_tt_2\b', effect_raw
                        ))
                    bd["effect_existing_tt_count"] = raw_count

                    cleaned_eff = re.sub(
                        rf'custom_tooltip\s*=\s*\{{\s*text\s*=\s*{re.escape(bk)}_tt_effect_\d+\s*\}}',
                        '', effect_raw
                    )
                    cleaned_eff = re.sub(
                        rf'custom_tooltip\s*=\s*\{{\s*text\s*=\s*{re.escape(bk)}_tt_2\s*\}}',
                        '', cleaned_eff
                    )
                    if cleaned_eff.strip():
                        bd["effect_modified"] = True
                        bd["effect_raw"] = effect_raw

                # Détection de modification manuelle dans le bloc ai_chance
                ai_raw = extract_named_block(bb, "ai_chance")
                if ai_raw is not None:
                    cleaned_ai = re.sub(r'value\s*=\s*10', '', ai_raw).strip()
                    if cleaned_ai:
                        bd["ai_chance_modified"] = True
                        bd["ai_chance_raw"] = ai_raw

        data["buttons"].append(bd)

    # Progress bars
    pb_keys = re.findall(
        rf'scripted_progress_bar\s*=\s*({re.escape(key)}_\d+_progress_bar)', block
    )
    for pk in pb_keys:
        sp = re.escape(pk)
        pb = {"name": "", "desc": "", "color": "default_green = yes",
              "start": "0", "min": "0", "max": "100",
              "is_inverted": False, "second_desc": False,
              "monthly_value": "", "monthly_desc": ""}
        for field, pattern in [
            ("name", rf'^\s*{sp}:0\s+"(.*?)"'),
            ("desc", rf'^\s*{sp}_desc:0\s+"(.*?)"'),
        ]:
            mm = re.search(pattern, loc_content, re.MULTILINE)
            if mm:
                val = mm.group(1)
                if field == "desc":
                    # Enlève le suffix [GetGlobalVariable(...).GetValue|D]/ N pour ne garder que le texte brut
                    val = re.sub(r'\s*\[GetGlobalVariable\([^)]+\)\.GetValue\|D\]/[^"]*', '', val).strip()
                pb[field] = val
        if pb_content:
            pbb = extract_named_block(pb_content, pk)
            if pbb:
                for ct in ["default_green", "default_bad", "default",
                           "double_sided_gold", "double_sided_bad"]:
                    if re.search(rf'{ct}\s*=\s*yes', pbb):
                        pb["color"] = f"{ct} = yes"
                        break
                for attr, pat in [("start", r'start_value\s*=\s*(\S+)'),
                                   ("min",   r'min_value\s*=\s*(\S+)'),
                                   ("max",   r'max_value\s*=\s*(\S+)')]:
                    mm = re.search(pat, pbb)
                    if mm:
                        pb[attr] = mm.group(1)
                pb["is_inverted"] = bool(re.search(r'is_inverted\s*=\s*yes', pbb))
                pb["second_desc"] = bool(re.search(r'second_desc', pbb))
                mm = re.search(
                    r'monthly_progress\s*=\s*\{[^}]*add\s*=\s*\{[^}]*value\s*=\s*(-?[\d.]+)', pbb)
                if mm:
                    pb["monthly_value"] = mm.group(1)
                mm = re.search(
                    r'monthly_progress\s*=\s*\{[^}]*add\s*=\s*\{[^}]*desc\s*=\s*"([^"]*)"', pbb)
                if mm:
                    pb["monthly_desc"] = mm.group(1)
        data["progress_bars"].append(pb)

    if data["goal_mode"] and data["progress_bars"]:
        first_pb = data["progress_bars"][0]
        data["goal_pb_name"] = first_pb["name"]
        data["goal_pb_desc"] = first_pb["desc"]
        data["goal_pb_color"] = first_pb["color"]
        data["goal_pb_max"] = first_pb["max"]

    # Status desc
    n, texts = 1, []
    while True:
        mm = re.search(rf'^\s*{safe}_status_desc_{n}:0\s+"(.*?)"', loc_content, re.MULTILINE)
        if not mm:
            break
        texts.append(mm.group(1))
        n += 1
    data["status_desc"] = texts

    # Status desc trigger — cherche dans le bloc JE
    sd_block = extract_named_block(block, "status_desc") or ""
    triggered_blocks = re.findall(r'triggered_desc\s*=\s*\{(.*?)\n\s*\}', sd_block, re.DOTALL)
    trig_m = re.search(r'global_var:(\S+)\s*(?:=|>|<=)\s*\S+', sd_block)
    if trig_m:
        data["status_desc_trigger_var"] = trig_m.group(1)
        specs = []
        for tb in triggered_blocks:
            fixed_m = re.search(r'global_var:\S+\s*=\s*(\S+)', tb)
            min_m = re.search(r'global_var:\S+\s*>\s*(\S+)', tb)
            max_m = re.search(r'global_var:\S+\s*<=\s*(\S+)', tb)
            if fixed_m:
                specs.append({"mode": "fixed", "value": fixed_m.group(1)})
            elif min_m or max_m:
                specs.append({
                    "mode": "range",
                    "min": min_m.group(1) if min_m else "",
                    "max": max_m.group(1) if max_m else "",
                })
        data["status_desc_trigger_values"] = specs
    else:
        data["status_desc_trigger_var"] = ""
        data["status_desc_trigger_values"] = []

    return data


def remove_loc_entries(content, key):
    safe = re.escape(key)
    return re.sub(rf'[ \t]*{safe}[^:\n]*:0[^\n]*\n', '', content)


def remove_blocks_for_key(content, key_prefix):
    pattern = re.escape(key_prefix)
    ranges = []
    for m in re.finditer(rf'(?m)^({pattern}\S*)\s*=\s*\{{', content):
        br = find_block_range(content, m.group(1))
        if br:
            ranges.append(br)
    for start, end in sorted(set(ranges), reverse=True):
        content = content[:start] + content[end:]
    return content.strip()


def patch_named_block_in(content, block_name, new_text):
    """Remplace block_name = { ... } dans content.
    Si absent, insère new_text avant la dernière accolade fermante."""
    br = find_block_range(content, block_name)
    if br:
        # Recule jusqu'au début de la ligne pour consommer les espaces de la ligne
        line_start = content.rfind('\n', 0, br[0]) + 1
        if content[line_start:br[0]].strip() == '':
            return content[:line_start] + new_text + content[br[1]:]
        return content[:br[0]] + new_text + content[br[1]:]
    last = content.rfind('}')
    if last >= 0:
        return content[:last] + '\n' + new_text + '\n' + content[last:]
    return content + '\n' + new_text


# ================================================================
# ONGLET GESTION JE
# ================================================================

def build_manage_tab(parent, path_var, tag_var):
    outer = ttk.Frame(parent)
    paned = ttk.PanedWindow(outer, orient="horizontal")
    paned.pack(fill="both", expand=True)

    # ── Panneau GAUCHE : sélection ───────────────────────────
    left = ttk.Frame(paned, width=200)
    paned.add(left, weight=0)

    ttk.Label(left, text="Journal Entries").pack(pady=(8, 2))
    tk.Button(left, text="Charger liste", command=lambda: load_je_list()).pack(pady=2)

    listbox_frame = ttk.Frame(left)
    listbox_frame.pack(fill="both", expand=True, padx=4)
    je_listbox = tk.Listbox(listbox_frame, selectmode="single", width=22)
    sb_list    = ttk.Scrollbar(listbox_frame, command=je_listbox.yview)
    je_listbox.config(yscrollcommand=sb_list.set)
    je_listbox.pack(side="left", fill="both", expand=True)
    sb_list.pack(side="right", fill="y")

    action_row = ttk.Frame(left)
    action_row.pack(pady=6)
    tk.Button(action_row, text="Charger JE sélectionnée",
              command=lambda: load_selected_je()).pack(side="left")
    tk.Button(action_row, text="X", width=3,
              command=lambda: delete_selected_je(), fg="red").pack(side="left", padx=(6, 0))

    current_key_var = tk.StringVar(value="")
    ttk.Label(left, textvariable=current_key_var,
              foreground="blue", wraplength=180).pack(pady=2)

    # ── Panneau DROIT : formulaire ───────────────────────────
    right = ttk.Frame(paned)
    paned.add(right, weight=1)

    feat_outer = ttk.LabelFrame(right, text="Édition de la Journal Entry")
    feat_outer.pack(fill="both", expand=True, padx=6, pady=6)

    canvas    = tk.Canvas(feat_outer, borderwidth=0, highlightthickness=0)
    scrollbar = ttk.Scrollbar(feat_outer, orient="vertical", command=canvas.yview)
    form      = ttk.Frame(canvas)
    form.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=form, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    # ── Champs de base ──────────────────────────────────────
    base = ttk.LabelFrame(form, text="Infos de base")
    base.pack(fill="x", padx=8, pady=6)
    base.columnconfigure(1, weight=1)

    ttk.Label(base, text="Année").grid(row=0, column=0, sticky="w", padx=6, pady=2)
    year_var = tk.StringVar()
    ttk.Entry(base, textvariable=year_var, width=10).grid(row=0, column=1, sticky="w", padx=6)

    ttk.Label(base, text="Titre").grid(row=1, column=0, sticky="w", padx=6, pady=2)
    title_var = tk.StringVar()
    ttk.Entry(base, textvariable=title_var, width=40).grid(row=1, column=1, sticky="w", padx=6)

    ttk.Label(base, text="Description").grid(row=2, column=0, sticky="nw", padx=6, pady=2)
    desc_text = tk.Text(base, height=3, width=40)
    desc_text.grid(row=2, column=1, sticky="w", padx=6, pady=2)

    tk.Button(base, text="Sauvegarder infos de base",
              command=lambda: save_infos(),
              bg="#2196F3", fg="white", padx=6).grid(row=3, column=1, sticky="w", padx=6, pady=4)

    mode_notebook = ttk.Notebook(form)
    mode_notebook.pack(fill="both", expand=True, padx=8, pady=(0, 6))

    tab_standard = ttk.Frame(mode_notebook)
    tab_goal = ttk.Frame(mode_notebook)
    mode_notebook.add(tab_standard, text="Standard")
    mode_notebook.add(tab_goal, text="Goal Value + Progress Bar")

    standard_container = ttk.Frame(tab_standard)
    standard_container.pack(fill="both", expand=True)

    gp_frame = ttk.Frame(tab_goal)
    gp_frame.pack(fill="x", padx=12, pady=8)

    ttk.Label(
        gp_frame,
        text="SchÃ©ma : progress bar pilotÃ©e par une variable globale,\n"
             "la JE se complÃ¨te quand current_value atteint goal_add_value.",
        foreground="gray",
        justify="left",
    ).pack(anchor="w", pady=(0, 8))

    row_gv = ttk.Frame(gp_frame); row_gv.pack(fill="x", pady=3)
    ttk.Label(row_gv, text="Variable globale :", width=20, anchor="w").pack(side="left")
    gp_global_var = tk.StringVar(value="(chargez une JE)")
    ttk.Label(row_gv, textvariable=gp_global_var,
              foreground="blue", font=("Consolas", 9)).pack(side="left", padx=4)

    row_goal = ttk.Frame(gp_frame); row_goal.pack(fill="x", pady=3)
    ttk.Label(row_goal, text="goal_add_value :", width=20, anchor="w").pack(side="left")
    gp_goal_value = tk.StringVar(value="6")
    ttk.Entry(row_goal, textvariable=gp_goal_value, width=8).pack(side="left", padx=4)

    row_pulse = ttk.Frame(gp_frame); row_pulse.pack(fill="x", pady=3)
    ttk.Label(row_pulse, text="IncrÃ©ment dans :", width=20, anchor="w").pack(side="left")
    gp_pulse = tk.StringVar(value="monthly")
    tk.Radiobutton(row_pulse, text="on_monthly_pulse", variable=gp_pulse, value="monthly").pack(side="left")
    tk.Radiobutton(row_pulse, text="on_yearly_pulse", variable=gp_pulse, value="yearly").pack(side="left", padx=8)

    ttk.Separator(gp_frame, orient="horizontal").pack(fill="x", pady=8)
    ttk.Label(gp_frame, text="Progress Bar", font=("", 10, "bold")).pack(anchor="w")

    row_pb1 = ttk.Frame(gp_frame); row_pb1.pack(fill="x", pady=3)
    ttk.Label(row_pb1, text="Nom affichÃ© :", width=20, anchor="w").pack(side="left")
    gp_pb_name = tk.StringVar()
    ttk.Entry(row_pb1, textvariable=gp_pb_name, width=28).pack(side="left", padx=4)
    ttk.Label(row_pb1, text="Desc :").pack(side="left")
    gp_pb_desc = tk.StringVar()
    ttk.Entry(row_pb1, textvariable=gp_pb_desc, width=28).pack(side="left", padx=4)

    row_pb2 = ttk.Frame(gp_frame); row_pb2.pack(fill="x", pady=3)
    ttk.Label(row_pb2, text="Max value :", width=20, anchor="w").pack(side="left")
    gp_pb_max = tk.StringVar(value="10")
    ttk.Entry(row_pb2, textvariable=gp_pb_max, width=8).pack(side="left", padx=4)

    row_pb3 = ttk.Frame(gp_frame); row_pb3.pack(fill="x", pady=3)
    ttk.Label(row_pb3, text="Couleur :", width=20, anchor="w").pack(side="left")
    gp_pb_color = tk.StringVar(value="default_green = yes")
    for lbl, val in [
        ("Vert", "default_green = yes"),
        ("Rouge", "default_bad = yes"),
        ("Neutre", "default = yes"),
        ("Or double", "double_sided_gold = yes"),
        ("Rouge double", "double_sided_bad = yes"),
    ]:
        tk.Radiobutton(row_pb3, text=lbl, variable=gp_pb_color, value=val).pack(side="left")

    ttk.Separator(gp_frame, orient="horizontal").pack(fill="x", pady=(8, 4))
    row_tt = ttk.Frame(gp_frame); row_tt.pack(fill="x", pady=3)
    ttk.Label(row_tt, text="Tooltip complete :", width=20, anchor="w").pack(side="left")
    gp_tt_complete = tk.StringVar(value="")
    ttk.Entry(row_tt, textvariable=gp_tt_complete, width=54).pack(side="left", padx=4)
    ttk.Label(gp_frame, text="(défaut auto : [GetGlobalVariable('...').GetValue|D])",
              foreground="gray", font=("", 8)).pack(anchor="w")

    tk.Button(gp_frame, text="Sauvegarder Goal Value + Progress Bar",
              command=lambda: save_goal_mode(),
              bg="#4CAF50", fg="white", padx=6).pack(anchor="w", pady=(12, 4))

    # ── features_data ──────────────────────────────────────
    features_data = {
        "is_shown":      {"enabled": tk.BooleanVar(value=False), "rows": [], "dlc": None, "_add_row": None, "_rows_frame": None},
        "possible":      {"enabled": tk.BooleanVar(value=False), "rows": [], "_add_row": None, "_rows_frame": None},
        "complete":      {"enabled": tk.BooleanVar(value=False), "rows": [], "_add_row": None, "_rows_frame": None},
        "fail":          {"enabled": tk.BooleanVar(value=False), "rows": [], "_add_row": None, "_rows_frame": None},
        "buttons":       {"enabled": tk.BooleanVar(value=False), "num": None, "rows": [], "_rows_frame": None},
        "status_desc":   {"enabled": tk.BooleanVar(value=False), "rows": [], "_rows_frame": None},
        "progress_bars": {"enabled": tk.BooleanVar(value=False), "rows": [], "_rows_frame": None},
        "monthly_empty": {"enabled": tk.BooleanVar(value=False)},
        "yearly":        {"enabled": tk.BooleanVar(value=False)},
    }

    scroll_frame = standard_container  # alias

    # ── make_feature (avec trace pour activation programmatique) ──
    def make_feature(parent, feat_key, feat_label, build_config_fn):
        row_frame    = ttk.Frame(parent)
        row_frame.pack(fill="x", padx=4, pady=2)
        config_frame = ttk.Frame(parent)
        enabled_var  = features_data[feat_key]["enabled"]

        def toggle(*_):
            if enabled_var.get():
                config_frame.pack(fill="x", padx=20, pady=2)
            else:
                config_frame.pack_forget()

        enabled_var.trace_add("write", toggle)
        tk.Checkbutton(row_frame, text=feat_label,
                       variable=enabled_var, anchor="w").pack(side="left")
        build_config_fn(config_frame, feat_key)
        tk.Button(config_frame, text="Sauvegarder cette section",
                  command=lambda k=feat_key: save_section(k),
                  bg="#4CAF50", fg="white", padx=6).pack(anchor="w", pady=(6, 2))

    # ── BUILDER GÉNÉRIQUE CONDITIONS ───────────────────────
    def build_condition_rows(parent, feat_key):
        rows_frame = ttk.Frame(parent)
        rows_frame.pack(fill="x")
        features_data[feat_key]["_rows_frame"] = rows_frame

        def add_row(type_name=None, v1="", v2="",
                    not_val=False, and_val=False, or_val=False):
            row_data  = {}
            row_frame = ttk.Frame(rows_frame)
            row_frame.pack(fill="x", pady=1)

            type_var = tk.StringVar(value=type_name or CONDITION_NAMES[0])
            v1_var   = tk.StringVar(value=v1)
            v2_var   = tk.StringVar(value=v2)
            not_var  = tk.BooleanVar(value=not_val)
            and_var  = tk.BooleanVar(value=and_val)
            or_var   = tk.BooleanVar(value=or_val)

            def toggle_and():
                if and_var.get(): or_var.set(False)

            def toggle_or():
                if or_var.get(): and_var.set(False)

            om = tk.OptionMenu(row_frame, type_var, *CONDITION_NAMES)
            om.config(width=22)
            om.pack(side="left")

            lbl1 = tk.Label(row_frame, width=8)
            ent1 = ttk.Entry(row_frame, textvariable=v1_var, width=12)
            lbl2 = tk.Label(row_frame, width=8)
            ent2 = ttk.Entry(row_frame, textvariable=v2_var, width=12)

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
            tk.Checkbutton(row_frame, text="AND", variable=and_var,
                           command=toggle_and, fg="blue").pack(side="left")
            tk.Checkbutton(row_frame, text="OR",  variable=or_var,
                           command=toggle_or, fg="green").pack(side="left")

            def remove():
                row_frame.destroy()
                if row_data in features_data[feat_key]["rows"]:
                    features_data[feat_key]["rows"].remove(row_data)

            tk.Button(row_frame, text="×", command=remove,
                      fg="red", width=2).pack(side="right")
            row_data.update({"type": type_var, "v1": v1_var, "v2": v2_var,
                             "not": not_var, "and": and_var, "or": or_var})
            features_data[feat_key]["rows"].append(row_data)

        features_data[feat_key]["_add_row"] = add_row
        tk.Button(parent, text="+ Ajouter condition",
                  command=add_row).pack(anchor="w", pady=2)

    # ── Build functions ────────────────────────────────────
    def build_is_shown_config(parent, key):
        dlc_frame = ttk.Frame(parent)
        dlc_frame.pack(fill="x", pady=(0, 4))
        ttk.Label(dlc_frame, text="DLC requis :").pack(side="left")
        dlc_var = tk.StringVar(value="")
        tk.OptionMenu(dlc_frame, dlc_var, *DLC_OPTIONS).pack(side="left", padx=4)
        features_data["is_shown"]["dlc"] = dlc_var
        ttk.Separator(parent, orient="horizontal").pack(fill="x", pady=2)
        build_condition_rows(parent, "is_shown")

    def build_possible_config(parent, key):
        ttk.Label(parent, text="game_date >= YEAR.1.1 toujours inclus.",
                  foreground="gray").pack(anchor="w")
        build_condition_rows(parent, "possible")

    def build_complete_config(parent, key):
        build_condition_rows(parent, "complete")

    def build_fail_config(parent, key):
        build_condition_rows(parent, "fail")

    def build_buttons_config(parent, key):
        ttk.Label(parent, text="Nombre de boutons :").pack(anchor="w")
        num_var = tk.IntVar(value=1)
        features_data["buttons"]["num"] = num_var
        btn_rows_frame = ttk.Frame(parent)
        features_data["buttons"]["_rows_frame"] = btn_rows_frame

        def refresh_buttons(*_):
            saved = [
                {"name":                       r["name"].get(),
                 "desc":                       r["desc"].get(),
                 "cooldown":                   r["cooldown"].get(),
                 "cooldown_unit":              r["cooldown_unit"].get(),
                 "possible_tts":               r["possible_tts"]["get"](),
                 "effect_tts":                 r["effect_tts"]["get"](),
                 "possible_modified":          r.get("possible_modified", False),
                 "possible_raw":               r.get("possible_raw", None),
                 "possible_existing_tt_count": r.get("possible_existing_tt_count", 0),
                 "visible_modified":           r.get("visible_modified", False),
                 "visible_raw":                r.get("visible_raw", None),
                 "effect_modified":            r.get("effect_modified", False),
                 "effect_raw":                 r.get("effect_raw", None),
                 "effect_existing_tt_count":   r.get("effect_existing_tt_count", 0),
                 "ai_chance_modified":         r.get("ai_chance_modified", False),
                 "ai_chance_raw":              r.get("ai_chance_raw", None)}
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
                ttk.Label(r1, text="Nom").pack(side="left")
                nv = tk.StringVar(value=s.get("name", ""))
                ttk.Entry(r1, textvariable=nv, width=16).pack(side="left", padx=4)
                ttk.Label(r1, text="Desc").pack(side="left")
                dv = tk.StringVar(value=s.get("desc", ""))
                ttk.Entry(r1, textvariable=dv, width=20).pack(side="left", padx=4)
                ttk.Label(r1, text="Cooldown").pack(side="left", padx=(8, 0))
                cd = tk.StringVar(value=s.get("cooldown", ""))
                ttk.Entry(r1, textvariable=cd, width=6).pack(side="left", padx=2)
                cu = tk.StringVar(value=s.get("cooldown_unit", "days"))
                ttk.OptionMenu(r1, cu, cu.get(), "days", "months", "years").pack(side="left", padx=2)

                pos_tts = make_tt_list(lf, "possible :", s.get("possible_tts", [""]))
                eff_tts = make_tt_list(lf, "effect :",   s.get("effect_tts",   [""]))

                pmod = s.get("possible_modified", False)
                praw = s.get("possible_raw", None)
                petc = s.get("possible_existing_tt_count", 0)
                vmod = s.get("visible_modified", False)
                vraw = s.get("visible_raw", None)
                emod = s.get("effect_modified", False)
                eraw = s.get("effect_raw", None)
                eetc = s.get("effect_existing_tt_count", 0)
                amod = s.get("ai_chance_modified", False)
                araw = s.get("ai_chance_raw", None)
                for warn in [
                    (pmod, "⚠ possible modifié manuellement — non écrasé à la sauvegarde"),
                    (vmod, "⚠ visible modifié manuellement — non écrasé à la sauvegarde"),
                    (emod, "⚠ effect modifié manuellement — non écrasé à la sauvegarde"),
                    (amod, "⚠ ai_chance modifié manuellement — non écrasé à la sauvegarde"),
                ]:
                    if warn[0]:
                        ttk.Label(lf, text=warn[1],
                                  foreground="orange").pack(anchor="w", pady=1)

                features_data["buttons"]["rows"].append({
                    "name": nv, "desc": dv, "cooldown": cd, "cooldown_unit": cu,
                    "possible_tts":               pos_tts,
                    "effect_tts":                 eff_tts,
                    "possible_modified":           pmod,
                    "possible_raw":               praw,
                    "possible_existing_tt_count": petc,
                    "visible_modified":            vmod,
                    "visible_raw":                vraw,
                    "effect_modified":             emod,
                    "effect_raw":                 eraw,
                    "effect_existing_tt_count":   eetc,
                    "ai_chance_modified":          amod,
                    "ai_chance_raw":              araw,
                })

        ttk.Spinbox(parent, from_=1, to=10, textvariable=num_var,
                    width=4, command=refresh_buttons).pack(anchor="w")
        btn_rows_frame.pack(fill="x")
        refresh_buttons()
        features_data["buttons"]["_refresh"] = refresh_buttons

    def build_status_config(parent, key):
        # ── Sélecteur de variable trigger ──
        trigger_mode_var = tk.StringVar(value="none")
        features_data["status_desc"]["trigger_mode"] = trigger_mode_var
        trig_frame = ttk.Frame(parent)
        trig_frame.pack(fill="x", pady=(0, 2))
        ttk.Label(trig_frame, text="Trigger :").pack(side="left")
        for lbl, val in [("Aucun", "none"), ("Nouvelle var globale", "new_var"),
                          ("Var progress bar", "pb_var"), ("Champ libre", "custom")]:
            tk.Radiobutton(trig_frame, text=lbl, variable=trigger_mode_var,
                           value=val).pack(side="left", padx=2)

        var_row_frame = ttk.Frame(parent)
        ttk.Label(var_row_frame, text="Variable :", width=10, anchor="w").pack(side="left")
        custom_var = tk.StringVar()
        features_data["status_desc"]["trigger_custom_var"] = custom_var
        trigger_entry = ttk.Entry(var_row_frame, textvariable=custom_var, width=46)
        trigger_entry.pack(side="left", fill="x", expand=True)

        def _on_trig_mode(*_):
            mode = trigger_mode_var.get()
            if mode == "none":
                var_row_frame.pack_forget()
            else:
                var_row_frame.pack(fill="x", pady=2)
                k = current_key_var.get()
                if mode == "new_var":
                    custom_var.set(f"{k}_global_variable_1" if k else "(chargez une JE)")
                    trigger_entry.config(state="disabled")
                elif mode == "pb_var":
                    pb_rows = features_data["progress_bars"]["rows"]
                    if pb_rows and k:
                        custom_var.set(f"{k}_global_variable_progress_bar_{pb_rows[0]['pb_index']}")
                    elif k:
                        custom_var.set(f"{k}_global_variable_progress_bar_1")
                    trigger_entry.config(state="normal")
                else:
                    trigger_entry.config(state="normal")

        trigger_mode_var.trace_add("write", _on_trig_mode)

        # ── Nombre de status_desc ──
        ttk.Label(parent, text="Nombre de status_desc (min 2) :").pack(anchor="w")
        num_var = tk.IntVar(value=2)
        status_rows_frame = ttk.Frame(parent)
        features_data["status_desc"]["_rows_frame"] = status_rows_frame

        def refresh_status(*_):
            for w in status_rows_frame.winfo_children():
                w.destroy()
            features_data["status_desc"]["rows"].clear()
            n = max(2, num_var.get())
            for i in range(1, n + 1):
                row = ttk.Frame(status_rows_frame)
                row.pack(fill="x", pady=1)
                ttk.Label(row, text=f"Status {i} :").pack(side="left")
                sv = tk.StringVar()
                ttk.Entry(row, textvariable=sv, width=28).pack(side="left", padx=4)
                vv = tk.StringVar(value=str(i))
                min_v = tk.StringVar()
                max_v = tk.StringVar()
                range_var = tk.BooleanVar(value=False)

                value_label = ttk.Label(row, text="val=")
                value_entry = ttk.Entry(row, textvariable=vv, width=5)
                range_check = ttk.Checkbutton(row, text="Plage", variable=range_var)
                min_label = ttk.Label(row, text="min >")
                min_entry = ttk.Entry(row, textvariable=min_v, width=5)
                max_label = ttk.Label(row, text="max <=")
                max_entry = ttk.Entry(row, textvariable=max_v, width=5)

                def toggle_mode(*_, _value_label=value_label, _value_entry=value_entry,
                                _min_label=min_label, _min_entry=min_entry,
                                _max_label=max_label, _max_entry=max_entry,
                                _range_var=range_var):
                    if _range_var.get():
                        _value_label.pack_forget()
                        _value_entry.pack_forget()
                        _min_label.pack(side="left")
                        _min_entry.pack(side="left", padx=(4, 0))
                        _max_label.pack(side="left", padx=(8, 0))
                        _max_entry.pack(side="left", padx=(4, 0))
                    else:
                        _min_label.pack_forget()
                        _min_entry.pack_forget()
                        _max_label.pack_forget()
                        _max_entry.pack_forget()
                        _value_label.pack(side="left")
                        _value_entry.pack(side="left", padx=(4, 0))

                range_check.pack(side="left", padx=(8, 0))
                toggle_mode()
                range_var.trace_add("write", toggle_mode)
                features_data["status_desc"]["rows"].append({
                    "text": sv,
                    "value": vv,
                    "use_range": range_var,
                    "min": min_v,
                    "max": max_v,
                })

        ttk.Spinbox(parent, from_=2, to=10, textvariable=num_var,
                    width=4, command=refresh_status).pack(anchor="w")
        status_rows_frame.pack(fill="x")
        refresh_status()
        features_data["status_desc"]["_refresh"] = refresh_status
        features_data["status_desc"]["_num_var"]  = num_var

    def build_pb_config(parent, key):
        pulse_var = tk.StringVar(value="monthly")
        pulse_row = ttk.Frame(parent)
        pulse_row.pack(fill="x", pady=2)
        ttk.Label(pulse_row, text="Pulse :").pack(side="left")
        tk.Radiobutton(pulse_row, text="on_monthly_pulse", variable=pulse_var, value="monthly").pack(side="left")
        tk.Radiobutton(pulse_row, text="on_yearly_pulse",  variable=pulse_var, value="yearly").pack(side="left", padx=8)
        features_data["progress_bars"]["pulse_var"] = pulse_var

        ttk.Label(parent, text="Nombre de progress bars :").pack(anchor="w")
        num_var = tk.IntVar(value=1)
        pb_rows_frame = ttk.Frame(parent)
        features_data["progress_bars"]["_rows_frame"] = pb_rows_frame

        def refresh_pb(*_):
            for w in pb_rows_frame.winfo_children():
                w.destroy()
            features_data["progress_bars"]["rows"].clear()
            for i in range(1, num_var.get() + 1):
                lf = ttk.LabelFrame(pb_rows_frame, text=f"Progress Bar {i}")
                lf.pack(fill="x", pady=3)
                r1 = ttk.Frame(lf); r1.pack(fill="x", pady=1)
                ttk.Label(r1, text="Nom :").pack(side="left")
                nv = tk.StringVar()
                ttk.Entry(r1, textvariable=nv, width=20).pack(side="left", padx=4)
                ttk.Label(r1, text="Desc :").pack(side="left")
                dv = tk.StringVar()
                ttk.Entry(r1, textvariable=dv, width=24).pack(side="left", padx=4)
                r2 = ttk.Frame(lf); r2.pack(fill="x", pady=1)
                color_var = tk.StringVar(value="default_green = yes")
                for lbl, val in [("Vert", "default_green = yes"),
                                  ("Rouge", "default_bad = yes"),
                                  ("Neutre", "default = yes"),
                                  ("Or double", "double_sided_gold = yes"),
                                  ("Rouge double", "double_sided_bad = yes")]:
                    tk.Radiobutton(r2, text=lbl, variable=color_var,
                                   value=val).pack(side="left")
                r3 = ttk.Frame(lf); r3.pack(fill="x", pady=1)
                for lbl, default, width in [("Start:", "0", 6), ("Min:", "0", 6), ("Max:", "100", 6)]:
                    ttk.Label(r3, text=lbl).pack(side="left")
                    v = tk.StringVar(value=default)
                    ttk.Entry(r3, textvariable=v, width=width).pack(side="left", padx=2)
                    if lbl == "Start:": sv = v
                    elif lbl == "Min:": mnv = v
                    else: mxv = v
                r4 = ttk.Frame(lf); r4.pack(fill="x", pady=1)
                inv_var = tk.BooleanVar(value=False)
                tk.Checkbutton(r4, text="is_inverted", variable=inv_var).pack(side="left")
                sd_var = tk.BooleanVar(value=False)
                tk.Checkbutton(r4, text="second_desc", variable=sd_var).pack(side="left", padx=8)
                ttk.Label(r4, text="monthly_progress :").pack(side="left", padx=(8, 0))
                mp_val = tk.StringVar()
                ttk.Entry(r4, textvariable=mp_val, width=6).pack(side="left", padx=2)
                ttk.Label(r4, text="desc :").pack(side="left")
                mp_desc = tk.StringVar()
                ttk.Entry(r4, textvariable=mp_desc, width=20).pack(side="left", padx=2)
                features_data["progress_bars"]["rows"].append({
                    "name": nv, "desc": dv, "color": color_var,
                    "start": sv, "min": mnv, "max": mxv,
                    "is_inverted": inv_var, "second_desc": sd_var,
                    "monthly_value": mp_val, "monthly_desc": mp_desc,
                    "pb_index": i,
                })

        ttk.Spinbox(parent, from_=1, to=10, textvariable=num_var,
                    width=4, command=refresh_pb).pack(anchor="w")
        pb_rows_frame.pack(fill="x")
        refresh_pb()
        features_data["progress_bars"]["_refresh"] = refresh_pb
        features_data["progress_bars"]["_num_var"]  = num_var

    def build_empty(parent, key):
        ttk.Label(parent, text="Sera généré avec accolades vides.",
                  foreground="gray").pack(anchor="w")

    # ── Sauvegarde chirurgicale Goal Value + Progress Bar ────────────
    def save_goal_mode():
        key = current_key_var.get()
        if not key:
            messagebox.showerror("Erreur", "Aucune JE chargée.")
            return
        _tag  = tag_var.get().upper()
        _base = path_var.get()
        _je_path  = os.path.join(_base, "common/journal_entries", f"{_tag}.txt")
        _loc_path = os.path.join(_base, "localization/english",
                                 "01_hmmf_je_localization_l_english.yml")
        _pb_path  = os.path.join(_base, "common/scripted_progress_bars", "hmmf_progressbar.txt")
        _year  = year_var.get().strip()
        _title = title_var.get().strip()
        _desc  = desc_text.get("1.0", "end").strip()

        global_var  = f"{key}_global_variable_progress_bar_1"
        tt_complete = gp_tt_complete.get().strip() or f"[GetGlobalVariable('{global_var}').GetValue|D]"
        goal_value  = gp_goal_value.get().strip()
        pb_name     = gp_pb_name.get().strip()
        pb_desc     = gp_pb_desc.get().strip()
        pb_max      = gp_pb_max.get().strip()
        pb_color    = gp_pb_color.get()
        pulse       = gp_pulse.get()

        if not goal_value or not pb_max:
            messagebox.showerror("Erreur",
                                 "Goal value et Max value sont obligatoires.")
            return

        pb_key   = f"{key}_1_progress_bar"
        safe_key = re.escape(key)

        try:
            je_content = read_file(_je_path)
            br = find_block_range(je_content, key)
            if not br:
                messagebox.showerror(
                    "Erreur",
                    "JE introuvable dans le fichier.\n"
                    "Utilisez 'Créer / Régénérer la JE' pour la créer d'abord."
                )
                return

            je_block = je_content[br[0]:br[1]]

            # complete block avec custom_tooltip
            je_block = patch_named_block_in(
                je_block, "complete",
                f"    complete = {{\n"
                f"        custom_tooltip = {{\n"
                f"            text = {key}_tt_complete_1\n"
                f"            scope:journal_entry = {{ is_goal_complete = yes }}\n"
                f"        }}\n"
                f"    }}"
            )
            # current_value
            je_block = patch_named_block_in(
                je_block, "current_value",
                f"    current_value = {{\n        value = global_var:{global_var}\n    }}"
            )
            # goal_add_value
            je_block = patch_named_block_in(
                je_block, "goal_add_value",
                f"    goal_add_value = {{\n        value = {goal_value}\n    }}"
            )
            # scripted_progress_bar (ligne)
            je_block = re.sub(
                rf'[ \t]*scripted_progress_bar\s*=\s*{safe_key}_\d+_progress_bar[ \t]*\n?',
                '', je_block)
            lb = je_block.rfind('}')
            je_block = je_block[:lb] + f"    scripted_progress_bar = {pb_key}\n" + je_block[lb:]

            # Bloc pulse (monthly ou yearly) — génère le bon et supprime l'autre
            def _pulse_snip(pulse_name):
                return (
                    f"    on_{pulse_name}_pulse = {{\n"
                    f"        effect = {{\n"
                    f"            scope:journal_entry ?= {{\n"
                    f"                if = {{\n"
                    f"                    limit = {{\n"
                    f"                    }}\n"
                    f"                    change_global_variable = {{\n"
                    f"                        name = {global_var}\n"
                    f"                        add = 1\n"
                    f"                    }}\n"
                    f"                }}\n"
                    f"            }}\n"
                    f"            je:{key} ?= {{\n"
                    f"                set_bar_progress = {{\n"
                    f"                    value = global_var:{global_var}\n"
                    f"                    name = {pb_key}\n"
                    f"                }}\n"
                    f"            }}\n"
                    f"        }}\n"
                    f"    }}"
                )

            other_pulse = "yearly" if pulse == "monthly" else "monthly"
            je_block = patch_named_block_in(je_block, f"on_{pulse}_pulse", _pulse_snip(pulse))
            other_br = find_block_range(je_block, f"on_{other_pulse}_pulse")
            if other_br:
                je_block = je_block[:other_br[0]].rstrip() + "\n" + je_block[other_br[1]:]

            # Écriture JE
            je_content = je_content[:br[0]] + je_block + je_content[br[1]:]
            with open(_je_path, "w", encoding="utf-8") as f:
                f.write(je_content)

            # Historique variable globale
            hist_path = os.path.join(_base, "common/history/global/00_hmmai_global.txt")
            if os.path.exists(hist_path):
                hist_content = read_file(hist_path)
                if global_var not in hist_content:
                    var_init = (
                        f"\n    set_global_variable = {{\n"
                        f"        name = {global_var}\n"
                        f"        value = 0\n"
                        f"    }}\n"
                    )
                    last_b = hist_content.rfind('}')
                    if last_b >= 0:
                        hist_content = hist_content[:last_b] + var_init + hist_content[last_b:]
                        with open(hist_path, "w", encoding="utf-8") as f:
                            f.write(hist_content)

            # PB file
            pb_data = {
                "key": pb_key, "name": pb_name, "desc": pb_desc, "color": pb_color,
                "start": "0", "min": "0", "max": pb_max,
                "is_inverted": False, "second_desc": False,
                "monthly_value": None, "monthly_desc": None,
            }
            pb_content = read_file(_pb_path) if os.path.exists(_pb_path) else ""
            pb_content = remove_blocks_for_key(pb_content, f"{key}_")
            pb_content = pb_content.rstrip() + "\n" + generate_progress_bar(pb_data)
            with open(_pb_path, "w", encoding="utf-8") as f:
                f.write(pb_content)

            # Loc : titre/desc + entrées PB + tt_complete
            _safe = re.escape(key)
            loc_content = read_file(_loc_path) if os.path.exists(_loc_path) else "l_english:\n"
            loc_content = re.sub(rf'[ \t]*{_safe}:0[^\n]*\n',                   '', loc_content)
            loc_content = re.sub(rf'[ \t]*{_safe}_reason:0[^\n]*\n',            '', loc_content)
            loc_content = re.sub(rf'[ \t]*{_safe}_tt_complete_1:0[^\n]*\n',     '', loc_content)
            loc_content = re.sub(rf'[ \t]*{_safe}_\d+_progress_bar[^\n]*\n',   '', loc_content)
            loc_content = loc_content.rstrip() + '\n\n'
            loc_content += f'  {key}:0 "{_title}"\n'
            loc_content += f'  {key}_reason:0 "{format_text(_desc)}"\n'
            loc_content += f'  {key}_tt_complete_1:0 "{tt_complete}"\n'
            loc_content += f'  {pb_key}:0 "{pb_name}"\n'
            loc_content += f'  {pb_key}_desc:0 "{pb_desc}"\n'
            with open(_loc_path, "w", encoding="utf-8") as f:
                f.write(loc_content)

            messagebox.showinfo("Succès", "Goal Value + Progress Bar sauvegardé !")

        except Exception as e:
            messagebox.showerror("Erreur", f"{type(e).__name__}: {e!s}")

    # ── Sauvegarde des infos de base (titre / desc / année) ──────────
    def save_infos():
        key = current_key_var.get()
        if not key:
            messagebox.showerror("Erreur", "Aucune JE chargée.")
            return
        _tag  = tag_var.get().upper()
        _base = path_var.get()
        _je_path  = os.path.join(_base, "common/journal_entries", f"{_tag}.txt")
        _loc_path = os.path.join(_base, "localization/english",
                                 "01_hmmf_je_localization_l_english.yml")
        _year  = year_var.get().strip()
        _title = title_var.get().strip()
        _desc  = desc_text.get("1.0", "end").strip()
        try:
            je_content = read_file(_je_path)
            br = find_block_range(je_content, key)
            if br:
                je_block = je_content[br[0]:br[1]]
                je_block = re.sub(r'(game_date\s*>=\s*)\d+', rf'\g<1>{_year}', je_block)
                je_content = je_content[:br[0]] + je_block + je_content[br[1]:]
                with open(_je_path, "w", encoding="utf-8") as f:
                    f.write(je_content)
            loc_content = read_file(_loc_path) if os.path.exists(_loc_path) else "l_english:\n"
            _safe = re.escape(key)
            loc_content = re.sub(rf'[ \t]*{_safe}:0[^\n]*\n',        '', loc_content)
            loc_content = re.sub(rf'[ \t]*{_safe}_reason:0[^\n]*\n', '', loc_content)
            loc_content = loc_content.rstrip() + '\n\n'
            loc_content += f'  {key}:0 "{_title}"\n'
            loc_content += f'  {key}_reason:0 "{format_text(_desc)}"\n'
            with open(_loc_path, "w", encoding="utf-8") as f:
                f.write(loc_content)
            messagebox.showinfo("Succès", "Infos de base sauvegardées !")
        except Exception as e:
            messagebox.showerror("Erreur", f"{type(e).__name__}: {e!s}")

    # ── Sauvegarde chirurgicale d'une seule section ───────────────────
    def save_section(feat_key):
        key = current_key_var.get()
        if not key:
            messagebox.showerror("Erreur", "Aucune JE chargée.")
            return
        _tag  = tag_var.get().upper()
        _base = path_var.get()
        _je_path  = os.path.join(_base, "common/journal_entries", f"{_tag}.txt")
        _loc_path = os.path.join(_base, "localization/english",
                                 "01_hmmf_je_localization_l_english.yml")
        _btn_path = os.path.join(_base, "common/scripted_buttons", f"{_tag}.txt")
        _pb_path  = os.path.join(_base, "common/scripted_progress_bars", "hmmf_progressbar.txt")
        _year  = year_var.get().strip()
        _title = title_var.get().strip()
        _desc  = desc_text.get("1.0", "end").strip()
        try:
            je_content = read_file(_je_path)
            br = find_block_range(je_content, key)
            if not br:
                messagebox.showerror(
                    "Erreur",
                    "JE introuvable dans le fichier.\n"
                    "Utilisez 'Créer / Régénérer la JE' pour la créer d'abord."
                )
                return
            je_block = je_content[br[0]:br[1]]
            safe_key = re.escape(key)
            mm = re.match(r'(.+)_je_(\d+)', key)
            je_tag   = mm.group(1) if mm else _tag
            je_index = int(mm.group(2)) if mm else 1
            je_obj   = JournalEntry(je_tag, je_index, _year, _title, _desc)

            if feat_key == "is_shown":
                cond = collect_conditions("is_shown", features_data)
                dlc_v = features_data["is_shown"].get("dlc")
                if dlc_v and dlc_v.get():
                    cond.insert(0, f"        {dlc_v.get()} = yes")
                cond_lines = "\n".join(cond) + "\n" if cond else ""
                snippet = f"    is_shown_when_inactive = {{\n{cond_lines}    }}"
                je_block = patch_named_block_in(je_block, "is_shown_when_inactive", snippet)

            elif feat_key == "possible":
                cond = collect_conditions("possible", features_data)
                cond_lines = "\n".join(cond) + "\n" if cond else ""
                snippet = f"    possible = {{\n        game_date >= {_year}.1.1\n{cond_lines}    }}"
                je_block = patch_named_block_in(je_block, "possible", snippet)

            elif feat_key == "complete":
                cond = collect_conditions("complete", features_data)
                cond_lines = "\n".join(cond) + "\n" if cond else ""
                snippet = f"    complete = {{\n{cond_lines}    }}"
                je_block = patch_named_block_in(je_block, "complete", snippet)

            elif feat_key == "fail":
                cond = collect_conditions("fail", features_data)
                cond_lines = "\n".join(cond) + "\n" if cond else ""
                snippet = f"    fail = {{\n{cond_lines}    }}"
                je_block = patch_named_block_in(je_block, "fail", snippet)

            elif feat_key == "buttons":
                num_btn  = features_data["buttons"]["num"].get() or 0
                btn_data = [{
                    "name":                       r["name"].get(),
                    "desc":                       r["desc"].get(),
                    "cooldown":                   r["cooldown"].get().strip() or None,
                    "cooldown_unit":              r["cooldown_unit"].get(),
                    "possible_tts":               r["possible_tts"]["get"]() or ["Nothing"],
                    "effect_tts":                 r["effect_tts"]["get"]()   or ["Nothing"],
                    "possible_modified":          r.get("possible_modified", False),
                    "possible_raw":               r.get("possible_raw", None),
                    "possible_existing_tt_count": r.get("possible_existing_tt_count", 0),
                    "visible_modified":           r.get("visible_modified", False),
                    "visible_raw":                r.get("visible_raw", None),
                    "effect_modified":            r.get("effect_modified", False),
                    "effect_raw":                 r.get("effect_raw", None),
                    "effect_existing_tt_count":   r.get("effect_existing_tt_count", 0),
                    "ai_chance_modified":         r.get("ai_chance_modified", False),
                    "ai_chance_raw":              r.get("ai_chance_raw", None),
                } for r in features_data["buttons"]["rows"]]
                # JE : lignes scripted_button
                je_block = re.sub(
                    rf'[ \t]*scripted_button\s*=\s*{safe_key}_button_\d+[ \t]*\n?', '', je_block)
                if num_btn:
                    btn_lines = "".join(
                        f"    scripted_button = {key}_button_{i}\n"
                        for i in range(1, num_btn + 1))
                    lb = je_block.rfind('}')
                    je_block = je_block[:lb] + btn_lines + je_block[lb:]
                # Fichier boutons
                btn_c = read_file(_btn_path) if os.path.exists(_btn_path) else ""
                btn_c = remove_blocks_for_key(btn_c, f"{key}_button_")
                if btn_data:
                    sep = "\n\n" if btn_c.strip() else ""
                    btn_c = btn_c.rstrip() + sep + generate_buttons(je_obj, btn_data)
                if btn_c.strip() or os.path.exists(_btn_path):
                    with open(_btn_path, "w", encoding="utf-8") as f:
                        f.write(btn_c)
                # Loc
                loc_c = read_file(_loc_path) if os.path.exists(_loc_path) else "l_english:\n"
                _safe = re.escape(key)
                loc_c = re.sub(rf'[ \t]*{_safe}_button_[^\n]*\n', '', loc_c)
                for i, bd in enumerate(btn_data, start=1):
                    bk = f"{key}_button_{i}"
                    loc_c += f'  {bk}:0 "{bd.get("name", "")}"\n'
                    loc_c += f'  {bk}_desc:0 "{bd.get("desc", "")}"\n'
                    for j, tt in enumerate(bd.get("possible_tts") or ["Nothing"], start=1):
                        loc_c += f'  {bk}_tt_possible_{j}:0 "{tt or "Nothing"}"\n'
                    for j, tt in enumerate(bd.get("effect_tts") or ["Nothing"], start=1):
                        loc_c += f'  {bk}_tt_effect_{j}:0 "{tt or "Nothing"}"\n'
                with open(_loc_path, "w", encoding="utf-8") as f:
                    f.write(loc_c)

            elif feat_key == "status_desc":
                sd_rows = features_data["status_desc"]["rows"]
                sd_list = [r["text"].get() for r in sd_rows if r["text"].get().strip()]
                sd_values = []
                for i, r in enumerate(sd_rows):
                    if not r["text"].get().strip():
                        continue
                    if r.get("use_range") and r["use_range"].get():
                        sd_values.append({
                            "mode": "range",
                            "min": r["min"].get().strip(),
                            "max": r["max"].get().strip(),
                        })
                    else:
                        sd_values.append({
                            "mode": "fixed",
                            "value": r["value"].get().strip() or str(i + 1),
                        })
                _tm = features_data["status_desc"].get("trigger_mode")
                _mode = _tm.get() if _tm else "none"
                if _mode == "none":
                    _tvar = None
                elif _mode == "new_var":
                    _tvar = f"{key}_global_variable_1"
                else:
                    _cv = features_data["status_desc"].get("trigger_custom_var")
                    _tvar = _cv.get().strip() if _cv else None
                entries = ""
                for i, text in enumerate(sd_list, start=1):
                    sk = f"{key}_status_desc_{i}"
                    spec = sd_values[i - 1] if i <= len(sd_values) else {"mode": "fixed", "value": str(i)}
                    if _tvar:
                        if isinstance(spec, dict) and spec.get("mode") == "range":
                            trig_lines = []
                            if spec.get("min", "").strip():
                                trig_lines.append(f"global_var:{_tvar} > {spec['min'].strip()}")
                            if spec.get("max", "").strip():
                                trig_lines.append(f"global_var:{_tvar} <= {spec['max'].strip()}")
                            trig_inner = (
                                "\n                    "
                                + "\n                    ".join(trig_lines)
                                + "\n                "
                            ) if trig_lines else ""
                        else:
                            val = spec.get("value", "").strip() if isinstance(spec, dict) else str(spec)
                            if not val:
                                val = str(i)
                            trig_inner = (f"\n                    global_var:{_tvar} = {val}\n"
                                          f"                ")
                    else:
                        trig_inner = ""
                    entries += (
                        f"\n            triggered_desc = {{\n"
                        f"                desc = {sk}\n"
                        f"                trigger = {{{trig_inner}}}\n"
                        f"            }}\n"
                    )
                snippet = f"    status_desc = {{\n        first_valid = {{{entries}        }}\n    }}"
                je_block = patch_named_block_in(je_block, "status_desc", snippet)
                # History — nouvelle variable globale
                if _mode == "new_var" and _tvar:
                    _hist_sd = os.path.join(_base, "common/history/global/00_hmmai_global.txt")
                    if os.path.exists(_hist_sd):
                        _hsd = read_file(_hist_sd)
                        if _tvar not in _hsd:
                            _vi_sd = (f"\n    set_global_variable = {{\n"
                                      f"        name = {_tvar}\n"
                                      f"        value = 0\n    }}\n")
                            _lb_sd = _hsd.rfind('}')
                            if _lb_sd >= 0:
                                _hsd = _hsd[:_lb_sd] + _vi_sd + _hsd[_lb_sd:]
                                with open(_hist_sd, "w", encoding="utf-8") as f:
                                    f.write(_hsd)
                # Loc
                loc_c = read_file(_loc_path) if os.path.exists(_loc_path) else "l_english:\n"
                _safe = re.escape(key)
                loc_c = re.sub(rf'[ \t]*{_safe}_status_desc_[^\n]*\n', '', loc_c)
                for i, txt in enumerate(sd_list, start=1):
                    loc_c += f'  {key}_status_desc_{i}:0 "{txt}"\n'
                with open(_loc_path, "w", encoding="utf-8") as f:
                    f.write(loc_c)

            elif feat_key == "progress_bars":
                def _build_pb_desc(raw_desc, pb_idx, pb_max):
                    gv  = f"{key}_global_variable_progress_bar_{pb_idx}"
                    sfx = f"[GetGlobalVariable('{gv}').GetValue|D]/ {pb_max}"
                    return (raw_desc + " " + sfx).strip() if raw_desc else sfx
                pb_list = [{
                    "pb_index":    r["pb_index"],
                    "key":         f"{key}_{r['pb_index']}_progress_bar",
                    "name":        r["name"].get(),
                    "desc":        _build_pb_desc(r["desc"].get(), r["pb_index"], r["max"].get()),
                    "color":       r["color"].get(),
                    "start":       r["start"].get(),
                    "min":         r["min"].get(),
                    "max":         r["max"].get(),
                    "is_inverted": r["is_inverted"].get(),
                    "second_desc": r["second_desc"].get(),
                    "monthly_value": r["monthly_value"].get().strip() or None,
                    "monthly_desc":  r["monthly_desc"].get().strip() or None,
                } for r in features_data["progress_bars"]["rows"]]
                # JE : lignes scripted_progress_bar
                je_block = re.sub(
                    rf'[ \t]*scripted_progress_bar\s*=\s*{safe_key}_\d+_progress_bar[ \t]*\n?',
                    '', je_block)
                _pulse_v  = features_data["progress_bars"].get("pulse_var")
                _pb_pulse = _pulse_v.get() if _pulse_v else "monthly"
                if pb_list:
                    pb_lines = "".join(
                        f"    scripted_progress_bar = {pb['key']}\n" for pb in pb_list)
                    lb = je_block.rfind('}')
                    je_block = je_block[:lb] + pb_lines + je_block[lb:]
                    pb_pulse_inner = "".join(
                        f"\n            je:{key} ?= {{\n"
                        f"                set_bar_progress = {{\n"
                        f"                    value = global_var:{key}_global_variable_progress_bar_{pb['pb_index']}\n"
                        f"                    name = {pb['key']}\n"
                        f"                }}\n"
                        f"            }}\n"
                        for pb in pb_list)
                    _pulse_snip = (
                        f"    on_{_pb_pulse}_pulse = {{\n"
                        f"        effect = {{{pb_pulse_inner}"
                        f"        }}\n"
                        f"    }}")
                    je_block = patch_named_block_in(je_block, f"on_{_pb_pulse}_pulse", _pulse_snip)
                    _other_pulse = "yearly" if _pb_pulse == "monthly" else "monthly"
                    _other_br = find_block_range(je_block, f"on_{_other_pulse}_pulse")
                    if _other_br:
                        je_block = je_block[:_other_br[0]].rstrip() + "\n" + je_block[_other_br[1]:]
                # Variables globales → history
                _hist_path = os.path.join(_base, "common/history/global/00_hmmai_global.txt")
                if os.path.exists(_hist_path) and pb_list:
                    _hist = read_file(_hist_path)
                    _hist_changed = False
                    for pb in pb_list:
                        _gv = f"{key}_global_variable_progress_bar_{pb['pb_index']}"
                        if _gv not in _hist:
                            _var_init = (
                                f"\n    set_global_variable = {{\n"
                                f"        name = {_gv}\n"
                                f"        value = 0\n"
                                f"    }}\n"
                            )
                            _last_b = _hist.rfind('}')
                            if _last_b >= 0:
                                _hist = _hist[:_last_b] + _var_init + _hist[_last_b:]
                                _hist_changed = True
                    if _hist_changed:
                        with open(_hist_path, "w", encoding="utf-8") as f:
                            f.write(_hist)
                # Fichier PB
                pb_c = read_file(_pb_path) if os.path.exists(_pb_path) else ""
                pb_c = remove_blocks_for_key(pb_c, f"{key}_")
                if pb_list:
                    pb_c = pb_c.rstrip() + "\n"
                    for pb in pb_list:
                        pb_c += generate_progress_bar(pb)
                if pb_c.strip() or os.path.exists(_pb_path):
                    with open(_pb_path, "w", encoding="utf-8") as f:
                        f.write(pb_c)
                # Loc
                loc_c = read_file(_loc_path) if os.path.exists(_loc_path) else "l_english:\n"
                _safe = re.escape(key)
                loc_c = re.sub(rf'[ \t]*{_safe}_\d+_progress_bar[^\n]*\n', '', loc_c)
                loc_c = re.sub(rf'[ \t]*{_safe}_tt_complete_1[^\n]*\n', '', loc_c)
                for pb in pb_list:
                    loc_c += f'  {pb["key"]}:0 "{pb["name"]}"\n'
                    loc_c += f'  {pb["key"]}_desc:0 "{pb["desc"]}"\n'
                with open(_loc_path, "w", encoding="utf-8") as f:
                    f.write(loc_c)

            elif feat_key == "monthly_empty":
                snippet = "    on_monthly_pulse = {\n        effect = {\n        }\n    }"
                je_block = patch_named_block_in(je_block, "on_monthly_pulse", snippet)

            elif feat_key == "yearly":
                snippet = "    on_yearly_pulse = {\n        effect = {\n        }\n    }"
                je_block = patch_named_block_in(je_block, "on_yearly_pulse", snippet)

            # Écriture JE
            je_content = je_content[:br[0]] + je_block + je_content[br[1]:]
            with open(_je_path, "w", encoding="utf-8") as f:
                f.write(je_content)
            messagebox.showinfo("Succès", "Section sauvegardée !")

        except Exception as e:
            messagebox.showerror("Erreur", f"{type(e).__name__}: {e!s}")

    # ── Assemblage du formulaire ────────────────────────────
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

    # ── Bouton sauvegarder ──────────────────────────────────
    tk.Button(right, text="Créer / Régénérer la JE complète", command=lambda: on_save(),
              bg="#FF9800", fg="white", font=("Arial", 10, "bold"),
              pady=6).pack(pady=8)

    # ================================================================
    # CHARGEMENT
    # ================================================================

    def load_je_list():
        je_listbox.delete(0, tk.END)
        tag       = tag_var.get().upper()
        base_path = path_var.get()
        path      = os.path.join(base_path, "common/journal_entries", f"{tag}.txt")
        if not os.path.exists(path):
            messagebox.showwarning("Avertissement", f"Fichier introuvable :\n{path}")
            return
        content = read_file(path)
        matches = re.findall(rf"{re.escape(tag)}_je_\d+", content)
        for m in sorted(set(matches)):
            je_listbox.insert(tk.END, m)

    def clear_condition_rows(feat_key):
        rf = features_data[feat_key].get("_rows_frame")
        if rf:
            for w in rf.winfo_children():
                w.destroy()
        features_data[feat_key]["rows"].clear()

    def clear_loaded_je():
        current_key_var.set("")
        year_var.set("")
        title_var.set("")
        desc_text.delete("1.0", "end")
        gp_global_var.set("(chargez une JE)")
        gp_goal_value.set("6")
        gp_pulse.set("monthly")
        gp_pb_name.set("")
        gp_pb_desc.set("")
        gp_pb_max.set("10")
        gp_pb_color.set("default_green = yes")
        gp_tt_complete.set("")
        mode_notebook.select(tab_standard)

        for fk in features_data:
            features_data[fk]["enabled"].set(False)
            if "rows" in features_data[fk]:
                clear_condition_rows(fk) if "_rows_frame" in features_data[fk] else None

    def delete_selected_je():
        sel = je_listbox.curselection()
        if not sel:
            messagebox.showwarning("Avertissement", "Sélectionnez une JE à supprimer.")
            return

        key = je_listbox.get(sel[0])
        tag = tag_var.get().upper()
        base_path = path_var.get()

        if not messagebox.askyesno("Confirmation", f"Supprimer {key} et toutes ses données liées ?"):
            return

        je_path   = os.path.join(base_path, "common/journal_entries", f"{tag}.txt")
        loc_path  = os.path.join(base_path, "localization/english", "01_hmmf_je_localization_l_english.yml")
        btn_path  = os.path.join(base_path, "common/scripted_buttons", f"{tag}.txt")
        pb_path   = os.path.join(base_path, "common/scripted_progress_bars", "hmmf_progressbar.txt")
        hist_path = os.path.join(base_path, "common/history/global/00_hmmai_global.txt")

        try:
            # ── Journal Entry ──
            je_content = read_file(je_path)
            br = find_block_range(je_content, key)
            if br:
                je_content = (je_content[:br[0]] + je_content[br[1]:]).strip()
                with open(je_path, "w", encoding="utf-8") as f:
                    f.write(je_content + ("\n" if je_content else ""))

            # ── Localisation (titre, desc, PBs, boutons, status_desc, tt_complete…) ──
            loc_content = read_file(loc_path) if os.path.exists(loc_path) else ""
            if loc_content:
                loc_content = remove_loc_entries(loc_content, key)
                with open(loc_path, "w", encoding="utf-8") as f:
                    f.write(loc_content.rstrip() + "\n")

            # ── Scripted buttons ──
            btn_content = read_file(btn_path) if os.path.exists(btn_path) else ""
            btn_content = remove_blocks_for_key(btn_content, f"{key}_button_")
            if btn_content.strip() or os.path.exists(btn_path):
                with open(btn_path, "w", encoding="utf-8") as f:
                    f.write(btn_content + ("\n" if btn_content else ""))

            # ── Scripted progress bars ──
            pb_content = read_file(pb_path) if os.path.exists(pb_path) else ""
            pb_content = remove_blocks_for_key(pb_content, f"{key}_")
            if pb_content.strip() or os.path.exists(pb_path):
                with open(pb_path, "w", encoding="utf-8") as f:
                    f.write(pb_content + ("\n" if pb_content else ""))

            # ── Variables globales dans l'historique ──
            # Supprime les blocs  set_global_variable = { name = {key}_global_variable_... }
            if os.path.exists(hist_path):
                hist_content = read_file(hist_path)
                safe_key = re.escape(key)
                cleaned = re.sub(
                    rf'\n[ \t]*set_global_variable\s*=\s*\{{[^{{}}]*name\s*=\s*{safe_key}_global_variable[^{{}}]*\}}',
                    '',
                    hist_content,
                )
                if cleaned != hist_content:
                    with open(hist_path, "w", encoding="utf-8") as f:
                        f.write(cleaned)

            je_listbox.delete(sel[0])
            clear_loaded_je()
            messagebox.showinfo("Succès", f"{key} a été supprimée.")
        except Exception as e:
            messagebox.showerror("Erreur", f"{type(e).__name__}: {e!s}")

    def load_selected_je():
        sel = je_listbox.curselection()
        if not sel:
            return
        key       = je_listbox.get(sel[0])
        tag       = tag_var.get().upper()
        base_path = path_var.get()

        je_path  = os.path.join(base_path, "common/journal_entries", f"{tag}.txt")
        loc_path = os.path.join(base_path, "localization/english", "01_hmmf_je_localization_l_english.yml")
        btn_path = os.path.join(base_path, "common/scripted_buttons", f"{tag}.txt")
        pb_path  = os.path.join(base_path, "common/scripted_progress_bars", "hmmf_progressbar.txt")

        d = parse_je_data(je_path, loc_path, btn_path, pb_path, key)
        current_key_var.set(key)

        # ── Réinitialiser toutes les features ──
        for fk in features_data:
            features_data[fk]["enabled"].set(False)
            if "rows" in features_data[fk]:
                clear_condition_rows(fk) if "_rows_frame" in features_data[fk] else None

        # ── Champs de base ──
        year_var.set(d["year"])
        title_var.set(d["title"])
        desc_text.delete("1.0", "end")
        desc_text.insert("1.0", d["desc"])
        _auto_var = f"{key}_global_variable_progress_bar_1"
        gp_global_var.set(_auto_var)
        gp_goal_value.set(d["goal_value"] or "6")
        gp_pulse.set(d["goal_pulse"] or "monthly")
        gp_pb_name.set(d["goal_pb_name"])
        gp_pb_desc.set(d["goal_pb_desc"])
        gp_pb_max.set(d["goal_pb_max"] or "10")
        gp_pb_color.set(d["goal_pb_color"] or "default_green = yes")
        gp_tt_complete.set(
            d["goal_tt_complete"] or
            f"[GetGlobalVariable('{_auto_var}').GetValue|D]"
        )
        mode_notebook.select(tab_goal if d["goal_mode"] else tab_standard)

        # ── is_shown ──
        if d["is_shown_rows"] or d["is_shown_dlc"]:
            features_data["is_shown"]["enabled"].set(True)
            if features_data["is_shown"]["dlc"] and d["is_shown_dlc"]:
                features_data["is_shown"]["dlc"].set(d["is_shown_dlc"])
            add_row_fn = features_data["is_shown"]["_add_row"]
            if add_row_fn:
                for r in d["is_shown_rows"]:
                    add_row_fn(r["type"], r["v1"], r["v2"],
                               r["not"], r["and"], r["or"])

        # ── possible ──
        if d["possible_rows"]:
            features_data["possible"]["enabled"].set(True)
            add_row_fn = features_data["possible"]["_add_row"]
            if add_row_fn:
                for r in d["possible_rows"]:
                    add_row_fn(r["type"], r["v1"], r["v2"],
                               r["not"], r["and"], r["or"])

        # ── complete ──
        if d["complete_rows"]:
            features_data["complete"]["enabled"].set(True)
            add_row_fn = features_data["complete"]["_add_row"]
            if add_row_fn:
                for r in d["complete_rows"]:
                    add_row_fn(r["type"], r["v1"], r["v2"],
                               r["not"], r["and"], r["or"])

        # ── fail ──
        if d["fail_rows"]:
            features_data["fail"]["enabled"].set(True)
            add_row_fn = features_data["fail"]["_add_row"]
            if add_row_fn:
                for r in d["fail_rows"]:
                    add_row_fn(r["type"], r["v1"], r["v2"],
                               r["not"], r["and"], r["or"])

        # ── Boutons ──
        if d["buttons"]:
            features_data["buttons"]["enabled"].set(True)
            # On injecte les données parsées dans saved avant le refresh
            # via un refresh avec données pré-chargées
            n = len(d["buttons"])
            features_data["buttons"]["num"].set(n)
            # Pré-charger les données dans une liste temporaire
            _preload = d["buttons"]

            def _refresh_with_data():
                btn_rows_frame = features_data["buttons"]["_rows_frame"]
                for w in btn_rows_frame.winfo_children():
                    w.destroy()
                features_data["buttons"]["rows"].clear()
                for i, bd in enumerate(_preload, start=1):
                    lf = ttk.LabelFrame(btn_rows_frame, text=f"Bouton {i}")
                    lf.pack(fill="x", pady=2)

                    r1 = ttk.Frame(lf); r1.pack(fill="x", pady=1)
                    ttk.Label(r1, text="Nom").pack(side="left")
                    nv = tk.StringVar(value=bd.get("name", ""))
                    ttk.Entry(r1, textvariable=nv, width=16).pack(side="left", padx=4)
                    ttk.Label(r1, text="Desc").pack(side="left")
                    dv = tk.StringVar(value=bd.get("desc", ""))
                    ttk.Entry(r1, textvariable=dv, width=20).pack(side="left", padx=4)
                    ttk.Label(r1, text="Cooldown").pack(side="left", padx=(8, 0))
                    cd = tk.StringVar(value=bd.get("cooldown", ""))
                    ttk.Entry(r1, textvariable=cd, width=6).pack(side="left", padx=2)
                    cu = tk.StringVar(value=bd.get("cooldown_unit", "days"))
                    ttk.OptionMenu(r1, cu, cu.get(), "days", "months", "years").pack(side="left", padx=2)

                    pos_tts = make_tt_list(lf, "possible :", bd.get("possible_tts") or [""])
                    eff_tts = make_tt_list(lf, "effect :",   bd.get("effect_tts")   or [""])

                    pmod = bd.get("possible_modified", False)
                    praw = bd.get("possible_raw", None)
                    petc = bd.get("possible_existing_tt_count", 0)
                    vmod = bd.get("visible_modified", False)
                    vraw = bd.get("visible_raw", None)
                    emod = bd.get("effect_modified", False)
                    eraw = bd.get("effect_raw", None)
                    eetc = bd.get("effect_existing_tt_count", 0)
                    amod = bd.get("ai_chance_modified", False)
                    araw = bd.get("ai_chance_raw", None)
                    for warn in [
                        (pmod, "⚠ possible modifié manuellement — non écrasé à la sauvegarde"),
                        (vmod, "⚠ visible modifié manuellement — non écrasé à la sauvegarde"),
                        (emod, "⚠ effect modifié manuellement — non écrasé à la sauvegarde"),
                        (amod, "⚠ ai_chance modifié manuellement — non écrasé à la sauvegarde"),
                    ]:
                        if warn[0]:
                            ttk.Label(lf, text=warn[1],
                                      foreground="orange").pack(anchor="w", pady=1)

                    features_data["buttons"]["rows"].append({
                        "name": nv, "desc": dv, "cooldown": cd, "cooldown_unit": cu,
                        "possible_tts":               pos_tts,
                        "effect_tts":                 eff_tts,
                        "possible_modified":           pmod,
                        "possible_raw":               praw,
                        "possible_existing_tt_count": petc,
                        "visible_modified":            vmod,
                        "visible_raw":                vraw,
                        "effect_modified":             emod,
                        "effect_raw":                 eraw,
                        "effect_existing_tt_count":   eetc,
                        "ai_chance_modified":          amod,
                        "ai_chance_raw":              araw,
                    })

            _refresh_with_data()

        # ── Status desc ──
        if d["status_desc"]:
            features_data["status_desc"]["enabled"].set(True)
            n = max(2, len(d["status_desc"]))
            features_data["status_desc"]["_num_var"].set(n)
            features_data["status_desc"]["_refresh"]()
            for i, txt in enumerate(d["status_desc"]):
                if i < len(features_data["status_desc"]["rows"]):
                    features_data["status_desc"]["rows"][i]["text"].set(txt)
            # Rétablir le trigger
            _tvar_d = d.get("status_desc_trigger_var", "")
            _tvals_d = d.get("status_desc_trigger_values", [])
            if _tvar_d:
                _tm_fd = features_data["status_desc"].get("trigger_mode")
                _cv_fd = features_data["status_desc"].get("trigger_custom_var")
                if _tm_fd:
                    _k = current_key_var.get()
                    if _tvar_d == f"{_k}_global_variable_1":
                        _tm_fd.set("new_var")
                    elif "_global_variable_progress_bar_" in _tvar_d:
                        _tm_fd.set("pb_var")
                        if _cv_fd:
                            _cv_fd.set(_tvar_d)
                    else:
                        _tm_fd.set("custom")
                        if _cv_fd:
                            _cv_fd.set(_tvar_d)
            for i, row in enumerate(features_data["status_desc"]["rows"]):
                if i < len(_tvals_d):
                    spec = _tvals_d[i]
                    if isinstance(spec, dict) and spec.get("mode") == "range":
                        row["use_range"].set(True)
                        row["min"].set(spec.get("min", ""))
                        row["max"].set(spec.get("max", ""))
                        row["value"].set("")
                    elif isinstance(spec, dict):
                        row["use_range"].set(False)
                        row["value"].set(spec.get("value", ""))
                    else:
                        row["use_range"].set(False)
                        row["value"].set(spec)

        # ── Progress bars ──
        if d["progress_bars"]:
            features_data["progress_bars"]["enabled"].set(True)
            n = len(d["progress_bars"])
            features_data["progress_bars"]["_num_var"].set(n)
            features_data["progress_bars"]["_refresh"]()
            for i, pb in enumerate(d["progress_bars"]):
                row = features_data["progress_bars"]["rows"][i]
                row["name"].set(pb["name"])
                row["desc"].set(pb["desc"])
                row["color"].set(pb["color"])
                row["start"].set(pb["start"])
                row["min"].set(pb["min"])
                row["max"].set(pb["max"])
                row["is_inverted"].set(pb["is_inverted"])
                row["second_desc"].set(pb["second_desc"])
                row["monthly_value"].set(pb["monthly_value"])
                row["monthly_desc"].set(pb["monthly_desc"])

        # ── Flags ──
        features_data["monthly_empty"]["enabled"].set(d["monthly_empty"])
        features_data["yearly"]["enabled"].set(d["yearly"])

    # ================================================================
    # SAUVEGARDE
    # ================================================================

    def on_save():
        key = current_key_var.get()
        if not key:
            messagebox.showerror("Erreur", "Aucune JE chargée.")
            return
        tag       = tag_var.get().upper()
        base_path = path_var.get()
        je_path   = os.path.join(base_path, "common/journal_entries", f"{tag}.txt")
        btn_path  = os.path.join(base_path, "common/scripted_buttons", f"{tag}.txt")
        loc_path  = os.path.join(base_path, "localization/english", "01_hmmf_je_localization_l_english.yml")
        pb_path   = os.path.join(base_path, "common/scripted_progress_bars", "hmmf_progressbar.txt")

        year  = year_var.get().strip()
        title = title_var.get().strip()
        desc  = desc_text.get("1.0", "end").strip()

        if mode_notebook.index(mode_notebook.select()) == 1:
            global_var  = f"{key}_global_variable_progress_bar_1"
            tt_complete = gp_tt_complete.get().strip() or f"[GetGlobalVariable('{global_var}').GetValue|D]"
            goal_value  = gp_goal_value.get().strip()
            pb_name     = gp_pb_name.get().strip()
            pb_desc     = gp_pb_desc.get().strip()
            pb_max      = gp_pb_max.get().strip()
            pb_color    = gp_pb_color.get()
            pulse       = gp_pulse.get()

            if not goal_value or not pb_max:
                messagebox.showerror("Erreur", "Goal value et Max value sont obligatoires.")
                return

            m = re.match(r'(.+)_je_(\d+)', key)
            je_tag   = m.group(1) if m else tag
            je_index = int(m.group(2)) if m else 1
            je       = JournalEntry(je_tag, je_index, year, title, desc)
            pb_key   = f"{key}_1_progress_bar"

            pb_data = {
                "key":           pb_key,
                "name":          pb_name,
                "desc":          pb_desc,
                "color":         pb_color,
                "start":         "0",
                "min":           "0",
                "max":           pb_max,
                "is_inverted":   False,
                "second_desc":   False,
                "monthly_value": None,
                "monthly_desc":  None,
            }

            new_je_block = generate_je_goal_progress_block(je, global_var, pb_key, goal_value, pulse)

            try:
                je_content = read_file(je_path)
                br = find_block_range(je_content, key)
                if br:
                    je_content = je_content[:br[0]] + new_je_block + je_content[br[1]:]
                else:
                    je_content += "\n" + new_je_block
                with open(je_path, "w", encoding="utf-8") as f:
                    f.write(je_content)

                # Historique variable globale
                hist_path = os.path.join(base_path, "common/history/global/00_hmmai_global.txt")
                if os.path.exists(hist_path):
                    hist_content = read_file(hist_path)
                    if global_var not in hist_content:
                        var_init = (
                            f"\n    set_global_variable = {{\n"
                            f"        name = {global_var}\n"
                            f"        value = 0\n"
                            f"    }}\n"
                        )
                        last_b = hist_content.rfind('}')
                        if last_b >= 0:
                            hist_content = hist_content[:last_b] + var_init + hist_content[last_b:]
                            with open(hist_path, "w", encoding="utf-8") as f:
                                f.write(hist_content)

                loc_content = read_file(loc_path) if os.path.exists(loc_path) else "l_english:\n"
                loc_content = remove_loc_entries(loc_content, key)
                loc_content = loc_content.rstrip() + "\n\n"
                loc_content += generate_localization(je, [], [pb_data], None)
                loc_content += f'  {key}_tt_complete_1:0 "{tt_complete}"\n'
                with open(loc_path, "w", encoding="utf-8") as f:
                    f.write(loc_content)

                btn_content = read_file(btn_path) if os.path.exists(btn_path) else ""
                btn_content = remove_blocks_for_key(btn_content, f"{key}_button_")
                if btn_content.strip() or os.path.exists(btn_path):
                    with open(btn_path, "w", encoding="utf-8") as f:
                        f.write(btn_content)

                pb_content = read_file(pb_path) if os.path.exists(pb_path) else ""
                pb_content = remove_blocks_for_key(pb_content, f"{key}_")
                pb_content = pb_content.rstrip() + "\n" + generate_progress_bar(pb_data)
                with open(pb_path, "w", encoding="utf-8") as f:
                    f.write(pb_content)

                messagebox.showinfo("Succès", f"{key} sauvegardée avec succès !")
            except Exception as e:
                messagebox.showerror("Erreur", f"{type(e).__name__}: {e!s}")
            return

        # ── is_shown ──
        is_shown_list = None
        if features_data["is_shown"]["enabled"].get():
            is_shown_list = collect_conditions("is_shown", features_data)
            dlc_var = features_data["is_shown"].get("dlc")
            if dlc_var and dlc_var.get():
                is_shown_list.insert(0, f"        {dlc_var.get()} = yes")

        # ── possible / complete / fail ──
        possible_cond  = collect_conditions("possible", features_data) if features_data["possible"]["enabled"].get() else None
        complete_cond  = collect_conditions("complete", features_data) if features_data["complete"]["enabled"].get() else None
        fail_cond      = collect_conditions("fail",     features_data) if features_data["fail"]["enabled"].get()     else None

        # ── Boutons ──
        num_buttons  = 0
        buttons_data = []
        if features_data["buttons"]["enabled"].get():
            num_buttons = features_data["buttons"]["num"].get() or 0
            for r in features_data["buttons"]["rows"]:
                buttons_data.append({
                    "name":                       r["name"].get(),
                    "desc":                       r["desc"].get(),
                    "cooldown":                   r["cooldown"].get().strip() or None,
                    "cooldown_unit":              r["cooldown_unit"].get(),
                    "possible_tts":               r["possible_tts"]["get"]() or ["Nothing"],
                    "effect_tts":                 r["effect_tts"]["get"]()   or ["Nothing"],
                    "possible_modified":          r.get("possible_modified", False),
                    "possible_raw":               r.get("possible_raw", None),
                    "possible_existing_tt_count": r.get("possible_existing_tt_count", 0),
                    "visible_modified":           r.get("visible_modified", False),
                    "visible_raw":                r.get("visible_raw", None),
                    "effect_modified":            r.get("effect_modified", False),
                    "effect_raw":                 r.get("effect_raw", None),
                    "effect_existing_tt_count":   r.get("effect_existing_tt_count", 0),
                    "ai_chance_modified":         r.get("ai_chance_modified", False),
                    "ai_chance_raw":              r.get("ai_chance_raw", None),
                })

        # ── Status desc ──
        status_desc_list   = None
        status_desc_tvar   = None
        status_desc_tvals  = []
        if features_data["status_desc"]["enabled"].get():
            _sd_rows = features_data["status_desc"]["rows"]
            status_desc_list = [r["text"].get() for r in _sd_rows if r["text"].get().strip()]
            status_desc_tvals = []
            for i, r in enumerate(_sd_rows):
                if not r["text"].get().strip():
                    continue
                if r.get("use_range") and r["use_range"].get():
                    status_desc_tvals.append({
                        "mode": "range",
                        "min": r["min"].get().strip(),
                        "max": r["max"].get().strip(),
                    })
                else:
                    status_desc_tvals.append({
                        "mode": "fixed",
                        "value": r["value"].get().strip() or str(i + 1),
                    })
            _stm = features_data["status_desc"].get("trigger_mode")
            _smode = _stm.get() if _stm else "none"
            if _smode == "new_var":
                status_desc_tvar = f"{key}_global_variable_1"
            elif _smode in ("pb_var", "custom"):
                _scv = features_data["status_desc"].get("trigger_custom_var")
                status_desc_tvar = _scv.get().strip() if _scv else None
            else:
                status_desc_tvar = None

        # ── Progress bars ──
        progress_bars = None
        if features_data["progress_bars"]["enabled"].get():
            progress_bars = []
            for r in features_data["progress_bars"]["rows"]:
                pb_key   = f"{key}_{r['pb_index']}_progress_bar"
                _gv_key  = f"{key}_global_variable_progress_bar_{r['pb_index']}"
                _mx      = r["max"].get()
                _sfx     = f"[GetGlobalVariable('{_gv_key}').GetValue|D]/ {_mx}"
                _rd      = r["desc"].get()
                progress_bars.append({
                    "pb_index": r["pb_index"], "key": pb_key,
                    "name": r["name"].get(),
                    "desc": (_rd + " " + _sfx).strip() if _rd else _sfx,
                    "color": r["color"].get(),
                    "start": r["start"].get(), "min": r["min"].get(), "max": _mx,
                    "is_inverted":   r["is_inverted"].get(),
                    "second_desc":   r["second_desc"].get(),
                    "monthly_value": r["monthly_value"].get().strip() or None,
                    "monthly_desc":  r["monthly_desc"].get().strip() or None,
                })

        # ── Construire l'objet JE ──
        m = re.match(r'(.+)_je_(\d+)', key)
        je_tag   = m.group(1) if m else tag
        je_index = int(m.group(2)) if m else 1
        je       = JournalEntry(je_tag, je_index, year, title, desc)

        try:
            je_content = read_file(je_path)
            br = find_block_range(je_content, key)

            if br:
                # ══ MODE CHIRURGICAL : JE déjà présente ══════════════════
                # Seules les sections cochées sont modifiées.
                # Les sections non cochées restent intactes dans le fichier.
                je_block = je_content[br[0]:br[1]]
                safe_key = re.escape(key)

                # Année : toujours mise à jour dans le bloc possible
                je_block = re.sub(r'(game_date\s*>=\s*)\d+', rf'\g<1>{year}', je_block)

                # is_shown_when_inactive
                if features_data["is_shown"]["enabled"].get():
                    cond_lines = "\n".join(is_shown_list) + "\n" if is_shown_list else ""
                    snippet = f"    is_shown_when_inactive = {{\n{cond_lines}    }}"
                    je_block = patch_named_block_in(je_block, "is_shown_when_inactive", snippet)

                # possible (conditions supplémentaires)
                if features_data["possible"]["enabled"].get():
                    cond_lines = "\n".join(possible_cond) + "\n" if possible_cond else ""
                    snippet = f"    possible = {{\n        game_date >= {year}.1.1\n{cond_lines}    }}"
                    je_block = patch_named_block_in(je_block, "possible", snippet)

                # complete
                if features_data["complete"]["enabled"].get():
                    cond_lines = "\n".join(complete_cond) + "\n" if complete_cond else ""
                    snippet = f"    complete = {{\n{cond_lines}    }}"
                    je_block = patch_named_block_in(je_block, "complete", snippet)

                # fail
                if features_data["fail"]["enabled"].get():
                    cond_lines = "\n".join(fail_cond) + "\n" if fail_cond else ""
                    snippet = f"    fail = {{\n{cond_lines}    }}"
                    je_block = patch_named_block_in(je_block, "fail", snippet)

                # Boutons (lignes scripted_button, pas un bloc nommé)
                if features_data["buttons"]["enabled"].get():
                    je_block = re.sub(
                        rf'[ \t]*scripted_button\s*=\s*{safe_key}_button_\d+[ \t]*\n?', '',
                        je_block
                    )
                    if num_buttons:
                        btn_lines = "".join(
                            f"    scripted_button = {key}_button_{i}\n"
                            for i in range(1, num_buttons + 1)
                        )
                        last_brace = je_block.rfind('}')
                        je_block = je_block[:last_brace] + btn_lines + je_block[last_brace:]

                # status_desc
                if features_data["status_desc"]["enabled"].get() and status_desc_list:
                    entries = ""
                    for i, text in enumerate(status_desc_list, start=1):
                        sk = f"{key}_status_desc_{i}"
                        spec = (status_desc_tvals[i - 1]
                                if status_desc_tvals and i <= len(status_desc_tvals)
                                else {"mode": "fixed", "value": str(i)})
                        if status_desc_tvar:
                            if isinstance(spec, dict) and spec.get("mode") == "range":
                                trig_lines = []
                                if spec.get("min", "").strip():
                                    trig_lines.append(
                                        f"global_var:{status_desc_tvar} > {spec['min'].strip()}"
                                    )
                                if spec.get("max", "").strip():
                                    trig_lines.append(
                                        f"global_var:{status_desc_tvar} <= {spec['max'].strip()}"
                                    )
                                trig_in = (
                                    "\n                    "
                                    + "\n                    ".join(trig_lines)
                                    + "\n                "
                                ) if trig_lines else ""
                            else:
                                val = spec.get("value", "").strip() if isinstance(spec, dict) else str(spec)
                                if not val:
                                    val = str(i)
                                trig_in = (f"\n                    global_var:{status_desc_tvar} = {val}\n"
                                           f"                ")
                        else:
                            trig_in = ""
                        entries += (
                            f"\n            triggered_desc = {{\n"
                            f"                desc = {sk}\n"
                            f"                trigger = {{{trig_in}}}\n"
                            f"            }}\n"
                        )
                    snippet = f"    status_desc = {{\n        first_valid = {{{entries}        }}\n    }}"
                    je_block = patch_named_block_in(je_block, "status_desc", snippet)
                    # History — nouvelle variable globale
                    if status_desc_tvar:
                        _stm2 = features_data["status_desc"].get("trigger_mode")
                        if _stm2 and _stm2.get() == "new_var":
                            _hp2 = os.path.join(base_path, "common/history/global/00_hmmai_global.txt")
                            if os.path.exists(_hp2):
                                _hc2 = read_file(_hp2)
                                if status_desc_tvar not in _hc2:
                                    _vi2 = (f"\n    set_global_variable = {{\n"
                                            f"        name = {status_desc_tvar}\n"
                                            f"        value = 0\n    }}\n")
                                    _lb2 = _hc2.rfind('}')
                                    if _lb2 >= 0:
                                        _hc2 = _hc2[:_lb2] + _vi2 + _hc2[_lb2:]
                                        with open(_hp2, "w", encoding="utf-8") as f:
                                            f.write(_hc2)

                # Progress bars (lignes scripted_progress_bar + pulse)
                if features_data["progress_bars"]["enabled"].get():
                    je_block = re.sub(
                        rf'[ \t]*scripted_progress_bar\s*=\s*{safe_key}_\d+_progress_bar[ \t]*\n?', '',
                        je_block
                    )
                    _pv  = features_data["progress_bars"].get("pulse_var")
                    _pbn = _pv.get() if _pv else "monthly"
                    if progress_bars:
                        pb_lines = "".join(
                            f"    scripted_progress_bar = {pb['key']}\n"
                            for pb in progress_bars
                        )
                        last_brace = je_block.rfind('}')
                        je_block = je_block[:last_brace] + pb_lines + je_block[last_brace:]
                        _pb_inner = "".join(
                            f"\n            je:{key} ?= {{\n"
                            f"                set_bar_progress = {{\n"
                            f"                    value = global_var:{key}_global_variable_progress_bar_{pb['pb_index']}\n"
                            f"                    name = {pb['key']}\n"
                            f"                }}\n"
                            f"            }}\n"
                            for pb in progress_bars
                        )
                        _pb_snip = (
                            f"    on_{_pbn}_pulse = {{\n"
                            f"        effect = {{{_pb_inner}"
                            f"        }}\n"
                            f"    }}"
                        )
                        je_block = patch_named_block_in(je_block, f"on_{_pbn}_pulse", _pb_snip)
                        _oth = "yearly" if _pbn == "monthly" else "monthly"
                        _oth_br = find_block_range(je_block, f"on_{_oth}_pulse")
                        if _oth_br:
                            je_block = je_block[:_oth_br[0]].rstrip() + "\n" + je_block[_oth_br[1]:]
                    # Variables globales → history
                    _hist_p = os.path.join(base_path, "common/history/global/00_hmmai_global.txt")
                    if os.path.exists(_hist_p) and progress_bars:
                        _hc = read_file(_hist_p)
                        _hchg = False
                        for pb in progress_bars:
                            _gvn = f"{key}_global_variable_progress_bar_{pb['pb_index']}"
                            if _gvn not in _hc:
                                _vi = (
                                    f"\n    set_global_variable = {{\n"
                                    f"        name = {_gvn}\n"
                                    f"        value = 0\n"
                                    f"    }}\n"
                                )
                                _lb2 = _hc.rfind('}')
                                if _lb2 >= 0:
                                    _hc = _hc[:_lb2] + _vi + _hc[_lb2:]
                                    _hchg = True
                        if _hchg:
                            with open(_hist_p, "w", encoding="utf-8") as f:
                                f.write(_hc)

                # on_monthly_pulse vide (seulement si pas de PB activées)
                if features_data["monthly_empty"]["enabled"].get() \
                        and not features_data["progress_bars"]["enabled"].get():
                    snippet = "    on_monthly_pulse = {\n        effect = {\n        }\n    }"
                    je_block = patch_named_block_in(je_block, "on_monthly_pulse", snippet)

                # on_yearly_pulse vide
                if features_data["yearly"]["enabled"].get():
                    snippet = "    on_yearly_pulse = {\n        effect = {\n        }\n    }"
                    je_block = patch_named_block_in(je_block, "on_yearly_pulse", snippet)

                # ── Écriture JE ──
                je_content = je_content[:br[0]] + je_block + je_content[br[1]:]
                with open(je_path, "w", encoding="utf-8") as f:
                    f.write(je_content)

                # ── Loc : chirurgical (seules les sections activées sont mises à jour) ──
                loc_content = read_file(loc_path) if os.path.exists(loc_path) else "l_english:\n"
                safe = re.escape(key)

                # Infos de base : titre + desc toujours mis à jour
                loc_content = re.sub(rf'[ \t]*{safe}:0[^\n]*\n', '', loc_content)
                loc_content = re.sub(rf'[ \t]*{safe}_reason:0[^\n]*\n', '', loc_content)
                loc_content = loc_content.rstrip() + '\n\n'
                loc_content += f'  {key}:0 "{title}"\n'
                loc_content += f'  {key}_reason:0 "{format_text(desc)}"\n'

                # Status desc
                if features_data["status_desc"]["enabled"].get() and status_desc_list:
                    loc_content = re.sub(rf'[ \t]*{safe}_status_desc_[^\n]*\n', '', loc_content)
                    for i, txt in enumerate(status_desc_list, start=1):
                        loc_content += f'  {key}_status_desc_{i}:0 "{txt}"\n'

                # Boutons
                if features_data["buttons"]["enabled"].get():
                    loc_content = re.sub(rf'[ \t]*{safe}_button_[^\n]*\n', '', loc_content)
                    for i, bd in enumerate(buttons_data, start=1):
                        btn_k = f"{key}_button_{i}"
                        loc_content += f'  {btn_k}:0 "{bd.get("name", "")}"\n'
                        loc_content += f'  {btn_k}_desc:0 "{bd.get("desc", "")}"\n'
                        for j, tt in enumerate(bd.get("possible_tts") or ["Nothing"], start=1):
                            loc_content += f'  {btn_k}_tt_possible_{j}:0 "{tt or "Nothing"}"\n'
                        for j, tt in enumerate(bd.get("effect_tts") or ["Nothing"], start=1):
                            loc_content += f'  {btn_k}_tt_effect_{j}:0 "{tt or "Nothing"}"\n'

                # Progress bars
                if features_data["progress_bars"]["enabled"].get() and progress_bars:
                    loc_content = re.sub(rf'[ \t]*{safe}_\d+_progress_bar[^\n]*\n', '', loc_content)
                    for pb in progress_bars:
                        loc_content += f'  {pb["key"]}:0 "{pb["name"]}"\n'
                        loc_content += f'  {pb["key"]}_desc:0 "{pb["desc"]}"\n'

                with open(loc_path, "w", encoding="utf-8") as f:
                    f.write(loc_content)

                # ── Btn file : seulement si boutons activés ──
                if features_data["buttons"]["enabled"].get():
                    if os.path.exists(btn_path):
                        btn_content = read_file(btn_path)
                    else:
                        btn_content = ""
                    btn_content = remove_blocks_for_key(btn_content, f"{key}_button_")
                    if buttons_data:
                        sep = "\n\n" if btn_content.strip() else ""
                        btn_content = btn_content.rstrip() + sep + generate_buttons(je, buttons_data)
                    if btn_content.strip() or os.path.exists(btn_path):
                        with open(btn_path, "w", encoding="utf-8") as f:
                            f.write(btn_content)

                # ── PB file : seulement si progress bars activées ──
                if features_data["progress_bars"]["enabled"].get():
                    pb_content = read_file(pb_path) if os.path.exists(pb_path) else ""
                    pb_content = remove_blocks_for_key(pb_content, f"{key}_")
                    if progress_bars:
                        pb_content = pb_content.rstrip() + "\n"
                        for pb in progress_bars:
                            pb_content += generate_progress_bar(pb)
                    if pb_content.strip() or os.path.exists(pb_path):
                        with open(pb_path, "w", encoding="utf-8") as f:
                            f.write(pb_content)

                messagebox.showinfo("Succès", f"{key} sauvegardée avec succès !")
                return

            # ══ MODE COMPLET : nouvelle JE (bloc absent) ═════════════════
            _cpv = features_data["progress_bars"].get("pulse_var")
            options = {
                "buttons":                  num_buttons,
                "progress_bars":            progress_bars,
                "pb_pulse":                 _cpv.get() if _cpv else "monthly",
                "status_desc":              status_desc_list,
                "status_desc_trigger_var":  status_desc_tvar,
                "status_desc_trigger_vals": status_desc_tvals,
                "monthly_empty":            features_data["monthly_empty"]["enabled"].get(),
                "yearly":                   features_data["yearly"]["enabled"].get(),
                "is_shown":                 is_shown_list,
                "possible_conditions":      possible_cond,
                "complete_conditions":      complete_cond,
                "fail_conditions":          fail_cond,
            }
            # History — nouvelle variable globale status_desc
            if status_desc_tvar:
                _stm3 = features_data["status_desc"].get("trigger_mode")
                if _stm3 and _stm3.get() == "new_var":
                    _hp3 = os.path.join(base_path, "common/history/global/00_hmmai_global.txt")
                    if os.path.exists(_hp3):
                        _hc3 = read_file(_hp3)
                        if status_desc_tvar not in _hc3:
                            _vi3 = (f"\n    set_global_variable = {{\n"
                                    f"        name = {status_desc_tvar}\n"
                                    f"        value = 0\n    }}\n")
                            _lb3b = _hc3.rfind('}')
                            if _lb3b >= 0:
                                _hc3 = _hc3[:_lb3b] + _vi3 + _hc3[_lb3b:]
                                with open(_hp3, "w", encoding="utf-8") as f:
                                    f.write(_hc3)

            new_je_block = generate_je_block(je, options)

            # ── JE file : ajouter le bloc ──
            je_content += "\n" + new_je_block
            with open(je_path, "w", encoding="utf-8") as f:
                f.write(je_content)

            # ── Loc file ──
            loc_content = read_file(loc_path) if os.path.exists(loc_path) else "l_english:\n"
            loc_content = remove_loc_entries(loc_content, key)
            loc_content = loc_content.rstrip() + "\n\n"
            loc_content += generate_localization(je, buttons_data, progress_bars, status_desc_list)
            with open(loc_path, "w", encoding="utf-8") as f:
                f.write(loc_content)

            # ── Button file ──
            if os.path.exists(btn_path):
                btn_content = read_file(btn_path)
                btn_content = remove_blocks_for_key(btn_content, f"{key}_button_")
                if buttons_data:
                    btn_content = btn_content.rstrip() + "\n\n" + generate_buttons(je, buttons_data)
                with open(btn_path, "w", encoding="utf-8") as f:
                    f.write(btn_content)
            elif buttons_data:
                with open(btn_path, "w", encoding="utf-8") as f:
                    f.write(generate_buttons(je, buttons_data))

            # ── PB file ──
            pb_content = read_file(pb_path) if os.path.exists(pb_path) else ""
            pb_content = remove_blocks_for_key(pb_content, f"{key}_")
            if progress_bars:
                pb_content = pb_content.rstrip() + "\n"
                for pb in progress_bars:
                    pb_content += generate_progress_bar(pb)
            if pb_content.strip() or os.path.exists(pb_path):
                with open(pb_path, "w", encoding="utf-8") as f:
                    f.write(pb_content)

            # ── History : variables globales des progress bars ──
            if progress_bars:
                _hn = os.path.join(base_path, "common/history/global/00_hmmai_global.txt")
                if os.path.exists(_hn):
                    _hct = read_file(_hn)
                    _hchg2 = False
                    for pb in progress_bars:
                        _gvk = f"{key}_global_variable_progress_bar_{pb['pb_index']}"
                        if _gvk not in _hct:
                            _vi2 = (
                                f"\n    set_global_variable = {{\n"
                                f"        name = {_gvk}\n"
                                f"        value = 0\n"
                                f"    }}\n"
                            )
                            _lb3 = _hct.rfind('}')
                            if _lb3 >= 0:
                                _hct = _hct[:_lb3] + _vi2 + _hct[_lb3:]
                                _hchg2 = True
                    if _hchg2:
                        with open(_hn, "w", encoding="utf-8") as f:
                            f.write(_hct)

            messagebox.showinfo("Succès", f"{key} sauvegardée avec succès !")

        except Exception as e:
            messagebox.showerror("Erreur", f"{type(e).__name__}: {e!s}")

    return outer
