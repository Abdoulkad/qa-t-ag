"""Exécution des tâches IA en arrière-plan (RA-39).

Mode "fond" : un fil d'exécution par tâche, la requête HTTP rend la main tout
de suite. Mode "immediat" : exécution dans la requête (tests automatisés).
Pour un usage à forte charge, ce module se remplace par une vraie file
(RQ, Celery) sans changer les routes.
"""
import threading

from sqlalchemy.orm import Session

from . import journal, regles, scripts_qa
from .config import parametres
from .db import SessionLocale
from .ia import agents, fournisseurs
from .models import ConfigIA, Defaut, Mission, QuestionMetier, TacheIA, VersionExigence, maintenant


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


def executer(tache_id: int) -> None:
    with SessionLocale() as db:
        tache = db.get(TacheIA, tache_id)
        tache.etat = "EN_COURS"
        db.commit()
        try:
            if tache.type == "ANALYSE":
                _analyser(db, tache)
            else:
                raise ValueError("type de tâche inconnu : %s" % tache.type)
            tache.etat = "TERMINEE"
        except Exception as e:  # noqa: BLE001 — toute erreur est tracée, jamais avalée
            db.rollback()
            tache = db.get(TacheIA, tache_id)
            tache.etat = "ECHEC"
            tache.erreur = str(e)[:2000]
            mission = db.get(Mission, tache.mission_id)
            if mission.statut == "ANALYSE_EN_COURS":
                mission.statut = "ECHEC_ANALYSE"
            journal.ajouter(db, tache.organisation_id, "analyse_echec", mission_id=mission.id,
                            agent="AG-01", details={"erreur": str(e)[:300]})
        tache.termine_le = maintenant()
        db.commit()


def _analyser(db: Session, tache: TacheIA) -> None:
    """AG-01 : revue de l'exigence par l'IA, contrôle par controler_revue.py."""
    version = db.get(VersionExigence, tache.version_id)
    mission = db.get(Mission, tache.mission_id)
    config = db.get(ConfigIA, mission.organisation_id)
    if config is None:
        raise fournisseurs.ErreurIA("Aucune IA configurée : un administrateur doit en "
                                    "choisir une dans la configuration.")
    rapport = fournisseurs.generer(config.fournisseur, config.modele,
                                   agents.prompt_skill("qa-revue-sfd"),
                                   agents.consigne_revue(version.texte))
    controle = scripts_qa.analyser_rapport_revue(rapport, version.texte)
    if controle["code"] == 2:
        raise ValueError("Rapport de revue mal formé : " + "; ".join(controle["erreurs"]))

    version.fournisseur_ia = config.fournisseur          # RA-38
    version.modele_ia = config.modele
    version.rapport_revue = rapport
    version.code_controle_revue = controle["code"]
    version.controle_revue = "\n".join(controle["erreurs"]) or "Citations toutes vérifiées"
    version.score_clarte = regles.score_clarte([d["gravite"] for d in controle["defauts"]])

    for d in controle["defauts"]:
        defaut = Defaut(version_id=version.id, code=d["code"], categorie=d["categorie"],
                        gravite=d["gravite"], section=d["section"], citation=d["citation"],
                        citation_verifiee=d["citation_verifiee"])
        db.add(defaut)
        db.flush()
        if d["question"]:
            db.add(QuestionMetier(version_id=version.id, defaut_id=defaut.id,
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
