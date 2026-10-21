"""RA-52 : limitation des tentatives de connexion.

Les échecs sont comptés sur une fenêtre glissante, par e-mail et par adresse IP.
Au-delà du seuil, la connexion est refusée (429) jusqu'à ce que le plus ancien
échec compté sorte de la fenêtre — même avec le bon mot de passe, sinon la
recherche du mot de passe continuerait. Une connexion réussie remet le compteur
de l'e-mail à zéro.
"""
import math
from datetime import timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from .config import parametres
from .models import TentativeConnexion, maintenant

CONSERVATION_JOURS = 30


def _echecs(db: Session, critere, depuis) -> list:
    """Horodatages des échecs depuis `depuis`, du plus ancien au plus récent."""
    return list(db.scalars(select(TentativeConnexion.horodatage).where(
        critere, TentativeConnexion.reussie.is_(False),
        TentativeConnexion.horodatage > depuis).order_by(TentativeConnexion.horodatage)))


def _depuis_email(db: Session, email: str, debut):
    """Les échecs antérieurs à la dernière connexion réussie ne comptent plus."""
    derniere_reussite = db.scalar(select(func.max(TentativeConnexion.horodatage)).where(
        TentativeConnexion.email == email, TentativeConnexion.reussie.is_(True)))
    return max(debut, derniere_reussite) if derniere_reussite else debut


def attente_minutes(db: Session, email: str, ip: str) -> int:
    """0 si la connexion peut être tentée, sinon les minutes à attendre."""
    p = parametres()
    fenetre = timedelta(minutes=p.connexion_fenetre_minutes)
    maint = maintenant()
    debut = maint - fenetre
    depuis_email = _depuis_email(db, email, debut)

    attente = timedelta(0)
    for critere, depuis, seuil in (
            (TentativeConnexion.email == email, depuis_email, p.connexion_essais_max),
            (TentativeConnexion.ip == ip, debut, p.connexion_essais_max_ip)):
        echecs = _echecs(db, critere, depuis)
        if len(echecs) >= seuil:
            # Le seuil reste atteint jusqu'à ce que l'échec de rang (n - seuil + 1)
            # sorte de la fenêtre : le compte retombe alors sous le seuil.
            attente = max(attente, echecs[len(echecs) - seuil] + fenetre - maint)
    if attente <= timedelta(0):
        return 0
    return max(1, math.ceil(attente.total_seconds() / 60))


def noter(db: Session, email: str, ip: str, reussie: bool) -> int:
    """Enregistre la tentative ; renvoie le nombre d'échecs de l'e-mail sur la
    fenêtre après celle-ci (0 si réussie). Purge les traces trop anciennes."""
    db.add(TentativeConnexion(email=email, ip=ip, reussie=reussie))
    db.execute(delete(TentativeConnexion).where(
        TentativeConnexion.horodatage < maintenant() - timedelta(days=CONSERVATION_JOURS)))
    db.flush()
    if reussie:
        return 0
    debut = maintenant() - timedelta(minutes=parametres().connexion_fenetre_minutes)
    return len(_echecs(db, TentativeConnexion.email == email, _depuis_email(db, email, debut)))
