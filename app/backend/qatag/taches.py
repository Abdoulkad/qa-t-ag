"""Exécution des tâches IA en arrière-plan (RA-39).

Mode "fond" : un fil d'exécution par tâche, la requête HTTP rend la main tout
de suite. Mode "immediat" : exécution dans la requête (tests automatisés).
Pour un usage à forte charge, ce module se remplace par une vraie file
(RQ, Celery) sans changer les routes.

Trois tâches, chacune = un agent IA + un contrôle par script :
- ANALYSE    (AG-01)  : revue de l'exigence      -> controler_revue.py
- REECRITURE           : exigence réécrite         -> verifier_reecriture.py
- CONCEPTION (AG-02/03): cas de test + traçabilité -> controler_cas.py
"""
import threading

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from . import journal, regles, scripts_qa
from .config import parametres
from .db import SessionLocale
from .ia import agents, fournisseurs
from .models import (CasTest, ConfigIA, CritereAcceptation, Defaut, Mission, QuestionMetier,
                     TacheIA, Trace, VersionExigence, maintenant)

# Statut de mission pendant la tâche -> statut si la tâche échoue
REPLI_SUR_ECHEC = {
    "ANALYSE": ("ANALYSE_EN_COURS", "ECHEC_ANALYSE"),
    "REECRITURE": ("REECRITURE", "CLARIFICATION"),
    "CONCEPTION": ("CONCEPTION", None),          # reste en CONCEPTION, relançable
}


def lancer(db: Session, mission: Mission, version: VersionExigence, type_tache: str) -> TacheIA:
    tache = TacheIA(organisation_id=mission.organisation_id, mission_id=mission.id,
                    version_id=version.id, type=type_tache)
    db.add(tache)
    db.commit()
    if parametres().mode_taches == "immediat":
        executer(tache.id)
    else:
        threading.Thread(target=executer, args=(tache.id,), daemon=True).start()
    return tache


def en_cours(db: Session, mission_id: int) -> bool:
    return db.scalar(select(TacheIA.id).where(
        TacheIA.mission_id == mission_id,
        TacheIA.etat.in_(("EN_ATTENTE", "EN_COURS"))).limit(1)) is not None


def executer(tache_id: int) -> None:
    with SessionLocale() as db:
        tache = db.get(TacheIA, tache_id)
        tache.etat = "EN_COURS"
        db.commit()
        try:
            {"ANALYSE": _analyser, "REECRITURE": _reecrire,
             "CONCEPTION": _concevoir}[tache.type](db, tache)
            tache.etat = "TERMINEE"
        except Exception as e:  # noqa: BLE001 — toute erreur est tracée, jamais avalée
            db.rollback()
            tache = db.get(TacheIA, tache_id)
            tache.etat = "ECHEC"
            tache.erreur = str(e)[:2000]
            mission = db.get(Mission, tache.mission_id)
            pendant, repli = REPLI_SUR_ECHEC.get(tache.type, (None, None))
            if repli and mission.statut == pendant:
                mission.statut = repli
            journal.ajouter(db, tache.organisation_id, "%s_echec" % tache.type.lower(),
                            mission_id=mission.id, details={"erreur": str(e)[:300]})
        tache.termine_le = maintenant()
        db.commit()


def _generer_au_format(config: ConfigIA, systeme: str, consigne: str, controler):
    """Appelle l'IA puis contrôle le format ; une seule nouvelle tentative si le
    format est rejeté, en renvoyant à l'IA les erreurs du script.

    `controler(sortie)` renvoie (resultat, erreurs) ; erreurs vide = conforme.
    En cas d'échec, l'erreur cite le début de la réponse pour le diagnostic.
    """
    sortie = fournisseurs.generer(config.fournisseur, config.modele, systeme, consigne)
    resultat, erreurs = controler(sortie)
    if not erreurs:
        return sortie, resultat, 1
    relance = (consigne + "\n\n---\nTa réponse précédente a été REJETÉE par le script de "
               "contrôle pour ces raisons :\n- " + "\n- ".join(erreurs) +
               "\nRecommence en respectant EXACTEMENT le format du contrat, sans rien "
               "avant ni après.")
    sortie = fournisseurs.generer(config.fournisseur, config.modele, systeme, relance)
    resultat, erreurs = controler(sortie)
    if erreurs:
        debut = " ".join(sortie.split())[:300]
        raise ValueError("%s (après 2 tentatives). Début de la réponse de l'IA : « %s »"
                         % ("; ".join(erreurs), debut))
    return sortie, resultat, 2


