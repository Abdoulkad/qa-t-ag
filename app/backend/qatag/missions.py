"""Services missions, versions et Human Gates (RA-08 à RA-16, RA-20, RA-26, RA-40)."""
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from . import journal, regles, scripts_qa, taches
from .models import (CasTest, ConfigIA, CritereAcceptation, DecisionPorte, Mission, Participant,
                     QuestionMetier, Trace, Utilisateur, VersionExigence, maintenant)
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
    if db.get(ConfigIA, auteur.organisation_id) is None:              # RA-37
        raise RegleViolee("RA-37", "Aucune IA n'est configurée : un administrateur doit "
                                   "en choisir une dans Configuration IA avant la première "
                                   "analyse.")
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
    libelles = {"A_CLARIFIER": "cas à clarifier", "INCOMPLET": "cas incomplet"}
    elements = ["%s : %s" % (c, libelles[s]) for c, s in cas if s in libelles]
    # RA-41 : chaque critère d'acceptation est couvert par au moins un cas
    couverts = set(db.scalars(select(Trace.reference).join(CasTest, CasTest.id == Trace.cas_id)
                              .where(CasTest.version_id == v.id)).all())
    elements += ["%s : critère non couvert par un cas" % c.code
                 for c in v.criteres if c.code not in couverts]
    return "RA-26", elements


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
    if decision == "APPROUVE" and porte == "PV-1":
        taches.lancer(db, m, v, "CONCEPTION")                # AG-02 dès PV-1 validé
    return d


# --- Lot 2 : clarification, réécriture, conception -------------------------

def _version_modifiable(m: Mission, statuts: tuple[str, ...], action: str,
                        exigence: bool = True) -> VersionExigence:
    """`exigence=True` : l'action touche l'exigence elle-même (texte, réponses,
    critères), interdite une fois la version figée par PV-1 (RA-10). Les cas de
    test, eux, se corrigent après PV-1 et jusqu'à PV-2 : le statut suffit."""
    if m.statut not in statuts:
        raise RegleViolee("RA-11", "%s impossible au statut %s" % (action, m.statut))
    v = version_courante(m)
    if exigence and v.figee:
        raise RegleViolee("RA-10", "Cette version est figée")
    return v


def repondre(db: Session, u: Utilisateur, m: Mission, question_id: int,
             reponse: str) -> QuestionMetier:
    """RA-18 : la réponse enregistre son auteur et sa date."""
    v = _version_modifiable(m, ("CLARIFICATION", "ATTENTE_PV1"), "Répondre")
    q = db.get(QuestionMetier, question_id)
    if q is None or q.version_id != v.id:
        raise RegleViolee("RA-05", "Question introuvable sur la version courante")
    reponse = (reponse or "").strip()
    q.reponse = reponse or None
    q.repondu_par_id = u.id if reponse else None
    q.repondu_le = maintenant() if reponse else None
    journal.ajouter(db, m.organisation_id, "question_repondue", mission_id=m.id, acteur_id=u.id,
                    details={"question": q.code, "reponse": reponse})
    db.commit()
    return q


def ajouter_precision(db: Session, u: Utilisateur, m: Mission, question: str,
                      reponse: str) -> QuestionMetier:
    """Précision apportée par un humain (question + réponse), utilisable comme source Q-n."""
    v = _version_modifiable(m, ("CLARIFICATION", "ATTENTE_PV1"), "Ajouter une précision")
    if not question.strip() or not reponse.strip():
        raise RegleViolee("RA-18", "Une précision exige une question et sa réponse")
    q = QuestionMetier(version_id=v.id, code="Q-%d" % (len(v.questions) + 1),
                       question=question.strip(), reponse=reponse.strip(), bloquante=False,
                       ajoutee_par_id=u.id, repondu_par_id=u.id, repondu_le=maintenant())
    db.add(q)
    db.flush()
    journal.ajouter(db, m.organisation_id, "precision_ajoutee", mission_id=m.id, acteur_id=u.id,
                    details={"question": q.code, "texte": q.question, "reponse": q.reponse})
    db.commit()
    return q


def lancer_reecriture(db: Session, u: Utilisateur, m: Mission):
    v = _version_modifiable(m, ("CLARIFICATION", "ATTENTE_PV1"), "La réécriture")
    if taches.en_cours(db, m.id):
        raise RegleViolee("RA-39", "Une tâche IA est déjà en cours sur cette mission")
    sans_reponse = [q.code for q in v.questions if q.bloquante and not (q.reponse or "").strip()]
    if sans_reponse:                                                            # RA-21
        raise RegleViolee("RA-21", "Répondez d'abord aux questions bloquantes",
                          ["%s : question bloquante sans réponse" % c for c in sans_reponse])
    regles.verifier_transition(m.statut, "REECRITURE")
    m.statut = "REECRITURE"
    journal.ajouter(db, m.organisation_id, "reecriture_lancee", mission_id=m.id, acteur_id=u.id,
                    details={"version": v.numero})
    db.commit()
    return taches.lancer(db, m, v, "REECRITURE")


