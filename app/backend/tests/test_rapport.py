"""RA-66 à RA-68 : rapport de test rédigé par AG-11, validé par l'humain."""
import io

import docx
from sqlalchemy import select

from qatag.db import SessionLocale
from qatag.models import ConfigIA, EntreeJournal

from .conftest import REDACTION_IA
from .test_recette import (_cahier, _cas, _echec, _executer, _mission_validee, _recette,
                           _texte)


def _campagne(client, h, ia):
    """CT-001 en échec (ANO-001 ouverte), les trois autres réussis."""
    mid = _mission_validee(client, h, ia)
    cas = _cas(client, h, mid)
    _echec(client, h, mid, cas["CT-001"]["id"])
    for code in ("CT-002", "CT-003", "CT-004"):
        _executer(client, h, mid, cas[code]["id"], "PASS", "Conforme")
    return mid, cas


def _rediger(client, h, mid):
    return client.post("/api/missions/%d/recette/rapport/redaction" % mid, headers=h)


def _enregistrer(client, h, mid, redaction, valider=False):
    return client.put("/api/missions/%d/recette/rapport" % mid, headers=h,
                      json={**redaction, "valider": valider})


def _rapport(client, h, mid):
    return _recette(client, h, mid)["rapport"]


def test_ag11_propose_un_rapport_non_valide(client, admin, ia):
    mid, _ = _campagne(client, admin, ia)
    assert _rediger(client, admin, mid).status_code == 202
    r = _rapport(client, admin, mid)
    assert r["agent"]["etat"] == "PROPOSEE" and r["valide_le"] is None
    assert r["redaction"]["avis"] == "Favorable avec réserves"
    assert r["redaction"]["recommandations"] == {
        "CT-001": "corriger ANO-001 puis rejouer le cas avant la mise en production."}
    consigne = ia.appels[-1]["corps"]["messages"][-1]["content"]
    assert "Réussis : 3" in consigne and "ANO-001" in consigne
    with SessionLocale() as db:
        e = db.scalar(select(EntreeJournal).where(EntreeJournal.evenement == "rapport_propose"))
        assert e.agent == "AG-11"


def test_redaction_impossible_avant_toute_execution(client, admin, ia):
    mid = _mission_validee(client, admin, ia)
    r = _rediger(client, admin, mid)
    assert r.status_code == 409 and r.json()["regle"] == "RA-66"


def test_ag11_ne_peut_pas_donner_un_avis_favorable_avec_un_echec(client, admin, ia):
    ia.reponses["rapport"] = REDACTION_IA.replace("Favorable avec réserves", "Favorable")
    mid, _ = _campagne(client, admin, ia)
    _rediger(client, admin, mid)
    r = _rapport(client, admin, mid)
    assert r["agent"]["etat"] == "ECHEC" and "Favorable" in r["agent"]["erreur"]


def test_ag11_ne_peut_pas_inventer_un_chiffre(client, admin, ia):
    ia.reponses["rapport"] = REDACTION_IA.replace("3 cas réussis (75 %)", "5 cas réussis (75 %)")
    mid, _ = _campagne(client, admin, ia)
    _rediger(client, admin, mid)
    assert _rapport(client, admin, mid)["agent"]["etat"] == "ECHEC"


def test_correction_humaine_controlee_comme_le_texte_de_l_agent(client, admin, ia):
    mid, _ = _campagne(client, admin, ia)
    _rediger(client, admin, mid)
    redaction = _rapport(client, admin, mid)["redaction"]
    faux = dict(redaction, synthese="Les 12 cas sont réussis.")
    r = _enregistrer(client, admin, mid, faux)
    assert r.status_code == 409 and r.json()["regle"] == "RA-67"
    assert any("12 cas" in e for e in r.json()["elements"])


def test_validation_puis_export_avec_le_texte_valide(client, admin, ia):
    mid, _ = _campagne(client, admin, ia)
    _rediger(client, admin, mid)
    redaction = _rapport(client, admin, mid)["redaction"]
    redaction["conclusion"] += " Un dernier test par le métier est conseillé."
    assert _enregistrer(client, admin, mid, redaction, valider=True).status_code == 200
    r = _rapport(client, admin, mid)
    assert r["valide_par"]["email"] == "bamk@exemple.ci" and r["a_revoir"] == []
    texte = _texte(_cahier(client, admin, mid).content)
    assert "La campagne porte sur la réinitialisation du mot de passe" in texte
    assert "Vérifier le refus d'un lien expiré (CA-01)." in texte
    assert "Avis sur la mise en production : Favorable avec réserves." in texte
    assert "proposées par l'agent AG-11, relues et validées par BAMK" in texte
    assert "Un dernier test par le métier est conseillé." in texte
    assert "Synthèse" in texte and "03 (75 %)" in texte
    assert "Sur les quatre (04) cas de test, quatre (04) ont été exécutés." in texte
    assert "corriger ANO-001 puis rejouer le cas" in texte          # observations du cas


def test_rapport_valide_perime_bloque_l_export(client, admin, ia):
    mid, cas = _campagne(client, admin, ia)
    _rediger(client, admin, mid)
    _enregistrer(client, admin, mid, _rapport(client, admin, mid)["redaction"], valider=True)
    _executer(client, admin, mid, cas["CT-001"]["id"], "PASS", "Message « Lien expiré »")
    assert _rapport(client, admin, mid)["a_revoir"]               # 4 réussis, plus 3
    r = _cahier(client, admin, mid)
    assert r.status_code == 409 and r.json()["regle"] == "RA-68"


def test_modifier_annule_la_validation(client, admin, ia):
    mid, _ = _campagne(client, admin, ia)
    _rediger(client, admin, mid)
    redaction = _rapport(client, admin, mid)["redaction"]
    _enregistrer(client, admin, mid, redaction, valider=True)
    _enregistrer(client, admin, mid, redaction, valider=False)
    assert _rapport(client, admin, mid)["valide_le"] is None
    assert "Avis sur la mise en production" not in _texte(_cahier(client, admin, mid).content)


def test_redaction_entierement_humaine_sans_ia(client, admin, ia):
    mid, _ = _campagne(client, admin, ia)
    with SessionLocale() as db:
        db.query(ConfigIA).delete()
        db.commit()
    assert _rediger(client, admin, mid).json()["regle"] == "RA-37"
    redaction = {"contexte": "Recette de la réinitialisation du mot de passe.",
                 "objectifs": ["Vérifier le refus d'un lien expiré (CA-01)."],
                 "synthese": "Un cas reste en échec (CT-001).", "recommandations": {},
                 "conclusion": "Correction attendue avant la mise en production.",
                 "avis": "Défavorable"}
    assert _enregistrer(client, admin, mid, redaction, valider=True).status_code == 200
    texte = _texte(_cahier(client, admin, mid).content)
    assert "Parties rédigées validées par BAMK" in texte and "AG-11" not in texte


def test_cahier_sans_rapport_garde_ses_parties_factuelles(client, admin, ia):
    mid, _ = _campagne(client, admin, ia)
    d = docx.Document(io.BytesIO(_cahier(client, admin, mid).content))
    texte = "\n".join(p.text for p in d.paragraphs)
    assert "Synthèse" in texte and "Avis sur la mise en production" not in texte
    assert ("Sur les quatre (04) cas de test, trois (03) sont conformes aux résultats attendus, "
            "un (01) en échec.") in texte
    assert "Anomalie restant à traiter : ANO-001" in texte
