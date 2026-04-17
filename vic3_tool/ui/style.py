"""
Module de style pour EBTX-hmmf-tool
Thème Catppuccin/Mocha - Identique à EBTX-hmm-tool
"""

import tkinter as tk
from tkinter import ttk


class StyleManager:
    """Gestionnaire de style centralisé pour l'application"""
    
    # Couleurs - Thème Catppuccin/Mocha
    C_BG       = "#1e1e2e"
    C_SIDEBAR  = "#181825"
    C_SURFACE  = "#313244"
    C_SURFACE2 = "#45475a"
    C_FG       = "#cdd6f4"
    C_ACCENT   = "#cba6f7"
    C_GREEN    = "#a6e3a1"
    C_RED      = "#f38ba8"
    C_YELLOW   = "#f9e2af"
    C_BLUE     = "#89b4fa"
    C_TEXT_DIM = "#6c7086"
    
    def __init__(self):
        self.root = None
        
    def setup_style(self, root):
        """Configure le style global de l'application"""
        self.root = root
        style = ttk.Style()
        style.theme_use("clam")
        
        BG = self.C_BG
        SIDEBAR = self.C_SIDEBAR
        SURF = self.C_SURFACE
        SURF2 = self.C_SURFACE2
        FG = self.C_FG
        ACC = self.C_ACCENT
        
        # Configuration de la fenêtre principale
        root.configure(bg=BG)
        
        # Style global
        style.configure(".", background=BG, foreground=FG, font=("Segoe UI", 9))
        style.configure("TFrame", background=BG)
        style.configure("TLabel", background=BG, foreground=FG)
        
        # Boutons standard
        style.configure("TButton", 
                        background=SURF, 
                        foreground=FG, 
                        borderwidth=0,
                        relief="flat", 
                        padding=(8, 5))
        style.map("TButton",
                  background=[("active", SURF2), ("pressed", SURF2)],
                  foreground=[("active", ACC)])
        
        # Boutons d'accent (pour actions principales)
        style.configure("Accent.TButton", 
                        background=ACC, 
                        foreground=BG, 
                        font=("Segoe UI", 9, "bold"))
        style.map("Accent.TButton", 
                  background=[("active", "#b4befe")])
        
        # Bouton succès (vert)
        style.configure("Success.TButton",
                        background=self.C_GREEN,
                        foreground=BG,
                        font=("Segoe UI", 9, "bold"))
        style.map("Success.TButton",
                  background=[("active", "#94e2d5")])
        
        # Bouton danger (rouge)
        style.configure("Danger.TButton",
                        background=self.C_RED,
                        foreground=BG,
                        font=("Segoe UI", 9, "bold"))
        style.map("Danger.TButton",
                  background=[("active", "#f5a8ba")])
        
        # Sidebar
        style.configure("Sidebar.TFrame", background=SIDEBAR)
        style.configure("SidebarTitle.TLabel", 
                        background=SIDEBAR, 
                        foreground=ACC,
                        font=("Segoe UI", 13, "bold"))
        style.configure("SidebarSub.TLabel", 
                        background=SIDEBAR, 
                        foreground=self.C_TEXT_DIM,
                        font=("Segoe UI", 8))
        
        # Navigation
        style.configure("Nav.TButton", 
                        background=SIDEBAR, 
                        foreground=FG,
                        font=("Segoe UI", 10), 
                        borderwidth=0, 
                        relief="flat",
                        padding=(12, 9), 
                        anchor="w")
        style.map("Nav.TButton",
                  background=[("active", SURF), ("pressed", SURF)],
                  foreground=[("active", ACC)])
        
        style.configure("NavActive.TButton", 
                        background=SURF, 
                        foreground=ACC,
                        font=("Segoe UI", 10, "bold"), 
                        borderwidth=0, 
                        relief="flat",
                        padding=(12, 9), 
                        anchor="w")
        
        # Topbar
        style.configure("TopBar.TFrame", background=SURF)
        style.configure("TopBar.TLabel", 
                        background=SURF, 
                        foreground=FG, 
                        font=("Segoe UI", 9))
        style.configure("TopBarPath.TLabel", 
                        background=SURF, 
                        foreground=self.C_TEXT_DIM,
                        font=("Segoe UI", 8))
        
        # Entrées de texte
        style.configure("TEntry", 
                        fieldbackground=SURF, 
                        foreground=FG,
                        insertcolor=FG, 
                        borderwidth=1)
        style.map("TEntry",
                  fieldbackground=[("readonly", SURF2)])
        
        # Listes déroulantes
        style.configure("TCombobox", 
                        fieldbackground=SURF, 
                        foreground=FG)
        style.map("TCombobox", 
                  fieldbackground=[("readonly", SURF)],
                  foreground=[("readonly", FG)],
                  background=[("readonly", SURF)],
                  arrowcolor=[("readonly", FG)])
        
        # Notebooks (onglets)
        style.configure("TNotebook", 
                        background=BG, 
                        borderwidth=0)
        style.configure("TNotebook.Tab", 
                        background=SURF, 
                        foreground=FG,
                        padding=(10, 5), 
                        font=("Segoe UI", 9))
        style.map("TNotebook.Tab",
                  background=[("selected", SURF2)],
                  foreground=[("selected", ACC)])
        
        # Cadres avec étiquettes
        style.configure("TLabelframe", 
                        background=BG, 
                        foreground=FG, 
                        bordercolor=SURF2)
        style.configure("TLabelframe.Label", 
                        background=BG, 
                        foreground=ACC,
                        font=("Segoe UI", 9, "bold"))
        
        # Scrollbars
        style.configure("TScrollbar", 
                        background=SURF, 
                        troughcolor=BG, 
                        borderwidth=0)
        style.configure("Vertical.TScrollbar",
                        background=SURF,
                        troughcolor=BG,
                        width=12)
        
        # Checkbuttons
        style.configure("TCheckbutton", 
                        background=BG, 
                        foreground=FG)
        style.map("TCheckbutton", 
                  background=[("active", BG)])
        
        # Radio buttons
        style.configure("TRadiobutton",
                        background=BG,
                        foreground=FG)
        style.map("TRadiobutton",
                  background=[("active", BG)],
                  indicatorcolor=[("selected", ACC)])
        
        # Separators
        style.configure("TSeparator", background=SURF2)
        
        # Progress bars
        style.configure("Horizontal.TProgressbar",
                        background=ACC,
                        troughcolor=SURF,
                        borderwidth=0)
        
        # Text (pour les zones de texte multiples)
        style.configure("Text", 
                        background=SURF, 
                        foreground=FG,
                        insertcolor=FG,
                        relief="flat",
                        borderwidth=0)
        
        return style
    
    # ============== Méthodes utilitaires pour les widgets ==============
    
    def create_styled_label(self, parent, text="", **kwargs):
        """Crée un label tk avec le style du thème"""
        return tk.Label(
            parent, 
            text=text, 
            bg=self.C_SURFACE, 
            fg=self.C_FG,
            **kwargs
        )
    
    def create_styled_entry(self, parent, textvariable=None, **kwargs):
        """Crée une entrée tk avec le style du thème"""
        return tk.Entry(
            parent,
            textvariable=textvariable,
            bg=self.C_SURFACE,
            fg=self.C_FG,
            insertbackground=self.C_FG,
            relief="flat",
            borderwidth=1,
            **kwargs
        )
    
    def create_styled_button(self, parent, text="", command=None, **kwargs):
        """Crée un bouton tk avec le style du thème"""
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=self.C_SURFACE,
            fg=self.C_FG,
            activebackground=self.C_SURFACE2,
            activeforeground=self.C_ACCENT,
            relief="flat",
            borderwidth=0,
            **kwargs
        )
    
    def create_styled_text(self, parent, **kwargs):
        """Crée une zone de texte tk avec le style du thème"""
        return tk.Text(
            parent,
            bg=self.C_SURFACE,
            fg=self.C_FG,
            insertbackground=self.C_FG,
            relief="flat",
            borderwidth=1,
            **kwargs
        )


# Instance globale du gestionnaire de style
style_manager = StyleManager()
