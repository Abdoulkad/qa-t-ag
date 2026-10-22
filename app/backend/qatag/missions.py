"""Services missions, versions et Human Gates (RA-08 à RA-16, RA-20, RA-26, RA-40)."""
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from . import journal, regles, scripts_qa, taches
from .models import (CasTest, ConfigIA, CritereAcceptation, DecisionPorte, Defaut, Mission,
                     Participant,
                     PhraseSource, QuestionMetier, RegleMetier, Trace, Utilisateur,
                     VersionExigence, maintenant)
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


def _motif_hypothese(code: str, rejetees: list[str], nature: str) -> str:
    if rejetees:
        return "%s : source non valable (%s)" % (code, ", ".join(rejetees))
    return "%s : %s sans source (hypothèse)" % (code, nature)


def _court(texte: str, n: int = 90) -> str:
    return texte if len(texte) <= n else texte[:n].rstrip() + "…"


def couverture(v: VersionExigence) -> list[dict]:
    """RA-48 : chaque phrase du texte d'origine est reprise par une citation valide
    d'une règle ou d'un critère restant, ou justifiée par l'humain. Recalculé à
    chaque lecture : écarter une règle peut découvrir une phrase."""
    citations = [s for e in list(v.regles) + list(v.criteres) for s in e.sources
                 if s.startswith("«")]
    resultat = []
    for ph in v.phrases:
        if ph.titre:
            statut = "TITRE"
        elif scripts_qa.phrase_couverte(ph.texte, citations):
            statut = "COUVERTE"
        elif scripts_qa.est_cadrage(ph.texte):
            statut = "CADRE"           # rôle ou bénéfice, repris par la User Story réécrite
        elif ph.motif_non_reprise:
            statut = "JUSTIFIEE"
        else:
            statut = "NON_COUVERTE"
        resultat.append({"id": ph.id, "numero": ph.numero, "texte": ph.texte, "statut": statut,
                         "motif": ph.motif_non_reprise, "justifie_le": ph.justifie_le})
    return resultat


def assurer_phrases(db: Session, v: VersionExigence) -> None:
    """Découpe le texte d'origine une seule fois par version : les justifications
    humaines survivent aux réécritures successives."""
    if v.phrases:
        return
    for ph in scripts_qa.phrases_source(v.texte):
        db.add(PhraseSource(version_id=v.id, numero=ph["numero"], texte=ph["texte"],
                            titre=ph["titre"]))
    db.flush()
    db.refresh(v)


def bloquants_porte(db: Session, porte: str, v: VersionExigence) -> tuple[str, list[str]]:
    """Ce qui empêche d'approuver une porte : (règle, liste d'éléments)."""
    if porte == "PV-1":
        elements: list[str] = []
        regle = None
        for r in v.regles:                                       # RA-47 + RA-20
            if r.statut == "HYPOTHESE":
                regle = regle or "RA-20"
                elements.append(_motif_hypothese(r.code, r.sources_rejetees, "règle"))
        codes_regles = {r.code for r in v.regles}
        verifiees = {code for c in v.criteres for code in c.regles}
        for r in v.regles:                                       # RA-47 : RG → CA
            if r.code not in verifiees:
                regle = regle or "RA-47"
                elements.append("%s : règle vérifiée par aucun critère" % r.code)
        for c in v.criteres:
            if c.statut == "HYPOTHESE":
                regle = regle or "RA-20"
                elements.append(_motif_hypothese(c.code, c.sources_rejetees, "critère"))
            ecartees = [code for code in c.regles if code not in codes_regles]
            if ecartees:
                regle = regle or "RA-47"
                elements.append("%s : vérifie une règle écartée (%s)" % (c.code, ", ".join(ecartees)))
        for ph in couverture(v):                                 # RA-48
            if ph["statut"] == "NON_COUVERTE":
                regle = regle or "RA-48"
                elements.append("Phrase %d non reprise : « %s »" % (ph["numero"], _court(ph["texte"])))
        return regle or "RA-20", elements
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
    if reponse:                    # une réponse remplace une décision antérieure
        q.decision = q.motif_decision = q.decide_par_id = q.decide_le = None
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
                       ajoutee_par_id=u.id, repondu_par_id=u.id, repondu_le=maintenant(),
                       nature="PRECISION")
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
    sans_reponse = [q.code for q in v.questions if q.bloquante and not q.decision
                    and not (q.reponse or "").strip()]
    if sans_reponse:                                                            # RA-21
        raise RegleViolee("RA-21", "Traitez d'abord les questions bloquantes : répondez-y, "
                                   "ou déclarez-les hors périmètre ou reportées",
                          ["%s : question bloquante non traitée" % c for c in sans_reponse])
    regles.verifier_transition(m.statut, "REECRITURE")
    m.statut = "REECRITURE"
    journal.ajouter(db, m.organisation_id, "reecriture_lancee", mission_id=m.id, acteur_id=u.id,
                    details={"version": v.numero})
    db.commit()
    return taches.lancer(db, m, v, "REECRITURE")


