"""
Composant Topbar pour EBTX-hmmf-tool
Barre supérieure affichant le chemin du mod et le TAG
"""

import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from vic3_tool.ui.style import style_manager


class TopBar:
    """Barre supérieure avec informations contextuelles"""
    
    def __init__(self, parent, path_var, tag_var):
        self.parent = parent
        self.path_var = path_var
        self.tag_var = tag_var
        self._build()
    
    def _build(self):
        styles = style_manager
        
        # Conteneur topbar
        self.frame = ttk.Frame(self.parent, style="TopBar.TFrame")
        self.frame.pack(side="top", fill="x")
        
        # Zone gauche : Chemin du mod
        left_frame = ttk.Frame(self.frame, style="TopBar.TFrame")
        left_frame.pack(side="left", fill="x", expand=True, padx=12, pady=8)
        
        # Label pour le chemin
        path_label = ttk.Label(
            left_frame, 
            text="Mod: ", 
            style="TopBarPath.TLabel"
        )
        path_label.pack(side="left")
        
        # Label dynamique pour le chemin
        self._path_display = ttk.Label(
            left_frame, 
            text="(non configure)", 
            style="TopBarPath.TLabel"
        )
        self._path_display.pack(side="left")
        
        # Bouton pour changer le dossier
        browse_btn = ttk.Button(
            left_frame,
            text="Changer",
            style="TButton",
            command=self._browse_folder
        )
        browse_btn.pack(side="left", padx=(10, 0))
        
        # Mise a jour de l'affichage du chemin
        self._update_path_display()
        
        # Zone droite : TAG
        right_frame = ttk.Frame(self.frame, style="TopBar.TFrame")
        right_frame.pack(side="right", padx=12, pady=8)
        
        tag_label = ttk.Label(
            right_frame,
            text="TAG: ",
            style="TopBar.TLabel"
        )
        tag_label.pack(side="left")
        
        # Entry pour le TAG
        self._tag_entry = ttk.Entry(
            right_frame,
            textvariable=self.tag_var,
            width=10,
            style="TEntry"
        )
        self._tag_entry.pack(side="left", padx=5)
        
        # Observer les changements de chemin
        self.path_var.trace_add("write", self._on_path_change)
    
    def _browse_folder(self):
        """Ouvre une boite de dialogue pour selectionner le dossier du mod"""
        path = filedialog.askdirectory(
            title="Selectionne le dossier du mod",
            initialdir=self.path_var.get() or "C:/"
        )
        if path:
            self.path_var.set(path)
    
    def _on_path_change(self, *args):
        """Callback lorsque le chemin change"""
        self._update_path_display()
    
    def _update_path_display(self):
        """Met a jour l'affichage du chemin"""
        path = self.path_var.get()
        if path:
            # Afficher juste le nom du dossier
            name = path.split('/')[-1] if '/' in path else path.split('\\')[-1]
            self._path_display.config(text=f"{name}   ({path})")
        else:
            self._path_display.config(text="(non configure)")
    
    def get_frame(self):
        """Retourne le frame de la topbar"""
        return self.frame