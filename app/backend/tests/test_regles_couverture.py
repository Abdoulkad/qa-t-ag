"""RA-47 (règles métier séparées) et RA-48 (couverture du texte d'origine)."""
from .conftest import REECRITURE_IA, US_TEST

SANS_CA03 = REECRITURE_IA.split("### CA-03")[0]


def _mission_reecrite(client, h, ia, reecriture=SANS_CA03, reponses=("30 minutes", "8 car.")):
    r = client.post("/api/missions", json={"titre": "US-042", "texte": US_TEST}, headers=h)
    mid = r.json()["mission"]["id"]
    v = client.get("/api/missions/%d" % mid, headers=h).json()["versions"][0]
    for q, rep in zip(v["questions"], reponses):
        client.put("/api/missions/%d/questions/%d" % (mid, q["id"]), json={"reponse": rep},
                   headers=h)
    ia.reponses["reecriture"] = reecriture
    assert client.post("/api/missions/%d/reecriture" % mid, headers=h).status_code == 202
    return mid


def _detail(client, h, mid):
    return client.get("/api/missions/%d" % mid, headers=h).json()


def _pv1(client, h, mid):
    return client.post("/api/missions/%d/portes/PV-1" % mid, json={"decision": "APPROUVE"},
                       headers=h)


def test_regles_separees_sourcees_et_liees_aux_criteres(client, admin, ia):
    mid = _mission_reecrite(client, admin, ia)
    v = _detail(client, admin, mid)["versions"][0]
    assert [(r["code"], r["statut"]) for r in v["regles"]] == [("RG-01", "SOURCE"),
                                                               ("RG-02", "SOURCE")]
    assert v["regles"][1]["sources"] == ["« le nouveau mot de passe doit être sécurisé »"]
    assert v["regles"][1]["criteres"] == ["CA-02"]
    ca2 = next(c for c in v["criteres"] if c["code"] == "CA-02")
    assert ca2["regles"] == ["RG-02"] and ca2["statut"] == "SOURCE"
    assert {p["numero"]: p["statut"] for p in v["couverture"]} == {
        1: "TITRE", 2: "COUVERTE", 3: "COUVERTE", 4: "COUVERTE"}
    assert _detail(client, admin, mid)["bloquants_porte"] == []
    assert _pv1(client, admin, mid).status_code == 200


def test_regle_hypothese_rend_le_critere_hypothese(client, admin, ia):
    texte = SANS_CA03.replace("« le nouveau mot de passe doit être sécurisé »",
                              "« le nouveau mot de passe doit être sécurisé » ; Q-2")
    mid = _mission_reecrite(client, admin, ia, texte, reponses=("30 minutes",))
    m = _detail(client, admin, mid)
    assert "RG-02 : source non valable (Q-2)" in m["bloquants_porte"]
    assert "CA-02 : source non valable (Q-2, RG-02 (règle non sourcée))" in m["bloquants_porte"]
    assert _pv1(client, admin, mid).json()["regle"] == "RA-20"


def test_phrase_non_reprise_bloque_pv1_puis_justification_motivee(client, admin, ia):
    sans_rg01 = SANS_CA03.replace("« réinitialiser son mot de passe facilement » ; ", "")
    mid = _mission_reecrite(client, admin, ia, sans_rg01)
    m = _detail(client, admin, mid)
    phrase = "L'utilisateur doit pouvoir réinitialiser son mot de passe facilement."
    assert m["bloquants_porte"] == ["Phrase 2 non reprise : « %s »" % phrase]
    r = _pv1(client, admin, mid)
    assert r.status_code == 409 and r.json()["regle"] == "RA-48"
    ph2 = next(p for p in m["versions"][0]["couverture"] if p["numero"] == 2)
    url = "/api/missions/%d/phrases-justification" % mid
    assert client.put(url, json={"ids": [ph2["id"]], "motif": "  "},
                      headers=admin).json()["regle"] == "RA-48"
    assert client.put(url, json={"ids": [ph2["id"]], "motif": "Couvert par l'US-043"},
                      headers=admin).status_code == 200
    m = _detail(client, admin, mid)
    ph2 = next(p for p in m["versions"][0]["couverture"] if p["numero"] == 2)
    assert ph2["statut"] == "JUSTIFIEE" and ph2["motif"] == "Couvert par l'US-043"
    assert m["bloquants_porte"] == []
    evts = [e["evenement"] for e in client.get("/api/missions/%d/journal" % mid,
                                               headers=admin).json()]
    assert "phrase_non_reprise_justifiee" in evts
    # la justification survit à une nouvelle réécriture de la même version
    assert client.post("/api/missions/%d/reecriture" % mid, headers=admin).status_code == 202
    assert _detail(client, admin, mid)["bloquants_porte"] == []
    # et elle s'annule
    client.put(url, json={"ids": [ph2["id"]], "motif": None}, headers=admin)
    assert _detail(client, admin, mid)["bloquants_porte"] != []


