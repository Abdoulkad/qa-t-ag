"""Modèle de données (docs/specifications.md §11)."""
from datetime import datetime, timezone

from sqlalchemy import (Boolean, CheckConstraint, DateTime, ForeignKey,
                        Integer, String, Text, UniqueConstraint)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base

ROLES = ("ANALYSTE", "SUPERVISEUR", "ADMIN")

STATUTS_MISSION = (
    "ANALYSE_EN_COURS", "CLARIFICATION", "REECRITURE", "ATTENTE_PV1",
    "CONCEPTION", "ATTENTE_PV2", "VALIDEE", "EN_RECETTE", "CLOTUREE",
    "A_CORRIGER", "ECHEC_ANALYSE",
)
STATUTS_CAS = ("PRET", "INCOMPLET", "A_CLARIFIER")
STATUTS_TEST = ("PASS", "FAIL", "BLOCKED", "NOT_RUN")
ETATS_TACHE = ("EN_ATTENTE", "EN_COURS", "TERMINEE", "ECHEC")


def maintenant():
    return datetime.now(timezone.utc)


def _dans(colonne, valeurs):
    return "%s IN (%s)" % (colonne, ", ".join("'%s'" % v for v in valeurs))


class Organisation(Base):
    __tablename__ = "organisation"
    id: Mapped[int] = mapped_column(primary_key=True)
    nom: Mapped[str] = mapped_column(String(200))
    cree_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=maintenant)


class Utilisateur(Base):
    __tablename__ = "utilisateur"
    id: Mapped[int] = mapped_column(primary_key=True)
    organisation_id: Mapped[int] = mapped_column(ForeignKey("organisation.id"), index=True)
    email: Mapped[str] = mapped_column(String(320), unique=True)
    nom: Mapped[str] = mapped_column(String(200), default="")
    hash_mot_de_passe: Mapped[str] = mapped_column(String(200))
    roles: Mapped[list[str]] = mapped_column(ARRAY(String(20)), default=list)
    actif: Mapped[bool] = mapped_column(Boolean, default=True)
    cree_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=maintenant)

    __table_args__ = (
        CheckConstraint("cardinality(roles) >= 1", name="ck_utilisateur_au_moins_un_role"),
        CheckConstraint("roles <@ ARRAY['ANALYSTE','SUPERVISEUR','ADMIN']::varchar[]",
                        name="ck_utilisateur_roles_connus"),
    )


class ConfigIA(Base):
    __tablename__ = "config_ia"
    organisation_id: Mapped[int] = mapped_column(ForeignKey("organisation.id"), primary_key=True)
    fournisseur: Mapped[str] = mapped_column(String(30))
    modele: Mapped[str] = mapped_column(String(100))
    modifie_par_id: Mapped[int | None] = mapped_column(ForeignKey("utilisateur.id"))
    modifie_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=maintenant)


class Mission(Base):
    __tablename__ = "mission"
    id: Mapped[int] = mapped_column(primary_key=True)
    organisation_id: Mapped[int] = mapped_column(ForeignKey("organisation.id"), index=True)
    reference: Mapped[str] = mapped_column(String(20))
    titre: Mapped[str] = mapped_column(String(300))
    statut: Mapped[str] = mapped_column(String(30))
    createur_id: Mapped[int] = mapped_column(ForeignKey("utilisateur.id"))
    cree_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=maintenant)
    modifie_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=maintenant,
                                                 onupdate=maintenant)

    versions: Mapped[list["VersionExigence"]] = relationship(
        back_populates="mission", order_by="VersionExigence.numero")
    participants: Mapped[list["Participant"]] = relationship(back_populates="mission")

    __table_args__ = (
        UniqueConstraint("organisation_id", "reference", name="uq_mission_reference"),
        CheckConstraint(_dans("statut", STATUTS_MISSION), name="ck_mission_statut"),
    )


class Participant(Base):
    __tablename__ = "participant"
    mission_id: Mapped[int] = mapped_column(ForeignKey("mission.id"), primary_key=True)
    utilisateur_id: Mapped[int] = mapped_column(ForeignKey("utilisateur.id"), primary_key=True)
    ajoute_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=maintenant)
    mission: Mapped[Mission] = relationship(back_populates="participants")
    utilisateur: Mapped[Utilisateur] = relationship()


