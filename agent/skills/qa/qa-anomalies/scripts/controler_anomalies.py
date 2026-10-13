#!/usr/bin/env python3
"""Contrôle de format du registre d'anomalies (AG-09).

Valide anomalies-<projet>.csv (ID;CT;Severite;Reproductibilite;Traitement) :
ID unique ANO-xxx, CT existant, sévérité / reproductibilité / statut connus.

Usage : python controler_anomalies.py <anomalies.csv>
Codes : 0 = conforme, 1 = incohérences, 2 = entrée inexploitable, 3 = défaut.
Auto-test : python controler_anomalies.py --selftest
"""

import csv
import os
import re
import shutil
import sys
import tempfile

EN_TETE = ["ID", "CT", "Severite", "Reproductibilite", "Traitement"]
RE_ANO = re.compile(r"^ANO-\d{3}$")
RE_CT = re.compile(r"^CT-\d{3}$")
SEVERITES = {"mineure", "majeure", "critique", "bloquante"}
REPRO = {"systématique", "intermittente", "non reproductible"}
TRAITEMENTS = {"ouverte", "assignée", "corrigée", "retestée", "fermée"}


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
    vus = set()
    for i, l in enumerate(lignes[1:], start=2):
        if len(l) < 5:
            incoherences.append("ligne %d : %d champs (5 attendus)" % (i, len(l)))
            continue
        aid, ct, sev, repro, trait = [c.strip() for c in l[:5]]
        if not RE_ANO.match(aid):
            incoherences.append("ligne %d : ID invalide %r (attendu ANO-NNN)" % (i, aid))
        elif aid in vus:
            incoherences.append("ligne %d : ID dupliqué %r" % (i, aid))
        vus.add(aid)
        if not RE_CT.match(ct):
            incoherences.append("ligne %d : CT invalide %r (attendu CT-NNN)" % (i, ct))
        if sev not in SEVERITES:
            incoherences.append("ligne %d : sévérité inconnue %r (attendu %s)"
                                % (i, sev, "/".join(sorted(SEVERITES))))
        if repro not in REPRO:
            incoherences.append("ligne %d : reproductibilité inconnue %r (attendu %s)"
                                % (i, repro, "/".join(sorted(REPRO))))
        if trait not in TRAITEMENTS:
            incoherences.append("ligne %d : traitement inconnu %r (attendu %s)"
                                % (i, trait, "/".join(sorted(TRAITEMENTS))))
    n = len(lignes) - 1
    if incoherences:
        return 1, "anomalies : %d ; incohérences : %d\n%s" % (
            n, len(incoherences), "\n".join("  - " + x for x in incoherences))
    return 0, "anomalies : %d ; conforme" % n


def _auto_test():
    echecs = []
    rep = tempfile.mkdtemp()
    f = os.path.join(rep, "anomalies-demo.csv")
    try:
        with open(f, "w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh, delimiter=";")
            w.writerow(EN_TETE)
            w.writerow(["ANO-001", "CT-001", "bloquante", "systématique", "ouverte"])
            w.writerow(["ANO-002", "CT-003", "majeure", "intermittente", "assignée"])
        code, msg = controler(f)
        if code != 0:
            echecs.append(("2 anomalies valides -> code %d" % code, msg))
        with open(f, "w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh, delimiter=";")
            w.writerow(EN_TETE)
            w.writerow(["ANO-001", "CT-001", "bloquante", "systématique", "ouverte"])
            w.writerow(["ANO-001", "X", "grave", "?", "?"])
        code, msg = controler(f)
        if code != 1:
            echecs.append(("anomalie invalide/dupliquée -> code %d" % code, msg))
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
        print("Auto-test controler_anomalies.py : OK (format, ID unique, sévérité)")
        sys.exit(0)
    if len(sys.argv) != 2:
        print("Usage : python controler_anomalies.py <anomalies.csv>", file=sys.stderr)
        sys.exit(3)
    code, msg = controler(sys.argv[1])
    print(msg)
    sys.exit(code)
