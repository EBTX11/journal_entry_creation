"""Application principale EBTX-hmmf-tool
Interface simplifiee : Sidebar + Vues directes (sans onglets)
Theme Catppuccin/Mocha"""

import tkinter as tk
from tkinter import StringVar, ttk

from vic3_tool.ui.style import style_manager
from vic3_tool.ui.sidebar import Sidebar
from vic3_tool.ui.topbar import TopBar
from vic3_tool.ui.tabs.create_tab import build_create_tab
from vic3_tool.ui.tabs.manage_tab import build_manage_tab
from vic3_tool.ui.tabs.treaty_tab import build_treaty_tab
from vic3_tool.ui.tabs.event_tab import build_event_tab
from vic3_tool.ui.tabs.modifier_tab import build_modifier_tab
from vic3_tool.ui.tabs.script_value_tab import build_script_value_tab


class EBTXApp:
    """Application principale avec interface simplifiee sans onglets"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("EBTX-HMMF Tool  —  Victoria 3 Journal Entry Creator")
        self.root.geometry("1280x780")
        self.root.minsize(960, 620)
        
        # Variables globales
        self.path_var = StringVar()
        self.tag_var = StringVar()
        
        # Configuration du style
        self._setup_style()
        
        # Construction de l'interface
        self._build_layout()
        
        # etat de navigation
        self._current_view = None
        self._view_frames = {}
        
        # Creer les vues
        self._build_views()
        
        # Afficher la premiere vue par defaut
        self._show_view("journal_entry")
    
    def _setup_style(self):
        """Configure le style global de l'application"""
        style_manager.setup_style(self.root)
    
    def _build_layout(self):
        """Construit la structure principale de l'interface"""
        # Conteneur principal
        main_container = ttk.Frame(self.root)
        main_container.pack(fill="both", expand=True)
        
        # Sidebar de navigation
        self.sidebar = Sidebar(main_container, on_nav_click=self._on_nav_click)
        
        # Conteneur de droite (topbar + contenu)
        right_container = ttk.Frame(main_container)
        right_container.pack(side="right", fill="both", expand=True)
        
        # Topbar
        self.topbar = TopBar(right_container, self.path_var, self.tag_var)
        
        # Zone de contenu principal (cadre pour les vues)
        self.content_frame = ttk.Frame(right_container)
        self.content_frame.pack(fill="both", expand=True, padx=10, pady=10)
    
    def _build_views(self):
        """Cree les vues de l'application (une par categorie)"""
        
        # Vue "Journal Entry" - avec les deux onglets fusionnes
        journal_entry_frame = ttk.Frame(self.content_frame)
        
        # Creer un mini-notebook pour Journal Entry seulement
        je_notebook = ttk.Notebook(journal_entry_frame)
        je_notebook.pack(fill="both", expand=True)
        
        # Ajouter les deux onglets pour Journal Entry
        create_view = build_create_tab(je_notebook, self.path_var, self.tag_var)
        manage_view = build_manage_tab(je_notebook, self.path_var, self.tag_var)
        
        je_notebook.add(create_view, text="Creation JE")
        je_notebook.add(manage_view, text="Gestion JE")
        
        self._view_frames["journal_entry"] = journal_entry_frame
        
        # Les autres categories - affichage direct sans onglets
        self._view_frames["treaty"] = build_treaty_tab(
            self.content_frame, self.path_var, self.tag_var
        )
        self._view_frames["event"] = build_event_tab(
            self.content_frame, self.path_var, self.tag_var
        )
        self._view_frames["modifier"] = build_modifier_tab(
            self.content_frame, self.path_var, self.tag_var
        )
        self._view_frames["script_value"] = build_script_value_tab(
            self.content_frame, self.path_var, self.tag_var
        )
    
    def _on_nav_click(self, key):
        """Callback lorsque l'utilisateur clique sur un element de la sidebar"""
        self._show_view(key)
    
    def _show_view(self, key):
        """Affiche la vue correspondante a la cle"""
        if key not in self._view_frames:
            return
        
        # Masquer la vue actuelle
        if self._current_view:
            self._view_frames[self._current_view].pack_forget()
        
        # Afficher la nouvelle vue
        self._view_frames[key].pack(fill="both", expand=True)
        self._current_view = key
        
        # Mettre a jour la sidebar
        self.sidebar.set_active(key)


# Instance racine globale pour la compatibilite avec run_ app.py
root = tk.Tk()
app = EBTXApp(root)


if __name__ == "__main__":
    root.mainloop()