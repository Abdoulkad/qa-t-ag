"""RA-49 (grille QA-REV-02) et RA-50 (validation humaine des défauts)."""
from .conftest import RAPPORT_IA, US_TEST

AVEC_QC = RAPPORT_IA.replace("## Questions complémentaires\nAucune", """## Questions complémentaires
### QC-01
- **Sujet** : Nombre de demandes de réinitialisation
- **Pourquoi** : sans limite, les tests d'abus ne peuvent pas être conçus.
- **Question** : Le nombre de demandes de réinitialisation par jour est-il limité ?""")


def _creer(client, h, ia, rapport=None):
    if rapport is not None:
        ia.reponse = rapport
    r = client.post("/api/missions", json={"titre": "US-042", "texte": US_TEST}, headers=h)
    mid = r.json()["mission"]["id"]
    return mid, client.get("/api/missions/%d" % mid, headers=h).json()


def _detail(client, h, mid):
    return client.get("/api/missions/%d" % mid, headers=h).json()


def _valider(client, h, mid, codes, action, motif=""):
    defs = {d["code"]: d["id"] for d in _detail(client, h, mid)["versions"][0]["defauts"]}
    return client.put("/api/missions/%d/defauts-validation" % mid, headers=h,
                      json={"ids": [defs[c] for c in codes], "action": action, "motif": motif})


def test_constat_justification_et_questions_complementaires(client, admin, ia):
    mid, m = _creer(client, admin, ia, AVEC_QC)
    v = m["versions"][0]
    d1 = v["defauts"][0]
    assert d1["constat"] == "La durée de validité du lien n'est pas chiffrée."
    assert d1["justification"].startswith("Testabilité")
    q = {x["code"]: x for x in v["questions"]}
    assert q["Q-4"]["nature"] == "COMPLEMENTAIRE" and q["Q-4"]["bloquante"] is False
    assert q["Q-4"]["sujet"] == "Nombre de demandes de réinitialisation"
    assert q["Q-1"]["nature"] == "DEFAUT"
    # la complémentaire ne pèse pas dans le score : 100 − 25 − 10 − 3
    assert v["score_clarte"] == 62


def test_reponse_a_une_complementaire_est_une_source(client, admin, ia):
    mid, m = _creer(client, admin, ia, AVEC_QC)
    q = {x["code"]: x for x in m["versions"][0]["questions"]}
    for code, rep in (("Q-1", "30 minutes"), ("Q-4", "5 demandes par jour")):
        client.put("/api/missions/%d/questions/%d" % (mid, q[code]["id"]), json={"reponse": rep},
                   headers=admin)
    client.post("/api/missions/%d/reecriture" % mid, headers=admin)
    consigne = ia.appels[-1]["corps"]["messages"][1]["content"]
    assert "Q-4 — Question : Le nombre de demandes" in consigne
    assert "5 demandes par jour" in consigne


def test_bloquante_sans_justification_refusee(client, admin, ia):
    sans = RAPPORT_IA.replace(
        "- **Justification** : Testabilité : sans durée, aucun cas d'expiration ne peut être conçu.\n", "")
    mid, m = _creer(client, admin, ia, sans)
    assert m["statut"] == "ECHEC_ANALYSE"
    assert "DEF-001 : criticité Bloquante sans justification" in m["derniere_tache"]["erreur"]


def test_contradiction_non_qualifiee_refusee_puis_corrigee(client, admin, ia):
    flou = RAPPORT_IA.replace("Terme non défini — Majeure", "Contradiction — Majeure")
    mid, m = _creer(client, admin, ia, [flou, RAPPORT_IA])
    assert m["statut"] == "CLARIFICATION"
    relance = ia.appels[-1]["corps"]["messages"][1]["content"]
    assert "Contradiction certaine ou Contradiction apparente" in relance


def test_doublon_signale_sans_bloquer(client, admin, ia):
    double = RAPPORT_IA.replace("- **Citation** : « sécurisé »", "- **Citation** : « durée limitée »")
    double = double.replace("Terme non défini — Majeure", "Ambiguïté — Majeure")
    mid, m = _creer(client, admin, ia, double)
    assert m["statut"] == "CLARIFICATION"
    assert "Doublon signalé : DEF-002 double DEF-001" in m["versions"][0]["controle_revue"]


def test_ecarter_un_defaut_motive_question_et_score_suivent(client, admin, ia):
    mid, _ = _creer(client, admin, ia)
    r = _valider(client, admin, mid, ["DEF-001"], "ECARTER")
    assert r.status_code == 409 and r.json()["regle"] == "RA-50"
    assert _valider(client, admin, mid, ["DEF-001"], "ECARTER",
                    "Durée fixée par la politique groupe").status_code == 200
    v = _detail(client, admin, mid)["versions"][0]
    assert v["defauts"][0]["validation"] == "ECARTE"
    assert v["score_clarte"] == 87                                   # 100 − 10 − 3
    q1 = v["questions"][0]
    assert q1["decision"] == "HORS_PERIMETRE" and "Défaut écarté (DEF-001)" in q1["motif_decision"]
    # Q-1 n'est plus bloquante non traitée : la réécriture peut partir, sans DEF-001
    assert client.post("/api/missions/%d/reecriture" % mid, headers=admin).status_code == 202
    consigne = ia.appels[-1]["corps"]["messages"][1]["content"]
    assert "DEF-001" not in consigne and "DEF-002" in consigne


def test_annuler_l_ecart_restaure_question_et_score(client, admin, ia):
    mid, _ = _creer(client, admin, ia)
    _valider(client, admin, mid, ["DEF-001"], "ECARTER", "faux positif")
    _valider(client, admin, mid, ["DEF-001"], "ANNULER")
    v = _detail(client, admin, mid)["versions"][0]
    assert v["defauts"][0]["validation"] is None and v["score_clarte"] == 62
    assert v["questions"][0]["decision"] is None


def test_confirmer_par_lot_une_ligne_de_journal_par_defaut(client, admin, ia):
    mid, _ = _creer(client, admin, ia)
    assert _valider(client, admin, mid, ["DEF-001", "DEF-002", "DEF-003"], "CONFIRMER").json() == \
        {"defauts": 3}
    evts = [e["evenement"] for e in client.get("/api/missions/%d/journal" % mid,
                                               headers=admin).json()]
    assert evts.count("defaut_confirme") == 3


def test_requalifier_la_criticite_motivee(client, admin, ia):
    mid, m = _creer(client, admin, ia)
    d2 = m["versions"][0]["defauts"][1]
    url = "/api/missions/%d/defauts/%d/criticite" % (mid, d2["id"])
    assert client.put(url, json={"gravite": "Bloquante", "motif": ""},
                      headers=admin).status_code == 422
    r = client.put(url, json={"gravite": "Bloquante",
                              "motif": "Calcul financier : la politique décide du droit d'accès"},
                   headers=admin)
    assert r.json() == {"code": "DEF-002", "gravite": "Bloquante", "gravite_initiale": "Majeure"}
    v = _detail(client, admin, mid)["versions"][0]
    assert v["score_clarte"] == 47                                   # 100 − 25 − 25 − 3
    assert v["questions"][1]["bloquante"] is True
    r = client.post("/api/missions/%d/reecriture" % mid, headers=admin)
    assert r.status_code == 409 and "Q-2 : question bloquante non traitée" in r.json()["elements"]
