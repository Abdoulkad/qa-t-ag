import json

from urllib.parse import quote

from fastapi import (APIRouter, Depends, File, Form, HTTPException, Response, UploadFile,
                     status)
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import missions as svc
from ..db import session_db
from ..deps import acteur_mission, utilisateur_courant
from ..extraction import FichierRefuse, extraire
from ..models import (CasTest, DecisionPorte, EntreeJournal, Execution, Mission, TacheIA, Trace,
                      Utilisateur, VersionExigence)
from ..regles import PORTES
from .schemas import (AjoutParticipant, CreationMission, Decision, DecisionQuestions,
                      EcartCritere, EcartCriteres, JustificationPhrases, ModificationCas,
                      NouvelleVersion, Precision, Requalification, ValidationDefauts,
                      Reponse)

routeur = APIRouter(prefix="/api", tags=["Missions"])


def _mission(db: Session, u: Utilisateur, mission_id: int) -> Mission:
    m = svc.obtenir(db, u, mission_id)
    if m is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mission introuvable")
    return m


def _resume(m: Mission, db: Session | None = None) -> dict:
    v = svc.version_courante(m)
    r = {"id": m.id, "reference": m.reference, "titre": m.titre, "statut": m.statut,
         "version": v.numero, "score_clarte": v.score_clarte,
         "nb_defauts": len(v.defauts), "cree_le": m.cree_le, "modifie_le": m.modifie_le}
    if db is not None:
        r.update(_situation(db, m, v))
    return r


def _situation(db: Session, m: Mission, v: VersionExigence) -> dict:
    """Ce qui attend une action sur la mission, calculé par le serveur (vue de pilotage
    et repères de la mission) : prochaine action, questions bloquantes, échec d'agent,
    avancement des cas."""
    bloquantes = [q.code for q in v.questions
                  if q.bloquante and not (q.reponse or "").strip() and not q.decision]
    tache = db.scalar(select(TacheIA).where(TacheIA.mission_id == m.id)
                      .order_by(TacheIA.id.desc()).limit(1))
    occupe = tache is not None and tache.etat in ("EN_ATTENTE", "EN_COURS")
    echec = None
    if m.statut == "ECHEC_ANALYSE":
        echec = "analyse en échec"
    elif m.statut == "CONCEPTION" and not occupe and tache is not None and tache.etat == "ECHEC":
        echec = "conception en échec"
    porte = next((p for p, (attente, _) in PORTES.items() if attente == m.statut), None)
    n_bloquants = len(svc.bloquants_porte(db, porte, v)[1]) if porte else 0
    cas = db.execute(select(CasTest.statut, func.count()).where(CasTest.version_id == v.id)
                     .group_by(CasTest.statut)).all()
    compte = dict(cas)
    if occupe:
        action = {"ANALYSE": "Analyse en cours", "REECRITURE": "Réécriture en cours",
                  "CONCEPTION": "Conception en cours"}.get(tache.type, "Agent au travail")
    elif echec:
        action = "Relancer l'analyse" if m.statut == "ECHEC_ANALYSE" else "Relancer la conception"
    elif m.statut == "CLARIFICATION":
        n = len(bloquantes)
        pluriel = "s" if n > 1 else ""
        action = ("Traiter %d question%s bloquante%s" % (n, pluriel, pluriel) if n
                  else "Lancer la réécriture")
    elif porte:
        action = "Décider %s" % porte + (" · %d point%s à traiter" % (n_bloquants, "s" * (n_bloquants > 1))
                                         if n_bloquants else "")
    else:
        action = {"VALIDEE": "Prête pour la recette", "A_CORRIGER": "Corriger et resoumettre",
                  "EN_RECETTE": "Recette en cours", "CLOTUREE": "Clôturée"}.get(m.statut, "—")
    return {"prochaine_action": action, "questions_bloquantes": bloquantes, "en_echec": echec,
            "occupe": occupe, "bloquants": n_bloquants,
            "cas": {"total": sum(compte.values()), "prets": compte.get("PRET", 0)}}


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
                     "citation_verifiee": d.citation_verifiee, "constat": d.constat,
                     "justification": d.justification, "validation": d.validation,
                     "motif_validation": d.motif_validation,
                     "gravite_initiale": d.gravite_initiale,
                     "motif_requalification": d.motif_requalification,
                     "valide_le": d.valide_le} for d in v.defauts],
        "questions": [{"id": q.id, "code": q.code, "defaut_id": q.defaut_id,
                       "question": q.question, "bloquante": q.bloquante, "reponse": q.reponse,
                       "ajoutee_par_humain": q.ajoutee_par_id is not None,
                       "nature": q.nature, "sujet": q.sujet, "pourquoi": q.pourquoi,
                       "decision": q.decision, "motif_decision": q.motif_decision,
                       "decide_le": q.decide_le,
                       "repondu_par_id": q.repondu_par_id, "repondu_le": q.repondu_le}
                      for q in v.questions],
        "texte_reecrit": v.texte_reecrit, "controle_reecriture": v.controle_reecriture,
        "points_ouverts": v.points_ouverts or [],
        "controle_conception": v.controle_conception,
        "regles": [{"id": r.id, "code": r.code, "texte": r.texte, "sources": r.sources,
                    "sources_rejetees": r.sources_rejetees, "statut": r.statut,
                    "criteres": [c.code for c in v.criteres if r.code in c.regles]}
                   for r in v.regles],
        "criteres": [{"id": c.id, "code": c.code, "texte": c.texte, "sources": c.sources,
                      "sources_rejetees": c.sources_rejetees, "regles": c.regles,
                      "statut": c.statut}
                     for c in v.criteres],
        "couverture": svc.couverture(v),
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
    return [_resume(m, db) for m in db.scalars(requete).all()]


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
    derniere = db.scalar(select(TacheIA).where(TacheIA.mission_id == m.id)
                         .order_by(TacheIA.id.desc()).limit(1))
    v = svc.version_courante(m)
    porte = next((p for p, (attente, _) in PORTES.items() if attente == m.statut), None)
    return {
        **_resume(m, db),
        "participants": [{"id": p.utilisateur.id, "email": p.utilisateur.email,
                          "nom": p.utilisateur.nom} for p in m.participants],
        "versions": [_version(db, x) for x in m.versions],
        "taches_en_cours": [t.id for t in taches_en_cours],
        "derniere_tache": ({"id": derniere.id, "type": derniere.type, "etat": derniere.etat,
                            "erreur": derniere.erreur, "termine_le": derniere.termine_le}
                           if derniere else None),
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
        "file_human_gate": [_resume(m, db) for m in en_attente],
        # Les quatre cartes « à faire » de la vue de pilotage
        "questions_bloquantes": [r for r in (_resume(m, db) for m in missions
                                             if m.statut == "CLARIFICATION")
                                 if r["questions_bloquantes"]],
        "en_echec": [r for r in (_resume(m, db) for m in missions
                                 if m.statut in ("ECHEC_ANALYSE", "CONCEPTION")) if r["en_echec"]],
        "pretes_recette": [_resume(m, db) for m in missions if m.statut == "VALIDEE"],
    }


