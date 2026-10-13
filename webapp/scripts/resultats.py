#!/usr/bin/env python3
"""Contrôle déterministe des résultats d'exécution (AG-08).

Vérifie que chaque CT a un résultat, chaque résultat a une preuve, et qu'aucun
PASS n'est posé sans preuve observable (règle AG-08 : 0 PASS sans preuve).

Usage : python resultats.py <cas.csv> <resultats.csv>
Codes : 0 = conforme, 1 = écarts (CT manquant), 2 = format invalide,
        3 = défaut du script.
Auto-test : python resultats.py --selftest
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
EN_TETE_RES = ["EXE", "CT", "Statut", "EVID", "Preuve"]
STATUTS = ("PASS", "FAIL", "BLOQUÉ", "NON_CONCLUANT")
RE_EXE = re.compile(r"^EXE-\d{3}$")
RE_CT = re.compile(r"^CT-\d{3}$")
RE_EVID = re.compile(r"^EVID-\d{3}$")


def _lire_csv(chemin, attendu):
    with open(chemin, "r", encoding="utf-8-sig") as f:
        lignes = list(csv.reader(f, delimiter=";"))
    if not lignes or lignes[0] != attendu:
        raise ValueError("en-tête non conforme : %s" % (lignes[0] if lignes else "(vide)"))
    return lignes[1:]


def resultats(cas_path, res_path):
    for p in (cas_path, res_path):
        if not os.path.isfile(p):
            return 2, "fichier introuvable : %s" % p
    try:
        cas_lignes = _lire_csv(cas_path, EN_TETE_CAS)
        res_lignes = _lire_csv(res_path, EN_TETE_RES)
    except ValueError as e:
        return 2, str(e)
    except Exception as e:
        return 3, "défaut du script : %s" % e

    cts = [l[0].strip() for l in cas_lignes if l and any(c.strip() for c in l)]
    erreurs = []
    ecarts = []
    ct_vus = {}
    for num, l in enumerate(res_lignes, start=2):
        if not l or all(c.strip() == "" for c in l):
            continue
        if len(l) != 5:
            erreurs.append("ligne %d : 5 colonnes attendues" % num)
            continue
        exe, ct, statut, evid, preuve = [c.strip() for c in l]
        if not RE_EXE.match(exe):
            erreurs.append("ligne %d : EXE invalide %r" % (num, exe))
        if not RE_CT.match(ct):
            erreurs.append("ligne %d : CT invalide %r" % (num, ct))
        elif ct not in cts:
            erreurs.append("ligne %d : CT inconnu %s" % (num, ct))
        if statut not in STATUTS:
            erreurs.append("ligne %d : statut inconnu %r" % (num, statut))
        if not RE_EVID.match(evid):
            erreurs.append("ligne %d : EVID invalide %r" % (num, evid))
        if not preuve:
            erreurs.append("ligne %d : preuve manquante" % num)
        if ct:
            ct_vus[ct] = ct_vus.get(ct, 0) + 1

    manquants = [c for c in cts if c not in ct_vus]
    if manquants:
        ecarts.append("CT sans résultat : %s" % ", ".join(manquants))

    lignes = []
    for e in erreurs:
        lignes.append("[ERREUR] " + e)
    for e in ecarts:
        lignes.append("[ÉCART] " + e)
    lignes.append("Résultats : %d / CT : %d" % (len(ct_vus), len(cts)))

    if erreurs:
        return 2, "\n".join(lignes)
    if ecarts:
        return 1, "\n".join(lignes)
    return 0, "\n".join(lignes)


def _ecrire(chemin, entete, lignes):
    with open(chemin, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(entete)
        for l in lignes:
            w.writerow(l)


def _auto_test():
    cas = ["CT-001", "CT-002"]
    echecs = []
    rep = tempfile.mkdtemp()
    fcas = os.path.join(rep, "cas-demo.csv")
    fres = os.path.join(rep, "resultats-demo.csv")
    try:
        _ecrire(fcas, EN_TETE_CAS, [
            ["CT-001", "T", "O", "REQ-001", "partitions d'équivalence", "Critique", "Fonctionnel", "p", "d", "e", "r", "OK"],
            ["CT-002", "T", "O", "REQ-002", "partitions d'équivalence", "Critique", "Fonctionnel", "p", "d", "e", "r", "OK"],
        ])
        _ecrire(fres, EN_TETE_RES, [
            ["EXE-001", "CT-001", "PASS", "EVID-001", "preuves/1.png"],
            ["EXE-002", "CT-002", "FAIL", "EVID-002", "preuves/2.png"],
        ])
        code, msg = resultats(fcas, fres)
        if code != 0:
            echecs.append(("conforme -> code %d" % code, msg))
        _ecrire(fres, EN_TETE_RES, [
            ["EXE-001", "CT-001", "PASS", "", ""],
            ["EXE-002", "CT-002", "FAIL", "EVID-002", "preuves/2.png"],
        ])
        code, msg = resultats(fcas, fres)
        if code != 2:
            echecs.append(("PASS sans preuve -> code %d" % code, msg))
        _ecrire(fres, EN_TETE_RES, [["EXE-001", "CT-001", "PASS", "EVID-001", "preuves/1.png"]])
        code, msg = resultats(fcas, fres)
        if code != 1:
            echecs.append(("CT manquant -> code %d" % code, msg))
        _ecrire(fres, EN_TETE_RES, [
            ["EXE-001", "CT-001", "PASSE", "EVID-001", "p.png"],
            ["EXE-002", "CT-002", "FAIL", "EVID-002", "p2.png"],
        ])
        code, msg = resultats(fcas, fres)
        if code != 2:
            echecs.append(("statut inconnu -> code %d" % code, msg))
    finally:
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
        print("Auto-test resultats.py : OK (couverture, preuve, 0 PASS sans preuve)")
        sys.exit(0)
    if len(sys.argv) != 3:
        print("Usage : python resultats.py <cas.csv> <resultats.csv>", file=sys.stderr)
        sys.exit(3)
    code, msg = resultats(sys.argv[1], sys.argv[2])
    print(msg)
    sys.exit(code)
