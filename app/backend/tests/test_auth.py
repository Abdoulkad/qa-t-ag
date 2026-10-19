"""RA-06, RA-07 : authentification."""
from sqlalchemy import select

from qatag.db import SessionLocale
from qatag.models import Utilisateur

from .conftest import entetes, inscrire


def test_mot_de_passe_trop_court_refuse(client):
    r = client.post("/api/auth/inscription", json={"email": "a@exemple.ci", "mot_de_passe": "court"})
    assert r.status_code == 422


def test_mot_de_passe_jamais_stocke_en_clair(client):
    inscrire(client, "a@exemple.ci", "motdepasse1")
    with SessionLocale() as db:
        u = db.scalar(select(Utilisateur))
        assert "motdepasse1" not in u.hash_mot_de_passe
        assert u.hash_mot_de_passe.startswith("$2")


def test_connexion_puis_moi(client):
    inscrire(client, "a@exemple.ci")
    r = client.get("/api/auth/moi", headers=entetes(client, "a@exemple.ci"))
    assert r.status_code == 200
    assert r.json()["email"] == "a@exemple.ci"


def test_email_insensible_a_la_casse(client):
    inscrire(client, "A@Exemple.ci")
    assert client.post("/api/auth/inscription", json={
        "email": "a@exemple.ci", "mot_de_passe": "motdepasse1"}).status_code == 409
    entetes(client, "A@EXEMPLE.CI")


def test_mauvais_mot_de_passe_meme_message_que_compte_inconnu(client):
    inscrire(client, "a@exemple.ci")
    r1 = client.post("/api/auth/connexion", json={"email": "a@exemple.ci", "mot_de_passe": "faux-faux"})
    r2 = client.post("/api/auth/connexion", json={"email": "x@exemple.ci", "mot_de_passe": "faux-faux"})
    assert r1.status_code == r2.status_code == 401
    assert r1.json() == r2.json()


def test_sans_jeton_ou_jeton_falsifie_refuse(client):
    assert client.get("/api/auth/moi").status_code == 401
    assert client.get("/api/auth/moi", headers={"Authorization": "Bearer abc"}).status_code == 401
