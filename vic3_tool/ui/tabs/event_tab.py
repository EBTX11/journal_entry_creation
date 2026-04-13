import tkinter as tk
from tkinter import ttk, messagebox
import os
import re

from vic3_tool.utils.formatter import format_text
from vic3_tool.utils.file_manager import read_file


# ================================================================
# UTILITAIRES DE PARSING
# ================================================================

def find_block_range(content, key):
    m = re.search(rf"{re.escape(key)}\s*=\s*\{{", content)
    if not m:
        return None
    start = m.start()
    i = m.end() - 1
    depth = 0
    while i < len(content):
        if content[i] == '{':
            depth += 1
        elif content[i] == '}':
            depth -= 1
            if depth == 0:
                return (start, i + 1)
        i += 1
    return None


def extract_named_block(content, name):
    m = re.search(rf"\b{re.escape(name)}\s*=\s*\{{", content)
    if not m:
        return None
    start = m.end() - 1
    depth = 0
    i = start
    while i < len(content):
        if content[i] == '{':
            depth += 1
        elif content[i] == '}':
            depth -= 1
            if depth == 0:
                return content[start + 1:i]
        i += 1
    return None


def parse_event_data(event_path, loc_path, key):
    """Parse les données d'un événement depuis le fichier event et localisation"""
    data = {
        "title": "",
        "desc": "",
        "flavor": "",
        "options": [],
    }
    
    event_content = read_file(event_path)
    loc_content = read_file(loc_path) if os.path.exists(loc_path) else ""
    
    # Trouver le bloc de l'événement
    br = find_block_range(event_content, key)
    if not br:
        return data
    
    block = event_content[br[0]:br[1]]
    safe_key = re.escape(key)
    
    # Extraire les options - chercher tous les blocs option = { ... }
    lines = block.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i]
        if re.match(r'^\s*option\s*=\s*\{', line):
            # Trouver la fin du bloc option
            brace_count = 0
            j = i
            while j < len(lines):
                brace_count += lines[j].count('{') - lines[j].count('}')
                if brace_count == 0 and j > i:
                    break
                j += 1

            opt_data = {"name": "", "desc": "", "is_default": False, "tooltip": ""}

            # Analyser le contenu de l'option
            for opt_line in lines[i:j+1]:
                name_m = re.match(r'^\s*name\s*=\s*(\S+)', opt_line)
                if name_m:
                    opt_data["name"] = name_m.group(1)

                # Chercher le custom_tooltip
                tooltip_m = re.search(r'custom_tooltip\s*=\s*\{[^}]*text\s*=\s*(\S+)', opt_line)
                if not tooltip_m:
                    # Essayer sur plusieurs lignes
                    if 'custom_tooltip' in opt_line and '{' in opt_line:
                        # Chercher dans les lignes suivantes
                        for k in range(i, j+1):
                            text_m = re.search(r'text\s*=\s*(\S+)', lines[k])
                            if text_m:
                                opt_data["tooltip"] = text_m.group(1)
                                break
                    elif 'text' in opt_line and not name_m:
                        text_m = re.search(r'text\s*=\s*(\S+)', opt_line)
                        if text_m:
                            opt_data["tooltip"] = text_m.group(1)
                else:
                    opt_data["tooltip"] = tooltip_m.group(1)

                if 'option_par_d' in opt_line or 'option_par_defaut' in opt_line:
                    opt_data["is_default"] = True

            if opt_data["name"]:
                data["options"].append(opt_data)
        i += 1

    # Extraire la localisation
    if loc_content:
        # Titre
        m = re.search(rf'^\s*{safe_key}\.t:0\s+"(.*?)"', loc_content, re.MULTILINE)
        if m:
            data["title"] = m.group(1)
        # Description
        m = re.search(rf'^\s*{safe_key}\.d:1\s+"(.*?)"', loc_content, re.MULTILINE)
        if m:
            data["desc"] = m.group(1)
        # Flavor
        m = re.search(rf'^\s*{safe_key}\.f:1\s+"(.*?)"', loc_content, re.MULTILINE)
        if m:
            data["flavor"] = m.group(1)

        # Noms des options et tooltips
        for opt in data["options"]:
            name_key = opt["name"]
            m = re.search(rf'^\s*{re.escape(name_key)}:0\s+"(.*?)"', loc_content, re.MULTILINE)
            if m:
                opt["name_text"] = m.group(1)

            # Chercher le tooltip
            tooltip_key = opt.get("tooltip", "")
            if tooltip_key:
                m = re.search(rf'^\s*{re.escape(tooltip_key)}:0\s+"(.*?)"', loc_content, re.MULTILINE)
                if m:
                    opt["tooltip_text"] = m.group(1)

    return data


