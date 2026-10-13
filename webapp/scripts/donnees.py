#!/usr/bin/env python3
"""Données de test (AG-04) — contrôle RG-11 et jeu de recette.

Vérifie que les données de test sont fictives, reconnaissables et exactes
(RG-11), que chaque valeur est présente mot pour mot dans son CT, et produit
le jeu de recette.

Usage : python donnees.py <sfd> <cas.csv> <dictionnaire.csv> <valeurs.csv>
Sorties : td-<projet>.csv (jeu de recette), ecarts-donnees-<projet>.csv.
Codes : 0 = aucun écart, 1 = des écarts (cas normal), 2 = entrée inexploitable
        ou format invalide, 3 = défaut du script.
Auto-test : python donnees.py --selftest
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
EN_TETE_DICO = ["Champ", "Catégorie"]
EN_TETE_VALEURS = ["CT", "Champ", "Valeur"]
CATEGORIES = ("texte", "identifiant", "montant", "date", "statut")
RE_CT = re.compile(r"^CT-\d{3}$")
RE_NOM_CAS = re.compile(r"^cas-(.+)\.csv$")


def _lire_csv(chemin, attendu):
    with open(chemin, "r", encoding="utf-8-sig") as f:
        lignes = list(csv.reader(f, delimiter=";"))
    if not lignes or lignes[0] != attendu:
        raise ValueError("en-tête non conforme : %s" % (lignes[0] if lignes else "(vide)"))
    return lignes[1:]


def _colonne_ct(cas_lignes, ct_id, idx):
    for l in cas_lignes:
        if l and l[0].strip() == ct_id:
            return l[idx] if idx < len(l) else ""
    return None


def donnees(sfd_path, cas_path, dico_path, valeurs_path):
    projet = None
    m = RE_NOM_CAS.match(os.path.basename(cas_path))
    if m:
        projet = m.group(1)
    if projet is None:
        return 2, "nom du fichier des cas non conforme"
    for p in (sfd_path, cas_path, dico_path, valeurs_path):
        if not os.path.isfile(p):
            return 2, "fichier introuvable : %s" % p
    try:
        cas_lignes = _lire_csv(cas_path, EN_TETE_CAS)
        dico_lignes = _lire_csv(dico_path, EN_TETE_DICO)
        valeurs_lignes = _lire_csv(valeurs_path, EN_TETE_VALEURS)
    except ValueError as e:
        return 2, str(e)
    except Exception as e:
        return 3, "défaut du script : %s" % e

    categories = {}
    for l in dico_lignes:
        if not l or all(c.strip() == "" for c in l):
            continue
        champ, cat = l[0].strip(), l[1].strip()
        if cat not in CATEGORIES:
            return 2, "dictionnaire : catégorie inconnue %r pour %s" % (cat, champ)
        categories[champ] = cat

    ecarts = []
    jeu = []
    for l in valeurs_lignes:
        if not l or all(c.strip() == "" for c in l):
            continue
        if len(l) != 3:
            ecarts.append({"code": "E01", "objet": str(l), "message": "3 colonnes attendues"})
            continue
        ct, champ, valeur = l[0].strip(), l[1].strip(), l[2].strip()
        if not RE_CT.match(ct):
            ecarts.append({"code": "E02", "objet": ct, "message": "CT invalide"})
            continue
        # valeur présente mot pour mot dans le CT (préconditions ou données)
        pre = _colonne_ct(cas_lignes, ct, 7)
        data = _colonne_ct(cas_lignes, ct, 8)
        if pre is None:
            ecarts.append({"code": "E03", "objet": ct, "message": "CT introuvable"})
            continue
        if valeur not in (pre or "") and valeur not in (data or ""):
            ecarts.append({"code": "E11", "objet": ct,
                           "message": "valeur absente du CT : %r" % valeur})
            continue
        # RG-11 : catégorie -> règle de fictivité
        cat = categories.get(champ)
        if cat == "texte" and "TEST" not in valeur.upper():
            ecarts.append({"code": "D01", "objet": champ,
                           "message": "RG-11 : texte sans TEST : %r" % valeur})
        if cat == "identifiant" and not valeur.startswith("99"):
            ecarts.append({"code": "D02", "objet": champ,
                           "message": "RG-11 : identifiant ne commençant pas par 99 : %r" % valeur})
        jeu.append([ct, champ, valeur])

    rep = os.path.dirname(os.path.abspath(cas_path))
    with open(os.path.join(rep, "td-%s.csv" % projet), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["CT", "Champ", "Valeur"])
        for r in jeu:
            w.writerow(r)
    with open(os.path.join(rep, "ecarts-donnees-%s.csv" % projet), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["Code", "Objet", "Message"])
        for e in ecarts:
            w.writerow([e["code"], e["objet"], e["message"]])

    lignes = ["Valeurs : %d" % len(jeu), "Jeu de recette : td-%s.csv" % projet]
    if ecarts:
        lignes.append("Écarts : %d" % len(ecarts))
        return 1, "\n".join(lignes)
    lignes.append("Écarts : 0")
    return 0, "\n".join(lignes)


def _ecrire(chemin, entete, lignes):
    with open(chemin, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(entete)
        for l in lignes:
            w.writerow(l)


def _auto_test():
    sfd = "REQ-001 : A.\n"
    echecs = []
    fd, fsfd = tempfile.mkstemp(suffix=".md")
    os.write(fd, sfd.encode("utf-8"))
    os.close(fd)
    rep = tempfile.mkdtemp()
    fcas = os.path.join(rep, "cas-demo.csv")
    fdico = os.path.join(rep, "dictionnaire-demo.csv")
    fval = os.path.join(rep, "valeurs-demo.csv")
    try:
        ct = ["CT-001", "T", "O", "REQ-001", "partitions d'équivalence", "Haute",
              "Fonctionnel", "Locataire TEST Dupont", "RIB 9912345", "e", "r", "OK"]
        _ecrire(fcas, EN_TETE_CAS, [ct])
        _ecrire(fdico, EN_TETE_DICO, [["Nom", "texte"], ["RIB", "identifiant"]])
        _ecrire(fval, EN_TETE_VALEURS,
                [["CT-001", "Nom", "TEST Dupont"], ["CT-001", "RIB", "9912345"]])
        code, msg = donnees(fsfd, fcas, fdico, fval)
        if code != 0:
            echecs.append(("conforme -> code %d" % code, msg))
        # RG-11 violé : texte sans TEST
        _ecrire(fval, EN_TETE_VALEURS,
                [["CT-001", "Nom", "Dupont"], ["CT-001", "RIB", "9912345"]])
        code, msg = donnees(fsfd, fcas, fdico, fval)
        if code != 1:
            echecs.append(("RG-11 violé -> code %d" % code, msg))
        # valeur absente du CT
        _ecrire(fval, EN_TETE_VALEURS, [["CT-001", "Nom", "TEST Martin"]])
        code, msg = donnees(fsfd, fcas, fdico, fval)
        if code != 1:
            echecs.append(("valeur absente -> code %d" % code, msg))
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
        print("Auto-test donnees.py : OK (RG-11, valeur mot pour mot, jeu de recette)")
        sys.exit(0)
    if len(sys.argv) != 5:
        print("Usage : python donnees.py <sfd> <cas.csv> <dictionnaire.csv> <valeurs.csv>",
              file=sys.stderr)
        sys.exit(3)
    code, msg = donnees(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
    print(msg)
    sys.exit(code)
