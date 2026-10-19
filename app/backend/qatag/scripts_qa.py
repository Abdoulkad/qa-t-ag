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
    rapport, corrections = normaliser_rapport_revue(rapport)
    defs, statut, erreurs = cr.parser_rapport(rapport)
    if erreurs:
        return {"code": 2, "erreurs": erreurs, "corrections": corrections, "statut": statut,
                "defauts": []}
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
            "corrections": corrections, "statut": statut, "defauts": defauts}


def normaliser_rapport_revue(rapport: str) -> tuple[str, list[str]]:
    """Ajoute les sections dont l'absence ne change pas le fond du rapport.

    - « ## Alerte sécurité » : sans alerte, l'IA omet souvent la section ;
      on l'ajoute vide (« Aucune »).
    - « ## Statut du livrable » manquant : on ajoute A_CLARIFIER, le statut
      le plus prudent (repris de l'ancienne app Streamlit).
    Les sections de fond (Inventaire, Défauts) ne sont jamais inventées :
    leur absence reste une erreur. Chaque ajout est tracé.
    """
    corrections = []
    if "## Alerte sécurité" not in rapport:
        ancre = rapport.find("## Inventaire REQ et BR")
        bloc = "## Alerte sécurité\nAucune\n\n"
        rapport = rapport[:ancre] + bloc + rapport[ancre:] if ancre >= 0 else bloc + rapport
        corrections.append("section « Alerte sécurité » absente : ajoutée vide")
    if not re.search(r"^##\s+Statut du livrable\s*$", rapport, re.MULTILINE):
        rapport = rapport.rstrip() + "\n\n## Statut du livrable\nA_CLARIFIER\n"
        corrections.append("statut du livrable absent : A_CLARIFIER ajouté")
    return rapport, corrections


def verifier_reecriture(origine: str, rapport: str, questions_repondues: list[str]) -> dict:
    """RA-19, RA-20 : verifier_reecriture.py tranche SOURCE / HYPOTHESE."""
    vr = _module("verifier_reecriture")
    code, texte, criteres, erreurs = vr.verifier(origine, rapport, questions_repondues)
    return {"code": code, "texte": texte, "criteres": criteres, "erreurs": erreurs,
            "points": vr.extraire_points_ouverts(rapport) if code != 2 else []}


EN_TETE_CAS = ["ID", "Titre", "Objectif", "Exigence", "Technique", "Priorité", "Type",
               "Préconditions", "Données de test", "Étapes", "Résultat attendu",
               "Statut livrable"]
RE_REFERENCE = re.compile(r"\b(?:REQ|BR|CA)-\d+\b")
RE_JUSTIF = re.compile(r"^\s*(CT-\d{3})\s*:\s*(.+?)\s*$")


def separer_conception(sortie_ia: str) -> tuple[str, dict[str, str]]:
    """Sépare le CSV des cas et le bloc « ## Justifications » (CT-nnn : …)."""
    lignes = sortie_ia.splitlines()
    debut = next((i for i, l in enumerate(lignes)
                  if l.strip().startswith("ID;Titre;Objectif;Exigence;Technique")), None)
    if debut is None:
        return "", {}
    csv_lignes, justifs, dans_justifs = [], {}, False
    for l in lignes[debut:]:
        s = l.strip()
        if s.startswith("```"):
            continue
        if s.lower().startswith("## justification"):
            dans_justifs = True
            continue
        if dans_justifs:
            m = RE_JUSTIF.match(s)
            if m:
                justifs[m.group(1)] = m.group(2)
        elif s:
            csv_lignes.append(s)
    return "\n".join(csv_lignes) + "\n", justifs


def controler_cas(texte_reference: str, csv_texte: str) -> dict:
    """Contrôle de format par controler_cas.py, puis lecture des lignes.

    Retourne {"code", "message", "lignes"} ; code 2 = format inexploitable.
    """
    import csv
    import io
    cc = _module("controler_cas")
    with tempfile.TemporaryDirectory() as d:
        sfd = os.path.join(d, "reference.md")
        cas = os.path.join(d, "cas-mission.csv")
        with open(sfd, "w", encoding="utf-8") as f:
            f.write(texte_reference)
        with open(cas, "w", encoding="utf-8") as f:
            f.write(csv_texte)
        code, message = cc.controler(sfd, cas)
    lignes = list(csv.reader(io.StringIO(csv_texte), delimiter=";"))
    lignes = [l for l in lignes[1:] if len(l) == 12] if lignes and lignes[0] == EN_TETE_CAS else []
    return {"code": code, "message": message, "lignes": lignes}


def references(exigence: str) -> list[str]:
    vus = []
    for m in RE_REFERENCE.finditer(exigence or ""):
        if m.group(0) not in vus:
            vus.append(m.group(0))
    return vus


_TECHNIQUES = {
    "partitions d'équivalence": "partitions d'équivalence",
    "partitions d'equivalence": "partitions d'équivalence",
    "partition d'équivalence": "partitions d'équivalence",
    "valeurs limites": "valeurs limites", "valeur limite": "valeurs limites",
    "analyse des valeurs limites": "valeurs limites",
    "table de décision": "table de décision", "table de decision": "table de décision",
    "tables de décision": "table de décision",
    "transitions d'état": "transitions d'état", "transitions d'etat": "transitions d'état",
    "transition d'état": "transitions d'état",
}


def normaliser_csv(csv_texte: str) -> str:
    """Normalise les variantes d'écriture de la technique (repris de l'app
    Streamlit) ; le reste est laissé tel quel pour que le contrôle tranche."""
    sortie = []
    for i, ligne in enumerate(csv_texte.splitlines()):
        parts = ligne.split(";")
        if i > 0 and len(parts) == 12:
            parts[4] = _TECHNIQUES.get(parts[4].strip().lower(), parts[4].strip())
        sortie.append(";".join(parts))
    return "\n".join(sortie) + "\n"


def statut_agent(valeur: str) -> str:
    """Statut livrable écrit par l'IA, normalisé par statuts.py (inconnu -> A_CLARIFIER)."""
    st = _module("statuts")
    try:
        return st.normaliser_statut_agent(valeur)
    except ValueError:
        return "A_CLARIFIER"
