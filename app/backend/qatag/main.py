"""Application FastAPI QA-T-AG."""
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from . import journal
from .db import session_db
from .deps import administrateur
from .models import Utilisateur
from .cahier_recette import ControleEchoue
from .regles import RegleViolee
from .config import parametres
from .routes import auth, config_ia, missions, recette, utilisateurs

_cle = parametres().secret_key
if _cle == "a-changer-dans-le-fichier-env" or len(_cle) < 32:
    raise RuntimeError("SECRET_KEY absente ou trop courte dans le fichier .env "
                       "(32 caractères minimum). Voir app/backend/.env.example.")

app = FastAPI(title="QA-T-AG", version="1.0.0",
              description="Le script calcule · l'agent analyse · l'humain arbitre.")

# Le frontend React de développement tourne sur un autre port
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"],
                   allow_methods=["*"], allow_headers=["*"])


# --- En-têtes de sécurité (RA-53) ---------------------------------------------
# L'interface n'utilise que ses propres fichiers : tout le reste est refusé.
CSP_INTERFACE = ("default-src 'self'; script-src 'self'; style-src 'self'; "
                 "img-src 'self' data: blob:; font-src 'self'; connect-src 'self'; "
                 "object-src 'none'; base-uri 'self'; form-action 'self'; "
                 "frame-ancestors 'none'")
# La documentation de l'API (/docs, /redoc) charge Swagger et ReDoc depuis un CDN
CSP_DOCUMENTATION = ("default-src 'self'; "
                     "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                     "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net "
                     "https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; "
                     "img-src 'self' data: https://fastapi.tiangolo.com https://cdn.redoc.ly; "
                     "worker-src 'self' blob:; connect-src 'self'; object-src 'none'; "
                     "base-uri 'self'; frame-ancestors 'none'")
ENTETES_SECURITE = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",
    "Cross-Origin-Opener-Policy": "same-origin",
}


@app.middleware("http")
async def entetes_securite(request: Request, call_next):
    reponse = await call_next(request)
    chemin = request.url.path
    for nom, valeur in ENTETES_SECURITE.items():
        reponse.headers.setdefault(nom, valeur)
    documentation = chemin in ("/docs", "/redoc") or chemin.startswith("/docs/")
    reponse.headers.setdefault("Content-Security-Policy",
                               CSP_DOCUMENTATION if documentation else CSP_INTERFACE)
    if chemin.startswith("/api/"):
        # Données métier : jamais conservées par le navigateur ou un proxy
        reponse.headers.setdefault("Cache-Control", "no-store")
    if request.url.scheme == "https":
        # Seulement en HTTPS : en HTTP, l'en-tête serait ignoré par le navigateur
        reponse.headers.setdefault("Strict-Transport-Security", "max-age=31536000")
    return reponse


@app.exception_handler(ControleEchoue)
def controle_echoue(_: Request, e: ControleEchoue):
    """RA-33 : le document produit ne correspond pas à la base, il n'est pas remis."""
    return JSONResponse(status_code=500, content={
        "regle": "RA-33", "detail": "Cahier non remis : le contrôle de relecture a échoué (%s)" % e})


@app.exception_handler(RegleViolee)
def regle_violee(_: Request, e: RegleViolee):
    """Une règle métier refuse l'action : 409 avec la règle et le détail."""
    return JSONResponse(status_code=409, content={
        "regle": e.regle, "detail": e.message, "elements": e.details})


for r in (auth.routeur, utilisateurs.routeur, config_ia.routeur, missions.routeur,
          recette.routeur):
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


# --- Interface web -----------------------------------------------------------
# Une fois le frontend construit (app/frontend/dist), le même serveur sert
# l'interface : une seule commande à lancer sur le poste.
from pathlib import Path  # noqa: E402

from fastapi import HTTPException  # noqa: E402
from fastapi.responses import FileResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402

_INTERFACE = Path(__file__).resolve().parents[2] / "frontend" / "dist"

if (_INTERFACE / "index.html").is_file():
    app.mount("/assets", StaticFiles(directory=_INTERFACE / "assets"), name="assets")

    @app.get("/{chemin:path}", include_in_schema=False)
    def interface(chemin: str):
        if chemin.startswith("api/"):
            raise HTTPException(404, "Route d'API inconnue")
        fichier = (_INTERFACE / chemin).resolve()
        if chemin and fichier.is_file() and _INTERFACE in fichier.parents:
            return FileResponse(fichier)
        return FileResponse(_INTERFACE / "index.html")   # routes React (/missions/3…)
