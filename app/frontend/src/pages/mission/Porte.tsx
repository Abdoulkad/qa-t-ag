import { useState } from "react";
import { api, type Mission } from "../../api";
import { MessageErreur, useAction } from "../../composants";
import { useSession } from "../../session";

const QUOI = {
  "PV-1": "Validez la User Story réécrite, ses règles métier et ses critères d'acceptation. L'agent concevra ensuite les cas de test à partir de cette version.",
  "PV-2": "Validez les cas de test. Une fois validés, ils ne sont plus modifiables et la recette peut commencer.",
};

export default function Porte({ mission: m, recharger }: {
  mission: Mission; recharger: () => void; lancerTache: (id: number) => void;
}) {
  const { moi } = useSession();
  const porte = m.porte_en_attente!;
  const [commentaire, setCommentaire] = useState("");
  const action = useAction();
  const courante = m.versions[m.versions.length - 1];
  const seul = m.participants.length === 1;
  const auteur = courante.auteur_id === moi?.id;
  const superviseur = !!moi?.roles.includes("SUPERVISEUR");
  // Reflet des règles RA-12 / RA-13 : le serveur reste juge
  const peutDecider = seul ? m.participants[0].id === moi?.id : superviseur && !auteur;

  const decider = (decision: "APPROUVE" | "REJETE") => action.lancer(async () => {
    await api(`/missions/${m.id}/portes/${porte}`, { methode: "POST", corps: { decision, commentaire } });
    setCommentaire("");
    recharger();
  });

  return (
    <section className="porte-panneau" aria-labelledby="titre-porte">
      <div className="panneau-entete">
        <h2 id="titre-porte">Human Gate {porte}</h2>
      </div>
      <div className="panneau-corps pile">
        <p>{QUOI[porte]}</p>
        {m.bloquants_porte.length > 0 && (
          <div>
            <div className="etiquette" style={{ marginBottom: 4 }}>
              À traiter avant de pouvoir approuver ({m.bloquants_porte.length})
            </div>
            <ul className="bloquants">{m.bloquants_porte.map((b) => <li key={b}>{b}</li>)}</ul>
          </div>
        )}
        {porte === "PV-1" && (courante.points_ouverts.length > 0 || courante.questions.some((q) => q.decision)
          || courante.couverture.some((p) => p.statut === "JUSTIFIEE")) && (
          <div className="message-info">
            <strong>À savoir avant de décider</strong>
            {courante.points_ouverts.length > 0 && (
              <div>{courante.points_ouverts.length} point(s) ouvert(s), non couvert(s) par les critères.</div>
            )}
            {courante.couverture.filter((p) => p.statut === "JUSTIFIEE").map((p) => (
              <div key={"ph" + p.id}>Phrase {p.numero} non reprise — « {p.motif} »</div>
            ))}
            {courante.questions.filter((q) => q.decision).map((q) => (
              <div key={q.id}>{q.code} : {q.decision === "HORS_PERIMETRE" ? "hors périmètre" : "reportée"} — « {q.motif_decision} »</div>
            ))}
          </div>
        )}
        {!peutDecider && (
          <div className="message-info">
            {seul ? "Seul le participant de la mission peut décider."
              : auteur ? "Vous êtes l'auteur de cette version : un autre Superviseur doit décider."
              : "Il faut le rôle Superviseur pour décider à ce Human Gate."}
          </div>
        )}
        <div className="champ">
          <label htmlFor="commentaire">Commentaire</label>
          <textarea id="commentaire" rows={3} value={commentaire} onChange={(e) => setCommentaire(e.target.value)}
                    placeholder="Obligatoire pour un rejet : dites ce qu'il faut corriger." />
        </div>
        {seul && peutDecider && (
          <p className="discret-texte">Vous êtes seul sur la mission : votre décision sera tracée comme une auto-validation.</p>
        )}
        <MessageErreur erreur={action.erreur} />
        <div className="rangee">
          <button className="bouton approuver" disabled={action.enCours || !peutDecider || m.bloquants_porte.length > 0}
                  onClick={() => decider("APPROUVE")}>Approuver {porte}</button>
          <button className="bouton rejeter" disabled={action.enCours || !peutDecider || !commentaire.trim()}
                  onClick={() => decider("REJETE")}>Rejeter</button>
        </div>
      </div>
    </section>
  );
}
