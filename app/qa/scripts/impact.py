#!/usr/bin/env python3
"""Calcul d'impact pour la sélection de régression (AG-10).

Étant donnés la matrice de traçabilité (AG-03) et la note de livraison
(exigences touchées), produit la sélection des CT à rejouer. Chaque CT
sélectionné porte sa raison (exigence touchée).

Usage : python impact.py <matrice.csv> <note-livraison.csv> <selection.csv>
Codes : 0 = sélection produite (toutes les exigences touchées résolues),
        1 = des exigences touchées absentes de la matrice (écart),
        2 = entrée inexploitable, 3 = défaut.
Auto-test : python impact.py --selftest
"""

import csv
import os
import re
import shutil
import sys
import tempfile

EN_TETE_MATRICE = ["Exigence", "CTs"]
EN_TETE_NOTE = ["Exigence"]
RE_EXIGENCE = re.compile(r"\b(REQ|BR)-\d+\b")
RE_CT = re.compile(r"^CT-\d{3}$")


def _lire_csv(chemin, attendu):
    with open(chemin, "r", encoding="utf-8-sig") as f:
        lignes = list(csv.reader(f, delimiter=";"))
    if not lignes or lignes[0] != attendu:
        raise ValueError("en-tête non conforme : %s" % (lignes[0] if lignes else "(vide)"))
    return lignes[1:]


def _lire_matrice(chemin):
    matrice = {}
    for l in _lire_csv(chemin, EN_TETE_MATRICE):
        if not l or not l[0].strip():
            continue
        ex = l[0].strip()
        cts = [c.strip() for c in l[1].split(",") if c.strip()] if len(l) > 1 else []
        matrice[ex] = cts
    return matrice


def _lire_note(chemin):
    touches = []
    for l in _lire_csv(chemin, EN_TETE_NOTE):
        if l and l[0].strip():
            for m in RE_EXIGENCE.finditer(l[0]):
                if m.group(0) not in touches:
                    touches.append(m.group(0))
    return touches


def impact(matrice_path, note_path, selection_path):
    for p in (matrice_path, note_path):
        if not os.path.isfile(p):
            return 2, "fichier introuvable : %s" % p
    try:
        matrice = _lire_matrice(matrice_path)
        touches = _lire_note(note_path)
    except ValueError as e:
        return 2, str(e)
    except Exception as e:
        return 3, "défaut du script : %s" % e

    selection = []
    absentes = []
    for ex in touches:
        if ex not in matrice:
            absentes.append(ex)
            continue
        for ct in matrice[ex]:
            if not RE_CT.match(ct):
                return 2, "CT invalide dans la matrice : %r" % ct
            selection.append((ct, ex))

    vus = set()
    sel_final = []
    for ct, ex in selection:
        if ct not in vus:
            vus.add(ct)
            sel_final.append((ct, ex))

    with open(selection_path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["CT", "Raison"])
        w.writerows(sel_final)

    lignes = ["CT sélectionnés : %d" % len(sel_final)]
    if absentes:
        lignes.append("Exigences touchées absentes de la matrice : %s" % ", ".join(absentes))
        return 1, "\n".join(lignes)
    return 0, "\n".join(lignes)


def _auto_test():
    echecs = []
    rep = tempfile.mkdtemp()
    fm = os.path.join(rep, "matrice-demo.csv")
    fn = os.path.join(rep, "note-demo.csv")
    fs = os.path.join(rep, "selection-demo.csv")
    try:
        with open(fm, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(EN_TETE_MATRICE)
            w.writerow(["REQ-001", "CT-001,CT-002"])
            w.writerow(["REQ-002", "CT-003"])
        with open(fn, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(EN_TETE_NOTE)
            w.writerow(["REQ-001"])
        code, msg = impact(fm, fn, fs)
        if code != 0:
            echecs.append(("impact REQ-001 -> code %d" % code, msg))
        with open(fs, "r", encoding="utf-8") as f:
            sel = list(csv.reader(f, delimiter=";"))[1:]
        if [s[0] for s in sel] != ["CT-001", "CT-002"]:
            echecs.append(("sélection attendue CT-001,CT-002", [s[0] for s in sel]))
        with open(fn, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(EN_TETE_NOTE)
            w.writerow(["REQ-999"])
        code, msg = impact(fm, fn, fs)
        if code != 1:
            echecs.append(("exigence absente -> code %d" % code, msg))
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
        print("Auto-test impact.py : OK (sélection, raison, exigence absente)")
        sys.exit(0)
    if len(sys.argv) != 4:
        print("Usage : python impact.py <matrice.csv> <note-livraison.csv> <selection.csv>",
              file=sys.stderr)
        sys.exit(3)
    code, msg = impact(sys.argv[1], sys.argv[2], sys.argv[3])
    print(msg)
    sys.exit(code)
