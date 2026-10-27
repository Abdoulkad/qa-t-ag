#!/usr/bin/env python3
"""Contrôle déterministe du rapport de revue SFD (AG-01, grille QA-REV-02).

Vérifie la structure, compte les DEF par criticité/catégorie, contrôle que
chaque citation existe mot pour mot dans la SFD, refuse un défaut bloquant
sans justification, signale les doublons (même citation, même catégorie) et
lit les questions complémentaires. Le décompte chiffré du rapport vient
d'ici, jamais du modèle.

Usage : python controler_revue.py <sfd> <rapport>
Codes : 0 = conforme, 1 = écarts (citations absentes), 2 = mal formé /
        entrée introuvable, 3 = défaut du script.
Auto-test : python controler_revue.py --selftest
"""

import os
import re
import sys
import tempfile

CATEGORIES = (
    "Contradiction certaine", "Contradiction apparente", "Ambiguïté",
    "Terme non défini", "Exigence non testable", "Règle manquante",
    "Cas limite à confirmer", "Règle sans exigence",
    "Incohérence avec les user stories",
)
# Anciens libellés dont le sens est inchangé : renommés sans juger à la place
# de l'agent. « Contradiction » seule est refusée : certaine ou apparente est
# un jugement que l'agent doit porter.
ALIAS_CATEGORIES = {"cas oublié": "Règle manquante", "cas oublie": "Règle manquante"}
GRAVITES = ("Bloquante", "Majeure", "Mineure")
SECTIONS_REQUISES = (
    "## Alerte sécurité",
    "## Inventaire REQ et BR",
    "## Défauts",
    "## Statut du livrable",
)

RE_DEF = re.compile(r"^###\s+(DEF-\d+)\s*[-—–]\s*(.+?)\s*[-—–]\s*(.+?)\s*$")
RE_QC = re.compile(r"^###\s+(QC-\d+)\b")


def _champ(nom):
    return re.compile(r"^\s*-\s*\*\*%s\*\*\s*:\s*(.*?)\s*$" % nom, re.IGNORECASE)


RE_CITATION = re.compile(r"^\s*-\s*\*\*Citation\*\*\s*:\s*«\s*(.*?)\s*»\s*$")
RE_SECTION = _champ("Section")
RE_CONSTAT = _champ("Constat")
RE_JUSTIFICATION = _champ("Justification")
RE_QUESTION = _champ("Question")
RE_SUJET = _champ("Sujet")
RE_POURQUOI = _champ("Pourquoi")
RE_STATUT = re.compile(r"^##\s+Statut du livrable\s*$", re.MULTILINE)
RE_SECTION_QC = re.compile(r"^##\s+Questions compl[ée]mentaires\s*$", re.MULTILINE | re.IGNORECASE)
RE_TITRE_2 = re.compile(r"^##\s", re.MULTILINE)

STATUTS = ("OK", "A_CLARIFIER", "EN_ATTENTE", "ERREUR", "BLOQUE")


def _lire(chemin):
    with open(chemin, "r", encoding="utf-8") as f:
        return f.read()


def categorie_canonique(libelle):
    """Libellé exact de la grille (casse tolérée), alias ancien, ou None."""
    cle = libelle.strip().lower()
    for c in CATEGORIES:
        if c.lower() == cle:
            return c
    return ALIAS_CATEGORIES.get(cle)


def _bloc_defauts(texte):
    """Texte entre « ## Défauts » et la section de niveau 2 suivante."""
    debut = texte.find("## Défauts")
    if debut < 0:
        return ""
    debut += len("## Défauts")
    m = RE_TITRE_2.search(texte, debut)
    return texte[debut:m.start() if m else len(texte)]


