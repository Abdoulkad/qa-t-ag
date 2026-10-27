#!/usr/bin/env python3
"""Tracer (AG-03) — matrice REQ/BR ↔ CT et écarts déterministes.

Construit la matrice de traçabilité et détecte les écarts. Le script est
l'autorité : l'agent ne modifie ni la matrice ni les écarts.

Usage : python tracer.py <sfd> <cas.csv>
Sorties : matrice-<projet>.csv et ecarts-<projet>.csv (à côté du cas.csv).
Codes : 0 = aucun écart, 1 = des écarts (cas normal), 2 = matrice impossible,
        3 = défaut du script.
Auto-test : python tracer.py --selftest
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
RE_EXIGENCE = re.compile(r"\b(REQ|BR)-\d+\b")
RE_CT = re.compile(r"^CT-\d{3}$")
RE_NOM_CAS = re.compile(r"^cas-(.+)\.csv$")


def extraire_exigences(texte_sfd):
    """Liste ordonnée des identifiants REQ-nnn / BR-nnn du SFD."""
    vus = []
    for m in RE_EXIGENCE.finditer(texte_sfd):
        idf = m.group(0)
        if idf not in vus:
            vus.append(idf)
    return vus


def lire_cas(chemin):
    with open(chemin, "r", encoding="utf-8-sig") as f:
        return list(csv.reader(f, delimiter=";"))


def _projet_depuis_nom(chemin):
    nom = os.path.basename(chemin)
    m = RE_NOM_CAS.match(nom)
    return m.group(1) if m else None


def tracer(sfd_path, cas_path):
    """Retourne (code, message). Écrit matrice et écarts en cas de succès."""
    if not os.path.isfile(sfd_path) or not os.path.isfile(cas_path):
        return 2, "fichier introuvable"
    projet = _projet_depuis_nom(cas_path)
    if projet is None:
        return 2, "nom du fichier des cas non conforme (attendu cas-<projet>.csv)"
    try:
        with open(sfd_path, "r", encoding="utf-8") as f:
            sfd = f.read()
        lignes = lire_cas(cas_path)
    except Exception as e:
        return 3, "défaut du script : %s" % e
    if not lignes:
        return 2, "fichier des cas vide"
    if lignes[0] != EN_TETE_CAS:
        return 2, "fichier des cas : en-tête non conforme"

    exigences = extraire_exigences(sfd)
    ct_exigences = {}   # CT -> [exigences citées]
    erreurs_lignes = []
    for num, ligne in enumerate(lignes[1:], start=2):
        if not ligne or all(c.strip() == "" for c in ligne):
            continue
        if len(ligne) != 12:
            erreurs_lignes.append("ligne %d : %d colonnes" % (num, len(ligne)))
            continue
        id_ = ligne[0].strip()
        if not RE_CT.match(id_):
            erreurs_lignes.append("ligne %d : ID invalide %r" % (num, id_))
            continue
        citees = [m.group(0) for m in RE_EXIGENCE.finditer(ligne[3])]
        ct_exigences[id_] = citees
    if erreurs_lignes:
        return 2, "fichier des cas, ligne :\n" + "\n".join(erreurs_lignes)

    # matrice : exigence -> CTs qui la citent
    matrice = {e: [ct for ct, exs in ct_exigences.items() if e in exs]
               for e in exigences}

    # écarts (catalogue de base ; le catalogue T01-T12 complet est à fixer par
    # la DSI, SFD §16 — voir notes)
    ecarts = []
    for e in exigences:
        if not matrice[e]:
            ecarts.append({"code": "E01", "objet": e,
                           "message": "exigence sans CT"})
    exs_connues = set(exigences)
    for ct, exs in ct_exigences.items():
        if not exs:
            ecarts.append({"code": "E03", "objet": ct,
                           "message": "CT sans exigence citée"})
        for ex in exs:
            if ex not in exs_connues:
                ecarts.append({"code": "E02", "objet": ct,
                               "message": "exigence inconnue %s" % ex})

    # écriture matrice.csv
    rep = os.path.dirname(os.path.abspath(cas_path))
    chemin_matrice = os.path.join(rep, "matrice-%s.csv" % projet)
    with open(chemin_matrice, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["Exigence", "CTs"])
        for e in exigences:
            w.writerow([e, ",".join(matrice[e])])

    # écriture ecarts.csv
    chemin_ecarts = os.path.join(rep, "ecarts-%s.csv" % projet)
    with open(chemin_ecarts, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["Code", "Objet", "Message"])
        for e in ecarts:
            w.writerow([e["code"], e["objet"], e["message"]])

    lignes_sortie = ["Exigences : %d, CT : %d" % (len(exigences), len(ct_exigences)),
                     "Matrice : %s" % chemin_matrice,
                     "Écarts : %s" % chemin_ecarts]
    if ecarts:
        lignes_sortie.append("Écarts : %d" % len(ecarts))
        return 1, "\n".join(lignes_sortie)
    lignes_sortie.append("Écarts : 0")
    return 0, "\n".join(lignes_sortie)


def _auto_test():
    sfd = "REQ-001 : A.\nREQ-002 : B.\nBR-001 : C.\n"
    ct = lambda i, ex: ["CT-%03d" % i, "T", "O", ex, "partitions d'équivalence",
                        "Haute", "Fonctionnel", "p", "d", "e", "r", "OK"]
    echecs = []
    fd, fsfd = tempfile.mkstemp(suffix=".md")
    os.write(fd, sfd.encode("utf-8"))
    os.close(fd)
    rep = tempfile.mkdtemp()
    fcas = os.path.join(rep, "cas-demo.csv")
    try:
        with open(fcas, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(EN_TETE_CAS)
            for l in [ct(1, "REQ-001"), ct(2, "REQ-002"), ct(3, "BR-001")]:
                w.writerow(l)
        code, msg = tracer(fsfd, fcas)
        if code != 0:
            echecs.append(("sans écart -> code %d" % code, msg))
        # retirer BR-001 -> écart E01
        with open(fcas, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(EN_TETE_CAS)
            for l in [ct(1, "REQ-001"), ct(2, "REQ-002")]:
                w.writerow(l)
        code, msg = tracer(fsfd, fcas)
        if code != 1:
            echecs.append(("écart -> code %d" % code, msg))
        # nom non conforme
        fbad = os.path.join(rep, "cas.csv")
        code, msg = tracer(fsfd, fbad)
        if code != 2:
            echecs.append(("nom non conforme -> code %d" % code, msg))
    finally:
        for c in (fsfd,):
            if os.path.isfile(c):
                os.unlink(c)
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
        print("Auto-test tracer.py : OK (matrice, écarts E01/E02/E03, nom)")
        sys.exit(0)
    if len(sys.argv) != 3:
        print("Usage : python tracer.py <sfd> <cas.csv>", file=sys.stderr)
        sys.exit(3)
    code, msg = tracer(sys.argv[1], sys.argv[2])
    print(msg)
    sys.exit(code)
