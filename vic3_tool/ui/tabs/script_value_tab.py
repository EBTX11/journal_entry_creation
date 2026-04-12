import tkinter as tk
from tkinter import messagebox
import os
import re


def build_script_value_tab(parent, path_var, tag_var):
    frame = tk.Frame(parent)

    # ------------------------------------------------------------------ helpers

    def _file_path():
        return os.path.join(
            path_var.get(), "common", "script_values", "01_hmmai_script_value.txt"
        )

    def _next_name():
        tag = tag_var.get().strip()
        if not tag:
            return ""
        path = _file_path()
        existing = ""
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                existing = f.read()
        n = 1
        while f"{tag}_script_value_{n}" in existing:
            n += 1
        return f"{tag}_script_value_{n}"

    def _build_block(name, with_if):
        if with_if:
            return (
                f"{name} = {{\n"
                f"\tvalue = 0\n"
                f"\tif = {{\n"
                f"\t\tlimit = {{\n"
                f"\t\t\t#vide ici\n"
                f"\t\t}}\n"
                f"\t\t#vide ici\n"
                f"\t}}\n"
                f"}}\n"
            )
        return (
            f"{name} = {{\n"
            f"\tvalue = 0\n"
            f"}}\n"
        )

    # ----------------------------------------------------------------- actions

    def refresh_name():
        n = _next_name()
        if not n:
            messagebox.showwarning("Attention", "Définissez d'abord un TAG")
            return
        name_entry.delete(0, tk.END)
        name_entry.insert(0, n)

    def create_sv():
        base_path = path_var.get().strip()
        name = name_entry.get().strip()

        if not base_path:
            messagebox.showerror("Erreur", "Choisissez un dossier de mod")
            return
        if not name:
            messagebox.showerror("Erreur", "Le nom est vide")
            return

        path = _file_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)

        existing = ""
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                existing = f.read()

        if re.search(rf"^{re.escape(name)}\s*=", existing, re.MULTILINE):
            messagebox.showerror("Erreur", f"'{name}' existe déjà dans le fichier")
            return

        block = _build_block(name, include_if_var.get())
        separator = "\n" if existing.strip() else ""

        with open(path, "a", encoding="utf-8") as f:
            f.write(separator + block)

        messagebox.showinfo("Succès", f"Script value '{name}' créée")
        refresh_name()

    # ----------------------------------------------------------------------- UI

    tk.Label(frame, text="Script Values", font=("", 11, "bold")).pack(pady=(8, 2))

    row_name = tk.Frame(frame)
    row_name.pack(pady=4)
    tk.Label(row_name, text="Nom").pack(side="left")
    name_entry = tk.Entry(row_name, width=38)
    name_entry.pack(side="left", padx=4)
    tk.Button(row_name, text="Auto", command=refresh_name).pack(side="left")

    include_if_var = tk.BooleanVar(value=False)
    tk.Checkbutton(frame, text="Inclure bloc if / limit", variable=include_if_var).pack(pady=3)

    tk.Button(frame, text="Créer Script Value", command=create_sv).pack(pady=8)

    return frame
