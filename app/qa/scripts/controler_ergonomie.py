#!/usr/bin/env python3
"""Contrôle de format des remarques ergonomie/accessibilité (AG-13).

Valide remarques-<projet>.csv (Element;Constat;Regle;Gravite) : règle
WCAG-x.y.z ou RGAA-x.y.z valide, gravité connue.

Usage : python controler_ergonomie.py <remarques.csv>
Codes : 0 = conforme, 1 = incohérences, 2 = entrée inexploitable, 3 = défaut.
Auto-test : python controler_ergonomie.py --selftest
"""

import csv
import os
import re
import shutil
import sys
import tempfile

EN_TETE = ["Element", "Constat", "Regle", "Gravite"]
RE_WCAG = re.compile(r"^WCAG-\d+\.\d+\.\d+$")
RE_RGAA = re.compile(r"^RGAA-\d+\.\d+\.\d+$")
GRAVITES = {"mineur", "moyen", "majeur", "bloquant"}


def _regle_valide(r):
    return bool(RE_WCAG.match(r) or RE_RGAA.match(r))


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
        elem, constat, regle, grav = [c.strip() for c in l[:4]]
        if not elem or not constat:
            incoherences.append("ligne %d : champ vide (Element/Constat)" % i)
        if not _regle_valide(regle):
            incoherences.append("ligne %d : règle invalide %r (attendu WCAG-x.y.z ou RGAA-x.y.z)" % (i, regle))
        if grav not in GRAVITES:
            incoherences.append("ligne %d : gravité inconnue %r (attendu %s)"
                                % (i, grav, "/".join(sorted(GRAVITES))))
    n = len(lignes) - 1
    if incoherences:
        return 1, "remarques : %d ; incohérences : %d\n%s" % (
            n, len(incoherences), "\n".join("  - " + x for x in incoherences))
    return 0, "remarques : %d ; conforme" % n


def _auto_test():
    echecs = []
    rep = tempfile.mkdtemp()
    f = os.path.join(rep, "remarques-demo.csv")
    try:
        with open(f, "w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh, delimiter=";")
            w.writerow(EN_TETE)
            w.writerow(["Bouton valider", "contraste insuffisant", "WCAG-1.4.3", "majeur"])
            w.writerow(["Titre page", "h1 absent", "RGAA-8.1.2", "moyen"])
        code, msg = controler(f)
        if code != 0:
            echecs.append(("2 remarques valides -> code %d" % code, msg))
        with open(f, "w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh, delimiter=";")
            w.writerow(EN_TETE)
            w.writerow(["", "", "WCAG-99", "grave"])
        code, msg = controler(f)
        if code != 1:
            echecs.append(("remarque invalide -> code %d" % code, msg))
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
        print("Auto-test controler_ergonomie.py : OK (WCAG, RGAA, gravité)")
        sys.exit(0)
    if len(sys.argv) != 2:
        print("Usage : python controler_ergonomie.py <remarques.csv>", file=sys.stderr)
        sys.exit(3)
    code, msg = controler(sys.argv[1])
    print(msg)
    sys.exit(code)
