"""Application FastAPI QA-T-AG."""
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from . import journal
from .db import session_db
from .deps import administrateur
from .models import Utilisateur
from .regles import RegleViolee
from .config import parametres
from .routes import auth, config_ia, missions, utilisateurs

_cle = parametres().secret_key
if _cle == "a-changer-dans-le-fichier-env" or len(_cle) < 32:
    raise RuntimeError("SECRET_KEY absente ou trop courte dans le fichier .env "
                       "(32 caractères minimum). Voir app/backend/.env.example.")

app = FastAPI(title="QA-T-AG", version="2.0.0-lot1",
              description="Le script calcule · l'agent analyse · l'humain arbitre.")

# Le frontend React de développement tourne sur un autre port
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"],
                   allow_methods=["*"], allow_headers=["*"])


@app.exception_handler(RegleViolee)
def regle_violee(_: Request, e: RegleViolee):
    """Une règle métier refuse l'action : 409 avec la règle et le détail."""
    return JSONResponse(status_code=409, content={
        "regle": e.regle, "detail": e.message, "elements": e.details})


for r in (auth.routeur, utilisateurs.routeur, config_ia.routeur, missions.routeur):
    app.include_router(r)


@app.get("/api/sante")
def sante():
    return {"etat": "ok"}


@app.get("/api/journal/verification")
def verification_journal(admin: Utilisateur = Depends(administrateur),
                         db: Session = Depends(session_db)):
    """RA-35 : vérifie que la chaîne d'empreintes du journal est intacte."""
    integre, premiere_faute = journal.verifier_chaine(db, admin.organisation_id)
    return {"integre": integre, "premiere_entree_alteree": premiere_faute}
