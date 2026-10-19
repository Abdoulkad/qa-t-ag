#!/usr/bin/env python3
"""Contrôle déterministe d'une exigence réécrite (cycle Clarifier → Réécrire).

Règles (docs/specifications.md) :
- RA-19 : chaque critère d'acceptation cite au moins une source vérifiable :
  une citation « mot pour mot » de l'exigence d'origine, ou une réponse
  humaine Q-n de l'étape Clarifier.
- RA-20 : un critère sans source vérifiable est une HYPOTHESE. L'IA
  n'invente pas de règle métier : c'est ce script qui tranche, pas le modèle.

Format attendu du rapport :

    ## Exigence réécrite
    <texte>

    ## Critères d'acceptation
    ### CA-01
    - **Critère** : Étant donné …, quand …, alors …
    - **Sources** : « passage exact » ; Q-2

Usage : python verifier_reecriture.py <origine> <reecriture> <reponses.json>
        reponses.json = liste des codes de questions répondues, ex. ["Q-1","Q-3"]
Codes : 0 = tous les critères sourcés, 1 = au moins une hypothèse,
        2 = rapport mal formé ou entrée introuvable, 3 = défaut du script.
Auto-test : python verifier_reecriture.py --selftest
"""

import json
import os
import re
import sys

# La forme est tolérante (niveau de titre, gras, numérotation, apostrophe
# typographique, deux-points) ; le FOND ne l'est jamais : la vérification des
# sources, plus bas, reste stricte.
_TITRE = r"^\s*(?:#{1,4}\s*)?(?:\d+[.)]\s*)?\**\s*"
_FIN = r"\s*\**\s*:?\s*\**\s*$"
RE_SECTION_EXIGENCE = re.compile(
    _TITRE + r"(?:exigence|user story|us)\s+(?:réécrite|reecrite|reformulée|reformulee)" + _FIN,
    re.MULTILINE | re.IGNORECASE)
RE_SECTION_CRITERES = re.compile(
    _TITRE + r"crit[èe]res\s+d['’]\s*acceptation" + _FIN, re.MULTILINE | re.IGNORECASE)
RE_SECTION_POINTS = re.compile(
    _TITRE + r"points\s+(?:ouverts|en\s+suspens|non\s+r[ée]solus)" + _FIN,
    re.MULTILINE | re.IGNORECASE)
RE_POINT = re.compile(r"^\s*[-*]\s+(.+?)\s*$")
RE_CA = re.compile(r"^\s*(?:#{2,4}\s*|[-*]\s*)?\**\s*(CA-\d{2,3})\b\**\s*(?:[:—–-].*)?$")
RE_CRITERE = re.compile(r"^\s*[-*]?\s*\**\s*Crit[èe]re\s*\**\s*:\s*\**\s*(.+?)\s*$",
                        re.IGNORECASE)
RE_SOURCES = re.compile(r"^\s*[-*]?\s*\**\s*Sources?\s*\**\s*:\s*\**\s*(.*?)\s*$",
                        re.IGNORECASE)
RE_CITATION = re.compile(r"«\s*(.+?)\s*»")
RE_QUESTION = re.compile(r"\bQ-\d+\b")


def _normaliser_espaces(s):
    return re.sub(r"\s+", " ", s).strip()


