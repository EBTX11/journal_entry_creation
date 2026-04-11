import tkinter as tk
from tkinter import messagebox
import os
import re

from vic3_tool.utils.formatter import format_text


def build_event_tab(parent, path_var, tag_var):
    frame = tk.Frame(parent)

    # ----------- FUNCTIONS -----------

    def get_next_event_id(tag, path):
        if not os.path.exists(path):
            return 1

        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        matches = re.findall(rf"00_hmmf_{tag}\.(\d+)", content)

        if not matches:
            return 1

        return max(map(int, matches)) + 1

    def create_event():
        base_path = path_var.get()
        tag = tag_var.get().upper()

        title = title_entry.get()
        desc = format_text(desc_entry.get("1.0", tk.END))
        flavor = format_text(flavor_entry.get("1.0", tk.END))

        if not base_path or not tag:
            messagebox.showerror("Erreur", "Dossier ou TAG manquant")
            return

        # ----------- PATHS -----------

        event_path = os.path.join(base_path, "events", f"{tag}.txt")
        loc_path = os.path.join(base_path, "localization/english", "00_hmmf_events_l_english.yml")

        os.makedirs(os.path.dirname(event_path), exist_ok=True)
        os.makedirs(os.path.dirname(loc_path), exist_ok=True)

        # ----------- ID -----------

        event_id = get_next_event_id(tag, event_path)

        key = f"00_hmmf_{tag}.{event_id}"

        # ----------- EVENT BLOCK -----------

        event_block = f"""
{key} = {{
    type = country_event
    placement = scope:capital_state

    title = {key}.t
    desc = {key}.d
    flavor = {key}.f

    duration = 3

    event_image = {{
        texture = "gfx/event_pictures/{key}.dds"
    }}

    on_created_soundeffect = "event:/SFX/UI/Alerts/event_appear"

    icon = "gfx/interface/icons/event_icons/event_default.dds"

    trigger = {{
    }}

    immediate = {{
    }}

    option = {{
        name = {key}.a
    }}
}}
"""

        # ----------- WRITE EVENT -----------

        with open(event_path, "a", encoding="utf-8") as f:
            f.write(event_block)

        # ----------- LOCALIZATION -----------

        if not os.path.exists(loc_path):
            loc_content = "l_english:\n\n"
        else:
            with open(loc_path, "r", encoding="utf-8") as f:
                loc_content = f.read()

        new_loc = f"""
  {key}.t:0 "{title}"
  {key}.d:1 "{desc}"
  {key}.f:1 "{flavor}"
  {key}.a:0 "Acknowledged"
"""

        loc_content += "\n\n" + new_loc

        with open(loc_path, "w", encoding="utf-8") as f:
            f.write(loc_content)

        messagebox.showinfo("Succès", f"Event {key} créé")

    # ----------- UI -----------

    tk.Label(frame, text="Titre").pack()
    title_entry = tk.Entry(frame)
    title_entry.pack()

    tk.Label(frame, text="Description (header)").pack()
    desc_entry = tk.Text(frame, height=3)
    desc_entry.pack()

    tk.Label(frame, text="Flavor (description)").pack()
    flavor_entry = tk.Text(frame, height=5)
    flavor_entry.pack()

    tk.Button(frame, text="Créer Event", command=create_event).pack(pady=10)

    return frame