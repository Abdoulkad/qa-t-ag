#!/usr/bin/env python3
"""Contrôle déterministe d'une User Story réécrite (cycle Clarifier → Réécrire).

Règles (docs/specifications.md) :
- RA-19 : chaque règle métier et chaque critère cite au moins une source
  vérifiable : une citation « mot pour mot » de l'exigence d'origine, ou une
  réponse humaine Q-n de l'étape Clarifier. Un critère peut aussi s'appuyer
  sur les règles qu'il vérifie (RG-n).
- RA-20 : un élément sans source vérifiable, ou qui cite UNE source rejetée
  (citation introuvable, question sans réponse, règle inconnue ou hypothèse),
  est une HYPOTHESE. C'est ce script qui tranche, pas le modèle.
- RA-47 : la User Story réécrite, les règles métier et les critères sont
  séparés.
- RA-48 : chaque phrase du texte d'origine doit être reprise par au moins une
  citation valide d'une règle ou d'un critère (sinon l'humain justifie).

Format attendu :

    ## User Story réécrite
    <texte>

    ## Règles métier
    ### RG-01
    - **Règle** : <règle de gestion>
    - **Sources** : « passage exact » ; Q-1

    ## Critères d'acceptation
    ### CA-01
    - **Critère** : Étant donné …, quand …, alors …
    - **Règles** : RG-01
    - **Sources** : « passage exact » ; Q-2

    ## Points ouverts            (facultatif)
    - <sujet non tranché>

Usage : python verifier_reecriture.py <origine> <reecriture> <reponses.json>
        reponses.json = liste des codes de questions répondues, ex. ["Q-1","Q-3"]
Codes : 0 = tout est sourcé, 1 = au moins une hypothèse,
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
RE_SECTION_REGLES = re.compile(
    _TITRE + r"r[èe]gles\s+(?:m[ée]tier|de\s+gestion)" + _FIN, re.MULTILINE | re.IGNORECASE)
RE_SECTION_CRITERES = re.compile(
    _TITRE + r"crit[èe]res\s+d['’]\s*acceptation" + _FIN, re.MULTILINE | re.IGNORECASE)
RE_SECTION_POINTS = re.compile(
    _TITRE + r"points\s+(?:ouverts|en\s+suspens|non\s+r[ée]solus)" + _FIN,
    re.MULTILINE | re.IGNORECASE)
RE_POINT = re.compile(r"^\s*[-*]\s+(.+?)\s*$")


def _re_code(prefixe):
    return re.compile(r"^\s*(?:#{2,4}\s*|[-*]\s*)?\**\s*(%s-\d{2,3})\b\**\s*(?:[:—–-].*)?$"
                      % prefixe)


def _re_champ(nom):
    return re.compile(r"^\s*[-*]?\s*\**\s*%s\s*\**\s*:\s*\**\s*(.*?)\s*$" % nom, re.IGNORECASE)


RE_CA = _re_code("CA")
RE_RG = _re_code("RG")
RE_CRITERE = _re_champ(r"Crit[èe]re")
RE_REGLE = _re_champ(r"R[èe]gle")
RE_REGLES_LIEES = _re_champ(r"R[èe]gles?(?:\s+v[ée]rifi[ée]es?)?")
RE_SOURCES = _re_champ(r"Sources?")
RE_CITATION = re.compile(r"«\s*(.+?)\s*»")
RE_QUESTION = re.compile(r"\bQ-\d+\b")
RE_CODE_RG = re.compile(r"\bRG-\d{2,3}\b")
_AUCUNE = ("aucune", "aucune.", "aucun", "néant", "-")


def _normaliser_espaces(s):
    return re.sub(r"\s+", " ", s).strip()


def _comparable(s):
    """Forme tolérée pour comparer une citation au texte : blancs multiples et casse
    (« le nouveau… » cite bien « Le nouveau… »). Les mots, eux, restent exacts."""
    return _normaliser_espaces(s).casefold()


def _items(bloc, re_code, re_texte, avec_regles):
    items, courant = [], None
    for ligne in bloc.splitlines():
        m = re_code.match(ligne)
        if m:
            courant = {"code": m.group(1), "texte": None, "sources_brutes": "",
                       "regles_brutes": ""}
            items.append(courant)
            continue
        if courant is None:
            continue
        if RE_SOURCES.match(ligne):
            courant["sources_brutes"] = RE_SOURCES.match(ligne).group(1)
        elif avec_regles and RE_REGLES_LIEES.match(ligne) and not courant["texte"] is None:
            courant["regles_brutes"] = RE_REGLES_LIEES.match(ligne).group(1)
        elif re_texte.match(ligne) and courant["texte"] is None:
            courant["texte"] = re_texte.match(ligne).group(1)
    return items


def parser_complet(rapport):
    """Retourne (texte_reecrit, regles, criteres, erreurs)."""
    erreurs = []
    m_ex = RE_SECTION_EXIGENCE.search(rapport)
    m_rg = RE_SECTION_REGLES.search(rapport)
    m_ca = RE_SECTION_CRITERES.search(rapport)
    if not m_ex:
        erreurs.append("section manquante : ## User Story réécrite")
    if not m_rg:
        erreurs.append("section manquante : ## Règles métier (écrire « Aucune » s'il n'y en a pas)")
    if not m_ca:
        erreurs.append("section manquante : ## Critères d'acceptation")
    if erreurs:
        return None, [], [], erreurs
    if not (m_ex.end() <= m_rg.start() and m_rg.end() <= m_ca.start()):
        return None, [], [], ["ordre attendu : User Story réécrite, Règles métier, "
                              "Critères d'acceptation"]
    texte = rapport[m_ex.end():m_rg.start()].strip()
    if not texte:
        erreurs.append("User Story réécrite vide")
    m_po = RE_SECTION_POINTS.search(rapport, m_ca.end())
    regles = _items(rapport[m_rg.end():m_ca.start()], RE_RG, RE_REGLE, False)
    criteres = _items(rapport[m_ca.end():m_po.start() if m_po else len(rapport)],
                      RE_CA, RE_CRITERE, True)
    if not criteres:
        erreurs.append("aucun critère d'acceptation")
    for nom, liste in (("règle", regles), ("critère", criteres)):
        codes = [i["code"] for i in liste]
        for i in liste:
            if not i["texte"]:
                erreurs.append("%s : %s sans texte" % (i["code"], nom))
        doublons = sorted({c for c in codes if codes.count(c) > 1})
        if doublons:
            erreurs.append("codes dupliqués : %s" % ", ".join(doublons))
    return texte, regles, criteres, erreurs


def parser(rapport):
    """Compatibilité : (texte_reecrit, criteres, erreurs)."""
    texte, _, criteres, erreurs = parser_complet(rapport)
    return texte, criteres, erreurs


def extraire_points_ouverts(rapport):
    """Section facultative « ## Points ouverts » : ce que l'IA n'a PAS transformé
    en règle ou en critère, faute de source. Ces points ne bloquent pas PV-1 mais
    sont montrés au valideur (RA-43)."""
    m_po = RE_SECTION_POINTS.search(rapport)
    if not m_po:
        return []
    points = []
    for ligne in rapport[m_po.end():].splitlines():
        if re.match(r"^\s*#", ligne):
            break
        m = RE_POINT.match(ligne)
        if m and m.group(1).strip().lower() not in _AUCUNE:
            points.append(m.group(1).strip())
    return points


def _sources(brutes, origine_norm, repondues):
    valides, rejetees = [], []
    for cit in RE_CITATION.findall(brutes):
        # mot pour mot, seuls les blancs multiples sont tolérés
        (valides if _comparable(cit) in origine_norm else rejetees).append("« %s »" % cit)
    for q in RE_QUESTION.findall(brutes):
        (valides if q in repondues else rejetees).append(q)
    return valides, rejetees


def statut_element(valides, rejetees):
    """RA-20 : une seule source rejetée suffit à faire une hypothèse."""
    return "SOURCE" if valides and not rejetees else "HYPOTHESE"


def analyser(origine, rapport, questions_repondues):
    """Contrôle complet. Retourne un dict : code, texte, regles, criteres,
    phrases (couverture RA-48), points, erreurs."""
    texte, regles, criteres, erreurs = parser_complet(rapport)
    resultat = {"code": 2, "texte": texte, "regles": regles, "criteres": criteres,
                "phrases": [], "points": [], "erreurs": erreurs}
    if erreurs:
        return resultat
    origine_norm = _comparable(origine)
    repondues = set(questions_repondues)
    for r in regles:
        r["sources"], r["sources_rejetees"] = _sources(r["sources_brutes"], origine_norm, repondues)
        r["statut"] = statut_element(r["sources"], r["sources_rejetees"])
    statut_regle = {r["code"]: r["statut"] for r in regles}
    for c in criteres:
        c["sources"], c["sources_rejetees"] = _sources(c["sources_brutes"], origine_norm, repondues)
        c["regles"] = []
        for code in dict.fromkeys(RE_CODE_RG.findall(c["regles_brutes"])):
            if code not in statut_regle:
                c["sources_rejetees"].append("%s (règle inconnue)" % code)
            elif statut_regle[code] == "HYPOTHESE":
                c["regles"].append(code)
                c["sources_rejetees"].append("%s (règle non sourcée)" % code)
            else:
                c["regles"].append(code)
        c["statut"] = statut_element(c["sources"] + c["regles"], c["sources_rejetees"])
    citations = [s for e in regles + criteres for s in e["sources"] if s.startswith("«")]
    resultat["phrases"] = couverture(origine, citations)
    resultat["points"] = extraire_points_ouverts(rapport)
    tout = regles + criteres
    resultat["code"] = 1 if any(e["statut"] == "HYPOTHESE" for e in tout) else 0
    return resultat


def verifier(origine, rapport, questions_repondues):
    """Compatibilité : (code, texte_reecrit, criteres, erreurs)."""
    r = analyser(origine, rapport, questions_repondues)
    return r["code"], r["texte"], r["criteres"], r["erreurs"]


# --- Couverture du texte d'origine (RA-48) ---------------------------------

_RE_SEPARATEUR = re.compile(r"(?<=[.!?;])\s+")
_RE_TITRE_ID = re.compile(r"^[A-Z][A-Z0-9]*[-_]\d+\b")


def _est_titre(phrase):
    """Ligne d'identification (« US-042 — Réinitialisation… », titre Markdown)
    ou fragment trop court pour porter une exigence."""
    if phrase.startswith("#") or len(phrase.split()) < 4:
        return True
    return bool(_RE_TITRE_ID.match(phrase)) and phrase[-1] not in ".!?;:"


def phrases_source(origine):
    """Découpe le texte d'origine en phrases numérotées, dans l'ordre."""
    phrases = []
    for ligne in origine.splitlines():
        for morceau in _RE_SEPARATEUR.split(ligne.strip()):
            morceau = _normaliser_espaces(morceau)
            if morceau:
                phrases.append({"numero": len(phrases) + 1, "texte": morceau,
                                "titre": _est_titre(morceau)})
    return phrases


def phrase_couverte(phrase, citations):
    """Vrai si une citation valide reprend tout ou partie de la phrase."""
    phrase = _comparable(phrase)
    for cit in citations:
        cit = _comparable(cit.strip("« »"))
        if not cit:
            continue
        if phrase in cit:
            return True
        if any(len(p.split()) >= 2 and p in phrase for p in _RE_SEPARATEUR.split(cit)):
            return True
        if len(cit.split()) >= 1 and cit in phrase:
            return True
    return False


def couverture(origine, citations):
    """RA-48 : statut de chaque phrase : COUVERTE, NON_COUVERTE ou TITRE."""
    resultat = []
    for p in phrases_source(origine):
        statut = ("TITRE" if p["titre"] else
                  "COUVERTE" if phrase_couverte(p["texte"], citations) else "NON_COUVERTE")
        resultat.append({"numero": p["numero"], "texte": p["texte"], "statut": statut})
    return resultat


def _auto_test():
    origine = ("US-042 — Réinitialisation\n"
               "Le lien de réinitialisation est valide pendant une durée limitée.\n"
               "REQ-001 : le nouveau mot de passe doit être sécurisé.\n"
               "En cas de succès, l'utilisateur est redirigé vers la page de connexion.")
    bon = """## User Story réécrite
