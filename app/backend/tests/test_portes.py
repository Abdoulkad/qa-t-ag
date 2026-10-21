"""RA-12 à RA-16, RA-20, RA-26 : Human Gates.

Le passage CLARIFICATION → ATTENTE_PV1 arrive au lot 2 (réécriture) : ici on
place la mission dans le statut voulu directement en base.
"""
from qatag.db import SessionLocale
from qatag.models import CasTest, CritereAcceptation, Mission

from .conftest import US_TEST, entetes, inscrire


def _mission_en_attente(client, h, statut="ATTENTE_PV1"):
    r = client.post("/api/missions", json={"titre": "US", "texte": US_TEST}, headers=h)
    mid = r.json()["mission"]["id"]
    with SessionLocale() as db:
        db.get(Mission, mid).statut = statut
        db.commit()
    return mid


def _ajouter_cas(mid, statuts):
    with SessionLocale() as db:
        m = db.get(Mission, mid)
        for i, s in enumerate(statuts, 1):
            db.add(CasTest(version_id=m.versions[-1].id, code="CT-%03d" % i, titre="t", statut=s))
        db.commit()


def _decider(client, h, mid, porte="PV-1", decision="APPROUVE", commentaire=""):
    return client.post("/api/missions/%d/portes/%s" % (mid, porte),
                       json={"decision": decision, "commentaire": commentaire}, headers=h)


def test_acteur_unique_peut_s_auto_valider_et_c_est_trace(client, ia):
    inscrire(client, "seul@exemple.ci")
    u = client.patch  # noqa: F841
    h = entetes(client, "seul@exemple.ci")
    client.put("/api/config-ia", json={"fournisseur": "deepseek", "modele": "m"}, headers=h)
    mid = _mission_en_attente(client, h)
    r = _decider(client, h, mid)
    assert r.status_code == 200, r.text
    assert r.json()["auto_validation"] is True
    journal = client.get("/api/missions/%d/journal" % mid, headers=h).json()
    porte = [e for e in journal if e["evenement"] == "porte_decidee"][0]
    assert porte["details"]["auto_validation"] is True


def test_acteur_unique_sans_role_superviseur_peut_quand_meme_decider(client, admin, ia):
    inscrire(client, "analyste@exemple.ci")
    h = entetes(client, "analyste@exemple.ci")
    mid = _mission_en_attente(client, h)
    assert _decider(client, h, mid).status_code == 200


def test_plusieurs_participants_il_faut_un_superviseur(client, admin, ia):
    inscrire(client, "a1@exemple.ci")
    inscrire(client, "a2@exemple.ci")
    h1, h2 = entetes(client, "a1@exemple.ci"), entetes(client, "a2@exemple.ci")
    mid = _mission_en_attente(client, h1)
    client.post("/api/missions/%d/participants" % mid, json={"email": "a2@exemple.ci"}, headers=h1)
    r = _decider(client, h2, mid)
    assert r.status_code == 409 and r.json()["regle"] == "RA-12"


def test_auteur_ne_valide_pas_son_travail_a_plusieurs(client, admin, ia):
    inscrire(client, "a2@exemple.ci")
    mid = _mission_en_attente(client, admin)          # admin = auteur, et superviseur
    client.post("/api/missions/%d/participants" % mid, json={"email": "a2@exemple.ci"},
                headers=admin)
    r = _decider(client, admin, mid)
    assert r.status_code == 409 and r.json()["regle"] == "RA-13"


def test_superviseur_non_auteur_decide_sans_auto_validation(client, admin, ia):
    inscrire(client, "a1@exemple.ci")
    h1 = entetes(client, "a1@exemple.ci")
    mid = _mission_en_attente(client, h1)
    client.post("/api/missions/%d/participants" % mid, json={"email": "bamk@exemple.ci"},
                headers=h1)
    r = _decider(client, admin, mid)
    assert r.status_code == 200 and r.json()["auto_validation"] is False


def test_rejet_sans_commentaire_refuse(client, admin, ia):
    mid = _mission_en_attente(client, admin)
    r = _decider(client, admin, mid, decision="REJETE", commentaire="  ")
    assert r.status_code == 409 and r.json()["regle"] == "RA-15"


def test_rejet_puis_correction_par_nouvelle_version(client, admin, ia):
    mid = _mission_en_attente(client, admin)
    r = _decider(client, admin, mid, decision="REJETE", commentaire="Durée non précisée")
    assert r.json()["statut_mission"] == "A_CORRIGER"
    # RA-16 : plus aucune décision sur la version rejetée
    assert _decider(client, admin, mid).status_code == 409
    r = client.post("/api/missions/%d/versions" % mid,
                    json={"texte": US_TEST + "Le lien expire après 30 minutes."}, headers=admin)
    assert r.status_code == 201 and r.json()["version"] == 2
    m = client.get("/api/missions/%d" % mid, headers=admin).json()
    assert m["versions"][0]["figee"] is True
    assert m["versions"][0]["decisions"][0]["decision"] == "REJETE"


def test_pv1_bloque_par_une_hypothese(client, admin, ia):
    mid = _mission_en_attente(client, admin)
    with SessionLocale() as db:
        v = db.get(Mission, mid).versions[-1]
        db.add(CritereAcceptation(version_id=v.id, code="CA-01", texte="x", sources=[],
                                  statut="HYPOTHESE"))
        db.commit()
    r = _decider(client, admin, mid)
    assert r.status_code == 409 and r.json()["regle"] == "RA-20"
    assert r.json()["elements"] == ["CA-01 : critère sans source (hypothèse)"]


def test_pv2_bloque_par_cas_a_clarifier_ou_incomplets(client, admin, ia):
    mid = _mission_en_attente(client, admin, "ATTENTE_PV2")
    _ajouter_cas(mid, ["PRET", "A_CLARIFIER", "INCOMPLET"])
    r = _decider(client, admin, mid, porte="PV-2")
    assert r.status_code == 409 and r.json()["regle"] == "RA-26"
    assert r.json()["elements"] == ["CT-002 : A_CLARIFIER", "CT-003 : INCOMPLET"]
    m = client.get("/api/missions/%d" % mid, headers=admin).json()
    assert m["porte_en_attente"] == "PV-2" and len(m["bloquants_porte"]) == 2


def test_pv2_sans_aucun_cas_refuse(client, admin, ia):
    mid = _mission_en_attente(client, admin, "ATTENTE_PV2")
    assert _decider(client, admin, mid, porte="PV-2").json()["regle"] == "RA-26"


def test_pv2_approuve_quand_tous_les_cas_sont_prets(client, admin, ia):
    mid = _mission_en_attente(client, admin, "ATTENTE_PV2")
    _ajouter_cas(mid, ["PRET", "PRET"])
    r = _decider(client, admin, mid, porte="PV-2")
    assert r.status_code == 200 and r.json()["statut_mission"] == "VALIDEE"


def test_mauvaise_porte_pour_le_statut(client, admin, ia):
    mid = _mission_en_attente(client, admin, "ATTENTE_PV1")
    assert _decider(client, admin, mid, porte="PV-2").json()["regle"] == "RA-11"