def ecarter_criteres(db: Session, u: Utilisateur, m: Mission, ids: list[int],
                     motif: str) -> int:
    """L'humain écarte un ou plusieurs critères (souvent des hypothèses), avec un
    motif commun ; le journal garde une ligne par critère (RA-44)."""
    v = _version_modifiable(m, ("ATTENTE_PV1",), "Écarter un critère")
    if not (motif or "").strip():
        raise RegleViolee("RA-20", "Écarter un critère doit être motivé")
    criteres = [db.get(CritereAcceptation, i) for i in dict.fromkeys(ids)]
    if not criteres or any(c is None or c.version_id != v.id for c in criteres):
        raise RegleViolee("RA-05", "Critère introuvable sur la version courante")
    for c in criteres:
        journal.ajouter(db, m.organisation_id, "critere_ecarte", mission_id=m.id,
                        acteur_id=u.id, details={"critere": c.code, "texte": c.texte,
                                                 "statut": c.statut, "motif": motif.strip()})
        db.delete(c)
    db.commit()
    return len(criteres)


def ecarter_regles(db: Session, u: Utilisateur, m: Mission, ids: list[int], motif: str) -> int:
    """RA-47 : l'humain écarte une ou plusieurs règles métier, avec un motif commun.
    Les critères qui les vérifient sont alors signalés à PV-1."""
    v = _version_modifiable(m, ("ATTENTE_PV1",), "Écarter une règle")
    if not (motif or "").strip():
        raise RegleViolee("RA-47", "Écarter une règle doit être motivé")
    regles_ = [db.get(RegleMetier, i) for i in dict.fromkeys(ids)]
    if not regles_ or any(r is None or r.version_id != v.id for r in regles_):
        raise RegleViolee("RA-05", "Règle introuvable sur la version courante")
    for r in regles_:
        journal.ajouter(db, m.organisation_id, "regle_ecartee", mission_id=m.id,
                        acteur_id=u.id, details={"regle": r.code, "texte": r.texte,
                                                 "statut": r.statut, "motif": motif.strip()})
        db.delete(r)
    db.commit()
    return len(regles_)


def justifier_phrases(db: Session, u: Utilisateur, m: Mission, ids: list[int],
                      motif: str | None) -> int:
    """RA-48 : l'humain déclare qu'une phrase du texte d'origine n'est volontairement
    pas reprise, avec un motif ; motif None annule. Groupable (RA-44)."""
    v = _version_modifiable(m, ("ATTENTE_PV1",), "Justifier une phrase non reprise")
    if motif is not None and not motif.strip():
        raise RegleViolee("RA-48", "Une phrase non reprise doit être justifiée par un motif")
    phrases = [db.get(PhraseSource, i) for i in dict.fromkeys(ids)]
    if not phrases or any(p is None or p.version_id != v.id for p in phrases):
        raise RegleViolee("RA-05", "Phrase introuvable sur la version courante")
    for ph in phrases:
        ph.motif_non_reprise = motif.strip() if motif else None
        ph.justifie_par_id = u.id if motif else None
        ph.justifie_le = maintenant() if motif else None
        journal.ajouter(db, m.organisation_id,
                        "phrase_non_reprise_justifiee" if motif else "justification_phrase_annulee",
                        mission_id=m.id, acteur_id=u.id,
                        details={"phrase": ph.numero, "texte": ph.texte,
                                 "motif": ph.motif_non_reprise})
    db.commit()
    return len(phrases)


PREFIXE_ECART_DEFAUT = "Défaut écarté"


def recalculer_score(v: VersionExigence) -> None:
    """RA-17 / RA-50 : le score de clarté porte sur les défauts retenus (non écartés),
    avec leur criticité courante."""
    v.score_clarte = regles.score_clarte([d.gravite for d in v.defauts if d.validation != "ECARTE"])


