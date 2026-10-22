"""Tests sur un vrai PostgreSQL (base qatag_test), sans appel IA réel."""
import json
import time
import os
import subprocess
import sys
from pathlib import Path

os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://qatag:qatag@localhost:5432/qatag_test")
os.environ["SECRET_KEY"] = "cle-de-test-suffisamment-longue-pour-hs256"
os.environ["MODE_TACHES"] = "immediat"
# Les tests créent plusieurs comptes par l'inscription ; l'inscription fermée
# (valeur par défaut, RA-51) est testée à part dans test_securite.py
os.environ["INSCRIPTION_LIBRE"] = "true"
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
Aucune

## Inventaire REQ et BR
- REQ-001 — mot de passe sécurisé

## Défauts
### DEF-001 — Ambiguïté — Bloquante
- **Section** : US-042
- **Citation** : « durée limitée »
- **Constat** : La durée de validité du lien n'est pas chiffrée.
- **Justification** : Testabilité : sans durée, aucun cas d'expiration ne peut être conçu.
- **Question** : Quelle est la durée de validité exacte du lien ?

### DEF-002 — Terme non défini — Majeure
- **Section** : REQ-001
- **Citation** : « sécurisé »
- **Constat** : Les règles de complexité ne sont pas définies.
- **Question** : Quelles règles de complexité définissent un mot de passe sécurisé ?

### DEF-003 — Exigence non testable — Mineure
- **Section** : US-042
- **Citation** : « facilement et sans effort »
- **Constat** : Aucun critère mesurable.
- **Question** : Comment mesurer « facilement » ?

## Questions complémentaires
Aucune

## Statut du livrable
A_CLARIFIER
"""


REECRITURE_IA = """## User Story réécrite
En tant qu'utilisateur ayant oublié son mot de passe, je reçois un lien de
réinitialisation valable 30 minutes et je définis un nouveau mot de passe.

## Règles métier
### RG-01
- **Règle** : L'utilisateur réinitialise son mot de passe par un lien valable une durée limitée.
- **Sources** : « réinitialiser son mot de passe facilement » ; « durée limitée »
### RG-02
- **Règle** : Le nouveau mot de passe respecte la politique de sécurité.
- **Sources** : « le nouveau mot de passe doit être sécurisé »

## Critères d'acceptation
### CA-01
- **Critère** : Étant donné un lien émis il y a 31 minutes, quand je l'ouvre, alors il est refusé.
- **Règles** : RG-01
- **Sources** : « durée limitée » ; Q-1
### CA-02
- **Critère** : Étant donné un nouveau mot de passe de 7 caractères, quand je valide, alors il est refusé.
- **Règles** : RG-02
- **Sources** : Q-2
### CA-03
- **Critère** : Étant donné une réinitialisation réussie, alors un SMS de confirmation est envoyé.
- **Sources** :
"""

CONCEPTION_IA = """ID;Titre;Objectif;Exigence;Technique;Priorité;Type;Préconditions;Données de test;Étapes;Résultat attendu;Statut livrable
CT-001;Lien expiré refusé;Vérifier l'expiration;CA-01;valeurs limites;Haute;Fonctionnel;Lien émis;Lien émis à 08:00 / ouverture à 08:31;Ouvrir le lien;Message « Lien expiré »;OK
CT-002;Lien valide accepté;Vérifier la validité;CA-01;Valeurs Limites;Haute;Fonctionnel;Lien émis;Lien émis à 08:00 / ouverture à 08:29;Ouvrir le lien;Formulaire de saisie affiché;OK
CT-003;Mot de passe trop court;Vérifier la longueur;CA-02;valeurs limites;Critique;Fonctionnel;Formulaire ouvert;mot de passe valide;Saisir le mot de passe;Message « 8 caractères minimum »;OK
CT-004;Cas douteux;Vérifier X;CA-02;partitions d'équivalence;Moyenne;Fonctionnel;Formulaire ouvert;Abc12345;Saisir le mot de passe;Mot de passe accepté;À_CLARIFIER

