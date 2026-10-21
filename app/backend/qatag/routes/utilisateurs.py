from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import journal
from ..db import session_db
from ..deps import administrateur
from ..models import ROLES, Utilisateur
from ..securite import hacher
from .schemas import ChangementActif, ChangementRoles, CreationUtilisateur, UtilisateurSortie

routeur = APIRouter(prefix="/api/utilisateurs", tags=["Utilisateurs"])


def _cible(db: Session, admin: Utilisateur, uid: int) -> Utilisateur:
    u = db.get(Utilisateur, uid)
    if u is None or u.organisation_id != admin.organisation_id:      # RA-05
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Utilisateur introuvable")
    return u


def _valider_roles(roles: list[str]) -> list[str]:
    inconnus = set(roles) - set(ROLES)
    if inconnus:
        raise HTTPException(422,
                            "Rôle inconnu : %s" % ", ".join(sorted(inconnus)))
    return [r for r in ROLES if r in roles]   # ordre canonique, sans doublon


def _admins_actifs(db: Session, organisation_id: int) -> int:
    return db.scalar(select(func.count()).select_from(Utilisateur).where(
        Utilisateur.organisation_id == organisation_id, Utilisateur.actif.is_(True),
        Utilisateur.roles.contains(["ADMIN"])))


@routeur.get("", response_model=list[UtilisateurSortie])
def lister(admin: Utilisateur = Depends(administrateur), db: Session = Depends(session_db)):
    return db.scalars(select(Utilisateur).where(
        Utilisateur.organisation_id == admin.organisation_id).order_by(Utilisateur.email)).all()


@routeur.post("", response_model=UtilisateurSortie, status_code=201)
def creer(entree: CreationUtilisateur, admin: Utilisateur = Depends(administrateur),
          db: Session = Depends(session_db)):
    email = entree.email.lower()
    if db.scalar(select(Utilisateur).where(func.lower(Utilisateur.email) == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Un compte existe déjà avec cet e-mail")
    roles = _valider_roles(entree.roles)
    if not roles:
        raise HTTPException(422, "Au moins un rôle (RA-01)")
    u = Utilisateur(organisation_id=admin.organisation_id, email=email, nom=entree.nom,
                    hash_mot_de_passe=hacher(entree.mot_de_passe), roles=roles)
    db.add(u)
    db.flush()
    journal.ajouter(db, admin.organisation_id, "compte_cree", acteur_id=admin.id,
                    details={"email": email, "roles": roles})
    db.commit()
    return u


@routeur.patch("/{uid}/roles", response_model=UtilisateurSortie)
def changer_roles(uid: int, entree: ChangementRoles, admin: Utilisateur = Depends(administrateur),
                  db: Session = Depends(session_db)):
    u = _cible(db, admin, uid)
    roles = _valider_roles(entree.roles)
    if "ADMIN" in u.roles and "ADMIN" not in roles and _admins_actifs(db, u.organisation_id) <= 1:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "RA-03 : impossible de retirer le dernier administrateur")
    avant = list(u.roles)
    u.roles = roles
    journal.ajouter(db, admin.organisation_id, "roles_modifies", acteur_id=admin.id,
                    details={"email": u.email, "avant": avant, "apres": roles})
    db.commit()
    return u


@routeur.patch("/{uid}/actif", response_model=UtilisateurSortie)
def changer_actif(uid: int, entree: ChangementActif, admin: Utilisateur = Depends(administrateur),
                  db: Session = Depends(session_db)):
    u = _cible(db, admin, uid)
    if (not entree.actif and "ADMIN" in u.roles and u.actif
            and _admins_actifs(db, u.organisation_id) <= 1):
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "RA-03 : impossible de désactiver le dernier administrateur")
    u.actif = entree.actif
    journal.ajouter(db, admin.organisation_id,
                    "compte_reactive" if entree.actif else "compte_desactive",
                    acteur_id=admin.id, details={"email": u.email})
    db.commit()
    return u
