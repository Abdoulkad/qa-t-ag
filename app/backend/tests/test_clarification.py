"""RA-18 à RA-21 : cycle Analyser → Clarifier → Réécrire → Valider."""
from .conftest import US_TEST, entetes, inscrire


def _mission(client, h):
    r = client.post("/api/missions", json={"titre": "US-042", "texte": US_TEST}, headers=h)
    return r.json()["mission"]["id"]


def _detail(client, h, mid):
    return client.get("/api/missions/%d" % mid, headers=h).json()


def _repondre(client, h, mid, code, texte):
    q = next(q for q in _detail(client, h, mid)["versions"][-1]["questions"] if q["code"] == code)
    return client.put("/api/missions/%d/questions/%d" % (mid, q["id"]),
                      json={"reponse": texte}, headers=h)


def test_questions_numerotees(client, admin, ia):
    v = _detail(client, admin, _mission(client, admin))["versions"][0]
    assert [q["code"] for q in v["questions"]] == ["Q-1", "Q-2", "Q-3"]


def test_reponse_tracee_auteur_et_date(client, admin, ia):
    mid = _mission(client, admin)
    r = _repondre(client, admin, mid, "Q-1", "30 minutes")
    assert r.status_code == 200 and r.json()["repondu_le"]
    q = _detail(client, admin, mid)["versions"][0]["questions"][0]
    assert q["reponse"] == "30 minutes" and q["repondu_par_id"] == 1
    evts = [e["evenement"] for e in client.get("/api/missions/%d/journal" % mid,
                                               headers=admin).json()]
    assert "question_repondue" in evts


def test_reecriture_refusee_si_question_bloquante_sans_reponse(client, admin, ia):
    mid = _mission(client, admin)
    r = client.post("/api/missions/%d/reecriture" % mid, headers=admin)
    assert r.status_code == 409 and r.json()["regle"] == "RA-21"
    assert r.json()["elements"] == ["Q-1 : question bloquante sans réponse"]


def test_reecriture_sources_verifiees_par_script(client, admin, ia):
    mid = _mission(client, admin)
    _repondre(client, admin, mid, "Q-1", "30 minutes")         # Q-2 reste sans réponse
    r = client.post("/api/missions/%d/reecriture" % mid, headers=admin)
    assert r.status_code == 202
    m = _detail(client, admin, mid)
    assert m["statut"] == "ATTENTE_PV1"
    criteres = {c["code"]: c for c in m["versions"][0]["criteres"]}
    assert criteres["CA-01"]["statut"] == "SOURCE"
    assert criteres["CA-01"]["sources"] == ["« durée limitée »", "Q-1"]
    # Q-2 n'a pas de réponse : ce n'est pas une source (RA-19)
    assert criteres["CA-02"]["statut"] == "HYPOTHESE"
    assert criteres["CA-02"]["sources_rejetees"] == ["Q-2"]
    # CA-03 inventé (SMS) : hypothèse (RA-20)
    assert criteres["CA-03"]["statut"] == "HYPOTHESE"
    assert m["versions"][0]["texte_reecrit"].startswith("En tant qu'utilisateur")


def test_pv1_bloque_puis_debloque_en_traitant_les_hypotheses(client, admin, ia):
    mid = _mission(client, admin)
    _repondre(client, admin, mid, "Q-1", "30 minutes")
    client.post("/api/missions/%d/reecriture" % mid, headers=admin)
    m = _detail(client, admin, mid)
    assert m["bloquants_porte"] == ["CA-02 : critère sans source (hypothèse)",
                                    "CA-03 : critère sans source (hypothèse)"]
    # L'humain répond à Q-2 puis relance la réécriture : CA-02 devient sourcé
    assert _repondre(client, admin, mid, "Q-2", "8 caractères minimum").status_code == 200
    assert client.post("/api/missions/%d/reecriture" % mid, headers=admin).status_code == 202
    m = _detail(client, admin, mid)
    assert m["bloquants_porte"] == ["CA-03 : critère sans source (hypothèse)"]
    # L'humain écarte CA-03, motif obligatoire
    ca3 = next(c for c in m["versions"][0]["criteres"] if c["code"] == "CA-03")
    url = "/api/missions/%d/criteres/%d" % (mid, ca3["id"])
    assert client.request("DELETE", url, json={"motif": ""}, headers=admin).status_code == 422
    assert client.request("DELETE", url, json={"motif": "Pas de SMS dans le périmètre"},
                          headers=admin).status_code == 200
    assert _detail(client, admin, mid)["bloquants_porte"] == []
    r = client.post("/api/missions/%d/portes/PV-1" % mid, json={"decision": "APPROUVE"},
                    headers=admin)
    assert r.status_code == 200


