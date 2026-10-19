"""RA-34, RA-35 : journal en ajout seul et chaîné."""
import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from qatag.db import moteur

from .conftest import US_TEST


def _remplir(client, admin):
    client.post("/api/missions", json={"titre": "US", "texte": US_TEST}, headers=admin)


def test_chaine_intacte(client, admin, ia):
    _remplir(client, admin)
    r = client.get("/api/journal/verification", headers=admin).json()
    assert r == {"integre": True, "premiere_entree_alteree": None}


@pytest.mark.parametrize("ordre", ["UPDATE journal SET evenement = 'x'", "DELETE FROM journal",
                                   "TRUNCATE journal"])
def test_la_base_refuse_toute_modification(client, admin, ia, ordre):
    _remplir(client, admin)
    with pytest.raises(DBAPIError) as e:
        with moteur.begin() as c:
            c.execute(text(ordre))
    assert "RA-34" in str(e.value)


def test_alteration_detectee_par_la_chaine(client, admin, ia):
    _remplir(client, admin)
    with moteur.begin() as c:     # un administrateur base qui contourne la protection
        c.execute(text("ALTER TABLE journal DISABLE TRIGGER USER"))
        c.execute(text("UPDATE journal SET details = '{\"falsifie\": true}' WHERE id = 2"))
        c.execute(text("ALTER TABLE journal ENABLE TRIGGER USER"))
    r = client.get("/api/journal/verification", headers=admin).json()
    assert r == {"integre": False, "premiere_entree_alteree": 2}


def test_journal_visible_et_horodate(client, admin, ia):
    _remplir(client, admin)
    evts = [e["evenement"] for e in client.get("/api/journal", headers=admin).json()]
    assert evts[:2] == ["analyse_terminee", "mission_creee"]