def parser(rapport):
    """Retourne (texte_reecrit, criteres, erreurs)."""
    erreurs = []
    m_ex = RE_SECTION_EXIGENCE.search(rapport)
    m_ca = RE_SECTION_CRITERES.search(rapport)
    if not m_ex:
        erreurs.append("section manquante : ## Exigence réécrite")
    if not m_ca:
        erreurs.append("section manquante : ## Critères d'acceptation")
    if erreurs:
        return None, [], erreurs
    if m_ca.start() < m_ex.end():
        return None, [], ["les critères doivent suivre l'exigence réécrite"]
    texte = rapport[m_ex.end():m_ca.start()].strip()
    if not texte:
        erreurs.append("exigence réécrite vide")

    m_po = RE_SECTION_POINTS.search(rapport, m_ca.end())
    fin_criteres = m_po.start() if m_po else len(rapport)
    criteres, courant = [], None
    for ligne in rapport[m_ca.end():fin_criteres].splitlines():
        m = RE_CA.match(ligne)
        if m:
            courant = {"code": m.group(1), "texte": None, "sources_brutes": ""}
            criteres.append(courant)
            continue
        if courant is None:
            continue
        mc = RE_CRITERE.match(ligne)
        if mc:
            courant["texte"] = mc.group(1)
        ms = RE_SOURCES.match(ligne)
        if ms:
            courant["sources_brutes"] = ms.group(1)
    if not criteres:
        erreurs.append("aucun critère d'acceptation")
    codes = [c["code"] for c in criteres]
    for c in criteres:
        if not c["texte"]:
            erreurs.append("%s : critère sans texte" % c["code"])
    doublons = sorted({c for c in codes if codes.count(c) > 1})
    if doublons:
        erreurs.append("codes dupliqués : %s" % ", ".join(doublons))
    return texte, criteres, erreurs


def extraire_points_ouverts(rapport):
    """Section facultative « ## Points ouverts » : ce que l'IA n'a PAS transformé
    en critère, faute de source. Ces points ne bloquent pas PV-1 mais sont
    montrés au valideur (RA-43)."""
    m_po = RE_SECTION_POINTS.search(rapport)
    if not m_po:
        return []
    points = []
    for ligne in rapport[m_po.end():].splitlines():
        if re.match(r"^\s*#", ligne):
            break
        m = RE_POINT.match(ligne)
        if m and m.group(1).strip().lower() not in ("aucun", "aucun.", "néant"):
            points.append(m.group(1).strip())
    return points


def verifier(origine, rapport, questions_repondues):
    """Retourne (code, texte_reecrit, criteres, erreurs).

    Chaque critère reçoit : sources (valides), sources_rejetees, statut.
    """
    texte, criteres, erreurs = parser(rapport)
    if erreurs:
        return 2, texte, criteres, erreurs
    origine_norm = _normaliser_espaces(origine)
    repondues = set(questions_repondues)
    hypothese = False
    for c in criteres:
        valides, rejetees = [], []
        for cit in RE_CITATION.findall(c["sources_brutes"]):
            # mot pour mot, seuls les blancs multiples sont tolérés
            (valides if _normaliser_espaces(cit) in origine_norm else rejetees).append("« %s »" % cit)
        for q in RE_QUESTION.findall(c["sources_brutes"]):
            (valides if q in repondues else rejetees).append(q)
        c["sources"] = valides
        c["sources_rejetees"] = rejetees
        # RA-20 : une seule source rejetée suffit. Elle signale une partie du
        # critère qui ne repose sur rien (ex. « 30 minutes » tiré d'une question
        # reportée), même si une autre source est valide.
        c["statut"] = "SOURCE" if valides and not rejetees else "HYPOTHESE"
        hypothese = hypothese or c["statut"] == "HYPOTHESE"
    return (1 if hypothese else 0), texte, criteres, []


