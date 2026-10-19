"""Services missions, versions et Human Gates (RA-08 à RA-16, RA-20, RA-26, RA-40)."""
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from . import journal, regles, scripts_qa, taches
from .models import (CasTest, CritereAcceptation, DecisionPorte, Mission, Participant,
                     Utilisateur, VersionExigence)
from .regles import RegleViolee


def visible_par(u: Utilisateur):
    """RA-40 : un Superviseur voit toutes les missions de l'organisation,
    un Analyste seulement celles dont il est participant."""
    requete = select(Mission).where(Mission.organisation_id == u.organisation_id)
    if "SUPERVISEUR" not in u.roles:
        requete = requete.where(Mission.id.in_(
            select(Participant.mission_id).where(Participant.utilisateur_id == u.id)))
    return requete


def obtenir(db: Session, u: Utilisateur, mission_id: int) -> Mission | None:
    return db.scalar(visible_par(u).where(Mission.id == mission_id))


def version_courante(m: Mission) -> VersionExigence:
    return m.versions[-1]


def _reference_suivante(db: Session, organisation_id: int) -> str:
    db.execute(text("SELECT pg_advisory_xact_lock(:c)"), {"c": 8_000_000 + organisation_id})
    n = db.scalar(select(func.count()).select_from(Mission)
                  .where(Mission.organisation_id == organisation_id))
    return "M-%03d" % (n + 1)


def _ajouter_version(db: Session, m: Mission, auteur: Utilisateur, texte: str,
                     nom_source: str) -> VersionExigence:
    numero = len(m.versions) + 1
    v = VersionExigence(mission_id=m.id, numero=numero, texte=texte, nom_source=nom_source,
                        empreinte=scripts_qa.empreinte_texte(texte), auteur_id=auteur.id)
    db.add(v)
    db.flush()
    db.refresh(m)
    return v


def creer(db: Session, auteur: Utilisateur, titre: str, texte: str,
          nom_source: str = "texte saisi") -> tuple[Mission, "taches.TacheIA"]:
    m = Mission(organisation_id=auteur.organisation_id, titre=titre.strip(),
                reference=_reference_suivante(db, auteur.organisation_id),
                statut="ANALYSE_EN_COURS", createur_id=auteur.id)
    db.add(m)
    db.flush()
    db.add(Participant(mission_id=m.id, utilisateur_id=auteur.id))      # RA-09
    v = _ajouter_version(db, m, auteur, texte, nom_source)
    journal.ajouter(db, m.organisation_id, "mission_creee", mission_id=m.id, acteur_id=auteur.id,
                    details={"reference": m.reference, "version": 1, "empreinte": v.empreinte})
    db.commit()
    return m, taches.lancer(db, m, v, "ANALYSE")


def nouvelle_version(db: Session, auteur: Utilisateur, m: Mission, texte: str,
                     nom_source: str = "texte saisi"):
    """RA-10, RA-15, RA-16 : corriger = nouvelle version, après rejet ou échec d'analyse."""
    if m.statut not in ("A_CORRIGER", "ECHEC_ANALYSE"):
        raise RegleViolee("RA-10", "Une nouvelle version n'est possible qu'après un rejet "
                                   "ou un échec d'analyse (statut actuel : %s)" % m.statut)
    precedente = version_courante(m)
    precedente.figee = True
    regles.verifier_transition(m.statut, "ANALYSE_EN_COURS")
    m.statut = "ANALYSE_EN_COURS"
    v = _ajouter_version(db, m, auteur, texte, nom_source)
    journal.ajouter(db, m.organisation_id, "version_creee", mission_id=m.id, acteur_id=auteur.id,
                    details={"version": v.numero, "empreinte": v.empreinte,
                             "remplace": precedente.numero})
    db.commit()
    return v, taches.lancer(db, m, v, "ANALYSE")


def ajouter_participant(db: Session, acteur: Utilisateur, m: Mission, email: str) -> Utilisateur:
    cible = db.scalar(select(Utilisateur).where(
        func.lower(Utilisateur.email) == email.lower(),
        Utilisateur.organisation_id == m.organisation_id))
    if cible is None or not cible.actif:
        raise RegleViolee("RA-05", "Aucun compte actif avec cet e-mail dans l'organisation")
    if db.get(Participant, (m.id, cible.id)) is None:
        db.add(Participant(mission_id=m.id, utilisateur_id=cible.id))
        journal.ajouter(db, m.organisation_id, "participant_ajoute", mission_id=m.id,
                        acteur_id=acteur.id, details={"email": cible.email})
        db.commit()
    return cible


def bloquants_porte(db: Session, porte: str, v: VersionExigence) -> tuple[str, list[str]]:
    """Ce qui empêche d'approuver une porte : (règle, liste d'éléments)."""
    if porte == "PV-1":
        hypotheses = db.scalars(select(CritereAcceptation.code).where(
            CritereAcceptation.version_id == v.id,
            CritereAcceptation.statut == "HYPOTHESE")).all()
        return "RA-20", ["%s : critère sans source (hypothèse)" % c for c in hypotheses]
    cas = db.execute(select(CasTest.code, CasTest.statut).where(
        CasTest.version_id == v.id).order_by(CasTest.code)).all()
    if not cas:
        return "RA-26", ["Aucun cas de test conçu"]
    return "RA-26", ["%s : %s" % (c, s) for c, s in cas if s in ("A_CLARIFIER", "INCOMPLET")]


def decider(db: Session, decideur: Utilisateur, m: Mission, porte: str, decision: str,
            commentaire: str) -> DecisionPorte:
    if porte not in regles.PORTES:
        raise RegleViolee("RA-11", "Porte inconnue : %s" % porte)
    attente, si_approuve = regles.PORTES[porte]
    if m.statut != attente:
        raise RegleViolee("RA-11", "La mission n'attend pas de décision %s (statut : %s)"
                          % (porte, m.statut))
    # RA-16 : après un rejet la mission est A_CORRIGER, le contrôle de statut
    # ci-dessus suffit à bloquer toute décision sur la version rejetée.
    v = version_courante(m)

    participants = [p.utilisateur_id for p in m.participants]
    hab = regles.habilitation_porte(decideur.id, decideur.roles, participants, v.auteur_id)
    if not hab.autorise:
        raise RegleViolee(hab.regle, hab.raison)

    commentaire = (commentaire or "").strip()
    if decision == "REJETE":
        if not commentaire:
            raise RegleViolee("RA-15", "Un rejet doit être motivé par un commentaire")
        cible = "A_CORRIGER"
    else:
        regle, bloquants = bloquants_porte(db, porte, v)
        if bloquants:
            raise RegleViolee(regle, "%s ne peut pas être approuvé : %d élément(s) bloquant(s)"
                              % (porte, len(bloquants)), bloquants)
        cible = si_approuve

    regles.verifier_transition(m.statut, cible)
    d = DecisionPorte(version_id=v.id, porte=porte, decision=decision, commentaire=commentaire,
                      decideur_id=decideur.id, auto_validation=hab.auto_validation)
    db.add(d)
    if decision == "REJETE" or porte == "PV-1":
        v.figee = True                     # RA-10 : décidée = plus modifiable
    m.statut = cible
    journal.ajouter(db, m.organisation_id, "porte_decidee", mission_id=m.id,
                    acteur_id=decideur.id, agent=porte,
                    details={"version": v.numero, "decision": decision,
                             "auto_validation": hab.auto_validation,               # RA-14
                             "commentaire": commentaire})
    db.commit()
    return d
