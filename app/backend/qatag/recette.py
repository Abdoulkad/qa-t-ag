"""Recette (lot 3) : exécutions, preuves, anomalies, clôture.

Le testeur exécute ; AG-09 propose une qualification des anomalies ; l'humain
valide et clôture. Toutes les règles sont appliquées ici (RA-27 à RA-31,
RA-59 à RA-63) ; l'interface ne fait que les refléter.
"""
import hashlib
import json

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import journal, regles, taches
from .missions import version_courante
from .models import (GRAVITES_ANOMALIE, REPRODUCTIBILITES, Anomalie, CasTest, ClotureRecette,
                     ConfigIA, Execution, Mission, Preuve, Utilisateur, maintenant)
from .regles import RegleViolee

STATUTS_RECETTE = ("VALIDEE", "EN_RECETTE")          # RA-27 : après PV-2, avant clôture
RESOLUES = ("FERMEE", "REJETEE")


def _verifier_ouverte(m: Mission, action: str) -> None:
    if m.statut not in STATUTS_RECETTE:
        if m.statut == "CLOTUREE":
            raise RegleViolee("RA-63", "La recette est clôturée : %s impossible" % action)
        raise RegleViolee("RA-27", "La recette s'ouvre après l'approbation de PV-2 "
                                   "(statut actuel : %s)" % m.statut)


def _cas(db: Session, m: Mission, cas_id: int) -> CasTest:
    c = db.get(CasTest, cas_id)
    if c is None or c.version_id != version_courante(m).id:
        raise RegleViolee("RA-27", "Cas introuvable dans la version courante de la mission")
    return c


def _anomalie(db: Session, m: Mission, anomalie_id: int) -> Anomalie:
    a = db.get(Anomalie, anomalie_id)
    if a is None or a.mission_id != m.id:
        raise RegleViolee("RA-30", "Anomalie introuvable dans cette mission")
    return a


def _code_suivant(db: Session, m: Mission) -> str:
    n = db.scalar(select(func.count()).select_from(Anomalie).where(Anomalie.mission_id == m.id))
    return "ANO-%03d" % (n + 1)


def ia_configuree(db: Session, organisation_id: int) -> bool:
    return db.get(ConfigIA, organisation_id) is not None


# --- Exécution -----------------------------------------------------------------

def enregistrer_execution(db: Session, u: Utilisateur, m: Mission, cas_id: int, statut: str,
                          resultat_obtenu: str, commentaire: str,
                          fichiers: list[tuple[str, bytes]]) -> Execution:
    """Enregistre un passage du cas (l'historique est conservé). Un échec ouvre ou
    rouvre une anomalie (RA-30, RA-62) ; une réussite ferme celles du cas (RA-61)."""
    _verifier_ouverte(m, "l'exécution")
    c = _cas(db, m, cas_id)
    resultat_obtenu = (resultat_obtenu or "").strip()
    commentaire = (commentaire or "").strip()
    regles.verifier_execution(statut, resultat_obtenu, commentaire, len(fichiers),
                              c.resultat_attendu, c.statut)
    preuves = []
    for nom, contenu in fichiers:                                         # RA-31
        if len(contenu) > regles.TAILLE_PREUVE_MAX:
            raise RegleViolee("RA-31", "Capture « %s » trop volumineuse (10 Mo maximum)" % nom)
        mime = regles.type_image(contenu)
        if mime is None:
            raise RegleViolee("RA-31", "« %s » n'est pas une image PNG ou JPEG" % nom)
        preuves.append(Preuve(nom=(nom or "capture")[:255], contenu=contenu, type_mime=mime,
                              taille=len(contenu),
                              empreinte=hashlib.sha256(contenu).hexdigest()))

    if m.statut == "VALIDEE":                                             # RA-27
        regles.verifier_transition(m.statut, "EN_RECETTE")
        m.statut = "EN_RECETTE"
        journal.ajouter(db, m.organisation_id, "recette_ouverte", mission_id=m.id,
                        acteur_id=u.id, details={"version": version_courante(m).numero})
    e = Execution(cas_id=c.id, statut=statut, resultat_obtenu=resultat_obtenu,
                  commentaire=commentaire, testeur_id=u.id)
    db.add(e)
    db.flush()
    for p in preuves:
        p.execution_id = e.id
        db.add(p)
    passage = db.scalar(select(func.count()).select_from(Execution)
                        .where(Execution.cas_id == c.id))
    journal.ajouter(db, m.organisation_id, "cas_execute", mission_id=m.id, acteur_id=u.id,
                    details={"cas": c.code, "statut": statut, "passage": passage,
                             "preuves": [p.empreinte for p in preuves]})

    a_qualifier = None
    ouvertes = db.scalars(select(Anomalie).where(
        Anomalie.cas_id == c.id, Anomalie.statut.in_(("OUVERTE", "CORRIGEE")))).all()
    if statut == "FAIL":
        if ouvertes:                                                      # RA-62
            a = ouvertes[0]
            a.execution_id = e.id
            if a.statut == "CORRIGEE":
                a.statut, a.corrigee_le = "OUVERTE", None
                a.motif_statut = "Échec au nouveau passage (%d) après correction" % passage
                journal.ajouter(db, m.organisation_id, "anomalie_rouverte", mission_id=m.id,
                                acteur_id=u.id, details={"anomalie": a.code, "cas": c.code,
                                                         "passage": passage})
        else:                                                             # RA-30
            a = Anomalie(mission_id=m.id, code=_code_suivant(db, m), cas_id=c.id,
                         execution_id=e.id, cree_par_id=u.id,
                         titre="%s en échec : %s" % (c.code, c.titre)[:300],
                         description="Résultat attendu : %s\nRésultat obtenu : %s%s" % (
                             c.resultat_attendu, resultat_obtenu,
                             "\nCommentaire du testeur : %s" % commentaire if commentaire else ""))
            db.add(a)
            db.flush()
            journal.ajouter(db, m.organisation_id, "anomalie_ouverte", mission_id=m.id,
                            acteur_id=u.id, details={"anomalie": a.code, "cas": c.code})
            a_qualifier = a
    elif statut == "PASS":                                                # RA-61
        for a in ouvertes:
            a.statut, a.fermee_le, a.execution_fermeture_id = "FERMEE", maintenant(), e.id
            a.motif_statut = "Cas %s réussi au passage %d" % (c.code, passage)
            journal.ajouter(db, m.organisation_id, "anomalie_fermee", mission_id=m.id,
                            acteur_id=u.id, details={"anomalie": a.code, "cas": c.code,
                                                     "passage": passage})
    if a_qualifier is not None and ia_configuree(db, m.organisation_id):
        a_qualifier.etat_agent = "EN_COURS"
    db.commit()
    if a_qualifier is not None and a_qualifier.etat_agent == "EN_COURS":
        lancer_qualification(db, m, a_qualifier)
    return e


