import os

def ensure_folder(path):
    os.makedirs(path, exist_ok=True)

def append_to_file(path, content):
    with open(path, "a", encoding="utf-8") as f:
        f.write(content)

def read_file(path):
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()