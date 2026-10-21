from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .db import session_db
from .models import Utilisateur
from .securite import lire_jeton

_bearer = HTTPBearer(auto_error=False)


MOT_DE_PASSE_A_CHANGER = "MOT_DE_PASSE_A_CHANGER"


def utilisateur_connecte(jeton: HTTPAuthorizationCredentials | None = Depends(_bearer),
                         db: Session = Depends(session_db)) -> Utilisateur:
    """Session valide, même avec un mot de passe provisoire (RA-55) : réservé à
    /auth/moi et au changement de mot de passe."""
    if jeton is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Connexion requise")
    lu = lire_jeton(jeton.credentials)
    u = db.get(Utilisateur, lu[0]) if lu else None
    if u is None or not u.actif:                                   # RA-04
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session invalide ou expirée")
    if lu[1] != u.version_session:                                 # RA-58
        raise HTTPException(status.HTTP_401_UNAUTHORIZED,
                            "Session expirée : le mot de passe a changé, reconnectez-vous")
    return u


def utilisateur_courant(u: Utilisateur = Depends(utilisateur_connecte)) -> Utilisateur:
    """Session valide et mot de passe définitif : toutes les autres routes."""
    if u.mot_de_passe_provisoire:                                  # RA-55
        raise HTTPException(status.HTTP_403_FORBIDDEN,
                            {"code": MOT_DE_PASSE_A_CHANGER,
                             "message": "Changez votre mot de passe provisoire pour continuer"})
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