def lancer_qualification(db: Session, m: Mission, a: Anomalie):
    """RA-60 : AG-09 propose une qualification, en tâche de fond."""
    a.etat_agent, a.erreur_agent = "EN_COURS", None
    db.commit()
    return taches.lancer(db, m, version_courante(m), "ANOMALIE", cible_id=a.id)


def relancer_qualification(db: Session, u: Utilisateur, m: Mission, anomalie_id: int):
    _verifier_ouverte(m, "la qualification")
    a = _anomalie(db, m, anomalie_id)
    if a.statut in RESOLUES:
        raise RegleViolee("RA-60", "Anomalie %s déjà %s" % (a.code, a.statut.lower()))
    if a.etat_agent == "EN_COURS":
        raise RegleViolee("RA-60", "AG-09 qualifie déjà cette anomalie")
    if not ia_configuree(db, m.organisation_id):
        raise RegleViolee("RA-37", "Aucune IA configurée : qualifiez l'anomalie vous-même")
    return lancer_qualification(db, m, a)


# --- Anomalies : qualification et cycle de vie ---------------------------------------

def qualifier(db: Session, u: Utilisateur, m: Mission, anomalie_id: int, gravite: str,
              reproductibilite: str, titre: str, motif: str) -> Anomalie:
    """RA-60 : l'humain retient la gravité. Confirmer la proposition d'AG-09 ne
    demande pas de motif ; s'en écarter, si."""
    _verifier_ouverte(m, "la qualification")
    a = _anomalie(db, m, anomalie_id)
    if gravite not in GRAVITES_ANOMALIE:
        raise RegleViolee("RA-60", "Gravité inconnue : %s" % gravite)
    if reproductibilite not in REPRODUCTIBILITES:
        raise RegleViolee("RA-60", "Reproductibilité inconnue : %s" % reproductibilite)
    motif = (motif or "").strip()
    ecart = a.gravite_proposee is not None and gravite != a.gravite_proposee
    if ecart and not motif:
        raise RegleViolee("RA-60", "AG-09 proposait « %s » : retenir « %s » exige un motif"
                          % (a.gravite_proposee, gravite))
    avant = a.gravite
    a.gravite, a.reproductibilite = gravite, reproductibilite
    if (titre or "").strip():
        a.titre = titre.strip()[:300]
    a.motif_requalification = motif or None
    a.qualifie_par_id, a.qualifie_le = u.id, maintenant()
    journal.ajouter(db, m.organisation_id, "anomalie_qualifiee", mission_id=m.id,
                    acteur_id=u.id, details={
                        "anomalie": a.code, "gravite": gravite, "avant": avant,
                        "proposition_ag09": a.gravite_proposee,
                        "reproductibilite": reproductibilite, "motif": motif})
    db.commit()
    return a


