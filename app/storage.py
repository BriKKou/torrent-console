"""Fichiers JSON du dossier de données."""
import json
import os


def read_json(path: str, default):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path: str, data) -> None:
    # Écriture dans un fichier temporaire puis renommage : jamais de fichier à moitié écrit
    temporary = f"{path}.tmp"
    with open(temporary, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    os.replace(temporary, path)
