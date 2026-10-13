#!/usr/bin/env python3
"""Contrôle déterministe du fichier des cas de test (AG-02).

Usage : python controler_cas.py <sfd> <cas.csv>
Codes : 0 = conforme (format + couverture complète),
        1 = couverture incomplète (REQ/BR sans CT),
        2 = entrée inexploitable ou erreur de format ([ERREUR]),
        3 = défaut du script.
Auto-test : python controler_cas.py --selftest
"""

import csv
import os
import re
import sys
import tempfile

EN_TETE = [
    "ID", "Titre", "Objectif", "Exigence", "Technique", "Priorité", "Type",
    "Préconditions", "Données de test", "Étapes", "Résultat attendu",
    "Statut livrable",
]
TECHNIQUES = (
    "partitions d'équivalence", "valeurs limites",
    "table de décision", "transitions d'état",
)
PRIORITES = ("Critique", "Haute", "Moyenne")
TYPES = ("Fonctionnel", "Interface utilisateur", "Sécurité/Habilitation")

RE_EXIGENCE = re.compile(r"\b(REQ|BR)-\d+\b")
RE_ET_PUIS = re.compile(r"\bet\b|\bpuis\b", re.IGNORECASE)
RE_GERONDIF = re.compile(r"\b\w+ant\b", re.IGNORECASE)
RE_VARIABLE = re.compile(r"\{[^}]+\}")


def extraire_exigences(texte_sfd):
    """Retourne la liste ordonnée des identifiants REQ-nnn / BR-nnn du SFD."""
    vus = []
    for m in RE_EXIGENCE.finditer(texte_sfd):
        idf = m.group(0)
        if idf not in vus:
            vus.append(idf)
    return vus


def lire_cas(chemin):
    with open(chemin, "r", encoding="utf-8-sig") as f:
        return list(csv.reader(f, delimiter=";"))


def controler(sfd_path, cas_path):
    """Retourne (code, message)."""
    if not os.path.isfile(sfd_path) or not os.path.isfile(cas_path):
        return 2, "ERREUR (entrée inexploitable) : fichier introuvable"
    try:
        with open(sfd_path, "r", encoding="utf-8") as f:
            sfd = f.read()
        lignes = lire_cas(cas_path)
    except Exception as e:
        return 3, "ERREUR (défaut du script) : %s" % e
    if not lignes:
        return 2, "ERREUR : fichier des cas vide"
    if lignes[0] != EN_TETE:
        return 2, "ERREUR : en-tête non conforme — attendu : %s" % ";".join(EN_TETE)

    exigences = extraire_exigences(sfd)
    erreurs = []
    alertes = []
    ids_vus = []
    citees = set()

    for num, ligne in enumerate(lignes[1:], start=2):
        if not ligne or all(c.strip() == "" for c in ligne):
            continue
        if len(ligne) != 12:
            erreurs.append("ligne %d : %d colonnes au lieu de 12" % (num, len(ligne)))
            continue
        (id_, titre, obj, exig, tech, prio, typ, pre, data, etapes, res, statut) = ligne
        if not re.match(r"^CT-\d{3}$", id_.strip()):
            erreurs.append("ligne %d : ID invalide %r (attendu CT-nnn)" % (num, id_))
        else:
            if id_.strip() in ids_vus:
                erreurs.append("ligne %d : ID dupliqué %s" % (num, id_))
            ids_vus.append(id_.strip())
        if tech.strip() not in TECHNIQUES:
            erreurs.append("ligne %d : technique inconnue %r" % (num, tech))
        if prio.strip() not in PRIORITES:
            erreurs.append("ligne %d : priorité inconnue %r" % (num, prio))
        if typ.strip() not in TYPES:
            erreurs.append("ligne %d : type inconnu %r" % (num, typ))
        if not exig.strip():
            erreurs.append("ligne %d : exigence vide" % num)
        else:
            for m in RE_EXIGENCE.finditer(exig):
                citees.add(m.group(0))
        if not res.strip():
            erreurs.append("ligne %d : résultat attendu vide" % num)
        if etapes and RE_ET_PUIS.search(etapes):
            alertes.append("ligne %d : étape avec « et » ou « puis » (RG-08)" % num)
        if etapes and RE_GERONDIF.search(etapes):
            alertes.append("ligne %d : gérondif dans les étapes" % num)
        if res and RE_VARIABLE.search(res):
            alertes.append("ligne %d : {variable} non résolue dans le résultat" % num)

    attendus = ["CT-%03d" % (k + 1) for k in range(len(ids_vus))]
    if ids_vus != attendus:
        alertes.append("ID non séquentiels : %s" % ", ".join(ids_vus))

    non_citees = [e for e in exigences if e not in citees]

    lignes_sortie = []
    for e in erreurs:
        lignes_sortie.append("[ERREUR] " + e)
    for a in alertes:
        lignes_sortie.append("[ALERTE] " + a)
    if non_citees:
        lignes_sortie.append("Couverture : non citées par un CT : %s" % ", ".join(non_citees))
    else:
        lignes_sortie.append("Couverture : toutes les exigences sont citées par un CT")

    if erreurs:
        return 2, "\n".join(lignes_sortie)
    if non_citees:
        return 1, "\n".join(lignes_sortie)
    lignes_sortie.append("CT : %d" % len(ids_vus))
    return 0, "\n".join(lignes_sortie)