def _config(db: Session, organisation_id: int) -> ConfigIA:
    config = db.get(ConfigIA, organisation_id)
    if config is None:
        raise fournisseurs.ErreurIA("Aucune IA configurée : un administrateur doit en "
                                    "choisir une dans la configuration.")
    return config


def _analyser(db: Session, tache: TacheIA) -> None:
    """AG-01 : revue de l'exigence par l'IA, contrôle par controler_revue.py."""
    version = db.get(VersionExigence, tache.version_id)
    mission = db.get(Mission, tache.mission_id)
    config = _config(db, mission.organisation_id)
    def controler(sortie):
        c = scripts_qa.analyser_rapport_revue(sortie, version.texte)
        return c, (["rapport de revue mal formé : " + e for e in c["erreurs"]]
                   if c["code"] == 2 else [])
    rapport, controle, tentatives = _generer_au_format(
        config, agents.prompt_skill("qa-revue-sfd"), agents.consigne_revue(version.texte),
        controler)
    if tentatives > 1:
        controle["corrections"].append("format corrigé par l'IA à la 2e tentative")

    version.fournisseur_ia = config.fournisseur          # RA-38
    version.modele_ia = config.modele
    version.rapport_revue = rapport
    version.code_controle_revue = controle["code"]
    version.controle_revue = "\n".join(controle["corrections"] + controle["erreurs"]) \
        or "Citations toutes vérifiées"
    version.score_clarte = regles.score_clarte([d["gravite"] for d in controle["defauts"]])

    n = 0
    for d in controle["defauts"]:
        defaut = Defaut(version_id=version.id, code=d["code"], categorie=d["categorie"],
                        gravite=d["gravite"], section=d["section"], citation=d["citation"],
                        citation_verifiee=d["citation_verifiee"])
        db.add(defaut)
        db.flush()
        if d["question"]:
            n += 1
            db.add(QuestionMetier(version_id=version.id, defaut_id=defaut.id, code="Q-%d" % n,
                                  question=d["question"],
                                  bloquante=d["gravite"] == "Bloquante"))

    regles.verifier_transition(mission.statut, "CLARIFICATION")
    mission.statut = "CLARIFICATION"
    journal.ajouter(db, mission.organisation_id, "analyse_terminee", mission_id=mission.id,
                    agent="AG-01", details={
                        "version": version.numero, "defauts": len(controle["defauts"]),
                        "score_clarte": version.score_clarte,
                        "controle": controle["code"],
                        "ia": "%s/%s" % (config.fournisseur, config.modele)})


def _reecrire(db: Session, tache: TacheIA) -> None:
    """Réécriture sourcée ; verifier_reecriture.py tranche SOURCE / HYPOTHESE (RA-19, RA-20)."""
    version = db.get(VersionExigence, tache.version_id)
    mission = db.get(Mission, tache.mission_id)
    config = _config(db, mission.organisation_id)
    questions = [{"code": q.code, "question": q.question, "reponse": q.reponse}
                 for q in version.questions]
    defauts = [{"code": d.code, "categorie": d.categorie, "gravite": d.gravite,
                "citation": d.citation} for d in version.defauts]
    repondues = [q["code"] for q in questions if (q["reponse"] or "").strip()]

    def controler(sortie):
        c = scripts_qa.verifier_reecriture(version.texte, sortie, repondues)
        return c, (["réécriture mal formée : " + e for e in c["erreurs"]]
                   if c["code"] == 2 else [])
    rapport, controle, _ = _generer_au_format(
        config, agents.prompt_skill("qa-reecriture"),
        agents.consigne_reecriture(version.texte, defauts, questions), controler)

    db.execute(delete(CritereAcceptation).where(CritereAcceptation.version_id == version.id))
    for c in controle["criteres"]:
        db.add(CritereAcceptation(version_id=version.id, code=c["code"], texte=c["texte"],
                                  sources=c["sources"], sources_rejetees=c["sources_rejetees"],
                                  statut=c["statut"]))
    version.texte_reecrit = controle["texte"]
    hypotheses = [c["code"] for c in controle["criteres"] if c["statut"] == "HYPOTHESE"]
    version.controle_reecriture = (
        "Hypothèses à trancher : %s" % ", ".join(hypotheses) if hypotheses
        else "Tous les critères sont sourcés")

    regles.verifier_transition(mission.statut, "ATTENTE_PV1")
    mission.statut = "ATTENTE_PV1"
    journal.ajouter(db, mission.organisation_id, "reecriture_terminee", mission_id=mission.id,
                    details={"version": version.numero, "criteres": len(controle["criteres"]),
                             "hypotheses": hypotheses,
                             "ia": "%s/%s" % (config.fournisseur, config.modele)})


