import { useRef, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, type ConfigIA, type ResumeMission } from "../api";
import { MessageErreur, useAction, useDonnees } from "../composants";
import { useSession } from "../session";

const EXEMPLE = `US-042 — Réinitialisation du mot de passe
En tant qu'utilisateur, je veux réinitialiser mon mot de passe facilement depuis la page de connexion.
Le système envoie un e-mail contenant un lien de réinitialisation valide pendant une durée limitée.
Le nouveau mot de passe doit être sécurisé et différent de l'ancien.
En cas de succès, l'utilisateur est redirigé vers la page de connexion et éventuellement notifié.`;

const FORMATS = ".txt,.md,.docx,.pdf";

export default function Analyse() {
  const navigate = useNavigate();
  const [titre, setTitre] = useState("");
  const [texte, setTexte] = useState("");
  const [fichier, setFichier] = useState<File | null>(null);
  const [survol, setSurvol] = useState(false);
  const champFichier = useRef<HTMLInputElement>(null);
  const { enCours, erreur, lancer } = useAction();
  const config = useDonnees<ConfigIA>("/config-ia");
  const { a } = useSession();
  const sansIA = config.donnees !== null && config.donnees.actif === null;

  const choisir = (f: File | undefined) => {
    if (!f) return;
    setFichier(f);
    if (!titre) setTitre(f.name.replace(/\.[^.]+$/, ""));
  };

  const envoyer = (ev: FormEvent) => {
    ev.preventDefault();
    lancer(async () => {
      let r: { mission: ResumeMission };
      if (fichier) {
        const f = new FormData();
        f.append("titre", titre);
        f.append("fichier", fichier);
        r = await api("/missions/fichier", { methode: "POST", formulaire: f });
      } else {
        r = await api("/missions", { methode: "POST", corps: { titre, texte } });
      }
      navigate("/missions/" + r.mission.id);
    });
  };

  return (
    <form className="pile" onSubmit={envoyer} style={{ maxWidth: 1120 }}>
      <div>
        <div className="surtitre">AG-01 · Exigences</div>
        <h1>Analyse des exigences</h1>
      </div>

      {sansIA && (
        <div className="message-erreur" role="alert">
          Aucune IA n'est encore configurée : l'analyse ne peut pas démarrer.{" "}
          {a("ADMIN")
            ? <Link to="/configuration">Choisir l'IA dans Configuration IA</Link>
            : "Demandez à un administrateur de la choisir dans Configuration IA."}
        </div>
      )}

      <section className="panneau-exigence" aria-labelledby="titre-exigence">
        <h2 id="titre-exigence">Exigence à analyser</h2>
        <p className="discret-texte" style={{ marginTop: 4 }}>
          SFD / User Story — deux façons de saisir : déposez un fichier ou collez le texte.
          L'agent AG-01 relève les défauts et prépare les questions métier.
        </p>

        <div className="champ" style={{ marginTop: 16 }}>
          <label htmlFor="titre" className="etiquette-bleue">Titre de la mission</label>
          <input id="titre" type="text" required value={titre} onChange={(e) => setTitre(e.target.value)}
                 placeholder="Ex. Réinitialisation du mot de passe" />
        </div>

        <div
          className={"depot-exigence" + (survol ? " survol" : "") + (fichier ? " rempli" : "")}
          role="button" tabIndex={0} aria-label="Déposer ou choisir un fichier d'exigence"
          onClick={() => champFichier.current?.click()}
          onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && champFichier.current?.click()}
          onDragOver={(e) => { e.preventDefault(); setSurvol(true); }}
          onDragLeave={() => setSurvol(false)}
          onDrop={(e) => { e.preventDefault(); setSurvol(false); choisir(e.dataTransfer.files[0]); }}
        >
          <svg width="22" height="22" viewBox="0 0 24 24" aria-hidden="true">
            <path d="M12 15V4M7.5 8.5 12 4l4.5 4.5M5 14v4a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-4" fill="none" stroke="currentColor"
                  strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          {fichier
            ? <><div><strong>{fichier.name}</strong> · {(fichier.size / 1024).toFixed(0)} Ko</div>
                <button type="button" className="bouton petit"
                        onClick={(e) => { e.stopPropagation(); setFichier(null); }}>Retirer le fichier</button></>
            : <><div>Glissez-déposez votre SFD ici, ou cliquez pour parcourir</div>
                <div className="depot-formats">.txt · .md · .docx · .pdf — 10 Mo max</div></>}
          <input ref={champFichier} type="file" accept={FORMATS} hidden
                 onChange={(e) => choisir(e.target.files?.[0])} />
        </div>

        {!fichier && (
          <div className="champ" style={{ marginTop: 16 }}>
            <label htmlFor="texte" className="etiquette-bleue">Zone de saisie du texte</label>
            <textarea id="texte" className="saisie-exigence" rows={9} value={texte}
                      onChange={(e) => setTexte(e.target.value)} required={!fichier}
                      placeholder="Collez ici le texte de la SFD ou de la User Story…" />
          </div>
        )}

        <MessageErreur erreur={erreur} />
        <div className="rangee" style={{ marginTop: 16 }}>
          <button className="bouton principal" disabled={enCours || sansIA || !titre.trim() || (!fichier && !texte.trim())}>
            {enCours ? "Envoi…" : "Analyser l'exigence"}
          </button>
          {!fichier && (
            <button type="button" className="bouton"
                    onClick={() => { setTexte(EXEMPLE); if (!titre) setTitre("Réinitialisation du mot de passe"); }}>
              Charger l'exemple
            </button>
          )}
        </div>
      </section>
    </form>
  );
}
