import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { api, enregistrerJeton, jeton, type Utilisateur } from "./api";

interface Session {
  moi: Utilisateur | null;
  chargement: boolean;
  connecter: (email: string, motDePasse: string) => Promise<void>;
  changerMotDePasse: (actuel: string, nouveau: string) => Promise<void>;
  deconnecter: () => void;
  a: (role: "ANALYSTE" | "SUPERVISEUR" | "ADMIN") => boolean;
}

const Contexte = createContext<Session | null>(null);

export function FournisseurSession({ children }: { children: ReactNode }) {
  const [moi, setMoi] = useState<Utilisateur | null>(null);
  const [chargement, setChargement] = useState(true);

  useEffect(() => {
    if (!jeton()) {
      setChargement(false);
      return;
    }
    api<Utilisateur>("/auth/moi")
      .then(setMoi)
      .catch(() => enregistrerJeton(null))
      .finally(() => setChargement(false));
  }, []);

  useEffect(() => {
    const sortir = () => setMoi(null);
    // RA-55 : le serveur signale un mot de passe provisoire -> écran de changement
    const provisoire = () => setMoi((m) => (m ? { ...m, mot_de_passe_provisoire: true } : m));
    window.addEventListener("qatag:deconnexion", sortir);
    window.addEventListener("qatag:mot-de-passe-provisoire", provisoire);
    return () => {
      window.removeEventListener("qatag:deconnexion", sortir);
      window.removeEventListener("qatag:mot-de-passe-provisoire", provisoire);
    };
  }, []);

  const connecter = useCallback(async (email: string, motDePasse: string) => {
    const r = await api<{ jeton: string }>("/auth/connexion", {
      methode: "POST", corps: { email, mot_de_passe: motDePasse },
    });
    enregistrerJeton(r.jeton);
    setMoi(await api<Utilisateur>("/auth/moi"));
  }, []);

  // RA-56 / RA-58 : les autres sessions sont fermées, celle-ci reçoit un nouveau jeton
  const changerMotDePasse = useCallback(async (actuel: string, nouveau: string) => {
    const r = await api<{ jeton: string }>("/auth/mot-de-passe", {
      methode: "POST", corps: { actuel, nouveau },
    });
    enregistrerJeton(r.jeton);
    setMoi(await api<Utilisateur>("/auth/moi"));
  }, []);

  const deconnecter = useCallback(() => {
    enregistrerJeton(null);
    setMoi(null);
  }, []);

  const a = useCallback((role: string) => !!moi?.roles.includes(role as never), [moi]);

  return (
    <Contexte.Provider value={{ moi, chargement, connecter, changerMotDePasse, deconnecter, a }}>
      {children}
    </Contexte.Provider>
  );
}

export function useSession(): Session {
  const s = useContext(Contexte);
  if (!s) throw new Error("useSession hors de FournisseurSession");
  return s;
}
