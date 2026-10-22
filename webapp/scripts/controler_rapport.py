#!/usr/bin/env python3
"""Contrôle déterministe de la rédaction du rapport de test (AG-11).

L'agent rédige le contexte, les objectifs, la synthèse, les recommandations et
la conclusion du rapport de test après exécution. Ce script vérifie le format
du contrat et, surtout, que le texte ne dit rien que les faits ne disent pas :

- chaque référence citée (CT-n, ANO-n, CA-n, RG-n) existe ;
- chaque nombre de cas ou d'anomalies cité correspond à un compteur réel,
  chaque pourcentage à une proportion réelle ;
- l'avis est compatible avec les résultats : « Favorable » seulement si tous
  les cas sont réussis et qu'aucune anomalie n'est ouverte ou corrigée ;
- aucune donnée personnelle (e-mail, téléphone) absente des faits.

Usage : python controler_rapport.py <redaction.md> <faits.json>
Codes : 0 = conforme, 2 = mal formé ou contraire aux faits, 3 = défaut du script.
Auto-test : python controler_rapport.py --selftest
"""

import json
import re
import sys

SECTIONS = ("Contexte", "Objectifs", "Synthèse", "Recommandations", "Conclusion")
AVIS = ("Favorable", "Favorable avec réserves", "Défavorable")
OBJECTIFS_MAX = 8

RE_SECTION = re.compile(r"^##\s+(.+?)\s*$")
RE_PUCE = re.compile(r"^\s*[-*•]\s+(.*)$")
RE_AVIS = re.compile(r"^\s*[-*]?\s*\*\*Avis\*\*\s*:\s*(.+?)\s*$")
RE_RECO = re.compile(r"^(CT-\d+)\s*:\s*(.+)$")
RE_REFERENCE = re.compile(r"\b(?:CT|ANO|CA|RG)-\d+\b")
RE_NOMBRE_CAS = re.compile(r"(?:\b|\()(\d+)\)?\s+cas\b", re.IGNORECASE)
RE_NOMBRE_ANO = re.compile(r"(?:\b|\()(\d+)\)?\s+anomalies?\b", re.IGNORECASE)
RE_POURCENT = re.compile(r"(\d+(?:[.,]\d+)?)\s*%")
RE_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
RE_TELEPHONE = re.compile(r"(?<!\d)(?:\+?\d[\s.-]?){8,}\d(?!\d)")


def _sections(texte: str):
    sections, courante, erreurs = {}, None, []
    for ligne in texte.splitlines():
        m = RE_SECTION.match(ligne)
        if m:
            courante = m.group(1).strip()
            if courante in sections:
                erreurs.append("section « %s » en double" % courante)
            sections[courante] = []
        elif courante is not None:
            sections[courante].append(ligne.rstrip())
    return sections, erreurs


def _paragraphes(lignes: list[str]) -> str:
    return "\n".join(l for l in (x.strip() for x in lignes) if l)


