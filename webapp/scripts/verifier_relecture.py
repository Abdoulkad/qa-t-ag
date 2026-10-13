#!/usr/bin/env python3
"""Relecteur (AG-05) — contrôle des remarques à double citation.

Chaque remarque doit être prouvée par deux citations exactes : une du fichier
des cas (CT) et une de la SFD. Ce script vérifie que les deux citations
existent mot pour mot, et que le code appartient au catalogue.

Usage : python verifier_relecture.py <sfd> <cas.csv> <remarques.csv>
Codes : 0 = conforme, 1 = citations absentes, 2 = format invalide,
        3 = défaut du script.
Auto-test : python verifier_relecture.py --selftest
"""

import csv
import os
import re
import sys
import tempfile

EN_TETE_CAS = [
    "ID", "Titre", "Objectif", "Exigence", "Technique", "Priorité", "Type",
    "Préconditions", "Données de test", "Étapes", "Résultat attendu",
    "Statut livrable",
]
EN_TETE_REMARQUES = ["Code", "CT", "Citation CT", "Citation SFD", "Message"]

# Catalogue C01-C08 : base provisoire, à finaliser par la DSI (SFD §16).
CODES = tuple("C%02d" % i for i in range(1, 9))
RE_CT = re.compile(r"^CT-\d{3}$")


def _lire_csv(chemin, attendu):
    with open(chemin, "r", encoding="utf-8-sig") as f:
        lignes = list(csv.reader(f, delimiter=";"))
    if not lignes or lignes[0] != attendu:
        raise ValueError("en-tête non conforme : %s" % (lignes[0] if lignes else "(vide)"))
    return lignes[1:]


def _texte_ct(cas_lignes, ct_id):
    for l in cas_lignes:
        if l and l[0].strip() == ct_id:
            return "\n".join(l)
    return None


def verifier(sfd_path, cas_path, remarques_path):
    for p in (sfd_path, cas_path, remarques_path):
        if not os.path.isfile(p):
            return 2, "fichier introuvable : %s" % p
    try:
        with open(sfd_path, "r", encoding="utf-8") as f:
            sfd = f.read()
        cas_lignes = _lire_csv(cas_path, EN_TETE_CAS)
        rem_lignes = _lire_csv(remarques_path, EN_TETE_REMARQUES)
    except ValueError as e:
        return 2, str(e)
    except Exception as e:
        return 3, "défaut du script : %s" % e

    ecarts = []
    for num, l in enumerate(rem_lignes, start=2):
        if not l or all(c.strip() == "" for c in l):
            continue
        if len(l) != 5:
            ecarts.append("ligne %d : 5 colonnes attendues" % num)
            continue
        code, ct, cit_ct, cit_sfd, msg = [c.strip() for c in l]
        if code not in CODES:
            ecarts.append("ligne %d : code inconnu %r (attendu C01-C08)" % (num, code))
            continue
        if not RE_CT.match(ct):
            ecarts.append("ligne %d : CT invalide %r" % (num, ct))
            continue
        texte_ct = _texte_ct(cas_lignes, ct)
        if texte_ct is None:
            ecarts.append("ligne %d : CT introuvable %s" % (num, ct))
            continue
        if cit_ct not in texte_ct:
            ecarts.append("ligne %d : citation CT absente du CT %s" % (num, ct))
        if cit_sfd not in sfd:
            ecarts.append("ligne %d : citation SFD absente" % num)

    if ecarts:
        return 1, "\n".join(ecarts)
    return 0, "Remarques conformes : %d, chacune à double citation" % len(
        [l for l in rem_lignes if l and any(c.strip() for c in l)])


def _ecrire(chemin, entete, lignes):
    with open(chemin, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(entete)
        for l in lignes:
            w.writerow(l)


def _auto_test():
    sfd = "REQ-001 : Le montant maximal est 100 000.\n"
    ct = ["CT-001", "T", "O", "REQ-001", "valeurs limites", "Critique",
          "Fonctionnel", "pré", "données", "Saisir 100 001",
          "Le montant maximal est 100 000", "OK"]
    echecs = []
    fd, fsfd = tempfile.mkstemp(suffix=".md")
    os.write(fd, sfd.encode("utf-8"))
    os.close(fd)
    rep = tempfile.mkdtemp()
    fcas = os.path.join(rep, "cas-demo.csv")
    frem = os.path.join(rep, "remarques-demo.csv")
    try:
        _ecrire(fcas, EN_TETE_CAS, [ct])
        # conforme : double citation exacte
        _ecrire(frem, EN_TETE_REMARQUES,
                [["C02", "CT-001", "Le montant maximal est 100 000",
                  "Le montant maximal est 100 000.", "calcul erroné"]])
        code, msg = verifier(fsfd, fcas, frem)
        if code != 0:
            echecs.append(("conforme -> code %d" % code, msg))
        # citation CT absente
        _ecrire(frem, EN_TETE_REMARQUES,
                [["C02", "CT-001", "montant 999 999",
                  "Le montant maximal est 100 000.", "calcul erroné"]])
        code, msg = verifier(fsfd, fcas, frem)
        if code != 1:
            echecs.append(("citation CT absente -> code %d" % code, msg))
        # code inconnu
        _ecrire(frem, EN_TETE_REMARQUES,
                [["C99", "CT-001", "x", "y", "z"]])
        code, msg = verifier(fsfd, fcas, frem)
        if code != 1:
            echecs.append(("code inconnu -> code %d" % code, msg))
    finally:
        os.unlink(fsfd)
        import shutil
        shutil.rmtree(rep, ignore_errors=True)
    return echecs


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--selftest":
        e = _auto_test()
        if e:
            for x in e:
                print("ÉCHEC:", x)
            sys.exit(1)
        print("Auto-test verifier_relecture.py : OK (double citation, catalogue)")
        sys.exit(0)
    if len(sys.argv) != 4:
        print("Usage : python verifier_relecture.py <sfd> <cas.csv> <remarques.csv>",
              file=sys.stderr)
        sys.exit(3)
    code, msg = verifier(sys.argv[1], sys.argv[2], sys.argv[3])
    print(msg)
    sys.exit(code)
