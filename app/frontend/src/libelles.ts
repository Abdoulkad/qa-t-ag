// Vocabulaire de l'interface : un statut garde le même nom partout.
import type { StatutCas, StatutMission } from "./api";

export const STATUT_MISSION: Record<StatutMission, { libelle: string; ton: Ton }> = {
  ANALYSE_EN_COURS: { libelle: "Analyse en cours", ton: "neutre" },
  ECHEC_ANALYSE: { libelle: "Analyse en échec", ton: "alerte" },
  CLARIFICATION: { libelle: "À clarifier", ton: "attente" },
  REECRITURE: { libelle: "Réécriture en cours", ton: "neutre" },
  ATTENTE_PV1: { libelle: "Attend PV-1", ton: "porte" },
  CONCEPTION: { libelle: "Conception des cas", ton: "neutre" },
  ATTENTE_PV2: { libelle: "Attend PV-2", ton: "porte" },
  VALIDEE: { libelle: "Validée", ton: "succes" },
  EN_RECETTE: { libelle: "En recette", ton: "neutre" },
  CLOTUREE: { libelle: "Clôturée", ton: "succes" },
  A_CORRIGER: { libelle: "À corriger", ton: "alerte" },
};

export const STATUT_CAS: Record<StatutCas, { libelle: string; ton: Ton }> = {
  PRET: { libelle: "Prêt", ton: "succes" },
  INCOMPLET: { libelle: "Incomplet", ton: "alerte" },
  A_CLARIFIER: { libelle: "À clarifier", ton: "attente" },
};

export type Ton = "neutre" | "attente" | "porte" | "succes" | "alerte";

export const ROLES: Record<string, string> = {
  ANALYSTE: "Analyste QA",
  SUPERVISEUR: "Superviseur",
  ADMIN: "Administrateur",
};

export const EVENEMENTS: Record<string, string> = {
  compte_cree: "Compte créé",
  connexion_bloquee: "Connexion bloquée après trop d'échecs",
  roles_modifies: "Rôles modifiés",
  compte_desactive: "Compte désactivé",
  compte_reactive: "Compte réactivé",
  config_ia_modifiee: "IA modifiée",
  mission_creee: "Mission créée",
  version_creee: "Nouvelle version",
  participant_ajoute: "Participant ajouté",
  analyse_terminee: "Analyse terminée",
  analyse_echec: "Analyse en échec",
  question_repondue: "Réponse enregistrée",
  precision_ajoutee: "Précision ajoutée",
  question_decidee: "Décision sur une question",
  decision_question_annulee: "Décision annulée",
  reecriture_lancee: "Réécriture lancée",
  reecriture_terminee: "Réécriture terminée",
  reecriture_echec: "Réécriture en échec",
  critere_ecarte: "Critère écarté",
  defaut_confirme: "Défaut confirmé",
  defaut_ecarte: "Défaut écarté",
  validation_defaut_annulee: "Validation du défaut annulée",
  defaut_requalifie: "Criticité changée",
  regle_ecartee: "Règle écartée",
  phrase_non_reprise_justifiee: "Phrase non reprise justifiée",
  justification_phrase_annulee: "Justification annulée",
  porte_decidee: "Décision Human Gate",
  conception_terminee: "Cas conçus",
  conception_echec: "Conception en échec",
  cas_modifie: "Cas corrigé",
  tache_relancee: "Agent relancé",
  cahier_cas_exporte: "Cahier des cas exporté",
};

export const DECISION_QUESTION: Record<string, string> = {
  HORS_PERIMETRE: "Hors périmètre",
  REPORTEE: "Reportée",
};

export function date(iso: string | null | undefined): string {
  if (!iso) return "";
  return new Date(iso).toLocaleString("fr-FR", {
    day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit",
  });
}
