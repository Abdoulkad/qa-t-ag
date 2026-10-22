"""Routes de la recette (lot 3) : exécutions, preuves, anomalies, clôture, cahier."""
import json
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session, undefer

from .. import recette as svc
from ..db import session_db
from ..deps import acteur_mission, utilisateur_courant
from ..missions import version_courante
from ..models import (Anomalie, CasTest, ClotureRecette, Execution, Preuve, Utilisateur)
from ..regles import LIBELLES_TEST, TAILLE_PREUVE_MAX
from .missions import _mission, _refs
from .schemas import ActionAnomalie, ClotureEntree, LeveeReserves, QualificationAnomalie

routeur = APIRouter(prefix="/api", tags=["Recette"])


def _personne(db: Session, uid: int | None) -> dict | None:
    if uid is None:
        return None
    p = db.get(Utilisateur, uid)
    return {"id": p.id, "nom": p.nom, "email": p.email} if p else None


def _anomalie(db: Session, a: Anomalie, codes_cas: dict[int, str], modifiable: bool) -> dict:
    return {
        "modifiable": modifiable and a.statut != "FERMEE",
        "id": a.id, "code": a.code, "cas_id": a.cas_id, "cas": codes_cas.get(a.cas_id),
        "execution_id": a.execution_id, "titre": a.titre, "description": a.description,
        "gravite": a.gravite, "reproductibilite": a.reproductibilite, "statut": a.statut,
        "motif_statut": a.motif_statut,
        "agent": {"etat": a.etat_agent, "gravite": a.gravite_proposee,
                  "reproductibilite": a.reproductibilite_proposee, "titre": a.titre_propose,
                  "justification": a.justification_agent, "erreur": a.erreur_agent},
        "qualifie_par": _personne(db, a.qualifie_par_id), "qualifie_le": a.qualifie_le,
        "motif_requalification": a.motif_requalification,
        "cree_le": a.cree_le, "corrigee_le": a.corrigee_le, "fermee_le": a.fermee_le,
    }


@routeur.get("/missions/{mission_id}/recette")
def etat_recette(mission_id: int, u: Utilisateur = Depends(utilisateur_courant),
                 db: Session = Depends(session_db)):
    """Tout ce qu'affiche l'étape Recette, calculé par le serveur."""
    m = _mission(db, u, mission_id)
    v = version_courante(m)
    cas = db.scalars(select(CasTest).where(CasTest.version_id == v.id)
                     .order_by(CasTest.code)).all()
    ids = [c.id for c in cas]
    refs = _refs(db, ids)
    execs: dict[int, list[Execution]] = {i: [] for i in ids}
    for e in db.scalars(select(Execution).where(Execution.cas_id.in_(ids))
                        .order_by(Execution.id)).all():
        execs[e.cas_id].append(e)
    preuves: dict[int, list[Preuve]] = {}
    tous_execs = [e.id for liste in execs.values() for e in liste]
    for p in db.scalars(select(Preuve).where(Preuve.execution_id.in_(tous_execs))
                        .order_by(Preuve.id)).all():
        preuves.setdefault(p.execution_id, []).append(p)
    codes = {c.id: c.code for c in cas}
    anomalies = db.scalars(select(Anomalie).where(Anomalie.mission_id == m.id)
                           .order_by(Anomalie.code)).all()
    ouvertes_par_cas: dict[int, list[str]] = {}
    for a in anomalies:
        if a.statut in ("OUVERTE", "CORRIGEE"):
            ouvertes_par_cas.setdefault(a.cas_id, []).append(a.code)

    suivi = svc.suivi_reserves(db, m)
    en_reserve = svc.cas_en_reserve(suivi)
    ouverte = m.statut in svc.STATUTS_RECETTE

    def autorise(cas_id: int) -> bool:          # même règle que le serveur (RA-27, RA-64)
        return ouverte or cas_id in en_reserve

    compte = {"PASS": 0, "FAIL": 0, "BLOCKED": 0, "NOT_RUN": 0, "A_EXECUTER": 0}
    lignes = []
    for c in cas:
        historique = execs[c.id]
        dernier = historique[-1] if historique else None
        compte[dernier.statut if dernier else "A_EXECUTER"] += 1
        lignes.append({
            "id": c.id, "code": c.code, "titre": c.titre, "objectif": c.objectif,
            "exigence": c.exigence, "references": refs[c.id], "priorite": c.priorite,
            "type": c.type, "preconditions": c.preconditions, "donnees_test": c.donnees_test,
            "etapes": c.etapes, "resultat_attendu": c.resultat_attendu, "statut_cas": c.statut,
            "statut": dernier.statut if dernier else None,
            "executable": autorise(c.id), "en_reserve": c.id in en_reserve,
            "anomalies_ouvertes": ouvertes_par_cas.get(c.id, []),
            "executions": [{
                "id": e.id, "passage": i, "statut": e.statut,
                "libelle": LIBELLES_TEST[e.statut], "resultat_obtenu": e.resultat_obtenu,
                "commentaire": e.commentaire, "testeur": _personne(db, e.testeur_id),
                "execute_le": e.execute_le,
                "preuves": [{"id": p.id, "nom": p.nom, "type": p.type_mime, "taille": p.taille,
                             "empreinte": p.empreinte} for p in preuves.get(e.id, [])],
            } for i, e in enumerate(historique, start=1)],
        })
    cloture = db.scalar(select(ClotureRecette).where(ClotureRecette.mission_id == m.id))
    return {
        "statut_mission": m.statut,
        "ouverte": ouverte,
        "suivi_reserves": suivi is not None,
        "reserves_restantes": svc.reserves_restantes(db, m) if suivi else [],
        "ia_configuree": svc.ia_configuree(db, m.organisation_id),
        "compteurs": {**compte, "total": len(cas),
                      "anomalies_ouvertes": sum(1 for a in anomalies
                                                if a.statut in ("OUVERTE", "CORRIGEE"))},
        "cas": lignes,
        "anomalies": [_anomalie(db, a, codes, autorise(a.cas_id)) for a in anomalies],
        "reserves": svc.reserves(db, m) if m.statut == "EN_RECETTE" else [],
        "cloture": ({"decision": cloture.decision, "commentaire": cloture.commentaire,
                     "reserves": json.loads(cloture.reserves),
                     "decideur": _personne(db, cloture.decideur_id),
                     "auto_validation": cloture.auto_validation,
                     "decide_le": cloture.decide_le,
                     "levee": ({"le": cloture.levee_le, "par": _personne(db, cloture.levee_par_id),
                                "auto_validation": cloture.levee_auto_validation,
                                "commentaire": cloture.levee_commentaire}
                               if cloture.levee_le else None)} if cloture else None),
    }


