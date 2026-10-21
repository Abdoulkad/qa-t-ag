"""Sauvegarde et restauration de la base QA-T-AG (RA-54).

Toutes les données de l'application sont en base (textes, défauts, cas, journal) :
une sauvegarde PostgreSQL suffit.

    python -m qatag.sauvegarde                       crée une sauvegarde
    python -m qatag.sauvegarde --lister              liste les sauvegardes
    python -m qatag.sauvegarde --restaurer FICHIER   remplace la base par FICHIER

La sauvegarde utilise pg_dump au format « custom » (compressé, restaurable par
pg_restore), puis la relit avec pg_restore --list pour vérifier qu'elle est
exploitable. Seules les N plus récentes sont conservées (SAUVEGARDES_CONSERVEES).
Le mot de passe de la base passe par la variable PGPASSWORD, jamais par la ligne
de commande.
"""
import argparse
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy.engine import make_url

from .config import parametres

PREFIXE = "qatag-"
EXTENSION = ".dump"


class ErreurSauvegarde(Exception):
    pass


def _outil(nom: str) -> str:
    """Chemin de pg_dump / pg_restore : dossier PG_BIN du .env, sinon le PATH."""
    dossier = parametres().pg_bin
    if dossier:
        for candidat in (Path(dossier) / nom, Path(dossier) / (nom + ".exe")):
            if candidat.is_file():
                return str(candidat)
        raise ErreurSauvegarde("%s introuvable dans PG_BIN (%s)" % (nom, dossier))
    chemin = shutil.which(nom)
    if not chemin:
        raise ErreurSauvegarde(
            "%s introuvable. Indiquez le dossier bin de PostgreSQL dans le .env, "
            "par exemple PG_BIN=C:\\Program Files\\PostgreSQL\\16\\bin" % nom)
    return chemin


def _connexion() -> tuple[list[str], dict, str]:
    """Options de connexion et environnement (mot de passe) tirés de DATABASE_URL."""
    url = make_url(parametres().database_url)
    options = ["--host", url.host or "localhost", "--port", str(url.port or 5432),
               "--username", url.username or "postgres", "--no-password"]
    env = dict(os.environ)
    if url.password:
        env["PGPASSWORD"] = url.password
    return options, env, url.database


def _executer(commande: list[str], env: dict) -> subprocess.CompletedProcess:
    r = subprocess.run(commande, env=env, capture_output=True, text=True)
    if r.returncode != 0:
        raise ErreurSauvegarde((r.stderr or r.stdout).strip() or "échec sans message")
    return r


def dossier() -> Path:
    d = Path(parametres().dossier_sauvegardes)
    d.mkdir(parents=True, exist_ok=True)
    return d


def lister() -> list[Path]:
    """Sauvegardes du dossier, de la plus récente à la plus ancienne."""
    return sorted(dossier().glob(PREFIXE + "*" + EXTENSION), reverse=True)


def sauvegarder() -> Path:
    options, env, base = _connexion()
    fichier = dossier() / ("%s%s%s" % (PREFIXE, datetime.now().strftime("%Y%m%d-%H%M%S"),
                                       EXTENSION))
    temporaire = fichier.with_suffix(".partiel")
    try:
        _executer([_outil("pg_dump"), *options, "--format=custom", "--no-owner",
                   "--file", str(temporaire), "--dbname", base], env)
        # Vérifie que la sauvegarde se relit et contient bien le journal
        contenu = _executer([_outil("pg_restore"), "--list", str(temporaire)], env).stdout
        if "TABLE public journal" not in contenu:
            raise ErreurSauvegarde("sauvegarde incomplète : la table journal est absente")
        temporaire.replace(fichier)
    finally:
        temporaire.unlink(missing_ok=True)
    # Rotation : on ne garde que les plus récentes
    for ancienne in lister()[parametres().sauvegardes_conservees:]:
        ancienne.unlink()
    return fichier


def restaurer(fichier: Path) -> None:
    """Remplace le contenu de la base par celui de la sauvegarde, en une seule
    transaction : en cas d'erreur, la base reste dans son état précédent."""
    if not fichier.is_file():
        raise ErreurSauvegarde("fichier introuvable : %s" % fichier)
    options, env, base = _connexion()
    _executer([_outil("pg_restore"), *options, "--clean", "--if-exists", "--no-owner",
               "--single-transaction", "--exit-on-error", "--dbname", base, str(fichier)], env)


def _taille(f: Path) -> str:
    octets = f.stat().st_size
    return "%.1f Mo" % (octets / 1e6) if octets >= 1e6 else "%d Ko" % max(1, octets // 1000)


def main(arguments: list[str] | None = None) -> int:
    analyseur = argparse.ArgumentParser(prog="python -m qatag.sauvegarde",
                                        description="Sauvegarde de la base QA-T-AG.")
    groupe = analyseur.add_mutually_exclusive_group()
    groupe.add_argument("--lister", action="store_true", help="liste les sauvegardes")
    groupe.add_argument("--restaurer", metavar="FICHIER", help="remplace la base par FICHIER")
    analyseur.add_argument("--oui", action="store_true",
                           help="restaurer sans demander de confirmation")
    a = analyseur.parse_args(arguments)
    try:
        if a.lister:
            fichiers = lister()
            print("Dossier : %s" % dossier())
            for f in fichiers:
                print("  %s  (%s)" % (f.name, _taille(f)))
            if not fichiers:
                print("  aucune sauvegarde")
            return 0
        if a.restaurer:
            fichier = Path(a.restaurer)
            if not fichier.is_file() and (dossier() / a.restaurer).is_file():
                fichier = dossier() / a.restaurer
            base = make_url(parametres().database_url).database
            if not a.oui:
                print("ATTENTION : le contenu actuel de la base « %s » sera remplacé par\n"
                      "%s. Arrêtez le serveur QA-T-AG avant de continuer." % (base, fichier))
                if input("Tapez RESTAURER pour confirmer : ").strip() != "RESTAURER":
                    print("Restauration annulée.")
                    return 1
            restaurer(fichier)
            print("Base « %s » restaurée depuis %s." % (base, fichier.name))
            return 0
        f = sauvegarder()
        print("Sauvegarde créée : %s (%s)" % (f, _taille(f)))
        return 0
    except ErreurSauvegarde as e:
        print("Erreur : %s" % e, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
