"""RA-51 à RA-53 : inscription fermée, limitation des connexions, en-têtes HTTP."""
import pytest
from sqlalchemy import select, text

from qatag.config import parametres
from qatag.db import SessionLocale, moteur
from qatag.models import EntreeJournal, TentativeConnexion

from .conftest import entetes, inscrire


def _connexion(client, email, mdp="motdepasse1"):
    return client.post("/api/auth/connexion", json={"email": email, "mot_de_passe": mdp})


@pytest.fixture
def inscription_fermee(monkeypatch):
    monkeypatch.setattr(parametres(), "inscription_libre", False)


# --- RA-51 : inscription ------------------------------------------------------

def test_premier_compte_toujours_possible(client, inscription_fermee):
    assert client.get("/api/auth/etat").json() == {"inscription_ouverte": True}
    inscrire(client, "admin@exemple.ci")
    assert client.get("/api/auth/etat").json() == {"inscription_ouverte": False}


def test_inscription_fermee_apres_le_premier_compte(client, inscription_fermee):
    inscrire(client, "admin@exemple.ci")
    r = client.post("/api/auth/inscription",
                    json={"email": "intrus@exemple.ci", "mot_de_passe": "motdepasse1"})
    assert r.status_code == 403
    assert "administrateur" in r.json()["detail"]


def test_administrateur_cree_toujours_les_comptes(client, inscription_fermee):
    inscrire(client, "admin@exemple.ci")
    r = client.post("/api/utilisateurs", headers=entetes(client, "admin@exemple.ci"),
                    json={"email": "b@exemple.ci", "mot_de_passe": "motdepasse1",
                          "roles": ["ANALYSTE"]})
    assert r.status_code == 201
    assert _connexion(client, "b@exemple.ci").status_code == 200


def test_inscription_libre_si_configuree(client):
    inscrire(client, "admin@exemple.ci")
    assert client.get("/api/auth/etat").json() == {"inscription_ouverte": True}
    inscrire(client, "b@exemple.ci")


def test_inscription_libre_desactivee_par_defaut():
    from qatag.config import Parametres
    assert Parametres.model_fields["inscription_libre"].default is False


# --- RA-52 : limitation des tentatives ------------------------------------------

def test_blocage_apres_cinq_echecs_meme_avec_le_bon_mot_de_passe(client):
    inscrire(client, "a@exemple.ci")
    for _ in range(5):
        assert _connexion(client, "a@exemple.ci", "mauvais-mdp").status_code == 401
    r = _connexion(client, "a@exemple.ci")
    assert r.status_code == 429
    assert "Réessayez dans 15 minutes" in r.json()["detail"]
    assert r.headers["Retry-After"] == "900"


def test_quatre_echecs_ne_bloquent_pas(client):
    inscrire(client, "a@exemple.ci")
    for _ in range(4):
        _connexion(client, "a@exemple.ci", "mauvais-mdp")
    assert _connexion(client, "a@exemple.ci").status_code == 200


def test_reussite_remet_le_compteur_a_zero(client):
    inscrire(client, "a@exemple.ci")
    for _ in range(4):
        _connexion(client, "a@exemple.ci", "mauvais-mdp")
    assert _connexion(client, "a@exemple.ci").status_code == 200
    for _ in range(4):
        _connexion(client, "a@exemple.ci", "mauvais-mdp")
    assert _connexion(client, "a@exemple.ci").status_code == 200


def test_blocage_leve_quand_les_echecs_sortent_de_la_fenetre(client):
    inscrire(client, "a@exemple.ci")
    for _ in range(5):
        _connexion(client, "a@exemple.ci", "mauvais-mdp")
    assert _connexion(client, "a@exemple.ci").status_code == 429
    with moteur.begin() as c:     # on vieillit les échecs de 16 minutes
        c.execute(text("UPDATE tentative_connexion SET horodatage = horodatage - interval '16 minutes'"))
    assert _connexion(client, "a@exemple.ci").status_code == 200