def parser_rapport(texte):
    """Retourne (defs, statut, erreurs). Chaque DEF : id, categorie, gravite,
    section, citation, constat, justification, question."""
    defs = []
    erreurs = []
    for s in SECTIONS_REQUISES:
        if s not in texte:
            erreurs.append("section manquante : %s" % s)
    m = RE_STATUT.search(texte)
    statut = None
    if m:
        suite = texte[m.end():].strip().splitlines()
        if suite:
            statut = suite[0].strip()
        if statut not in STATUTS:
            erreurs.append("statut du livrable invalide : %r" % statut)
    else:
        erreurs.append("section « Statut du livrable » introuvable")
    def_courant = None
    for ligne in _bloc_defauts(texte).splitlines():
        m = RE_DEF.match(ligne)
        if m:
            if def_courant:
                defs.append(def_courant)
            brut = m.group(2).strip()
            def_courant = {
                "id": m.group(1), "categorie": categorie_canonique(brut) or brut,
                "gravite": m.group(3).strip(), "citation": None, "section": None,
                "constat": None, "justification": None, "question": None,
            }
            if categorie_canonique(brut) is None:
                aide = (" (préciser : Contradiction certaine ou Contradiction apparente)"
                        if brut.lower().startswith("contradiction") else "")
                erreurs.append("%s : catégorie inconnue %r%s" % (def_courant["id"], brut, aide))
            if def_courant["gravite"] not in GRAVITES:
                erreurs.append("%s : gravité inconnue %r" % (def_courant["id"], def_courant["gravite"]))
            continue
        if def_courant:
            for cle, motif in (("citation", RE_CITATION), ("section", RE_SECTION),
                               ("constat", RE_CONSTAT), ("justification", RE_JUSTIFICATION),
                               ("question", RE_QUESTION)):
                mc = motif.match(ligne)
                if mc and def_courant[cle] is None:
                    def_courant[cle] = mc.group(1)
    if def_courant:
        defs.append(def_courant)
    for d in defs:
        if not d["citation"]:
            erreurs.append("%s : citation manquante" % d["id"])
        if d["gravite"] == "Bloquante" and not (d["justification"] or "").strip():
            erreurs.append("%s : criticité Bloquante sans justification" % d["id"])
    return defs, statut, erreurs


def parser_complementaires(texte):
    """Section « ## Questions complémentaires » : règles absentes du texte.
    Retourne [{id, sujet, pourquoi, question}] (questions sans texte ignorées)."""
    m = RE_SECTION_QC.search(texte)
    if not m:
        return []
    fin = RE_TITRE_2.search(texte, m.end())
    qcs, courant = [], None
    for ligne in texte[m.end():fin.start() if fin else len(texte)].splitlines():
        mq = RE_QC.match(ligne)
        if mq:
            courant = {"id": mq.group(1), "sujet": None, "pourquoi": None, "question": None}
            qcs.append(courant)
            continue
        if courant:
            for cle, motif in (("sujet", RE_SUJET), ("pourquoi", RE_POURQUOI),
                               ("question", RE_QUESTION)):
                mc = motif.match(ligne)
                if mc and courant[cle] is None:
                    courant[cle] = mc.group(1)
    return [q for q in qcs if (q["question"] or "").strip()]


def doublons(defs):
    """Défauts qui citent le même passage avec la même catégorie (signalement,
    pas un refus : deux aspects d'un même passage restent légitimes)."""
    vus, signales = {}, []
    for d in defs:
        cle = (re.sub(r"\s+", " ", d["citation"] or "").strip().lower(), d["categorie"])
        if cle[0] and cle in vus:
            signales.append("%s double %s (même citation, même catégorie)" % (d["id"], vus[cle]))
        else:
            vus.setdefault(cle, d["id"])
    return signales


def verifier_citations(defs, sfd_texte):
    """Retourne la liste des DEF dont la citation est absente du SFD."""
    return [d["id"] for d in defs if d["citation"] and d["citation"] not in sfd_texte]


def compter(defs, cle):
    compte = {}
    for d in defs:
        compte[d[cle]] = compte.get(d[cle], 0) + 1
    return compte


def controler(sfd_path, rapport_path):
    """Retourne (code, message)."""
    if not os.path.isfile(sfd_path) or not os.path.isfile(rapport_path):
        return 2, "ERREUR (entrée inexploitable) : fichier introuvable"
    try:
        sfd = _lire(sfd_path)
        rapport = _lire(rapport_path)
    except Exception as e:
        return 3, "ERREUR (défaut du script) : %s" % e
    defs, statut, erreurs = parser_rapport(rapport)
    if erreurs:
        return 2, "ERREUR (rapport mal formé) :\n" + "\n".join(erreurs)
    absentes = verifier_citations(defs, sfd)
    lignes = [
        "DEF : %d" % len(defs),
        "questions complémentaires : %d" % len(parser_complementaires(rapport)),
        "par gravité : %s" % compter(defs, "gravite"),
        "par catégorie : %s" % compter(defs, "categorie"),
        "statut du livrable : %s" % statut,
    ] + ["Doublon signalé : %s" % x for x in doublons(defs)]
    if absentes:
        lignes.append("Citations absentes du SFD : %s" % ", ".join(absentes))
        return 1, "\n".join(lignes)
    lignes.append("Citations : toutes présentes mot pour mot")
    return 0, "\n".join(lignes)