def _concevoir(db: Session, tache: TacheIA) -> None:
    """AG-02 conception + AG-03 traçabilité ; statuts des cas calculés (RA-22 à RA-25)."""
    version = db.get(VersionExigence, tache.version_id)
    mission = db.get(Mission, tache.mission_id)
    config = _config(db, mission.organisation_id)
    criteres = [{"code": c.code, "texte": c.texte} for c in version.criteres]
    reference = "\n\n".join([version.texte, version.texte_reecrit or ""] +
                            ["%s : %s" % (c["code"], c["texte"]) for c in criteres])

    def controler(sortie):
        csv_texte, justifs = scripts_qa.separer_conception(sortie)
        if not csv_texte.strip():
            return None, ["aucun CSV exploitable (l'en-tête ID;Titre;… est introuvable)"]
        c = scripts_qa.controler_cas(reference, scripts_qa.normaliser_csv(csv_texte))
        c["justifications"] = justifs
        if c["code"] in (2, 3):
            lignes = [l for l in c["message"].splitlines() if l.startswith("[ERREUR]")]
            return c, ["cas de test mal formés : " + l for l in lignes[:10]] or [c["message"][:300]]
        return c, []
    _, controle, _ = _generer_au_format(
        config, agents.prompt_skill("qa-conception"),
        agents.consigne_conception(version.texte_reecrit or version.texte, criteres, version.texte),
        controler)
    justifications = controle["justifications"]

    references_connues = ({c["code"] for c in criteres} |
                          set(scripts_qa.references(version.texte)))
    anciens = select(CasTest.id).where(CasTest.version_id == version.id)
    db.execute(delete(Trace).where(Trace.cas_id.in_(anciens)))
    db.execute(delete(CasTest).where(CasTest.version_id == version.id))
    for (code, titre, objectif, exigence, technique, priorite, type_, pre, donnees, etapes,
         resultat, statut_ia) in controle["lignes"]:
        code = code.strip()
        statut, motif = regles.statut_cas(pre, donnees, resultat,
                                          scripts_qa.statut_agent(statut_ia))
        justification = justifications.get(code, "").strip()
        refs = scripts_qa.references(exigence)
        inconnues = [r for r in refs if r not in references_connues]
        problemes = []
        if not justification:
            problemes.append("technique non justifiée")                # RA-22
        if not refs:
            problemes.append("aucune exigence tracée")                 # RA-25
        if inconnues:
            problemes.append("référence inconnue : %s" % ", ".join(inconnues))
        if problemes and statut == "PRET":
            statut, motif = "INCOMPLET", "; ".join(problemes)
        elif problemes:
            motif = "; ".join([motif] + problemes)
        cas = CasTest(version_id=version.id, code=code, titre=titre.strip(),
                      objectif=objectif.strip(), exigence=exigence.strip(),
                      technique=technique.strip(), justification_technique=justification,
                      priorite=priorite.strip(), type=type_.strip(),
                      preconditions=pre.strip(), donnees_test=donnees.strip(),
                      etapes=etapes.strip(), resultat_attendu=resultat.strip(),
                      statut=statut, motif_statut=motif)
        db.add(cas)
        db.flush()
        for r in refs:
            if r in references_connues:
                db.add(Trace(cas_id=cas.id, reference=r))
    version.controle_conception = controle["message"][:4000]

    regles.verifier_transition(mission.statut, "ATTENTE_PV2")
    mission.statut = "ATTENTE_PV2"
    journal.ajouter(db, mission.organisation_id, "conception_terminee", mission_id=mission.id,
                    agent="AG-02", details={"version": version.numero,
                                           "cas": len(controle["lignes"]),
                                           "controle": controle["code"],
                                           "ia": "%s/%s" % (config.fournisseur, config.modele)})
