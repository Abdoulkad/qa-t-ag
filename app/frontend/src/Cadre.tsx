import { createContext, useContext, useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import { api, type Pilotage, type Role } from "./api";
import { initiales } from "./composants";
import { Marque } from "./Logo";
import { ROLES } from "./libelles";
import { useSession } from "./session";

/** Une page peut compléter le fil d'Ariane (ex. la référence d'une mission). */
const FilContexte = createContext<(complement: string | null) => void>(() => {});
export function useComplementFil(complement: string | null) {
  const fixer = useContext(FilContexte);
  useEffect(() => { fixer(complement); return () => fixer(null); }, [complement, fixer]);
}

const PAGES: Record<string, [string, string]> = {
  "/": ["Espace QA", "Vue de pilotage"],
  "/analyse": ["Espace QA", "Analyse des exigences"],
  "/cas": ["Espace QA", "Suivi des cas"],
  "/utilisateurs": ["Administration", "Utilisateurs"],
  "/configuration": ["Administration", "Configuration IA"],
};

const ROLE_PRINCIPAL: Role[] = ["ADMIN", "SUPERVISEUR", "ANALYSTE"];

/** Barre d'en-tête de chaque page : fil d'Ariane à gauche, profil connecté à droite. */
function EnteteApp({ complement }: { complement: string | null }) {
  const { pathname } = useLocation();
  const { moi } = useSession();
  if (!moi) return null;
  const mission = pathname.startsWith("/missions/");
  const [espace, page] = mission ? ["Espace QA", "Vue de pilotage"] : PAGES[pathname] ?? ["Espace QA", ""];
  const principal = ROLE_PRINCIPAL.find((r) => moi.roles.includes(r));
  return (
    <header className="entete-app">
      <nav aria-label="Fil d'Ariane" className="fil-ariane">
        <span>{espace}</span>
        <span className="separateur" aria-hidden="true">›</span>
        {mission ? <Link to="/">{page}</Link> : <span aria-current="page" className="courant">{page}</span>}
        {mission && <>
          <span className="separateur" aria-hidden="true">›</span>
          <span aria-current="page" className="courant">{complement ?? "Mission"}</span>
        </>}
      </nav>
      <div className="profil" title={moi.roles.map((r) => ROLES[r]).join(", ")}>
        <span className="profil-statut" aria-hidden="true" />
        <span className="profil-role">{principal ? ROLES[principal] : ""}</span>
        <span className="profil-separateur" aria-hidden="true" />
        <span className="profil-nom">{moi.nom || moi.email}</span>
        <span className="avatar">{initiales(moi.nom, moi.email)}</span>
        <span className="invisible">connecté</span>
      </div>
    </header>
  );
}

const trait = { fill: "none", stroke: "currentColor", strokeWidth: 1.7, strokeLinecap: "round" as const, strokeLinejoin: "round" as const };

export function Icone({ nom }: { nom: string }) {
  const d: Record<string, React.ReactNode> = {
    pilotage: <><rect x="3" y="3" width="7" height="9" rx="1.5" {...trait} /><rect x="14" y="3" width="7" height="5" rx="1.5" {...trait} /><rect x="14" y="12" width="7" height="9" rx="1.5" {...trait} /><rect x="3" y="16" width="7" height="5" rx="1.5" {...trait} /></>,
    analyse: <><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" {...trait} /><path d="M14 3v5h5M9 13h6M9 17h4" {...trait} /></>,
    cas: <><path d="M9 6h11M9 12h11M9 18h11" {...trait} /><path d="m3.5 6 1.2 1.2L7 5M3.5 12l1.2 1.2L7 11M3.5 18l1.2 1.2L7 17" {...trait} /></>,
    utilisateurs: <><circle cx="9" cy="8" r="3.5" {...trait} /><path d="M2.5 20a6.5 6.5 0 0 1 13 0M16 4.5a3.5 3.5 0 0 1 0 7M21.5 20a6.5 6.5 0 0 0-4-6" {...trait} /></>,
    config: <><circle cx="12" cy="12" r="3" {...trait} /><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z" {...trait} /></>,
    marque: <path d="M3 12h4l2-5 4 10 2-5h6" {...trait} strokeWidth={2.2} />,
    sortie: <><path d="M15 4h3a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-3M10 17l-5-5 5-5M5 12h11" {...trait} /></>,
  };
  return <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true">{d[nom]}</svg>;
}

export default function Cadre() {
  const { moi, a, deconnecter } = useSession();
  const [enAttente, setEnAttente] = useState(0);
  const [complementFil, setComplementFil] = useState<string | null>(null);

  useEffect(() => {
    let actif = true;
    const lire = () => api<Pilotage>("/pilotage")
      .then((p) => actif && setEnAttente(p.human_gate_en_attente)).catch(() => {});
    lire();
    const t = setInterval(lire, 30000);
    return () => { actif = false; clearInterval(t); };
  }, []);

  if (!moi) return null;
  const acteur = a("ANALYSTE") || a("SUPERVISEUR");
  return (
    <div className="cadre">
      <aside className="barre">
        <NavLink to="/" className="marque" aria-label="QA-T-AG, vue de pilotage">
          <Marque />
        </NavLink>
        <nav className="nav" aria-label="Navigation principale">
          {acteur && <>
            <div className="nav-titre">Espace QA</div>
            <NavLink to="/" end><Icone nom="pilotage" />Vue de pilotage
              {enAttente > 0 && <span className="compteur" title="Décisions Human Gate en attente">{enAttente}</span>}
            </NavLink>
            <NavLink to="/analyse"><Icone nom="analyse" />Analyse des exigences</NavLink>
            <NavLink to="/cas"><Icone nom="cas" />Suivi des cas</NavLink>
          </>}
          {a("ADMIN") && <>
            <div className="nav-titre">Administration</div>
            <NavLink to="/utilisateurs"><Icone nom="utilisateurs" />Utilisateurs</NavLink>
            <NavLink to="/configuration"><Icone nom="config" />Configuration IA</NavLink>
          </>}
        </nav>
        <div className="barre-pied">
          <button className="bouton discret" onClick={deconnecter}><Icone nom="sortie" />Se déconnecter</button>
        </div>
      </aside>
      <div className="principal">
        <EnteteApp complement={complementFil} />
        <FilContexte.Provider value={setComplementFil}>
          <main className="page"><Outlet /></main>
        </FilContexte.Provider>
      </div>
    </div>
  );
}