def test_precision_humaine_utilisable_comme_source(client, admin, ia):
    mid = _mission(client, admin)
    _repondre(client, admin, mid, "Q-1", "30 minutes")
    r = client.post("/api/missions/%d/questions" % mid,
                    json={"question": "Notification ?", "reponse": "SMS de confirmation"},
                    headers=admin)
    assert r.status_code == 201 and r.json()["code"] == "Q-4"
    ia.reponses["reecriture"] = ia.reponses["reecriture"].replace(
        "- **Sources** :\n", "- **Sources** : Q-4\n")
    client.post("/api/missions/%d/reecriture" % mid, headers=admin)
    criteres = {c["code"]: c["statut"] for c in _detail(client, admin, mid)["versions"][0]["criteres"]}
    assert criteres["CA-03"] == "SOURCE"


def test_reecriture_mal_formee_retour_en_clarification(client, admin, ia):
    mid = _mission(client, admin)
    _repondre(client, admin, mid, "Q-1", "30 minutes")
    ia.reponses["reecriture"] = "Voici ma proposition libre."
    r = client.post("/api/missions/%d/reecriture" % mid, headers=admin)
    t = client.get("/api/taches/%d" % r.json()["tache_id"], headers=admin).json()
    assert t["etat"] == "ECHEC" and "mal formée" in t["erreur"]
    assert _detail(client, admin, mid)["statut"] == "CLARIFICATION"


def test_reponse_impossible_hors_clarification(client, admin, ia):
    ia.statut_http = 500
    mid = _mission(client, admin)                               # ECHEC_ANALYSE
    r = client.post("/api/missions/%d/questions" % mid,
                    json={"question": "q", "reponse": "r"}, headers=admin)
    assert r.status_code == 409 and r.json()["regle"] == "RA-11"


def test_analyste_non_participant_ne_peut_pas_repondre(client, admin, ia):
    mid = _mission(client, admin)
    inscrire(client, "t@exemple.ci")
    r = client.post("/api/missions/%d/questions" % mid, json={"question": "q", "reponse": "r"},
                    headers=entetes(client, "t@exemple.ci"))
    assert r.status_code == 404


def test_format_rejete_puis_corrige_a_la_seconde_tentative(client, admin, ia):
    from .conftest import REECRITURE_IA
    mid = _mission(client, admin)
    _repondre(client, admin, mid, "Q-1", "30 minutes")
    ia.reponses["reecriture"] = ["Voici ma proposition libre.", REECRITURE_IA]
    client.post("/api/missions/%d/reecriture" % mid, headers=admin)
    assert _detail(client, admin, mid)["statut"] == "ATTENTE_PV1"
    relance = ia.appels[-1]["corps"]["messages"][1]["content"]
    assert "REJETÉE par le script de contrôle" in relance


def test_echec_cite_le_debut_de_la_reponse(client, admin, ia):
    mid = _mission(client, admin)
    _repondre(client, admin, mid, "Q-1", "30 minutes")
    ia.reponses["reecriture"] = "Voici ma proposition libre."
    r = client.post("/api/missions/%d/reecriture" % mid, headers=admin)
    t = client.get("/api/taches/%d" % r.json()["tache_id"], headers=admin).json()
    assert "après 2 tentatives" in t["erreur"] and "Voici ma proposition libre" in t["erreur"]


def test_titres_en_forme_libre_acceptes_sources_toujours_verifiees(client, admin, ia):
    mid = _mission(client, admin)
    _repondre(client, admin, mid, "Q-1", "30 minutes")
    ia.reponses["reecriture"] = (ia.reponses["reecriture"]
                                 .replace("## Exigence réécrite", "### 1. **Exigence réécrite :**")
                                 .replace("## Critères d'acceptation", "## Critères d’acceptation"))
    client.post("/api/missions/%d/reecriture" % mid, headers=admin)
    m = _detail(client, admin, mid)
    assert m["statut"] == "ATTENTE_PV1"
    statuts = {c["code"]: c["statut"] for c in m["versions"][0]["criteres"]}
    assert statuts == {"CA-01": "SOURCE", "CA-02": "HYPOTHESE", "CA-03": "HYPOTHESE"}
