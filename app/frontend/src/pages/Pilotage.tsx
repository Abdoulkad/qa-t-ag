import { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import type { EntreeJournal, Pilotage, ResumeMission } from "../api";
import { MessageErreur, MiniChaine, PastilleMission, useDonnees } from "../composants";
import { date, EVENEMENTS } from "../libelles";

const FILTRES: { cle: string; libelle: string; garde: (m: ResumeMission) => boolean }[] = [
  { cle: "toutes", libelle: "Toutes", garde: () => true },
  { cle: "gate", libelle: "Human Gate", garde: (m) => m.statut === "ATTENTE_PV1" || m.statut === "ATTENTE_PV2" },
  { cle: "cours", libelle: "En cours", garde: (m) => ["ANALYSE_EN_COURS", "CLARIFICATION", "REECRITURE", "CONCEPTION", "EN_RECETTE"].includes(m.statut) },
  { cle: "corriger", libelle: "À corriger", garde: (m) => m.statut === "A_CORRIGER" || m.statut === "ECHEC_ANALYSE" },
  { cle: "validees", libelle: "Validées", garde: (m) => m.statut === "VALIDEE" || m.statut === "CLOTUREE" },
];

function pourcent(v: number | null) {
  return v === null ? "—" : v + " %";
}

export default function PilotagePage() {
  const navigate = useNavigate();
  const p = useDonnees<Pilotage>("/pilotage");
  const missions = useDonnees<ResumeMission[]>("/missions");
  const journal = useDonnees<EntreeJournal[]>("/journal?limite=12");
  const [filtre, setFiltre] = useState("toutes");
  const [recherche, setRecherche] = useState("");

  const refs = useMemo(() => new Map((missions.donnees ?? []).map((m) => [m.id, m.reference])),
                       [missions.donnees]);
  const liste = useMemo(() => {
    const f = FILTRES.find((x) => x.cle === filtre)!;
    const q = recherche.trim().toLowerCase();
    return (missions.donnees ?? []).filter((m) => f.garde(m) &&
      (!q || m.titre.toLowerCase().includes(q) || m.reference.toLowerCase().includes(q)));
  }, [missions.donnees, filtre, recherche]);

  return (
    <div className="pile">
      <div className="entete-page">
        <div>
          <h1>Vue de pilotage</h1>
          <p>Vos missions, et les décisions qui vous attendent.</p>
        </div>
        <Link to="/analyse" className="bouton principal">Analyser une exigence</Link>
      </div>

      <MessageErreur erreur={p.erreur || missions.erreur} />

      {p.donnees && (
        <section className="indicateurs" aria-label="Indicateurs">
          <div className="indicateur">
            <div className="indicateur-valeur">{p.donnees.missions}</div>
            <div className="indicateur-libelle">Missions suivies</div>
          </div>
          <div className="indicateur porte">
            <div className="indicateur-valeur">{p.donnees.human_gate_en_attente}</div>
            <div className="indicateur-libelle">Décisions Human Gate en attente</div>
          </div>
          <div className="indicateur">
            <div className="indicateur-valeur">{pourcent(p.donnees.taux_pass)}</div>
            <div className="indicateur-libelle">Cas exécutés en succès</div>
          </div>
          <div className="indicateur">
            <div className="indicateur-valeur">{pourcent(p.donnees.taux_approbation)}</div>
            <div className="indicateur-libelle">Décisions approuvées</div>
          </div>
        </section>
      )}

      <div className="deux-colonnes">
        <div className="pile">
          {p.donnees && p.donnees.file_human_gate.length > 0 && (
            <section className="porte-panneau">
              <div className="panneau-entete">
                <h2>À décider</h2>
                <p>Ces missions attendent une validation humaine.</p>
              </div>
              <div className="panneau-corps sans-marge table-defile">
                <table>
                  <tbody>
                    {p.donnees.file_human_gate.map((m) => (
                      <tr key={m.id} className="cliquable" onClick={() => navigate("/missions/" + m.id)}>
                        <td style={{ width: 90 }}><span className="ref">{m.reference}</span></td>
                        <td>{m.titre}<div className="sous">Version {m.version}</div></td>
                        <td style={{ textAlign: "right" }}><PastilleMission statut={m.statut} /></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          <section className="panneau">
            <div className="panneau-entete">
              <h2>Missions</h2>
              <input type="search" placeholder="Rechercher une mission" value={recherche}
                     onChange={(e) => setRecherche(e.target.value)} style={{ maxWidth: 260 }}
                     aria-label="Rechercher une mission" />
            </div>
            <div className="onglets" role="tablist" style={{ padding: "0 12px" }}>
              {FILTRES.map((f) => (
                <button key={f.cle} role="tab" aria-selected={filtre === f.cle} onClick={() => setFiltre(f.cle)}>
                  {f.libelle}<span className="nb">{(missions.donnees ?? []).filter(f.garde).length}</span>
                </button>
              ))}
            </div>
            {missions.donnees && liste.length === 0 && (
              <div className="vide">
                {missions.donnees.length === 0
                  ? <><strong>Aucune mission pour l'instant</strong>Commencez par déposer une SFD ou une User Story.
                      <div style={{ marginTop: 14 }}><Link to="/analyse" className="bouton principal">Analyser une exigence</Link></div></>
                  : "Aucune mission ne correspond à ce filtre."}
              </div>
            )}
            {liste.length > 0 && (
              <div className="table-defile">
                <table>
                  <thead>
                    <tr><th>Mission</th><th>Avancement</th><th>Clarté</th><th>Statut</th></tr>
                  </thead>
                  <tbody>
                    {liste.map((m) => (
                      <tr key={m.id} className="cliquable" onClick={() => navigate("/missions/" + m.id)}>
                        <td>
                          <Link to={"/missions/" + m.id} onClick={(e) => e.stopPropagation()}
                                style={{ color: "inherit", textDecoration: "none" }}>
                            <span className="ref">{m.reference}</span> {m.titre}
                          </Link>
                          <div className="sous">Version {m.version} · modifiée le {date(m.modifie_le)}</div>
                        </td>
                        <td><MiniChaine statut={m.statut} /></td>
                        <td>{m.score_clarte === null ? "—" : m.score_clarte + "/100"}</td>
                        <td><PastilleMission statut={m.statut} /></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </div>

        <aside className="panneau">
          <div className="panneau-entete"><h2>Journal QA</h2></div>
          <div className="panneau-corps">
            {journal.donnees?.length === 0 && <p className="discret-texte">Rien pour l'instant.</p>}
            <ul className="journal">
              {(journal.donnees ?? []).map((e) => (
                <li key={e.id}>
                  <div className="quand">{date(e.horodatage)}</div>
                  <div>
                    {e.mission_id && <Link className="ref" to={"/missions/" + e.mission_id}>{refs.get(e.mission_id) ?? "Mission"}</Link>}{" "}
                    {EVENEMENTS[e.evenement] ?? e.evenement}
                    {e.evenement === "porte_decidee" && <> · {String(e.agent)} {e.details.decision === "APPROUVE" ? "approuvé" : "rejeté"}</>}
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </aside>
      </div>
    </div>
  );
}
