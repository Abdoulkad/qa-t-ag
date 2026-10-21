import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import type { Cas, ResumeMission } from "../api";
import { MessageErreur, Pastille, PastilleCas, useDonnees } from "../composants";
import { STATUT_CAS } from "../libelles";

interface Reponse {
  total: number;
  par_statut: Record<string, number>;
  executes: number;
  non_executes: number;
  cas: (Cas & { execution: string | null; mission: { id: number; reference: string; titre: string } })[];
}

const EXECUTION: Record<string, { libelle: string; ton: "succes" | "alerte" | "attente" | "neutre" }> = {
  PASS: { libelle: "Réussi", ton: "succes" },
  FAIL: { libelle: "Échoué", ton: "alerte" },
  BLOCKED: { libelle: "Bloqué", ton: "attente" },
  NOT_RUN: { libelle: "Non exécuté", ton: "neutre" },
};

const trait = { fill: "none", stroke: "currentColor", strokeWidth: 1.8, strokeLinecap: "round" as const, strokeLinejoin: "round" as const };

function Kpi({ ton, libelle, valeur, aide }: { ton: string; libelle: string; valeur: number | string; aide: string }) {
  return (
    <div className={"carte-kpi " + ton} title={aide}>
      <div className="carte-kpi-libelle">{libelle}</div>
      <div className="carte-kpi-valeur">{valeur}</div>
    </div>
  );
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
  const { donnees, erreur, recharger, chargement } = useDonnees<Reponse>("/cas?" + params.toString());
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
      <div className="entete-page" style={{ marginBottom: 0 }}>
        <h1 className="titre-icone">
          <svg width="24" height="24" viewBox="0 0 24 24" aria-hidden="true">
            <rect x="5" y="4" width="14" height="17" rx="2" {...trait} />
            <path d="M9 4V3h6v1M9 10h6M9 14h6M9 18h3" {...trait} />
          </svg>
          Suivi des cas
        </h1>
        <button className="bouton-icone" aria-label="Actualiser" title="Actualiser" disabled={chargement}
                onClick={() => { recharger(); missions.recharger(); }}>
          <svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true">
            <path d="M20 11a8 8 0 0 0-14.3-4.9L4 8M4 4v4h4M4 13a8 8 0 0 0 14.3 4.9L20 16M20 20v-4h-4" {...trait} />
          </svg>
        </button>
      </div>

      {donnees && (
        <div className="cartes-kpi">
          <Kpi ton="bleu" libelle="Cas de test" valeur={donnees.total} aide="Cas des versions courantes, selon les filtres" />
          <Kpi ton="attente" libelle="À clarifier" valeur={donnees.par_statut.A_CLARIFIER}
               aide={`Dont ${donnees.par_statut.INCOMPLET} incomplet(s) et ${donnees.par_statut.PRET} prêt(s)`} />
          <Kpi ton="succes" libelle="Exécutés" valeur={donnees.executes} aide="Cas avec au moins une exécution (recette)" />
          <Kpi ton="sarcelle" libelle="Non exécutés" valeur={donnees.non_executes} aide="Cas jamais exécutés" />
        </div>
      )}

      <section className="panneau filtres" aria-labelledby="titre-filtres">
        <div id="titre-filtres" className="filtres-titre">Filtres et recherche</div>
        <div className="filtres-champs">
          <div className="champ" style={{ flex: "3 1 320px" }}>
            <label htmlFor="q">Recherche</label>
            <div className="champ-recherche">
              <svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="6.5" {...trait} /><path d="m16 16 4 4" {...trait} /></svg>
              <input id="q" type="search" value={q} onChange={(e) => setQ(e.target.value)}
                     placeholder="Un cas, une mission, un commentaire…" />
            </div>
          </div>
          <div className="champ" style={{ flex: "1 1 200px" }}>
            <label htmlFor="mission">Mission</label>
            <select id="mission" value={mission} onChange={(e) => setMission(e.target.value)}>
              <option value="">Toutes les missions</option>
              {(missions.donnees ?? []).map((m) => <option key={m.id} value={m.id}>{m.reference} — {m.titre}</option>)}
            </select>
          </div>
          <div className="champ" style={{ flex: "1 1 170px" }}>
            <label htmlFor="statut">Statut</label>
            <select id="statut" value={statut} onChange={(e) => setStatut(e.target.value)}>
              <option value="">Tous les statuts</option>
              <optgroup label="Conception">
                {Object.entries(STATUT_CAS).map(([k, v]) => <option key={k} value={k}>{v.libelle}</option>)}
              </optgroup>
              <optgroup label="Recette">
                <option value="EXECUTE">Exécutés</option>
                <option value="NON_EXECUTE">Non exécutés</option>
              </optgroup>
            </select>
          </div>
        </div>
      </section>

      <MessageErreur erreur={erreur} />
      {donnees && <div className="discret-texte">{donnees.total} cas affiché{donnees.total > 1 ? "s" : ""}</div>}
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
              <thead><tr><th>Cas</th><th style={{ width: 150 }}>Couvre</th><th style={{ width: 170 }}>Technique</th>
                <th style={{ width: 120 }}>Conception</th><th style={{ width: 120 }}>Exécution</th></tr></thead>
              <tbody>
                {g.cas.map((c) => {
                  const ex = EXECUTION[c.execution ?? "NOT_RUN"];
                  return (
                    <tr key={c.id}>
                      <td><span className="ref">{c.code}</span> {c.titre}
                        {c.motif_statut && <div className="sous">{c.motif_statut}</div>}</td>
                      <td>{c.references.map((r) => <span key={r} className="ref" style={{ marginRight: 6 }}>{r}</span>)}</td>
                      <td>{c.technique}</td>
                      <td><PastilleCas statut={c.statut} /></td>
                      <td><Pastille ton={ex.ton}>{ex.libelle}</Pastille></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>
      ))}
    </div>
  );
}
