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
    status_desc=None,
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

    # -------- OPTIONS POUR LE TEMPLATE --------

    options = {
        "buttons":             num_buttons,
        "progress_bars":       progress_bars,
        "status_desc":         status_desc,
        "monthly_empty":       monthly_empty,
        "yearly":              yearly,
        "modifiers":           modifiers,
        "on_fail":             on_fail,
        "is_shown":            is_shown,
        "possible_conditions": possible_conditions,
        "complete_conditions": complete_conditions,
        "fail_conditions":     fail_conditions,
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


def create_je_goal_progress(
    base_path, tag, year, title, desc,
    global_var, goal_value,
    pb_name, pb_desc, pb_color, pb_max_value,
    pulse="monthly",
):
    je_path  = os.path.join(base_path, "common/journal_entries", f"{tag}.txt")
    pb_path  = os.path.join(base_path, "common/scripted_progress_bars", "hmmf_progressbar.txt")
    loc_path = os.path.join(base_path, "localization/english", "01_hmmf_je_localization_l_english.yml")

    ensure_folder(os.path.dirname(je_path))
    ensure_folder(os.path.dirname(pb_path))
    ensure_folder(os.path.dirname(loc_path))

    index  = get_next_je_index(tag, je_path)
    je     = JournalEntry(tag, index, year, title, desc)
    pb_key = f"{je.key}_1_progress_bar"

    pb_data = {
        "key":           pb_key,
        "name":          pb_name,
        "desc":          pb_desc,
        "color":         pb_color,
        "start":         "0",
        "min":           "0",
        "max":           pb_max_value,
        "is_inverted":   False,
        "second_desc":   False,
        "monthly_value": None,
        "monthly_desc":  None,
    }

    append_to_file(je_path,  "\n" + generate_je_goal_progress_block(je, global_var, pb_key, goal_value, pulse))
    append_to_file(pb_path,  generate_progress_bar(pb_data))
    append_to_file(loc_path, "\n" + generate_localization(je, [], [pb_data], None))
