import tkinter as tk
from tkinter import messagebox
import os

def build_treaty_tab(parent, path_var, tag_var):
    frame = tk.Frame(parent)

    def create_treaty():
        base_path = path_var.get()
        name = treaty_entry.get().strip()

        if not base_path or not name:
            messagebox.showerror("Erreur", "Champs manquants")
            return

        loc_path = os.path.join(
            base_path,
            "localization/english",
            "01_hmmf_je_localization_l_english.yml"
        )

        key = f"treaty_{name.lower().replace(' ', '_')}"

        # création fichier si besoin
        if not os.path.exists(loc_path):
            content = "l_english:\n"
        else:
            with open(loc_path, "r", encoding="utf-8") as f:
                content = f.read()

        # éviter doublon
        if key in content:
            messagebox.showerror("Erreur", "Déjà existant")
            return

        # 🔥 insertion en haut (après l_english:)
        if "l_english:" in content:
            parts = content.split("l_english:\n", 1)
            header = parts[0] + "l_english:\n"
            body = parts[1]

            new_line = f'  {key}:0 "{name}"\n'
            content = header + new_line + body
        else:
            content = "l_english:\n" + f'  {key}:0 "{name}"\n' + content

        with open(loc_path, "w", encoding="utf-8") as f:
            f.write(content)

        messagebox.showinfo("Succès", "Treaty ajouté")

    # UI

    tk.Label(frame, text="Nom du Treaty").pack()

    treaty_entry = tk.Entry(frame)
    treaty_entry.pack()

    tk.Button(frame, text="Créer Treaty", command=create_treaty).pack()

    return frame