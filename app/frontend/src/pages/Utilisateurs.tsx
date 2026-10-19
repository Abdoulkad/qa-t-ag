import { useState, type FormEvent } from "react";
import { api, type Role, type Utilisateur } from "../api";
import { initiales, MessageErreur, Pastille, useAction, useDonnees } from "../composants";
import { date, ROLES } from "../libelles";
import { useSession } from "../session";

const TOUS: Role[] = ["ANALYSTE", "SUPERVISEUR", "ADMIN"];

export default function Utilisateurs() {
  const { moi } = useSession();
  const { donnees, erreur, recharger } = useDonnees<Utilisateur[]>("/utilisateurs");
  const action = useAction();

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
                      {u.id !== moi?.id && (
                        <button className="bouton discret petit" disabled={action.enCours} onClick={() => basculerActif(u)}>
                          {u.actif ? "Désactiver" : "Réactiver"}
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
        <p>Communiquez le mot de passe provisoire à la personne de vive voix.</p>
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
            <input id="n-mdp" type="password" required minLength={8} value={motDePasse}
                   onChange={(e) => setMotDePasse(e.target.value)} autoComplete="new-password" />
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
