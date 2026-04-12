import os
import re
import tkinter as tk
from tkinter import messagebox


def build_modifier_tab(parent, path_var, tag_var):
    frame = tk.Frame(parent)

    def get_paths():
        base_path = path_var.get().strip()
        mod_path = os.path.join(base_path, "common/static_modifiers", "00_hmmf_static_modifier.txt")
        loc_path = os.path.join(base_path, "localization/english", "01_hmmf_static_modifier_localization_l_english.yml")
        return base_path, mod_path, loc_path

    def read_text(path):
        if not os.path.exists(path):
            return ""
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def write_text(path, content):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    def get_next_modifier_id(tag, path):
        content = read_text(path)
        matches = re.findall(rf"{re.escape(tag)}_modifier_(\d+)", content)
        if not matches:
            return 1
        return max(map(int, matches)) + 1

    def find_block_range(content, key):
        m = re.search(rf"{re.escape(key)}\s*=\s*\{{", content)
        if not m:
            return None
        start = m.start()
        i = m.end() - 1
        depth = 0
        while i < len(content):
            if content[i] == "{":
                depth += 1
            elif content[i] == "}":
                depth -= 1
                if depth == 0:
                    return (start, i + 1)
            i += 1
        return None

    def get_loc_value(content, key):
        m = re.search(rf'^\s*{re.escape(key)}:0\s+"(.*?)"', content, re.MULTILINE)
        return m.group(1) if m else ""

    def upsert_loc_value(content, key, value):
        line = f'  {key}:0 "{value}"\n'
        pattern = rf'^\s*{re.escape(key)}:0\s+".*?"\n?'
        if re.search(pattern, content, re.MULTILINE):
            return re.sub(pattern, line, content, flags=re.MULTILINE)
        if not content.strip():
            content = "l_english:\n"
        if "l_english:" not in content:
            content = "l_english:\n" + content
        return content.rstrip() + "\n" + line

    def list_modifier_keys(content, tag):
        return sorted(set(re.findall(rf"{re.escape(tag)}_modifier_\d+", content)))

    def create_modifier():
        base_path, mod_path, loc_path = get_paths()
        tag = tag_var.get().upper().strip()
        name = name_entry.get().strip()
        modifier_type = type_var.get()
        components = components_text.get("1.0", "end").strip()

        if not base_path or not tag or not name:
            messagebox.showerror("Erreur", "Dossier, TAG et nom sont obligatoires.")
            return

        mod_id = get_next_modifier_id(tag, mod_path)
        key = f"{tag}_modifier_{mod_id}"
        icon = (
            "gfx/interface/icons/timed_modifier_icons/modifier_gear_positive.dds"
            if modifier_type == "positif"
            else "gfx/interface/icons/timed_modifier_icons/modifier_gear_negative.dds"
        )

        inner = ""
        if components:
            inner = "\n".join(f"    {line}" for line in components.splitlines()) + "\n"

        modifier_block = f"""
{key} = {{
    icon = {icon}
{inner}}}
"""

        mod_content = read_text(mod_path).rstrip()
        mod_content = (mod_content + "\n\n" if mod_content else "") + modifier_block.strip() + "\n"
        write_text(mod_path, mod_content)

        loc_content = read_text(loc_path)
        loc_content = upsert_loc_value(loc_content, key, name)
        write_text(loc_path, loc_content)

        load_modifiers()
        messagebox.showinfo("Succès", f"Modifier {key} créé")

    def load_modifiers():
        modifier_listbox.delete(0, tk.END)
        _, mod_path, _ = get_paths()
        tag = tag_var.get().upper().strip()
        if not tag:
            return
        for key in list_modifier_keys(read_text(mod_path), tag):
            modifier_listbox.insert(tk.END, key)

    def load_selected_modifier():
        sel = modifier_listbox.curselection()
        if not sel:
            return

        key = modifier_listbox.get(sel[0])
        _, mod_path, loc_path = get_paths()
        mod_content = read_text(mod_path)
        loc_content = read_text(loc_path)
        br = find_block_range(mod_content, key)
        if not br:
            messagebox.showerror("Erreur", f"Bloc introuvable pour {key}")
            return

        block = mod_content[br[0]:br[1]]
        current_modifier_var.set(key)
        edit_name_var.set(get_loc_value(loc_content, key))
        edit_block_text.delete("1.0", "end")
        edit_block_text.insert("1.0", block)

    def save_selected_modifier():
        key = current_modifier_var.get().strip()
        if not key:
            messagebox.showerror("Erreur", "Aucun modifier chargé.")
            return

        _, mod_path, loc_path = get_paths()
        mod_content = read_text(mod_path)
        loc_content = read_text(loc_path)
        new_block = edit_block_text.get("1.0", "end").strip()
        new_name = edit_name_var.get().strip()

        if not new_block:
            messagebox.showerror("Erreur", "Le bloc modifier ne peut pas être vide.")
            return
        if not re.match(rf"^{re.escape(key)}\s*=\s*\{{", new_block):
            messagebox.showerror("Erreur", "Le bloc doit commencer par la clé du modifier chargé.")
            return

        br = find_block_range(mod_content, key)
        if not br:
            messagebox.showerror("Erreur", f"Bloc introuvable pour {key}")
            return

        mod_content = mod_content[:br[0]] + new_block + "\n" + mod_content[br[1]:]
        write_text(mod_path, mod_content)

        if new_name:
            loc_content = upsert_loc_value(loc_content, key, new_name)
            write_text(loc_path, loc_content)

        load_modifiers()
        messagebox.showinfo("Succès", f"{key} sauvegardé.")

    create_box = tk.LabelFrame(frame, text="Créer un modifier")
    create_box.pack(fill="x", padx=10, pady=8)

    tk.Label(create_box, text="Nom du modifier").pack(anchor="w")
    name_entry = tk.Entry(create_box, width=40)
    name_entry.pack(fill="x")

    tk.Label(create_box, text="Type").pack(anchor="w", pady=(8, 0))
    type_var = tk.StringVar(value="positif")
    tk.Radiobutton(create_box, text="Positif", variable=type_var, value="positif").pack(anchor="w")
    tk.Radiobutton(create_box, text="Négatif", variable=type_var, value="negatif").pack(anchor="w")

    tk.Label(create_box, text="Composantes du modifier").pack(anchor="w", pady=(8, 0))
    components_text = tk.Text(create_box, height=6, width=60)
    components_text.pack(fill="x")

    tk.Button(create_box, text="Créer Modifier", command=create_modifier).pack(pady=10)

    editor_box = tk.LabelFrame(frame, text="Modifier existant")
    editor_box.pack(fill="both", expand=True, padx=10, pady=(0, 8))

    top_row = tk.Frame(editor_box)
    top_row.pack(fill="both", expand=True)

    left_col = tk.Frame(top_row)
    left_col.pack(side="left", fill="y", padx=(0, 10))

    tk.Button(left_col, text="Charger la liste", command=load_modifiers).pack(fill="x", pady=(0, 6))
    modifier_listbox = tk.Listbox(left_col, width=28, height=18)
    modifier_listbox.pack(fill="y", expand=True)
    tk.Button(left_col, text="Charger le modifier", command=load_selected_modifier).pack(fill="x", pady=6)

    right_col = tk.Frame(top_row)
    right_col.pack(side="left", fill="both", expand=True)

    current_modifier_var = tk.StringVar(value="")
    tk.Label(right_col, textvariable=current_modifier_var, fg="blue").pack(anchor="w")

    name_row = tk.Frame(right_col)
    name_row.pack(fill="x", pady=(4, 6))
    tk.Label(name_row, text="Localisation", width=12, anchor="w").pack(side="left")
    edit_name_var = tk.StringVar()
    tk.Entry(name_row, textvariable=edit_name_var).pack(side="left", fill="x", expand=True)

    tk.Label(right_col, text="Bloc libre du modifier").pack(anchor="w")
    edit_block_text = tk.Text(right_col, height=18, width=70)
    edit_block_text.pack(fill="both", expand=True)

    tk.Button(right_col, text="Sauvegarder", command=save_selected_modifier).pack(pady=8, anchor="e")

    return frame
