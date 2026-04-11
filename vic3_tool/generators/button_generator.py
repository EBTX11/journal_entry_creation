def generate_buttons(je, buttons_data):
    content = ""

    for i, btn_data in enumerate(buttons_data, start=1):
        btn = f"{je.key}_button_{i}"

        content += f"""{btn} = {{
    name = "{btn}"
    desc = "{btn}_desc"

    visible = {{
        always = yes 
        NOT = {{ 
        }}
        OR = {{ 
        }}  
    }}

    possible = {{
        NOT = {{ 
        }} 
        custom_tooltip = {{
            text = {btn}_tt_1
            NOT = {{ 
            }} 
        }} 
    }}

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