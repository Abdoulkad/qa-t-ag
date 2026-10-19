"""RA-08 à RA-11, RA-40 : missions, versions, visibilité ; analyse AG-01."""
import hashlib
import io

import docx

from .conftest import US_TEST, entetes, inscrire


def _creer(client, h, texte=US_TEST):
    r = client.post("/api/missions", json={"titre": "Réinitialisation", "texte": texte}, headers=h)
    assert r.status_code == 201, r.text
    return client.get("/api/missions/%d" % r.json()["mission"]["id"], headers=h).json()


def test_creation_analyse_et_passage_en_clarification(client, admin, ia):
    m = _creer(client, admin)
    assert m["reference"] == "M-001"
    assert m["statut"] == "CLARIFICATION"
    v = m["versions"][0]
    assert [d["code"] for d in v["defauts"]] == ["DEF-001", "DEF-002", "DEF-003"]
    assert len(v["questions"]) == 3
    assert [q["bloquante"] for q in v["questions"]] == [True, False, False]


def test_empreinte_calculee_par_script(client, admin, ia):
    m = _creer(client, admin)
    texte = m["versions"][0]["texte"]
    assert m["versions"][0]["empreinte"] == hashlib.sha256(texte.encode("utf-8")).hexdigest()


def test_citation_inventee_detectee_par_le_script(client, admin, ia):
    v = _creer(client, admin)["versions"][0]
    verif = {d["code"]: d["citation_verifiee"] for d in v["defauts"]}
    assert verif == {"DEF-001": True, "DEF-002": True, "DEF-003": False}
    assert v["code_controle_revue"] == 1


def test_rapport_mal_forme_met_l_analyse_en_echec(client, admin, ia):
    ia.reponse = "Je n'ai pas suivi le format."
    m = _creer(client, admin)
    assert m["statut"] == "ECHEC_ANALYSE"


def test_mission_refusee_tant_qu_aucune_ia_n_est_configuree(client, ia):
    inscrire(client, "a@exemple.ci")
    h = entetes(client, "a@exemple.ci")
    r = client.post("/api/missions", json={"titre": "x", "texte": US_TEST}, headers=h)
    assert r.status_code == 409 and r.json()["regle"] == "RA-37"
    assert client.get("/api/missions", headers=h).json() == []


def test_section_alerte_omise_par_l_ia_est_toleree_et_tracee(client, admin, ia):
    ia.reponse = ia.reponse.replace("## Alerte sécurité\n\n", "")
    m = _creer(client, admin)
    assert m["statut"] == "CLARIFICATION"
    assert "Alerte sécurité" in m["versions"][0]["controle_revue"]


def test_section_de_fond_manquante_reste_une_erreur(client, admin, ia):
    ia.reponse = ia.reponse.split("## Défauts")[0]
    m = _creer(client, admin)
    assert m["statut"] == "ECHEC_ANALYSE"
    assert m["derniere_tache"]["etat"] == "ECHEC"
    assert "Défauts" in m["derniere_tache"]["erreur"]


def test_creation_depuis_un_fichier_docx(client, admin, ia):
    d = docx.Document()
    for ligne in US_TEST.splitlines():
        d.add_paragraph(ligne)
    flux = io.BytesIO()
    d.save(flux)
    r = client.post("/api/missions/fichier", data={"titre": "US docx"},
                    files={"fichier": ("us.docx", flux.getvalue())}, headers=admin)
    assert r.status_code == 201, r.text
    m = client.get("/api/missions/%d" % r.json()["mission"]["id"], headers=admin).json()
    assert m["versions"][0]["nom_source"] == "us.docx"
    assert "durée limitée" in m["versions"][0]["texte"]


def test_fichier_au_mauvais_format_refuse(client, admin, ia):
    r = client.post("/api/missions/fichier", data={"titre": "x"},
                    files={"fichier": ("us.exe", b"MZ")}, headers=admin)
    assert r.status_code == 422


def test_nouvelle_version_refusee_hors_rejet(client, admin, ia):
    m = _creer(client, admin)
    r = client.post("/api/missions/%d/versions" % m["id"], json={"texte": "v2"}, headers=admin)
    assert r.status_code == 409 and r.json()["regle"] == "RA-10"


def test_nouvelle_version_apres_echec_d_analyse(client, admin, ia):
    ia.statut_http = 500
    m = _creer(client, admin)
    ia.statut_http = 200
    r = client.post("/api/missions/%d/versions" % m["id"], json={"texte": US_TEST + "v2"},
                    headers=admin)
    assert r.status_code == 201
    m = client.get("/api/missions/%d" % m["id"], headers=admin).json()
    assert [v["numero"] for v in m["versions"]] == [1, 2]
    assert m["versions"][0]["figee"] is True
    assert m["statut"] == "CLARIFICATION"


def test_analyste_ne_voit_que_ses_missions(client, admin, ia):
    _creer(client, admin)
    inscrire(client, "t@exemple.ci")
    h = entetes(client, "t@exemple.ci")
    assert client.get("/api/missions", headers=h).json() == []
    assert client.get("/api/missions/1", headers=h).status_code == 404
    client.post("/api/missions/1/participants", json={"email": "t@exemple.ci"}, headers=admin)
    assert len(client.get("/api/missions", headers=h).json()) == 1


def test_admin_seul_ne_peut_pas_creer_de_mission(client, admin, ia):
    u = inscrire(client, "it@exemple.ci")
    client.patch("/api/utilisateurs/%d/roles" % u["id"], json={"roles": ["ADMIN"]}, headers=admin)
    r = client.post("/api/missions", json={"titre": "x", "texte": "y"},
                    headers=entetes(client, "it@exemple.ci"))
    assert r.status_code == 403


def test_references_sequentielles(client, admin, ia):
    assert [_creer(client, admin)["reference"] for _ in range(3)] == ["M-001", "M-002", "M-003"]
