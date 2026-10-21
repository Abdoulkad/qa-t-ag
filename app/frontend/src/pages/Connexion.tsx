import { useState, type FormEvent } from "react";
import { api } from "../api";
import { MessageErreur, useAction } from "../composants";
import { Marque } from "../Logo";
import { useSession } from "../session";

export default function Connexion() {
  const { connecter } = useSession();
  const [mode, setMode] = useState<"connexion" | "inscription">("connexion");
  const [email, setEmail] = useState("");
  const [nom, setNom] = useState("");
  const [motDePasse, setMotDePasse] = useState("");
  const { enCours, erreur, lancer } = useAction();

  const envoyer = (ev: FormEvent) => {
    ev.preventDefault();
    lancer(async () => {
      if (mode === "inscription") {
        await api("/auth/inscription", {
          methode: "POST", corps: { email, nom, mot_de_passe: motDePasse },
        });
      }
      await connecter(email, motDePasse);
    });
  };

  return (
    <div className="connexion">
      <section className="connexion-recit">
        <div className="marque"><Marque /></div>
        <h1>L'agent prépare vos tests. Vous décidez.</h1>
        <p>
          QA-T-AG relit vos exigences, conçoit les cas de test et en garde la trace.
          Aucune étape ne passe sans votre validation aux Human Gates.
        </p>
        <ol className="connexion-etapes">
          <li><div><strong>Déposez une exigence</strong>
            <p>SFD ou User Story : l'agent relève les ambiguïtés et pose les questions métier.</p></div></li>
          <li><div><strong>Clarifiez, puis validez la réécriture</strong>
            <p>Chaque critère d'acceptation cite sa source. Rien n'est inventé sans que vous le voyiez.</p></div></li>
          <li><div><strong>Validez les cas, menez la recette</strong>
            <p>Les cas incomplets bloquent la validation. Le cahier Word sort de la base, pas d'une copie.</p></div></li>
        </ol>
      </section>
      <section className="connexion-formulaire">
        <form className="connexion-carte" onSubmit={envoyer}>
          <h2>{mode === "connexion" ? "Se connecter" : "Créer un compte"}</h2>
          {mode === "inscription" && (
            <div className="champ">
              <label htmlFor="nom">Nom</label>
              <input id="nom" type="text" value={nom} onChange={(e) => setNom(e.target.value)} autoComplete="name" />
            </div>
          )}
          <div className="champ">
            <label htmlFor="email">E-mail</label>
            <input id="email" type="email" required value={email} autoComplete="email"
                   onChange={(e) => setEmail(e.target.value)} placeholder="prenom.nom@entreprise.ci" />
          </div>
          <div className="champ">
            <label htmlFor="mdp">Mot de passe</label>
            <input id="mdp" type="password" required minLength={mode === "inscription" ? 8 : undefined}
                   value={motDePasse} onChange={(e) => setMotDePasse(e.target.value)}
                   autoComplete={mode === "connexion" ? "current-password" : "new-password"} />
            {mode === "inscription" && <span className="aide">8 caractères minimum.</span>}
          </div>
          <MessageErreur erreur={erreur} />
          <button className="bouton principal" disabled={enCours}>
            {mode === "connexion" ? "Se connecter" : "Créer mon compte"}
          </button>
          <p className="discret-texte">
            {mode === "connexion" ? "Pas encore de compte ? " : "Déjà un compte ? "}
            <button type="button" className="bouton discret petit"
                    onClick={() => setMode(mode === "connexion" ? "inscription" : "connexion")}>
              {mode === "connexion" ? "Créer un compte" : "Se connecter"}
            </button>
          </p>
          {mode === "inscription" && (
            <p className="discret-texte">
              Le premier compte de l'installation reçoit tous les rôles. Les suivants sont
              Analyste QA ; un administrateur peut les promouvoir.
            </p>
          )}
        </form>
      </section>
    </div>
  );
}
