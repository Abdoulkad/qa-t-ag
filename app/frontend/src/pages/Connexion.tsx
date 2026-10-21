import { useEffect, useState, type FormEvent } from "react";
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
  const [voir, setVoir] = useState(false);
  const { enCours, erreur, lancer } = useAction();
  // RA-51 : après le premier compte, seul un administrateur crée les comptes
  const [inscriptionOuverte, setInscriptionOuverte] = useState(false);
  useEffect(() => {
    api<{ inscription_ouverte: boolean }>("/auth/etat")
      .then((e) => setInscriptionOuverte(e.inscription_ouverte))
      .catch(() => setInscriptionOuverte(false));
  }, []);

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
        <form className="connexion-cadre" onSubmit={envoyer} aria-labelledby="titre-connexion">
          <div className="connexion-surtitre">{mode === "connexion" ? "Bon retour" : "Bienvenue"}</div>
          <h2 id="titre-connexion" className="titre-mono">
            {mode === "connexion" ? "Content de vous revoir" : "Créer votre compte"}
          </h2>
          <p className="discret-texte" style={{ fontSize: "0.92rem" }}>
            {mode === "connexion"
              ? "Retrouvez vos missions, vos validations et vos exports de cas de test."
              : "Quelques secondes suffisent : nom, e-mail et mot de passe."}
          </p>

          {inscriptionOuverte && (
            <div className="bascule" role="group" aria-label="Choisir une action">
              <button type="button" aria-pressed={mode === "connexion"} onClick={() => setMode("connexion")}>Se connecter</button>
              <button type="button" aria-pressed={mode === "inscription"} onClick={() => setMode("inscription")}>Créer un compte</button>
            </div>
          )}

          {mode === "inscription" && (
            <div className="champ">
              <label htmlFor="nom">Nom</label>
              <input id="nom" type="text" value={nom} onChange={(e) => setNom(e.target.value)} autoComplete="name"
                     placeholder="Prénom Nom" />
            </div>
          )}
          <div className="champ">
            <label htmlFor="email">E-mail</label>
            <input id="email" type="email" required value={email} autoComplete="email"
                   onChange={(e) => setEmail(e.target.value)} placeholder="prenom.nom@entreprise.ci" />
          </div>
          <div className="champ">
            <label htmlFor="mdp">Mot de passe</label>
            <div className="champ-mdp">
              <input id="mdp" type={voir ? "text" : "password"} required
                     minLength={mode === "inscription" ? 8 : undefined}
                     value={motDePasse} onChange={(e) => setMotDePasse(e.target.value)}
                     placeholder="Votre mot de passe"
                     autoComplete={mode === "connexion" ? "current-password" : "new-password"} />
              <button type="button" className="oeil" onClick={() => setVoir(!voir)}
                      aria-label={voir ? "Masquer le mot de passe" : "Afficher le mot de passe"} aria-pressed={voir}>
                <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12Z" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round" />
                  <circle cx="12" cy="12" r="3" fill="none" stroke="currentColor" strokeWidth="1.7" />
                  {voir && <path d="M4 4 20 20" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />}
                </svg>
              </button>
            </div>
            {mode === "inscription" && <span className="aide">8 caractères minimum.</span>}
          </div>
          <MessageErreur erreur={erreur} />
          <button className="bouton principal connexion-valider" disabled={enCours}>
            {enCours ? "Un instant…" : mode === "connexion" ? "Accéder à mes missions" : "Créer mon compte"}
            <svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" /></svg>
          </button>
          <p className="connexion-note">
            {mode === "connexion"
              ? "Vos missions sont conservées sur le serveur QA-T-AG de votre organisation, et restent visibles depuis n'importe quel navigateur."
              : "Le premier compte de l'installation reçoit tous les rôles. Les suivants sont Analyste QA ; un administrateur peut les promouvoir."}
          </p>
        </form>
        {inscriptionOuverte ? (
          <p className="connexion-pied">
            {mode === "connexion" ? "Pas encore de compte ? " : "Déjà un compte ? "}
            <button type="button" className="lien" onClick={() => setMode(mode === "connexion" ? "inscription" : "connexion")}>
              {mode === "connexion" ? "Créez-en un en une minute" : "Se connecter"}
            </button>
          </p>
        ) : (
          <p className="connexion-pied">Pas encore de compte ? Demandez-le à un administrateur QA-T-AG.</p>
        )}
      </section>
    </div>
  );
}
