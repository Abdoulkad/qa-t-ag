from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .db import session_db
from .models import Utilisateur
from .securite import lire_jeton

_bearer = HTTPBearer(auto_error=False)


def utilisateur_courant(jeton: HTTPAuthorizationCredentials | None = Depends(_bearer),
                        db: Session = Depends(session_db)) -> Utilisateur:
    if jeton is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Connexion requise")
    uid = lire_jeton(jeton.credentials)
    u = db.get(Utilisateur, uid) if uid else None
    if u is None or not u.actif:                                   # RA-04
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session invalide ou expirée")
    return u


def exiger_role(*roles: str):
    def _verif(u: Utilisateur = Depends(utilisateur_courant)) -> Utilisateur:
        if not set(roles) & set(u.roles):
            raise HTTPException(status.HTTP_403_FORBIDDEN,
                                "Rôle requis : %s" % " ou ".join(roles))
        return u
    return _verif


# Agir sur les missions : Analyste ou Superviseur (un Admin seul ne le peut pas)
acteur_mission = exiger_role("ANALYSTE", "SUPERVISEUR")
administrateur = exiger_role("ADMIN")
