import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import { api, ErreurApi, type StatutMission, type Tache } from "./api";
import { STATUT_CAS, STATUT_MISSION, type Ton } from "./libelles";
import type { StatutCas } from "./api";

export function Pastille({ ton, children }: { ton: Ton; children: ReactNode }) {
  return <span className={"pastille ton-" + ton}>{children}</span>;
}

export function PastilleMission({ statut }: { statut: StatutMission }) {
  const s = STATUT_MISSION[statut];
  return <Pastille ton={s.ton}>{s.libelle}</Pastille>;
}

export function PastilleCas({ statut }: { statut: StatutCas }) {
  const s = STATUT_CAS[statut];
  return <Pastille ton={s.ton}>{s.libelle}</Pastille>;
}

/** Affiche une erreur d'API, avec la règle métier et les éléments bloquants. */
export function MessageErreur({ erreur }: { erreur: unknown }) {
  if (!erreur) return null;
  const e = erreur instanceof ErreurApi ? erreur : null;
  return (
    <div className="message-erreur" role="alert">
      {e?.regle && <strong>{e.regle} · </strong>}
      {e ? e.message : "Une erreur inattendue est survenue."}
      {e && e.elements.length > 0 && (
        <ul>{e.elements.map((x) => <li key={x}>{x}</li>)}</ul>
      )}
    </div>
  );
}

/** Charge une ressource de l'API ; `recharger` la relit. */
export function useDonnees<T>(chemin: string | null) {
  const [donnees, setDonnees] = useState<T | null>(null);
  const [erreur, setErreur] = useState<unknown>(null);
  const [chargement, setChargement] = useState(true);
  const recharger = useCallback(async () => {
    if (!chemin) return;
    try {
      setDonnees(await api<T>(chemin));
      setErreur(null);
    } catch (e) {
      setErreur(e);
    } finally {
      setChargement(false);
    }
  }, [chemin]);
  useEffect(() => {
    setChargement(true);
    recharger();
  }, [recharger]);
  return { donnees, erreur, chargement, recharger };
}

/** Suit une tâche IA jusqu'à sa fin, puis appelle `fin`. */
export function useSuiviTache(fin: () => void) {
  const [tacheId, setTacheId] = useState<number | null>(null);
  const [tache, setTache] = useState<Tache | null>(null);
  const finRef = useRef(fin);
  finRef.current = fin;
  useEffect(() => {
    if (tacheId === null) return;
    let actif = true;
    const tour = async () => {
      try {
        const t = await api<Tache>("/taches/" + tacheId);
        if (!actif) return;
        setTache(t);
        if (t.etat === "TERMINEE" || t.etat === "ECHEC") {
          setTacheId(null);
          finRef.current();
          return;
        }
      } catch {
        /* nouvel essai au prochain tour */
      }
      if (actif) setTimeout(tour, 2000);
    };
    tour();
    return () => { actif = false; };
  }, [tacheId]);
  return { suivre: setTacheId, enCours: tacheId !== null, tache };
}

/** Un bouton qui exécute une action d'API et montre son erreur éventuelle. */
export function useAction() {
  const [enCours, setEnCours] = useState(false);
  const [erreur, setErreur] = useState<unknown>(null);
  const lancer = useCallback(async <T,>(f: () => Promise<T>): Promise<T | undefined> => {
    setEnCours(true);
    setErreur(null);
    try {
      return await f();
    } catch (e) {
      setErreur(e);
      return undefined;
    } finally {
      setEnCours(false);
    }
  }, []);
  return { enCours, erreur, lancer, effacer: () => setErreur(null) };
}

// --- La chaîne de traitement ----------------------------------------------

type EtatEtape = "faite" | "courante" | "echec" | "";
type EtatPorte = "ouverte" | "attend" | "fermee" | "";

const ORDRE: StatutMission[] = [
  "ANALYSE_EN_COURS", "CLARIFICATION", "REECRITURE", "ATTENTE_PV1", "CONCEPTION",
  "ATTENTE_PV2", "VALIDEE", "EN_RECETTE", "CLOTUREE",
];

