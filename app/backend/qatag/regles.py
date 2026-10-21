"""Règles métier pures (sans base), testables isolément.

Le serveur les applique ; l'interface ne fait que les refléter.
"""
from dataclasses import dataclass

# RA-11 — transitions autorisées du statut de mission
TRANSITIONS = {
    "ANALYSE_EN_COURS": ("CLARIFICATION", "ECHEC_ANALYSE"),
    "ECHEC_ANALYSE": ("ANALYSE_EN_COURS",),
    "CLARIFICATION": ("REECRITURE",),
    "REECRITURE": ("ATTENTE_PV1",),
    "ATTENTE_PV1": ("CONCEPTION", "A_CORRIGER"),
    "CONCEPTION": ("ATTENTE_PV2",),
    "ATTENTE_PV2": ("VALIDEE", "A_CORRIGER"),
    "VALIDEE": ("EN_RECETTE",),
    "EN_RECETTE": ("CLOTUREE",),
    "A_CORRIGER": ("ANALYSE_EN_COURS",),
    "CLOTUREE": (),
}

# Porte -> (statut d'attente, statut si approuvée)
PORTES = {
    "PV-1": ("ATTENTE_PV1", "CONCEPTION"),
    "PV-2": ("ATTENTE_PV2", "VALIDEE"),
}

# Libellés d'affichage des statuts de test (codes canoniques de statuts.py)
LIBELLES_TEST = {"PASS": "Succès", "FAIL": "Échec", "BLOCKED": "Non testable",
                 "NOT_RUN": "Non exécuté"}


class RegleViolee(Exception):
    """Action refusée par une règle ; `regle` = identifiant RA-xx."""

    def __init__(self, regle: str, message: str, details=None):
        super().__init__(message)
        self.regle = regle
        self.message = message
        self.details = details or []


def verifier_transition(courant: str, cible: str) -> None:
    if cible not in TRANSITIONS.get(courant, ()):
        raise RegleViolee("RA-11", "Transition interdite : %s → %s" % (courant, cible))


@dataclass
class Habilitation:
    autorise: bool
    auto_validation: bool = False
    regle: str = ""
    raison: str = ""


def habilitation_porte(decideur_id: int, roles_decideur: list[str],
                       participants_ids: list[int], auteur_version_id: int) -> Habilitation:
    """RA-12, RA-13, RA-14 : qui peut décider à un Human Gate."""
    participants = set(participants_ids)
    if len(participants) == 1 and decideur_id in participants:
        return Habilitation(True, auto_validation=True)
    if "SUPERVISEUR" not in roles_decideur:
        return Habilitation(False, regle="RA-12",
                            raison="Le rôle Superviseur est requis pour décider à un "
                                   "Human Gate quand la mission a plusieurs participants.")
    if decideur_id == auteur_version_id:
        return Habilitation(False, regle="RA-13",
                            raison="L'auteur de la version ne peut pas valider son propre "
                                   "travail quand la mission a plusieurs participants.")
    return Habilitation(True)


GRAVITE_POIDS = {"Bloquante": 25, "Majeure": 10, "Mineure": 3}


def score_clarte(gravites: list[str]) -> int:
    """RA-17 : 100 − 25×bloquants − 10×majeurs − 3×mineurs, borné à [0, 100]."""
    score = 100 - sum(GRAVITE_POIDS.get(g, 0) for g in gravites)
    return max(0, min(100, score))


def statuts_test_autorises(resultat_attendu: str) -> tuple[str, ...]:
    """RA-28 : sans résultat attendu, seuls BLOCKED et NOT_RUN sont permis."""
    if (resultat_attendu or "").strip():
        return ("PASS", "FAIL", "BLOCKED", "NOT_RUN")
    return ("BLOCKED", "NOT_RUN")
