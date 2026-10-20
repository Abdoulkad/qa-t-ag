// Client de l'API QA-T-AG. Le jeton de session est gardé dans le navigateur.

const CLE_JETON = "qatag.jeton";

export function jeton(): string | null {
  try {
    return localStorage.getItem(CLE_JETON);
  } catch {
    return null;
  }
}

export function enregistrerJeton(valeur: string | null) {
  try {
    if (valeur) localStorage.setItem(CLE_JETON, valeur);
    else localStorage.removeItem(CLE_JETON);
  } catch {
    /* navigation privée : la session reste en mémoire le temps de l'onglet */
  }
}

/** Erreur renvoyée par l'API, avec la règle métier (RA-xx) quand il y en a une. */
export class ErreurApi extends Error {
  statut: number;
  regle?: string;
  elements: string[];
  constructor(statut: number, message: string, regle?: string, elements: string[] = []) {
    super(message);
    this.statut = statut;
    this.regle = regle;
    this.elements = elements;
  }
}

function messageDe(corps: unknown, statut: number): string {
  if (corps && typeof corps === "object" && "detail" in corps) {
    const d = (corps as { detail: unknown }).detail;
    if (typeof d === "string") return d;
    if (Array.isArray(d) && d.length) {
      // erreurs de validation FastAPI
      return d.map((e: { msg?: string }) => e.msg ?? "Valeur invalide").join(" ; ");
    }
  }
  return statut >= 500 ? "Le serveur a rencontré une erreur." : "Requête refusée.";
}

export async function api<T = unknown>(
  chemin: string,
  options: { methode?: string; corps?: unknown; formulaire?: FormData } = {},
): Promise<T> {
  const entetes: Record<string, string> = {};
  const j = jeton();
  if (j) entetes["Authorization"] = "Bearer " + j;
  let body: BodyInit | undefined;
  if (options.formulaire) body = options.formulaire;
  else if (options.corps !== undefined) {
    entetes["Content-Type"] = "application/json";
    body = JSON.stringify(options.corps);
  }
  let r: Response;
  try {
    r = await fetch("/api" + chemin, { method: options.methode ?? "GET", headers: entetes, body });
  } catch {
    throw new ErreurApi(0, "Le serveur QA-T-AG ne répond pas. Vérifiez qu'il est lancé.");
  }
  const texte = await r.text();
  const corps = texte ? JSON.parse(texte) : null;
  if (!r.ok) {
    if (r.status === 401 && chemin !== "/auth/connexion") {
      enregistrerJeton(null);
      window.dispatchEvent(new Event("qatag:deconnexion"));
    }
    throw new ErreurApi(r.status, messageDe(corps, r.status), corps?.regle, corps?.elements ?? []);
  }
  return corps as T;
}

