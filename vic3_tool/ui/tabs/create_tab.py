import tkinter as tk
from tkinter import messagebox

from vic3_tool.main import create_full_je

button_fields = []

def build_create_tab(parent, path_var, tag_var):
    frame = tk.Frame(parent)

    # ----------- FUNCTIONS -----------

    def generate_button_fields():
        for widget in button_frame.winfo_children():
            widget.destroy()

        button_fields.clear()

        try:
            n = int(buttons_entry.get())
        except:
            return

        for i in range(1, n + 1):
            tk.Label(button_frame, text=f"Bouton {i}").pack()

            name = tk.Entry(button_frame)
            name.pack()
            name.insert(0, f"Nom bouton {i}")

            desc = tk.Entry(button_frame)
            desc.pack()
            desc.insert(0, f"Description bouton {i}")

            tt1 = tk.Entry(button_frame)
            tt1.pack()
            tt1.insert(0, "Tooltip 1")

            tt2 = tk.Entry(button_frame)
            tt2.pack()
            tt2.insert(0, "Tooltip 2")

            button_fields.append((name, desc, tt1, tt2))

    def create_je_ui():
        base_path = path_var.get()
        tag = tag_var.get().upper()

        year = year_entry.get()
        title = title_entry.get()
        desc = desc_entry.get("1.0", tk.END)

        if not base_path or not tag:
            messagebox.showerror("Erreur", "Dossier ou TAG manquant")
            return

        buttons_data = []

        for name, desc_field, tt1, tt2 in button_fields:
            buttons_data.append({
                "name": name.get(),
                "desc": desc_field.get(),
                "tt1": tt1.get(),
                "tt2": tt2.get()
            })

        try:
            create_full_je(
                base_path=base_path,
                tag=tag,
                year=int(year),
                title=title,
                desc=desc,
                num_buttons=len(buttons_data),
                buttons_data=buttons_data
            )
            messagebox.showinfo("Succès", "JE créée !")
        except Exception as e:
            messagebox.showerror("Erreur", str(e))

    # ----------- UI -----------

    tk.Label(frame, text="Année").pack()
    year_entry = tk.Entry(frame)
    year_entry.pack()

    tk.Label(frame, text="Titre").pack()
    title_entry = tk.Entry(frame)
    title_entry.pack()

    tk.Label(frame, text="Description").pack()
    desc_entry = tk.Text(frame, height=5)
    desc_entry.pack()

    tk.Label(frame, text="Nombre de boutons").pack()
    buttons_entry = tk.Entry(frame)
    buttons_entry.pack()

    tk.Button(frame, text="Générer boutons", command=generate_button_fields).pack()

    button_frame = tk.Frame(frame)
    button_frame.pack()

    tk.Button(frame, text="Créer JE", command=create_je_ui).pack()

    return frame