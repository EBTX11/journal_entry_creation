def generate_progress_bar(pb):
    color = pb.get("color", "default_green = yes")
    start = pb.get("start", 0)
    min_val = pb.get("min", 0)
    max_val = pb.get("max", 100)

    return f"""
{pb['key']} = {{
    name = "{pb['key']}"
    desc = "{pb['key']}_desc"

    {color}

    start_value = {start}
    min_value = {min_val}
    max_value = {max_val}
}}
"""