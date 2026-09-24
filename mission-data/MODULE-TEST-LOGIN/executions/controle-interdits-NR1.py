#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Vérifie que .interdits contient le mot de passe de test (sans jamais l'afficher),
et l'y ajoute s'il manque. Rapporte uniquement le nombre de valeurs, jamais les valeurs.
"""
import os
import re

def lire_mdp_public():
    txt = open("AGENTS.md", encoding="utf-8").read()
    for line in txt.splitlines():
        if line.strip().startswith("- Mot de passe"):
            m = re.search(r"`([^`]+)`", line)
            if m:
                return m.group(1)
    raise SystemExit("mot de passe introuvable dans AGENTS.md")

interdits_path = "mission-data/MODULE-TEST-LOGIN/.interdits"
mdp = lire_mdp_public()

valeurs = []
if os.path.exists(interdits_path):
    with open(interdits_path, encoding="utf-8") as f:
        valeurs = [l.strip("\r\n") for l in f if l.strip()]

present = any(v == mdp for v in valeurs)
if not present:
    with open(interdits_path, "a", encoding="utf-8") as f:
        f.write(mdp + "\n")
    valeurs.append(mdp)

print(f"mot_de_passe_present_avant = {present}")
print(f"nb_valeurs_interdites_apres = {len(valeurs)}")