## Justifications
CT-001 : valeurs limites — 31 min, juste au-delà de la borne de 30 min.
CT-002 : valeurs limites — 29 min, juste en deçà de la borne.
CT-003 : valeurs limites — 7 caractères, sous la borne de 8.
"""


QUALIFICATION_IA = """## Anomalie
- **Titre** : Le lien expiré reste accepté au-delà de 30 minutes
- **Gravité** : Critique
- **Reproductibilité** : Non déterminée
- **Justification** : Le résultat attendu est le message « Lien expiré ». Le testeur obtient le formulaire de saisie, ce qui contredit CA-01. Une seule exécution en échec est disponible.
"""


REDACTION_IA = """## Contexte
La campagne porte sur la réinitialisation du mot de passe : expiration du lien et longueur du nouveau mot de passe.
## Objectifs
- Vérifier le refus d'un lien expiré (CA-01).
- Vérifier la longueur minimale du mot de passe (CA-02).
## Synthèse
Sur les quatre (04) cas de test, 4 cas ont été exécutés : 3 cas réussis (75 %) et 1 cas en échec.
L'anomalie ANO-001 reste ouverte.
## Recommandations
- CT-001 : corriger ANO-001 puis rejouer le cas avant la mise en production.
## Conclusion
La fonctionnalité est conforme sur la longueur du mot de passe ; le refus des liens expirés reste à corriger.
- **Avis** : Favorable avec réserves
"""


class IAFactice:
    """Remplace le réseau : enregistre les appels, renvoie une réponse préparée
    selon l'agent appelé (revue, réécriture ou conception)."""

    def __init__(self):
        self.appels = []
        self.reponses = {"revue": RAPPORT_IA, "reecriture": REECRITURE_IA,
                         "conception": CONCEPTION_IA, "anomalie": QUALIFICATION_IA,
                         "rapport": REDACTION_IA}
        self.statut_http = 200
        self.pauses = []
        self.pannes = []      # exceptions httpx levées aux premiers appels
        self.flux = False     # répondre en SSE (text/event-stream)

    @property
    def reponse(self):
        return self.reponses["revue"]

    @reponse.setter
    def reponse(self, valeur):
        self.reponses["revue"] = valeur

    def _agent(self, corps):
        systeme = corps.get("system") or corps["messages"][0]["content"]
        if "Réécriture d'exigence" in systeme:
            return "reecriture"
        if "AG-09" in systeme:
            return "anomalie"
        if "AG-11" in systeme:
            return "rapport"
        if "AG-02" in systeme:
            return "conception"
        return "revue"

    @staticmethod
    def _sse(texte, anthropic):
        moities = [texte[:len(texte) // 2], texte[len(texte) // 2:]]
        lignes = ["", ": keep-alive", ""]
        for m in moities:
            obj = ({"type": "content_block_delta", "delta": {"type": "text_delta", "text": m}}
                   if anthropic else {"choices": [{"delta": {"content": m}}]})
            lignes += ["data: " + json.dumps(obj), ""]
        lignes += ["data: [DONE]", ""]
        return "\n".join(lignes).encode()

    def __call__(self, requete: httpx.Request) -> httpx.Response:
        corps = json.loads(requete.content)
        self.appels.append({"url": str(requete.url), "entetes": dict(requete.headers),
                            "corps": corps})
        if self.pannes:
            raise self.pannes.pop(0)
        if self.statut_http != 200:
            return httpx.Response(self.statut_http, json={"error": "refus"})
        texte = self.reponses[self._agent(corps)]
        if isinstance(texte, list):          # réponses successives : la dernière se répète
            texte = texte.pop(0) if len(texte) > 1 else texte[0]
        if self.flux:
            return httpx.Response(200, headers={"content-type": "text/event-stream"},
                                  content=self._sse(texte, "anthropic" in str(requete.url)))
        if "anthropic" in str(requete.url):
            return httpx.Response(200, json={"content": [{"type": "text", "text": texte}]})
        return httpx.Response(200, json={"choices": [{"message": {"content": texte}}]})


@pytest.fixture(scope="session", autouse=True)
def schema():
    env = dict(os.environ)
    subprocess.run([sys.executable, "-m", "alembic", "downgrade", "base"], cwd=BACKEND, env=env, check=True,
                   capture_output=True)
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=BACKEND, env=env, check=True,
                   capture_output=True)
    yield


@pytest.fixture(autouse=True)
def base_vide():
    tables = ("preuve, anomalie, execution, trace, cas_test, critere_acceptation, "
              "question_metier, defaut, decision_porte, tache_ia, journal, version_exigence, "
              "participant, cloture_recette, rapport_recette, mission, config_ia, utilisateur, organisation, "
              "tentative_connexion")
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
    fournisseurs.attendre = faux.pauses.append     # pas d'attente réelle
    yield faux
    fournisseurs.transport_http = None
    fournisseurs.attendre = time.sleep


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
