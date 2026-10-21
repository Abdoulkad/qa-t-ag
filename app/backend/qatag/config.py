"""Configuration lue dans le fichier .env (jamais en base pour les secrets — RA-36)."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

RACINE_DEPOT = Path(__file__).resolve().parents[3]


class Parametres(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8",
                                      extra="ignore")

    # Base PostgreSQL
    database_url: str = "postgresql+psycopg://qatag:qatag@localhost:5432/qatag"

    # Sécurité
    secret_key: str = "a-changer-dans-le-fichier-env"
    duree_session_heures: int = 8

    # Emplacements
    dossier_scripts: Path = RACINE_DEPOT / "webapp" / "scripts"
    dossier_skills: Path = RACINE_DEPOT / "webapp" / "skills"
    dossier_fichiers: Path = RACINE_DEPOT / "app" / "donnees"
    gabarit_cahier: Path = RACINE_DEPOT / "webapp" / "modele-cahier-cas.docx"

    # Clés d'API des fournisseurs IA (RA-36) — jamais exposées par l'API
    deepseek_api_key: str = ""
    openai_api_key: str = ""
    mistral_api_key: str = ""
    anthropic_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434/v1"
    # Longueur maximale d'une réponse IA, en tokens. 0 = valeur du fournisseur.
    ia_max_tokens: int = 0

    # Exécution des tâches IA : "fond" (thread) ou "immediat" (tests)
    mode_taches: str = "fond"


@lru_cache
def parametres() -> Parametres:
    return Parametres()
