from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from .. import journal
from ..db import session_db
from ..deps import utilisateur_courant
from ..models import Organisation, Utilisateur
from ..securite import creer_jeton, hacher, verifier
from .schemas import Connexion, Inscription, Jeton, UtilisateurSortie

routeur = APIRouter(prefix="/api/auth", tags=["Authentification"])


@routeur.post("/inscription", response_model=UtilisateurSortie, status_code=201)
def inscription(entree: Inscription, db: Session = Depends(session_db)):
    email = entree.email.lower()
    # Sérialise les inscriptions : deux « premiers comptes » simultanés impossibles
    db.execute(text("SELECT pg_advisory_xact_lock(1)"))
    if db.scalar(select(Utilisateur).where(func.lower(Utilisateur.email) == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Un compte existe déjà avec cet e-mail")
    org = db.scalar(select(Organisation).order_by(Organisation.id).limit(1))
    if org is None:
        # RA-02 : premier compte de l'installation -> crée l'organisation, 3 rôles
        org = Organisation(nom=entree.organisation or "Mon organisation")
        db.add(org)
        db.flush()
        roles = ["ANALYSTE", "SUPERVISEUR", "ADMIN"]
    else:
        roles = ["ANALYSTE"]
    u = Utilisateur(organisation_id=org.id, email=email, nom=entree.nom,
                    hash_mot_de_passe=hacher(entree.mot_de_passe), roles=roles)
    db.add(u)
    db.flush()
    journal.ajouter(db, org.id, "compte_cree", acteur_id=u.id,
                    details={"email": email, "roles": roles})
    db.commit()
    return u


@routeur.post("/connexion", response_model=Jeton)
def connexion(entree: Connexion, db: Session = Depends(session_db)):
    u = db.scalar(select(Utilisateur).where(func.lower(Utilisateur.email) == entree.email.lower()))
    # Même message que le compte existe ou non : pas d'énumération des comptes
    if u is None or not verifier(entree.mot_de_passe, u.hash_mot_de_passe):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "E-mail ou mot de passe incorrect")
    if not u.actif:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Compte désactivé")
    return Jeton(jeton=creer_jeton(u.id))


@routeur.get("/moi", response_model=UtilisateurSortie)
def moi(u: Utilisateur = Depends(utilisateur_courant)):
    return u
