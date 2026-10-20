from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from ..securite import LONGUEUR_MIN_MOT_DE_PASSE


class Inscription(BaseModel):
    email: EmailStr
    nom: str = Field(default="", max_length=200)
    mot_de_passe: str = Field(min_length=LONGUEUR_MIN_MOT_DE_PASSE, max_length=200)
    organisation: str | None = Field(default=None, max_length=200)


class Connexion(BaseModel):
    email: EmailStr
    mot_de_passe: str


class Jeton(BaseModel):
    jeton: str
    type: str = "bearer"


class UtilisateurSortie(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    nom: str
    roles: list[str]
    actif: bool
    cree_le: datetime


class CreationUtilisateur(Inscription):
    roles: list[str] = ["ANALYSTE"]


class ChangementRoles(BaseModel):
    roles: list[str] = Field(min_length=1)


class ChangementActif(BaseModel):
    actif: bool


class ConfigIAEntree(BaseModel):
    fournisseur: str
    modele: str = Field(min_length=1, max_length=100)


class CreationMission(BaseModel):
    titre: str = Field(min_length=1, max_length=300)
    texte: str = Field(min_length=1)


class NouvelleVersion(BaseModel):
    texte: str = Field(min_length=1)


class AjoutParticipant(BaseModel):
    email: EmailStr


class Decision(BaseModel):
    decision: str = Field(pattern="^(APPROUVE|REJETE)$")
    commentaire: str = ""


class Reponse(BaseModel):
    reponse: str = ""


class Precision(BaseModel):
    question: str = Field(min_length=1)
    reponse: str = Field(min_length=1)


class EcartCritere(BaseModel):
    motif: str = Field(min_length=1)


class ModificationCas(BaseModel):
    titre: str | None = None
    objectif: str | None = None
    exigence: str | None = None
    technique: str | None = None
    justification_technique: str | None = None
    priorite: str | None = None
    type: str | None = None
    preconditions: str | None = None
    donnees_test: str | None = None
    etapes: str | None = None
    resultat_attendu: str | None = None
    confirmer: bool = False


class DecisionQuestions(BaseModel):
    ids: list[int] = Field(min_length=1)
    decision: str | None = None          # HORS_PERIMETRE, REPORTEE, ou null pour annuler
    motif: str = ""


class EcartCriteres(BaseModel):
    ids: list[int] = Field(min_length=1)
    motif: str = Field(min_length=1)


class JustificationPhrases(BaseModel):
    ids: list[int] = Field(min_length=1)
    motif: str | None = None             # null pour annuler la justification
