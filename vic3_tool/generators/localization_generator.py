from vic3_tool.utils.formatter import format_text


def generate_localization(je, buttons_data):
    loc = ""

    # JE
    loc += f'  {je.key}:0 "{je.title}"\n'
    loc += f'  {je.key}_reason:0 "{format_text(je.desc)}"\n'

    # BOUTONS
    for i, btn_data in enumerate(buttons_data, start=1):
        btn = f"{je.key}_button_{i}"

        name = btn_data["name"]
        desc = btn_data["desc"]

        tt1 = btn_data.get("tt1", "Nothing")
        tt2 = btn_data.get("tt2", "Nothing")

        loc += f'  {btn}:0 "{name}"\n'
        loc += f'  {btn}_desc:0 "{desc}"\n'
        loc += f'  {btn}_tt_1:0 "{tt1}"\n'
        loc += f'  {btn}_tt_2:0 "{tt2}"\n'

    return loc