def _build_tt_block(block_name, btn_name, btn_data):
    """Génère un bloc possible/effect avec custom_tooltips."""
    modified_key = f"{block_name}_modified"
    raw_key      = f"{block_name}_raw"
    tts_key      = f"{block_name}_tts"
    existing_key = f"{block_name}_existing_tt_count"

    if btn_data.get(modified_key) and btn_data.get(raw_key) is not None:
        raw_inner      = btn_data[raw_key]
        tts            = btn_data.get(tts_key) or []
        existing_count = btn_data.get(existing_key, len(tts))
        new_tts        = tts[existing_count:]
        if new_tts:
            start_num  = existing_count + 1
            injections = "\n".join(
                f"        custom_tooltip = {{\n            text = {btn_name}_tt_{block_name}_{start_num + j}\n        }}"
                for j in range(len(new_tts))
            )
            raw_inner = raw_inner.rstrip() + "\n" + injections + "\n    "
        return f"    {block_name} = {{{raw_inner}}}"
    else:
        tts = btn_data.get(tts_key) or ["Nothing"]
        tt_lines = "\n".join(
            f"        custom_tooltip = {{\n            text = {btn_name}_tt_{block_name}_{j}\n        }}"
            for j in range(1, len(tts) + 1)
        )
        return f"    {block_name} = {{\n{tt_lines}\n    }}"


def generate_buttons(je, buttons_data):
    content = ""

    for i, btn_data in enumerate(buttons_data, start=1):
        btn = f"{je.key}_button_{i}"

        cooldown_block = ""
        if btn_data.get("cooldown"):
            unit = btn_data.get("cooldown_unit") or "days"
            cooldown_block = f"""
    cooldown = {{ {unit} = {btn_data['cooldown']} }}
"""

        # ── possible / effect blocks ────────────────────────────────
        possible_block = _build_tt_block("possible", btn, btn_data)
        effect_block   = _build_tt_block("effect",   btn, btn_data)

        # ── visible block ───────────────────────────────────────────
        if btn_data.get("visible_modified") and btn_data.get("visible_raw") is not None:
            visible_block = f"    visible = {{{btn_data['visible_raw']}}}"
        else:
            visible_block = "    visible = {\n    }"

        # ── ai_chance block ─────────────────────────────────────────
        if btn_data.get("ai_chance_modified") and btn_data.get("ai_chance_raw") is not None:
            ai_chance_block = f"    ai_chance = {{{btn_data['ai_chance_raw']}}}"
        else:
            ai_chance_block = "    ai_chance = {\n        value = 10\n    }"

        content += f"""{btn} = {{
    name = "{btn}"
    desc = "{btn}_desc"

{visible_block}

{possible_block}
{cooldown_block}
{effect_block}

{ai_chance_block}
}}

"""
    return content