En tant qu'utilisateur, je réinitialise mon mot de passe.

## Règles métier
### RG-01
- **Règle** : Le lien expire 30 minutes après son émission.
- **Sources** : « valide pendant une durée limitée » ; Q-1
### RG-02
- **Règle** : Le mot de passe compte au moins 8 caractères.
- **Sources** : « le nouveau mot de passe doit être sécurisé » ; Q-2

## Critères d'acceptation
### CA-01
- **Critère** : Étant donné un lien émis il y a 31 minutes, quand je l'ouvre, alors il est refusé.
- **Règles** : RG-01
### CA-02
- **Critère** : Étant donné un mot de passe de 7 caractères, quand je valide, alors il est refusé.
- **Règles** : RG-02
### CA-03
- **Critère** : Alors un SMS est envoyé.
- **Sources** : « un SMS est envoyé »
"""
    echecs = []

    def statuts(r):
        return {e["code"]: e["statut"] for e in r["regles"] + r["criteres"]}

    r = analyser(origine, bon, ["Q-1"])
    attendu = {"RG-01": "SOURCE", "RG-02": "HYPOTHESE", "CA-01": "SOURCE",
               "CA-02": "HYPOTHESE", "CA-03": "HYPOTHESE"}
    if r["code"] != 1 or statuts(r) != attendu:
        echecs.append(("règles et critères", r["code"], statuts(r), r["erreurs"]))
    else:
        if r["regles"][1]["sources_rejetees"] != ["Q-2"]:
            echecs.append(("question non répondue rejetée", r["regles"][1]))
        # un critère hérite de l'hypothèse de la règle qu'il vérifie
        if r["criteres"][1]["sources_rejetees"] != ["RG-02 (règle non sourcée)"]:
            echecs.append(("règle hypothèse propagée", r["criteres"][1]))
    r = analyser(origine, bon, ["Q-1", "Q-2"])
    if statuts(r)["CA-02"] != "SOURCE" or statuts(r)["CA-03"] != "HYPOTHESE":
        echecs.append(("citation inventée", statuts(r)))
    # Faille corrigée : une source valide ne couvre pas une source rejetée
    r = analyser(origine, bon, [])
    if r["regles"] and (r["regles"][0]["statut"] != "HYPOTHESE"
                        or r["regles"][0]["sources_rejetees"] != ["Q-1"]):
        echecs.append(("source rejetée à côté d'une source valide", r["regles"][0]))
    inconnue = bon.replace("- **Règles** : RG-01", "- **Règles** : RG-09")
    r = analyser(origine, inconnue, ["Q-1", "Q-2"])
    if r["criteres"] and r["criteres"][0]["sources_rejetees"] != ["RG-09 (règle inconnue)"]:
        echecs.append(("règle inconnue", r["criteres"][0]))
    # Couverture : la phrase sur la redirection n'est reprise par rien
    r = analyser(origine, bon, ["Q-1", "Q-2"])
    couv = {p["numero"]: p["statut"] for p in r["phrases"]}
    if couv != {1: "TITRE", 2: "COUVERTE", 3: "COUVERTE", 4: "NON_COUVERTE"}:
        echecs.append(("couverture", couv))
    # Format
    if analyser(origine, "pas de format", [])["code"] != 2:
        echecs.append(("mal formé", ""))
    sans_regles = bon.split("## Règles métier")[0] + "## Critères d'acceptation" + \
        bon.split("## Critères d'acceptation")[1]
    r = analyser(origine, sans_regles, ["Q-1"])
    if r["code"] != 2 or not any("Règles métier" in e for e in r["erreurs"]):
        echecs.append(("section règles obligatoire", r["erreurs"]))
    aucune = sans_regles.replace("## Critères d'acceptation",
                                 "## Règles métier\nAucune\n\n## Critères d'acceptation")
    aucune = aucune.replace("- **Règles** : RG-01", "- **Sources** : « durée limitée » ; Q-1")
    r = analyser(origine, aucune, ["Q-1"])
    if r["code"] == 2 or r["regles"] or statuts(r).get("CA-01") != "SOURCE":
        echecs.append(("règles : Aucune", r["erreurs"], statuts(r)))
    casse = bon.replace("« le nouveau mot de passe doit être sécurisé »",
                        "« Le nouveau mot de passe doit être sécurisé »")
    r = analyser(origine, casse, ["Q-1", "Q-2"])
    if not r["regles"] or r["regles"][1]["statut"] != "SOURCE":
        echecs.append(("casse tolérée", r["regles"][1:2]))
    mots = bon.replace("« le nouveau mot de passe doit être sécurisé »",
                       "« le mot de passe doit être sécurisé »")
    r = analyser(origine, mots, ["Q-1", "Q-2"])
    if not r["regles"] or r["regles"][1]["statut"] != "HYPOTHESE":
        echecs.append(("mot manquant refusé", r["regles"][1:2]))
    multi_blancs = bon.replace("valide pendant une durée", "valide  pendant  une durée")
    r = analyser(origine, multi_blancs, ["Q-1"])
    if not r["regles"] or r["regles"][0]["statut"] != "SOURCE":
        echecs.append(("blancs tolérés", r["regles"][:1]))
    variante = """### 1. **Exigence réécrite :**