def _auto_test():
    origine = "Le lien de réinitialisation est valide pendant une durée limitée.\nREQ-001 : mot de passe sécurisé."
    bon = """## Exigence réécrite
En tant qu'utilisateur, je réinitialise mon mot de passe.

## Critères d'acceptation
### CA-01
- **Critère** : Étant donné un lien émis, quand 30 minutes sont écoulées, alors il est refusé.
- **Sources** : « valide pendant une durée limitée » ; Q-1
### CA-02
- **Critère** : Étant donné un nouveau mot de passe de 7 caractères, alors il est refusé.
- **Sources** : Q-2
### CA-03
- **Critère** : Alors un SMS est envoyé.
- **Sources** : « un SMS est envoyé »
"""
    echecs = []
    code, texte, cas, err = verifier(origine, bon, ["Q-1"])
    statuts = {c["code"]: c["statut"] for c in cas}
    if code != 1 or statuts != {"CA-01": "SOURCE", "CA-02": "HYPOTHESE", "CA-03": "HYPOTHESE"}:
        echecs.append(("hypothèses", code, statuts))
    if cas and cas[1]["sources_rejetees"] != ["Q-2"]:
        echecs.append(("question non répondue rejetée", cas[1]["sources_rejetees"]))
    code, *_ = verifier(origine, bon, ["Q-1", "Q-2"])
    if code != 1:      # CA-03 reste inventé
        echecs.append(("citation inventée", code))
    # Faille corrigée : une source valide ne couvre pas une source rejetée
    code, _, cas, _ = verifier(origine, bon, [])          # Q-1 non répondue
    if cas[0]["statut"] != "HYPOTHESE" or cas[0]["sources_rejetees"] != ["Q-1"]:
        echecs.append(("source rejetée à côté d'une source valide", cas[0]))
    code, _, _, err = verifier(origine, "pas de format", [])
    if code != 2:
        echecs.append(("mal formé", code, err))
    multi_blancs = bon.replace("valide pendant une durée", "valide  pendant  une durée")
    code, _, cas, _ = verifier(origine, multi_blancs, ["Q-1"])
    if cas[0]["statut"] != "SOURCE":
        echecs.append(("blancs tolérés", cas[0]))
    variante = """### 1. **Exigence réécrite :**
En tant qu'utilisateur, je réinitialise mon mot de passe.

### 2. Critères d’acceptation
**CA-01** — lien expiré
- Critère : Étant donné un lien émis, quand 30 minutes sont écoulées, alors il est refusé.
- Sources : « valide pendant une durée limitée » ; Q-1
"""
    code, texte, cas, err = verifier(origine, variante, ["Q-1"])
    if code != 0 or len(cas) != 1 or cas[0]["statut"] != "SOURCE":
        echecs.append(("format tolérant", code, err, cas))
    avec_points = variante + "\n## Points ouverts\n- Notification après succès non précisée (Q-3)\n"
    code, _, cas, _ = verifier(origine, avec_points, ["Q-1"])
    if code != 0 or len(cas) != 1:
        echecs.append(("points ouverts hors critères", code, cas))
    if extraire_points_ouverts(avec_points) != ["Notification après succès non précisée (Q-3)"]:
        echecs.append(("points ouverts", extraire_points_ouverts(avec_points)))
    return echecs


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--selftest":
        e = _auto_test()
        if e:
            for x in e:
                print("ÉCHEC:", x)
            sys.exit(1)
        print("Auto-test verifier_reecriture.py : OK")
        sys.exit(0)
    if len(sys.argv) != 4:
        print(__doc__, file=sys.stderr)
        sys.exit(3)
    try:
        for p in sys.argv[1:4]:
            if not os.path.isfile(p):
                print("ERREUR : fichier introuvable %s" % p)
                sys.exit(2)
        with open(sys.argv[1], encoding="utf-8") as f:
            origine = f.read()
        with open(sys.argv[2], encoding="utf-8") as f:
            rapport = f.read()
        with open(sys.argv[3], encoding="utf-8") as f:
            repondues = json.load(f)
    except Exception as ex:  # noqa: BLE001
        print("ERREUR (défaut du script) : %s" % ex)
        sys.exit(3)
    code, _, criteres, erreurs = verifier(origine, rapport, repondues)
    for e in erreurs:
        print("[ERREUR] " + e)
    for c in criteres:
        print("%s : %s %s" % (c["code"], c.get("statut", "?"),
                              ("(rejetées : %s)" % ", ".join(c["sources_rejetees"]))
                              if c.get("sources_rejetees") else ""))
    sys.exit(code)
