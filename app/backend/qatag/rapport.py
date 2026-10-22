"""Rapport de test rédigé (RA-66 à RA-68) : AG-11 propose, l'humain valide.

Les faits (compteurs, cas, anomalies, références) sont calculés ici ; le même
contrôle (`controler_rapport.py`) s'applique au texte d'AG-11, au texte corrigé
par l'humain, et de nouveau à l'export : un rapport validé qui ne correspond
plus aux résultats n'est pas remis.
"""
import json

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import journal, scripts_qa, taches
from .missions import version_courante
from .models import (Anomalie, CasTest, ClotureRecette, ConfigIA, Execution, Mission,
                     RapportRecette, Utilisateur, maintenant)
from .recette import dernieres_executions
from .regles import LIBELLES_TEST, RegleViolee

STATUTS_RAPPORT = ("EN_RECETTE", "CLOTUREE", "RESERVES_LEVEES")
CHAMPS = ("contexte", "objectifs", "synthese", "recommandations", "conclusion", "avis")


def faits(db: Session, m: Mission) -> tuple[dict, str]:
    """(faits pour le contrôle, texte des faits pour AG-11)."""
    v = version_courante(m)
    cas = db.scalars(select(CasTest).where(CasTest.version_id == v.id)
                     .order_by(CasTest.code)).all()
    dernieres = dernieres_executions(db, [c.id for c in cas])
    passages = dict(db.execute(select(Execution.cas_id, func.count()).where(
        Execution.cas_id.in_([c.id for c in cas])).group_by(Execution.cas_id)).all())
    compte = {"PASS": 0, "FAIL": 0, "BLOCKED": 0, "NOT_RUN": 0}
    for c in cas:
        e = dernieres.get(c.id)
        compte[e.statut if e else "NOT_RUN"] += 1
    anomalies = db.scalars(select(Anomalie).where(Anomalie.mission_id == m.id)
                           .order_by(Anomalie.code)).all()
    ouvertes = sum(1 for a in anomalies if a.statut in ("OUVERTE", "CORRIGEE"))
    cloture = db.scalar(select(ClotureRecette).where(ClotureRecette.mission_id == m.id))
    references = [r.code for r in v.regles] + [c.code for c in v.criteres]

    rejoues = [c.code for c in cas if passages.get(c.id, 0) > 1]
    nature = ("tests de confirmation : %s rejoué%s après la correction d'anomalies"
              % (", ".join(rejoues), "s" if len(rejoues) > 1 else "") if rejoues
              else "première exécution des cas validés à PV-2 (tests d'acceptance)")
    lignes = ["## Mission %s — fonctionnalité « %s »" % (m.reference, m.titre),
              "- Nature de la campagne : %s" % nature, ""]
    if v.texte_reecrit:
        lignes += ["## Exigence réécrite validée à PV-1", v.texte_reecrit, ""]
    if v.regles or v.criteres:
        lignes.append("## Règles et critères validés")
        lignes += ["- %s : %s" % (r.code, r.texte) for r in v.regles]
        lignes += ["- %s : %s" % (c.code, c.texte) for c in v.criteres]
        lignes.append("")
    lignes += ["## Compteurs (exacts)",
               "- Cas de test : %d" % len(cas),
               "- Exécutés (dernier passage réussi, en échec ou non testable) : %d"
               % (compte["PASS"] + compte["FAIL"] + compte["BLOCKED"]),
               "- Réussis : %d" % compte["PASS"], "- En échec : %d" % compte["FAIL"],
               "- Non testables : %d" % compte["BLOCKED"],
               "- Non exécutés : %d" % compte["NOT_RUN"],
               "- Anomalies : %d, dont %d ouvertes ou corrigées non retestées"
               % (len(anomalies), ouvertes), "", "## Cas"]
    for c in cas:
        e = dernieres.get(c.id)
        lignes.append("- %s — %s (priorité %s) : %s%s" % (
            c.code, c.titre, c.priorite or "—",
            LIBELLES_TEST[e.statut] if e else "non exécuté",
            ", %d passages" % passages[c.id] if passages.get(c.id, 0) > 1 else ""))
        lignes.append("  Objectif : %s" % (c.objectif or "—"))
        if e and e.resultat_obtenu:
            lignes.append("  Résultat obtenu : %s" % e.resultat_obtenu)
        if e and e.commentaire:
            lignes.append("  Commentaire du testeur : %s" % e.commentaire)
    lignes += ["", "## Anomalies"]
    lignes += ["- %s (cas %s) : %s — gravité %s, %s" % (
        a.code, next((c.code for c in cas if c.id == a.cas_id), "?"), a.titre,
        a.gravite or "non qualifiée", a.statut.lower()) for a in anomalies] or ["- aucune"]
    if cloture:
        lignes += ["", "## Clôture de la recette",
                   "- Décision : %s" % ("avec réserves" if cloture.decision ==
                                        "CLOTURE_AVEC_RESERVES" else "sans réserve")]
        if cloture.commentaire:
            lignes.append("- Motif : %s" % cloture.commentaire)
        lignes += ["- Réserve : %s" % r for r in json.loads(cloture.reserves)]
        if cloture.levee_le:
            lignes.append("- Réserves levées")
    texte = "\n".join(lignes)
    return ({"total": len(cas), "executes": compte["PASS"] + compte["FAIL"] + compte["BLOCKED"],
             **compte, "anomalies": [a.code for a in anomalies], "anomalies_ouvertes": ouvertes,
             "cas": [c.code for c in cas], "references": references, "texte": texte}, texte)