def valider_defauts(db: Session, u: Utilisateur, m: Mission, ids: list[int], action: str,
                    motif: str = "") -> int:
    """RA-50 : l'humain confirme, écarte (faux positif, motif obligatoire) ou remet à
    examiner un ou plusieurs défauts. Écarter un défaut déclare sa question sans réponse
    hors périmètre avec le même motif ; l'annulation le défait. Groupable (RA-44)."""
    v = _version_modifiable(m, ("CLARIFICATION", "ATTENTE_PV1"), "Valider un défaut")
    if action not in ("CONFIRMER", "ECARTER", "ANNULER"):
        raise RegleViolee("RA-50", "Action inconnue : %s" % action)
    if action == "ECARTER" and not (motif or "").strip():
        raise RegleViolee("RA-50", "Écarter un défaut doit être motivé")
    defauts = [db.get(Defaut, i) for i in dict.fromkeys(ids)]
    if not defauts or any(d is None or d.version_id != v.id for d in defauts):
        raise RegleViolee("RA-05", "Défaut introuvable sur la version courante")
    valeur = {"CONFIRMER": "CONFIRME", "ECARTER": "ECARTE", "ANNULER": None}[action]
    for d in defauts:
        d.validation = valeur
        d.motif_validation = motif.strip() if action == "ECARTER" else None
        d.valide_par_id = u.id if valeur else None
        d.valide_le = maintenant() if valeur else None
        for q in v.questions:
            if q.defaut_id != d.id or (q.reponse or "").strip():
                continue
            if action == "ECARTER":
                q.decision, q.decide_par_id, q.decide_le = "HORS_PERIMETRE", u.id, maintenant()
                q.motif_decision = "%s (%s) : %s" % (PREFIXE_ECART_DEFAUT, d.code, motif.strip())
            elif (q.motif_decision or "").startswith(PREFIXE_ECART_DEFAUT):
                q.decision = q.motif_decision = q.decide_par_id = q.decide_le = None
        journal.ajouter(db, m.organisation_id,
                        {"CONFIRMER": "defaut_confirme", "ECARTER": "defaut_ecarte",
                         "ANNULER": "validation_defaut_annulee"}[action],
                        mission_id=m.id, acteur_id=u.id,
                        details={"defaut": d.code, "categorie": d.categorie,
                                 "gravite": d.gravite, "motif": d.motif_validation})
    recalculer_score(v)
    db.commit()
    return len(defauts)


def requalifier_defaut(db: Session, u: Utilisateur, m: Mission, defaut_id: int, gravite: str,
                       motif: str) -> Defaut:
    """RA-50 : l'humain change la criticité d'un défaut, avec un motif. La criticité
    proposée par l'agent est conservée ; la question suit (bloquante ou non)."""
    v = _version_modifiable(m, ("CLARIFICATION", "ATTENTE_PV1"), "Requalifier un défaut")
    if gravite not in regles.GRAVITE_POIDS:
        raise RegleViolee("RA-50", "Criticité inconnue : %s" % gravite)
    if not (motif or "").strip():
        raise RegleViolee("RA-50", "Changer la criticité d'un défaut doit être motivé")
    d = db.get(Defaut, defaut_id)
    if d is None or d.version_id != v.id:
        raise RegleViolee("RA-05", "Défaut introuvable sur la version courante")
    if gravite == d.gravite:
        raise RegleViolee("RA-50", "%s est déjà %s" % (d.code, gravite))
    ancienne = d.gravite
    d.gravite_initiale = d.gravite_initiale or d.gravite
    d.gravite = gravite
    d.motif_requalification = motif.strip()
    d.valide_par_id, d.valide_le = u.id, maintenant()
    d.validation = d.validation or "CONFIRME"
    for q in v.questions:
        if q.defaut_id == d.id:
            q.bloquante = gravite == "Bloquante"
    journal.ajouter(db, m.organisation_id, "defaut_requalifie", mission_id=m.id, acteur_id=u.id,
                    details={"defaut": d.code, "de": ancienne, "vers": gravite,
                             "motif": motif.strip()})
    recalculer_score(v)
    db.commit()
    return d


def ecarter_critere(db: Session, u: Utilisateur, m: Mission, critere_id: int, motif: str) -> None:
    ecarter_criteres(db, u, m, [critere_id], motif)


DECISIONS_QUESTION = {"HORS_PERIMETRE": "hors périmètre", "REPORTEE": "reportée"}


def decider_questions(db: Session, u: Utilisateur, m: Mission, ids: list[int],
                      decision: str | None, motif: str) -> int:
    """RA-42 : à défaut de réponse, l'humain déclare une question hors périmètre ou
    reportée, avec un motif. `decision=None` annule la décision. Groupable (RA-44)."""
    v = _version_modifiable(m, ("CLARIFICATION", "ATTENTE_PV1"), "Décider d'une question")
    if decision is not None and decision not in DECISIONS_QUESTION:
        raise RegleViolee("RA-42", "Décision inconnue : %s" % decision)
    if decision and not (motif or "").strip():
        raise RegleViolee("RA-42", "Une décision sur une question doit être motivée")
    questions = [db.get(QuestionMetier, i) for i in dict.fromkeys(ids)]
    if not questions or any(q is None or q.version_id != v.id for q in questions):
        raise RegleViolee("RA-05", "Question introuvable sur la version courante")
    repondues = [q.code for q in questions if decision and (q.reponse or "").strip()]
    if repondues:
        raise RegleViolee("RA-42", "Ces questions ont déjà une réponse : effacez-la d'abord",
                          ["%s : déjà répondue" % c for c in repondues])
    for q in questions:
        q.decision = decision
        q.motif_decision = motif.strip() if decision else None
        q.decide_par_id = u.id if decision else None
        q.decide_le = maintenant() if decision else None
        journal.ajouter(db, m.organisation_id,
                        "question_decidee" if decision else "decision_question_annulee",
                        mission_id=m.id, acteur_id=u.id,
                        details={"question": q.code, "decision": decision,
                                 "motif": q.motif_decision})
    db.commit()
    return len(questions)


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
    connues = ({x.code for x in v.criteres} | {x.code for x in v.regles} |
               set(scripts_qa.references(v.texte)))
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