def parser(texte: str, faits: dict):
    """Retourne (redaction, erreurs). redaction = {contexte, objectifs[], synthese,
    recommandations{CT: texte}, conclusion, avis} ; erreurs vide = conforme.

    faits : {total, executes, PASS, FAIL, BLOCKED, NOT_RUN, anomalies[],
             anomalies_ouvertes, cas[], references[], texte}"""
    sections, erreurs = _sections(texte)
    noms = list(sections)
    for nom in SECTIONS:
        if nom not in sections:
            erreurs.append("section « ## %s » absente" % nom)
    inconnues = [n for n in noms if n not in SECTIONS]
    if inconnues:
        erreurs.append("section(s) inconnue(s) : %s" % ", ".join(inconnues))
    if not erreurs and noms != list(SECTIONS):
        erreurs.append("sections dans le désordre : attendu %s" % ", ".join(SECTIONS))
    if erreurs:
        return None, erreurs

    contexte = _paragraphes(sections["Contexte"])
    synthese = _paragraphes(sections["Synthèse"])
    objectifs = [RE_PUCE.match(l).group(1).strip() for l in sections["Objectifs"]
                 if RE_PUCE.match(l) and RE_PUCE.match(l).group(1).strip()]
    recommandations = {}
    reco_brut = [l for l in sections["Recommandations"] if l.strip()]
    if not (len(reco_brut) == 1 and reco_brut[0].strip().strip("-* ").rstrip(".") == "Aucune"):
        for l in reco_brut:
            m = RE_PUCE.match(l)
            r = RE_RECO.match(m.group(1).strip()) if m else None
            if not r:
                erreurs.append("recommandation mal formée (attendu « - CT-nnn : texte ») : %s"
                               % l.strip()[:80])
                continue
            if r.group(1) in recommandations:
                erreurs.append("deux recommandations pour %s" % r.group(1))
            recommandations[r.group(1)] = r.group(2).strip()
    avis, conclusion_lignes = None, []
    for l in sections["Conclusion"]:
        m = RE_AVIS.match(l)
        if m:
            if avis is not None:
                erreurs.append("avis donné deux fois")
            avis = m.group(1).strip().rstrip(".")
        elif l.strip():
            conclusion_lignes.append(l)
    conclusion = _paragraphes(conclusion_lignes)

    for nom, valeur in (("Contexte", contexte), ("Synthèse", synthese), ("Conclusion", conclusion)):
        if not valeur:
            erreurs.append("section « %s » vide" % nom)
    if not objectifs:
        erreurs.append("au moins un objectif en puce est attendu")
    if len(objectifs) > OBJECTIFS_MAX:
        erreurs.append("%d objectifs au plus" % OBJECTIFS_MAX)
    if avis is None:
        erreurs.append("ligne « - **Avis** : … » absente de la conclusion")
    elif avis not in AVIS:
        erreurs.append("avis « %s » non permis (valeurs : %s)" % (avis, ", ".join(AVIS)))
    if erreurs:
        return None, erreurs

    tout = "\n".join([contexte, synthese, conclusion] + objectifs + list(recommandations.values()))
    connues = set(faits.get("cas", [])) | set(faits.get("anomalies", [])) | \
        set(faits.get("references", []))
    for ref in sorted(set(RE_REFERENCE.findall(tout)) | set(recommandations)):
        if ref not in connues:
            erreurs.append("référence inconnue : %s" % ref)

    total = faits["total"]
    comptes = {faits[k] for k in ("total", "executes", "PASS", "FAIL", "BLOCKED", "NOT_RUN")}
    for n in RE_NOMBRE_CAS.findall(tout):
        if int(n) not in comptes:
            erreurs.append("« %s cas » ne correspond à aucun compteur (%s)"
                           % (n, ", ".join(str(x) for x in sorted(comptes))))
    nb_ano = {len(faits.get("anomalies", [])), faits.get("anomalies_ouvertes", 0)}
    for n in RE_NOMBRE_ANO.findall(tout):
        if int(n) not in nb_ano:
            erreurs.append("« %s anomalie(s) » ne correspond à aucun compteur" % n)
    if total:
        proportions = {round(100 * faits[k] / total)
                       for k in ("executes", "PASS", "FAIL", "BLOCKED", "NOT_RUN")} | {100, 0}
        for p in RE_POURCENT.findall(tout):
            if round(float(p.replace(",", "."))) not in proportions:
                erreurs.append("pourcentage %s %% ne correspond à aucune proportion réelle" % p)

    tout_ok = (faits["PASS"] == total and faits.get("anomalies_ouvertes", 0) == 0)
    if avis == "Favorable" and not tout_ok:
        erreurs.append("avis « Favorable » impossible : des cas ne sont pas réussis ou des "
                       "anomalies restent ouvertes ; écris « Favorable avec réserves » ou "
                       "« Défavorable »")

    for motif, nature in ((RE_EMAIL, "adresse e-mail"), (RE_TELEPHONE, "numéro de téléphone")):
        for trouve in motif.findall(tout):
            if trouve not in faits.get("texte", ""):
                erreurs.append("donnée personnelle (%s) : retire-la" % nature)
    if erreurs:
        return None, erreurs
    return {"contexte": contexte, "objectifs": objectifs, "synthese": synthese,
            "recommandations": recommandations, "conclusion": conclusion, "avis": avis}, []