def changer_statut(db: Session, u: Utilisateur, m: Mission, anomalie_id: int, action: str,
                   motif: str) -> Anomalie:
    """RA-61 : corrigée (livraison annoncée), rejetée (pas une anomalie) ou rouverte.
    La fermeture, elle, ne se décide pas : elle suit une réussite du cas."""
    _verifier_ouverte(m, "le changement de statut")
    a = _anomalie(db, m, anomalie_id)
    if action not in regles.ACTIONS_ANOMALIE:
        raise RegleViolee("RA-61", "Action inconnue : %s" % action)
    departs, arrivee, motif_exige = regles.ACTIONS_ANOMALIE[action]
    if a.statut not in departs:
        raise RegleViolee("RA-61", "Anomalie %s %s : action « %s » impossible"
                          % (a.code, a.statut.lower(), action.lower()))
    motif = (motif or "").strip()
    if motif_exige and not motif:
        raise RegleViolee("RA-61", "Cette action doit être motivée")
    a.statut, a.motif_statut = arrivee, motif or None
    if arrivee == "CORRIGEE":
        a.corrigee_le = maintenant()
    elif arrivee == "OUVERTE":
        a.corrigee_le = None
    journal.ajouter(db, m.organisation_id, "anomalie_%s" % arrivee.lower(), mission_id=m.id,
                    acteur_id=u.id, details={"anomalie": a.code, "motif": motif})
    db.commit()
    return a


# --- État de la recette, clôture ------------------------------------------------------

def dernieres_executions(db: Session, cas_ids: list[int]) -> dict[int, Execution]:
    dernieres: dict[int, Execution] = {}
    for e in db.scalars(select(Execution).where(Execution.cas_id.in_(cas_ids))
                        .order_by(Execution.id)).all():
        dernieres[e.cas_id] = e
    return dernieres


def reserves(db: Session, m: Mission) -> list[str]:
    """Ce qui empêche une clôture sans réserve (RA-63), calculé par le serveur."""
    v = version_courante(m)
    cas = db.scalars(select(CasTest).where(CasTest.version_id == v.id)
                     .order_by(CasTest.code)).all()
    dernieres = dernieres_executions(db, [c.id for c in cas])
    liste = []
    for c in cas:
        e = dernieres.get(c.id)
        if e is None:
            liste.append("%s non exécuté" % c.code)
        elif e.statut != "PASS":
            liste.append("%s : %s" % (c.code, regles.LIBELLES_TEST[e.statut].lower()))
    for a in db.scalars(select(Anomalie).where(Anomalie.mission_id == m.id,
                                               Anomalie.statut.in_(("OUVERTE", "CORRIGEE")))
                        .order_by(Anomalie.code)).all():
        liste.append("%s %s%s (%s)" % (a.code, a.statut.lower(),
                                       ", %s" % a.gravite.lower() if a.gravite else
                                       ", non qualifiée", a.titre))
    return liste


def cloturer(db: Session, u: Utilisateur, m: Mission, decision: str,
             commentaire: str) -> ClotureRecette:
    """RA-63 : clôture par un superviseur (ou auto-validation tracée si seul sur la
    mission). Sans réserve : tous les cas réussis, aucune anomalie ouverte ou
    corrigée non retestée. Avec réserves : motif obligatoire, réserves figées."""
    if m.statut != "EN_RECETTE":
        raise RegleViolee("RA-63", "Seule une recette en cours se clôture (statut : %s)"
                          % m.statut)
    if decision not in ("CLOTURE", "CLOTURE_AVEC_RESERVES"):
        raise RegleViolee("RA-63", "Décision inconnue : %s" % decision)
    v = version_courante(m)
    participants = [p.utilisateur_id for p in m.participants]
    hab = regles.habilitation_porte(u.id, u.roles, participants, v.auteur_id)
    if not hab.autorise:
        raise RegleViolee(hab.regle, hab.raison.replace("à un Human Gate",
                                                         "pour clôturer la recette"))
    commentaire = (commentaire or "").strip()
    liste = reserves(db, m)
    if decision == "CLOTURE" and liste:
        raise RegleViolee("RA-63", "Clôture sans réserve impossible : %d point(s) restent "
                                   "ouverts. Clôturez avec réserves, motif à l'appui."
                          % len(liste), liste)
    if decision == "CLOTURE_AVEC_RESERVES":
        if not liste:
            raise RegleViolee("RA-63", "Aucune réserve : clôturez sans réserve")
        if not commentaire:
            raise RegleViolee("RA-63", "Une clôture avec réserves doit être motivée")
    regles.verifier_transition(m.statut, "CLOTUREE")
    d = ClotureRecette(mission_id=m.id, version_id=v.id, decision=decision,
                       commentaire=commentaire, reserves=json.dumps(liste, ensure_ascii=False),
                       decideur_id=u.id, auto_validation=hab.auto_validation)
    db.add(d)
    m.statut = "CLOTUREE"
    journal.ajouter(db, m.organisation_id, "recette_cloturee", mission_id=m.id, acteur_id=u.id,
                    details={"decision": decision, "reserves": len(liste),
                             "auto_validation": hab.auto_validation,
                             "commentaire": commentaire})
    db.commit()
    return d
