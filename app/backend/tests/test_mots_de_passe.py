"""RA-55 à RA-58 : mot de passe provisoire, changement, réinitialisation, sessions."""
from sqlalchemy import select

from qatag.db import SessionLocale
from qatag.models import EntreeJournal, Utilisateur

from .conftest import entetes, inscrire


def _connexion(client, email, mdp):
    return client.post("/api/auth/connexion", json={"email": email, "mot_de_passe": mdp})


def _bearer(jeton):
    return {"Authorization": "Bearer " + jeton}


def _creer_par_admin(client, email="b@exemple.ci", mdp="provisoire1"):
    inscrire(client, "admin@exemple.ci")
    r = client.post("/api/utilisateurs", headers=entetes(client, "admin@exemple.ci"),
                    json={"email": email, "mot_de_passe": mdp, "roles": ["ANALYSTE"]})
    assert r.status_code == 201
    return r.json()


def _changer(client, jeton, actuel, nouveau):
    return client.post("/api/auth/mot-de-passe", headers=_bearer(jeton),
                       json={"actuel": actuel, "nouveau": nouveau})


# --- RA-55 : mot de passe provisoire ----------------------------------------------

def test_compte_cree_par_admin_a_un_mot_de_passe_provisoire(client):
    u = _creer_par_admin(client)
    assert u["mot_de_passe_provisoire"] is True
    r = _connexion(client, "b@exemple.ci", "provisoire1")
    assert r.status_code == 200 and r.json()["mot_de_passe_provisoire"] is True


def test_inscription_libre_n_est_pas_provisoire(client):
    inscrire(client, "a@exemple.ci")
    assert _connexion(client, "a@exemple.ci", "motdepasse1").json()["mot_de_passe_provisoire"] is False


def test_provisoire_bloque_tout_sauf_moi_et_changement(client):
    _creer_par_admin(client)
    jeton = _connexion(client, "b@exemple.ci", "provisoire1").json()["jeton"]
    assert client.get("/api/auth/moi", headers=_bearer(jeton)).status_code == 200
    r = client.get("/api/missions", headers=_bearer(jeton))
    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "MOT_DE_PASSE_A_CHANGER"
    assert client.get("/api/pilotage", headers=_bearer(jeton)).status_code == 403


def test_apres_changement_tout_est_accessible(client):
    _creer_par_admin(client)
    jeton = _connexion(client, "b@exemple.ci", "provisoire1").json()["jeton"]
    r = _changer(client, jeton, "provisoire1", "definitif-123")
    assert r.status_code == 200
    nouveau = r.json()["jeton"]
    assert client.get("/api/missions", headers=_bearer(nouveau)).status_code == 200
    assert client.get("/api/auth/moi", headers=_bearer(nouveau)).json()["mot_de_passe_provisoire"] is False
    assert _connexion(client, "b@exemple.ci", "definitif-123").status_code == 200
    assert _connexion(client, "b@exemple.ci", "provisoire1").status_code == 401


# --- RA-56 : changement par l'utilisateur ------------------------------------------

def test_changement_exige_le_mot_de_passe_actuel(client):
    inscrire(client, "a@exemple.ci")
    jeton = _connexion(client, "a@exemple.ci", "motdepasse1").json()["jeton"]
    r = _changer(client, jeton, "pas-le-bon", "nouveau-123")
    assert r.status_code == 400 and "actuel incorrect" in r.json()["detail"]


def test_nouveau_doit_differer_de_l_actuel(client):
    inscrire(client, "a@exemple.ci")
    jeton = _connexion(client, "a@exemple.ci", "motdepasse1").json()["jeton"]
    assert _changer(client, jeton, "motdepasse1", "motdepasse1").status_code == 400


def test_nouveau_mot_de_passe_trop_court(client):
    inscrire(client, "a@exemple.ci")
    jeton = _connexion(client, "a@exemple.ci", "motdepasse1").json()["jeton"]
    assert _changer(client, jeton, "motdepasse1", "court").status_code == 422


def test_essais_de_l_ancien_mot_de_passe_limites(client):
    inscrire(client, "a@exemple.ci")
    jeton = _connexion(client, "a@exemple.ci", "motdepasse1").json()["jeton"]
    for _ in range(5):
        assert _changer(client, jeton, "mauvais-mdp", "nouveau-123").status_code == 400
    assert _changer(client, jeton, "motdepasse1", "nouveau-123").status_code == 429


