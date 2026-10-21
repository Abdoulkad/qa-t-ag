from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import journal
from ..db import session_db
from ..deps import administrateur, utilisateur_courant
from ..ia.fournisseurs import FOURNISSEURS
from ..models import ConfigIA, Utilisateur, maintenant
from .schemas import ConfigIAEntree

routeur = APIRouter(prefix="/api/config-ia", tags=["Configuration IA"])


def _etat(db: Session, organisation_id: int) -> dict:
    c = db.get(ConfigIA, organisation_id)
    return {
        "actif": {"fournisseur": c.fournisseur, "modele": c.modele} if c else None,
        # RA-36 : on indique seulement si une clé est présente, jamais sa valeur
        "fournisseurs": [{"code": f.code, "libelle": f.libelle,
                          "cle_presente": f.disponible(),
                          "cle_requise": f.attribut_cle is not None,
                          "modele_suggere": f.modele_par_defaut}
                         for f in FOURNISSEURS.values()],
    }


@routeur.get("")
def lire(u: Utilisateur = Depends(utilisateur_courant), db: Session = Depends(session_db)):
    return _etat(db, u.organisation_id)


@routeur.put("")
def modifier(entree: ConfigIAEntree, admin: Utilisateur = Depends(administrateur),
             db: Session = Depends(session_db)):
    f = FOURNISSEURS.get(entree.fournisseur)
    if f is None:
        raise HTTPException(422, "Fournisseur inconnu")
    if not f.disponible():                                            # RA-37
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "RA-37 : la clé d'API de %s est absente du fichier .env "
                            "du serveur" % f.libelle)
    c = db.get(ConfigIA, admin.organisation_id)
    if c is None:
        c = ConfigIA(organisation_id=admin.organisation_id)
        db.add(c)
    c.fournisseur, c.modele = f.code, entree.modele.strip()
    c.modifie_par_id, c.modifie_le = admin.id, maintenant()
    journal.ajouter(db, admin.organisation_id, "config_ia_modifiee", acteur_id=admin.id,
                    details={"fournisseur": f.code, "modele": c.modele})
    db.commit()
    return _etat(db, admin.organisation_id)
