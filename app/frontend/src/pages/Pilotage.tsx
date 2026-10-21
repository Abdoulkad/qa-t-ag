import { useMemo, useState, type ReactNode } from "react";
import { Link, useNavigate } from "react-router-dom";
import type { EntreeJournal, Pilotage, ResumeMission } from "../api";
import { MessageErreur, MiniChaine, PastilleMission, useDonnees } from "../composants";
import { date, EVENEMENTS } from "../libelles";

const FILTRES: { cle: string; libelle: string; garde: (m: ResumeMission) => boolean }[] = [
  { cle: "cours", libelle: "En cours", garde: (m) => !["VALIDEE", "CLOTUREE"].includes(m.statut) },
  { cle: "gate", libelle: "Human Gate", garde: (m) => m.statut === "ATTENTE_PV1" || m.statut === "ATTENTE_PV2" },
  { cle: "validees", libelle: "Validées", garde: (m) => m.statut === "VALIDEE" || m.statut === "CLOTUREE" },
  { cle: "toutes", libelle: "Toutes", garde: () => true },
];

const trait = { fill: "none", stroke: "currentColor", strokeWidth: 2, strokeLinecap: "round" as const, strokeLinejoin: "round" as const };
const ICONES: Record<string, ReactNode> = {
  porte: <path d="M12 3 21 12 12 21 3 12Z" {...trait} />,
  attente: <><circle cx="12" cy="12" r="9" {...trait} /><path d="M9.5 9.5a2.5 2.5 0 1 1 3.5 2.3c-.6.3-1 .8-1 1.5V14M12 17.2v.1" {...trait} /></>,
  alerte: <><path d="M12 4 21.5 20h-19Z" {...trait} /><path d="M12 10v4M12 17v.1" {...trait} /></>,
  succes: <path d="m5 12 4.5 4.5L19 7" {...trait} strokeWidth={2.2} />,
};

/** Qui a agi : la personne (nom, sinon e-mail), ou l'agent IA. */
function auteur(e: EntreeJournal) {
  if (e.acteur) return e.acteur.nom || e.acteur.email;
  if (e.agent && /^AG-/.test(e.agent)) return "Agent " + e.agent;
  return e.agent ? e.agent : "Agent IA";
}

/** Une précision courte sur l'action (porte, question, critère, motif…). */
function precision(e: EntreeJournal) {
  const d = e.details as Record<string, unknown>;
  if (e.evenement === "porte_decidee") return `${String(e.agent ?? d.porte ?? "")} ${d.decision === "APPROUVE" ? "approuvé" : "rejeté"}`;
  if (e.evenement === "conception_terminee" && typeof d.cas === "number") return `${d.cas} cas`;
  const morceaux = [d.question, d.critere, d.regle, d.defaut, d.cas].filter(Boolean).map(String);
  if (d.defauts !== undefined) morceaux.push(`${d.defauts} défaut(s), clarté ${d.score_clarte}/100`);
  if (d.motif) morceaux.push("« " + String(d.motif) + " »");
  return morceaux.join(" · ");
}

function couleurClarte(s: number | null) {
  if (s === null) return "var(--encre-pale)";
  return s >= 70 ? "var(--succes)" : s >= 40 ? "var(--attente)" : "var(--alerte)";
}

/** Une carte « à faire » : un ton, un compte, les missions concernées. */
function CarteAFaire({ ton, titre, missions, detail, rien }: {
  ton: "porte" | "attente" | "alerte" | "succes"; titre: string; missions: ResumeMission[];
  detail: (m: ResumeMission) => string; rien: string;
}) {
  return (
    <section className={"carte-afaire " + ton} aria-label={titre}>
      <div className="carte-afaire-tete">
        <span className="carte-afaire-titre">
          <span className="carte-afaire-icone"><svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true">{ICONES[ton]}</svg></span>
          {titre}
        </span>
        <span className="carte-afaire-nombre">{missions.length}</span>
      </div>
      {missions.length ? (
        <ul>
          {missions.slice(0, 4).map((m) => (
            <li key={m.id}>
              <Link to={"/missions/" + m.id}><span className="ref">{m.reference}</span> {m.titre}</Link>
              <span className="detail"> · {detail(m)}</span>
            </li>
          ))}
          {missions.length > 4 && <li className="detail">et {missions.length - 4} autre(s)</li>}
        </ul>
      ) : <div className="rien">{rien}</div>}
    </section>
  );
}

