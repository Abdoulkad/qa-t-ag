#!/usr/bin/env python3
"""Empreinte SHA-256 des artefacts — autorité déterministe.

SFD V2.0 §6.1 : « sha256 doit être calculé par script ; le modèle ne doit
pas fabriquer d'empreinte. »

Usage :
    python empreinte.py <fichier> [<fichier>...]
Sortie : JSON {chemin: sha256} dans l'ordre des arguments.

Auto-test : `python empreinte.py --selftest`.
"""

import hashlib
import json
import os
import sys
import tempfile

TAILLE_BLOC = 1024 * 1024  # 1 Mio


def empreinte_fichier(chemin):
    """SHA-256 hexadécimal d'un fichier, lu par blocs (sans tout charger)."""
    h = hashlib.sha256()
    with open(chemin, "rb") as f:
        while True:
            bloc = f.read(TAILLE_BLOC)
            if not bloc:
                break
            h.update(bloc)
    return h.hexdigest()


def empreinte_artefacts(chemins):
    """{chemin: sha256}, ordre d'entrée conservé."""
    return {c: empreinte_fichier(c) for c in chemins}


def _selftest():
    contenu = b"QA-T-AG socle deterministe\n"
    attendu = hashlib.sha256(contenu).hexdigest()
    fd, chemin = tempfile.mkstemp()
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(contenu)
        obtenu = empreinte_fichier(chemin)
        print("empreinte obtenue :", obtenu)
        print("empreinte attendue:", attendu)
        return 0 if obtenu == attendu else 1
    finally:
        os.unlink(chemin)


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "--selftest":
        sys.exit(_selftest())
    if len(sys.argv) < 2:
        print("Usage : python empreinte.py <fichier> [<fichier>...]", file=sys.stderr)
        sys.exit(2)
    resultats = {}
    for chemin in sys.argv[1:]:
        if not os.path.isfile(chemin):
            print("fichier introuvable : %s" % chemin, file=sys.stderr)
            sys.exit(2)
        resultats[chemin] = empreinte_fichier(chemin)
    print(json.dumps(resultats, ensure_ascii=False, indent=2))
    sys.exit(0)
