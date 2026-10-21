import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import missions as svc
from ..db import session_db
from ..deps import acteur_mission, utilisateur_courant
from ..extraction import FichierRefuse, extraire
from ..models import (DecisionPorte, EntreeJournal, Execution, Mission, TacheIA, Utilisateur,
                      CasTest, VersionExigence)
from ..regles import PORTES
from .schemas import AjoutParticipant, CreationMission, Decision, NouvelleVersion

routeur = APIRouter(prefix="/api", tags=["Missions"])


def _mission(db: Session, u: Utilisateur, mission_id: int) -> Mission:
    m = svc.obtenir(db, u, mission_id)
    if m is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mission introuvable")
    return m


def _resume(m: Mission) -> dict:
    v = svc.version_courante(m)
    return {"id": m.id, "reference": m.reference, "titre": m.titre, "statut": m.statut,
            "version": v.numero, "score_clarte": v.score_clarte,
            "nb_defauts": len(v.defauts), "cree_le": m.cree_le, "modifie_le": m.modifie_le}


def _version(db: Session, v: VersionExigence) -> dict:
    decisions = db.scalars(select(DecisionPorte).where(DecisionPorte.version_id == v.id)
                           .order_by(DecisionPorte.id)).all()
    return {
        "id": v.id, "numero": v.numero, "texte": v.texte, "nom_source": v.nom_source,
        "empreinte": v.empreinte, "auteur_id": v.auteur_id, "figee": v.figee,
        "ia": {"fournisseur": v.fournisseur_ia, "modele": v.modele_ia},
        "score_clarte": v.score_clarte, "controle_revue": v.controle_revue,
        "code_controle_revue": v.code_controle_revue, "cree_le": v.cree_le,
        "defauts": [{"id": d.id, "code": d.code, "categorie": d.categorie, "gravite": d.gravite,
                     "section": d.section, "citation": d.citation,
                     "citation_verifiee": d.citation_verifiee} for d in v.defauts],
        "questions": [{"id": q.id, "defaut_id": q.defaut_id, "question": q.question,
                       "bloquante": q.bloquante, "reponse": q.reponse,
                       "repondu_par_id": q.repondu_par_id, "repondu_le": q.repondu_le}
                      for q in v.questions],
        "decisions": [{"porte": d.porte, "decision": d.decision, "commentaire": d.commentaire,
                       "decideur_id": d.decideur_id, "auto_validation": d.auto_validation,
                       "decide_le": d.decide_le} for d in decisions],
    }


@routeur.get("/missions")
def lister(statut: str | None = None, u: Utilisateur = Depends(utilisateur_courant),
           db: Session = Depends(session_db)):
    requete = svc.visible_par(u).order_by(Mission.id.desc())
    if statut:
        requete = requete.where(Mission.statut == statut)
    return [_resume(m) for m in db.scalars(requete).all()]


@routeur.post("/missions", status_code=201)
def creer(entree: CreationMission, u: Utilisateur = Depends(acteur_mission),
          db: Session = Depends(session_db)):
    m, tache = svc.creer(db, u, entree.titre, entree.texte.strip())
    return {"mission": _resume(m), "tache_id": tache.id}


@routeur.post("/missions/fichier", status_code=201)
async def creer_depuis_fichier(titre: str = Form(..., min_length=1, max_length=300),
                               fichier: UploadFile = File(...),
                               u: Utilisateur = Depends(acteur_mission),
                               db: Session = Depends(session_db)):
    try:
        texte = extraire(fichier.filename or "", await fichier.read())
    except FichierRefuse as e:
        raise HTTPException(422, str(e)) from e
    m, tache = svc.creer(db, u, titre, texte, nom_source=fichier.filename)
    return {"mission": _resume(m), "tache_id": tache.id}


@routeur.get("/missions/{mission_id}")
def detail(mission_id: int, u: Utilisateur = Depends(utilisateur_courant),
           db: Session = Depends(session_db)):
    m = _mission(db, u, mission_id)
    taches_en_cours = db.scalars(select(TacheIA).where(
        TacheIA.mission_id == m.id, TacheIA.etat.in_(("EN_ATTENTE", "EN_COURS")))).all()
    v = svc.version_courante(m)
    porte = next((p for p, (attente, _) in PORTES.items() if attente == m.statut), None)
    return {
        **_resume(m),
        "participants": [{"id": p.utilisateur.id, "email": p.utilisateur.email,
                          "nom": p.utilisateur.nom} for p in m.participants],
        "versions": [_version(db, x) for x in m.versions],
        "taches_en_cours": [t.id for t in taches_en_cours],
        "porte_en_attente": porte,
        "bloquants_porte": svc.bloquants_porte(db, porte, v)[1] if porte else [],
    }


