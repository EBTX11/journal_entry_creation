import os
import re

from vic3_tool.models.journal_entry import JournalEntry
from vic3_tool.generators.je_generator import generate_je_block, generate_je_goal_progress_block
from vic3_tool.generators.button_generator import generate_buttons
from vic3_tool.generators.localization_generator import generate_localization
from vic3_tool.generators.progress_bar_generator import generate_progress_bar
from vic3_tool.utils.file_manager import ensure_folder, append_to_file, read_file


def get_next_je_index(tag, je_path):
    if not os.path.exists(je_path):
        return 1

    content = read_file(je_path)
    matches = re.findall(rf"{tag}_je_(\d+)", content)

    if not matches:
        return 1

    return max(map(int, matches)) + 1


def create_full_je(
    base_path, tag, year, title, desc,
    num_buttons, buttons_data,
    progress_bars=None,
    pb_pulse="monthly",
    status_desc=None,
    status_desc_trigger_var=None,
    status_desc_trigger_vals=None,
    monthly_empty=False,
    yearly=False,
    modifiers=False,
    on_fail=False,
    is_shown=None,
    possible_conditions=None,
    complete_conditions=None,
    fail_conditions=None,
):
    je_path = os.path.join(base_path, "common/journal_entries", f"{tag}.txt")
    btn_path = os.path.join(base_path, "common/scripted_buttons", f"{tag}.txt")
    loc_path = os.path.join(base_path, "localization/english", "01_hmmf_je_localization_l_english.yml")
    pb_path  = os.path.join(base_path, "common/scripted_progress_bars", "hmmf_progressbar.txt")

    ensure_folder(os.path.dirname(je_path))
    ensure_folder(os.path.dirname(btn_path))
    ensure_folder(os.path.dirname(loc_path))
    ensure_folder(os.path.dirname(pb_path))

    index = get_next_je_index(tag, je_path)
    je = JournalEntry(tag, index, year, title, desc)

    # -------- CONSTRUIRE LES CLÉS DES PROGRESS BARS --------

    if progress_bars:
        for pb in progress_bars:
            pb["key"] = f"{je.key}_{pb['pb_index']}_progress_bar"
            gv  = f"{je.key}_global_variable_progress_bar_{pb['pb_index']}"
            sfx = f"[GetGlobalVariable('{gv}').GetValue|D]/ {pb['max']}"
            pb["desc"] = (pb["desc"] + " " + sfx).strip() if pb.get("desc") else sfx

    # -------- RÉSOUDRE LA VARIABLE TRIGGER STATUS_DESC --------

    # Si l'appelant a fourni un placeholder contenant "TAG_je_X", on le remplace
    # par le vrai je.key maintenant que l'index est connu.
    resolved_tvar = None
    if status_desc_trigger_var:
        resolved_tvar = re.sub(r'\b[A-Z]+_je_X\b', je.key, status_desc_trigger_var)

    # -------- OPTIONS POUR LE TEMPLATE --------

    options = {
        "buttons":                  num_buttons,
        "progress_bars":            progress_bars,
        "pb_pulse":                 pb_pulse,
        "status_desc":              status_desc,
        "status_desc_trigger_var":  resolved_tvar,
        "status_desc_trigger_vals": status_desc_trigger_vals or [],
        "monthly_empty":            monthly_empty,
        "yearly":                   yearly,
        "modifiers":                modifiers,
        "on_fail":                  on_fail,
        "is_shown":                 is_shown,
        "possible_conditions":      possible_conditions,
        "complete_conditions":      complete_conditions,
        "fail_conditions":          fail_conditions,
    }

    # -------- WRITE FILES --------

    append_to_file(je_path, "\n" + generate_je_block(je, options))

    if buttons_data:
        append_to_file(btn_path, generate_buttons(je, buttons_data))

    append_to_file(loc_path, "\n" + generate_localization(je, buttons_data, progress_bars, status_desc))

    # -------- PROGRESS BAR FILE --------

    if progress_bars:
        for pb in progress_bars:
            append_to_file(pb_path, generate_progress_bar(pb))

    # -------- HISTORY : global variables for progress bars --------

    if progress_bars:
        hist_path = os.path.join(base_path, "common/history/global/00_hmmai_global.txt")
        if os.path.exists(hist_path):
            hist_content = read_file(hist_path)
            changed = False
            for pb in progress_bars:
                gv = f"{je.key}_global_variable_progress_bar_{pb['pb_index']}"
                if gv not in hist_content:
                    var_init = (
                        f"\n    set_global_variable = {{\n"
                        f"        name = {gv}\n"
                        f"        value = 0\n"
                        f"    }}\n"
                    )
                    last_b = hist_content.rfind('}')
                    if last_b >= 0:
                        hist_content = hist_content[:last_b] + var_init + hist_content[last_b:]
                        changed = True
            if changed:
                with open(hist_path, "w", encoding="utf-8") as f:
                    f.write(hist_content)

    # -------- HISTORY : global variable for status_desc trigger (new_var mode) --------

    if resolved_tvar and status_desc_trigger_var and "_je_X_" in status_desc_trigger_var:
        hist_path = os.path.join(base_path, "common/history/global/00_hmmai_global.txt")
        if os.path.exists(hist_path):
            hist_content = read_file(hist_path)
            if resolved_tvar not in hist_content:
                var_init = (
                    f"\n    set_global_variable = {{\n"
                    f"        name = {resolved_tvar}\n"
                    f"        value = 0\n"
                    f"    }}\n"
                )
                last_b = hist_content.rfind('}')
                if last_b >= 0:
                    hist_content = hist_content[:last_b] + var_init + hist_content[last_b:]
                    with open(hist_path, "w", encoding="utf-8") as f:
                        f.write(hist_content)


