#!/usr/bin/env python3
"""Normalisation déterministe des statuts QA-T-AG.

SFD V2.0 — §6.2 (livrable d'agent), §7.1 (campagne), §9.1 (résultat de test).
Autorité unique sur les statuts : résout DEF-001 (vocabulaire non normalisé).

Le modèle n'écrit jamais un statut de sa propre initiative : il appelle
`normaliser_statut_*` et reporte la valeur canonique renvoyée.

Auto-test : `python statuts.py` (code de sortie 0 = OK, 1 = échec).
"""

import sys
import unicodedata

# --- Valeurs canoniques (référence) ---------------------------------------
STATUT_AGENT = ("OK", "A_CLARIFIER", "EN_ATTENTE", "ERREUR", "BLOQUE")
STATUT_TEST = ("PASS", "FAIL", "BLOCKED", "NOT_RUN", "NON_CONCLUANT")
STATUT_CAMPAGNE = (
    "BROUILLON", "PREPAREE", "EN_COURS", "CONTROLES",
    "ATTENTE_VALIDATION", "VALIDEE", "REJETEE", "CLOTUREE",
)
STATUT_CAMPAGNE_EXCEPTION = ("BLOQUEE", "ECHEC", "ANNULEE", "INCOMPLETE")

# --- Alias historiques -> canonique (par domaine, car « BLOQUÉ » est ambigu)
ALIAS_AGENT = {
    "A_CLARIFIER": "A_CLARIFIER", "A CLARIFIER": "A_CLARIFIER",
    "A-CLARIFIER": "A_CLARIFIER",
    "EN_ATTENTE": "EN_ATTENTE", "EN ATTENTE": "EN_ATTENTE",
    "EN-ATTENTE": "EN_ATTENTE",
    "BLOQUE": "BLOQUE", "BLOQUEE": "BLOQUE",
    "ERREUR": "ERREUR",
    "OK": "OK",
}

ALIAS_TEST = {
    "PASS": "PASS", "PASSE": "PASS",
    "FAIL": "FAIL", "ECHEC": "FAIL",
    "BLOCKED": "BLOCKED", "BLOQUE": "BLOCKED", "BLOQUEE": "BLOCKED",
    "NOT_RUN": "NOT_RUN", "NOT RUN": "NOT_RUN",
    "NON_EXECUTE": "NOT_RUN", "NON EXECUTE": "NOT_RUN",
    "NON_CONCLUANT": "NON_CONCLUANT", "NON CONCLUANT": "NON_CONCLUANT",
    "NON-CONCLUANT": "NON_CONCLUANT", "INCONCLUSIF": "NON_CONCLUANT",
    "INCONCLUSIVE": "NON_CONCLUANT",
}

ALIAS_CAMPAGNE = {
    "BROUILLON": "BROUILLON",
    "PREPAREE": "PREPAREE", "PREPARE": "PREPAREE",
    "EN_COURS": "EN_COURS", "EN COURS": "EN_COURS",
    "CONTROLES": "CONTROLES",
    "ATTENTE_VALIDATION": "ATTENTE_VALIDATION",
    "VALIDEE": "VALIDEE", "VALIDE": "VALIDEE",
    "REJETEE": "REJETEE", "REJETE": "REJETEE",
    "CLOTUREE": "CLOTUREE", "CLOTURE": "CLOTUREE",
    # exceptions
    "BLOQUEE": "BLOQUEE", "BLOQUE": "BLOQUEE",
    "ECHEC": "ECHEC",
    "ANNULEE": "ANNULEE", "ANNULE": "ANNULEE",
    "INCOMPLETE": "INCOMPLETE", "INCOMPLET": "INCOMPLETE",
}


def _normaliser_libelle(s):
    """Supprime les accents, passe en majuscules, normalise séparateurs en '_'."""
    if s is None:
        return ""
    s = str(s).strip()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.upper()
    for sep in (" ", "-", "\u00A0"):
        s = s.replace(sep, "_")
    while "__" in s:
        s = s.replace("__", "_")
    return s.strip("_")


def _normaliser(s, table, domaine):
    key = _normaliser_libelle(s)
    if key in table:
        return table[key]
    raise ValueError(
        "Statut %r non reconnu dans le domaine %s. "
        "Valeurs acceptées : %s" % (s, domaine, ", ".join(sorted(set(table.values()))))
    )


def normaliser_statut_agent(s):
    return _normaliser(s, ALIAS_AGENT, "agent")


def normaliser_statut_test(s):
    return _normaliser(s, ALIAS_TEST, "test")


def normaliser_statut_campagne(s):
    return _normaliser(s, ALIAS_CAMPAGNE, "campagne")


# --- Auto-test --------------------------------------------------------------
def _auto_test():
    cas_agent = [
        ("OK", "OK"), ("À_CLARIFIER", "A_CLARIFIER"), ("A clarifier", "A_CLARIFIER"),
        ("EN_ATTENTE", "EN_ATTENTE"), ("En attente", "EN_ATTENTE"),
        ("BLOQUÉ", "BLOQUE"), ("BLOQUE", "BLOQUE"), ("ERREUR", "ERREUR"),
    ]
    cas_test = [
        ("PASS", "PASS"), ("FAIL", "FAIL"), ("Échec", "FAIL"),
        ("BLOCKED", "BLOCKED"), ("BLOQUÉ", "BLOCKED"),
        ("NOT_RUN", "NOT_RUN"), ("NON EXÉCUTÉ", "NOT_RUN"),
        ("NON_CONCLUANT", "NON_CONCLUANT"), ("INCONCLUSIF", "NON_CONCLUANT"),
        ("Inconclusive", "NON_CONCLUANT"),
    ]
    cas_campagne = [
        ("BROUILLON", "BROUILLON"), ("PRÉPARÉE", "PREPAREE"),
        ("EN_COURS", "EN_COURS"), ("CONTRÔLES", "CONTROLES"),
        ("VALIDÉE", "VALIDEE"), ("CLÔTURÉE", "CLOTUREE"),
        ("BLOQUÉE", "BLOQUEE"), ("ÉCHEC", "ECHEC"),
        ("INCOMPLET", "INCOMPLETE"),
    ]
    echecs = []
    for entree, attendu in cas_agent:
        r = normaliser_statut_agent(entree)
        if r != attendu:
            echecs.append(("agent", entree, attendu, r))
    for entree, attendu in cas_test:
        r = normaliser_statut_test(entree)
        if r != attendu:
            echecs.append(("test", entree, attendu, r))
    for entree, attendu in cas_campagne:
        r = normaliser_statut_campagne(entree)
        if r != attendu:
            echecs.append(("campagne", entree, attendu, r))
    # un statut inconnu doit lever ValueError (jamais deviné)
    try:
        normaliser_statut_agent("N_IMPORTE_QUOI")
        echecs.append(("agent", "N_IMPORTE_QUOI", "ValueError", "aucune erreur"))
    except ValueError:
        pass
    return echecs


if __name__ == "__main__":
    echecs = _auto_test()
    if echecs:
        for e in echecs:
            print("ÉCHEC:", e)
        print("%d échec(s)" % len(echecs))
        sys.exit(1)
    print("Auto-test statuts.py : OK (27 cas)")
    sys.exit(0)