def ecarter_critere(db: Session, u: Utilisateur, m: Mission, critere_id: int, motif: str) -> None:
    """L'humain écarte un critère (souvent une hypothèse) : décision motivée et journalisée."""
    v = _version_modifiable(m, ("ATTENTE_PV1",), "Écarter un critère")
    c = db.get(CritereAcceptation, critere_id)
    if c is None or c.version_id != v.id:
        raise RegleViolee("RA-05", "Critère introuvable sur la version courante")
    if not (motif or "").strip():
        raise RegleViolee("RA-20", "Écarter un critère doit être motivé")
    journal.ajouter(db, m.organisation_id, "critere_ecarte", mission_id=m.id, acteur_id=u.id,
                    details={"critere": c.code, "texte": c.texte, "statut": c.statut,
                             "motif": motif.strip()})
    db.delete(c)
    db.commit()


def relancer(db: Session, u: Utilisateur, m: Mission):
    """Relance l'agent après un échec : analyse (ECHEC_ANALYSE) ou conception (CONCEPTION)."""
    if taches.en_cours(db, m.id):
        raise RegleViolee("RA-39", "Une tâche IA est déjà en cours sur cette mission")
    v = version_courante(m)
    if m.statut == "ECHEC_ANALYSE":
        regles.verifier_transition(m.statut, "ANALYSE_EN_COURS")
        m.statut = "ANALYSE_EN_COURS"
        type_tache = "ANALYSE"
    elif m.statut == "CONCEPTION":
        type_tache = "CONCEPTION"
    else:
        raise RegleViolee("RA-11", "Rien à relancer au statut %s" % m.statut)
    journal.ajouter(db, m.organisation_id, "tache_relancee", mission_id=m.id, acteur_id=u.id,
                    details={"type": type_tache, "version": v.numero})
    db.commit()
    return taches.lancer(db, m, v, type_tache)


CHAMPS_CAS = ("titre", "objectif", "exigence", "technique", "justification_technique",
              "priorite", "type", "preconditions", "donnees_test", "etapes", "resultat_attendu")


def modifier_cas(db: Session, u: Utilisateur, m: Mission, cas_id: int, champs: dict,
                 confirmer: bool) -> CasTest:
    """Correction humaine d'un cas avant PV-2 ; le statut est recalculé (RA-23, RA-24)."""
    v = _version_modifiable(m, ("ATTENTE_PV2",), "Modifier un cas", exigence=False)
    c = db.get(CasTest, cas_id)
    if c is None or c.version_id != v.id:
        raise RegleViolee("RA-05", "Cas introuvable sur la version courante")
    modifies = {}
    for k, val in champs.items():
        if k in CHAMPS_CAS and val is not None and val != getattr(c, k):
            modifies[k] = {"avant": getattr(c, k), "apres": val}
            setattr(c, k, val.strip())
    refs = scripts_qa.references(c.exigence)
    connues = {x.code for x in v.criteres} | set(scripts_qa.references(v.texte))
    statut_ia = "A_CLARIFIER" if c.statut == "A_CLARIFIER" else "OK"
    statut, motif = regles.statut_cas(c.preconditions, c.donnees_test, c.resultat_attendu,
                                      statut_ia, confirme_par_humain=confirmer)
    problemes = []
    if not c.justification_technique.strip():
        problemes.append("technique non justifiée")
    if not refs:
        problemes.append("aucune exigence tracée")
    inconnues = [r for r in refs if r not in connues]
    if inconnues:
        problemes.append("référence inconnue : %s" % ", ".join(inconnues))
    if problemes and statut == "PRET":
        statut, motif = "INCOMPLET", "; ".join(problemes)
    if confirmer and statut == "PRET":
        c.confirme_par_id = u.id
    c.statut, c.motif_statut = statut, motif
    db.execute(Trace.__table__.delete().where(Trace.cas_id == c.id))
    for r in refs:
        if r in connues:
            db.add(Trace(cas_id=c.id, reference=r))
    journal.ajouter(db, m.organisation_id, "cas_modifie", mission_id=m.id, acteur_id=u.id,
                    details={"cas": c.code, "modifications": modifies, "confirme": confirmer,
                             "statut": statut})
    db.commit()
    return c
