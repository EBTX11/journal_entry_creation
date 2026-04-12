from tkinter import Tk, StringVar, Frame, Label, Entry, Button
from tkinter import filedialog
from tkinter import ttk

from vic3_tool.ui.tabs.create_tab import build_create_tab
from vic3_tool.ui.tabs.manage_tab import build_manage_tab
from vic3_tool.ui.tabs.treaty_tab import build_treaty_tab
from vic3_tool.ui.tabs.event_tab import build_event_tab
from vic3_tool.ui.tabs.modifier_tab import build_modifier_tab
from vic3_tool.ui.tabs.script_value_tab import build_script_value_tab

root = Tk()
root.title("Vic3 JE Tool")

# ----------- GLOBAL VAR -----------

path_var = StringVar()
tag_var = StringVar()

# ----------- TOP BAR -----------

top_frame = Frame(root)
top_frame.pack(pady=5)

def select_folder():
    path = filedialog.askdirectory()
    path_var.set(path)

Label(top_frame, text="Dossier du mod").grid(row=0, column=0)
Entry(top_frame, textvariable=path_var, width=40).grid(row=0, column=1)
Button(top_frame, text="Choisir", command=select_folder).grid(row=0, column=2)

Label(top_frame, text="TAG").grid(row=1, column=0)
Entry(top_frame, textvariable=tag_var).grid(row=1, column=1)

# ----------- TABS -----------

notebook = ttk.Notebook(root)
notebook.pack(fill="both", expand=True)

create_tab = build_create_tab(notebook, path_var, tag_var)
manage_tab = build_manage_tab(notebook, path_var, tag_var)
treaty_tab = build_treaty_tab(notebook, path_var, tag_var)
event_tab = build_event_tab(notebook, path_var, tag_var)
modifier_tab = build_modifier_tab(notebook, path_var, tag_var)
script_value_tab = build_script_value_tab(notebook, path_var, tag_var)

notebook.add(create_tab, text="Création JE")
notebook.add(manage_tab, text="Gestion JE")
notebook.add(treaty_tab, text="Treaty")
notebook.add(event_tab, text="Event")
notebook.add(modifier_tab, text="Modifier")
notebook.add(script_value_tab, text="Script Value")

root.mainloop()