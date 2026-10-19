import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, type EntreeJournal, type Mission } from "../api";
import { Chaine, MessageErreur, PastilleMission, useAction, useDonnees, useSuiviTache } from "../composants";
import { date, EVENEMENTS } from "../libelles";
import CasTests from "./mission/CasTests";
import Exigence from "./mission/Exigence";
import Porte from "./mission/Porte";
import Tracabilite from "./mission/Tracabilite";

const NOM_TACHE: Record<string, string> = {
  ANALYSE: "L'analyse (AG-01)", REECRITURE: "La réécriture", CONCEPTION: "La conception (AG-02)",
};

const LIBELLE_TACHE: Record<string, string> = {
  ANALYSE: "L'agent AG-01 analyse l'exigence",
  REECRITURE: "L'agent réécrit l'exigence à partir de vos réponses",
  CONCEPTION: "L'agent AG-02 conçoit les cas de test",
};

export default function MissionPage() {
  const { id } = useParams();
  const { donnees: m, erreur, recharger } = useDonnees<Mission>("/missions/" + id);
  const [onglet, setOnglet] = useState("exigence");
  const [numeroVersion, setNumeroVersion] = useState<number | null>(null);
  const suivi = useSuiviTache(recharger);

  // Reprend le suivi d'une tâche lancée ailleurs (ou avant un rechargement)
  useEffect(() => {
    if (m && m.taches_en_cours.length && !suivi.enCours) suivi.suivre(m.taches_en_cours[0]);
  }, [m]); // eslint-disable-line react-hooks/exhaustive-deps

  // Après PV-1 ou PV-2, l'utilisateur a surtout besoin de voir les cas
  useEffect(() => {
    if (m?.statut === "ATTENTE_PV2") setOnglet((o) => (o === "exigence" ? "cas" : o));
  }, [m?.statut]);

  if (erreur) return <MessageErreur erreur={erreur} />;
  if (!m) return <div className="charge">Chargement de la mission…</div>;

  const courante = m.versions[m.versions.length - 1];
  const version = m.versions.find((v) => v.numero === numeroVersion) ?? courante;
  const historique = version !== courante;
  const rejet = courante.decisions.find((d) => d.decision === "REJETE");
  const tacheType = suivi.tache?.type ?? (m.statut === "ANALYSE_EN_COURS" ? "ANALYSE"
    : m.statut === "REECRITURE" ? "REECRITURE" : null);
  const lancerTache = (tacheId: number) => { suivi.suivre(tacheId); recharger(); };

  return (
    <div className="pile">
      <div>
        <div className="fil"><Link to="/">Vue de pilotage</Link> / <span className="ref">{m.reference}</span></div>
        <div className="entete-page" style={{ marginBottom: 12 }}>
          <div>
            <h1>{m.titre}</h1>
            <p className="rangee">
              <PastilleMission statut={m.statut} />
              <span>Version {courante.numero} · {courante.nom_source}</span>
              {courante.ia.modele && <span className="discret-texte">IA : {courante.ia.fournisseur} / {courante.ia.modele}</span>}
            </p>
          </div>
          {m.versions.length > 1 && (
            <div className="champ" style={{ minWidth: 220 }}>
              <label htmlFor="version">Version affichée</label>
              <select id="version" value={version.numero} onChange={(e) => setNumeroVersion(Number(e.target.value))}>
                {m.versions.map((v) => (
                  <option key={v.numero} value={v.numero}>
                    Version {v.numero}{v === courante ? " (courante)" : " (archivée)"}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>
        <div className="panneau" style={{ padding: "6px 10px" }}>
          <Chaine statut={m.statut} rejetee={rejet ? rejet.porte : null} />
        </div>
      </div>

      {(suivi.enCours || m.taches_en_cours.length > 0) && (
        <div className="message-info tache-en-cours" role="status">
          {LIBELLE_TACHE[tacheType ?? ""] ?? "L'agent travaille"}… Cette page se met à jour toute seule ;
          vous pouvez aussi la quitter.
        </div>
      )}
      {!suivi.enCours && m.taches_en_cours.length === 0 && m.derniere_tache?.etat === "ECHEC" && (
        <div className="message-erreur" role="alert">
          <strong>{NOM_TACHE[m.derniere_tache.type] ?? "L'agent"} a échoué</strong>
          {m.derniere_tache.termine_le && <> le {date(m.derniere_tache.termine_le)}</>} :{" "}
          {m.derniere_tache.erreur}
        </div>
      )}

      {historique && (
        <div className="message-info">
          Vous consultez la version {version.numero}, archivée en lecture seule.{" "}
          <button className="bouton discret petit" onClick={() => setNumeroVersion(null)}>Revenir à la version courante</button>
        </div>
      )}

      {!historique && <Corrections mission={m} lancerTache={lancerTache} />}

      <div className="deux-colonnes">
        <div className="panneau">
          <div className="onglets" role="tablist" style={{ padding: "0 12px" }}>
            {[["exigence", "Exigence"], ["cas", "Cas de test"], ["tracabilite", "Traçabilité"],
              ["journal", "Journal"]].map(([cle, libelle]) => (
              <button key={cle} role="tab" aria-selected={onglet === cle} onClick={() => setOnglet(cle)}>{libelle}</button>
            ))}
          </div>
          {onglet === "exigence" && (
            <Exigence mission={m} version={version} modifiable={!historique} recharger={recharger}
                      lancerTache={lancerTache} occupe={suivi.enCours} />
          )}
          {onglet === "cas" && <CasTests mission={m} historique={historique} recharger={recharger} />}
          {onglet === "tracabilite" && <Tracabilite missionId={m.id} />}
          {onglet === "journal" && <JournalMission missionId={m.id} />}
        </div>

        <div className="pile">
          {m.porte_en_attente && !historique && (
            <Porte mission={m} recharger={recharger} lancerTache={lancerTache} />
          )}
          <Decisions mission={m} />
          <Participants mission={m} recharger={recharger} />
        </div>
      </div>
    </div>
  );
}

function Corrections({ mission: m, lancerTache }: { mission: Mission; lancerTache: (id: number) => void }) {
  const courante = m.versions[m.versions.length - 1];
  const [texte, setTexte] = useState(courante.texte);
  const action = useAction();
  if (m.statut === "CONCEPTION" && m.taches_en_cours.length === 0) {
    return (
      <div className="message-erreur rangee">
        La conception des cas n'a pas abouti.
        <button className="bouton petit" disabled={action.enCours}
                onClick={() => action.lancer(async () => {
                  const r = await api<{ tache_id: number }>(`/missions/${m.id}/relancer`, { methode: "POST" });
                  lancerTache(r.tache_id);
                })}>Relancer la conception</button>
        <MessageErreur erreur={action.erreur} />
      </div>
    );
  }
  if (m.statut !== "A_CORRIGER" && m.statut !== "ECHEC_ANALYSE") return null;
  const rejet = courante.decisions.find((d) => d.decision === "REJETE");
  return (
    <section className="panneau" style={{ borderColor: "#e3b5ac" }}>
      <div className="panneau-entete">
        <div>
          <h2>{m.statut === "A_CORRIGER" ? "Corriger et resoumettre" : "L'analyse n'a pas abouti"}</h2>
          {rejet
            ? <p>Rejetée à {rejet.porte} : « {rejet.commentaire} »</p>
            : <p>Relancez l'analyse, ou corrigez le texte pour créer une nouvelle version.</p>}
        </div>
      </div>
      <div className="panneau-corps pile">
        <div className="champ">
          <label htmlFor="correction">Texte de la version {courante.numero + 1}</label>
          <textarea id="correction" rows={8} value={texte} onChange={(e) => setTexte(e.target.value)} />
        </div>
        <MessageErreur erreur={action.erreur} />
        <div className="rangee">
          <button className="bouton principal" disabled={action.enCours || !texte.trim()}
                  onClick={() => action.lancer(async () => {
                    const r = await api<{ tache_id: number }>(`/missions/${m.id}/versions`,
                      { methode: "POST", corps: { texte } });
                    lancerTache(r.tache_id);
                  })}>Créer la version {courante.numero + 1} et l'analyser</button>
          {m.statut === "ECHEC_ANALYSE" && (
            <button className="bouton" disabled={action.enCours}
                    onClick={() => action.lancer(async () => {
                      const r = await api<{ tache_id: number }>(`/missions/${m.id}/relancer`, { methode: "POST" });
                      lancerTache(r.tache_id);
                    })}>Relancer l'analyse sans changer le texte</button>
          )}
        </div>
      </div>
    </section>
  );
}

function Decisions({ mission: m }: { mission: Mission }) {
  const decisions = m.versions.flatMap((v) => v.decisions.map((d) => ({ ...d, version: v.numero })));
  if (!decisions.length) return null;
  const nom = (id: number) => m.participants.find((p) => p.id === id)?.nom || m.participants.find((p) => p.id === id)?.email || "Superviseur";
  return (
    <section className="panneau">
      <div className="panneau-entete"><h2>Décisions</h2></div>
      <div className="panneau-corps">
        <ul className="journal">
          {decisions.reverse().map((d, i) => (
            <li key={i}>
              <div className="quand">{date(d.decide_le)} · version {d.version}</div>
              <div><strong>{d.porte}</strong> {d.decision === "APPROUVE" ? "approuvé" : "rejeté"} par {nom(d.decideur_id)}</div>
              {d.auto_validation && <div className="discret-texte">Validé par l'unique acteur de la mission</div>}
              {d.commentaire && <div className="discret-texte">« {d.commentaire} »</div>}
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

function Participants({ mission: m, recharger }: { mission: Mission; recharger: () => void }) {
  const [email, setEmail] = useState("");
  const action = useAction();
  return (
    <section className="panneau">
      <div className="panneau-entete">
        <h2>Participants</h2>
      </div>
      <div className="panneau-corps pile">
        <ul style={{ margin: 0, paddingLeft: 18 }}>
          {m.participants.map((p) => <li key={p.id}>{p.nom || p.email}</li>)}
        </ul>
        <p className="discret-texte">
          {m.participants.length === 1
            ? "Seul participant : vous pouvez valider les Human Gates vous-même. La validation sera marquée comme telle."
            : "Plusieurs participants : un Superviseur qui n'est pas l'auteur doit valider les Human Gates."}
        </p>
        <form className="rangee" onSubmit={(e) => {
          e.preventDefault();
          action.lancer(async () => {
            await api(`/missions/${m.id}/participants`, { methode: "POST", corps: { email } });
            setEmail("");
            recharger();
          });
        }}>
          <input type="email" required placeholder="E-mail d'un collègue" value={email}
                 onChange={(e) => setEmail(e.target.value)} style={{ flex: 1, minWidth: 160 }}
                 aria-label="E-mail du participant à ajouter" />
          <button className="bouton petit" disabled={action.enCours}>Ajouter</button>
        </form>
        <MessageErreur erreur={action.erreur} />
      </div>
    </section>
  );
}

function JournalMission({ missionId }: { missionId: number }) {
  const { donnees } = useDonnees<EntreeJournal[]>(`/missions/${missionId}/journal`);
  return (
    <div className="panneau-corps">
      <ul className="journal">
        {(donnees ?? []).map((e) => (
          <li key={e.id}>
            <div className="quand">{date(e.horodatage)}{e.agent ? " · " + e.agent : ""}</div>
            <div>{EVENEMENTS[e.evenement] ?? e.evenement}</div>
            <DetailsJournal e={e} />
          </li>
        ))}
      </ul>
    </div>
  );
}

function DetailsJournal({ e }: { e: EntreeJournal }) {
  const d = e.details as Record<string, unknown>;
  const morceaux: string[] = [];
  if (d.question) morceaux.push(String(d.question));
  if (d.critere) morceaux.push(String(d.critere));
  if (d.cas) morceaux.push(String(d.cas));
  if (d.motif) morceaux.push("motif : " + String(d.motif));
  if (d.commentaire) morceaux.push("« " + String(d.commentaire) + " »");
  if (d.defauts !== undefined) morceaux.push(`${d.defauts} défaut(s), clarté ${d.score_clarte}/100`);
  if (d.auto_validation) morceaux.push("auto-validation (acteur unique)");
  if (d.erreur) morceaux.push(String(d.erreur));
  if (d.ia) morceaux.push("IA " + String(d.ia));
  return morceaux.length ? <div className="discret-texte">{morceaux.join(" · ")}</div> : null;
}