/** Télécharge un fichier produit par le serveur (le jeton ne passe pas dans un lien). */
export async function telecharger(chemin: string): Promise<void> {
  const entetes: Record<string, string> = {};
  const j = jeton();
  if (j) entetes["Authorization"] = "Bearer " + j;
  let r: Response;
  try {
    r = await fetch("/api" + chemin, { headers: entetes });
  } catch {
    throw new ErreurApi(0, "Le serveur QA-T-AG ne répond pas. Vérifiez qu'il est lancé.");
  }
  if (!r.ok) {
    const texte = await r.text();
    const corps = texte ? JSON.parse(texte) : null;
    throw new ErreurApi(r.status, messageDe(corps, r.status), corps?.regle, corps?.elements ?? []);
  }
  const dispo = r.headers.get("Content-Disposition") ?? "";
  const m = /filename\*=UTF-8''([^;]+)/.exec(dispo);
  const nom = m ? decodeURIComponent(m[1]) : "export.docx";
  const url = URL.createObjectURL(await r.blob());
  const a = document.createElement("a");
  a.href = url;
  a.download = nom;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

// --- Types renvoyés par l'API ------------------------------------------------

export type Role = "ANALYSTE" | "SUPERVISEUR" | "ADMIN";

export interface Utilisateur {
  id: number;
  email: string;
  nom: string;
  roles: Role[];
  actif: boolean;
  cree_le: string;
}

export type StatutMission =
  | "ANALYSE_EN_COURS" | "ECHEC_ANALYSE" | "CLARIFICATION" | "REECRITURE" | "ATTENTE_PV1"
  | "CONCEPTION" | "ATTENTE_PV2" | "VALIDEE" | "EN_RECETTE" | "CLOTUREE" | "A_CORRIGER";

export interface ResumeMission {
  id: number;
  reference: string;
  titre: string;
  statut: StatutMission;
  version: number;
  score_clarte: number | null;
  nb_defauts: number;
  cree_le: string;
  modifie_le: string;
}

export interface Defaut {
  id: number; code: string; categorie: string; gravite: string;
  section: string | null; citation: string | null; citation_verifiee: boolean;
}

export interface Question {
  id: number; code: string; defaut_id: number | null; question: string; bloquante: boolean;
  reponse: string | null; ajoutee_par_humain: boolean; repondu_le: string | null;
  decision: "HORS_PERIMETRE" | "REPORTEE" | null; motif_decision: string | null;
  decide_le: string | null;
}

export interface ElementSource {
  id: number; code: string; texte: string; sources: string[]; sources_rejetees: string[];
  statut: "SOURCE" | "HYPOTHESE";
}

export interface Critere extends ElementSource {
  regles: string[];            // règles métier vérifiées (RG-n)
}

export interface Regle extends ElementSource {
  criteres: string[];          // critères qui la vérifient
}

export type StatutPhrase = "TITRE" | "COUVERTE" | "NON_COUVERTE" | "JUSTIFIEE";

export interface PhraseCouverture {
  id: number; numero: number; texte: string; statut: StatutPhrase;
  motif: string | null; justifie_le: string | null;
}

export interface DecisionPorte {
  porte: "PV-1" | "PV-2"; decision: "APPROUVE" | "REJETE"; commentaire: string;
  decideur_id: number; auto_validation: boolean; decide_le: string;
}

export interface Version {
  id: number; numero: number; texte: string; nom_source: string; empreinte: string;
  auteur_id: number; figee: boolean; ia: { fournisseur: string | null; modele: string | null };
  score_clarte: number | null; controle_revue: string | null; code_controle_revue: number | null;
  defauts: Defaut[]; questions: Question[]; decisions: DecisionPorte[];
  texte_reecrit: string | null; controle_reecriture: string | null;
  controle_conception: string | null; criteres: Critere[]; points_ouverts: string[];
  regles: Regle[]; couverture: PhraseCouverture[];
  cree_le: string;
}

export interface Mission extends ResumeMission {
  participants: { id: number; email: string; nom: string }[];
  versions: Version[];
  taches_en_cours: number[];
  derniere_tache: { id: number; type: string; etat: Tache["etat"]; erreur: string | null;
                    termine_le: string | null } | null;
  porte_en_attente: "PV-1" | "PV-2" | null;
  bloquants_porte: string[];
}

export type StatutCas = "PRET" | "INCOMPLET" | "A_CLARIFIER";

export interface Cas {
  id: number; code: string; titre: string; objectif: string; exigence: string;
  references: string[]; technique: string; justification_technique: string; priorite: string;
  type: string; preconditions: string; donnees_test: string; etapes: string;
  resultat_attendu: string; statut: StatutCas; motif_statut: string;
  confirme_par_id: number | null;
}

export interface Tache {
  id: number; type: string; etat: "EN_ATTENTE" | "EN_COURS" | "TERMINEE" | "ECHEC";
  erreur: string | null; mission_id: number;
}

export interface EntreeJournal {
  id: number; mission_id: number | null; acteur_id: number | null; agent: string | null;
  evenement: string; details: Record<string, unknown>; horodatage: string;
}

export interface Pilotage {
  missions: number;
  human_gate_en_attente: number;
  taux_pass: number | null;
  taux_approbation: number | null;
  file_human_gate: ResumeMission[];
}

export interface ConfigIA {
  actif: { fournisseur: string; modele: string } | null;
  fournisseurs: { code: string; libelle: string; cle_presente: boolean; cle_requise: boolean;
                  modele_suggere: string }[];
}

export interface Tracabilite {
  matrice: { reference: string; libelle: string; cas: string[] }[];
  regles: { code: string; texte: string; criteres: string[]; cas: string[] }[];
  couverture: number | null;
  cas_sans_reference: string[];
  par_technique: Record<string, number>;
}
