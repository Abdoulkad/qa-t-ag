"""RA-01 à RA-05 : comptes, rôles, cloisonnement."""
from qatag.db import SessionLocale
from qatag.models import Organisation, Utilisateur

from .conftest import entetes, inscrire


def test_premier_compte_a_les_trois_roles_les_suivants_analyste(client):
    assert inscrire(client, "premier@exemple.ci")["roles"] == ["ANALYSTE", "SUPERVISEUR", "ADMIN"]
    assert inscrire(client, "second@exemple.ci")["roles"] == ["ANALYSTE"]


def test_seul_un_admin_gere_les_roles(client, admin):
    u = inscrire(client, "testeur@exemple.ci")
    h_testeur = entetes(client, "testeur@exemple.ci")
    assert client.patch("/api/utilisateurs/%d/roles" % u["id"], json={"roles": ["SUPERVISEUR"]},
                        headers=h_testeur).status_code == 403
    r = client.patch("/api/utilisateurs/%d/roles" % u["id"],
                     json={"roles": ["SUPERVISEUR", "ANALYSTE"]}, headers=admin)
    assert r.status_code == 200
    assert r.json()["roles"] == ["ANALYSTE", "SUPERVISEUR"]     # cumul, ordre canonique


def test_roles_vides_ou_inconnus_refuses(client, admin):
    u = inscrire(client, "t@exemple.ci")
    assert client.patch("/api/utilisateurs/%d/roles" % u["id"], json={"roles": []},
                        headers=admin).status_code == 422
    assert client.patch("/api/utilisateurs/%d/roles" % u["id"], json={"roles": ["ROI"]},
                        headers=admin).status_code == 422


def test_dernier_admin_ne_peut_pas_se_retirer(client, admin):
    moi = client.get("/api/auth/moi", headers=admin).json()
    r = client.patch("/api/utilisateurs/%d/roles" % moi["id"], json={"roles": ["ANALYSTE"]},
                     headers=admin)
    assert r.status_code == 409 and "RA-03" in r.json()["detail"]
    r = client.patch("/api/utilisateurs/%d/actif" % moi["id"], json={"actif": False}, headers=admin)
    assert r.status_code == 409


def test_compte_desactive_ne_peut_plus_agir(client, admin):
    u = inscrire(client, "t@exemple.ci")
    h = entetes(client, "t@exemple.ci")
    client.patch("/api/utilisateurs/%d/actif" % u["id"], json={"actif": False}, headers=admin)
    assert client.get("/api/auth/moi", headers=h).status_code == 401
    assert client.post("/api/auth/connexion", json={
        "email": "t@exemple.ci", "mot_de_passe": "motdepasse1"}).status_code == 403


def test_admin_ne_voit_pas_une_autre_organisation(client, admin):
    with SessionLocale() as db:
        autre = Organisation(nom="Autre")
        db.add(autre)
        db.flush()
        etranger = Utilisateur(organisation_id=autre.id, email="x@autre.ci", hash_mot_de_passe="x",
                               roles=["ANALYSTE"])
        db.add(etranger)
        db.commit()
        eid = etranger.id
    emails = [u["email"] for u in client.get("/api/utilisateurs", headers=admin).json()]
    assert "x@autre.ci" not in emails
    assert client.patch("/api/utilisateurs/%d/roles" % eid, json={"roles": ["ADMIN"]},
                        headers=admin).status_code == 404
