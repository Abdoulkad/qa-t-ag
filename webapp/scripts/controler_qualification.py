#!/usr/bin/env python3
"""Contrôle déterministe de la qualification d'une anomalie de recette (AG-09).

L'agent propose un titre, une gravité, une reproductibilité et une
justification pour une anomalie ouverte par un cas en échec. Ce script vérifie
le format du contrat, les valeurs permises, la longueur du titre, l'absence de
données personnelles (adresses e-mail, numéros de téléphone) qui ne figuraient
pas déjà dans les faits fournis, et qu'une reproductibilité « Systématique » ou
« Intermittente » s'appuie sur au moins deux exécutions en échec.

Usage : python controler_qualification.py <qualification.md> [nb_echecs] [faits.txt]
Codes : 0 = conforme, 2 = mal formé, 3 = défaut du script.
Auto-test : python controler_qualification.py --selftest
"""

import re
import sys

GRAVITES = ("Bloquante", "Critique", "Majeure", "Mineure")
REPRODUCTIBILITES = ("Systématique", "Intermittente", "Non reproductible", "Non déterminée")
CHAMPS = ("Titre", "Gravité", "Reproductibilité", "Justification")
TITRE_MAX = 120

RE_CHAMP = re.compile(r"^\s*[-*]\s*\*\*(.+?)\*\*\s*:\s*(.*)$")
RE_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
RE_TELEPHONE = re.compile(r"(?<!\d)(?:\+?\d[\s.-]?){8,}\d(?!\d)")


def _normaliser(valeur: str) -> str:
    return valeur.strip().strip("«»\"' ").rstrip(".").strip()


def parser(texte: str, nb_echecs: int = 1, faits: str = ""):
    """Retourne (qualification, erreurs). qualification = {titre, gravite,
    reproductibilite, justification} ; erreurs vide = conforme."""
    erreurs = []
    if "## Anomalie" not in texte:
        erreurs.append("section « ## Anomalie » absente")
    champs, courant = {}, None
    for ligne in texte.splitlines():
        m = RE_CHAMP.match(ligne)
        if m:
            nom = m.group(1).strip().rstrip(":").strip()
            courant = nom
            if nom in champs:
                erreurs.append("champ « %s » en double" % nom)
            champs[nom] = m.group(2).strip()
        elif courant == "Justification" and ligne.strip() and not ligne.startswith("#"):
            champs["Justification"] += " " + ligne.strip()   # justification sur plusieurs lignes
    for nom in CHAMPS:
        if not champs.get(nom, "").strip():
            erreurs.append("champ « %s » absent ou vide" % nom)
    inconnus = sorted(set(champs) - set(CHAMPS))
    if inconnus:
        erreurs.append("champ(s) inconnu(s) : %s" % ", ".join(inconnus))
    if erreurs:
        return None, erreurs

    titre = champs["Titre"].strip().strip("«»\"").strip()
    gravite = _normaliser(champs["Gravité"])
    repro = _normaliser(champs["Reproductibilité"])
    justification = " ".join(champs["Justification"].split())
    if len(titre) > TITRE_MAX:
        erreurs.append("titre trop long (%d caractères, %d au plus)" % (len(titre), TITRE_MAX))
    if gravite not in GRAVITES:
        erreurs.append("gravité « %s » non permise (valeurs : %s)" % (gravite, ", ".join(GRAVITES)))
    if repro not in REPRODUCTIBILITES:
        erreurs.append("reproductibilité « %s » non permise (valeurs : %s)"
                       % (repro, ", ".join(REPRODUCTIBILITES)))
    elif repro in ("Systématique", "Intermittente") and nb_echecs < 2:
        erreurs.append("reproductibilité « %s » avec une seule exécution en échec : "
                       "écris « Non déterminée »" % repro)
    for zone, valeur in (("titre", titre), ("justification", justification)):
        for motif, nature in ((RE_EMAIL, "adresse e-mail"), (RE_TELEPHONE, "numéro de téléphone")):
            for trouve in motif.findall(valeur):
                if trouve not in faits:
                    erreurs.append("donnée personnelle (%s) dans le %s : retire-la" % (nature, zone))
    if erreurs:
        return None, erreurs
    return {"titre": titre, "gravite": gravite, "reproductibilite": repro,
            "justification": justification}, []


def _auto_test() -> int:
    bon = ("## Anomalie\n- **Titre** : Le lien de réinitialisation reste valide après 24 h\n"
           "- **Gravité** : Critique\n- **Reproductibilité** : Non déterminée\n"
           "- **Justification** : Le résultat obtenu contredit la règle RG-01.\n"
           "Une seule exécution est disponible.\n")
    q, e = parser(bon)
    assert not e and q["gravite"] == "Critique" and "seule exécution" in q["justification"], e
    assert parser(bon.replace("Critique", "Grave"))[1]
    assert parser(bon.replace("Non déterminée", "Systématique"))[1]
    assert not parser(bon.replace("Non déterminée", "Systématique"), nb_echecs=2)[1]
    assert parser(bon.replace("Critique.", "Critique"))[0] is not None
    assert parser(bon.replace("## Anomalie\n", ""))[1]
    assert parser(bon.replace("RG-01.", "RG-01, voir jean.dupont@exemple.ci."))[1]
    assert not parser(bon.replace("RG-01.", "RG-01 (a@b.ci)."), faits="a@b.ci")[1]
    assert parser(bon.replace("Le lien", "x" * 130))[1]
    assert parser(bon + "- **Priorité** : Haute\n")[1]
    print("auto-test OK")
    return 0


def main(argv) -> int:
    if len(argv) == 2 and argv[1] == "--selftest":
        return _auto_test()
    if len(argv) not in (2, 3, 4):
        print(__doc__)
        return 2
    try:
        texte = open(argv[1], encoding="utf-8").read()
        nb = int(argv[2]) if len(argv) > 2 else 1
        faits = open(argv[3], encoding="utf-8").read() if len(argv) > 3 else ""
    except (OSError, ValueError) as e:
        print("entrée inexploitable : %s" % e)
        return 2
    try:
        q, erreurs = parser(texte, nb, faits)
    except Exception as e:  # noqa: BLE001
        print("défaut du script : %s" % e)
        return 3
    if erreurs:
        print("\n".join(erreurs))
        return 2
    print("%s · %s · %s" % (q["gravite"], q["reproductibilite"], q["titre"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