def remove_loc_entries_event(content, key):
    """Supprime les entrées de localisation pour un événement"""
    safe_key = re.escape(key)
    # Supprimer les entrées .t, .d, .f, .aN et _desc.aN (tooltips)
    content = re.sub(rf'[ \t]*{safe_key}\.(t|d|f)(:[^\n]*)?\n', '', content)
    content = re.sub(rf'[ \t]*{safe_key}\.a\d+(:[^\n]*)?\n', '', content)
    content = re.sub(rf'[ \t]*{safe_key}_desc\.a\d+(:[^\n]*)?\n', '', content)
    return content


def patch_named_block_event(content, block_name, new_text):
    """Remplace block_name = { ... } dans content"""
    br = find_block_range(content, block_name)
    if br:
        line_start = content.rfind('\n', 0, br[0]) + 1
        if content[line_start:br[0]].strip() == '':
            return content[:line_start] + new_text + content[br[1]:]
        return content[:br[0]] + new_text + content[br[1]:]
    last = content.rfind('}')
    if last >= 0:
        return content[:last] + '\n' + new_text + '\n' + content[last:]
    return content + '\n' + new_text


# ================================================================
# ONGLET EVENT
# ================================================================

def build_event_tab(parent, path_var, tag_var):
    outer = ttk.Frame(parent)
    paned = ttk.PanedWindow(outer, orient="horizontal")
    paned.pack(fill="both", expand=True)

    # ── Panneau GAUCHE : liste des événements ─────────────────
    left = ttk.Frame(paned, width=220)
    paned.add(left, weight=0)

    tk.Label(left, text="Evénements", font=("Arial", 11, "bold")).pack(pady=(8, 2))
    tk.Button(left, text="Charger la liste", command=lambda: load_event_list()).pack(pady=2)

    listbox_frame = ttk.Frame(left)
    listbox_frame.pack(fill="both", expand=True, padx=4)
    event_listbox = tk.Listbox(listbox_frame, selectmode="single", width=26)
    sb_list = ttk.Scrollbar(listbox_frame, command=event_listbox.yview)
    event_listbox.config(yscrollcommand=sb_list.set)
    event_listbox.pack(side="left", fill="both", expand=True)
    sb_list.pack(side="right", fill="y")

    action_row = ttk.Frame(left)
    action_row.pack(pady=6)
    tk.Button(action_row, text="Charger", width=8,
              command=lambda: load_selected_event()).pack(side="left")
    tk.Button(action_row, text="X", width=3,
              command=lambda: delete_selected_event(), fg="red").pack(side="left", padx=(4, 0))

    current_key_var = tk.StringVar(value="")
    tk.Label(left, textvariable=current_key_var,
             foreground="blue", font=("Arial", 9)).pack(pady=2)

    # ── Panneau DROIT : formulaire de création / édition ─────────
    right = ttk.Frame(paned)
    paned.add(right, weight=1)

    form_outer = ttk.LabelFrame(right, text="Créer / Modifier un Event")
    form_outer.pack(fill="both", expand=True, padx=6, pady=6)

    canvas = tk.Canvas(form_outer, borderwidth=0, highlightthickness=0)
    scrollbar = ttk.Scrollbar(form_outer, orient="vertical", command=canvas.yview)
    form = ttk.Frame(canvas)
    form.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=form, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    # ── Champs de base ──────────────────────────────────────
    base_frame = ttk.LabelFrame(form, text="Informations de base")
    base_frame.pack(fill="x", padx=8, pady=6)
    base_frame.columnconfigure(1, weight=1)

    tk.Label(base_frame, text="Titre :").grid(row=0, column=0, sticky="w", padx=6, pady=3)
    title_var = tk.StringVar()
    tk.Entry(base_frame, textvariable=title_var, width=40).grid(row=0, column=1, sticky="ew", padx=6, pady=3)

    tk.Label(base_frame, text="Description (header) :").grid(row=1, column=0, sticky="nw", padx=6, pady=3)
    desc_text = tk.Text(base_frame, height=4, width=40)
    desc_text.grid(row=1, column=1, sticky="ew", padx=6, pady=3)

    tk.Label(base_frame, text="Flavor :").grid(row=2, column=0, sticky="nw", padx=6, pady=3)
    flavor_text = tk.Text(base_frame, height=5, width=40)
    flavor_text.grid(row=2, column=1, sticky="ew", padx=6, pady=3)

    # ── Options Frame ───────────────────────────────────────
    options_section = ttk.LabelFrame(form, text="Options de l'événement")
    options_section.pack(fill="x", padx=8, pady=6)

    options_data = []  # Stocke les widgets pour les options
    options_widgets_frame = ttk.Frame(options_section)
    options_widgets_frame.pack(fill="x", padx=4, pady=4)

    def clear_options():
        """Efface tous les champs d'option"""
        for w in options_widgets_frame.winfo_children():
            w.destroy()
        options_data.clear()


    def add_option_widget(name="", is_default=False, tooltip_text=""):
        """Ajoute un widget de configuration d'option"""
        row_frame = ttk.Frame(options_widgets_frame)
        row_frame.pack(fill="x", pady=2)
        
        # Sous-frame pour la rangée principale
        main_row = ttk.Frame(row_frame)
        main_row.pack(fill="x")
        
        # Numéro de l'option
        opt_num = len(options_data) + 1
        tk.Label(main_row, text=f"Option {opt_num}:", width=10).pack(side="left", padx=2)
        
        # Nom de l'option
        name_var = tk.StringVar(value=name)
        tk.Entry(main_row, textvariable=name_var, width=18).pack(side="left", padx=2)
        
        # Checkbox option par défaut
        default_var = tk.BooleanVar(value=is_default)
        tk.Checkbutton(main_row, text="Par défaut", variable=default_var).pack(side="left", padx=4)
        
        # Bouton supprimer
        def remove_this():
            row_frame.destroy()
            # Retrouver et supprimer dans options_data
            for i, item in enumerate(options_data):
                if item[0] == row_frame:
                    options_data.pop(i)
                    break
            # Renuméroter les options restantes
            renumber_options()
        
        tk.Button(main_row, text="X", command=remove_this, width=2, fg="red").pack(side="right", padx=2)
        

        # Sous-frame pour le tooltip (description uniquement)
        tooltip_row = ttk.Frame(row_frame)
        tooltip_row.pack(fill="x", padx=(24, 0), pady=2)
        











        tk.Label(tooltip_row, text="Tooltip desc:", width=12).pack(side="left")
        tooltip_text_var = tk.StringVar(value=tooltip_text)
        tk.Entry(tooltip_row, textvariable=tooltip_text_var, width=50).pack(side="left", fill="x", expand=True, padx=2)

        options_data.append((row_frame, name_var, default_var, tooltip_text_var))
    def renumber_options():
        """Renumérote les options après suppression"""
        for i, item in enumerate(options_data, start=1):
            w = item[0]
            # Trouver le label et le mettre à jour
            for child in w.winfo_children():
                if hasattr(child, 'winfo_children'):
                    for subchild in child.winfo_children():
                        if isinstance(subchild, tk.Label) and subchild.cget("text").startswith("Option"):
                            subchild.config(text=f"Option {i}:")
                        break

    # Bouton pour ajouter une option
    tk.Button(options_section, text="+ Ajouter une option",
              command=lambda: add_option_widget()).pack(anchor="w", padx=4, pady=2)

    # Ajouter une option par défaut au départ
    add_option_widget()

    # ── Boutons d'action ─────────────────────────────────────
    button_frame = ttk.Frame(form)
    button_frame.pack(fill="x", padx=8, pady=6)

    # Bouton Créer un nouvel événement
    tk.Button(button_frame, text="Créer Nouvel Event",
              command=lambda: create_new_event(),
              bg="green", fg="white", font=("Arial", 10, "bold"),
              padx=10, pady=4).pack(side="left", padx=4)

    # Bouton Sauvegarder les modifications
    tk.Button(button_frame, text="Sauvegarder Modifications",
              command=lambda: save_event_changes(),
              bg="#2196F3", fg="white", font=("Arial", 10, "bold"),
              padx=10, pady=4).pack(side="left", padx=4)

    # ================================================================
    # FONCTIONS
    # ================================================================

    def get_next_event_version(tag, path):
        """Récupère la prochaine version d'événement au format TAG_event_majeur.mineur"""
        if not os.path.exists(path):
            return "1.1"

        content = read_file(path)
        pattern = rf"{tag}_event_(\d+)\.(\d+)"
        matches = re.findall(pattern, content)

        if not matches:
            return "1.1"

        versions = [(int(major), int(minor)) for major, minor in matches]
        versions.sort(key=lambda x: (x[0], x[1]))
        last_major, last_minor = versions[-1]

        return f"{last_major}.{last_minor + 1}"

    def create_new_event():
        """Crée un nouvel événement"""
        base_path = path_var.get()
        tag = tag_var.get().upper()

        title = title_var.get().strip()
        desc = format_text(desc_text.get("1.0", "end").strip())
        flavor = format_text(flavor_text.get("1.0", "end").strip())

        if not base_path or not tag:
            messagebox.showerror("Erreur", "Dossier ou TAG manquant")
            return

        if not title:
            messagebox.showerror("Erreur", "Le titre est obligatoire")
            return

        # Paths
        event_path = os.path.join(base_path, "events", f"{tag}.txt")
        loc_path = os.path.join(base_path, "localization/english", "00_hmmf_events_l_english.yml")

        os.makedirs(os.path.dirname(event_path), exist_ok=True)
        os.makedirs(os.path.dirname(loc_path), exist_ok=True)

        # Générer la nouvelle version
        version = get_next_event_version(tag, event_path)
        key = f"{tag}_event_{version}"

        # Collecter les options
        options = []
        for i, item in enumerate(options_data, start=1):

            w, name_var, default_var, tooltip_text_var = item
            opt_name = name_var.get().strip()



            opt_tooltip_text = tooltip_text_var.get().strip()
            # Auto-générer la clé seulement s'il y a du texte tooltip





            opt_tooltip_key = f"{key}_desc.a{i}" if opt_tooltip_text else ""
            if opt_name:
                options.append({
                    'index': i,
                    'name': opt_name,
                    'tooltip_key': opt_tooltip_key,
                    'tooltip_text': opt_tooltip_text,
                    'is_default': default_var.get(),
                    'loc_key': f"{key}.a{i}"
                })

        if not options:
            options.append({
                'index': 1,
                'name': "Acknowledged",
                'tooltip_key': "",
                'tooltip_text': "",
                'is_default': True,
                'loc_key': f"{key}.a1"
            })

        # Construire le block d'options
        options_block = ""
        for opt in options:
            default_marker = "        option_par_défaut = oui" if opt['is_default'] else ""
            tooltip_block = f"        custom_tooltip = {{\n            text = {opt['tooltip_key']}\n        }}" if opt['tooltip_key'] else ""
            options_block += f"""    option = {{
        name = {opt['loc_key']}
{tooltip_block}
{default_marker}
    }}
"""
        # Construire le block d'événement
        event_block = f"""
{key} = {{
    type = country_event
    placement = scope:capital_state

    title = {key}.t
    desc = {key}.d
    flavor = {key}.f

    duration = 3

    event_image = {{
        video = "unspecific_signed_contract"
    }}

    on_created_soundeffect = "event:/SFX/UI/Alerts/event_appear"

    icon = "gfx/interface/icons/event_icons/event_default.dds"

    trigger = {{
    }}

    immediate = {{
    }}

{options_block}}}
"""

        # Écrire l'événement
        with open(event_path, "a", encoding="utf-8") as f:
            f.write(event_block)

        # Écrire la localisation
        if not os.path.exists(loc_path):
            loc_content = "l_english:\n\n"
        else:
            loc_content = read_file(loc_path)

        new_loc = f"""
  {key}.t:0 "{title}"
  {key}.d:1 "{desc}"
  {key}.f:1 "{flavor}"
"""
        for opt in options:
            new_loc += f"  {opt['loc_key']}:0 \"{opt['name']}\"\n"
            if opt['tooltip_key'] and opt['tooltip_text']:
                new_loc += f"  {opt['tooltip_key']}:0 \"{opt['tooltip_text']}\"\n"

        loc_content += "\n" + new_loc

        with open(loc_path, "w", encoding="utf-8") as f:
            f.write(loc_content)

        # Mettre à jour la clé courante
        current_key_var.set(key)

        # Rafraîchir la liste
        load_event_list()

        messagebox.showinfo("Succès", f"Event {key} créé avec {len(options)} option(s)")

    def save_event_changes():
        """Sauvegarde les modifications d'un événement existant"""
        key = current_key_var.get()
        if not key:
            messagebox.showerror("Erreur", "Aucun événement chargé")
            return

        base_path = path_var.get()
        tag = tag_var.get().upper()

        title = title_var.get().strip()
        desc = format_text(desc_text.get("1.0", "end").strip())
        flavor = format_text(flavor_text.get("1.0", "end").strip())

        if not title:
            messagebox.showerror("Erreur", "Le titre est obligatoire")
            return

        event_path = os.path.join(base_path, "events", f"{tag}.txt")
        loc_path = os.path.join(base_path, "localization/english", "00_hmmf_events_l_english.yml")

        # Collecter les options
        options = []
        for i, item in enumerate(options_data, start=1):

            w, name_var, default_var, tooltip_text_var = item
            opt_name = name_var.get().strip()



            opt_tooltip_text = tooltip_text_var.get().strip()
            # Auto-générer la clé seulement s'il y a du texte tooltip





            opt_tooltip_key = f"{key}_desc.a{i}" if opt_tooltip_text else ""
            if opt_name:
                options.append({
                    'index': i,
                    'name': opt_name,
                    'tooltip_key': opt_tooltip_key,
                    'tooltip_text': opt_tooltip_text,
                    'is_default': default_var.get(),
                    'loc_key': f"{key}.a{i}"
                })

        if not options:
            options.append({
                'index': 1,
                'name': "Acknowledged",
                'tooltip_key': "",
                'tooltip_text': "",
                'is_default': True,
                'loc_key': f"{key}.a1"
            })

        # Construire le block d'options
        options_block = ""
        for opt in options:
            default_marker = "        option_par_défaut = oui" if opt['is_default'] else ""
            tooltip_block = f"        custom_tooltip = {{\n            text = {opt['tooltip_key']}\n        }}" if opt['tooltip_key'] else ""
            options_block += f"""    option = {{
        name = {opt['loc_key']}
{tooltip_block}
{default_marker}
    }}
"""

        # Lire et modifier le fichier d'événement
        event_content = read_file(event_path)

        # Trouver et remplacer le bloc de l'événement
        br = find_block_range(event_content, key)
        if br:
            event_content = event_content[:br[0]] + event_content[br[1]:]

        # Retirer les anciennes options et ajouter les nouvelles
        event_block = f"""
{key} = {{
    type = country_event
    placement = scope:capital_state

    title = {key}.t
    desc = {key}.d
    flavor = {key}.f

    duration = 3

    event_image = {{
        video = "unspecific_signed_contract"
    }}

    on_created_soundeffect = "event:/SFX/UI/Alerts/event_appear"

    icon = "gfx/interface/icons/event_icons/event_default.dds"

    trigger = {{
    }}

    immediate = {{
    }}

{options_block}}}
"""

        event_content = event_content.rstrip() + "\n\n" + event_block

        with open(event_path, "w", encoding="utf-8") as f:
            f.write(event_content)

        # Mettre à jour la localisation
        loc_content = read_file(loc_path) if os.path.exists(loc_path) else "l_english:\n"
        loc_content = remove_loc_entries_event(loc_content, key)

        new_loc = f"""
  {key}.t:0 "{title}"
  {key}.d:1 "{desc}"
  {key}.f:1 "{flavor}"
"""
        for opt in options:
            new_loc += f"  {opt['loc_key']}:0 \"{opt['name']}\"\n"
            if opt['tooltip_key'] and opt['tooltip_text']:
                new_loc += f"  {opt['tooltip_key']}:0 \"{opt['tooltip_text']}\"\n"

        loc_content = loc_content.rstrip() + "\n" + new_loc

        with open(loc_path, "w", encoding="utf-8") as f:
            f.write(loc_content)
        messagebox.showinfo("Succès", f"Event {key} sauvegardé avec {len(options)} option(s)")

    def load_event_list():
        """Charge la liste des événements existants"""
        event_listbox.delete(0, tk.END)
        tag = tag_var.get().upper()
        base_path = path_var.get()
        path = os.path.join(base_path, "events", f"{tag}.txt")

        if not os.path.exists(path):
            return

        content = read_file(path)
        # Chercher toutes les clés au format TAG_event_X.Y
        pattern = rf"{tag}_event_\d+\.\d+"
        matches = re.findall(pattern, content)

        for m in sorted(set(matches)):
            event_listbox.insert(tk.END, m)

    def load_selected_event():
        """Charge l'événement sélectionné dans le formulaire"""
        sel = event_listbox.curselection()
        if not sel:
            return

        key = event_listbox.get(sel[0])
        tag = tag_var.get().upper()
        base_path = path_var.get()

        event_path = os.path.join(base_path, "events", f"{tag}.txt")
        loc_path = os.path.join(base_path, "localization/english", "00_hmmf_events_l_english.yml")

        # Parser les données
        data = parse_event_data(event_path, loc_path, key)

        # Mettre à jour la clé courante
        current_key_var.set(key)

        # Remplir le formulaire
        title_var.set(data.get("title", ""))
        desc_text.delete("1.0", "end")
        desc_text.insert("1.0", data.get("desc", "").replace("\\n", "\n"))
        flavor_text.delete("1.0", "end")
        flavor_text.insert("1.0", data.get("flavor", "").replace("\\n", "\n"))

        # Charger les options
        clear_options()
        options = data.get("options", [])
        if not options:
            add_option_widget()
        else:
            for opt in options:
                name_text = opt.get("name_text", "")
                if not name_text:
                    # Essayer d'extraire le nom depuis la clé
                    name_match = re.search(r'\.a(\d+)$', opt.get("name", ""))
                    if name_match:
                        name_text = opt.get("name", "")
                raw_tooltip = opt.get("tooltip", "")
                # Si la valeur contient des espaces, c'est un texte littéral, pas une clé
                if " " in raw_tooltip:


                    tooltip_text = raw_tooltip
                else:



                    tooltip_text = opt.get("tooltip_text", "")
                add_option_widget(name=name_text, is_default=opt.get("is_default", False), tooltip_text=tooltip_text)

    def delete_selected_event():
        """Supprime l'événement sélectionné"""
        sel = event_listbox.curselection()
        if not sel:
            messagebox.showwarning("Avertissement", "Sélectionnez un événement à supprimer")
            return

        key = event_listbox.get(sel[0])
        tag = tag_var.get().upper()
        base_path = path_var.get()

        if not messagebox.askyesno("Confirmation", f"Supprimer {key} et toutes ses données liées ?"):
            return

        event_path = os.path.join(base_path, "events", f"{tag}.txt")
        loc_path = os.path.join(base_path, "localization/english", "00_hmmf_events_l_english.yml")

        try:
            # Supprimer le bloc d'événement
            event_content = read_file(event_path)
            br = find_block_range(event_content, key)
            if br:
                event_content = (event_content[:br[0]] + event_content[br[1]:]).strip()
                with open(event_path, "w", encoding="utf-8") as f:
                    f.write(event_content + "\n" if event_content else "")

            # Supprimer les entrées de localisation
            if os.path.exists(loc_path):
                loc_content = read_file(loc_path)
                loc_content = remove_loc_entries_event(loc_content, key)
                with open(loc_path, "w", encoding="utf-8") as f:
                    f.write(loc_content.rstrip() + "\n")

            event_listbox.delete(sel[0])

            # Réinitialiser le formulaire
            current_key_var.set("")
            title_var.set("")
            desc_text.delete("1.0", "end")
            flavor_text.delete("1.0", "end")
            clear_options()
            add_option_widget()
            messagebox.showinfo("Succès", f"{key} a été supprimé")
        except Exception as e:
            messagebox.showerror("Erreur", f"{type(e).__name__}: {e!s}")

    return outer
