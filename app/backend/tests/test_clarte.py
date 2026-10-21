"""RA-17 : score de clarté calculé par script."""
from qatag.regles import score_clarte

from .conftest import US_TEST


def test_formule():
    assert score_clarte([]) == 100
    assert score_clarte(["Bloquante", "Majeure", "Mineure"]) == 62
    assert score_clarte(["Bloquante"] * 5) == 0          # borné à 0


def test_score_de_la_mission_vient_du_script(client, admin, ia):
    r = client.post("/api/missions", json={"titre": "US", "texte": US_TEST}, headers=admin)
    m = client.get("/api/missions/%d" % r.json()["mission"]["id"], headers=admin).json()
    assert m["score_clarte"] == 62