def vers_markdown(r: dict) -> str:
    """Texte au format du contrat d'AG-11, pour le contrôle."""
    lignes = ["## Contexte", r.get("contexte", ""), "## Objectifs"]
    lignes += ["- %s" % o for o in r.get("objectifs", []) if o.strip()]
    lignes += ["## Synthèse", r.get("synthese", ""), "## Recommandations"]
    recos = r.get("recommandations", {}) or {}
    lignes += ["- %s : %s" % (k, v) for k, v in recos.items() if v.strip()] or ["Aucune"]
    lignes += ["## Conclusion", r.get("conclusion", ""), "- **Avis** : %s" % r.get("avis", "")]
    return "\n".join(lignes)


def controler(texte: str, f: dict):
    return scripts_qa._module("controler_rapport").parser(texte, f)


def _rapport(db: Session, m: Mission) -> RapportRecette | None:
    return db.scalar(select(RapportRecette).where(RapportRecette.mission_id == m.id))


def _verifier(db: Session, m: Mission) -> None:
    if m.statut not in STATUTS_RAPPORT:
        raise RegleViolee("RA-66", "Le rapport se rédige une fois la recette commencée")


def etat(db: Session, m: Mission) -> dict | None:
    r = _rapport(db, m)
    if r is None:
        return None
    redaction = json.loads(r.redaction) if r.redaction else None
    erreurs = []
    if redaction and r.valide_le:                       # RA-68 : encore conforme aux faits ?
        erreurs = controler(vers_markdown(redaction), faits(db, m)[0])[1]
    personne = (lambda uid: (lambda p: {"nom": p.nom, "email": p.email} if p else None)(
        db.get(Utilisateur, uid)) if uid else None)
    return {"agent": {"etat": r.etat_agent, "erreur": r.erreur_agent, "ia": r.ia,
                      "propose_le": r.propose_le},
            "redaction": redaction, "modifie_le": r.modifie_le,
            "modifie_par": personne(r.modifie_par_id),
            "valide_le": r.valide_le, "valide_par": personne(r.valide_par_id),
            "a_revoir": erreurs}


def lancer_redaction(db: Session, u: Utilisateur, m: Mission):
    """RA-66 : AG-11 rédige en tâche de fond ; sa proposition remplace le texte en cours
    et annule une validation précédente."""
    _verifier(db, m)
    if db.get(ConfigIA, m.organisation_id) is None:
        raise RegleViolee("RA-37", "Aucune IA configurée : rédigez le rapport vous-même")
    f = faits(db, m)[0]
    if f["executes"] == 0:
        raise RegleViolee("RA-66", "Aucun cas exécuté : rien à rédiger pour l'instant")
    r = _rapport(db, m) or RapportRecette(mission_id=m.id)
    if r.etat_agent == "EN_COURS":
        raise RegleViolee("RA-66", "AG-11 rédige déjà le rapport")
    r.etat_agent, r.erreur_agent = "EN_COURS", None
    db.add(r)
    journal.ajouter(db, m.organisation_id, "rapport_redaction_lancee", mission_id=m.id,
                    acteur_id=u.id, details={})
    db.commit()
    return taches.lancer(db, m, version_courante(m), "RAPPORT", cible_id=r.id)


def enregistrer(db: Session, u: Utilisateur, m: Mission, redaction: dict, valider: bool):
    """RA-67 : l'humain corrige et valide. Le texte passe le même contrôle que celui
    d'AG-11 ; toute modification annule la validation précédente."""
    _verifier(db, m)
    propre = {
        "contexte": (redaction.get("contexte") or "").strip(),
        "objectifs": [o.strip() for o in redaction.get("objectifs") or [] if o.strip()],
        "synthese": (redaction.get("synthese") or "").strip(),
        "recommandations": {k.strip(): v.strip() for k, v in
                            (redaction.get("recommandations") or {}).items() if v.strip()},
        "conclusion": (redaction.get("conclusion") or "").strip(),
        "avis": (redaction.get("avis") or "").strip(),
    }
    r_controle, erreurs = controler(vers_markdown(propre), faits(db, m)[0])
    if erreurs:
        raise RegleViolee("RA-67", "Le rapport ne peut pas être enregistré : %d point(s) "
                                   "contraires aux faits ou au format" % len(erreurs), erreurs)
    r = _rapport(db, m) or RapportRecette(mission_id=m.id)
    db.add(r)
    r.redaction = json.dumps(r_controle, ensure_ascii=False)
    r.modifie_par_id, r.modifie_le = u.id, maintenant()
    r.valide_par_id, r.valide_le = (u.id, maintenant()) if valider else (None, None)
    journal.ajouter(db, m.organisation_id, "rapport_valide" if valider else "rapport_modifie",
                    mission_id=m.id, acteur_id=u.id, details={"avis": r_controle["avis"]})
    db.commit()
    return r


def pour_export(db: Session, m: Mission) -> tuple[dict | None, RapportRecette | None]:
    """RA-68 : le texte validé, recontrôlé contre les faits du moment ; None s'il n'y
    a pas de rapport validé (le cahier garde alors ses parties factuelles)."""
    r = _rapport(db, m)
    if r is None or r.valide_le is None or not r.redaction:
        return None, r
    redaction = json.loads(r.redaction)
    erreurs = controler(vers_markdown(redaction), faits(db, m)[0])[1]
    if erreurs:
        raise RegleViolee("RA-68", "Le rapport validé ne correspond plus aux résultats de la "
                                   "recette : mettez-le à jour dans l'onglet Rapport, puis "
                                   "validez-le de nouveau", erreurs)
    return redaction, r
