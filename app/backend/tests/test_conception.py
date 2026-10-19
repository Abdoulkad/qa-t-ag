"""RA-22 à RA-26, RA-41 : conception des cas, statuts calculés, traçabilité, PV-2."""
from qatag.regles import statut_cas

from .conftest import US_TEST


def _jusqua_pv2(client, h, ia):
    r = client.post("/api/missions", json={"titre": "US-042", "texte": US_TEST}, headers=h)
    mid = r.json()["mission"]["id"]
    v = client.get("/api/missions/%d" % mid, headers=h).json()["versions"][0]
    for q, rep in zip(v["questions"], ("30 minutes", "8 caractères minimum")):
        client.put("/api/missions/%d/questions/%d" % (mid, q["id"]), json={"reponse": rep},
                   headers=h)
    ia.reponses["reecriture"] = ia.reponses["reecriture"].split("### CA-03")[0]
    client.post("/api/missions/%d/reecriture" % mid, headers=h)
    r = client.post("/api/missions/%d/portes/PV-1" % mid, json={"decision": "APPROUVE"}, headers=h)
    assert r.status_code == 200, r.text
    return mid


def _cas(client, h, mid):
    return {c["code"]: c for c in client.get("/api/missions/%d/cas" % mid, headers=h).json()}


def test_pv1_lance_la_conception_puis_attente_pv2(client, admin, ia):
    mid = _jusqua_pv2(client, admin, ia)
    m = client.get("/api/missions/%d" % mid, headers=admin).json()
    assert m["statut"] == "ATTENTE_PV2"
    assert len(_cas(client, admin, mid)) == 4


def test_technique_normalisee_et_justifiee(client, admin, ia):
    cas = _cas(client, admin, _jusqua_pv2(client, admin, ia))
    assert cas["CT-002"]["technique"] == "valeurs limites"          # « Valeurs Limites »
    assert "29 min" in cas["CT-002"]["justification_technique"]


def test_statuts_calcules_pas_choisis_par_l_ia(client, admin, ia):
    cas = _cas(client, admin, _jusqua_pv2(client, admin, ia))
    assert cas["CT-001"]["statut"] == "PRET"
    # données « mot de passe valide » : pas concrètes, même si l'IA a écrit OK (RA-23)
    assert cas["CT-003"]["statut"] == "INCOMPLET"
    assert "non concrètes" in cas["CT-003"]["motif_statut"]
    # CT-004 : l'IA le signale à clarifier ET sa technique n'est pas justifiée
    assert cas["CT-004"]["statut"] == "A_CLARIFIER"
    assert "technique non justifiée" in cas["CT-004"]["motif_statut"]


def test_tracabilite_et_couverture(client, admin, ia):
    mid = _jusqua_pv2(client, admin, ia)
    t = client.get("/api/missions/%d/tracabilite" % mid, headers=admin).json()
    matrice = {ligne["reference"]: ligne["cas"] for ligne in t["matrice"]}
    assert matrice["CA-01"] == ["CT-001", "CT-002"]
    assert matrice["CA-02"] == ["CT-003", "CT-004"]
    assert matrice["REQ-001"] == []          # REQ de l'origine non citée par un cas
    assert t["couverture"] == 67
    assert t["par_technique"] == {"valeurs limites": 3, "partitions d'équivalence": 1}


def test_pv2_bloque_puis_correction_humaine(client, admin, ia):
    mid = _jusqua_pv2(client, admin, ia)
    r = client.post("/api/missions/%d/portes/PV-2" % mid, json={"decision": "APPROUVE"},
                    headers=admin)
    assert r.status_code == 409 and r.json()["regle"] == "RA-26"
    assert r.json()["elements"] == ["CT-003 : cas incomplet", "CT-004 : cas à clarifier"]

    cas = _cas(client, admin, mid)
    url = "/api/missions/%d/cas/%d" % (mid, cas["CT-003"]["id"])
    r = client.patch(url, json={"donnees_test": "Abc1234 (7 caractères)"}, headers=admin)
    assert r.status_code == 200, r.text
    assert r.json()["statut"] == "PRET"

    url = "/api/missions/%d/cas/%d" % (mid, cas["CT-004"]["id"])
    r = client.patch(url, json={"justification_technique": "Partition valide : 8 caractères"},
                     headers=admin)
    assert r.json()["statut"] == "A_CLARIFIER"       # pas encore confirmé par l'humain
    r = client.patch(url, json={"confirmer": True}, headers=admin)
    assert r.json()["statut"] == "PRET" and r.json()["confirme_par_id"] == 1

    r = client.post("/api/missions/%d/portes/PV-2" % mid, json={"decision": "APPROUVE"},
                    headers=admin)
    assert r.status_code == 200 and r.json()["statut_mission"] == "VALIDEE"
    evts = [e["evenement"] for e in client.get("/api/missions/%d/journal" % mid,
                                               headers=admin).json()]
    assert evts.count("cas_modifie") == 3


def test_pv2_bloque_si_un_critere_n_est_couvert_par_aucun_cas(client, admin, ia):
    ia.reponses["conception"] = "\n".join(
        line for line in ia.reponses["conception"].splitlines()
        if not line.startswith(("CT-003", "CT-004")))
    mid = _jusqua_pv2(client, admin, ia)
    r = client.post("/api/missions/%d/portes/PV-2" % mid, json={"decision": "APPROUVE"},
                    headers=admin)
    assert r.json()["elements"] == ["CA-02 : critère non couvert par un cas"]


def test_conception_mal_formee_relancable(client, admin, ia):
    ia.reponses["conception"] = "Pas de CSV ici."
    mid = _jusqua_pv2(client, admin, ia)
    m = client.get("/api/missions/%d" % mid, headers=admin).json()
    assert m["statut"] == "CONCEPTION"
    from .conftest import CONCEPTION_IA
    ia.reponses["conception"] = CONCEPTION_IA
    r = client.post("/api/missions/%d/relancer" % mid, headers=admin)
    assert r.status_code == 202
    assert client.get("/api/missions/%d" % mid, headers=admin).json()["statut"] == "ATTENTE_PV2"


def test_cas_non_modifiable_apres_pv2(client, admin, ia):
    mid = _jusqua_pv2(client, admin, ia)
    cas = _cas(client, admin, mid)
    for code in ("CT-003", "CT-004"):
        client.patch("/api/missions/%d/cas/%d" % (mid, cas[code]["id"]),
                     json={"donnees_test": "Abc1234", "justification_technique": "j",
                           "confirmer": True}, headers=admin)
    client.post("/api/missions/%d/portes/PV-2" % mid, json={"decision": "APPROUVE"}, headers=admin)
    r = client.patch("/api/missions/%d/cas/%d" % (mid, cas["CT-001"]["id"]),
                     json={"titre": "x"}, headers=admin)
    assert r.status_code == 409


def test_suivi_des_cas(client, admin, ia):
    _jusqua_pv2(client, admin, ia)
    r = client.get("/api/cas", headers=admin).json()
    assert r["total"] == 4
    assert r["par_statut"] == {"PRET": 2, "INCOMPLET": 1, "A_CLARIFIER": 1}
    assert client.get("/api/cas?q=expiré", headers=admin).json()["total"] == 1
    assert client.get("/api/cas?statut=PRET", headers=admin).json()["total"] == 2


def test_regle_statut_cas_unitaire():
    assert statut_cas("p", "Sans objet", "r", "OK") == ("PRET", "")
    assert statut_cas("p", "{login}", "r", "OK")[0] == "INCOMPLET"
    assert statut_cas("p", "tomsmith", "à définir", "OK")[0] == "INCOMPLET"
