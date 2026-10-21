import { useState, type FormEvent } from "react";
import { MessageErreur, useAction } from "../composants";
import { Marque } from "../Logo";
import { useSession } from "../session";

/** RA-55 / RA-56 : changement du mot de passe. `impose` : écran plein, sans
 *  navigation, tant que le mot de passe provisoire n'est pas remplacé. */
export default function MotDePasse({ impose = false }: { impose?: boolean }) {
  const { moi, changerMotDePasse, deconnecter } = useSession();
  const [actuel, setActuel] = useState("");
  const [nouveau, setNouveau] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [fait, setFait] = useState(false);
  const { enCours, erreur, lancer } = useAction();
  const different = confirmation !== "" && confirmation !== nouveau;

  const envoyer = (ev: FormEvent) => {
    ev.preventDefault();
    if (nouveau !== confirmation) return;
    lancer(async () => {
      await changerMotDePasse(actuel, nouveau);
      setActuel(""); setNouveau(""); setConfirmation("");
      setFait(true);
    });
  };

  const formulaire = (
    <form className={impose ? "connexion-cadre" : "panneau-corps pile"} onSubmit={envoyer}
          aria-labelledby="titre-mdp" style={impose ? undefined : { maxWidth: 460 }}>
      {impose && <>
        <div className="connexion-surtitre">Première connexion</div>
        <h2 id="titre-mdp" className="titre-mono">Choisissez votre mot de passe</h2>
        <p className="discret-texte" style={{ fontSize: "0.92rem" }}>
          Le mot de passe que vous avez reçu est provisoire. Remplacez-le par un mot de passe
          connu de vous seul : vos validations aux Human Gates sont signées à votre nom.
        </p>
      </>}
      <div className="champ">
        <label htmlFor="mdp-actuel">{impose ? "Mot de passe provisoire" : "Mot de passe actuel"}</label>
        <input id="mdp-actuel" type="password" required value={actuel} autoComplete="current-password"
               onChange={(e) => setActuel(e.target.value)} />
      </div>
      <div className="champ">
        <label htmlFor="mdp-nouveau">Nouveau mot de passe</label>
        <input id="mdp-nouveau" type="password" required minLength={8} value={nouveau}
               autoComplete="new-password" onChange={(e) => setNouveau(e.target.value)} />
        <span className="aide">8 caractères minimum, différent de l'actuel.</span>
      </div>
      <div className="champ">
        <label htmlFor="mdp-confirmation">Confirmer le nouveau mot de passe</label>
        <input id="mdp-confirmation" type="password" required value={confirmation}
               autoComplete="new-password" aria-invalid={different}
               onChange={(e) => setConfirmation(e.target.value)} />
        {different && <span className="aide" style={{ color: "var(--alerte)" }}>Les deux saisies diffèrent.</span>}
      </div>
      <MessageErreur erreur={erreur} />
      {fait && !impose && (
        <div className="message-info" role="status">
          Mot de passe changé. Vos sessions ouvertes sur d'autres postes sont fermées.
        </div>
      )}
      <div>
        <button className={"bouton principal" + (impose ? " connexion-valider" : "")}
                disabled={enCours || different}>
          {enCours ? "Un instant…" : "Enregistrer le mot de passe"}
        </button>
      </div>
      {impose && (
        <p className="connexion-note">
          Connecté en tant que {moi?.email}.{" "}
          <button type="button" className="lien" onClick={deconnecter}>Se déconnecter</button>
        </p>
      )}
    </form>
  );

  if (impose) {
    return (
      <div className="connexion-formulaire" style={{ minHeight: "100vh" }}>
        <div className="marque"><Marque /></div>
        {formulaire}
      </div>
    );
  }
  return (
    <div className="pile">
      <div className="entete-page">
        <div>
          <h1 id="titre-mdp">Mot de passe</h1>
          <p>Après le changement, vos sessions ouvertes sur d'autres postes sont fermées.</p>
        </div>
      </div>
      <section className="panneau">{formulaire}</section>
    </div>
  );
}
