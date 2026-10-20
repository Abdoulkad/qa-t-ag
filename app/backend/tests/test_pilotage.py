"""Vue de pilotage : prochaine action et cartes « à faire », calculées par le serveur."""
from .conftest import US_TEST
from .test_conception import _jusqua_pv2


def _creer(client, h):
    r = client.post("/api/missions", json={"titre": "US-042", "texte": US_TEST}, headers=h)
    return r.json()["mission"]["id"]


def test_questions_bloquantes_et_prochaine_action(client, admin, ia):
    mid = _creer(client, admin)
    m = client.get("/api/missions/%d" % mid, headers=admin).json()
    assert m["questions_bloquantes"] == ["Q-1"]
    assert m["prochaine_action"] == "Traiter 1 question bloquante"
    p = client.get("/api/pilotage", headers=admin).json()
    assert [x["reference"] for x in p["questions_bloquantes"]] == ["M-001"]
    q1 = m["versions"][0]["questions"][0]
    client.put("/api/missions/%d/questions/%d" % (mid, q1["id"]), json={"reponse": "30 min"},
               headers=admin)
    m = client.get("/api/missions/%d" % mid, headers=admin).json()
    assert m["prochaine_action"] == "Lancer la réécriture"
    assert client.get("/api/pilotage", headers=admin).json()["questions_bloquantes"] == []


def test_agent_en_echec_et_porte_avec_points(client, admin, ia):
    ia.statut_http = 401                       # erreur définitive : pas de nouvelle tentative
    mid = _creer(client, admin)
    p = client.get("/api/pilotage", headers=admin).json()
    assert p["en_echec"][0]["en_echec"] == "analyse en échec"
    assert p["en_echec"][0]["prochaine_action"] == "Relancer l'analyse"
    ia.statut_http = 200
    mid2 = _jusqua_pv2(client, admin, ia)
    m = client.get("/api/missions/%d" % mid2, headers=admin).json()
    assert m["prochaine_action"] == "Décider PV-2 · 2 points à traiter"
    assert m["cas"] == {"total": 4, "prets": 2}


def test_pretes_pour_la_recette(client, admin, ia):
    mid = _jusqua_pv2(client, admin, ia)
    cas = {c["code"]: c for c in client.get("/api/missions/%d/cas" % mid, headers=admin).json()}
    for code in ("CT-003", "CT-004"):
        client.patch("/api/missions/%d/cas/%d" % (mid, cas[code]["id"]),
                     json={"donnees_test": "Abc1234 (7 caractères)",
                           "justification_technique": "Partition", "confirmer": True},
                     headers=admin)
    client.post("/api/missions/%d/portes/PV-2" % mid, json={"decision": "APPROUVE"}, headers=admin)
    p = client.get("/api/pilotage", headers=admin).json()
    assert [x["prochaine_action"] for x in p["pretes_recette"]] == ["Prête pour la recette"]
