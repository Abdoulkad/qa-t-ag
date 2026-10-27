#!/usr/bin/env python3
"""Contrôle de format des scénarios de performance (AG-11).

Valide scenarios-<projet>.csv (Type;Cible;Parametres;Criteres) :
chaque scénario doit avoir ses 4 champs, un Type connu et des champs non vides.

Usage : python controler_scenarios.py <scenarios.csv>
Codes : 0 = conforme, 1 = incohérences (listées), 2 = entrée inexploitable,
        3 = défaut.
Auto-test : python controler_scenarios.py --selftest
"""

import csv
import os
import shutil
import sys
import tempfile

EN_TETE = ["Type", "Cible", "Parametres", "Criteres"]
TYPES = {"charge", "stress", "endurance", "pic", "volume"}


def controler(chemin):
    if not os.path.isfile(chemin):
        return 2, "fichier introuvable : %s" % chemin
    try:
        with open(chemin, "r", encoding="utf-8-sig") as f:
            lignes = list(csv.reader(f, delimiter=";"))
    except Exception as e:
        return 3, "défaut du script : %s" % e
    if not lignes or lignes[0] != EN_TETE:
        return 2, "en-tête non conforme : %s" % (lignes[0] if lignes else "(vide)")
    incoherences = []
    for i, l in enumerate(lignes[1:], start=2):
        if len(l) < 4:
            incoherences.append("ligne %d : %d champs (4 attendus)" % (i, len(l)))
            continue
        typ, cible, params, crit = [c.strip() for c in l[:4]]
        if typ not in TYPES:
            incoherences.append("ligne %d : Type inconnu %r (attendu %s)"
                                % (i, typ, "/".join(sorted(TYPES))))
        if not cible or not params or not crit:
            incoherences.append("ligne %d : champ vide (Cible/Parametres/Criteres)" % i)
    n = len(lignes) - 1
    if incoherences:
        return 1, "scénarios : %d ; incohérences : %d\n%s" % (
            n, len(incoherences), "\n".join("  - " + x for x in incoherences))
    return 0, "scénarios : %d ; conforme" % n


def _auto_test():
    echecs = []
    rep = tempfile.mkdtemp()
    f = os.path.join(rep, "scenarios-demo.csv")
    try:
        with open(f, "w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh, delimiter=";")
            w.writerow(EN_TETE)
            w.writerow(["charge", "GET /login", "100 VU, 10 min", "temps < 2s, erreurs < 1%"])
            w.writerow(["stress", "POST /auth", "VU croissants jusqu'à rupture", "dégradation maîtrisée"])
        code, msg = controler(f)
        if code != 0:
            echecs.append(("2 scénarios valides -> code %d" % code, msg))
        with open(f, "w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh, delimiter=";")
            w.writerow(EN_TETE)
            w.writerow(["inconnu", "", "", ""])
        code, msg = controler(f)
        if code != 1:
            echecs.append(("scénario invalide -> code %d" % code, msg))
    finally:
        shutil.rmtree(rep, ignore_errors=True)
    return echecs


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--selftest":
        e = _auto_test()
        if e:
            for x in e:
                print("ÉCHEC:", x)
            sys.exit(1)
        print("Auto-test controler_scenarios.py : OK (conforme, type inconnu)")
        sys.exit(0)
    if len(sys.argv) != 2:
        print("Usage : python controler_scenarios.py <scenarios.csv>", file=sys.stderr)
        sys.exit(3)
    code, msg = controler(sys.argv[1])
    print(msg)
    sys.exit(code)
