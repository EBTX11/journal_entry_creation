from vic3_tool.utils.formatter import format_text


def generate_localization(je, buttons_data, progress_bars=None, status_desc=None):
    loc = ""

    # -------- JE --------
    loc += f'  {je.key}:0 "{je.title}"\n'
    loc += f'  {je.key}_reason:0 "{format_text(je.desc)}"\n'

    # -------- STATUS DESC --------
    if status_desc:
        for i, text in enumerate(status_desc, start=1):
            key = f"{je.key}_status_desc_{i}"
            loc += f'  {key}:0 "{text}"\n'

    # -------- BOUTONS --------
    for i, btn_data in enumerate(buttons_data, start=1):
        btn = f"{je.key}_button_{i}"

        name = btn_data.get("name", "")
        desc = btn_data.get("desc", "")
        tt1  = btn_data.get("tt1", "Nothing")
        tt2  = btn_data.get("tt2", "Nothing")

        loc += f'  {btn}:0 "{name}"\n'
        loc += f'  {btn}_desc:0 "{desc}"\n'
        loc += f'  {btn}_tt_1:0 "{tt1}"\n'
        loc += f'  {btn}_tt_2:0 "{tt2}"\n'

    # -------- PROGRESS BARS --------
    if progress_bars:
        for pb in progress_bars:
            loc += f'  {pb["key"]}:0 "{pb["name"]}"\n'
            loc += f'  {pb["key"]}_desc:0 "{pb["desc"]}"\n'

    return loc