@routeur.post("/missions/{mission_id}/cas/{cas_id}/executions", status_code=201)
async def executer(mission_id: int, cas_id: int, statut: str = Form(...),
                   resultat_obtenu: str = Form(""), commentaire: str = Form(""),
                   captures: list[UploadFile] = File(default=[]),
                   u: Utilisateur = Depends(acteur_mission), db: Session = Depends(session_db)):
    """RA-27 à RA-31, RA-59 : un passage du cas, avec ses captures."""
    m = _mission(db, u, mission_id)
    fichiers = []
    for f in captures:
        contenu = await f.read(TAILLE_PREUVE_MAX + 1)
        if contenu:
            fichiers.append((f.filename or "capture", contenu))
    e = svc.enregistrer_execution(db, u, m, cas_id, statut, resultat_obtenu, commentaire,
                                  fichiers)
    return {"id": e.id, "statut": e.statut}


@routeur.get("/missions/{mission_id}/preuves/{preuve_id}")
def preuve(mission_id: int, preuve_id: int, u: Utilisateur = Depends(utilisateur_courant),
           db: Session = Depends(session_db)):
    """Une capture, servie seulement à qui voit la mission."""
    m = _mission(db, u, mission_id)
    p = db.scalar(select(Preuve).options(undefer(Preuve.contenu)).where(Preuve.id == preuve_id))
    cas = db.get(CasTest, db.get(Execution, p.execution_id).cas_id) if p else None
    if p is None or cas is None or cas.version_id not in {v.id for v in m.versions}:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Capture introuvable")
    return Response(p.contenu, media_type=p.type_mime,
                    headers={"Content-Disposition": "inline",
                             "X-Content-SHA256": p.empreinte})


@routeur.put("/missions/{mission_id}/anomalies/{anomalie_id}/qualification")
def qualifier(mission_id: int, anomalie_id: int, entree: QualificationAnomalie,
              u: Utilisateur = Depends(acteur_mission), db: Session = Depends(session_db)):
    m = _mission(db, u, mission_id)
    a = svc.qualifier(db, u, m, anomalie_id, entree.gravite, entree.reproductibilite,
                      entree.titre, entree.motif)
    return {"id": a.id, "gravite": a.gravite}


@routeur.post("/missions/{mission_id}/anomalies/{anomalie_id}/statut")
def changer_statut(mission_id: int, anomalie_id: int, entree: ActionAnomalie,
                   u: Utilisateur = Depends(acteur_mission), db: Session = Depends(session_db)):
    m = _mission(db, u, mission_id)
    a = svc.changer_statut(db, u, m, anomalie_id, entree.action, entree.motif)
    return {"id": a.id, "statut": a.statut}


@routeur.post("/missions/{mission_id}/anomalies/{anomalie_id}/agent", status_code=202)
def requalifier_par_agent(mission_id: int, anomalie_id: int,
                          u: Utilisateur = Depends(acteur_mission),
                          db: Session = Depends(session_db)):
    m = _mission(db, u, mission_id)
    tache = svc.relancer_qualification(db, u, m, anomalie_id)
    return {"tache_id": tache.id}


@routeur.post("/missions/{mission_id}/recette/cloture")
def cloturer(mission_id: int, entree: ClotureEntree, u: Utilisateur = Depends(acteur_mission),
             db: Session = Depends(session_db)):
    m = _mission(db, u, mission_id)
    d = svc.cloturer(db, u, m, entree.decision, entree.commentaire)
    return {"decision": d.decision, "reserves": json.loads(d.reserves)}


@routeur.post("/missions/{mission_id}/recette/levee-reserves")
def lever_reserves(mission_id: int, entree: LeveeReserves, u: Utilisateur = Depends(acteur_mission),
                   db: Session = Depends(session_db)):
    """RA-65 : levée des réserves d'une recette clôturée avec réserves."""
    m = _mission(db, u, mission_id)
    d = svc.lever_reserves(db, u, m, entree.commentaire)
    return {"levee_le": d.levee_le}


@routeur.get("/missions/{mission_id}/cahier-recette")
def cahier_recette(mission_id: int, u: Utilisateur = Depends(utilisateur_courant),
                   db: Session = Depends(session_db)):
    """RA-32, RA-33 : cahier de recette Word, généré depuis la base et relu."""
    from .. import cahier_recette as cr
    contenu, nom = cr.exporter(db, u, _mission(db, u, mission_id))
    return Response(contenu, media_type="application/vnd.openxmlformats-officedocument."
                                        "wordprocessingml.document",
                    headers={"Content-Disposition": "attachment; filename*=UTF-8''%s" % quote(nom)})
