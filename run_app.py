import sys
import os

# ajoute le dossier racine au path
sys.path.append(os.path.dirname(__file__))

from vic3_tool.ui.app import root

root.mainloop()