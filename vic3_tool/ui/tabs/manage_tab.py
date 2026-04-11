import tkinter as tk
from tkinter import messagebox
import os
import re

manage_button_fields = []

def build_manage_tab(parent, path_var, tag_var):
    frame = tk.Frame(parent)

    # ----------- FUNCTIONS -----------

    def load_je_list():
        tag = tag_var.get().upper()
        base_path = path_var.get()

        je_listbox.delete(0, tk.END)

        path = os.path.join(base_path, "common/journal_entries", f"{tag}.txt")

        if not os.path.exists(path):
            return

        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        matches = re.findall(rf"{tag}_je_\d+", content)

        for m in sorted(set(matches)):
            je_listbox.insert(tk.END, m)

    def load_selected_je():
        for w in button_frame.winfo_children():
            w.destroy()

        manage_button_fields.clear()

        selection = je_listbox.curselection()
        if not selection:
            return

        key = je_listbox.get(selection[0])
        tag = tag_var.get().upper()
        base_path = path_var.get()

        key_label.config(text=key)

        je_path = os.path.join(base_path, "common/journal_entries", f"{tag}.txt")

        with open(je_path, "r", encoding="utf-8") as f:
            content = f.read()

        block = re.search(rf"{key}.*?\n\}}", content, re.DOTALL)

        if block:
            year = re.search(r"game_date >= (\d+)", block.group())
            if year:
                year_entry.delete(0, tk.END)
                year_entry.insert(0, year.group(1))

        loc_path = os.path.join(base_path, "localization/english", "01_hmmf_je_localization_l_english.yml")

        if os.path.exists(loc_path):
            with open(loc_path, "r", encoding="utf-8") as f:
                loc = f.read()

            title = re.search(rf"{key}:0 \"(.*?)\"", loc)
            desc = re.search(rf"{key}_reason:0 \"(.*?)\"", loc)

            if title:
                title_entry.delete(0, tk.END)
                title_entry.insert(0, title.group(1))

            if desc:
                desc_entry.delete("1.0", tk.END)
                desc_entry.insert("1.0", desc.group(1).replace("\\n\\n", "\n\n"))

        buttons = re.findall(rf"{key}_button_(\d+)", content)
        count = max([int(x) for x in buttons], default=0)

        for i in range(1, count + 1):
            tk.Label(button_frame, text=f"Bouton {i}").pack()

            name = tk.Entry(button_frame)
            name.pack()

            desc_b = tk.Entry(button_frame)
            desc_b.pack()

            tooltip = tk.Entry(button_frame)
            tooltip.pack()

            if os.path.exists(loc_path):
                btn_key = f"{key}_button_{i}"

                name_match = re.search(rf"{btn_key}:0 \"(.*?)\"", loc)
                desc_match = re.search(rf"{btn_key}_desc:0 \"(.*?)\"", loc)
                tt_match = re.search(rf"{btn_key}_tt:0 \"(.*?)\"", loc)

                if name_match:
                    name.insert(0, name_match.group(1))
                if desc_match:
                    desc_b.insert(0, desc_match.group(1))
                if tt_match:
                    tooltip.insert(0, tt_match.group(1))

            manage_button_fields.append((name, desc_b, tooltip))

    def save_selected_je():
        selection = je_listbox.curselection()
        if not selection:
            return

        key = je_listbox.get(selection[0])
        tag = tag_var.get().upper()
        base_path = path_var.get()

        year = year_entry.get()
        title = title_entry.get()
        desc = desc_entry.get("1.0", tk.END).strip().replace("\n\n", "\\n\\n")

        # ----------- UPDATE JE FILE -----------

        je_path = os.path.join(base_path, "common/journal_entries", f"{tag}.txt")

        with open(je_path, "r", encoding="utf-8") as f:
            content = f.read()

        new_block = f"""{key} = {{
    icon = "gfx/interface/icons/event_icons/{key}.dds"

    group = je_group_ef
    should_be_pinned_by_default = yes

    is_shown_when_inactive = {{
        exists = c:{tag}
        c:{tag} ?= THIS
    }}

    possible = {{
        game_date >= {year}.1.1
    }}

    immediate = {{
    }}

    complete = {{
    }}
}}
"""

        content = re.sub(rf"{key}.*?\n\}}", new_block, content, flags=re.DOTALL)

        with open(je_path, "w", encoding="utf-8") as f:
            f.write(content)

        # ----------- UPDATE LOCALIZATION -----------

        loc_path = os.path.join(base_path, "localization/english", "01_hmmf_je_localization_l_english.yml")

        if os.path.exists(loc_path):
            with open(loc_path, "r", encoding="utf-8") as f:
                loc = f.read()
        else:
            loc = "l_english:\n"

        # remove old JE loc
        loc = re.sub(rf"{key}:0 \".*?\"\n", "", loc)
        loc = re.sub(rf"{key}_reason:0 \".*?\"\n", "", loc)

        # remove old button loc
        for i in range(1, 20):
            loc = re.sub(rf"{key}_button_{i}.*\n", "", loc)
            loc = re.sub(rf"{key}_button_{i}_desc.*\n", "", loc)
            loc = re.sub(rf"{key}_button_{i}_tt.*\n", "", loc)

        # add new JE loc
        loc += f'  {key}:0 "{title}"\n'
        loc += f'  {key}_reason:0 "{desc}"\n'

        # add new button loc
        for i, (name, desc_b, tooltip) in enumerate(manage_button_fields, start=1):
            btn = f"{key}_button_{i}"

            loc += f'  {btn}:0 "{name.get()}"\n'
            loc += f'  {btn}_desc:0 "{desc_b.get()}"\n'
            loc += f'  {btn}_tt:0 "{tooltip.get()}"\n'

        with open(loc_path, "w", encoding="utf-8") as f:
            f.write(loc)

        messagebox.showinfo("Succès", "JE + localisation mises à jour")

    # ----------- UI -----------

    tk.Label(frame, text="TAG").pack()
    tag_entry = tk.Entry(frame)
    tag_entry.pack()

    tk.Button(frame, text="Charger JE", command=load_je_list).pack()

    je_listbox = tk.Listbox(frame)
    je_listbox.pack()

    tk.Button(frame, text="Charger sélection", command=load_selected_je).pack()

    key_label = tk.Label(frame)
    key_label.pack()

    tk.Label(frame, text="Année").pack()
    year_entry = tk.Entry(frame)
    year_entry.pack()

    tk.Label(frame, text="Titre").pack()
    title_entry = tk.Entry(frame)
    title_entry.pack()

    tk.Label(frame, text="Description").pack()
    desc_entry = tk.Text(frame, height=5)
    desc_entry.pack()

    button_frame = tk.Frame(frame)
    button_frame.pack()

    tk.Button(frame, text="Sauvegarder", command=save_selected_je).pack()

    return frame