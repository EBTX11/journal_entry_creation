def generate_progress_bar(pb):
    color    = pb.get("color", "default_green = yes")
    start    = pb.get("start", 0)
    min_val  = pb.get("min", 0)
    max_val  = pb.get("max", 100)

    second_desc_line = f'\n    second_desc = "{pb["key"]}_second_desc"' if pb.get("second_desc") else ""
    inverted_line    = "\n    is_inverted = yes"                         if pb.get("is_inverted") else ""

    monthly_block = ""
    if pb.get("monthly_value"):
        monthly_desc  = pb.get("monthly_desc") or f"{pb['key']}_monthly_progress"
        monthly_block = f"""
    monthly_progress = {{
        add = {{
            desc = "{monthly_desc}"
            value = {pb['monthly_value']}
        }}
    }}"""

    return f"""
{pb['key']} = {{
    name = "{pb['key']}"
    desc = "{pb['key']}_desc"{second_desc_line}{inverted_line}

    {color}

    start_value = {start}
    min_value = {min_val}
    max_value = {max_val}{monthly_block}
}}
"""