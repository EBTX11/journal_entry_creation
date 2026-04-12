def generate_buttons(je, buttons_data):
    content = ""

    for i, btn_data in enumerate(buttons_data, start=1):
        btn = f"{je.key}_button_{i}"

        cooldown_block = ""
        if btn_data.get("cooldown"):
            cooldown_block = f"""
    cooldown = {{ days = {btn_data['cooldown']} }}
"""

        # ── possible block ──────────────────────────────────────────
        if btn_data.get("possible_modified") and btn_data.get("possible_raw") is not None:
            # Bloc modifié manuellement : on préserve le contenu existant
            # et on injecte uniquement les nouvelles entrées TT (au-delà du compte initial)
            raw_inner      = btn_data["possible_raw"]
            possible_tts   = btn_data.get("possible_tts") or []
            existing_count = btn_data.get("possible_existing_tt_count", len(possible_tts))
            new_tts        = possible_tts[existing_count:]

            if new_tts:
                start_num  = existing_count + 1
                injections = "\n".join(
                    f"        custom_tooltip = {{\n            text = {btn}_tt_possible_{start_num + j}\n        }}"
                    for j in range(len(new_tts))
                )
                raw_inner = raw_inner.rstrip() + "\n" + injections + "\n    "

            possible_block = f"    possible = {{{raw_inner}}}"
        else:
            possible_tts = btn_data.get("possible_tts") or ["Nothing"]
            tt_lines = "\n".join(
                f"        custom_tooltip = {{\n            text = {btn}_tt_possible_{j}\n        }}"
                for j in range(1, len(possible_tts) + 1)
            )
            possible_block = f"    possible = {{\n{tt_lines}\n    }}"

        # ── effect block ────────────────────────────────────────────
        effect_tts = btn_data.get("effect_tts") or ["Nothing"]
        effect_tt_lines = "\n".join(
            f"        custom_tooltip = {{\n            text = {btn}_tt_effect_{j}\n        }}"
            for j in range(1, len(effect_tts) + 1)
        )
        effect_block = f"    effect = {{\n{effect_tt_lines}\n    }}"

        # ── visible block ───────────────────────────────────────────
        if btn_data.get("visible_modified") and btn_data.get("visible_raw") is not None:
            visible_block = f"    visible = {{{btn_data['visible_raw']}}}"
        else:
            visible_block = "    visible = {\n    }"

        content += f"""{btn} = {{
    name = "{btn}"
    desc = "{btn}_desc"

{visible_block}

{possible_block}
{cooldown_block}
{effect_block}

    ai_chance = {{
        value = 10
    }}
}}

"""
    return content
