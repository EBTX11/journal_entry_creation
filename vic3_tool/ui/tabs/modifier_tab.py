import tkinter as tk
from tkinter import messagebox
import os
import re


def build_modifier_tab(parent, path_var, tag_var):
    frame = tk.Frame(parent)

    # ----------- FUNCTIONS -----------

    def get_next_modifier_id(tag, path):
        if not os.path.exists(path):
            return 1

        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        matches = re.findall(rf"{tag}_modifier_(\d+)", content)

        if not matches:
            return 1

        return max(map(int, matches)) + 1

    def create_modifier():
        base_path = path_var.get()
        tag = tag_var.get().upper()

        name = name_entry.get()
        modifier_type = type_var.get()

        if not base_path or not tag or not name:
            messagebox.showerror("Erreur", "Champs manquants")
            return

        # ----------- PATHS -----------

        mod_path = os.path.join(base_path, "common/static_modifiers", "00_hmmf_static_modifier.txt")
        loc_path = os.path.join(base_path, "localization/english", "01_hmmf_static_modifier_localization_l_english.yml")

        os.makedirs(os.path.dirname(mod_path), exist_ok=True)
        os.makedirs(os.path.dirname(loc_path), exist_ok=True)

        # ----------- ID -----------

        mod_id = get_next_modifier_id(tag, mod_path)
        key = f"{tag}_modifier_{mod_id}"

        # ----------- ICON -----------

        if modifier_type == "positif":
            icon = "gfx/interface/icons/timed_modifier_icons/modifier_gear_positive.dds"
        else:
            icon = "gfx/interface/icons/timed_modifier_icons/modifier_gear_negative.dds"

        # ----------- MODIFIER BLOCK -----------

        modifier_block = f"""
{key} = {{
    icon = {icon}
    
    

}}
"""

        # ----------- WRITE MODIFIER -----------

        with open(mod_path, "a", encoding="utf-8") as f:
            f.write(modifier_block)

        # ----------- LOCALIZATION -----------

        if not os.path.exists(loc_path):
            loc_content = "l_english:\n\n"
        else:
            with open(loc_path, "r", encoding="utf-8") as f:
                loc_content = f.read()

        loc_content += f'\n  {key}:0 "{name}"\n'

        with open(loc_path, "w", encoding="utf-8") as f:
            f.write(loc_content)

        messagebox.showinfo("Succès", f"Modifier {key} créé")

    # ----------- UI -----------

    tk.Label(frame, text="Nom du modifier").pack()
    name_entry = tk.Entry(frame)
    name_entry.pack()

    tk.Label(frame, text="Type").pack()

    type_var = tk.StringVar(value="positif")

    tk.Radiobutton(frame, text="Positif", variable=type_var, value="positif").pack()
    tk.Radiobutton(frame, text="Négatif", variable=type_var, value="negatif").pack()

    tk.Button(frame, text="Créer Modifier", command=create_modifier).pack(pady=10)

    return frame