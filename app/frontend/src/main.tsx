import "@fontsource/ibm-plex-sans/400.css";
import "@fontsource/ibm-plex-sans/500.css";
import "@fontsource/ibm-plex-sans/600.css";
import "@fontsource/ibm-plex-mono/500.css";
import "@fontsource/ibm-plex-mono/600.css";
import "./styles.css";

import { StrictMode, type ReactNode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import Cadre from "./Cadre";
import { FournisseurSession, useSession } from "./session";
import Analyse from "./pages/Analyse";
import Configuration from "./pages/Configuration";
import Connexion from "./pages/Connexion";
import MissionPage from "./pages/Mission";
import PilotagePage from "./pages/Pilotage";
import SuiviCas from "./pages/SuiviCas";
import Utilisateurs from "./pages/Utilisateurs";

function Protege({ children, role }: { children: ReactNode; role?: "ADMIN" }) {
  const { moi, chargement, a } = useSession();
  if (chargement) return <div className="charge">Chargement…</div>;
  if (!moi) return <Navigate to="/connexion" replace />;
  if (role && !a(role)) return <Navigate to="/" replace />;
  return <>{children}</>;
}

function Accueil() {
  const { a } = useSession();
  // Un administrateur sans rôle QA n'a pas de missions : il arrive sur les comptes
  if (!a("ANALYSTE") && !a("SUPERVISEUR")) return <Navigate to="/utilisateurs" replace />;
  return <PilotagePage />;
}

function Application() {
  const { moi, chargement } = useSession();
  return (
    <Routes>
      <Route path="/connexion" element={chargement ? null : moi ? <Navigate to="/" replace /> : <Connexion />} />
      <Route element={<Protege><Cadre /></Protege>}>
        <Route index element={<Accueil />} />
        <Route path="analyse" element={<Analyse />} />
        <Route path="missions/:id" element={<MissionPage />} />
        <Route path="cas" element={<SuiviCas />} />
        <Route path="utilisateurs" element={<Protege role="ADMIN"><Utilisateurs /></Protege>} />
        <Route path="configuration" element={<Protege role="ADMIN"><Configuration /></Protege>} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

createRoot(document.getElementById("racine")!).render(
  <StrictMode>
    <BrowserRouter>
      <FournisseurSession><Application /></FournisseurSession>
    </BrowserRouter>
  </StrictMode>,
);
