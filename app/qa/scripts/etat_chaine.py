#!/usr/bin/env python3
"""Transitions de campagne (SFD §7.1) et route de la chaîne V1.

Deux niveaux :
- États de campagne (grossiers) : BROUILLON -> ... -> CLOTUREE (§7.1).
- Étapes de la chaîne V1 (fines) : AG-01 -> PV-1 -> AG-02 -> ... -> PV-2 -> AG-06,
  avec deux portes de validation humaine (PV-1, PV-2).

Auto-test : python etat_chaine.py (code 0 = OK).
"""

import sys

import statuts

TRANSITIONS_NOMINALES = {
    "BROUILLON": ["PREPAREE"],
    "PREPAREE": ["EN_COURS"],
    "EN_COURS": ["CONTROLES"],
    "CONTROLES": ["ATTENTE_VALIDATION"],
    "ATTENTE_VALIDATION": ["VALIDEE", "REJETEE"],
    "VALIDEE": ["CLOTUREE"],
    "REJETEE": ["CLOTUREE"],
    "CLOTUREE": [],
}

ETATS_EXCEPTION = ("BLOQUEE", "ECHEC", "ANNULEE", "INCOMPLETE")


def transition_valide(etat_courant, etat_cible):
    courant = statuts.normaliser_statut_campagne(etat_courant)
    cible = statuts.normaliser_statut_campagne(etat_cible)
    if courant == "CLOTUREE":
        return False
    if cible in ETATS_EXCEPTION:
        return True
    return cible in TRANSITIONS_NOMINALES.get(courant, [])


def prochains_etats(etat_courant):
    courant = statuts.normaliser_statut_campagne(etat_courant)
    if courant == "CLOTUREE":
        return []
    return list(TRANSITIONS_NOMINALES.get(courant, [])) + list(ETATS_EXCEPTION)


CHAINE_V1 = ["AG-01", "PV-1", "AG-02", "AG-03", "AG-04", "AG-05", "PV-2", "AG-06"]


def est_porte(etape):
    return etape.startswith("PV-")


def prochaine_etape(etape_courante):
    if etape_courante not in CHAINE_V1:
        raise ValueError("étape inconnue : %r" % etape_courante)
    i = CHAINE_V1.index(etape_courante)
    return CHAINE_V1[i + 1] if i + 1 < len(CHAINE_V1) else None


def avancer(etape_courante, porte_validee=False):
    if est_porte(etape_courante) and not porte_validee:
        raise ValueError("porte %s non validée par l'humain" % etape_courante)
    return prochaine_etape(etape_courante)


def _auto_test():
    echecs = []
    cas = [
        ("BROUILLON", "PREPAREE", True),
        ("BROUILLON", "EN_COURS", False),
        ("PREPAREE", "CONTROLES", False),
        ("ATTENTE_VALIDATION", "VALIDEE", True),
        ("ATTENTE_VALIDATION", "REJETEE", True),
        ("VALIDEE", "CLOTUREE", True),
        ("REJETEE", "CLOTUREE", True),
        ("CLOTUREE", "PREPAREE", False),
        ("EN_COURS", "BLOQUEE", True),
        ("EN_COURS", "INCOMPLETE", True),
        ("EN_COURS", "ANNULÉE", True),
    ]
    for courant, cible, attendu in cas:
        if transition_valide(courant, cible) != attendu:
            echecs.append((courant, cible, attendu))
    if prochaine_etape("AG-01") != "PV-1":
        echecs.append(("prochaine AG-01", prochaine_etape("AG-01")))
    if prochaine_etape("AG-06") is not None:
        echecs.append(("AG-06 terminal", prochaine_etape("AG-06")))
    if not (est_porte("PV-1") and est_porte("PV-2") and not est_porte("AG-01")):
        echecs.append(("est_porte", None))
    try:
        avancer("PV-1", False)
        echecs.append(("PV-1 non validée acceptée", None))
    except ValueError:
        pass
    if avancer("PV-1", True) != "AG-02":
        echecs.append(("PV-1 validée", avancer("PV-1", True)))
    return echecs


if __name__ == "__main__":
    echecs = _auto_test()
    if echecs:
        for e in echecs:
            print("ÉCHEC:", e)
        sys.exit(1)
    print("Auto-test etat_chaine.py : OK (11 cas campagne + 6 cas chaîne V1)")
    sys.exit(0)
