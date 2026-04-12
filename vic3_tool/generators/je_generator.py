import os


def generate_je_goal_progress_block(je, global_var, pb_key, goal_value, pulse="monthly"):
    """Génère un JE suivant le schéma 'progress bar pilotée par une variable globale'."""
    return f"""{je.key} = {{
    icon = "gfx/interface/icons/event_icons/{je.key}.dds"

    group = je_group_historical_content
    should_be_pinned_by_default = yes

    modifiers_while_active = {{
    }}

    is_shown_when_inactive = {{
        exists = c:{je.tag}
        c:{je.tag} ?= THIS
    }}

    possible = {{
        game_date >= {je.year}.1.1
    }}

    immediate = {{
    }}

    complete = {{
        scope:journal_entry = {{ is_goal_complete = yes }}
    }}

    fail = {{
    }}

    on_complete = {{
    }}

    on_fail = {{
    }}

    scripted_progress_bar = {pb_key}

    on_{pulse}_pulse = {{
        effect = {{
            scope:journal_entry ?= {{
                if = {{
                    limit = {{
                    }}
                    change_global_variable = {{
                        name = {global_var}
                        add = 1
                    }}
                }}
            }}
            je:{je.key} ?= {{
                set_bar_progress = {{
                    value = global_var:{global_var}
                    name = {pb_key}
                }}
            }}
        }}
    }}

    current_value = {{
        value = global_var:{global_var}
    }}
    goal_add_value = {{
        value = {goal_value}
    }}
}}
"""


TEMPLATE_PATH = os.path.join(
    os.path.dirname(__file__),
    "../templates/je_templates.txt"
)


def generate_je_block(je, options):
    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        template = f.read()

    # -------- IS_SHOWN_WHEN_INACTIVE --------

    is_shown_conditions = options.get("is_shown")
    if is_shown_conditions is not None:
        # Les conditions sont déjà formatées et indentées par l'UI
        lines = "\n".join(is_shown_conditions) if is_shown_conditions else ""
        is_shown_block = f"""    is_shown_when_inactive = {{
{lines}
    }}
"""
    else:
        is_shown_block = f"""    is_shown_when_inactive = {{
        exists = c:{je.tag}
        c:{je.tag} ?= THIS
    }}
"""

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
        progress_link = "\n".join(
            f"    scripted_progress_bar = {pb['key']}"
            for pb in options["progress_bars"]
        )

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

    # -------- BUTTONS --------

    buttons = ""
    if options.get("buttons"):
        for i in range(1, options["buttons"] + 1):
            buttons += f"    scripted_button = {je.key}_button_{i}\n"

    # -------- POSSIBLE (conditions supplémentaires) --------

    possible_lines = options.get("possible_conditions")
    possible_cond_str = ("\n".join(possible_lines) + "\n") if possible_lines else ""

    # -------- COMPLETE --------

    complete_lines = options.get("complete_conditions")
    complete_cond_str = ("\n".join(complete_lines) + "\n") if complete_lines else ""

    # -------- FAIL --------

    fail_cond_str = ""
    fail_lines = options.get("fail_conditions")
    if fail_lines is not None:
        fail_cond_str = ("\n".join(fail_lines) + "\n") if fail_lines else ""

    # -------- ON_COMPLETE --------

    return template.format(
        KEY=je.key,
        TAG=je.tag,
        YEAR=je.year,
        IS_SHOWN=is_shown_block,
        POSSIBLE_COND=possible_cond_str,
        COMPLETE_COND=complete_cond_str,
        STATUS_DESC=status_block,
        PROGRESS_BAR_LINK=progress_link,
        IMMEDIATE="",
        FAIL_COND=fail_cond_str,
        ON_COMPLETE="",
        ON_MONTHLY=monthly_progress if monthly_progress else monthly_empty,
        ON_YEARLY=yearly_block,
        BUTTONS=buttons
    )