class VersionExigence(Base):
    __tablename__ = "version_exigence"
    id: Mapped[int] = mapped_column(primary_key=True)
    mission_id: Mapped[int] = mapped_column(ForeignKey("mission.id"), index=True)
    numero: Mapped[int] = mapped_column(Integer)
    texte: Mapped[str] = mapped_column(Text)
    nom_source: Mapped[str] = mapped_column(String(300), default="texte saisi")
    empreinte: Mapped[str] = mapped_column(String(64))
    auteur_id: Mapped[int] = mapped_column(ForeignKey("utilisateur.id"))
    fournisseur_ia: Mapped[str | None] = mapped_column(String(30))
    modele_ia: Mapped[str | None] = mapped_column(String(100))
    rapport_revue: Mapped[str | None] = mapped_column(Text)
    controle_revue: Mapped[str | None] = mapped_column(Text)
    code_controle_revue: Mapped[int | None] = mapped_column(Integer)
    score_clarte: Mapped[int | None] = mapped_column(Integer)
    texte_reecrit: Mapped[str | None] = mapped_column(Text)
    points_ouverts: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    controle_reecriture: Mapped[str | None] = mapped_column(Text)
    controle_conception: Mapped[str | None] = mapped_column(Text)
    figee: Mapped[bool] = mapped_column(Boolean, default=False)
    cree_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=maintenant)

    mission: Mapped[Mission] = relationship(back_populates="versions")
    defauts: Mapped[list["Defaut"]] = relationship(order_by="Defaut.code")
    questions: Mapped[list["QuestionMetier"]] = relationship(order_by="QuestionMetier.id")
    criteres: Mapped[list["CritereAcceptation"]] = relationship(order_by="CritereAcceptation.code")
    regles: Mapped[list["RegleMetier"]] = relationship(order_by="RegleMetier.code")
    phrases: Mapped[list["PhraseSource"]] = relationship(order_by="PhraseSource.numero")

    __table_args__ = (UniqueConstraint("mission_id", "numero", name="uq_version_numero"),)


class Defaut(Base):
    __tablename__ = "defaut"
    id: Mapped[int] = mapped_column(primary_key=True)
    version_id: Mapped[int] = mapped_column(ForeignKey("version_exigence.id"), index=True)
    code: Mapped[str] = mapped_column(String(20))
    categorie: Mapped[str] = mapped_column(String(60))
    gravite: Mapped[str] = mapped_column(String(20))
    section: Mapped[str | None] = mapped_column(Text)
    citation: Mapped[str | None] = mapped_column(Text)
    citation_verifiee: Mapped[bool] = mapped_column(Boolean, default=False)
    # QA-REV-02 : constat et criticité motivée, puis validation humaine (RA-49, RA-50)
    constat: Mapped[str | None] = mapped_column(Text)
    justification: Mapped[str | None] = mapped_column(Text)
    validation: Mapped[str | None] = mapped_column(String(20))          # CONFIRME | ECARTE
    motif_validation: Mapped[str | None] = mapped_column(Text)
    gravite_initiale: Mapped[str | None] = mapped_column(String(20))    # avant requalification
    motif_requalification: Mapped[str | None] = mapped_column(Text)
    valide_par_id: Mapped[int | None] = mapped_column(ForeignKey("utilisateur.id"))
    valide_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (CheckConstraint(
        "validation IS NULL OR validation IN ('CONFIRME', 'ECARTE')",
        name="ck_defaut_validation"),)


class QuestionMetier(Base):
    __tablename__ = "question_metier"
    id: Mapped[int] = mapped_column(primary_key=True)
    version_id: Mapped[int] = mapped_column(ForeignKey("version_exigence.id"), index=True)
    defaut_id: Mapped[int | None] = mapped_column(ForeignKey("defaut.id"))
    code: Mapped[str] = mapped_column(String(10))
    question: Mapped[str] = mapped_column(Text)
    # DEFAUT (liée à un défaut), COMPLEMENTAIRE (règle absente du texte), PRECISION (humaine)
    nature: Mapped[str] = mapped_column(String(20), default="DEFAUT", server_default="DEFAUT")
    sujet: Mapped[str | None] = mapped_column(Text)
    pourquoi: Mapped[str | None] = mapped_column(Text)
    ajoutee_par_id: Mapped[int | None] = mapped_column(ForeignKey("utilisateur.id"))
    bloquante: Mapped[bool] = mapped_column(Boolean, default=False)
    reponse: Mapped[str | None] = mapped_column(Text)
    repondu_par_id: Mapped[int | None] = mapped_column(ForeignKey("utilisateur.id"))
    repondu_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # RA-42 : à défaut de réponse, une décision humaine motivée
    decision: Mapped[str | None] = mapped_column(String(20))
    motif_decision: Mapped[str | None] = mapped_column(Text)
    decide_par_id: Mapped[int | None] = mapped_column(ForeignKey("utilisateur.id"))
    decide_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        CheckConstraint("decision IS NULL OR decision IN ('HORS_PERIMETRE', 'REPORTEE')",
                        name="ck_question_decision"),
        CheckConstraint("nature IN ('DEFAUT', 'COMPLEMENTAIRE', 'PRECISION')",
                        name="ck_question_nature"))