export default function PilotagePage() {
  const navigate = useNavigate();
  const p = useDonnees<Pilotage>("/pilotage");
  const missions = useDonnees<ResumeMission[]>("/missions");
  const journal = useDonnees<EntreeJournal[]>("/journal?limite=12");
  const [filtre, setFiltre] = useState("cours");
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
      <div className="entete-page" style={{ marginBottom: 4 }}>
        <div>
          <h1>Vue de pilotage</h1>
          <p>Ce qui attend une action, puis l'avancement de chaque mission.</p>
        </div>
        <Link to="/analyse" className="bouton principal">Analyser une exigence</Link>
      </div>

      <MessageErreur erreur={p.erreur || missions.erreur} />

      {p.donnees && (
        <div className="cartes-afaire">
          <CarteAFaire ton="porte" titre="Human Gates en attente" missions={p.donnees.file_human_gate}
                       detail={(m) => (m.statut === "ATTENTE_PV1" ? "PV-1" : "PV-2") + (m.bloquants ? ` · ${m.bloquants} point(s) à traiter` : "")}
                       rien="Aucune décision en attente." />
          <CarteAFaire ton="attente" titre="Questions bloquantes" missions={p.donnees.questions_bloquantes}
                       detail={(m) => m.questions_bloquantes.join(", ")} rien="Aucune question ne bloque la réécriture." />
          <CarteAFaire ton="alerte" titre="Agent en échec" missions={p.donnees.en_echec}
                       detail={(m) => m.en_echec ?? ""} rien="Aucun échec : tous les agents ont abouti." />
          <CarteAFaire ton="succes" titre="Prêtes pour la recette" missions={p.donnees.pretes_recette}
                       detail={(m) => `${m.cas.total} cas validés`} rien="Aucune mission validée à PV-2 pour l'instant." />
        </div>
      )}

      <div className="pilotage-colonnes">
      <section className="panneau" style={{ minWidth: 0 }}>
        <div className="panneau-entete" style={{ flexWrap: "wrap", gap: 12 }}>
          <h2>Missions</h2>
          <div className="puces" role="group" aria-label="Filtrer les missions">
            {FILTRES.map((f) => (
              <button key={f.cle} type="button" className="puce" aria-pressed={filtre === f.cle}
                      onClick={() => setFiltre(f.cle)}>
                {f.libelle} · {(missions.donnees ?? []).filter(f.garde).length}
              </button>
            ))}
          </div>
          <input type="search" placeholder="Rechercher une mission" value={recherche}
                 onChange={(e) => setRecherche(e.target.value)} style={{ maxWidth: 240, marginLeft: "auto" }}
                 aria-label="Rechercher une mission" />
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
                <tr><th>Mission</th><th style={{ width: 220 }}>Avancement</th><th style={{ width: 80 }}>Clarté</th>
                  <th>Prochaine action</th><th style={{ width: 110 }}>Mise à jour</th></tr>
              </thead>
              <tbody>
                {liste.map((m) => (
                  <tr key={m.id} className="cliquable" onClick={() => navigate("/missions/" + m.id)}>
                    <td>
                      <Link to={"/missions/" + m.id} onClick={(e) => e.stopPropagation()}
                            style={{ color: "inherit", textDecoration: "none", fontWeight: 500 }}>
                        <span className="ref">{m.reference}</span> {m.titre}
                      </Link>
                      <div className="sous">Version {m.version}</div>
                    </td>
                    <td>
                      <MiniChaine statut={m.statut} enEchec={!!m.en_echec} />
                      <div style={{ marginTop: 4 }}><PastilleMission statut={m.statut} /></div>
                    </td>
                    <td style={{ fontWeight: 600, color: couleurClarte(m.score_clarte) }}>
                      {m.score_clarte === null ? "—" : m.score_clarte}
                    </td>
                    <td>{m.prochaine_action}</td>
                    <td className="discret-texte">{date(m.modifie_le)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <aside className="journal-qa" aria-labelledby="titre-journal">
        <h2 id="titre-journal" className="titre-mono">
          <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="8.5" fill="none" stroke="currentColor" strokeWidth="1.8" /><path d="M12 7.5V12l3 2" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" /></svg>
          Journal QA
        </h2>
        {journal.donnees?.length === 0 && <p className="discret-texte">Rien pour l'instant.</p>}
        <ol className="fil-journal">
          {(journal.donnees ?? []).map((e) => (
            <li key={e.id}>
              <div className="quand">{date(e.horodatage)}</div>
              <div className="qui">
                {e.mission_id
                  ? <Link to={"/missions/" + e.mission_id}>{refs.get(e.mission_id) ?? "Mission"}</Link>
                  : <span>QA-T-AG</span>}
                {" · "}<span title={e.acteur?.email}>{auteur(e)}</span>
              </div>
              <div className="quoi">
                {EVENEMENTS[e.evenement] ?? e.evenement}
                {precision(e) && <> — {precision(e)}</>}
              </div>
            </li>
          ))}
        </ol>
      </aside>
      </div>

    </div>
  );
}
