#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Wrapper d'exécution — non-régression NR1 (SFD-TEST-001 v1.0).

Lit le mot de passe de test PUBLIC (documenté dans AGENTS.md, donnée de démo)
et l'expose via TEST_PASSWORD, puis exécute le runner Playwright.
Le mot de passe n'est jamais écrit en clair dans ce fichier ni dans les sorties.
"""
import os
import re
import subprocess
import sys


def lire_mdp_public():
    txt = open("AGENTS.md", encoding="utf-8").read()
    for line in txt.splitlines():
        if line.strip().startswith("- Mot de passe"):
            m = re.search(r"`([^`]+)`", line)
            if m:
                return m.group(1)
    raise SystemExit("mot de passe de test introuvable dans AGENTS.md")


env = dict(os.environ)
env["TEST_PASSWORD"] = lire_mdp_public()
rc = subprocess.run(
    [sys.executable,
     "mission-data/MODULE-TEST-LOGIN/executions/runner-SFD-TEST-001.py"],
    env=env,
)
sys.exit(rc.returncode)
