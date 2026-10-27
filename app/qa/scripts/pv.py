#!/usr/bin/env python3
"""Contrôle des portes de validation (PV) — SFD §AG-07.

Lit pv<n>-<projet>.md et détermine son statut. L'orchestrateur ne franchit une
porte que si ce script répond VALIDÉ.

Usage : python pv.py <pv1-<projet>.md>
Codes : 0 = VALIDÉ, 1 = EN_ATTENTE/REJETÉ/ILLISIBLE, 2 = fichier absent, 3 = défaut.
Auto-test : python pv.py --selftest
"""

import os
import re
import sys
import tempfile
import unicodedata

RE_STATUT = re.compile(r"\*\*Statut\s*:\*\*\s*`?([A-Za-zÀ-ÿ_]+)`?", re.IGNORECASE)


def _normaliser(statut):
    s = unicodedata.normalize("NFKD", statut)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.upper().replace(" ", "_")


def lire_statut(chemin):
    if not os.path.isfile(chemin):
        return "ABSENT"
    try:
        with open(chemin, "r", encoding="utf-8") as f:
            texte = f.read()
    except Exception:
        return "ILLISIBLE"
    m = RE_STATUT.search(texte)
    return _normaliser(m.group(1)) if m else "ILLISIBLE"


def porte_validee(chemin):
    return lire_statut(chemin) == "VALIDE"


def _auto_test():
    echecs = []
    rep = tempfile.mkdtemp()
    try:
        p = os.path.join(rep, "pv1-demo.md")
        for statut, attendu in [("VALIDÉ", True), ("EN_ATTENTE", False), ("REJETÉ", False)]:
            with open(p, "w", encoding="utf-8") as f:
                f.write("# PV-1\n\n**Statut :** `%s`\n" % statut)
            if porte_validee(p) != attendu:
                echecs.append((statut, lire_statut(p)))
        if porte_validee(os.path.join(rep, "pv2-absent.md")):
            echecs.append(("absent pris pour VALIDÉ", None))
    finally:
        import shutil
        shutil.rmtree(rep, ignore_errors=True)
    return echecs


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--selftest":
        e = _auto_test()
        if e:
            for x in e:
                print("ÉCHEC:", x)
            sys.exit(1)
        print("Auto-test pv.py : OK (VALIDÉ/EN_ATTENTE/REJETÉ/absent)")
        sys.exit(0)
    if len(sys.argv) != 2:
        print("Usage : python pv.py <pv1-<projet>.md>", file=sys.stderr)
        sys.exit(3)
    statut = lire_statut(sys.argv[1])
    print("Statut PV :", statut)
    sys.exit(0 if statut == "VALIDE" else (2 if statut == "ABSENT" else 1))
