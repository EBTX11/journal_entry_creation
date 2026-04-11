import os

TEMPLATE_PATH = os.path.join(
    os.path.dirname(__file__),
    "../templates/je_templates.txt"
)


def generate_je_block(je, options):
    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        template = f.read()

    # -------- STATUS DESC --------

    status_block = ""
    if options.get("status_desc"):
        entries = ""
        for i, text in enumerate(options["status_desc"], start=1):
            key = f"{je.key}_status_desc_{i}"

            entries += f"""
            triggered_desc = {{
                desc = {key}
                trigger = {{
                }}
            }}
"""

        status_block = f"""
    status_desc = {{
        first_valid = {{
{entries}
        }}
    }}
"""

    # -------- PROGRESS BAR --------

    progress_link = ""
    monthly_progress = ""

    if options.get("progress_bars"):
        progress_link = f"    scripted_progress_bar = {options['progress_bars'][0]['key']}"

        monthly_progress = """
    on_monthly_pulse = {
        effect = {
"""

        for pb in options["progress_bars"]:
            monthly_progress += f"""
            je:{je.key} ?= {{
                set_bar_progress = {{
                    value = 0
                    name = {pb['key']}
                }}
            }}
"""

        monthly_progress += """
        }
    }
"""

    # -------- MODULES SIMPLES --------

    monthly_empty = ""
    if options.get("monthly_empty") and not options.get("progress_bars"):
        monthly_empty = """
    on_monthly_pulse = {
        effect = {
        }
    }
"""

    yearly_block = ""
    if options.get("yearly"):
        yearly_block = """
    on_yearly_pulse = {
        effect = {
        }
    }
"""

    modifiers_block = ""
    if options.get("modifiers"):
        modifiers_block = """
    modifiers_while_active = {
    }
"""

    # -------- BUTTONS --------

    buttons = ""
    if options.get("buttons"):
        for i in range(1, options["buttons"] + 1):
            buttons += f"    scripted_button = {je.key}_button_{i}\n"

    return template.format(
        KEY=je.key,
        TAG=je.tag,
        YEAR=je.year,
        CONDITIONS=options.get("conditions", ""),
        STATUS_DESC=status_block,
        PROGRESS_BAR_LINK=progress_link,
        IMMEDIATE="",
        ON_MONTHLY=monthly_progress if monthly_progress else monthly_empty,
        ON_YEARLY=yearly_block,
        MODIFIERS=modifiers_block,
        BUTTONS=buttons
    )