# --- Lot 2 : clarification, réécriture, conception -------------------------

@routeur.put("/missions/{mission_id}/questions/{question_id}")
def repondre(mission_id: int, question_id: int, entree: Reponse,
             u: Utilisateur = Depends(acteur_mission), db: Session = Depends(session_db)):
    q = svc.repondre(db, u, _mission(db, u, mission_id), question_id, entree.reponse)
    return {"id": q.id, "code": q.code, "reponse": q.reponse, "repondu_le": q.repondu_le}


@routeur.post("/missions/{mission_id}/questions", status_code=201)
def ajouter_precision(mission_id: int, entree: Precision,
                      u: Utilisateur = Depends(acteur_mission), db: Session = Depends(session_db)):
    q = svc.ajouter_precision(db, u, _mission(db, u, mission_id), entree.question, entree.reponse)
    return {"id": q.id, "code": q.code}


@routeur.post("/missions/{mission_id}/reecriture", status_code=202)
def reecrire(mission_id: int, u: Utilisateur = Depends(acteur_mission),
             db: Session = Depends(session_db)):
    t = svc.lancer_reecriture(db, u, _mission(db, u, mission_id))
    return {"tache_id": t.id}


@routeur.put("/missions/{mission_id}/questions-decision")
def decider_questions(mission_id: int, entree: DecisionQuestions,
                      u: Utilisateur = Depends(acteur_mission), db: Session = Depends(session_db)):
    n = svc.decider_questions(db, u, _mission(db, u, mission_id), entree.ids, entree.decision,
                              entree.motif)
    return {"questions": n}


@routeur.delete("/missions/{mission_id}/criteres")
def ecarter_criteres(mission_id: int, entree: EcartCriteres,
                     u: Utilisateur = Depends(acteur_mission), db: Session = Depends(session_db)):
    n = svc.ecarter_criteres(db, u, _mission(db, u, mission_id), entree.ids, entree.motif)
    return {"ecartes": n}


