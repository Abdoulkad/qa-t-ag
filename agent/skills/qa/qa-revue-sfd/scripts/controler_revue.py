#!/usr/bin/env python3
"""Contrôle déterministe du rapport de revue SFD (AG-01).

Vérifie la structure, compte les DEF par gravité/catégorie, et contrôle que
chaque citation existe mot pour mot dans la SFD. Le décompte chiffré du
rapport vient d'ici, jamais du modèle.

Usage : python controler_revue.py <sfd> <rapport>
Codes : 0 = conforme, 1 = écarts (citations absentes), 2 = mal formé /
        entrée introuvable, 3 = défaut du script.
Auto-test : python controler_revue.py --selftest
"""

import os
import re
import sys
import tempfile

CATEGORIES = (
    "Ambiguïté", "Contradiction", "Cas oublié", "Exigence non testable",
    "Règle sans exigence", "Terme non défini",
    "Incohérence avec les user stories",
)
GRAVITES = ("Bloquante", "Majeure", "Mineure")
SECTIONS_REQUISES = (
    "## Alerte sécurité",
    "## Inventaire REQ et BR",
    "## Défauts",
    "## Statut du livrable",
)

RE_DEF = re.compile(r"^###\s+(DEF-\d+)\s*[-—–]\s*(.+?)\s*[-—–]\s*(.+?)\s*$")
RE_CITATION = re.compile(r"^\s*-\s*\*\*Citation\*\*\s*:\s*«\s*(.*?)\s*»\s*$")
RE_SECTION = re.compile(r"^\s*-\s*\*\*Section\*\*\s*:\s*(.*?)\s*$")
RE_STATUT = re.compile(r"^##\s+Statut du livrable\s*$", re.MULTILINE)

STATUTS = ("OK", "A_CLARIFIER", "EN_ATTENTE", "ERREUR", "BLOQUE")


def _lire(chemin):
    with open(chemin, "r", encoding="utf-8") as f:
        return f.read()


def parser_rapport(texte):
    """Retourne (defs, statut, erreurs)."""
    defs = []
    erreurs = []
    for s in SECTIONS_REQUISES:
        if s not in texte:
            erreurs.append("section manquante : %s" % s)
    m = RE_STATUT.search(texte)
    statut = None
    if m:
        suite = texte[m.end():].strip().splitlines()
        if suite:
            statut = suite[0].strip()
        if statut not in STATUTS:
            erreurs.append("statut du livrable invalide : %r" % statut)
    else:
        erreurs.append("section « Statut du livrable » introuvable")
    def_courant = None
    for ligne in texte.splitlines():
        m = RE_DEF.match(ligne)
        if m:
            if def_courant:
                defs.append(def_courant)
            def_courant = {
                "id": m.group(1),
                "categorie": m.group(2).strip(),
                "gravite": m.group(3).strip(),
                "citation": None,
                "section": None,
            }
            if def_courant["categorie"] not in CATEGORIES:
                erreurs.append("%s : catégorie inconnue %r" % (def_courant["id"], def_courant["categorie"]))
            if def_courant["gravite"] not in GRAVITES:
                erreurs.append("%s : gravité inconnue %r" % (def_courant["id"], def_courant["gravite"]))
            continue
        if def_courant:
            mc = RE_CITATION.match(ligne)
            if mc:
                def_courant["citation"] = mc.group(1)
            ms = RE_SECTION.match(ligne)
            if ms:
                def_courant["section"] = ms.group(1)
    if def_courant:
        defs.append(def_courant)
    for d in defs:
        if not d["citation"]:
            erreurs.append("%s : citation manquante" % d["id"])
    return defs, statut, erreurs


def verifier_citations(defs, sfd_texte):
    """Retourne la liste des DEF dont la citation est absente du SFD."""
    return [d["id"] for d in defs if d["citation"] and d["citation"] not in sfd_texte]


def compter(defs, cle):
    compte = {}
    for d in defs:
        compte[d[cle]] = compte.get(d[cle], 0) + 1
    return compte


def controler(sfd_path, rapport_path):
    """Retourne (code, message)."""
    if not os.path.isfile(sfd_path) or not os.path.isfile(rapport_path):
        return 2, "ERREUR (entrée inexploitable) : fichier introuvable"
    try:
        sfd = _lire(sfd_path)
        rapport = _lire(rapport_path)
    except Exception as e:
        return 3, "ERREUR (défaut du script) : %s" % e
    defs, statut, erreurs = parser_rapport(rapport)
    if erreurs:
        return 2, "ERREUR (rapport mal formé) :\n" + "\n".join(erreurs)
    absentes = verifier_citations(defs, sfd)
    lignes = [
        "DEF : %d" % len(defs),
        "par gravité : %s" % compter(defs, "gravite"),
        "par catégorie : %s" % compter(defs, "categorie"),
        "statut du livrable : %s" % statut,
    ]
    if absentes:
        lignes.append("Citations absentes du SFD : %s" % ", ".join(absentes))
        return 1, "\n".join(lignes)
    lignes.append("Citations : toutes présentes mot pour mot")
    return 0, "\n".join(lignes)


def _auto_test():
    sfd = "Le dossier est traité sous 5 jours ouvrés.\nLe montant maximal est 100 000.\n"
    rapport_ok = (
        "# Revue SFD — demo\n\n"
        "## Alerte sécurité\n\n"
        "## Inventaire REQ et BR\n- REQ-001 — traitement\n\n"
        "## Défauts\n"
        "### DEF-001 — Ambiguïté — Majeure\n"
        "- **Section** : 1\n"
        "- **Citation** : « Le dossier est traité sous 5 jours ouvrés. »\n"
        "- **Question** : à partir de quand ?\n\n"
        "## Statut du livrable\nOK\n"
    )
    rapport_citation_absente = rapport_ok.replace(
        "Le dossier est traité sous 5 jours ouvrés.",
        "Le dossier est traité sous 6 jours ouvrés.")
    echecs = []
    fd, fsfd = tempfile.mkstemp(suffix=".md")
    os.write(fd, sfd.encode("utf-8"))
    os.close(fd)
    fd, fr = tempfile.mkstemp(suffix=".md")
    os.close(fd)
    try:
        with open(fr, "w", encoding="utf-8") as f:
            f.write(rapport_ok)
        code, msg = controler(fsfd, fr)
        if code != 0:
            echecs.append(("rapport valide -> code %d" % code, msg))
        with open(fr, "w", encoding="utf-8") as f:
            f.write(rapport_citation_absente)
        code, msg = controler(fsfd, fr)
        if code != 1:
            echecs.append(("citation absente -> code %d" % code, msg))
        with open(fr, "w", encoding="utf-8") as f:
            f.write("# pas de sections\n")
        code, msg = controler(fsfd, fr)
        if code != 2:
            echecs.append(("rapport mal formé -> code %d" % code, msg))
    finally:
        for c in (fsfd, fr):
            if os.path.isfile(c):
                os.unlink(c)
    return echecs


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--selftest":
        e = _auto_test()
        if e:
            for x in e:
                print("ÉCHEC:", x)
            sys.exit(1)
        print("Auto-test controler_revue.py : OK (structure, comptage, citation)")
        sys.exit(0)
    if len(sys.argv) != 3:
        print("Usage : python controler_revue.py <sfd> <rapport>", file=sys.stderr)
        sys.exit(3)
    code, msg = controler(sys.argv[1], sys.argv[2])
    print(msg)
    sys.exit(code)