function rang(statut: StatutMission): number {
  if (statut === "ECHEC_ANALYSE") return 0;
  if (statut === "A_CORRIGER") return -1;
  return ORDRE.indexOf(statut);
}

function etatsChaine(statut: StatutMission, rejetee: "PV-1" | "PV-2" | null) {
  const r = rang(statut);
  const etape = (debut: number, fin: number): EtatEtape => {
    if (statut === "ECHEC_ANALYSE" && debut === 0) return "echec";
    if (r > fin) return "faite";
    if (r >= debut && r <= fin) return "courante";
    return "";
  };
  const porte = (attente: number, nom: "PV-1" | "PV-2"): EtatPorte => {
    if (rejetee === nom) return "fermee";
    if (r > attente) return "ouverte";
    if (r === attente) return "attend";
    return "";
  };
  return {
    analyser: etape(0, 0), clarifier: etape(1, 2), pv1: porte(3, "PV-1"),
    concevoir: etape(4, 4), pv2: porte(5, "PV-2"), recette: etape(6, 7),
  };
}

export function Chaine({ statut, rejetee }: { statut: StatutMission; rejetee: "PV-1" | "PV-2" | null }) {
  const e = etatsChaine(statut, rejetee);
  const Etape = ({ etat, nom, detail }: { etat: EtatEtape; nom: string; detail: string }) => (
    <div className={"etape " + etat}>
      <div className="etape-nom">{nom}</div>
      <div className="etape-detail">{detail}</div>
    </div>
  );
  const Porte = ({ etat, nom }: { etat: EtatPorte; nom: string }) => (
    <div className={"porte-chaine " + etat} title={"Human Gate " + nom}>
      <span>{nom}</span>
    </div>
  );
  return (
    <nav className="chaine" aria-label="Avancement de la mission">
      <Etape etat={e.analyser} nom="Analyser" detail="AG-01 · défauts" />
      <Etape etat={e.clarifier} nom="Clarifier, réécrire" detail="Réponses, critères" />
      <Porte etat={e.pv1} nom="PV-1" />
      <Etape etat={e.concevoir} nom="Concevoir" detail="AG-02 · cas de test" />
      <Porte etat={e.pv2} nom="PV-2" />
      <Etape etat={e.recette} nom="Recette" detail="Exécution, cahier" />
    </nav>
  );
}

export function MiniChaine({ statut }: { statut: StatutMission }) {
  const e = etatsChaine(statut, null);
  const c = (x: EtatEtape) => (x === "faite" ? "f" : "");
  const p = (x: EtatPorte) => (x === "ouverte" ? "p f" : x === "attend" ? "p a" : "p");
  return (
    <span className="mini-chaine" aria-hidden="true">
      <i className={c(e.analyser)} /><i className={c(e.clarifier)} /><i className={p(e.pv1)} />
      <i className={c(e.concevoir)} /><i className={p(e.pv2)} /><i className={c(e.recette)} />
    </span>
  );
}

export function Volet({ titre, sousTitre, fermer, pied, children }: {
  titre: ReactNode; sousTitre?: ReactNode; fermer: () => void; pied?: ReactNode; children: ReactNode;
}) {
  useEffect(() => {
    const esc = (ev: KeyboardEvent) => { if (ev.key === "Escape") fermer(); };
    window.addEventListener("keydown", esc);
    return () => window.removeEventListener("keydown", esc);
  }, [fermer]);
  return (
    <>
      <div className="voile" onClick={fermer} />
      <aside className="volet" role="dialog" aria-modal="true">
        <div className="volet-entete">
          <div>
            <h2>{titre}</h2>
            {sousTitre && <div className="discret-texte">{sousTitre}</div>}
          </div>
          <button className="bouton discret" onClick={fermer} aria-label="Fermer">Fermer</button>
        </div>
        <div className="volet-corps">{children}</div>
        {pied && <div className="volet-pied">{pied}</div>}
      </aside>
    </>
  );
}

export function initiales(nom: string, email: string) {
  const base = nom.trim() || email;
  const mots = base.replace(/@.*/, "").split(/[\s._-]+/).filter(Boolean);
  return ((mots[0]?.[0] ?? "") + (mots[1]?.[0] ?? "")).toUpperCase() || "?";
}