STATUTS_CAHIER = ("ATTENTE_PV2", "VALIDEE", "EN_RECETTE", "CLOTUREE")


def lignes_cahier(db: Session, v: VersionExigence, regle: str) -> tuple[list, list[list[str]]]:
    """Cas de la version au format du gabarit (cahier_word.py), dans l'ordre des codes.
    Un cas dont la priorité ou le type n'a pas de case dans le gabarit bloque l'export."""
    cas = db.scalars(select(CasTest).where(CasTest.version_id == v.id)
                     .order_by(CasTest.code)).all()
    if not cas:
        raise RegleViolee(regle, "Aucun cas de test à exporter")
    cw = scripts_qa._module("cahier_word")
    lignes, invalides = [], []
    for c in cas:
        prio = scripts_qa.valeur_gabarit(c.priorite, tuple(cw.PRIO_TOK))
        typ = scripts_qa.valeur_gabarit(c.type, tuple(cw.TYPE_TOK))
        if prio is None:
            invalides.append("%s : priorité « %s » absente du gabarit" % (c.code, c.priorite))
        if typ is None:
            invalides.append("%s : type « %s » absent du gabarit" % (c.code, c.type))
        statut = "À_CLARIFIER" if c.statut == "A_CLARIFIER" else c.statut
        lignes.append([c.code, c.titre, c.objectif, c.exigence, c.technique, prio or "",
                       typ or "", c.preconditions, c.donnees_test, c.etapes,
                       c.resultat_attendu, statut])
    if invalides:
        raise RegleViolee(regle, "Corrigez ces cas avant l'export : chaque cas doit "
                                 "cocher une priorité et un type du gabarit", invalides)
    return cas, lignes


def exporter_cahier_cas(db: Session, u: Utilisateur, m: Mission) -> tuple[bytes, str]:
    """RA-46 : cahier des cas au gabarit Word DSI, sur la version courante.

    Recopie fidèle des cas enregistrés ; zones d'exécution laissées vides. Avant
    PV-2, le document est marqué « document de travail ». Chaque export est tracé
    au journal avec l'empreinte SHA-256 du fichier remis."""
    import hashlib
    import os
    import tempfile

    if m.statut not in STATUTS_CAHIER:
        raise RegleViolee("RA-46", "Le cahier des cas s'exporte une fois les cas conçus "
                                   "(statut actuel : %s)" % m.statut)
    v = version_courante(m)
    cas, lignes = lignes_cahier(db, v, "RA-46")
    pv2 = db.scalar(select(DecisionPorte).where(DecisionPorte.version_id == v.id,
                                                DecisionPorte.porte == "PV-2",
                                                DecisionPorte.decision == "APPROUVE"))
    entete = "Mission %s — %s · version %d · empreinte %s" % (
        m.reference, m.titre, v.numero, v.empreinte[:12])
    if pv2:
        decideur = db.get(Utilisateur, pv2.decideur_id)
        etat = "Cas validés à PV-2 le %s par %s%s" % (
            pv2.decide_le.strftime("%d/%m/%Y"), decideur.nom or decideur.email,
            " (auto-validation)" if pv2.auto_validation else "")
    else:
        etat = "DOCUMENT DE TRAVAIL — cas non validés (PV-2 en attente)"
    fd, chemin = tempfile.mkstemp(suffix=".docx")
    os.close(fd)
    try:
        scripts_qa.cahier_cas(lignes, "%s\n%s · %d cas" % (etat, entete, len(cas)), chemin)
        with open(chemin, "rb") as f:
            contenu = f.read()
    finally:
        os.remove(chemin)
    nom = "Cahier_cas_%s_v%d%s.docx" % (m.reference, v.numero, "" if pv2 else "_brouillon")
    journal.ajouter(db, m.organisation_id, "cahier_cas_exporte", mission_id=m.id,
                    acteur_id=u.id, details={"version": v.numero, "cas": len(cas),
                                             "valide_pv2": bool(pv2), "fichier": nom,
                                             "empreinte": hashlib.sha256(contenu).hexdigest()})
    db.commit()
    return contenu, nom
