"""Définit l'identifiant et le mot de passe de la page.

    python3 app/set_password.py config.json     (puis redémarrer : docker compose restart)
"""
import getpass
import json
import os
import sys

from auth import hash_password

path = sys.argv[1] if len(sys.argv) > 1 else "config.json"
with open(path, encoding="utf-8") as f:
    config = json.load(f)
current = config.get("auth", {}).get("user") or "admin"
user = input(f"Identifiant [{current}] : ").strip() or current
password = getpass.getpass("Mot de passe : ")
if not password or password != getpass.getpass("Confirmation : "):
    sys.exit("Mots de passe vides ou différents : rien n'a changé.")
config["auth"] = {"user": user, "password_hash": hash_password(password)}
# Réécrit le fichier en place : propriétaire et droits (600) conservés
descriptor = os.open(path, os.O_WRONLY | os.O_TRUNC)
os.write(descriptor, json.dumps(config, indent=2, ensure_ascii=False).encode())
os.close(descriptor)
print("Mot de passe enregistré. Redémarrer l'application pour l'appliquer.")
