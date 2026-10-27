#!/usr/bin/env python3
"""Contrôle de format des tests de sécurité (AG-12).

Valide tests-securite-<projet>.csv (ID;Cible;Vulnerabilite;Reference;Risque) :
référence WSTG-xxx-xxx ou ASVS-x.y.z valide, niveau de risque connu.

Usage : python controler_securite.py <tests-securite.csv>
Codes : 0 = conforme, 1 = incohérences, 2 = entrée inexploitable, 3 = défaut.
Auto-test : python controler_securite.py --selftest
"""

import csv
import os
import re
import shutil
import sys
import tempfile

EN_TETE = ["ID", "Cible", "Vulnerabilite", "Reference", "Risque"]
RE_WSTG = re.compile(r"^WSTG-[A-Z]{4}-\d{2}$")
RE_ASVS = re.compile(r"^ASVS-\d+\.\d+\.\d+-\d+\.\d+\.\d+$")
RISQUES = {"faible", "moyen", "élevé", "critique"}


def _ref_valide(r):
    return bool(RE_WSTG.match(r) or RE_ASVS.match(r))


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
        if len(l) < 5:
            incoherences.append("ligne %d : %d champs (5 attendus)" % (i, len(l)))
            continue
        cid, cible, vuln, ref, risque = [c.strip() for c in l[:5]]
        if not cid or not cible or not vuln:
            incoherences.append("ligne %d : champ vide (ID/Cible/Vulnerabilite)" % i)
        if not _ref_valide(ref):
            incoherences.append("ligne %d : référence invalide %r (attendu WSTG-XXXX-NN ou ASVS-x.y.z-w.x.y)" % (i, ref))
        if risque not in RISQUES:
            incoherences.append("ligne %d : risque inconnu %r (attendu %s)"
                                % (i, risque, "/".join(sorted(RISQUES))))
    n = len(lignes) - 1
    if incoherences:
        return 1, "tests : %d ; incohérences : %d\n%s" % (
            n, len(incoherences), "\n".join("  - " + x for x in incoherences))
    return 0, "tests : %d ; conforme" % n


def _auto_test():
    echecs = []
    rep = tempfile.mkdtemp()
    f = os.path.join(rep, "tests-securite-demo.csv")
    try:
        with open(f, "w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh, delimiter=";")
            w.writerow(EN_TETE)
            w.writerow(["SEC-001", "POST /login", "injection SQL", "WSTG-INPV-05", "élevé"])
            w.writerow(["SEC-002", "GET /compte", "contrôle d'accès", "ASVS-4.0.3-4.1.1", "critique"])
        code, msg = controler(f)
        if code != 0:
            echecs.append(("2 tests valides -> code %d" % code, msg))
        with open(f, "w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh, delimiter=";")
            w.writerow(EN_TETE)
            w.writerow(["SEC-003", "GET /", "x", "WSTG-INVALIDE", "énorme"])
        code, msg = controler(f)
        if code != 1:
            echecs.append(("test invalide -> code %d" % code, msg))
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
        print("Auto-test controler_securite.py : OK (WSTG, ASVS, risque)")
        sys.exit(0)
    if len(sys.argv) != 2:
        print("Usage : python controler_securite.py <tests-securite.csv>", file=sys.stderr)
        sys.exit(3)
    code, msg = controler(sys.argv[1])
    print(msg)
    sys.exit(code)
