"""Règles métier pures (sans base), testables isolément.

Le serveur les applique ; l'interface ne fait que les refléter.
"""
import re as _re
from dataclasses import dataclass

# RA-11 — transitions autorisées du statut de mission
TRANSITIONS = {
    "ANALYSE_EN_COURS": ("CLARIFICATION", "ECHEC_ANALYSE"),
    "ECHEC_ANALYSE": ("ANALYSE_EN_COURS",),
    "CLARIFICATION": ("REECRITURE",),
    "REECRITURE": ("ATTENTE_PV1", "CLARIFICATION"),     # échec IA -> retour
    "ATTENTE_PV1": ("CONCEPTION", "A_CORRIGER", "REECRITURE"),  # relancer
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


# --- RA-23, RA-24 : statut d'un cas de test, calculé (jamais choisi par l'IA) ---

_RE_GABARIT = _re.compile(
    r"\{[^}]+\}|\b(TBD|TODO|XXX+|N/?A)\b|à (définir|préciser|compléter)|"
    r"a (definir|preciser|completer)|non (défini|precise|précisé)", _re.IGNORECASE)
# Données « génériques » : décrivent une classe, pas une valeur concrète
_GENERIQUES = {
    "valide", "valides", "invalide", "invalides", "données valides", "données invalides",
    "donnees valides", "donnees invalides", "identifiants valides", "identifiants invalides",
    "valeur valide", "valeur invalide", "-", "—", "aucune", "néant", "neant",
}
# Description d'une classe de valeurs (« mot de passe valide », « un e-mail
# existant ») sans aucune valeur précise : ni chiffre, ni guillemet, ni @, ni =.
_RE_DESCRIPTION_GENERIQUE = _re.compile(
    r"\b(valides?|invalides?|correcte?s?|incorrecte?s?|existante?s?|inexistante?s?|"
    r"quelconques?|aléatoires?|aleatoires?|conformes?|non conformes?)\b", _re.IGNORECASE)
_RE_VALEUR_PRECISE = _re.compile(r"[0-9@=«»\"':/]")
SANS_OBJET = "sans objet"


def donnees_concretes(donnees: str) -> bool:
    d = (donnees or "").strip()
    if not d:
        return False
    if d.lower() == SANS_OBJET:
        return True
    if d.lower().strip(" .") in _GENERIQUES or _RE_GABARIT.search(d):
        return False
    if _RE_DESCRIPTION_GENERIQUE.search(d) and not _RE_VALEUR_PRECISE.search(d):
        return False
    return True


def statut_cas(preconditions: str, donnees_test: str, resultat_attendu: str,
               statut_ia: str, confirme_par_humain: bool = False) -> tuple[str, str]:
    """Retourne (statut, motif). PRET exige des préconditions, des données
    concrètes et un résultat attendu ; « Sans objet » est accepté pour des
    données quand le cas n'en demande pas."""
    manques = []
    if not (preconditions or "").strip():
        manques.append("préconditions absentes")
    donnees = (donnees_test or "").strip()
    if not donnees:
        manques.append("données de test absentes")
    elif not donnees_concretes(donnees):
        manques.append("données de test non concrètes (%s)" % donnees[:60])
    resultat = (resultat_attendu or "").strip()
    if not resultat:
        manques.append("résultat attendu absent")
    elif _RE_GABARIT.search(resultat):
        manques.append("résultat attendu incomplet")
    if manques:
        return "INCOMPLET", "; ".join(manques)
    if statut_ia == "A_CLARIFIER" and not confirme_par_humain:
        return "A_CLARIFIER", "signalé à clarifier par l'agent de conception"
    return "PRET", ""