En tant qu'utilisateur, je réinitialise mon mot de passe.

### 2. Règles de gestion
**RG-01** — expiration
- Règle : Le lien expire 30 minutes après son émission.
- Sources : « valide pendant une durée limitée » ; Q-1

### 3. Critères d’acceptation
**CA-01** — lien expiré
- Critère : Étant donné un lien émis, quand 30 minutes sont écoulées, alors il est refusé.
- Règles vérifiées : RG-01
"""
    r = analyser(origine, variante, ["Q-1"])
    if r["code"] != 0 or len(r["criteres"]) != 1 or r["criteres"][0]["regles"] != ["RG-01"]:
        echecs.append(("format tolérant", r["code"], r["erreurs"], r["criteres"]))
    avec_points = variante + "\n## Points ouverts\n- Notification après succès non précisée (Q-3)\n"
    r = analyser(origine, avec_points, ["Q-1"])
    if r["code"] != 0 or len(r["criteres"]) != 1:
        echecs.append(("points ouverts hors critères", r["code"], r["criteres"]))
    if r["points"] != ["Notification après succès non précisée (Q-3)"]:
        echecs.append(("points ouverts", r["points"]))
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
    r = analyser(origine, rapport, repondues)
    for e in r["erreurs"]:
        print("[ERREUR] " + e)
    for c in r["regles"] + r["criteres"]:
        print("%s : %s %s" % (c["code"], c.get("statut", "?"),
                              ("(rejetées : %s)" % ", ".join(c["sources_rejetees"]))
                              if c.get("sources_rejetees") else ""))
    for p in r["phrases"]:
        if p["statut"] == "NON_COUVERTE":
            print("[NON REPRISE] phrase %d : %s" % (p["numero"], p["texte"]))
    sys.exit(r["code"])