@routeur.put("/missions/{mission_id}/defauts-validation")
def valider_defauts(mission_id: int, entree: ValidationDefauts,
                    u: Utilisateur = Depends(acteur_mission), db: Session = Depends(session_db)):
    n = svc.valider_defauts(db, u, _mission(db, u, mission_id), entree.ids, entree.action,
                            entree.motif)
    return {"defauts": n}


@routeur.put("/missions/{mission_id}/defauts/{defaut_id}/criticite")
def requalifier_defaut(mission_id: int, defaut_id: int, entree: Requalification,
                       u: Utilisateur = Depends(acteur_mission), db: Session = Depends(session_db)):
    d = svc.requalifier_defaut(db, u, _mission(db, u, mission_id), defaut_id, entree.gravite,
                               entree.motif)
    return {"code": d.code, "gravite": d.gravite, "gravite_initiale": d.gravite_initiale}


@routeur.delete("/missions/{mission_id}/regles")
def ecarter_regles(mission_id: int, entree: EcartCriteres,
                   u: Utilisateur = Depends(acteur_mission), db: Session = Depends(session_db)):
    n = svc.ecarter_regles(db, u, _mission(db, u, mission_id), entree.ids, entree.motif)
    return {"ecartees": n}


@routeur.put("/missions/{mission_id}/phrases-justification")
def justifier_phrases(mission_id: int, entree: JustificationPhrases,
                      u: Utilisateur = Depends(acteur_mission), db: Session = Depends(session_db)):
    n = svc.justifier_phrases(db, u, _mission(db, u, mission_id), entree.ids, entree.motif)
    return {"phrases": n}


@routeur.delete("/missions/{mission_id}/criteres/{critere_id}")
def ecarter_critere(mission_id: int, critere_id: int, entree: EcartCritere,
                    u: Utilisateur = Depends(acteur_mission), db: Session = Depends(session_db)):
    svc.ecarter_critere(db, u, _mission(db, u, mission_id), critere_id, entree.motif)
    return {"ecarte": True}


@routeur.post("/missions/{mission_id}/relancer", status_code=202)
def relancer(mission_id: int, u: Utilisateur = Depends(acteur_mission),
             db: Session = Depends(session_db)):
    t = svc.relancer(db, u, _mission(db, u, mission_id))
    return {"tache_id": t.id}


def _cas(c: CasTest, refs: list[str]) -> dict:
    return {"id": c.id, "code": c.code, "titre": c.titre, "objectif": c.objectif,
            "exigence": c.exigence, "references": refs, "technique": c.technique,
            "justification_technique": c.justification_technique, "priorite": c.priorite,
            "type": c.type, "preconditions": c.preconditions, "donnees_test": c.donnees_test,
            "etapes": c.etapes, "resultat_attendu": c.resultat_attendu, "statut": c.statut,
            "motif_statut": c.motif_statut, "confirme_par_id": c.confirme_par_id}


def _refs(db: Session, ids: list[int]) -> dict[int, list[str]]:
    refs: dict[int, list[str]] = {i: [] for i in ids}
    for cas_id, ref in db.execute(select(Trace.cas_id, Trace.reference)
                                  .where(Trace.cas_id.in_(ids)).order_by(Trace.reference)):
        refs[cas_id].append(ref)
    return refs


@routeur.get("/missions/{mission_id}/cas")
def cas_mission(mission_id: int, u: Utilisateur = Depends(utilisateur_courant),
                db: Session = Depends(session_db)):
    v = svc.version_courante(_mission(db, u, mission_id))
    cas = db.scalars(select(CasTest).where(CasTest.version_id == v.id)
                     .order_by(CasTest.code)).all()
    refs = _refs(db, [c.id for c in cas])
    return [_cas(c, refs[c.id]) for c in cas]


@routeur.patch("/missions/{mission_id}/cas/{cas_id}")
def modifier_cas(mission_id: int, cas_id: int, entree: ModificationCas,
                 u: Utilisateur = Depends(acteur_mission), db: Session = Depends(session_db)):
    champs = entree.model_dump(exclude={"confirmer"}, exclude_none=True)
    c = svc.modifier_cas(db, u, _mission(db, u, mission_id), cas_id, champs, entree.confirmer)
    return _cas(c, _refs(db, [c.id])[c.id])


@routeur.get("/missions/{mission_id}/cahier-cas")
def cahier_cas(mission_id: int, u: Utilisateur = Depends(utilisateur_courant),
               db: Session = Depends(session_db)):
    """RA-46 : cahier des cas de test au gabarit Word DSI (version courante)."""
    contenu, nom = svc.exporter_cahier_cas(db, u, _mission(db, u, mission_id))
    return Response(contenu, media_type="application/vnd.openxmlformats-officedocument."
                                        "wordprocessingml.document",
                    headers={"Content-Disposition": "attachment; filename*=UTF-8''%s" % quote(nom)})