def _auto_test():
    sfd = ("Le dossier est traité sous 5 jours ouvrés.\nLe montant maximal est 100 000.\n"
           "Toute facture est remboursée. Toutefois, une facture non acquittée peut être acceptée.\n")
    rapport_ok = (
        "# Revue SFD — demo\n\n"
        "## Alerte sécurité\nAucune\n\n"
        "## Inventaire REQ et BR\n- REQ-001 — traitement\n\n"
        "## Défauts\n"
        "### DEF-001 — Ambiguïté — Majeure\n"
        "- **Section** : 1\n"
        "- **Citation** : « Le dossier est traité sous 5 jours ouvrés. »\n"
        "- **Constat** : l'événement de départ du délai n'est pas indiqué.\n"
        "- **Question** : À partir de quel événement le délai court-il ?\n"
        "### DEF-002 — Contradiction apparente — Bloquante\n"
        "- **Section** : 3\n"
        "- **Citation** : « Toutefois, une facture non acquittée peut être acceptée. »\n"
        "- **Constat** : exception sans condition.\n"
        "- **Justification** : Calcul financier : décide si l'assureur paie.\n"
        "- **Question** : Dans quels cas une facture non acquittée est-elle acceptée ?\n\n"
        "## Questions complémentaires\n"
        "### QC-01\n"
        "- **Sujet** : Plafond partiellement atteint\n"
        "- **Pourquoi** : le montant versé en dépend.\n"
        "- **Question** : Que rembourse-t-on quand le plafond restant est inférieur au montant ?\n\n"
        "## Statut du livrable\nA_CLARIFIER\n"
    )
    echecs = []
    defs, statut, err = parser_rapport(rapport_ok)
    if err or len(defs) != 2 or defs[1]["categorie"] != "Contradiction apparente":
        echecs.append(("rapport v2 valide", err, defs))
    elif defs[0]["constat"] != "l'événement de départ du délai n'est pas indiqué." \
            or not defs[1]["justification"] or not defs[0]["question"]:
        echecs.append(("champs constat/justification/question", defs))
    qcs = parser_complementaires(rapport_ok)
    if [q["sujet"] for q in qcs] != ["Plafond partiellement atteint"]:
        echecs.append(("questions complémentaires", qcs))
    _, _, err = parser_rapport(rapport_ok.replace(
        "- **Justification** : Calcul financier : décide si l'assureur paie.\n", ""))
    if err != ["DEF-002 : criticité Bloquante sans justification"]:
        echecs.append(("bloquante sans justification refusée", err))
    _, _, err = parser_rapport(rapport_ok.replace("Contradiction apparente", "Contradiction"))
    if not err or "certaine ou Contradiction apparente" not in err[0]:
        echecs.append(("contradiction non qualifiée refusée", err))
    defs, _, err = parser_rapport(rapport_ok.replace("Ambiguïté — Majeure", "cas oublié — Majeure"))
    if err or defs[0]["categorie"] != "Règle manquante":
        echecs.append(("alias Cas oublié", err, defs[:1]))
    double = rapport_ok.replace("### DEF-002 — Contradiction apparente",
                                "### DEF-002 — Contradiction apparente").replace(
        "« Toutefois, une facture non acquittée peut être acceptée. »",
        "« Le dossier est traité sous 5 jours ouvrés. »").replace(
        "Contradiction apparente — Bloquante", "Ambiguïté — Bloquante")
    if doublons(parser_rapport(double)[0]) != ["DEF-002 double DEF-001 (même citation, même catégorie)"]:
        echecs.append(("doublon signalé", doublons(parser_rapport(double)[0])))
    rapport_citation_absente = rapport_ok.replace(
        "Le dossier est traité sous 5 jours ouvrés.",
        "Le dossier est traité sous 6 jours ouvrés.")
    fd, fsfd = tempfile.mkstemp(suffix=".md")
    os.write(fd, sfd.encode("utf-8"))
    os.close(fd)
    fd, fr = tempfile.mkstemp(suffix=".md")
    os.close(fd)
    try:
        with open(fr, "w", encoding="utf-8") as f:
            f.write(rapport_ok)
        code, msg = controler(fsfd, fr)
        if code != 0:
            echecs.append(("rapport valide -> code %d" % code, msg))
        with open(fr, "w", encoding="utf-8") as f:
            f.write(rapport_citation_absente)
        code, msg = controler(fsfd, fr)
        if code != 1:
            echecs.append(("citation absente -> code %d" % code, msg))
        with open(fr, "w", encoding="utf-8") as f:
            f.write("# pas de sections\n")
        code, msg = controler(fsfd, fr)
        if code != 2:
            echecs.append(("rapport mal formé -> code %d" % code, msg))
    finally:
        for c in (fsfd, fr):
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
        print("Auto-test controler_revue.py : OK (structure, grille QA-REV-02, citation, doublons)")
        sys.exit(0)
    if len(sys.argv) != 3:
        print("Usage : python controler_revue.py <sfd> <rapport>", file=sys.stderr)
        sys.exit(3)
    code, msg = controler(sys.argv[1], sys.argv[2])
    print(msg)
    sys.exit(code)
