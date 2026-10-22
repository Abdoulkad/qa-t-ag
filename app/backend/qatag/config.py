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
    # RA-51 : après le premier compte, seuls les administrateurs créent des comptes,
    # sauf si l'inscription libre est explicitement ouverte.
    inscription_libre: bool = False
    # RA-52 : échecs de connexion tolérés sur la fenêtre, par e-mail puis par adresse IP
    connexion_essais_max: int = 5
    connexion_essais_max_ip: int = 20
    connexion_fenetre_minutes: int = 15

    # Emplacements
    dossier_scripts: Path = RACINE_DEPOT / "webapp" / "scripts"
    dossier_skills: Path = RACINE_DEPOT / "webapp" / "skills"
    dossier_fichiers: Path = RACINE_DEPOT / "app" / "donnees"
    gabarit_cahier: Path = RACINE_DEPOT / "webapp" / "modele-cahier-cas.docx"
    # Cahier de recette : gabarit DSI du rapport de test après exécution
    gabarit_rapport_test: Path = RACINE_DEPOT / "webapp" / "modele-rapport-test.docx"

    # Sauvegardes (RA-54) : dossier, nombre conservé, dossier bin de PostgreSQL
    # si pg_dump n'est pas dans le PATH (fréquent sous Windows)
    dossier_sauvegardes: Path = RACINE_DEPOT / "app" / "sauvegardes"
    sauvegardes_conservees: int = 14
    pg_bin: str = ""

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
