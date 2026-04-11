def generate_buttons(je, buttons_data):
    content = ""

    for i, btn_data in enumerate(buttons_data, start=1):
        btn = f"{je.key}_button_{i}"

        cooldown_block = ""
        if btn_data.get("cooldown"):
            cooldown_block = f"""
    cooldown = {{ days = {btn_data['cooldown']} }}
"""

        content += f"""{btn} = {{
    name = "{btn}"
    desc = "{btn}_desc"

    visible = {{
    }}

    possible = {{
        custom_tooltip = {{
            text = {btn}_tt_1
        }}
    }}
{cooldown_block}
    effect = {{
        custom_tooltip = {{
            text = {btn}_tt_2
        }}
    }}

    ai_chance = {{
        value = 10
    }}
}}

"""
    return content