class RegleMetier(Base):
    """RA-47 : règle de gestion de la User Story réécrite, sourcée comme un critère."""
    __tablename__ = "regle_metier"
    id: Mapped[int] = mapped_column(primary_key=True)
    version_id: Mapped[int] = mapped_column(ForeignKey("version_exigence.id"), index=True)
    code: Mapped[str] = mapped_column(String(20))
    texte: Mapped[str] = mapped_column(Text)
    sources: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    sources_rejetees: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    statut: Mapped[str] = mapped_column(String(20))
    __table_args__ = (CheckConstraint(_dans("statut", ("SOURCE", "HYPOTHESE")),
                                      name="ck_regle_statut"),
                      UniqueConstraint("version_id", "code", name="uq_regle_code"))


class PhraseSource(Base):
    """RA-48 : phrase du texte d'origine ; une phrase non reprise est justifiée par
    l'humain. La couverture elle-même est recalculée, jamais stockée."""
    __tablename__ = "phrase_source"
    id: Mapped[int] = mapped_column(primary_key=True)
    version_id: Mapped[int] = mapped_column(ForeignKey("version_exigence.id"), index=True)
    numero: Mapped[int] = mapped_column(Integer)
    texte: Mapped[str] = mapped_column(Text)
    titre: Mapped[bool] = mapped_column(Boolean, default=False)
    motif_non_reprise: Mapped[str | None] = mapped_column(Text)
    justifie_par_id: Mapped[int | None] = mapped_column(ForeignKey("utilisateur.id"))
    justifie_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (UniqueConstraint("version_id", "numero", name="uq_phrase_numero"),)


class CritereAcceptation(Base):
    __tablename__ = "critere_acceptation"
    id: Mapped[int] = mapped_column(primary_key=True)
    version_id: Mapped[int] = mapped_column(ForeignKey("version_exigence.id"), index=True)
    code: Mapped[str] = mapped_column(String(20))
    texte: Mapped[str] = mapped_column(Text)
    sources: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    sources_rejetees: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    regles: Mapped[list[str]] = mapped_column(ARRAY(String(20)), default=list)  # RG vérifiées
    statut: Mapped[str] = mapped_column(String(20))
    __table_args__ = (CheckConstraint(_dans("statut", ("SOURCE", "HYPOTHESE")),
                                      name="ck_critere_statut"),)


class CasTest(Base):
    __tablename__ = "cas_test"
    id: Mapped[int] = mapped_column(primary_key=True)
    version_id: Mapped[int] = mapped_column(ForeignKey("version_exigence.id"), index=True)
    code: Mapped[str] = mapped_column(String(20))
    titre: Mapped[str] = mapped_column(Text)
    objectif: Mapped[str] = mapped_column(Text, default="")
    exigence: Mapped[str] = mapped_column(Text, default="")
    technique: Mapped[str] = mapped_column(String(60), default="")
    justification_technique: Mapped[str] = mapped_column(Text, default="")
    priorite: Mapped[str] = mapped_column(String(20), default="")
    type: Mapped[str] = mapped_column(String(40), default="")
    preconditions: Mapped[str] = mapped_column(Text, default="")
    donnees_test: Mapped[str] = mapped_column(Text, default="")
    etapes: Mapped[str] = mapped_column(Text, default="")
    resultat_attendu: Mapped[str] = mapped_column(Text, default="")
    statut: Mapped[str] = mapped_column(String(20))
    motif_statut: Mapped[str] = mapped_column(Text, default="")
    confirme_par_id: Mapped[int | None] = mapped_column(ForeignKey("utilisateur.id"))
    __table_args__ = (
        CheckConstraint(_dans("statut", STATUTS_CAS), name="ck_cas_statut"),
        UniqueConstraint("version_id", "code", name="uq_cas_code"),
    )


