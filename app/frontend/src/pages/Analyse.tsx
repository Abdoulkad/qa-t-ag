import { useRef, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { api, type ResumeMission } from "../api";
import { MessageErreur, useAction } from "../composants";

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
    <form className="pile" onSubmit={envoyer} style={{ maxWidth: 860 }}>
      <div className="entete-page">
        <div>
          <h1>Analyser une exigence</h1>
          <p>Déposez une SFD ou une User Story. L'agent AG-01 relève les défauts et prépare les questions métier.</p>
        </div>
      </div>

      <section className="panneau">
        <div className="panneau-corps pile">
          <div className="champ">
            <label htmlFor="titre">Titre de la mission</label>
            <input id="titre" type="text" required value={titre} onChange={(e) => setTitre(e.target.value)}
                   placeholder="Ex. Réinitialisation du mot de passe" />
          </div>

          <div
            className={"depot" + (survol ? " survol" : "")}
            role="button" tabIndex={0}
            onClick={() => champFichier.current?.click()}
            onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && champFichier.current?.click()}
            onDragOver={(e) => { e.preventDefault(); setSurvol(true); }}
            onDragLeave={() => setSurvol(false)}
            onDrop={(e) => { e.preventDefault(); setSurvol(false); choisir(e.dataTransfer.files[0]); }}
          >
            {fichier
              ? <><strong>{fichier.name}</strong> · {(fichier.size / 1024).toFixed(0)} Ko
                  <div style={{ marginTop: 8 }}>
                    <button type="button" className="bouton petit"
                            onClick={(e) => { e.stopPropagation(); setFichier(null); }}>Retirer le fichier</button>
                  </div></>
              : <><strong>Glissez votre fichier ici</strong> ou cliquez pour le choisir
                  <div className="discret-texte">.txt, .md, .docx ou .pdf — 10 Mo maximum</div></>}
            <input ref={champFichier} type="file" accept={FORMATS} hidden
                   onChange={(e) => choisir(e.target.files?.[0])} />
          </div>

          {!fichier && (
            <div className="champ">
              <label htmlFor="texte">Ou collez le texte de l'exigence</label>
              <textarea id="texte" rows={10} value={texte} onChange={(e) => setTexte(e.target.value)}
                        required={!fichier} />
            </div>
          )}

          <MessageErreur erreur={erreur} />
          <div className="rangee">
            <button className="bouton principal" disabled={enCours || !titre.trim() || (!fichier && !texte.trim())}>
              {enCours ? "Envoi…" : "Lancer l'analyse"}
            </button>
            {!fichier && (
              <button type="button" className="bouton"
                      onClick={() => { setTexte(EXEMPLE); if (!titre) setTitre("Réinitialisation du mot de passe"); }}>
                Charger l'exemple
              </button>
            )}
          </div>
        </div>
      </section>
    </form>
  );
}
