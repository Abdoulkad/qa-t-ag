from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from .. import connexions, journal
from ..config import parametres
from ..db import session_db
from ..deps import utilisateur_connecte
from ..models import Organisation, Utilisateur
from ..securite import creer_jeton, hacher, verifier, verifier_factice
from .schemas import (ChangementMotDePasse, Connexion, EtatAuth, Inscription, Jeton,
                      UtilisateurSortie)

routeur = APIRouter(prefix="/api/auth", tags=["Authentification"])


def _inscription_ouverte(db: Session) -> bool:
    """RA-51 : ouverte pour le premier compte, puis seulement si configurée libre."""
    return parametres().inscription_libre or db.scalar(
        select(Organisation.id).limit(1)) is None


@routeur.get("/etat", response_model=EtatAuth)
def etat(db: Session = Depends(session_db)):
    """Ce que la page de connexion doit proposer (aucune donnée sur les comptes)."""
    return EtatAuth(inscription_ouverte=_inscription_ouverte(db))


@routeur.post("/inscription", response_model=UtilisateurSortie, status_code=201)
def inscription(entree: Inscription, db: Session = Depends(session_db)):
    email = entree.email.lower()
    # Sérialise les inscriptions : deux « premiers comptes » simultanés impossibles
    db.execute(text("SELECT pg_advisory_xact_lock(1)"))
    if not _inscription_ouverte(db):
        raise HTTPException(status.HTTP_403_FORBIDDEN,
                            "Inscription fermée : demandez un compte à un administrateur")
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
def connexion(entree: Connexion, requete: Request, db: Session = Depends(session_db)):
    email = entree.email.lower()
    ip = requete.client.host if requete.client else "inconnue"
    # RA-52 : au-delà du seuil d'échecs, refus même avec le bon mot de passe
    attente = connexions.attente_minutes(db, email, ip)
    if attente:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                            "Trop de tentatives de connexion. Réessayez dans %d minute%s."
                            % (attente, "s" if attente > 1 else ""),
                            headers={"Retry-After": str(attente * 60)})
    u = db.scalar(select(Utilisateur).where(func.lower(Utilisateur.email) == email))
    # Même message, et même durée de calcul, que le compte existe ou non :
    # pas d'énumération des comptes
    valide = verifier(entree.mot_de_passe, u.hash_mot_de_passe) if u else verifier_factice(
        entree.mot_de_passe)
    if not valide:
        echecs = connexions.noter(db, email, ip, reussie=False)
        if u is not None and echecs == parametres().connexion_essais_max:
            journal.ajouter(db, u.organisation_id, "connexion_bloquee", acteur_id=u.id,
                            details={"email": email, "ip": ip, "echecs": echecs})
        db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "E-mail ou mot de passe incorrect")
    if not u.actif:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Compte désactivé")
    connexions.noter(db, email, ip, reussie=True)
    db.commit()
    return Jeton(jeton=creer_jeton(u.id, u.version_session),
                 mot_de_passe_provisoire=u.mot_de_passe_provisoire)


@routeur.get("/moi", response_model=UtilisateurSortie)
def moi(u: Utilisateur = Depends(utilisateur_connecte)):
    return u


@routeur.post("/mot-de-passe", response_model=Jeton)
def changer_mot_de_passe(entree: ChangementMotDePasse, requete: Request,
                         u: Utilisateur = Depends(utilisateur_connecte),
                         db: Session = Depends(session_db)):
    """RA-56 : l'utilisateur change son mot de passe (obligatoire s'il est provisoire).
    Les autres sessions sont fermées (RA-58) ; celle-ci reçoit un nouveau jeton."""
    ip = requete.client.host if requete.client else "inconnue"
    # Même limitation que la connexion : pas de recherche de l'ancien mot de passe
    attente = connexions.attente_minutes(db, u.email, ip)
    if attente:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                            "Trop de tentatives. Réessayez dans %d minute%s."
                            % (attente, "s" if attente > 1 else ""),
                            headers={"Retry-After": str(attente * 60)})
    if not verifier(entree.actuel, u.hash_mot_de_passe):
        connexions.noter(db, u.email, ip, reussie=False)
        db.commit()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Mot de passe actuel incorrect")
    if entree.nouveau == entree.actuel:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            "Le nouveau mot de passe doit être différent de l'actuel")
    provisoire = u.mot_de_passe_provisoire
    u.hash_mot_de_passe = hacher(entree.nouveau)
    u.mot_de_passe_provisoire = False
    u.version_session += 1
    journal.ajouter(db, u.organisation_id, "mot_de_passe_change", acteur_id=u.id,
                    details={"email": u.email, "provisoire_remplace": provisoire})
    db.commit()
    return Jeton(jeton=creer_jeton(u.id, u.version_session))
