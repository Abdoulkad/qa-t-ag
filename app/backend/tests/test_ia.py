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


def test_requete_demande_le_flux_continu(ia):
    fournisseurs.generer("deepseek", "deepseek-flash", "SYS", "USR")
    assert ia.appels[0]["corps"]["stream"] is True


@pytest.mark.parametrize("code", ["deepseek", "anthropic"])
def test_reponse_en_flux_lue_malgre_les_keep_alive(ia, monkeypatch, code):
    monkeypatch.setattr(parametres(), "anthropic_api_key", "cle-anthropic")
    ia.flux = True
    assert fournisseurs.generer(code, "m", "s", "u") == ia.reponse


def test_coupure_reseau_retentee_puis_reussie(ia):
    import httpx
    ia.pannes = [httpx.RemoteProtocolError("Server disconnected")]
    assert fournisseurs.generer("deepseek", "m", "s", "u") == ia.reponse
    assert ia.pauses == [5] and len(ia.appels) == 2


def test_coupures_repetees_message_clair(ia):
    import httpx
    ia.pannes = [httpx.RemoteProtocolError("x") for _ in range(3)]
    with pytest.raises(fournisseurs.ErreurIA) as e:
        fournisseurs.generer("deepseek", "m", "s", "u")
    assert "connexion coupée par le serveur" in str(e.value)
    assert "échec après 3 tentatives" in str(e.value) and ia.pauses == [5, 20]


def test_surcharge_503_retentee_mais_pas_401(ia):
    ia.statut_http = 503
    with pytest.raises(fournisseurs.ErreurIA):
        fournisseurs.generer("deepseek", "m", "s", "u")
    assert len(ia.appels) == 3
    ia.appels.clear(); ia.statut_http = 401
    with pytest.raises(fournisseurs.ErreurIA):
        fournisseurs.generer("deepseek", "m", "s", "u")
    assert len(ia.appels) == 1


def test_reponse_tronquee_signalee(ia):
    import httpx
    fournisseurs.transport_http = httpx.MockTransport(lambda r: httpx.Response(200, json={
        "choices": [{"message": {"content": "ID;Titre\nCT-001;dé"}, "finish_reason": "length"}]}))
    with pytest.raises(fournisseurs.ErreurIA) as e:
        fournisseurs.generer("deepseek", "m", "s", "u")
    assert "tronqué" in str(e.value) and "IA_MAX_TOKENS" in str(e.value)


def test_longueur_de_reponse_par_fournisseur_et_reglable(ia, monkeypatch):
    fournisseurs.generer("deepseek", "m", "s", "u")
    fournisseurs.generer("ollama", "m", "s", "u")
    assert [a["corps"]["max_tokens"] for a in ia.appels] == [32768, 8192]
    monkeypatch.setattr(parametres(), "ia_max_tokens", 50000)
    fournisseurs.generer("deepseek", "m", "s", "u")
    assert ia.appels[-1]["corps"]["max_tokens"] == 50000