def test_compte_inconnu_bloque_comme_un_compte_existant(client):
    """Même réponse que le compte existe ou non : le blocage ne révèle rien."""
    for _ in range(5):
        assert _connexion(client, "personne@exemple.ci", "mauvais-mdp").status_code == 401
    assert _connexion(client, "personne@exemple.ci", "mauvais-mdp").status_code == 429


def test_blocage_d_un_compte_n_empeche_pas_les_autres(client):
    inscrire(client, "a@exemple.ci")
    inscrire(client, "b@exemple.ci")
    for _ in range(5):
        _connexion(client, "a@exemple.ci", "mauvais-mdp")
    assert _connexion(client, "a@exemple.ci").status_code == 429
    assert _connexion(client, "b@exemple.ci").status_code == 200


def test_limite_par_adresse_ip(client, monkeypatch):
    """Une même adresse qui essaie de nombreux e-mails est bloquée."""
    monkeypatch.setattr(parametres(), "connexion_essais_max_ip", 6)
    inscrire(client, "a@exemple.ci")
    for i in range(6):
        _connexion(client, "essai%d@exemple.ci" % i, "mauvais-mdp")
    assert _connexion(client, "a@exemple.ci").status_code == 429


def test_blocage_inscrit_au_journal(client):
    inscrire(client, "a@exemple.ci")
    for _ in range(5):
        _connexion(client, "a@exemple.ci", "mauvais-mdp")
    with SessionLocale() as db:
        entrees = db.scalars(select(EntreeJournal).where(
            EntreeJournal.evenement == "connexion_bloquee")).all()
        assert len(entrees) == 1
        assert '"a@exemple.ci"' in entrees[0].details


def test_traces_anciennes_purgees(client):
    with moteur.begin() as c:
        c.execute(text("INSERT INTO tentative_connexion (email, ip, reussie, horodatage) "
                       "VALUES ('vieux@exemple.ci', '1.2.3.4', false, now() - interval '31 days')"))
    _connexion(client, "x@exemple.ci", "mauvais-mdp")
    with SessionLocale() as db:
        emails = db.scalars(select(TentativeConnexion.email)).all()
        assert emails == ["x@exemple.ci"]


def test_mot_de_passe_jamais_trace(client):
    _connexion(client, "a@exemple.ci", "secret-tres-unique")
    with moteur.begin() as c:
        ligne = c.execute(text("SELECT * FROM tentative_connexion")).one()
        assert "secret-tres-unique" not in str(tuple(ligne))


# --- RA-53 : en-têtes HTTP --------------------------------------------------------

def test_entetes_de_securite_sur_l_api(client):
    r = client.get("/api/sante")
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"
    assert r.headers["Referrer-Policy"] == "no-referrer"
    assert "frame-ancestors 'none'" in r.headers["Content-Security-Policy"]
    assert "script-src 'self';" in r.headers["Content-Security-Policy"]
    assert r.headers["Cache-Control"] == "no-store"


def test_entetes_presents_meme_sur_une_erreur(client):
    r = client.get("/api/auth/moi")
    assert r.status_code == 401
    assert r.headers["X-Frame-Options"] == "DENY"


def test_documentation_api_garde_son_cdn(client):
    r = client.get("/docs")
    assert r.status_code == 200
    # Lecture directive par directive : sources autorisées de chaque directive
    directives = {d.split()[0]: d.split()[1:]
                  for d in r.headers["Content-Security-Policy"].split(";") if d.strip()}
    assert "https://cdn.jsdelivr.net" in directives["script-src"]
    assert directives["frame-ancestors"] == ["'none'"]


def test_hsts_seulement_en_https(client):
    assert "Strict-Transport-Security" not in client.get("/api/sante").headers
    from fastapi.testclient import TestClient
    from qatag.main import app
    with TestClient(app, base_url="https://testserver") as c:
        assert c.get("/api/sante").headers["Strict-Transport-Security"] == "max-age=31536000"


def test_fenetre_par_defaut():
    p = parametres()
    assert (p.connexion_essais_max, p.connexion_essais_max_ip,
            p.connexion_fenetre_minutes) == (5, 20, 15)
