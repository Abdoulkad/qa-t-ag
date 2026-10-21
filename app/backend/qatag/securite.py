"""Mots de passe (bcrypt) et jetons de session (JWT) — RA-06, RA-07."""
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from .config import parametres

ALGO = "HS256"
LONGUEUR_MIN_MOT_DE_PASSE = 8


def hacher(mot_de_passe: str) -> str:
    # bcrypt ne prend en compte que les 72 premiers octets
    return bcrypt.hashpw(mot_de_passe.encode("utf-8")[:72], bcrypt.gensalt()).decode()


def verifier(mot_de_passe: str, hache: str) -> bool:
    try:
        return bcrypt.checkpw(mot_de_passe.encode("utf-8")[:72], hache.encode())
    except ValueError:
        return False


# Empreinte d'un mot de passe que personne ne connaît : vérifier contre elle
# quand le compte n'existe pas prend le même temps qu'une vraie vérification.
_HASH_FACTICE = bcrypt.hashpw(b"compte-inexistant", bcrypt.gensalt()).decode()


def verifier_factice(mot_de_passe: str) -> bool:
    verifier(mot_de_passe, _HASH_FACTICE)
    return False


def creer_jeton(utilisateur_id: int) -> str:
    p = parametres()
    expire = datetime.now(timezone.utc) + timedelta(hours=p.duree_session_heures)
    return jwt.encode({"sub": str(utilisateur_id), "exp": expire}, p.secret_key, algorithm=ALGO)


def lire_jeton(jeton: str) -> int | None:
    try:
        donnees = jwt.decode(jeton, parametres().secret_key, algorithms=[ALGO])
        return int(donnees["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None