def test_ecarter_une_regle_signale_ses_criteres_et_la_phrase_decouverte(client, admin, ia):
    mid = _mission_reecrite(client, admin, ia)
    rg2 = next(r for r in _detail(client, admin, mid)["versions"][0]["regles"]
               if r["code"] == "RG-02")
    url = "/api/missions/%d/regles" % mid
    assert client.request("DELETE", url, json={"ids": [rg2["id"]], "motif": ""},
                          headers=admin).status_code == 422
    r = client.request("DELETE", url, json={"ids": [rg2["id"]], "motif": "Politique hors lot"},
                       headers=admin)
    assert r.json() == {"ecartees": 1}
    bloquants = _detail(client, admin, mid)["bloquants_porte"]
    assert "CA-02 : vérifie une règle écartée (RG-02)" in bloquants
    assert any(b.startswith("Phrase 4 non reprise") for b in bloquants)
    evts = [e["evenement"] for e in client.get("/api/missions/%d/journal" % mid,
                                               headers=admin).json()]
    assert "regle_ecartee" in evts


def test_section_regles_obligatoire(client, admin, ia):
    sans = REECRITURE_IA.split("## Règles métier")[0] + "## Critères d'acceptation" + \
        REECRITURE_IA.split("## Critères d'acceptation")[1]
    r = client.post("/api/missions", json={"titre": "US-042", "texte": US_TEST}, headers=admin)
    mid = r.json()["mission"]["id"]
    q1 = _detail(client, admin, mid)["versions"][0]["questions"][0]
    client.put("/api/missions/%d/questions/%d" % (mid, q1["id"]), json={"reponse": "30 minutes"},
               headers=admin)
    ia.reponses["reecriture"] = sans
    t = client.post("/api/missions/%d/reecriture" % mid, headers=admin).json()["tache_id"]
    erreur = client.get("/api/taches/%d" % t, headers=admin).json()["erreur"]
    assert "Règles métier" in erreur


def test_conception_recoit_les_regles_et_tracabilite_rg_ca_ct(client, admin, ia):
    mid = _mission_reecrite(client, admin, ia)
    assert _pv1(client, admin, mid).status_code == 200
    consigne = ia.appels[-1]["corps"]["messages"][1]["content"]
    assert "## Règles métier validées" in consigne and "(vérifie RG-02)" in consigne
    t = client.get("/api/missions/%d/tracabilite" % mid, headers=admin).json()
    rg2 = next(r for r in t["regles"] if r["code"] == "RG-02")
    assert rg2["criteres"] == ["CA-02"] and rg2["cas"] == ["CT-003", "CT-004"]
    assert t["couverture"] == 80


def test_regle_verifiee_par_aucun_critere_bloque_pv1(client, admin, ia):
    texte = SANS_CA03.replace("- **Règles** : RG-01\n", "")
    mid = _mission_reecrite(client, admin, ia, texte)
    m = _detail(client, admin, mid)
    assert m["bloquants_porte"] == ["RG-01 : règle vérifiée par aucun critère"]
    assert _pv1(client, admin, mid).json()["regle"] == "RA-47"


def test_cadrage_de_la_user_story_non_bloquant_besoin_controle(client, admin, ia):
    """Rôle et bénéfice sont repris par la User Story réécrite ; le besoin reste contrôlé."""
    texte = ("En tant que client disposant d'un contrat d'assurance automobile,\n"
             "je veux réinitialiser son mot de passe facilement,\n"
             "afin de réparer mon véhicule sans subir de difficultés financières.\n"
             "Le lien de réinitialisation est valide pendant une durée limitée.\n"
             "REQ-001 : le nouveau mot de passe doit être sécurisé.")
    r = client.post("/api/missions", json={"titre": "US", "texte": texte}, headers=admin)
    mid = r.json()["mission"]["id"]
    q1 = _detail(client, admin, mid)["versions"][0]["questions"][0]
    client.put("/api/missions/%d/questions/%d" % (mid, q1["id"]), json={"reponse": "30 min"},
               headers=admin)
    ia.reponses["reecriture"] = SANS_CA03.replace("- **Sources** : Q-2\n", "")
    client.post("/api/missions/%d/reecriture" % mid, headers=admin)
    v = _detail(client, admin, mid)["versions"][0]
    assert [p["statut"] for p in v["couverture"]] == [
        "CADRE", "COUVERTE", "CADRE", "COUVERTE", "COUVERTE"]
    assert _detail(client, admin, mid)["bloquants_porte"] == []


def test_cas_qui_cite_une_regle_est_trace(client, admin, ia):
    """Un cas qui cite RG-02 n'est plus « sans exigence tracée » ; la règle le compte."""
    mid = _mission_reecrite(client, admin, ia)
    assert _pv1(client, admin, mid).status_code == 200
    cas = {c["code"]: c for c in client.get("/api/missions/%d/cas" % mid, headers=admin).json()}
    r = client.patch("/api/missions/%d/cas/%d" % (mid, cas["CT-003"]["id"]),
                     json={"exigence": "RG-02", "donnees_test": "Abc1234 (7 caractères)"},
                     headers=admin)
    assert r.json()["statut"] == "PRET" and r.json()["references"] == ["RG-02"]
    t = client.get("/api/missions/%d/tracabilite" % mid, headers=admin).json()
    assert "CT-003" in next(x for x in t["regles"] if x["code"] == "RG-02")["cas"]
    # RG-09 n'existe pas : référence inconnue
    r = client.patch("/api/missions/%d/cas/%d" % (mid, cas["CT-003"]["id"]),
                     json={"exigence": "RG-09"}, headers=admin)
    assert r.json()["statut"] == "INCOMPLET" and "référence inconnue : RG-09" in r.json()["motif_statut"]
