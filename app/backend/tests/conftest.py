"""Tests sur un vrai PostgreSQL (base qatag_test), sans appel IA réel."""
import json
import os
import subprocess
from pathlib import Path

os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://qatag:qatag@localhost:5432/qatag_test")
os.environ["SECRET_KEY"] = "cle-de-test-suffisamment-longue-pour-hs256"
os.environ["MODE_TACHES"] = "immediat"
os.environ["DEEPSEEK_API_KEY"] = "cle-factice"
os.environ["ANTHROPIC_API_KEY"] = ""
os.environ["OPENAI_API_KEY"] = ""
os.environ["MISTRAL_API_KEY"] = ""

import httpx  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from qatag.db import moteur  # noqa: E402
from qatag.ia import fournisseurs  # noqa: E402
from qatag.main import app  # noqa: E402

BACKEND = Path(__file__).resolve().parents[1]

US_TEST = (
    "US-042 — Réinitialisation du mot de passe\n"
    "L'utilisateur doit pouvoir réinitialiser son mot de passe facilement.\n"
    "Le lien de réinitialisation est valide pendant une durée limitée.\n"
    "REQ-001 : le nouveau mot de passe doit être sécurisé.\n"
)

RAPPORT_IA = """# Revue SFD — us-042

## Alerte sécurité

## Inventaire REQ et BR
- REQ-001 — mot de passe sécurisé

## Défauts
### DEF-001 — Ambiguïté — Bloquante
- **Section** : US-042
- **Citation** : « durée limitée »
- **Question** : Quelle est la durée de validité exacte du lien ?

### DEF-002 — Terme non défini — Majeure
- **Section** : REQ-001
- **Citation** : « sécurisé »
- **Question** : Quelles règles de complexité définissent un mot de passe sécurisé ?

### DEF-003 — Exigence non testable — Mineure
- **Section** : US-042
- **Citation** : « facilement et sans effort »
- **Question** : Comment mesurer « facilement » ?

## Statut du livrable
A_CLARIFIER
"""


class IAFactice:
    """Remplace le réseau : enregistre les appels, renvoie une réponse préparée."""

    def __init__(self):
        self.appels = []
        self.reponse = RAPPORT_IA
        self.statut_http = 200

    def __call__(self, requete: httpx.Request) -> httpx.Response:
        self.appels.append({"url": str(requete.url), "entetes": dict(requete.headers),
                            "corps": json.loads(requete.content)})
        if self.statut_http != 200:
            return httpx.Response(self.statut_http, json={"error": "refus"})
        if "anthropic" in str(requete.url):
            return httpx.Response(200, json={"content": [{"type": "text", "text": self.reponse}]})
        return httpx.Response(200, json={"choices": [{"message": {"content": self.reponse}}]})


@pytest.fixture(scope="session", autouse=True)
def schema():
    env = dict(os.environ)
    subprocess.run(["alembic", "downgrade", "base"], cwd=BACKEND, env=env, check=True,
                   capture_output=True)
    subprocess.run(["alembic", "upgrade", "head"], cwd=BACKEND, env=env, check=True,
                   capture_output=True)
    yield


@pytest.fixture(autouse=True)
def base_vide():
    tables = ("preuve, anomalie, execution, trace, cas_test, critere_acceptation, "
              "question_metier, defaut, decision_porte, tache_ia, journal, version_exigence, "
              "participant, mission, config_ia, utilisateur, organisation")
    with moteur.begin() as c:
        # Les tests seuls contournent la protection du journal, pour repartir à vide
        c.execute(text("ALTER TABLE journal DISABLE TRIGGER USER"))
        c.execute(text("TRUNCATE %s RESTART IDENTITY CASCADE" % tables))
        c.execute(text("ALTER TABLE journal ENABLE TRIGGER USER"))
    yield


@pytest.fixture
def ia():
    faux = IAFactice()
    fournisseurs.transport_http = httpx.MockTransport(faux)
    yield faux
    fournisseurs.transport_http = None


@pytest.fixture
def client():
    return TestClient(app)


def inscrire(client, email, mot_de_passe="motdepasse1", nom=""):
    r = client.post("/api/auth/inscription",
                    json={"email": email, "mot_de_passe": mot_de_passe, "nom": nom})
    assert r.status_code == 201, r.text
    return r.json()


def entetes(client, email, mot_de_passe="motdepasse1"):
    r = client.post("/api/auth/connexion", json={"email": email, "mot_de_passe": mot_de_passe})
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["jeton"]}


@pytest.fixture
def admin(client):
    """Premier compte : Analyste + Superviseur + Admin, IA DeepSeek configurée."""
    inscrire(client, "bamk@exemple.ci", nom="BAMK")
    h = entetes(client, "bamk@exemple.ci")
    r = client.put("/api/config-ia", json={"fournisseur": "deepseek", "modele": "deepseek-flash"},
                   headers=h)
    assert r.status_code == 200, r.text
    return h