def _auto_test() -> int:
    faits = {"total": 4, "executes": 3, "PASS": 2, "FAIL": 1, "BLOCKED": 0, "NOT_RUN": 1,
             "anomalies": ["ANO-001"], "anomalies_ouvertes": 1,
             "cas": ["CT-001", "CT-002", "CT-003", "CT-004"], "references": ["CA-01", "RG-01"],
             "texte": ""}
    bon = """## Contexte
Campagne de recette de la réinitialisation du mot de passe (version 1).
## Objectifs
- Vérifier le refus d'un lien expiré (CA-01).
- Vérifier la règle de longueur (RG-01).
## Synthèse
Sur les quatre (04) cas de test, 3 cas ont été exécutés : 2 cas réussis (50 %), 1 cas en échec.
Une anomalie reste ouverte (ANO-001).
## Recommandations
- CT-001 : corriger ANO-001 puis rejouer le cas.
## Conclusion
La fonctionnalité n'est pas encore conforme sur le refus des liens expirés.
- **Avis** : Favorable avec réserves
"""
    r, e = parser(bon, faits)
    assert not e, e
    assert r["avis"] == "Favorable avec réserves" and r["recommandations"]["CT-001"]
    assert len(r["objectifs"]) == 2
    assert parser(bon.replace("Favorable avec réserves", "Favorable"), faits)[1]
    assert parser(bon.replace("3 cas ont", "5 cas ont"), faits)[1]
    assert parser(bon.replace("(50 %)", "(60 %)"), faits)[1]
    assert parser(bon.replace("ANO-001 puis", "ANO-009 puis"), faits)[1]
    assert parser(bon.replace("- CT-001 :", "- CT-007 :"), faits)[1]
    assert parser(bon.replace("## Synthèse", "## Résumé"), faits)[1]
    assert parser(bon.replace("- **Avis** : Favorable avec réserves\n", ""), faits)[1]
    assert parser(bon.replace("(version 1).", "(contact a.b@c.ci)."), faits)[1]
    assert not parser(bon.replace("- CT-001 : corriger ANO-001 puis rejouer le cas.",
                                  "Aucune"), faits)[1]
    tout_bon = dict(faits, PASS=4, FAIL=0, NOT_RUN=0, executes=4, anomalies_ouvertes=0)
    favorable = bon.replace("3 cas ont été exécutés : 2 cas réussis (50 %), 1 cas en échec",
                            "4 cas ont été exécutés et réussis (100 %)")
    favorable = favorable.replace("Une anomalie reste ouverte (ANO-001).",
                                  "1 anomalie a été corrigée puis fermée.")
    assert not parser(favorable.replace("Favorable avec réserves", "Favorable"), tout_bon)[1]
    print("auto-test OK")
    return 0


def main(argv) -> int:
    if len(argv) == 2 and argv[1] == "--selftest":
        return _auto_test()
    if len(argv) != 3:
        print(__doc__)
        return 2
    try:
        texte = open(argv[1], encoding="utf-8").read()
        faits = json.load(open(argv[2], encoding="utf-8"))
    except (OSError, ValueError) as e:
        print("entrée inexploitable : %s" % e)
        return 2
    try:
        r, erreurs = parser(texte, faits)
    except Exception as e:  # noqa: BLE001
        print("défaut du script : %s" % e)
        return 3
    if erreurs:
        print("\n".join(erreurs))
        return 2
    print("Avis : %s · %d objectif(s) · %d recommandation(s)"
          % (r["avis"], len(r["objectifs"]), len(r["recommandations"])))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