def _ecrire_cas(chemin, ct_lignes):
    with open(chemin, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(EN_TETE)
        for l in ct_lignes:
            w.writerow(l)


def _auto_test():
    sfd = "REQ-001 : le système calcule le montant.\nREQ-002 : le système ouvre le droit.\nBR-001 : le montant maximal est 100 000.\n"
    ct = lambda i, ex: ["CT-%03d" % i, "Titre", "Objectif", ex,
                        "partitions d'équivalence", "Haute", "Fonctionnel",
                        "pré", "données", "Saisir la valeur", "Résultat : %s" % ex, "OK"]
    echecs = []
    fd, fsfd = tempfile.mkstemp(suffix=".md")
    os.write(fd, sfd.encode("utf-8"))
    os.close(fd)
    fd, fcas = tempfile.mkstemp(suffix=".csv")
    os.close(fd)
    try:
        _ecrire_cas(fcas, [ct(1, "REQ-001"), ct(2, "REQ-002"), ct(3, "BR-001")])
        code, msg = controler(fsfd, fcas)
        if code != 0:
            echecs.append(("couverture complète -> code %d" % code, msg))
        _ecrire_cas(fcas, [ct(1, "REQ-001"), ct(2, "REQ-002")])
        code, msg = controler(fsfd, fcas)
        if code != 1:
            echecs.append(("couverture incomplète -> code %d" % code, msg))
        with open(fcas, "w", encoding="utf-8") as f:
            f.write("ID;Titre\n")
        code, msg = controler(fsfd, fcas)
        if code != 2:
            echecs.append(("en-tête faux -> code %d" % code, msg))
        mauvais = ct(1, "REQ-001")
        mauvais[4] = "technique bidon"
        _ecrire_cas(fcas, [mauvais])
        code, msg = controler(fsfd, fcas)
        if code != 2:
            echecs.append(("technique inconnue -> code %d" % code, msg))
    finally:
        for c in (fsfd, fcas):
            if os.path.isfile(c):
                os.unlink(c)
    return echecs


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--selftest":
        e = _auto_test()
        if e:
            for x in e:
                print("ÉCHEC:", x)
            sys.exit(1)
        print("Auto-test controler_cas.py : OK (en-tête, couverture, format)")
        sys.exit(0)
    if len(sys.argv) != 3:
        print("Usage : python controler_cas.py <sfd> <cas.csv>", file=sys.stderr)
        sys.exit(3)
    code, msg = controler(sys.argv[1], sys.argv[2])
    print(msg)
    sys.exit(code)
