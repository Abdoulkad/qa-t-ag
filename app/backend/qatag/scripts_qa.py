"""Pont vers les scripts déterministes existants (webapp/scripts).

Les scripts restent l'autorité : on les importe tels quels, sans les
réécrire. « Le script calcule · l'agent analyse · l'humain arbitre. »
"""
import importlib
import os
import re
import sys
import tempfile

from .config import parametres

RE_QUESTION = re.compile(r"^\s*-\s*\*\*Question\*\*\s*:\s*(.+?)\s*$")


def _module(nom):
    dossier = str(parametres().dossier_scripts)
    if dossier not in sys.path:
        sys.path.insert(0, dossier)
    return importlib.import_module(nom)


def empreinte_texte(texte: str) -> str:
    """RA-08 : SHA-256 calculé par empreinte.py sur le texte encodé en UTF-8."""
    empreinte = _module("empreinte")
    fd, chemin = tempfile.mkstemp(suffix=".txt")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(texte.encode("utf-8"))
        return empreinte.empreinte_fichier(chemin)
    finally:
        os.remove(chemin)


def analyser_rapport_revue(rapport: str, texte_sfd: str) -> dict:
    """Contrôle le rapport AG-01 avec controler_revue.py et en extrait les défauts.

    Retourne {"code", "erreurs", "statut", "defauts": [...]}. Code 0 = conforme,
    1 = citations absentes du texte, 2 = rapport mal formé.
    """
    cr = _module("controler_revue")
    defs, statut, erreurs = cr.parser_rapport(rapport)
    if erreurs:
        return {"code": 2, "erreurs": erreurs, "statut": statut, "defauts": []}
    absentes = set(cr.verifier_citations(defs, texte_sfd))

    # Le script ne lit pas les questions : on les rattache à leur DEF ici.
    questions, courant = {}, None
    for ligne in rapport.splitlines():
        m = cr.RE_DEF.match(ligne)
        if m:
            courant = m.group(1)
            continue
        mq = RE_QUESTION.match(ligne)
        if mq and courant:
            questions[courant] = mq.group(1)

    defauts = [{
        "code": d["id"], "categorie": d["categorie"], "gravite": d["gravite"],
        "section": d["section"], "citation": d["citation"],
        "citation_verifiee": d["id"] not in absentes,
        "question": questions.get(d["id"]),
    } for d in defs]
    return {"code": 1 if absentes else 0,
            "erreurs": ["Citation absente du texte : %s" % c for c in sorted(absentes)],
            "statut": statut, "defauts": defauts}
