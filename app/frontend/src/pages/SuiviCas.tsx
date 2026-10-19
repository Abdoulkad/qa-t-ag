import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import type { Cas, ResumeMission } from "../api";
import { MessageErreur, PastilleCas, useDonnees } from "../composants";
import { STATUT_CAS } from "../libelles";

interface Reponse {
  total: number;
  par_statut: Record<string, number>;
  cas: (Cas & { mission: { id: number; reference: string; titre: string } })[];
}

export default function SuiviCas() {
  const [q, setQ] = useState("");
  const [qDiffere, setQDiffere] = useState("");
  const [mission, setMission] = useState("");
  const [statut, setStatut] = useState("");
  useEffect(() => {
    const t = setTimeout(() => setQDiffere(q), 300);
    return () => clearTimeout(t);
  }, [q]);

  const params = new URLSearchParams();
  if (qDiffere.trim()) params.set("q", qDiffere.trim());
  if (mission) params.set("mission_id", mission);
  if (statut) params.set("statut", statut);
  const { donnees, erreur } = useDonnees<Reponse>("/cas?" + params.toString());
  const missions = useDonnees<ResumeMission[]>("/missions");

  // Regroupement par mission, dans l'ordre reçu
  const groupes: { id: number; reference: string; titre: string; cas: Reponse["cas"] }[] = [];
  for (const c of donnees?.cas ?? []) {
    let g = groupes.find((x) => x.id === c.mission.id);
    if (!g) groupes.push(g = { ...c.mission, cas: [] });
    g.cas.push(c);
  }

  return (
    <div className="pile">
      <div className="entete-page">
        <div>
          <h1>Suivi des cas</h1>
          <p>Les cas de test de la version courante de chaque mission.</p>
        </div>
      </div>

      {donnees && (
        <section className="indicateurs" aria-label="Répartition des cas">
          <div className="indicateur"><div className="indicateur-valeur">{donnees.total}</div><div className="indicateur-libelle">Cas affichés</div></div>
          <div className="indicateur"><div className="indicateur-valeur" style={{ color: "var(--succes)" }}>{donnees.par_statut.PRET}</div><div className="indicateur-libelle">Prêts</div></div>
          <div className="indicateur"><div className="indicateur-valeur" style={{ color: "var(--alerte)" }}>{donnees.par_statut.INCOMPLET}</div><div className="indicateur-libelle">Incomplets</div></div>
          <div className="indicateur"><div className="indicateur-valeur" style={{ color: "var(--attente)" }}>{donnees.par_statut.A_CLARIFIER}</div><div className="indicateur-libelle">À clarifier</div></div>
        </section>
      )}

      <section className="panneau">
        <div className="panneau-corps rangee" style={{ alignItems: "flex-end" }}>
          <div className="champ" style={{ flex: 2, minWidth: 220 }}>
            <label htmlFor="q">Rechercher</label>
            <input id="q" type="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Code, titre ou exigence" />
          </div>
          <div className="champ" style={{ flex: 1, minWidth: 180 }}>
            <label htmlFor="mission">Mission</label>
            <select id="mission" value={mission} onChange={(e) => setMission(e.target.value)}>
              <option value="">Toutes les missions</option>
              {(missions.donnees ?? []).map((m) => <option key={m.id} value={m.id}>{m.reference} — {m.titre}</option>)}
            </select>
          </div>
          <div className="champ" style={{ flex: 1, minWidth: 150 }}>
            <label htmlFor="statut">Statut</label>
            <select id="statut" value={statut} onChange={(e) => setStatut(e.target.value)}>
              <option value="">Tous les statuts</option>
              {Object.entries(STATUT_CAS).map(([k, v]) => <option key={k} value={k}>{v.libelle}</option>)}
            </select>
          </div>
        </div>
      </section>

      <MessageErreur erreur={erreur} />
      {donnees && donnees.total === 0 && (
        <div className="panneau vide">Aucun cas ne correspond. Les cas apparaissent après l'approbation de PV-1.</div>
      )}

      {groupes.map((g) => (
        <section key={g.id} className="panneau">
          <div className="panneau-entete">
            <h2><Link to={"/missions/" + g.id} style={{ color: "inherit", textDecoration: "none" }}>
              <span className="ref">{g.reference}</span> {g.titre}</Link></h2>
            <span className="discret-texte">{g.cas.length} cas</span>
          </div>
          <div className="table-defile">
            <table>
              <thead><tr><th>Cas</th><th>Couvre</th><th>Technique</th><th>Statut</th></tr></thead>
              <tbody>
                {g.cas.map((c) => (
                  <tr key={c.id}>
                    <td><span className="ref">{c.code}</span> {c.titre}
                      {c.motif_statut && <div className="sous">{c.motif_statut}</div>}</td>
                    <td>{c.references.join(", ")}</td>
                    <td>{c.technique}</td>
                    <td><PastilleCas statut={c.statut} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ))}
    </div>
  );
}
