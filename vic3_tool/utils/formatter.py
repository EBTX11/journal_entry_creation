def format_text(text):
    text = text.strip()

    # remplace double saut de ligne (paragraphe)
    text = text.replace("\n\n", "\\n\\n")

    # remplace saut simple
    text = text.replace("\n", "\\n")

    return text