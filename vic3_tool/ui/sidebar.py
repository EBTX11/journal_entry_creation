"""
Composant Sidebar pour EBTX-hmmf-tool
Navigation latérale avec le même style que EBTX-hmm-tool
"""

import tkinter as tk
from tkinter import ttk
from vic3_tool.ui.style import style_manager


class Sidebar:
    """Barre latérale de navigation"""
    
    def __init__(self, parent, on_nav_click=None):
        self.parent = parent
        self.on_nav_click = on_nav_click
        self._nav_buttons = {}
        self._current_key = None
        self._build()
    
    def _build(self):
        styles = style_manager
        
        # Conteneur sidebar
        self.frame = ttk.Frame(self.parent, style="Sidebar.TFrame", width=200)
        self.frame.pack(side="left", fill="y")
        self.frame.pack_propagate(False)
        
        # Titre principal
        title_label = ttk.Label(
            self.frame, 
            text="EBTX-HMMF", 
            style="SidebarTitle.TLabel"
        )
        title_label.pack(pady=(20, 2))
        
        # Sous-titre
        sub_label = ttk.Label(
            self.frame, 
            text="Victoria 3 Journal Entry Tool", 
            style="SidebarSub.TLabel"
        )
        sub_label.pack(pady=(0, 12))
        
        # Séparateur
        sep = tk.Frame(
            self.frame, 
            bg=styles.C_SURFACE, 
            height=1
        )
        sep.pack(fill="x", padx=12, pady=4)
        
        # Navigation - 5 éléments (Journal Entry fusionné)
        nav_items = [
            ("Journal Entry", "journal_entry"),
            ("Treaty", "treaty"),
            ("Event", "event"),
            ("Modifier", "modifier"),
            ("Script Value", "script_value"),
        ]
        
        for label, key in nav_items:
            btn = ttk.Button(
                self.frame, 
                text=label, 
                style="Nav.TButton",
                command=lambda k=key: self._on_nav_click(k)
            )
            btn.pack(fill="x", padx=6, pady=1)
            self._nav_buttons[key] = btn
        
        # Séparateur en bas
        sep2 = tk.Frame(
            self.frame, 
            bg=styles.C_SURFACE, 
            height=1
        )
        sep2.pack(fill="x", padx=12, pady=(12, 4), side="bottom")
        
        # Version
        version_label = ttk.Label(
            self.frame, 
            text="v1.0 — EBTX-HMMF", 
            style="SidebarSub.TLabel"
        )
        version_label.pack(side="bottom", pady=6)
        
        # Sélectionner le premier élément par défaut
        self._set_active("journal_entry")
    
    def _on_nav_click(self, key):
        if self.on_nav_click:
            self.on_nav_click(key)
        self._set_active(key)
    
    def _set_active(self, key):
        """Met en évidence le bouton de navigation actif"""
        # Réinitialiser tous les boutons
        for btn_key, btn in self._nav_buttons.items():
            if btn_key == key:
                btn.configure(style="NavActive.TButton")
            else:
                btn.configure(style="Nav.TButton")
        self._current_key = key
    
    def set_active(self, key):
        """Méthode publique pour changer l'élément actif depuis l'extérieur"""
        self._set_active(key)
    
    def get_frame(self):
        """Retourne le frame de la sidebar"""
        return self.frame