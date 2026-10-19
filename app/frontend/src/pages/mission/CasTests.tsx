import { useState } from "react";
import { api, type Cas, type Mission } from "../../api";
import { MessageErreur, PastilleCas, useAction, useDonnees, Volet } from "../../composants";

const TECHNIQUES = ["partitions d'équivalence", "valeurs limites", "table de décision", "transitions d'état"];

export default function CasTests({ mission: m, historique, recharger }: {
  mission: Mission; historique: boolean; recharger: () => void;
}) {
  const { donnees, erreur, recharger: relire } = useDonnees<Cas[]>(`/missions/${m.id}/cas`);
  const [ouvert, setOuvert] = useState<Cas | null>(null);
  const modifiable = !historique && m.statut === "ATTENTE_PV2";

  if (erreur) return <div className="panneau-corps"><MessageErreur erreur={erreur} /></div>;
  if (!donnees) return <div className="charge">Chargement…</div>;
  if (!donnees.length) {
    return (
      <div className="vide">
        <strong>Pas encore de cas de test</strong>
        L'agent les concevra dès que PV-1 sera approuvé.
      </div>
    );
  }
  const compte = (s: string) => donnees.filter((c) => c.statut === s).length;
  return (
    <>
      <div className="panneau-corps rangee" style={{ gap: 16 }}>
        <span><strong>{donnees.length}</strong> cas</span>
        <span><strong style={{ color: "var(--succes)" }}>{compte("PRET")}</strong> prêts</span>
        <span><strong style={{ color: "var(--alerte)" }}>{compte("INCOMPLET")}</strong> incomplets</span>
        <span><strong style={{ color: "var(--attente)" }}>{compte("A_CLARIFIER")}</strong> à clarifier</span>
        {modifiable && compte("PRET") < donnees.length && (
          <span className="discret-texte">Ouvrez un cas pour le compléter : son statut est recalculé à l'enregistrement.</span>
        )}
      </div>
      <div className="table-defile">
        <table>
          <thead>
            <tr><th>Cas</th><th>Couvre</th><th>Technique</th><th>Priorité</th><th>Statut</th></tr>
          </thead>
          <tbody>
            {donnees.map((c) => (
              <tr key={c.id} className="cliquable" onClick={() => setOuvert(c)}>
                <td>
                  <span className="ref">{c.code}</span> {c.titre}
                  {c.motif_statut && <div className="sous">{c.motif_statut}</div>}
                </td>
                <td>{c.references.map((r) => <span key={r} className="ref" style={{ marginRight: 6 }}>{r}</span>)}</td>
                <td>{c.technique}</td>
                <td>{c.priorite}</td>
                <td><PastilleCas statut={c.statut} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {ouvert && (
        <EditionCas cas={ouvert} missionId={m.id} modifiable={modifiable} fermer={() => setOuvert(null)}
                    apres={(c) => { setOuvert(c); relire(); recharger(); }} />
      )}
    </>
  );
}

const CHAMPS: [keyof Cas, string, number][] = [
  ["titre", "Titre", 1], ["objectif", "Objectif", 2], ["exigence", "Exigences couvertes (CA-xx, REQ-xxx)", 1],
  ["preconditions", "Préconditions", 2], ["donnees_test", "Données de test", 2], ["etapes", "Étapes", 4],
  ["resultat_attendu", "Résultat attendu", 2], ["justification_technique", "Justification de la technique", 2],
];

function EditionCas({ cas, missionId, modifiable, fermer, apres }: {
  cas: Cas; missionId: number; modifiable: boolean; fermer: () => void; apres: (c: Cas) => void;
}) {
  const [valeurs, setValeurs] = useState<Record<string, string>>(() =>
    Object.fromEntries([...CHAMPS.map(([k]) => [k, String(cas[k] ?? "")]),
      ["technique", cas.technique], ["priorite", cas.priorite], ["type", cas.type]]));
  const action = useAction();
  const enregistrer = (confirmer: boolean) => action.lancer(async () => {
    const c = await api<Cas>(`/missions/${missionId}/cas/${cas.id}`,
      { methode: "PATCH", corps: { ...valeurs, confirmer } });
    apres(c);
  });
  const champ = (k: string, libelle: string, lignes: number) => (
    <div className="champ" key={k}>
      <label htmlFor={"cas-" + k}>{libelle}</label>
      {modifiable
        ? lignes === 1
          ? <input id={"cas-" + k} type="text" value={valeurs[k]} onChange={(e) => setValeurs({ ...valeurs, [k]: e.target.value })} />
          : <textarea id={"cas-" + k} rows={lignes} value={valeurs[k]} onChange={(e) => setValeurs({ ...valeurs, [k]: e.target.value })} />
        : <div style={{ whiteSpace: "pre-wrap" }}>{valeurs[k] || <span className="discret-texte">Non renseigné</span>}</div>}
    </div>
  );
  return (
    <Volet titre={<><span className="ref">{cas.code}</span> {cas.titre}</>}
           sousTitre={<PastilleCas statut={cas.statut} />} fermer={fermer}
           pied={modifiable ? <>
             <MessageErreur erreur={action.erreur} />
             {cas.statut === "A_CLARIFIER" && (
               <button className="bouton" disabled={action.enCours} onClick={() => enregistrer(true)}
                       title="Vous confirmez que le point signalé par l'agent est résolu">
                 Enregistrer et confirmer le cas
               </button>
             )}
             <button className="bouton principal" disabled={action.enCours} onClick={() => enregistrer(false)}>Enregistrer</button>
           </> : undefined}>
      {cas.motif_statut && <div className={cas.statut === "PRET" ? "message-info" : "message-erreur"}>{cas.motif_statut}</div>}
      {!modifiable && <p className="discret-texte">Les cas se modifient uniquement en attente de PV-2.</p>}
      {CHAMPS.slice(0, 3).map(([k, l, n]) => champ(k, l, n))}
      <div className="rangee" style={{ alignItems: "flex-start" }}>
        <div className="champ" style={{ flex: 1, minWidth: 160 }}>
          <label htmlFor="cas-technique">Technique</label>
          {modifiable
            ? <select id="cas-technique" value={valeurs.technique} onChange={(e) => setValeurs({ ...valeurs, technique: e.target.value })}>
                {TECHNIQUES.map((t) => <option key={t}>{t}</option>)}
              </select>
            : <div>{valeurs.technique}</div>}
        </div>
        <div className="champ" style={{ flex: 1, minWidth: 120 }}>
          <label htmlFor="cas-priorite">Priorité</label>
          {modifiable
            ? <select id="cas-priorite" value={valeurs.priorite} onChange={(e) => setValeurs({ ...valeurs, priorite: e.target.value })}>
                {["Critique", "Haute", "Moyenne"].map((t) => <option key={t}>{t}</option>)}
              </select>
            : <div>{valeurs.priorite}</div>}
        </div>
      </div>
      {CHAMPS.slice(3).map(([k, l, n]) => champ(k, l, n))}
      {modifiable && <p className="discret-texte">
        Données de test : des valeurs exactes. « Mot de passe valide » ne suffit pas ; écrivez « Sans objet » si le cas n'en demande pas.
      </p>}
    </Volet>
  );
}
