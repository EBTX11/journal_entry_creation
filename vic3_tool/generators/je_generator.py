import os

TEMPLATE_PATH = os.path.join(
    os.path.dirname(__file__),
    "../templates/je_templates.txt"
)

def generate_je_block(je, num_buttons, conditions="", immediate=""):
    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        template = f.read()

    buttons = ""
    for i in range(1, num_buttons + 1):
        buttons += f"    scripted_button = {je.key}_button_{i}\n"

    return template.format(
        KEY=je.key,
        TAG=je.tag,
        YEAR=je.year,
        CONDITIONS=conditions,
        IMMEDIATE=immediate,
        BUTTONS=buttons
    )
