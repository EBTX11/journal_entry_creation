import os

from vic3_tool.models.journal_entry import JournalEntry
from vic3_tool.generators.je_generator import generate_je_block
from vic3_tool.generators.button_generator import generate_buttons
from vic3_tool.generators.localization_generator import generate_localization
from vic3_tool.utils.file_manager import ensure_folder, append_to_file, read_file

import re


def get_next_je_index(tag, je_path):
    if not os.path.exists(je_path):
        return 1

    content = read_file(je_path)
    matches = re.findall(rf"{tag}_je_(\d+)", content)

    if not matches:
        return 1

    return max(map(int, matches)) + 1


def create_full_je(base_path, tag, year, title, desc, num_buttons, buttons_data):
    je_path = os.path.join(base_path, "common/journal_entries", f"{tag}.txt")
    btn_path = os.path.join(base_path, "common/scripted_buttons", f"{tag}.txt")
    loc_path = os.path.join(base_path, "localization/english", "01_hmmf_je_localization_l_english.yml")

    ensure_folder(os.path.dirname(je_path))
    ensure_folder(os.path.dirname(btn_path))
    ensure_folder(os.path.dirname(loc_path))

    index = get_next_je_index(tag, je_path)
    je = JournalEntry(tag, index, year, title, desc)

    append_to_file(je_path, generate_je_block(je, len(buttons_data)))
    append_to_file(btn_path, generate_buttons(je, buttons_data))
    append_to_file(loc_path, generate_localization(je, buttons_data))