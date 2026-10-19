"""RA-42 à RA-44 : décisions sur les questions, points ouverts, traitement groupé."""
from .conftest import REECRITURE_IA, US_TEST


def _mission(client, h):
    r = client.post("/api/missions", json={"titre": "US-042", "texte": US_TEST}, headers=h)
    return r.json()["mission"]["id"]


def _detail(client, h, mid):
    return client.get("/api/missions/%d" % mid, headers=h).json()


def _questions(client, h, mid):
    return {q["code"]: q for q in _detail(client, h, mid)["versions"][-1]["questions"]}


def _decider(client, h, mid, codes, decision, motif="motif"):
    qs = _questions(client, h, mid)
    return client.put("/api/missions/%d/questions-decision" % mid, headers=h,
                      json={"ids": [qs[c]["id"] for c in codes], "decision": decision,
                            "motif": motif})


def test_question_bloquante_reportee_debloque_la_reecriture(client, admin, ia):
    mid = _mission(client, admin)
    assert _decider(client, admin, mid, ["Q-1"], "REPORTEE", "Attente du PO").status_code == 200
    assert client.post("/api/missions/%d/reecriture" % mid, headers=admin).status_code == 202
    q1 = _questions(client, admin, mid)["Q-1"]
    assert q1["decision"] == "REPORTEE" and q1["motif_decision"] == "Attente du PO"


def test_decision_sans_motif_refusee(client, admin, ia):
    mid = _mission(client, admin)
    r = _decider(client, admin, mid, ["Q-1"], "HORS_PERIMETRE", "  ")
    assert r.status_code == 409 and r.json()["regle"] == "RA-42"


def test_decision_groupee_une_ligne_de_journal_par_question(client, admin, ia):
    mid = _mission(client, admin)
    assert _decider(client, admin, mid, ["Q-2", "Q-3"], "HORS_PERIMETRE",
                    "Hors lot 1").json() == {"questions": 2}
    evts = [e for e in client.get("/api/missions/%d/journal" % mid, headers=admin).json()
            if e["evenement"] == "question_decidee"]
    assert sorted(e["details"]["question"] for e in evts) == ["Q-2", "Q-3"]


def test_decision_refusee_sur_question_repondue_et_reponse_remplace_decision(client, admin, ia):
    mid = _mission(client, admin)
    qs = _questions(client, admin, mid)
    client.put("/api/missions/%d/questions/%d" % (mid, qs["Q-1"]["id"]),
               json={"reponse": "30 minutes"}, headers=admin)
    r = _decider(client, admin, mid, ["Q-1"], "REPORTEE")
    assert r.status_code == 409 and r.json()["elements"] == ["Q-1 : déjà répondue"]
    _decider(client, admin, mid, ["Q-2"], "REPORTEE")
    client.put("/api/missions/%d/questions/%d" % (mid, qs["Q-2"]["id"]),
               json={"reponse": "8 caractères"}, headers=admin)
    assert _questions(client, admin, mid)["Q-2"]["decision"] is None


def test_annuler_une_decision(client, admin, ia):
    mid = _mission(client, admin)
    _decider(client, admin, mid, ["Q-3"], "HORS_PERIMETRE")
    _decider(client, admin, mid, ["Q-3"], None, "")
    assert _questions(client, admin, mid)["Q-3"]["decision"] is None


def test_consigne_distingue_hors_perimetre_et_reportees(client, admin, ia):
    mid = _mission(client, admin)
    qs = _questions(client, admin, mid)
    client.put("/api/missions/%d/questions/%d" % (mid, qs["Q-1"]["id"]),
               json={"reponse": "30 minutes"}, headers=admin)
    _decider(client, admin, mid, ["Q-2"], "HORS_PERIMETRE")
    _decider(client, admin, mid, ["Q-3"], "REPORTEE")
    client.post("/api/missions/%d/reecriture" % mid, headers=admin)
    consigne = ia.appels[-1]["corps"]["messages"][1]["content"]
    hors, ouvertes = consigne.split("HORS PÉRIMÈTRE")[1].split("Questions sans réponse ou reportées")
    assert "Q-2" in hors and "Q-3" in ouvertes and "(reportée)" in ouvertes


def test_points_ouverts_ne_bloquent_pas_pv1_et_sont_conserves(client, admin, ia):
    mid = _mission(client, admin)
    qs = _questions(client, admin, mid)
    for code, rep in (("Q-1", "30 minutes"), ("Q-2", "8 caractères minimum")):
        client.put("/api/missions/%d/questions/%d" % (mid, qs[code]["id"]),
                   json={"reponse": rep}, headers=admin)
    ia.reponses["reecriture"] = (REECRITURE_IA.split("### CA-03")[0] +
                                 "\n## Points ouverts\n- Mesure de « facilement » (Q-3)\n")
    client.post("/api/missions/%d/reecriture" % mid, headers=admin)
    m = _detail(client, admin, mid)
    assert m["versions"][0]["points_ouverts"] == ["Mesure de « facilement » (Q-3)"]
    assert m["bloquants_porte"] == []
    assert [c["code"] for c in m["versions"][0]["criteres"]] == ["CA-01", "CA-02"]


def test_ecarter_plusieurs_hypotheses_en_une_fois(client, admin, ia):
    mid = _mission(client, admin)
    qs = _questions(client, admin, mid)
    client.put("/api/missions/%d/questions/%d" % (mid, qs["Q-1"]["id"]),
               json={"reponse": "30 minutes"}, headers=admin)
    client.post("/api/missions/%d/reecriture" % mid, headers=admin)
    crits = _detail(client, admin, mid)["versions"][0]["criteres"]
    hyp = [c["id"] for c in crits if c["statut"] == "HYPOTHESE"]
    assert len(hyp) == 2
    r = client.request("DELETE", "/api/missions/%d/criteres" % mid, headers=admin,
                       json={"ids": hyp, "motif": "Hors périmètre du lot"})
    assert r.json() == {"ecartes": 2}
    assert _detail(client, admin, mid)["bloquants_porte"] == []
    evts = [e for e in client.get("/api/missions/%d/journal" % mid, headers=admin).json()
            if e["evenement"] == "critere_ecarte"]
    assert len(evts) == 2


def test_source_valide_ne_couvre_pas_une_question_reportee(client, admin, ia):
    """Faille corrigée (RA-20) : CA-01 cite « durée limitée » (valide) et Q-1
    (reportée). Les « 30 minutes » ne reposent sur rien : hypothèse, PV-1 bloqué."""
    mid = _mission(client, admin)
    _decider(client, admin, mid, ["Q-1"], "REPORTEE", "Attente du PO")
    client.post("/api/missions/%d/reecriture" % mid, headers=admin)
    m = _detail(client, admin, mid)
    ca1 = next(c for c in m["versions"][0]["criteres"] if c["code"] == "CA-01")
    assert ca1["statut"] == "HYPOTHESE"
    assert ca1["sources"] == ["« durée limitée »"] and ca1["sources_rejetees"] == ["Q-1"]
    assert "CA-01 : source non valable (Q-1)" in m["bloquants_porte"]
    r = client.post("/api/missions/%d/portes/PV-1" % mid, json={"decision": "APPROUVE"},
                    headers=admin)
    assert r.status_code == 409 and r.json()["regle"] == "RA-20"