def create_je_goal_progress(
    base_path, tag, year, title, desc,
    goal_value,
    pb_name, pb_desc, pb_color, pb_max_value,
    pulse="monthly", tt_complete="",
):
    je_path   = os.path.join(base_path, "common/journal_entries", f"{tag}.txt")
    pb_path   = os.path.join(base_path, "common/scripted_progress_bars", "hmmf_progressbar.txt")
    loc_path  = os.path.join(base_path, "localization/english", "01_hmmf_je_localization_l_english.yml")
    hist_path = os.path.join(base_path, "common/history/global/00_hmmai_global.txt")

    ensure_folder(os.path.dirname(je_path))
    ensure_folder(os.path.dirname(pb_path))
    ensure_folder(os.path.dirname(loc_path))

    index      = get_next_je_index(tag, je_path)
    je         = JournalEntry(tag, index, year, title, desc)
    pb_key     = f"{je.key}_1_progress_bar"
    global_var = f"{je.key}_global_variable_progress_bar_1"

    _gv_suffix  = f"[GetGlobalVariable('{global_var}').GetValue|D]/ {goal_value}"
    tt_complete = (f"{tt_complete} " if tt_complete else "") + _gv_suffix

    pb_desc_suffix = f" {_gv_suffix}"
    pb_desc_final  = pb_desc + pb_desc_suffix if pb_desc else pb_desc_suffix.strip()

    pb_data = {
        "key":           pb_key,
        "name":          pb_name,
        "desc":          pb_desc_final,
        "color":         pb_color,
        "start":         "0",
        "min":           "0",
        "max":           pb_max_value,
        "is_inverted":   False,
        "second_desc":   False,
        "monthly_value": None,
        "monthly_desc":  None,
    }

    append_to_file(je_path, "\n" + generate_je_goal_progress_block(je, global_var, pb_key, goal_value, pulse))
    append_to_file(pb_path, generate_progress_bar(pb_data))

    loc_block  = "\n" + generate_localization(je, [], [pb_data], None)
    loc_block += f'  {je.key}_tt_complete_1:0 "{tt_complete}"\n'
    append_to_file(loc_path, loc_block)

    # Initialiser la variable globale dans l'historique
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