@routeur.post("/missions/{mission_id}/versions", status_code=201)
def nouvelle_version(mission_id: int, entree: NouvelleVersion,
                     u: Utilisateur = Depends(acteur_mission), db: Session = Depends(session_db)):
    m = _mission(db, u, mission_id)
    v, tache = svc.nouvelle_version(db, u, m, entree.texte.strip())
    return {"version": v.numero, "tache_id": tache.id}


@routeur.post("/missions/{mission_id}/participants", status_code=201)
def ajouter_participant(mission_id: int, entree: AjoutParticipant,
                        u: Utilisateur = Depends(acteur_mission), db: Session = Depends(session_db)):
    m = _mission(db, u, mission_id)
    cible = svc.ajouter_participant(db, u, m, entree.email)
    return {"id": cible.id, "email": cible.email}


@routeur.post("/missions/{mission_id}/portes/{porte}")
def decider(mission_id: int, porte: str, entree: Decision,
            u: Utilisateur = Depends(acteur_mission), db: Session = Depends(session_db)):
    m = _mission(db, u, mission_id)
    d = svc.decider(db, u, m, porte, entree.decision, entree.commentaire)
    return {"porte": d.porte, "decision": d.decision, "auto_validation": d.auto_validation,
            "statut_mission": m.statut}


@routeur.get("/taches/{tache_id}")
def tache(tache_id: int, u: Utilisateur = Depends(utilisateur_courant),
          db: Session = Depends(session_db)):
    t = db.get(TacheIA, tache_id)
    if t is None or svc.obtenir(db, u, t.mission_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tâche introuvable")
    return {"id": t.id, "type": t.type, "etat": t.etat, "erreur": t.erreur,
            "mission_id": t.mission_id, "cree_le": t.cree_le, "termine_le": t.termine_le}


def _entree(e: EntreeJournal) -> dict:
    return {"id": e.id, "mission_id": e.mission_id, "acteur_id": e.acteur_id, "agent": e.agent,
            "evenement": e.evenement, "details": json.loads(e.details),
            "horodatage": e.horodatage}


@routeur.get("/journal")
def journal_recent(limite: int = 30, u: Utilisateur = Depends(utilisateur_courant),
                   db: Session = Depends(session_db)):
    ids_visibles = select(svc.visible_par(u).subquery().c.id)
    entrees = db.scalars(select(EntreeJournal).where(
        EntreeJournal.organisation_id == u.organisation_id,
        EntreeJournal.mission_id.in_(ids_visibles))
        .order_by(EntreeJournal.id.desc()).limit(min(limite, 200))).all()
    return [_entree(e) for e in entrees]


@routeur.get("/missions/{mission_id}/journal")
def journal_mission(mission_id: int, u: Utilisateur = Depends(utilisateur_courant),
                    db: Session = Depends(session_db)):
    m = _mission(db, u, mission_id)
    return [_entree(e) for e in db.scalars(select(EntreeJournal).where(
        EntreeJournal.mission_id == m.id).order_by(EntreeJournal.id)).all()]


@routeur.get("/pilotage")
def pilotage(u: Utilisateur = Depends(utilisateur_courant), db: Session = Depends(session_db)):
    """Indicateurs de la vue de pilotage, calculés en base (jamais estimés)."""
    ids = select(svc.visible_par(u).subquery().c.id)
    missions = db.scalars(select(Mission).where(Mission.id.in_(ids))).all()
    en_attente = [m for m in missions if m.statut in ("ATTENTE_PV1", "ATTENTE_PV2")]
    versions_ids = select(VersionExigence.id).where(VersionExigence.mission_id.in_(ids))
    execs = db.execute(select(Execution.statut, func.count()).join(
        CasTest, CasTest.id == Execution.cas_id).where(CasTest.version_id.in_(versions_ids))
        .group_by(Execution.statut)).all()
    executions = dict(execs)
    jouees = executions.get("PASS", 0) + executions.get("FAIL", 0)
    decisions = db.execute(select(DecisionPorte.decision, func.count()).where(
        DecisionPorte.version_id.in_(versions_ids)).group_by(DecisionPorte.decision)).all()
    dec = dict(decisions)
    total_dec = dec.get("APPROUVE", 0) + dec.get("REJETE", 0)
    return {
        "missions": len(missions),
        "human_gate_en_attente": len(en_attente),
        "taux_pass": round(100 * executions.get("PASS", 0) / jouees) if jouees else None,
        "taux_approbation": round(100 * dec.get("APPROUVE", 0) / total_dec) if total_dec else None,
        "file_human_gate": [_resume(m) for m in en_attente],
    }
