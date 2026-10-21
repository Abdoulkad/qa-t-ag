"""RA-36 à RA-39 : IA configurable."""
import json

import pytest

from qatag.config import parametres
from qatag.ia import fournisseurs

from .conftest import US_TEST, entetes, inscrire


def test_cle_jamais_renvoyee_par_l_api(client, admin):
    r = client.get("/api/config-ia", headers=admin)
    assert "cle-factice" not in json.dumps(r.json())
    ds = next(f for f in r.json()["fournisseurs"] if f["code"] == "deepseek")
    assert ds["cle_presente"] is True


def test_choix_refuse_si_cle_absente(client, admin):
    r = client.put("/api/config-ia", json={"fournisseur": "anthropic", "modele": "x"}, headers=admin)
    assert r.status_code == 409 and "RA-37" in r.json()["detail"]


def test_ollama_ne_demande_pas_de_cle(client, admin):
    r = client.put("/api/config-ia", json={"fournisseur": "ollama", "modele": "llama3.1"},
                   headers=admin)
    assert r.status_code == 200
    assert r.json()["actif"] == {"fournisseur": "ollama", "modele": "llama3.1"}


def test_seul_un_admin_change_l_ia(client, admin):
    inscrire(client, "t@exemple.ci")
    r = client.put("/api/config-ia", json={"fournisseur": "ollama", "modele": "m"},
                   headers=entetes(client, "t@exemple.ci"))
    assert r.status_code == 403


def test_format_openai_compatible(ia):
    fournisseurs.generer("deepseek", "deepseek-flash", "SYS", "USR")
    appel = ia.appels[0]
    assert appel["url"] == "https://api.deepseek.com/chat/completions"
    assert appel["entetes"]["authorization"] == "Bearer cle-factice"
    assert appel["corps"]["messages"][0] == {"role": "system", "content": "SYS"}


def test_format_anthropic(ia, monkeypatch):
    monkeypatch.setattr(parametres(), "anthropic_api_key", "cle-anthropic")
    texte = fournisseurs.generer("anthropic", "claude-x", "SYS", "USR")
    appel = ia.appels[0]
    assert appel["url"] == "https://api.anthropic.com/v1/messages"
    assert appel["entetes"]["x-api-key"] == "cle-anthropic"
    assert appel["entetes"]["anthropic-version"] == "2023-06-01"
    assert appel["corps"]["system"] == "SYS"
    assert texte == ia.reponse


def test_erreur_http_remontee_sans_cle(ia):
    ia.statut_http = 401
    with pytest.raises(fournisseurs.ErreurIA) as e:
        fournisseurs.generer("deepseek", "m", "s", "u")
    assert "cle-factice" not in str(e.value)


def test_fournisseur_et_modele_enregistres_sur_la_version(client, admin, ia):
    r = client.post("/api/missions", json={"titre": "US-042", "texte": US_TEST}, headers=admin)
    m = client.get("/api/missions/%d" % r.json()["mission"]["id"], headers=admin).json()
    assert m["versions"][0]["ia"] == {"fournisseur": "deepseek", "modele": "deepseek-flash"}


def test_etat_de_tache_consultable(client, admin, ia):
    r = client.post("/api/missions", json={"titre": "US-042", "texte": US_TEST}, headers=admin)
    t = client.get("/api/taches/%d" % r.json()["tache_id"], headers=admin).json()
    assert t["etat"] == "TERMINEE" and t["type"] == "ANALYSE"


def test_echec_ia_trace_et_mission_en_echec(client, admin, ia):
    ia.statut_http = 500
    r = client.post("/api/missions", json={"titre": "US-042", "texte": US_TEST}, headers=admin)
    t = client.get("/api/taches/%d" % r.json()["tache_id"], headers=admin).json()
    assert t["etat"] == "ECHEC" and "HTTP 500" in t["erreur"]
    m = client.get("/api/missions/%d" % r.json()["mission"]["id"], headers=admin).json()
    assert m["statut"] == "ECHEC_ANALYSE"
