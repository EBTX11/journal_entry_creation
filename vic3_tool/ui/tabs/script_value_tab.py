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

    def _global_file_path():
        return os.path.join(
            path_var.get(), "common", "history", "global", "00_hmmai_global.txt"
        )

    def _find_block_end(text, open_brace_pos):
        """Return index of the } that closes the { at open_brace_pos."""
        depth = 0
        for i in range(open_brace_pos, len(text)):
            if text[i] == '{':
                depth += 1
            elif text[i] == '}':
                depth -= 1
                if depth == 0:
                    return i
        return -1

    def _ensure_global_file():
        path = _global_file_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if not os.path.exists(path):
            with open(path, "w", encoding="utf-8") as f:
                f.write("GLOBAL = {\n}\n")
        return path

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

    def _next_var_name():
        tag = tag_var.get().strip()
        if not tag:
            return ""
        path = _global_file_path()
        existing = ""
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                existing = f.read()
        n = 1
        while f"{tag}_variable_{n}" in existing:
            n += 1
        return f"{tag}_variable_{n}"

    def _next_global_var_name():
        tag = tag_var.get().strip()
        if not tag:
            return ""
        path = _global_file_path()
        existing = ""
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                existing = f.read()
        n = 1
        while f"{tag}_global_variable_{n}" in existing:
            n += 1
        return f"{tag}_global_variable_{n}"

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

    def refresh_var_name():
        n = _next_var_name()
        if not n:
            messagebox.showwarning("Attention", "Définissez d'abord un TAG")
            return
        var_name_entry.delete(0, tk.END)
        var_name_entry.insert(0, n)

    def create_var():
        base_path = path_var.get().strip()
        name = var_name_entry.get().strip()

        if not base_path:
            messagebox.showerror("Erreur", "Choisissez un dossier de mod")
            return
        if not name:
            messagebox.showerror("Erreur", "Le nom est vide")
            return

        path = _ensure_global_file()

        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        if f"name = {name}" in content:
            messagebox.showerror("Erreur", f"'{name}' existe déjà dans le fichier")
            return

        new_block = (
            f"\t\tset_variable = {{\n"
            f"\t\t\tname = {name}\n"
            f"\t\t\tvalue = 1\n"
            f"\t\t}}\n"
        )

        global_match = re.search(r'GLOBAL\s*=\s*\{', content)
        if not global_match:
            messagebox.showerror("Erreur", "Bloc GLOBAL introuvable dans le fichier")
            return

        global_open = global_match.end() - 1  # position of '{'
        global_end = _find_block_end(content, global_open)

        global_inner = content[global_match.end():global_end]
        ec_match = re.search(r'every_country\s*=\s*\{', global_inner)

        if ec_match:
            ec_open_in_full = global_match.end() + ec_match.end() - 1
            ec_end = _find_block_end(content, ec_open_in_full)
            line_start = content.rfind('\n', 0, ec_end) + 1
            content = content[:line_start] + new_block + content[line_start:]
        else:
            ec_block = (
                f"\tevery_country = {{\n"
                f"{new_block}"
                f"\t}}\n"
            )
            line_start = content.rfind('\n', 0, global_end) + 1
            content = content[:line_start] + ec_block + content[line_start:]

        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

        messagebox.showinfo("Succès", f"Variable définie '{name}' créée")
        refresh_var_name()

    def refresh_global_var_name():
        n = _next_global_var_name()
        if not n:
            messagebox.showwarning("Attention", "Définissez d'abord un TAG")
            return
        global_var_name_entry.delete(0, tk.END)
        global_var_name_entry.insert(0, n)

    def create_global_var():
        base_path = path_var.get().strip()
        name = global_var_name_entry.get().strip()

        if not base_path:
            messagebox.showerror("Erreur", "Choisissez un dossier de mod")
            return
        if not name:
            messagebox.showerror("Erreur", "Le nom est vide")
            return

        path = _ensure_global_file()

        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        if f"name = {name}" in content:
            messagebox.showerror("Erreur", f"'{name}' existe déjà dans le fichier")
            return

        new_block = (
            f"\tset_global_variable = {{\n"
            f"\t\tname = {name}\n"
            f"\t\tvalue = 0\n"
            f"\t}}\n"
        )

        global_match = re.search(r'GLOBAL\s*=\s*\{', content)
        if not global_match:
            messagebox.showerror("Erreur", "Bloc GLOBAL introuvable dans le fichier")
            return

        global_open = global_match.end() - 1
        global_end = _find_block_end(content, global_open)
        line_start = content.rfind('\n', 0, global_end) + 1

        content = content[:line_start] + new_block + content[line_start:]

        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

        messagebox.showinfo("Succès", f"Variable globale '{name}' créée")
        refresh_global_var_name()

    # ----------------------------------------------------------------------- UI

    # ── Section Script Values ──────────────────────────────────────────────────
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

    # ── Section Variable Définie Simple ────────────────────────────────────────
    tk.Frame(frame, height=1, bg="gray").pack(fill="x", padx=10, pady=(4, 2))
    tk.Label(frame, text="Variable Définie (every_country)", font=("", 11, "bold")).pack(pady=(4, 2))
    tk.Label(
        frame,
        text="→ common/history/global/00_hmmai_global.txt",
        font=("", 8),
        fg="gray"
    ).pack()

    row_var = tk.Frame(frame)
    row_var.pack(pady=4)
    tk.Label(row_var, text="Nom").pack(side="left")
    var_name_entry = tk.Entry(row_var, width=38)
    var_name_entry.pack(side="left", padx=4)
    tk.Button(row_var, text="Auto", command=refresh_var_name).pack(side="left")

    tk.Button(frame, text="Créer Variable Définie", command=create_var).pack(pady=8)

    # ── Section Variable Définie Globale ───────────────────────────────────────
    tk.Frame(frame, height=1, bg="gray").pack(fill="x", padx=10, pady=(4, 2))
    tk.Label(frame, text="Variable Définie Globale (GLOBAL)", font=("", 11, "bold")).pack(pady=(4, 2))
    tk.Label(
        frame,
        text="→ common/history/global/00_hmmai_global.txt",
        font=("", 8),
        fg="gray"
    ).pack()

    row_gvar = tk.Frame(frame)
    row_gvar.pack(pady=4)
    tk.Label(row_gvar, text="Nom").pack(side="left")
    global_var_name_entry = tk.Entry(row_gvar, width=38)
    global_var_name_entry.pack(side="left", padx=4)
    tk.Button(row_gvar, text="Auto", command=refresh_global_var_name).pack(side="left")

    tk.Button(frame, text="Créer Variable Globale", command=create_global_var).pack(pady=8)

    return frame