@routeur.get("/missions/{mission_id}/tracabilite")
def tracabilite(mission_id: int, u: Utilisateur = Depends(utilisateur_courant),
                db: Session = Depends(session_db)):
    """Matrice exigences/critères ↔ cas et couverture (AG-03), calculées en base."""
    v = svc.version_courante(_mission(db, u, mission_id))
    cas = db.scalars(select(CasTest).where(CasTest.version_id == v.id)
                     .order_by(CasTest.code)).all()
    refs = _refs(db, [c.id for c in cas])
    from ..scripts_qa import references
    lignes_ref = [(c.code, c.texte) for c in v.criteres] + \
                 [(r, "") for r in references(v.texte)]
    matrice = [{"reference": r, "libelle": lib,
                "cas": [c.code for c in cas if r in refs[c.id]]} for r, lib in lignes_ref]
    couvertes = sum(1 for ligne in matrice if ligne["cas"])
    techniques: dict[str, int] = {}
    for c in cas:
        techniques[c.technique] = techniques.get(c.technique, 0) + 1
    regles_ = [{"code": r.code, "texte": r.texte,
                "criteres": [c.code for c in v.criteres if r.code in c.regles],
                "cas": sorted({cas_.code for cas_ in cas
                               if r.code in refs[cas_.id]                 # cité directement
                               or any(r.code in c.regles and c.code in refs[cas_.id]
                                      for c in v.criteres)})}
               for r in v.regles]
    # la couverture compte aussi les règles métier : une règle sans cas n'est pas couverte
    total = len(matrice) + len(regles_)
    couvertes += sum(1 for r in regles_ if r["cas"])
    return {"matrice": matrice, "regles": regles_,
            "couverture": round(100 * couvertes / total) if total else None,
            "cas_sans_reference": [c.code for c in cas if not refs[c.id]],
            "par_technique": techniques}


@routeur.get("/cas")
def suivi_des_cas(q: str | None = None, mission_id: int | None = None,
                  statut: str | None = None, u: Utilisateur = Depends(utilisateur_courant),
                  db: Session = Depends(session_db)):
    """Suivi des cas : tous les cas des versions courantes des missions visibles.

    `statut` : PRET, INCOMPLET, A_CLARIFIER (conception) ou EXECUTE, NON_EXECUTE
    (recette). `q` cherche dans le cas, sa mission, son motif et les commentaires
    d'exécution. Les compteurs portent sur les cas affichés."""
    missions_visibles = db.scalars(svc.visible_par(u)).all()
    if mission_id:
        missions_visibles = [m for m in missions_visibles if m.id == mission_id]
    courantes = {svc.version_courante(m).id: m for m in missions_visibles if m.versions}
    requete = select(CasTest).where(CasTest.version_id.in_(list(courantes)))
    if statut in ("PRET", "INCOMPLET", "A_CLARIFIER"):
        requete = requete.where(CasTest.statut == statut)
    cas = db.scalars(requete.order_by(CasTest.version_id.desc(), CasTest.code)).all()
    executions: dict[int, list[Execution]] = {}
    for e in db.scalars(select(Execution).where(Execution.cas_id.in_([c.id for c in cas]))
                        .order_by(Execution.id)).all():
        executions.setdefault(e.cas_id, []).append(e)
    if statut == "EXECUTE":
        cas = [c for c in cas if c.id in executions]
    elif statut == "NON_EXECUTE":
        cas = [c for c in cas if c.id not in executions]
    if q and q.strip():
        cle = q.strip().lower()

        def correspond(c: CasTest) -> bool:
            m = courantes[c.version_id]
            champs = [c.code, c.titre, c.exigence, c.motif_statut, m.reference, m.titre] + \
                     [e.commentaire for e in executions.get(c.id, [])]
            return any(cle in (x or "").lower() for x in champs)
        cas = [c for c in cas if correspond(c)]
    refs = _refs(db, [c.id for c in cas])
    compte = {s: 0 for s in ("PRET", "INCOMPLET", "A_CLARIFIER")}
    for c in cas:
        compte[c.statut] += 1
    executes = sum(1 for c in cas if c.id in executions)
    return {"total": len(cas), "par_statut": compte,
            "executes": executes, "non_executes": len(cas) - executes,
            "cas": [{**_cas(c, refs[c.id]),
                     "execution": executions[c.id][-1].statut if c.id in executions else None,
                     "mission": {"id": courantes[c.version_id].id,
                                 "reference": courantes[c.version_id].reference,
                                 "titre": courantes[c.version_id].titre}} for c in cas]}