def test_changement_au_journal_sans_mot_de_passe(client):
    inscrire(client, "a@exemple.ci")
    jeton = _connexion(client, "a@exemple.ci", "motdepasse1").json()["jeton"]
    _changer(client, jeton, "motdepasse1", "secret-unique-42")
    with SessionLocale() as db:
        e = db.scalar(select(EntreeJournal).where(EntreeJournal.evenement == "mot_de_passe_change"))
        assert e is not None and "secret-unique-42" not in e.details
        assert "motdepasse1" not in e.details


# --- RA-57 : réinitialisation par l'administrateur -----------------------------------

def test_admin_reinitialise_un_mot_de_passe(client):
    inscrire(client, "admin@exemple.ci")
    inscrire(client, "b@exemple.ci")
    with SessionLocale() as db:
        uid = db.scalar(select(Utilisateur.id).where(Utilisateur.email == "b@exemple.ci"))
    r = client.post("/api/utilisateurs/%d/mot-de-passe" % uid,
                    headers=entetes(client, "admin@exemple.ci"), json={"mot_de_passe": "temporaire-9"})
    assert r.status_code == 200 and r.json()["mot_de_passe_provisoire"] is True
    assert _connexion(client, "b@exemple.ci", "motdepasse1").status_code == 401
    assert _connexion(client, "b@exemple.ci", "temporaire-9").json()["mot_de_passe_provisoire"] is True
    with SessionLocale() as db:
        e = db.scalar(select(EntreeJournal).where(
            EntreeJournal.evenement == "mot_de_passe_reinitialise"))
        assert '"b@exemple.ci"' in e.details and "temporaire-9" not in e.details


def test_reinitialisation_reservee_aux_admins(client):
    inscrire(client, "admin@exemple.ci")
    inscrire(client, "b@exemple.ci")
    r = client.post("/api/utilisateurs/1/mot-de-passe", headers=entetes(client, "b@exemple.ci"),
                    json={"mot_de_passe": "temporaire-9"})
    assert r.status_code == 403


def test_admin_ne_reinitialise_pas_son_propre_compte(client):
    inscrire(client, "admin@exemple.ci")
    r = client.post("/api/utilisateurs/1/mot-de-passe", headers=entetes(client, "admin@exemple.ci"),
                    json={"mot_de_passe": "temporaire-9"})
    assert r.status_code == 409


# --- RA-58 : sessions fermées après changement ----------------------------------------

def test_changement_ferme_les_autres_sessions(client):
    inscrire(client, "a@exemple.ci")
    autre_poste = _connexion(client, "a@exemple.ci", "motdepasse1").json()["jeton"]
    ce_poste = _connexion(client, "a@exemple.ci", "motdepasse1").json()["jeton"]
    nouveau = _changer(client, ce_poste, "motdepasse1", "nouveau-123").json()["jeton"]
    r = client.get("/api/auth/moi", headers=_bearer(autre_poste))
    assert r.status_code == 401 and "reconnectez-vous" in r.json()["detail"]
    assert client.get("/api/auth/moi", headers=_bearer(ce_poste)).status_code == 401
    assert client.get("/api/auth/moi", headers=_bearer(nouveau)).status_code == 200


def test_reinitialisation_ferme_les_sessions_du_compte(client):
    inscrire(client, "admin@exemple.ci")
    inscrire(client, "b@exemple.ci")
    session_b = _connexion(client, "b@exemple.ci", "motdepasse1").json()["jeton"]
    client.post("/api/utilisateurs/2/mot-de-passe", headers=entetes(client, "admin@exemple.ci"),
                json={"mot_de_passe": "temporaire-9"})
    assert client.get("/api/auth/moi", headers=_bearer(session_b)).status_code == 401


def test_jeton_sans_version_reste_valide_pour_un_compte_jamais_modifie(client):
    """Les sessions ouvertes avant la mise à jour (jetons sans version) restent valides."""
    import jwt
    from datetime import datetime, timedelta, timezone
    from qatag.config import parametres
    inscrire(client, "a@exemple.ci")
    ancien = jwt.encode({"sub": "1", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
                        parametres().secret_key, algorithm="HS256")
    assert client.get("/api/auth/moi", headers=_bearer(ancien)).status_code == 200