class Trace(Base):
    __tablename__ = "trace"
    cas_id: Mapped[int] = mapped_column(ForeignKey("cas_test.id"), primary_key=True)
    reference: Mapped[str] = mapped_column(String(40), primary_key=True)


class DecisionPorte(Base):
    __tablename__ = "decision_porte"
    id: Mapped[int] = mapped_column(primary_key=True)
    version_id: Mapped[int] = mapped_column(ForeignKey("version_exigence.id"), index=True)
    porte: Mapped[str] = mapped_column(String(10))
    decision: Mapped[str] = mapped_column(String(10))
    commentaire: Mapped[str] = mapped_column(Text, default="")
    decideur_id: Mapped[int] = mapped_column(ForeignKey("utilisateur.id"))
    auto_validation: Mapped[bool] = mapped_column(Boolean, default=False)
    decide_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=maintenant)
    __table_args__ = (
        CheckConstraint(_dans("porte", ("PV-1", "PV-2")), name="ck_decision_porte"),
        CheckConstraint(_dans("decision", ("APPROUVE", "REJETE")), name="ck_decision_valeur"),
        UniqueConstraint("version_id", "porte", name="uq_decision_unique_par_porte"),
    )


class Execution(Base):
    __tablename__ = "execution"
    id: Mapped[int] = mapped_column(primary_key=True)
    cas_id: Mapped[int] = mapped_column(ForeignKey("cas_test.id"), index=True)
    statut: Mapped[str] = mapped_column(String(20))
    resultat_obtenu: Mapped[str] = mapped_column(Text, default="")
    commentaire: Mapped[str] = mapped_column(Text, default="")
    testeur_id: Mapped[int] = mapped_column(ForeignKey("utilisateur.id"))
    execute_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=maintenant)
    __table_args__ = (CheckConstraint(_dans("statut", STATUTS_TEST), name="ck_execution_statut"),)


class Preuve(Base):
    __tablename__ = "preuve"
    id: Mapped[int] = mapped_column(primary_key=True)
    execution_id: Mapped[int] = mapped_column(ForeignKey("execution.id"), index=True)
    chemin: Mapped[str] = mapped_column(Text)
    type_mime: Mapped[str] = mapped_column(String(50))
    taille: Mapped[int] = mapped_column(Integer)
    empreinte: Mapped[str] = mapped_column(String(64))
    ajoute_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=maintenant)


class Anomalie(Base):
    __tablename__ = "anomalie"
    id: Mapped[int] = mapped_column(primary_key=True)
    cas_id: Mapped[int] = mapped_column(ForeignKey("cas_test.id"), index=True)
    execution_id: Mapped[int | None] = mapped_column(ForeignKey("execution.id"))
    description: Mapped[str] = mapped_column(Text)
    gravite: Mapped[str] = mapped_column(String(20), default="Majeure")
    statut: Mapped[str] = mapped_column(String(20), default="OUVERTE")
    cree_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=maintenant)


class EntreeJournal(Base):
    __tablename__ = "journal"
    id: Mapped[int] = mapped_column(primary_key=True)
    organisation_id: Mapped[int] = mapped_column(ForeignKey("organisation.id"), index=True)
    mission_id: Mapped[int | None] = mapped_column(ForeignKey("mission.id"), index=True)
    acteur_id: Mapped[int | None] = mapped_column(ForeignKey("utilisateur.id"))
    agent: Mapped[str | None] = mapped_column(String(10))
    evenement: Mapped[str] = mapped_column(String(60))
    details: Mapped[str] = mapped_column(Text, default="{}")
    horodatage: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=maintenant)
    empreinte_precedente: Mapped[str] = mapped_column(String(64))
    empreinte: Mapped[str] = mapped_column(String(64))


class TacheIA(Base):
    __tablename__ = "tache_ia"
    id: Mapped[int] = mapped_column(primary_key=True)
    organisation_id: Mapped[int] = mapped_column(ForeignKey("organisation.id"), index=True)
    mission_id: Mapped[int] = mapped_column(ForeignKey("mission.id"), index=True)
    version_id: Mapped[int] = mapped_column(ForeignKey("version_exigence.id"))
    type: Mapped[str] = mapped_column(String(30))
    etat: Mapped[str] = mapped_column(String(20), default="EN_ATTENTE")
    erreur: Mapped[str | None] = mapped_column(Text)
    cree_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=maintenant)
    termine_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (CheckConstraint(_dans("etat", ETATS_TACHE), name="ck_tache_etat"),)
