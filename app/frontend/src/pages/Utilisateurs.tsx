import { useState, type FormEvent } from "react";
import { api, type Role, type Utilisateur } from "../api";
import { initiales, MessageErreur, Pastille, useAction, useDonnees } from "../composants";
import { date, ROLES } from "../libelles";
import { useSession } from "../session";

const TOUS: Role[] = ["ANALYSTE", "SUPERVISEUR", "ADMIN"];

/** Mot de passe provisoire aléatoire (12 caractères, sans caractères ambigus). */
function motDePasseAleatoire(): string {
  const alphabet = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789";
  const octets = crypto.getRandomValues(new Uint32Array(12));
  return Array.from(octets, (n) => alphabet[n % alphabet.length]).join("");
}

export default function Utilisateurs() {
  const { moi } = useSession();
  const { donnees, erreur, recharger } = useDonnees<Utilisateur[]>("/utilisateurs");
  const action = useAction();
  const [provisoire, setProvisoire] = useState<{ email: string; mot: string } | null>(null);

  // RA-57 : nouveau mot de passe provisoire, à changer à la prochaine connexion
  const reinitialiser = (u: Utilisateur) => action.lancer(async () => {
    const mot = motDePasseAleatoire();
    await api(`/utilisateurs/${u.id}/mot-de-passe`, { methode: "POST", corps: { mot_de_passe: mot } });
    setProvisoire({ email: u.email, mot });
    recharger();
  });

  const basculerRole = (u: Utilisateur, r: Role) => action.lancer(async () => {
    const roles = u.roles.includes(r) ? u.roles.filter((x) => x !== r) : [...u.roles, r];
    await api(`/utilisateurs/${u.id}/roles`, { methode: "PATCH", corps: { roles } });
    recharger();
  });
  const basculerActif = (u: Utilisateur) => action.lancer(async () => {
    await api(`/utilisateurs/${u.id}/actif`, { methode: "PATCH", corps: { actif: !u.actif } });
    recharger();
  });

  return (
    <div className="pile">
      <div className="entete-page">
        <div>
          <h1>Utilisateurs</h1>
          <p>Les rôles se cumulent. Un Analyste ne voit que les missions auxquelles il participe ; un Superviseur les voit toutes et décide aux Human Gates.</p>
        </div>
      </div>
      <MessageErreur erreur={erreur || action.erreur} />
      {provisoire && (
        <div className="message-info" role="status">
          Mot de passe provisoire de <strong>{provisoire.email}</strong> :{" "}
          <code style={{ fontSize: "1rem", userSelect: "all" }}>{provisoire.mot}</code>.
          Communiquez-le de vive voix : il ne sera plus affiché. La personne devra le changer à
          sa prochaine connexion, et ses sessions ouvertes sont fermées.{" "}
          <button type="button" className="lien" onClick={() => setProvisoire(null)}>Masquer</button>
        </div>
      )}
      <section className="panneau">
        <div className="table-defile">
          <table>
            <thead><tr><th>Compte</th>{TOUS.map((r) => <th key={r}>{ROLES[r]}</th>)}<th>Accès</th></tr></thead>
            <tbody>
              {(donnees ?? []).map((u) => (
                <tr key={u.id}>
                  <td>
                    <div className="rangee" style={{ flexWrap: "nowrap" }}>
                      <span className="avatar">{initiales(u.nom, u.email)}</span>
                      <div>
                        <div>{u.nom || u.email} {u.id === moi?.id && <span className="discret-texte">(vous)</span>}</div>
                        <div className="sous">{u.email} · inscrit le {date(u.cree_le)}</div>
                      </div>
                    </div>
                  </td>
                  {TOUS.map((r) => (
                    <td key={r}>
                      <input type="checkbox" checked={u.roles.includes(r)} disabled={action.enCours}
                             onChange={() => basculerRole(u, r)}
                             aria-label={`${ROLES[r]} pour ${u.email}`} />
                    </td>
                  ))}
                  <td>
                    <div className="rangee">
                      {u.actif ? <Pastille ton="succes">Actif</Pastille> : <Pastille ton="alerte">Désactivé</Pastille>}
                      {u.mot_de_passe_provisoire && (
                        <Pastille ton="attente">Mot de passe provisoire</Pastille>
                      )}
                      {u.id !== moi?.id && (
                        <button className="bouton discret petit" disabled={action.enCours} onClick={() => basculerActif(u)}>
                          {u.actif ? "Désactiver" : "Réactiver"}
                        </button>
                      )}
                      {u.id !== moi?.id && u.actif && (
                        <button className="bouton discret petit" disabled={action.enCours}
                                onClick={() => reinitialiser(u)}
                                title="Attribue un nouveau mot de passe provisoire">
                          Réinitialiser le mot de passe
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      <NouveauCompte recharger={recharger} />
    </div>
  );
}

function NouveauCompte({ recharger }: { recharger: () => void }) {
  const [email, setEmail] = useState("");
  const [nom, setNom] = useState("");
  const [motDePasse, setMotDePasse] = useState("");
  const [roles, setRoles] = useState<Role[]>(["ANALYSTE"]);
  const action = useAction();
  const envoyer = (ev: FormEvent) => {
    ev.preventDefault();
    action.lancer(async () => {
      await api("/utilisateurs", { methode: "POST", corps: { email, nom, mot_de_passe: motDePasse, roles } });
      setEmail(""); setNom(""); setMotDePasse(""); setRoles(["ANALYSTE"]);
      recharger();
    });
  };
  return (
    <form className="panneau" onSubmit={envoyer}>
      <div className="panneau-entete">
        <h2>Créer un compte</h2>
        <p>Le mot de passe est provisoire : la personne le remplace à sa première connexion.
          Communiquez-le de vive voix.</p>
      </div>
      <div className="panneau-corps pile">
        <div className="rangee" style={{ alignItems: "flex-start" }}>
          <div className="champ" style={{ flex: 1, minWidth: 200 }}>
            <label htmlFor="n-email">E-mail</label>
            <input id="n-email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>
          <div className="champ" style={{ flex: 1, minWidth: 160 }}>
            <label htmlFor="n-nom">Nom</label>
            <input id="n-nom" type="text" value={nom} onChange={(e) => setNom(e.target.value)} />
          </div>
          <div className="champ" style={{ flex: 1, minWidth: 160 }}>
            <label htmlFor="n-mdp">Mot de passe provisoire</label>
            <div className="rangee" style={{ flexWrap: "nowrap", gap: 6 }}>
              <input id="n-mdp" type="text" required minLength={8} value={motDePasse}
                     onChange={(e) => setMotDePasse(e.target.value)} autoComplete="off" spellCheck={false} />
              <button type="button" className="bouton discret petit" onClick={() => setMotDePasse(motDePasseAleatoire())}>
                Générer
              </button>
            </div>
          </div>
        </div>
        <fieldset className="rangee" style={{ border: 0, padding: 0, margin: 0 }}>
          <legend className="etiquette" style={{ marginBottom: 6 }}>Rôles</legend>
          {TOUS.map((r) => (
            <label key={r} className="rangee" style={{ gap: 6, marginRight: 14 }}>
              <input type="checkbox" checked={roles.includes(r)}
                     onChange={() => setRoles(roles.includes(r) ? roles.filter((x) => x !== r) : [...roles, r])} />
              {ROLES[r]}
            </label>
          ))}
        </fieldset>
        <MessageErreur erreur={action.erreur} />
        <div><button className="bouton principal" disabled={action.enCours || !roles.length}>Créer le compte</button></div>
      </div>
    </form>
  );
}
