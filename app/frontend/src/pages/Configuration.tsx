import { useEffect, useState } from "react";
import { api, type ConfigIA } from "../api";
import { MessageErreur, Pastille, useAction, useDonnees } from "../composants";

export default function Configuration() {
  const { donnees: c, erreur, recharger } = useDonnees<ConfigIA>("/config-ia");
  const [fournisseur, setFournisseur] = useState("");
  const [modele, setModele] = useState("");
  const [enregistre, setEnregistre] = useState(false);
  const action = useAction();

  useEffect(() => {
    if (c?.actif) { setFournisseur(c.actif.fournisseur); setModele(c.actif.modele); }
  }, [c]);

  const choix = c?.fournisseurs.find((f) => f.code === fournisseur);

  return (
    <div className="pile" style={{ maxWidth: 820 }}>
      <div className="entete-page">
        <div>
          <h1>Configuration IA</h1>
          <p>Le fournisseur et le modèle utilisés par tous les agents de votre organisation.</p>
        </div>
      </div>
      <MessageErreur erreur={erreur} />

      {c && (
        <section className="panneau">
          <div className="panneau-entete">
            <h2>Fournisseurs</h2>
            <p>Les clés d'API se renseignent dans le fichier .env du serveur, jamais ici.</p>
          </div>
          <div className="table-defile">
            <table>
              <thead><tr><th>Fournisseur</th><th>Clé d'API</th><th>Modèle suggéré</th></tr></thead>
              <tbody>
                {c.fournisseurs.map((f) => (
                  <tr key={f.code}>
                    <td>{f.libelle}{c.actif?.fournisseur === f.code && <> <Pastille ton="succes">Actif</Pastille></>}</td>
                    <td>{!f.cle_requise
                      ? <span className="discret-texte">Aucune, modèle local</span>
                      : f.cle_presente ? <Pastille ton="succes">Présente</Pastille> : <Pastille ton="alerte">Absente</Pastille>}</td>
                    <td><code>{f.modele_suggere}</code></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {c && (
        <form className="panneau" onSubmit={(e) => {
          e.preventDefault();
          setEnregistre(false);
          action.lancer(async () => {
            await api("/config-ia", { methode: "PUT", corps: { fournisseur, modele } });
            setEnregistre(true);
            recharger();
          });
        }}>
          <div className="panneau-entete"><h2>IA active</h2></div>
          <div className="panneau-corps pile">
            <div className="rangee" style={{ alignItems: "flex-start" }}>
              <div className="champ" style={{ flex: 1, minWidth: 200 }}>
                <label htmlFor="fournisseur">Fournisseur</label>
                <select id="fournisseur" value={fournisseur} required onChange={(e) => {
                  setFournisseur(e.target.value);
                  const f = c.fournisseurs.find((x) => x.code === e.target.value);
                  if (f) setModele(f.modele_suggere);
                }}>
                  <option value="" disabled>Choisir…</option>
                  {c.fournisseurs.map((f) => (
                    <option key={f.code} value={f.code} disabled={f.cle_requise && !f.cle_presente}>
                      {f.libelle}{f.cle_requise && !f.cle_presente ? " (clé absente)" : ""}
                    </option>
                  ))}
                </select>
              </div>
              <div className="champ" style={{ flex: 1, minWidth: 200 }}>
                <label htmlFor="modele">Modèle</label>
                <input id="modele" type="text" required value={modele} onChange={(e) => setModele(e.target.value)} />
                <span className="aide">Le nom exact du modèle, tel que l'indique la documentation du fournisseur.</span>
              </div>
            </div>
            {choix?.code === "ollama" && (
              <div className="message-info">Avec Ollama, les exigences ne quittent pas votre poste. Ollama doit être lancé et le modèle téléchargé.</div>
            )}
            <MessageErreur erreur={action.erreur} />
            <div className="rangee">
              <button className="bouton principal" disabled={action.enCours || !fournisseur || !modele.trim()}>Enregistrer</button>
              {enregistre && <span className="discret-texte" role="status">IA enregistrée. Les prochaines analyses l'utiliseront.</span>}
            </div>
          </div>
        </form>
      )}
    </div>
  );
}
