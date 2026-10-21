"""RA-54 : sauvegarde et restauration de la base (vrai pg_dump / pg_restore)."""
import shutil

import pytest
from sqlalchemy import func, select, text

from qatag import sauvegarde
from qatag.config import parametres
from qatag.db import SessionLocale, moteur
from qatag.models import Utilisateur

from .conftest import inscrire

pytestmark = pytest.mark.skipif(not shutil.which("pg_dump"), reason="pg_dump absent")


@pytest.fixture
def dossier(tmp_path, monkeypatch):
    monkeypatch.setattr(parametres(), "dossier_sauvegardes", tmp_path)
    return tmp_path


def _comptes():
    with SessionLocale() as db:
        return db.scalar(select(func.count()).select_from(Utilisateur))


def test_sauvegarde_puis_restauration(client, dossier):
    inscrire(client, "a@exemple.ci")
    fichier = sauvegarde.sauvegarder()
    assert fichier.parent == dossier and fichier.suffix == ".dump"
    assert not list(dossier.glob("*.partiel"))
    inscrire(client, "b@exemple.ci")
    assert _comptes() == 2
    sauvegarde.restaurer(fichier)
    assert _comptes() == 1          # retour à l'état sauvegardé
    # La protection du journal (ajout seul) est restaurée avec la base
    with pytest.raises(Exception):
        with moteur.begin() as c:
            c.execute(text("DELETE FROM journal"))


def test_rotation_garde_les_plus_recentes(client, dossier, monkeypatch):
    monkeypatch.setattr(parametres(), "sauvegardes_conservees", 2)
    for nom in ("qatag-20260101-000000.dump", "qatag-20260102-000000.dump"):
        (dossier / nom).write_bytes(b"ancienne")
    nouvelle = sauvegarde.sauvegarder()
    assert [f.name for f in sauvegarde.lister()] == [nouvelle.name, "qatag-20260102-000000.dump"]


def test_mot_de_passe_hors_ligne_de_commande(client, dossier, monkeypatch):
    commandes = []
    vrai = sauvegarde._executer
    monkeypatch.setattr(sauvegarde, "_executer",
                        lambda c, env: (commandes.append((c, env)), vrai(c, env))[1])
    sauvegarde.sauvegarder()
    for commande, env in commandes:
        assert "qatag:qatag" not in " ".join(commande)
        assert env["PGPASSWORD"] == "qatag"


def test_restauration_fichier_absent(dossier):
    with pytest.raises(sauvegarde.ErreurSauvegarde):
        sauvegarde.restaurer(dossier / "absent.dump")


def test_restauration_annulee_sans_confirmation(dossier, monkeypatch, capsys):
    f = dossier / "qatag-20260101-000000.dump"
    f.write_bytes(b"x")
    monkeypatch.setattr("builtins.input", lambda _: "non")
    assert sauvegarde.main(["--restaurer", str(f)]) == 1
    assert "annulée" in capsys.readouterr().out


def test_pg_bin_invalide_message_clair(dossier, monkeypatch, tmp_path):
    monkeypatch.setattr(parametres(), "pg_bin", str(tmp_path / "rien"))
    assert sauvegarde.main([]) == 2
